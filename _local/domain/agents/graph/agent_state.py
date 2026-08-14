"""AgentState local — substitui `domain.agents.graph.agent_state`.

Só os campos que o agente de relatórios lê ou escreve.
"""

from typing import Annotated, Any, TypedDict

try:
    from langgraph.graph.message import add_messages
except ImportError:  # pragma: no cover
    add_messages = None  # type: ignore[assignment]


class AgentState(TypedDict, total=False):
    message: str
    user_id: str
    session_id: str
    metadata: dict[str, Any]
    response: str
    messages: Annotated[list, add_messages] if add_messages else list
    agent_used: str
    current_step: str
    error_message: str | None
    fallback_used: bool
