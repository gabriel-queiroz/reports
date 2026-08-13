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
from domain.agents.reports_b2b.schema_extractor import get_all_tables_for_sql_generation
from domain.agents.reports_b2b.sql_validator import (
    GROUP_ID_FIELD_MAPPING,
    QueryNotAllowedError,
    validate_alias_misuse,
    validate_company_group_id_in_select,
    validate_group_id_present,
    validate_mandatory_joins,
)
from domain.core.ioc import get_logger
from domain.infra.genplat.genplat_provider import GenplatProvider

logger = logging.getLogger(__name__)


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
    """Initialize the LLM instance (lazy initialization)."""
    global _llm_instance, _genplat_provider
    if _llm_instance is None:
        _genplat_provider = genplat_provider
        _llm_instance = genplat_provider.create_llm(
            model="gpt-4.1",
            temperature=0.2,
            max_tokens=1024,
        )
    return _llm_instance


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
        ValueError: If group_id not provided
        InvalidFieldsError: If question mentions non-existent fields
        QueryNotAllowedError: If unable to inject multi-tenant filter
    """
    log = get_logger()

    log.log_information(
        "Starting SQL generation",
        domain=domain,
        question_length=len(question),
    )

    # Validate group_id was provided
    if not group_id or not group_id.strip():
        log.log_error(
            "group_id missing for SQL generation",
            ValueError(
                "group_id is mandatory for multi-tenant security. "
                "Without data isolation filter, query will be rejected."
            ),
            domain=domain,
        )
        raise ValueError(
            "group_id is mandatory for multi-tenant security. "
            "Without data isolation filter, query will be rejected."
        )

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

    # Attempt SQL generation with automatic retry if filter is missing
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        log.log_information(
            "Generating SQL with LLM",
            domain=domain,
            attempt=attempt,
            max_attempts=max_attempts,
        )

        response: GeneratedQuery = llm_with_struct.invoke(
            [("system", sql_system), ("user", sql_user)]
        )
        sql = response.sql

        log.log_information(
            "LLM SQL generated",
            domain=domain,
            sql_length=len(sql),
            sql=sql,
        )

        # Valida que o SQL inclui os JOINs obrigatórios para
        # filtrar por company_group_id
        try:
            validate_mandatory_joins(sql, domain)
            log.log_information(
                "Mandatory JOINs validation passed",
                domain=domain,
            )
        except Exception as e:
            log.log_warning(
                "Mandatory JOINs validation failed",
                domain=domain,
                error=str(e),
            )
            raise

        # Valida que o LLM não alucionou e usou aliases PT-BR como nomes de campos
        try:
            alias_errors = validate_alias_misuse(sql, tables_doc, domain)
            if alias_errors:
                log.log_warning(
                    "Alias misuse validation failed",
                    domain=domain,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    errors=alias_errors,
                )
                if attempt < max_attempts:
                    # Continua para próxima tentativa (o LLM será chamado novamente)
                    continue
                else:
                    log.log_error(
                        "SQL generation failed - alias misuse not corrected",
                        None,
                        domain=domain,
                        max_attempts=max_attempts,
                        errors=alias_errors,
                    )
                    raise Exception(
                        f"SQL gerado com aliases PT-BR usados incorretamente "
                        f"após {max_attempts} tentativas:\n" + "\n".join(alias_errors)
                    )
            log.log_information(
                "Alias misuse validation passed",
                domain=domain,
            )
        except Exception as e:
            if "alias misuse not corrected" not in str(e):
                log.log_warning(
                    "Alias misuse validation error",
                    domain=domain,
                    error=str(e),
                )
            raise

        # Valida que a coluna company_group_id está presente no SELECT
        try:
            select_errors = validate_company_group_id_in_select(sql)
            if select_errors:
                log.log_warning(
                    "company_group_id in SELECT validation failed",
                    domain=domain,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    errors=select_errors,
                )
                if attempt < max_attempts:
                    continue
                else:
                    log.log_error(
                        "SQL generation failed - company_group_id column not present",
                        None,
                        domain=domain,
                        max_attempts=max_attempts,
                        errors=select_errors,
                    )
                    raise Exception(
                        "SQL gerado sem a coluna company_group_id no SELECT "
                        f"após {max_attempts} tentativas:\n" + "\n".join(select_errors)
                    )
            log.log_information(
                "company_group_id in SELECT validation passed",
                domain=domain,
            )
        except Exception as e:
            if "company_group_id column not present" not in str(e):
                log.log_warning(
                    "company_group_id in SELECT validation error",
                    domain=domain,
                    error=str(e),
                )
            raise

        # Valida que o LLM incluiu o filtro de segurança
        # multi-tenant (obrigatório)
        try:
            sql = validate_group_id_present(sql, group_field, group_id, domain)
            log.log_information(
                "SQL generated successfully",
                domain=domain,
                sql_length=len(sql),
                group_field=group_field,
                sql=sql,
            )
            return sql
        except QueryNotAllowedError as e:
            log.log_warning(
                "group_id filter validation failed",
                domain=domain,
                attempt=attempt,
                max_attempts=max_attempts,
                error=str(e),
            )
            if attempt < max_attempts:
                continue
            else:
                log.log_error(
                    "SQL generation failed after all attempts",
                    e,
                    domain=domain,
                    max_attempts=max_attempts,
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
