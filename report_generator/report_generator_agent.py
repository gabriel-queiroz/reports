"""Report Generator Agent — ReAct reports-b2b workflow.

Implements the ReAct pattern with a generate_query_tool for SQL generation.
The agent reasons about when to call the tool, and the tool handles SQL
generation with hardcoded security validations.
"""

import uuid
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from domain.agents.base.base_agent import BaseAgent
from domain.agents.i18n.pt_br import INTERACTION_ERROR_RESPONSE
from domain.agents.reports_b2b.report_generator.prompts import agent_system_prompt
from domain.agents.reports_b2b.report_generator.tools import generate_sql_tool
from domain.core.logger import Logger
from domain.infra.genplat.genplat_provider import GenplatProvider


class ReportGeneratorAgent(BaseAgent):
    """ReAct agent that reasons about SQL generation via generate_sql_tool.

    Loads ``schema.md`` at construction time and injects it into the system
    prompt so the LLM always has the full data catalog available when deciding
    whether to call the SQL generation tool.

    The agent handles pre-tool validation, tool invocation, and post-tool
    processing. The actual SQL generation is delegated to generate_sql_tool
    which includes hardcoded security validations.
    """

    def __init__(self, logger: Logger, genplat_provider: GenplatProvider):
        self.logger = logger
        self.genplat_provider = genplat_provider

        # Hardcoded domain descriptions (single source of truth: schema.md)
        dominios_text = (
            "- **colaboradores**: A tabela master de dados de funcionários da plataforma iFood Benefits. "
            "Centraliza informações de identidade e status de emprego.\n"
            "- **recargas**: Recargas de benefícios do iFood Benefits. Uma linha por transação individual de recarga.\n"
            "- **financeiro**: Notas fiscais (NF-e/NFS-e) emitidas para empresas clientes. Ativos a receber "
            "(boletos, PIX e faturas). Estornos de recargas."
        )

        # Load agent system prompt with domains
        system_prompt = agent_system_prompt(dominios=dominios_text)

        super().__init__(
            name="report_generator",
            system_prompt=system_prompt,
            schema=None,  # Free-text SQL generation
            tools=[generate_sql_tool],  # Add tool for ReAct loop
        )

        self._schema_path = (
            Path(__file__).parent.parent.parent.parent.parent.parent
            / "data"
            / "schema.md"
        )
        self._schema_content: str = ""

    def _create_llm(self) -> ChatOpenAI:
        return self.genplat_provider.create_llm(
            model="gpt-4.1",
            temperature=0.2,
            max_tokens=1024,
        )

    def _build_system_prompt(self, state: dict) -> str:
        """Inject schema.md content into the system prompt."""
        if not self._schema_content:
            self._schema_content = self._load_schema()

        return (
            f"{self.system_prompt}\n\n"
            f"## Schema de Dados Disponível\n\n{self._schema_content}"
        )

    async def __call__(self, state: dict) -> Command:
        user_id = state.get("user_id", "unknown")
        user_message = (state.get("message") or "").strip()

        self.logger.log_information(
            "ReportGeneratorAgent processing message",
            user_id=user_id,
            message_length=len(user_message),
        )

        if not user_message:
            return Command(
                goto="__end__",
                update={
                    "response": (
                        "Olá! Qual relatório você precisa? Por exemplo: "
                        "'Quantos colaboradores ativos?' ou "
                        "'Total de recargas em julho'"
                    ),
                    "messages": [
                        AIMessage(
                            content="Olá! Envie sua solicitação de relatório.",
                            id=str(uuid.uuid4()),
                        )
                    ],
                    "agent_used": "report_generator",
                    "current_step": "completed",
                },
            )

        try:
            return await super().__call__(state)
        except Exception as e:
            import traceback

            self.logger.log_error(
                "Error in ReportGeneratorAgent",
                e,
                user_id=state.get("user_id"),
                traceback=traceback.format_exc(),
            )
            return Command(
                goto="__end__",
                update={
                    "response": INTERACTION_ERROR_RESPONSE,
                    "messages": [
                        AIMessage(
                            content=INTERACTION_ERROR_RESPONSE,
                            id=str(uuid.uuid4()),
                        )
                    ],
                    "agent_used": "report_generator",
                    "current_step": "completed",
                    "error_message": str(e),
                    "fallback_used": True,
                },
            )

    def _build_command(self, structured: Any, state: dict) -> Command:
        response_content = (
            structured if isinstance(structured, str) else str(structured)
        )

        self.logger.log_information(
            "ReportGeneratorAgent response generated",
            user_id=state.get("user_id", "unknown"),
        )

        return Command(
            goto="__end__",
            update={
                "response": response_content,
                "messages": [AIMessage(content=response_content, id=str(uuid.uuid4()))],
                "agent_used": "report_generator",
                "current_step": "completed",
                "error_message": None,
                "fallback_used": False,
            },
        )

    def _load_schema(self) -> str:
        """Load the schema.md file content."""
        if not self._schema_path.exists():
            self.logger.log_warning(
                "Schema file not found, continuing without schema",
                path=str(self._schema_path),
            )
            return "Schema não disponível no momento."

        content = self._schema_path.read_text(encoding="utf-8")
        self.logger.log_information(
            "Schema loaded successfully",
            path=str(self._schema_path),
            length=len(content),
        )
        return content
