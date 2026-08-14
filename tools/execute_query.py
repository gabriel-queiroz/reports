"""Tool for data consultation: generates SQL, validates, and calls reports service."""

import json
from typing import Annotated, Literal

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from pydantic import BaseModel, Field

from domain.agents.reports_b2b.report_generator.tools.generate_query_tool import (
    _generate_sql_internal,
)
from domain.agents.reports_b2b.guardrails import (
    InvalidGroupIdError,
    InvalidQuestionError,
    sanitize_question,
    validate_group_id,
)
from domain.agents.reports_b2b.sql_validator import (
    InvalidFieldsError,
    QueryNotAllowedError,
)
from domain.core.ioc import get_logger
from domain.infra.genplat.genplat_provider import GenplatProvider


class ExecuteQueryInput(BaseModel):
    """Input for the query execution tool."""

    question: str = Field(
        description=(
            "Pergunta do usuário reescrita de forma completa e autocontida, "
            "incluindo período, filtros e agrupamentos desejados."
        )
    )
    domain: Literal["colaboradores", "recargas", "financeiro"] = Field(
        description="Domínio de dados a consultar."
    )
    desired_fields: str = Field(
        default="all",
        description=(
            "Campos que o usuário quer no relatório. "
            "Pode ser 'all' (todos os campos), ou números/nomes específicos "
            "como '1,3,5'. "
            "Se não especificado, usa todos os campos disponíveis do domínio."
        ),
    )


@tool(args_schema=ExecuteQueryInput)
async def execute_query(
    question: str,
    domain: Literal["colaboradores", "recargas", "financeiro"],
    desired_fields: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Execute data query: generate SQL, validate, and request report generation.

    Returns JSON with status, message and report tracking ID (if successful).

    Note: group_id and user_id are retrieved from injected state.
    """
    logger = get_logger()

    # Get group_id from metadata and user_id from top-level state
    metadata = state.get("metadata", {})
    user_id = state.get("user_id", "unknown")

    # GUARDRAIL: sem tenant válido não há consulta. O default "unknown" que
    # existia aqui gerava query para um grupo inexistente e ainda passava pela
    # validação do reports_service.
    try:
        group_id = validate_group_id(metadata.get("group_id"))
    except InvalidGroupIdError as e:
        logger.log_warning(
            "execute_query blocked: invalid group_id",
            domain=domain,
            user_id=user_id,
            error=str(e),
        )
        return json.dumps(
            {
                "status": "error",
                "message": (
                    "Não foi possível identificar o grupo de empresas desta "
                    "sessão. A consulta não foi executada."
                ),
            },
            ensure_ascii=False,
        )

    # GUARDRAIL: a pergunta é dado, não instrução — ela entra dentro de
    # <pergunta> no prompt de geração de SQL.
    try:
        question = sanitize_question(question)
    except InvalidQuestionError as e:
        logger.log_warning(
            "execute_query blocked: invalid question",
            domain=domain,
            user_id=user_id,
            error=str(e),
        )
        return json.dumps(
            {"status": "invalid_question", "message": str(e)},
            ensure_ascii=False,
        )

    try:
        genplat_provider = GenplatProvider(logger)
    except Exception as e:
        logger.log_error("Failed to initialize GenplatProvider", e)
        return json.dumps(
            {
                "status": "error",
                "message": "Failed to initialize SQL generator. Try again.",
            },
            ensure_ascii=False,
        )

    try:
        logger.log_information(
            "execute_query tool called",
            domain=domain,
            user_id=user_id,
            group_id=group_id,
            question_length=len(question),
        )

        # Generate SQL with validations (4 layers)
        sql = _generate_sql_internal(question, domain, group_id, genplat_provider)

        logger.log_information(
            "SQL generated in execute_query",
            domain=domain,
            sql_length=len(sql),
            sql=sql,
        )

        # Request report generation via Reports Service API (groupId validation)
        logger.log_information(
            "Calling Reports Service API",
            domain=domain,
            user_id=user_id,
            sql_length=len(sql),
        )
        from domain.agents.reports_b2b.reports_service import generate_reports

        # Directly await async function (tool is now async)
        result = await generate_reports(sql, group_id=group_id, user_id=user_id)

        report_id = result.get("id")
        logger.log_information(
            "Report generation requested successfully",
            domain=domain,
            report_id=report_id,
            user_id=user_id,
        )

        return json.dumps(
            {
                "status": "success",
                "message": "Report generation requested successfully.",
                "report_id": report_id,
                "result": result,
            },
            ensure_ascii=False,
        )

    except InvalidFieldsError as e:
        logger.log_warning(
            "Invalid fields error in execute_query",
            domain=domain,
            user_id=user_id,
            error=str(e),
        )
        return json.dumps(
            {
                "status": "invalid_fields",
                "message": f"I couldn't understand some fields you mentioned. {e!s}",
            },
            ensure_ascii=False,
        )
    except QueryNotAllowedError as e:
        logger.log_warning(
            "Query blocked by validators in execute_query",
            domain=domain,
            user_id=user_id,
            error=str(e),
        )
        return json.dumps(
            {
                "status": "error",
                "message": (
                    "Could not complete this query. Try reformulating your question."
                ),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        logger.log_error(
            "Failed to generate/execute query in execute_query",
            e,
            domain=domain,
            user_id=user_id,
        )
        return json.dumps(
            {
                "status": "error",
                "message": (
                    "A temporary problem occurred while fetching data. "
                    "Try again shortly."
                ),
            },
            ensure_ascii=False,
        )
