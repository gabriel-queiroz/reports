"""BaseAgent local — implementa o loop ReAct que no projeto principal vive em
`domain.agents.base.base_agent`.

Não é o código da empresa: é uma reimplementação com o mesmo contrato, para o agente
rodar aqui sem alteração. O contrato que os agentes deste repositório esperam é:

- `__init__(name, system_prompt, schema=None, tools=None, state_schema=None)`
- `_create_llm()` — a subclasse devolve o LLM
- `_build_system_prompt(state)` — a subclasse monta o system prompt (pode injetar schema)
- `_build_command(structured, state)` — a subclasse converte a resposta final em `Command`
- `await agente(state)` — roda o loop e devolve `Command`

O loop: monta as mensagens, faz bind das tools, chama o LLM; enquanto vier `tool_calls`,
executa as tools e devolve o resultado como `ToolMessage`; quando vier texto puro, entrega
para `_build_command`.
"""

import inspect
import json
from typing import Any

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

MAX_ITERACOES = 8


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

    # ------------------------------------------------------------------ hooks
    def _create_llm(self) -> Any:
        raise NotImplementedError("a subclasse deve implementar _create_llm")

    def _build_system_prompt(self, state: dict) -> str:
        return self.system_prompt

    def _build_command(self, structured: Any, state: dict) -> Any:
        raise NotImplementedError("a subclasse deve implementar _build_command")

    # ------------------------------------------------------------------ loop
    async def __call__(self, state: dict) -> Any:
        llm = self._create_llm()
        if self.tools:
            llm = llm.bind_tools(self.tools)
        elif self.schema is not None:
            llm = llm.with_structured_output(self.schema)

        mensagens: list[Any] = [SystemMessage(content=self._build_system_prompt(state))]
        mensagens.extend(state.get("messages") or [])
        if state.get("message"):
            mensagens.append(HumanMessage(content=state["message"]))

        por_nome = {t.name: t for t in self.tools}

        for _ in range(MAX_ITERACOES):
            resposta = await self._invocar(llm, mensagens)
            mensagens.append(resposta)

            chamadas = getattr(resposta, "tool_calls", None) or []
            if not chamadas:
                conteudo = getattr(resposta, "content", resposta)
                return self._build_command(conteudo, state)

            for chamada in chamadas:
                resultado = await self._executar_tool(por_nome, chamada, state)
                mensagens.append(
                    ToolMessage(
                        content=resultado,
                        tool_call_id=chamada.get("id", chamada["name"]),
                    )
                )

        return self._build_command(
            "Não consegui concluir sua solicitação agora. Pode reformular?", state
        )

    # ------------------------------------------------------------------ apoio
    @staticmethod
    async def _invocar(llm: Any, mensagens: list[Any]) -> Any:
        if hasattr(llm, "ainvoke"):
            return await llm.ainvoke(mensagens)
        return llm.invoke(mensagens)

    @staticmethod
    async def _executar_tool(por_nome: dict, chamada: dict, state: dict) -> str:
        tool = por_nome.get(chamada["name"])
        if tool is None:
            return json.dumps(
                {"status": "error", "message": f"tool desconhecida: {chamada['name']}"},
                ensure_ascii=False,
            )

        args = dict(chamada.get("args") or {})

        # tools que declaram InjectedState recebem o state — no projeto principal
        # quem faz isso é o ToolNode do langgraph
        funcao = getattr(tool, "coroutine", None) or getattr(tool, "func", None)
        if funcao is not None and "state" in inspect.signature(funcao).parameters:
            args["state"] = state

        try:
            if hasattr(tool, "ainvoke"):
                resultado = await tool.ainvoke(args)
            else:
                resultado = tool.invoke(args)
        except Exception as erro:  # noqa: BLE001 — o loop não pode morrer por causa de tool
            return json.dumps(
                {"status": "error", "message": f"{type(erro).__name__}: {erro}"},
                ensure_ascii=False,
            )

        return resultado if isinstance(resultado, str) else str(resultado)


__all__ = ["BaseAgent", "AIMessage"]
