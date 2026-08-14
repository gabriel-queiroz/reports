"""SQL generation tool with hardcoded security validations."""

import json
import logging
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from domain.agents.reports_b2b.report_generator.prompts import (
    sql_system_prompt,
    sql_user_prompt,
)
from domain.agents.reports_b2b.guardrails import (
    InvalidGroupIdError,
    sanitize_question,
    validate_group_id,
)
from domain.agents.reports_b2b.schema_extractor import get_all_tables_for_sql_generation
from domain.agents.reports_b2b.sql_guard import SqlGuardError, guard_query
from domain.agents.reports_b2b.sql_validator import (
    GROUP_ID_FIELD_MAPPING,
    QueryNotAllowedError,
)
from domain.core.ioc import get_logger
from domain.infra.genplat.genplat_provider import GenplatProvider

logger = logging.getLogger(__name__)

# Tentativas de geração de SQL. A partir da segunda, o LLM recebe o erro da
# tentativa anterior — antes disso, todas as validações tentavam duas vezes com
# exatamente o mesmo prompt.
MAX_SQL_ATTEMPTS = 2


class GenerateSQLInput(BaseModel):
    """Input schema for SQL generation tool."""

    question: str = Field(
        description=(
            "Pergunta do usuário reescrita de forma completa e autocontida, "
            "incluindo período, filtros e agrupamentos desejados."
        )
    )
    domain: Literal["colaboradores", "recargas", "financeiro"] = Field(
        description="Domínio de dados a consultar."
    )
    group_id: str = Field(
        description=(
            "UUID do grupo de empresa para filtro de segurança "
            "multi-tenant (OBRIGATÓRIO)."
        )
    )


class GeneratedQuery(BaseModel):
    """Query SQL gerada a partir da pergunta do usuário."""

    sql: str = Field(
        description=(
            "Query SELECT completa para Databricks (Spark SQL), "
            "sem markdown e sem explicações."
        )
    )


# Global LLM instance (will be initialized lazily)
_llm_instance: ChatOpenAI | None = None
_genplat_provider: GenplatProvider | None = None
_schema_content: str | None = None
_tabelas_doc: str | None = None


def _initialize_llm(genplat_provider: GenplatProvider) -> ChatOpenAI:
    """Initialize the LLM instance (lazy initialization).

    `temperature=0`: geração de SQL não se beneficia de variedade — a mesma
    pergunta deve dar a mesma query, e é isso que torna o golden set (fase 6)
    capaz de medir mudança de prompt.

    `max_tokens` alto: relatório com muitos campos trunca o structured output,
    e o SQL cortado chega ao usuário parecendo alucinação.
    """
    global _llm_instance, _genplat_provider
    if _llm_instance is None:
        _genplat_provider = genplat_provider
        _llm_instance = genplat_provider.create_llm(
            model="gpt-4.1",
            temperature=0,
            max_tokens=4096,
        )
    return _llm_instance


def _correction_message(rejected_sql: str, error: SqlGuardError) -> str:
    """A mensagem de correção que realimenta o LLM na próxima tentativa.

    Vai como turno de `user` (e não de `assistant`) de propósito: o structured
    output ocupa o turno do assistente, e nem todo provider aceita um turno de
    assistente avulso no meio.
    """
    return (
        "A query abaixo foi REJEITADA pela validação. Corrija o que o erro "
        "aponta e devolva a query completa e corrigida — não explique.\n\n"
        f"Query rejeitada:\n{rejected_sql}\n\n"
        f"Motivo da rejeição ({type(error).__name__}):\n{error}"
    )


def _load_schema() -> str:
    """Load schema.md from the data directory."""
    global _schema_content
    if _schema_content is not None:
        return _schema_content

    # Navigate from gerar_sql_tool.py to reports_b2b/data/schema.md
    schema_path = Path(__file__).parent.parent.parent / "data" / "schema.md"

    if not schema_path.exists():
        logger.warning("Schema file not found: %s", schema_path)
        return "Schema não disponível no momento."

    _schema_content = schema_path.read_text(encoding="utf-8")
    return _schema_content


def _load_tables_doc() -> str:
    """Load tabelas documentation (same as schema.md for now)."""
    global _tabelas_doc
    if _tabelas_doc is None:
        _tabelas_doc = _load_schema()
    return _tabelas_doc


def _generate_sql_internal(
    question: str,
    domain: str,
    group_id: str,
    genplat_provider: GenplatProvider,
) -> str:
    """
    Generate SQL from question, validating fields against documentation.

    Args:
        question: User question
        domain: Data domain
        group_id: Company group UUID for data filtering
            (MANDATORY for multi-tenant safety)
        genplat_provider: GenPlat provider for LLM creation

    Returns:
        Valid SQL to execute

    Raises:
        InvalidGroupIdError: If group_id is missing or is not a UUID
        InvalidQuestionError: If the question is empty or too long
        SqlGuardError: If the AST guard rejects the query (a QueryNotAllowedError)
    """
    log = get_logger()

    log.log_information(
        "Starting SQL generation",
        domain=domain,
        question_length=len(question),
    )

    # GUARDRAIL: este é o ponto onde o group_id vira f-string (prompt e, depois,
    # WHERE do SQL). Daqui para baixo só circula o UUID canônico.
    try:
        group_id = validate_group_id(group_id)
    except InvalidGroupIdError as e:
        log.log_error("group_id invalid for SQL generation", e, domain=domain)
        raise

    # A pergunta é interpolada dentro de <pergunta> no prompt do usuário.
    question = sanitize_question(question)

    # Load documentation
    tables_doc = _load_tables_doc()

    # Get all tables from schema.md for SQL generation
    # LLM needs to see all tables to understand relationships and create proper JOINs
    tables = get_all_tables_for_sql_generation()

    # Build security instruction for group_id (mandatory)
    group_field = GROUP_ID_FIELD_MAPPING.get(domain, "companies.company_group_id")
    group_id_restriction = (
        f"Query MUST filter by {group_field} = '{group_id}' to ensure "
        f"only correct company group data is returned. "
        f"This restriction is MANDATORY for multi-tenant security."
    )

    # Create prompts for SQL generation
    sql_system = sql_system_prompt(
        restricao_group_id=group_id_restriction,
        documentacao_tabelas=tables_doc,
        group_id=group_id,
    )
    sql_user = sql_user_prompt(
        dominio=domain,
        tabelas=tables,
        pergunta=question,
        group_id=group_id,
    )

    # Initialize LLM
    llm = _initialize_llm(genplat_provider)
    llm_with_struct = llm.with_structured_output(GeneratedQuery)

    # A conversa cresce a cada tentativa: o erro do guard entra como mensagem,
    # senão o retry reinvoca o prompt idêntico e só gasta uma chamada de LLM.
    messages = [("system", sql_system), ("user", sql_user)]

    for attempt in range(1, MAX_SQL_ATTEMPTS + 1):
        log.log_information(
            "Generating SQL with LLM",
            domain=domain,
            attempt=attempt,
            max_attempts=MAX_SQL_ATTEMPTS,
        )

        response: GeneratedQuery = llm_with_struct.invoke(messages)
        sql = response.sql

        log.log_information(
            "LLM SQL generated",
            domain=domain,
            sql_length=len(sql),
            sql=sql,
        )

        # Guard de AST: statement único de leitura, tabelas do catálogo, filtro
        # de tenant injetado e conferido na árvore, coluna de grupo na saída.
        # O que volta é o SQL regerado a partir da AST — não a string do LLM.
        try:
            sql = guard_query(sql, group_id)
            log.log_information(
                "SQL generated successfully",
                domain=domain,
                sql_length=len(sql),
                group_field=group_field,
                sql=sql,
            )
            return sql
        except SqlGuardError as e:
            log.log_warning(
                "AST guard rejected the query",
                domain=domain,
                attempt=attempt,
                max_attempts=MAX_SQL_ATTEMPTS,
                reason=type(e).__name__,
                error=str(e),
            )
            if attempt < MAX_SQL_ATTEMPTS:
                messages.append(("user", _correction_message(sql, e)))
                continue

            log.log_error(
                "SQL generation failed after all attempts",
                e,
                domain=domain,
                max_attempts=MAX_SQL_ATTEMPTS,
            )
            raise


@tool(args_schema=GenerateSQLInput)
def generate_sql_tool(
    question: str,
    domain: str,
    group_id: str,
) -> str:
    """Generate Databricks SQL with hardcoded security validations.

    Returns JSON with status, message and SQL (if successful).
    """
    log = get_logger()

    # Placeholder para genplat_provider (será injetado pelo agente)
    # TODO: Passar genplat_provider via contexto da tool
    try:
        from domain.infra.genplat.genplat_provider import GenplatProvider

        genplat_provider = GenplatProvider(log)
        log.log_information("GenplatProvider initialized", domain=domain)
    except Exception as e:
        log.log_error("Failed to initialize GenplatProvider", e, domain=domain)
        return json.dumps(
            {
                "status": "erro",
                "mensagem": "Falha ao inicializar SQL generator. Tente novamente.",
            },
            ensure_ascii=False,
        )

    try:
        log.log_information(
            "generate_sql_tool called",
            domain=domain,
            question_length=len(question),
        )
        sql = _generate_sql_internal(question, domain, group_id, genplat_provider)
        log.log_information(
            "SQL generated in generate_sql_tool",
            domain=domain,
            sql_length=len(sql),
            status="success",
        )
        return json.dumps(
            {
                "status": "pending_execution",
                "message": (
                    "Query prepared and registered. Report will be delivered "
                    "as .csv file."
                ),
                "sql": sql,
            },
            ensure_ascii=False,
        )
    except QueryNotAllowedError as e:
        log.log_warning(
            "Query blocked by validators in generate_sql_tool",
            domain=domain,
            error=str(e),
        )
        return json.dumps(
            {
                "status": "error",
                "message": (
                    "Could not complete this query. Try rephrasing the question."
                ),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.log_error(
            "Failed to generate SQL in generate_sql_tool",
            e,
            domain=domain,
        )
        return json.dumps(
            {
                "status": "error",
                "message": "Temporary problem generating SQL. Try again shortly.",
            },
            ensure_ascii=False,
        )
