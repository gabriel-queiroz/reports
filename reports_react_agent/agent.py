"""ReAct agent for reports B2B data consultation."""

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.types import Command

from domain.agents.base.base_agent import BaseAgent
from domain.agents.graph.agent_state import AgentState
from domain.agents.i18n.pt_br import INTERACTION_ERROR_RESPONSE
from domain.agents.reports_b2b.report_generator.prompts import agent_system_prompt
from domain.agents.reports_b2b.tools.execute_query import execute_query
from domain.agents.reports_b2b.tools.list_fields import list_fields
from domain.core.logger import Logger
from domain.infra.genplat.genplat_provider import GenplatProvider


class ReportsB2bReactAgent(BaseAgent):
    """ReAct agent for reports B2B data queries.

    Uses execute_query tool for SQL generation and execution.
    The LLM autonomously decides when to call the tool (ReAct pattern).
    """

    def __init__(
        self,
        logger: Logger,
        genplat_provider: GenplatProvider,
    ):
        self.logger = logger
        self.genplat_provider = genplat_provider
        self.user_id = None  # Will be set during __call__
        self.group_id = None  # Will be set during __call__

        # Hardcoded domain descriptions (single source of truth: schema.md)
        self.dominios_text = (
            "- **colaboradores**: A tabela master de dados de funcionários da plataforma iFood Benefits. "
            "Centraliza informações de identidade e status de emprego.\n"
            "- **recargas**: Recargas de benefícios do iFood Benefits. Uma linha por transação individual de recarga.\n"
            "- **financeiro**: Notas fiscais (NF-e/NFS-e) emitidas para empresas clientes. Ativos a receber "
            "(boletos, PIX e faturas). Estornos de recargas."
        )

        # Build system prompt with domains (group_id will be injected during __call__)
        system_prompt = agent_system_prompt(dominios=self.dominios_text, group_id=None)

        super().__init__(
            name="reports_b2b_react",
            system_prompt=system_prompt,
            tools=[list_fields, execute_query],
            state_schema=AgentState,
        )

    def _create_llm(self):
        return self.genplat_provider.create_llm(
            model="gpt-4.1",
            temperature=0.2,
            max_tokens=1024,
        )

    def _build_system_prompt(self, state: dict) -> str:
        """Build system prompt with group_id injected for multi-tenant security.

        The group_id is set during __call__ and injected into the prompt
        so the LLM knows which group_id to use when calling execute_query.
        """
        # Use the group_id set during __call__, or fall back to placeholder
        group_id = self.group_id or "{group_id_not_set}"
        return agent_system_prompt(
            dominios=self.dominios_text,
            group_id=group_id,
        )

    async def __call__(self, state: dict) -> Command:
        user_id = str(state.get("user_id", "unknown"))
        session_id = str(state.get("session_id", "unknown"))
        self.user_id = user_id  # Store for tool context injection

        self.logger.log_information(
            "🚀 [ReportsB2bReactAgent] Started",
            user_id=user_id,
            session_id=session_id,
        )

        # GUARDRAIL: groupId validation - extract from session metadata
        # (stored at session creation). The metadata dict is passed through
        # from session creation and contains the locked-in group_id
        session_metadata = state.get("metadata", {})
        group_id = session_metadata.get("group_id")

        self.logger.log_information(
            "🔐 [ReportsB2bReactAgent] Validating groupId from session metadata",
            user_id=user_id,
            has_group_id=bool(group_id),
            session_id=session_id,
        )

        if not group_id:
            self.logger.log_warning(
                (
                    "❌ [ReportsB2bReactAgent] groupId validation FAILED - "
                    "missing in session metadata"
                ),
                user_id=user_id,
                session_id=session_id,
            )
            return Command(
                goto="__end__",
                update={
                    "response": "Missing groupId. Cannot process queries.",
                    "messages": [
                        AIMessage(
                            content="Missing groupId. Cannot process queries.",
                            id="reports_b2b_react_groupid_validation",
                        )
                    ],
                    "agent_used": "reports_b2b",
                    "current_step": "completed",
                    "error_message": (
                        "groupId validation failed: "
                        "missing group_id in session metadata"
                    ),
                    "fallback_used": True,
                },
            )

        # Store group_id to be used in _build_system_prompt()
        self.group_id = group_id

        self.logger.log_information(
            "✅ [ReportsB2bReactAgent] Security passed - starting ReAct loop",
            user_id=user_id,
            session_id=session_id,
            group_id=group_id,
        )

        try:
            return await super().__call__(state)
        except Exception as e:
            self.logger.log_error(
                "reports_b2b_react error",
                e,
                user_id=user_id,
                group_id=group_id,
            )
            return Command(
                goto="__end__",
                update={
                    "response": INTERACTION_ERROR_RESPONSE,
                    "messages": [
                        AIMessage(
                            content=INTERACTION_ERROR_RESPONSE,
                            id="reports_b2b_react_error",
                        )
                    ],
                    "agent_used": "reports_b2b",
                    "current_step": "completed",
                    "error_message": str(e),
                    "fallback_used": True,
                },
            )

    def _build_command(self, structured: Any, state: dict) -> Command:
        user_id = str(state.get("user_id", "unknown"))
        self.logger.log_information(
            "reports_b2b_react response generated",
            user_id=user_id,
        )
        return Command(
            goto="__end__",
            update={
                "response": structured,
                "messages": [
                    AIMessage(
                        content=structured,
                        id="reports_b2b_react_response",
                    )
                ],
                "agent_used": "reports_b2b",
                "current_step": "completed",
                "error_message": None,
                "fallback_used": False,
            },
        )
