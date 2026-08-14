"""BaseAgent local — substitui `domain.agents.base.base_agent`.

⚠️ **Não é a implementação real.** O BaseAgent do projeto principal contém o loop ReAct
(chamada ao LLM, despacho de tools, montagem do Command). Aqui só existe o suficiente para
os módulos do agente **importarem** e para o harness exercitar a geração de SQL, que não
passa pelo loop.

Se um dia o harness for testar o ReAct de ponta a ponta, esta classe precisa ser trocada
pela real — e é por isso que `__call__` falha explicitamente em vez de fingir que funciona.
"""

from typing import Any


class BaseAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        schema: Any = None,
        tools: list[Any] | None = None,
        state_schema: Any = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.schema = schema
        self.tools = tools or []
        self.state_schema = state_schema

    def _create_llm(self) -> Any:
        raise NotImplementedError

    def _build_system_prompt(self, state: dict) -> str:
        return self.system_prompt

    def _build_command(self, structured: Any, state: dict) -> Any:
        raise NotImplementedError

    async def __call__(self, state: dict) -> Any:
        raise NotImplementedError(
            "O loop ReAct vive no BaseAgent do projeto principal. Este stand-in só "
            "permite importar o agente e testar a geração de SQL — use o harness com "
            "`_generate_sql_internal`."
        )
