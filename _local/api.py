"""API de teste do agente de relatórios B2B.

Sobe o **subgrafo real** (`graph.ReportsB2bSubgraph`) com a camada `_local/domain` no
lugar do `domain` do projeto principal, e ainda faz o papel do Reports Service, para o
fluxo fechar de ponta a ponta sem depender de nada externo.

    .venv/bin/python _local/api.py                 # http://127.0.0.1:8000

Endpoints:
    GET  /                     console HTML simples para conversar com o agente
    POST /chat                 {"message", "session_id", "group_id", "user_id"}
    GET  /sessions/{id}        histórico da sessão
    DELETE /sessions/{id}      zera a sessão
    POST /v1/reports/ai-report Reports Service falso — registra o SQL recebido
    GET  /reports              tudo que o agente mandou executar (SQL incluso)
    GET  /health

Sem `OPENAI_API_KEY` o LLM entra em modo roteirizado: o agente pede confirmação e, ao
receber "sim", chama a tool. Com a chave, é o `gpt-4.1` de verdade.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Any

_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ / "_local"))
sys.path.insert(0, str(_RAIZ))

PORTA = int(os.getenv("PORT", "8000"))

# o agente chama o Reports Service por HTTP; apontamos para esta própria API
os.environ.setdefault("REPORTS_SERVICE_API_URL", f"http://127.0.0.1:{PORTA}")
os.environ.setdefault("REQUESTER_TOKEN", "token-de-teste")

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from domain.core.ioc import get_logger  # noqa: E402
from domain.infra.genplat.genplat_provider import GenplatProvider  # noqa: E402

logger = get_logger()
provider = GenplatProvider(logger)

from domain.agents.reports_b2b.graph import ReportsB2bSubgraph  # noqa: E402

grafo = ReportsB2bSubgraph(logger=logger, genplat_provider=provider).build()

app = FastAPI(title="Reports B2B — API de teste")

_sessoes: dict[str, list[Any]] = {}
_relatorios: list[dict[str, Any]] = []

GROUP_ID_EXEMPLO = "550e8400-e29b-41d4-a716-446655440000"


class ChatIn(BaseModel):
    message: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    group_id: str = GROUP_ID_EXEMPLO
    user_id: str = "usuario-de-teste"


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "llm": provider.modo,
        "sessoes": len(_sessoes),
        "relatorios": len(_relatorios),
    }


@app.post("/chat")
async def chat(entrada: ChatIn) -> dict[str, Any]:
    historico = _sessoes.setdefault(entrada.session_id, [])

    estado = {
        "message": entrada.message,
        "user_id": entrada.user_id,
        "session_id": entrada.session_id,
        "metadata": {"group_id": entrada.group_id},
        "messages": list(historico),
    }

    antes = len(_relatorios)
    tamanho_anterior = len(historico)
    resultado = await grafo.ainvoke(estado)

    from langchain_core.messages import AIMessage, HumanMessage

    # `messages` volta acumulado (o reducer add_messages já juntou o histórico
    # enviado com o que o nó produziu) — então só interessa o delta
    todas = resultado.get("messages") or []
    delta = todas[tamanho_anterior:] if len(todas) >= tamanho_anterior else todas

    historico.append(HumanMessage(content=entrada.message))
    if delta:
        historico.extend(delta)
    else:
        historico.append(AIMessage(content=resultado.get("response", "")))

    return {
        "session_id": entrada.session_id,
        "response": resultado.get("response"),
        "agent_used": resultado.get("agent_used"),
        "error_message": resultado.get("error_message"),
        "fallback_used": resultado.get("fallback_used"),
        "relatorios_gerados_nesta_chamada": _relatorios[antes:],
    }


@app.get("/sessions/{session_id}")
async def sessao(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "mensagens": [
            {"tipo": getattr(m, "type", "?"), "conteudo": getattr(m, "content", "")}
            for m in _sessoes.get(session_id, [])
        ],
    }


@app.delete("/sessions/{session_id}")
async def limpar(session_id: str) -> dict[str, str]:
    _sessoes.pop(session_id, None)
    return {"status": "limpa"}


@app.post("/v1/reports/ai-report")
async def reports_service_falso(payload: dict) -> dict[str, str]:
    """Reports Service falso: guarda o SQL em vez de executar no Databricks."""
    report_id = str(uuid.uuid4())
    _relatorios.append(
        {
            "id": report_id,
            "groupId": payload.get("groupId"),
            "userId": payload.get("userId"),
            "query": payload.get("query"),
        }
    )
    logger.log_information(
        "Reports Service falso recebeu query", report_id=report_id
    )
    return {"id": report_id}


@app.get("/reports")
async def relatorios() -> dict[str, Any]:
    return {"total": len(_relatorios), "relatorios": _relatorios}


@app.get("/", response_class=HTMLResponse)
async def console() -> str:
    return f"""<!doctype html><meta charset="utf-8">
<title>Reports B2B — console de teste</title>
<style>
 body{{font:14px/1.5 system-ui,sans-serif;max-width:820px;margin:32px auto;padding:0 16px;
      background:#111;color:#eee}}
 h1{{font-size:18px}} .meta{{color:#888;font-size:12px;margin-bottom:16px}}
 #log{{border:1px solid #333;border-radius:8px;padding:12px;height:52vh;overflow:auto;
      background:#181818;white-space:pre-wrap}}
 .u{{color:#7cc3ff}} .a{{color:#9be89b}} .e{{color:#ff8a8a}} .s{{color:#888;font-size:12px}}
 form{{display:flex;gap:8px;margin-top:12px}}
 input{{flex:1;padding:10px;border-radius:6px;border:1px solid #333;background:#181818;
       color:#eee}}
 button{{padding:10px 16px;border-radius:6px;border:0;background:#2f6fed;color:#fff;
        cursor:pointer}}
 a{{color:#7cc3ff}}
</style>
<h1>Reports B2B — console de teste</h1>
<div class="meta">LLM: <b>{provider.modo}</b> · group_id: {GROUP_ID_EXEMPLO}
 · <a href="/reports">/reports</a> · <a href="/health">/health</a></div>
<div id="log"></div>
<form onsubmit="enviar(event)">
  <input id="msg" placeholder="Ex.: quantos colaboradores ativos por empresa?" autofocus>
  <button>Enviar</button>
</form>
<script>
const sid = crypto.randomUUID(); const log = document.getElementById('log');
function add(cls, txt) {{
  const d = document.createElement('div'); d.className = cls; d.textContent = txt;
  log.appendChild(d); log.scrollTop = log.scrollHeight;
}}
async function enviar(e) {{
  e.preventDefault();
  const i = document.getElementById('msg'); const t = i.value.trim();
  if (!t) return; i.value = ''; add('u', '› ' + t);
  try {{
    const r = await fetch('/chat', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{message: t, session_id: sid}})
    }});
    const j = await r.json();
    add('a', j.response || '(sem resposta)');
    if (j.error_message) add('e', 'erro: ' + j.error_message);
    (j.relatorios_gerados_nesta_chamada || []).forEach(rel =>
      add('s', 'SQL enviado ao Reports Service (' + rel.id.slice(0, 8) + '):\\n' + rel.query));
  }} catch (err) {{ add('e', 'falha: ' + err); }}
}}
add('s', 'Sessão ' + sid.slice(0, 8) + '. Sem OPENAI_API_KEY o LLM responde roteirizado — '
       + 'peça um relatório e responda "sim" para confirmar.');
</script>"""


if __name__ == "__main__":
    import uvicorn

    print(f"\n  LLM em modo: {provider.modo}")
    print(f"  console:     http://127.0.0.1:{PORTA}/\n")
    uvicorn.run(app, host="127.0.0.1", port=PORTA, log_level="warning")
