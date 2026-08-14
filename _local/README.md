# `_local/` — andaime de teste

**Nada aqui vai para o projeto principal.** Quando o agente voltar para lá, esta pasta fica
para trás: o `domain` real já existe no projeto, com o Logger, o IoC e o GenPlat de verdade.

O código do agente (raiz do repositório) **não foi alterado** para isso funcionar. Ele segue
importando `domain.agents.reports_b2b.…`, `domain.core.ioc` e
`domain.infra.genplat.genplat_provider` exatamente como em produção.

## O que tem aqui

| Arquivo | Substitui | Observação |
|---|---|---|
| `domain/core/logger.py` | `domain.core.logger` | Imprime no stdout; mesma interface |
| `domain/core/ioc.py` | `domain.core.ioc` | `get_logger()` |
| `domain/core/config.py` | `domain.core.config` | `settings` para o `reports_service` |
| `domain/infra/genplat/genplat_provider.py` | `domain.infra.genplat.genplat_provider` | Fala com a **API da OpenAI** no lugar do gateway interno |
| `domain/agents/reports_b2b/__init__.py` | — | Ponte: aponta `__path__` para a raiz do repo |
| `domain/agents/base/base_agent.py` | `domain.agents.base.base_agent` | Loop ReAct reimplementado com o mesmo contrato |
| `domain/agents/graph/agent_state.py` | `domain.agents.graph.agent_state` | Campos usados pelo agente |
| `domain/agents/i18n/pt_br.py` | `domain.agents.i18n.pt_br` | Mensagem de erro |
| `harness.py` | — | CLI que exercita o fluxo real de geração de SQL |
| `api.py` | — | API; sobe o subgrafo real e finge ser o Reports Service |
| `web/` | — | Front em Next.js que consome a API |

A ponte merece nota: em vez de copiar os arquivos do agente para dentro de um pacote
`domain/`, o `__init__.py` aponta o `__path__` para a raiz. Assim existe **uma** cópia do
código, e o import absoluto do agente continua resolvendo.

## Instalação

```bash
uv venv .venv
uv pip install --python .venv/bin/python pydantic langchain-core langchain-openai langgraph
uv pip install --python .venv/bin/python pytest sqlglot
```

`sqlglot` é dependência do agente (guard de AST); `pytest` é só de desenvolvimento.

## Testes

Ficam em `tests/`, **fora desta pasta**, de propósito: eles testam o agente e vão junto
com ele para o projeto principal. Importam pelo caminho de produção
(`domain.agents.reports_b2b.…`); o único ponto de contato com este andaime é o
`tests/conftest.py`, que só cai em `_local/` quando o `domain` real não existe.

```bash
.venv/bin/python -m pytest tests/ -q
```

## Uso

```bash
# modo fake (sem chave): SQL roteirizado, exercita prompt + validadores offline
.venv/bin/python _local/harness.py "colaboradores ativos por empresa" --dominio colaboradores

# alimentando um SQL específico nos validadores — é assim que se escreve caso de teste
.venv/bin/python _local/harness.py "estornos de julho" --dominio financeiro \
  --sql "SELECT ch.id AS id_estorno, ch.group_id AS company_group_id FROM ..."

# com LLM de verdade
OPENAI_API_KEY=sk-... .venv/bin/python _local/harness.py "..." --dominio recargas

# ver o prompt inteiro que vai para o modelo
.venv/bin/python _local/harness.py "..." --mostrar-prompt
```

Sem `OPENAI_API_KEY` o provider entra em modo fake automaticamente. Com a chave, o caminho
exercitado é o mesmo de produção (`ChatOpenAI` + `with_structured_output`).

## O que ele já pegou

Na primeira execução, com o SQL padrão do modo fake:

```
... GROUP BY c.company_name, c.company_group_id  AND c.company_group_id = '550e…' LIMIT 1000
```

O filtro multi-tenant foi injetado **depois do `GROUP BY`** — SQL inválido — e mesmo assim a
query foi **aceita** pelos validadores. Era o bug do `_inject_filter_in_query_with_where`.
O mesmo comando hoje devolve o filtro no `WHERE`, antes do `GROUP BY` (fase 2, guard de AST).

O outro buraco reproduzível era o domínio `recargas`, onde uma query sem filtro de grupo
passava por todas as validações. Hoje o guard injeta `r.company_group.id`:

```bash
.venv/bin/python _local/harness.py "recargas de julho" --dominio recargas \
  --sql "SELECT r.order_id AS id_pedido, r.company_group.id AS company_group_id \
         FROM main.fintech_finance.ifood_benefits_recharges r \
         WHERE r.update_month >= '2026-07' LIMIT 1000"
```

Os dois casos viraram teste de regressão em `tests/test_sql_guard.py` — é lá que eles ficam
travados, não aqui.

## API — fluxo completo

```bash
uv pip install --python .venv/bin/python fastapi uvicorn httpx
.venv/bin/python _local/api.py        # http://127.0.0.1:8000
```

Sobe o **subgrafo real** (`ReportsB2bSubgraph`) e ainda faz o papel do Reports Service, então
o ciclo fecha sem nada externo: conversa → confirmação → tool → geração de SQL → validadores
→ SQL entregue. O que seria enviado ao Databricks fica em `GET /reports`.

| Rota | O quê |
|---|---|
| `GET /` | console web para conversar com o agente |
| `POST /chat` | `{message, session_id, group_id, user_id}` |
| `GET /sessions/{id}` | histórico da sessão |
| `POST /v1/reports/ai-report` | Reports Service falso — guarda o SQL |
| `GET /reports` | tudo que o agente mandou executar |
| `GET /health` | modo do LLM, sessões, relatórios |

Sem `OPENAI_API_KEY` o LLM é roteirizado: pede confirmação e, ao receber "sim", chama a tool —
o suficiente para exercitar o caminho inteiro. Com a chave, é o `gpt-4.1` de verdade.

### O que a API mostrou

Antes da fase 2, o SQL que **chegava ao Reports Service** carregava o bug do `GROUP BY` —
ou seja, não era detalhe interno do validador, era o que sairia para execução:

```sql
... GROUP BY c.company_name, c.company_group_id  AND c.company_group_id = '550e…' LIMIT 1000
```

Hoje o `GET /reports` mostra o SQL regerado a partir da AST, com o filtro no lugar certo.

O guardrail de tenant funciona nas duas formas: `group_id` vazio devolve
`"groupId validation failed: missing group_id in session metadata"`, e um `group_id` que não
é UUID devolve `"groupId validation failed: group_id não é um UUID válido…"` — os dois com
`fallback_used: true`, sem chamar o LLM.

## Front (Next.js)

```bash
cd _local/web && npm install     # já instalado
npm run dev                      # http://localhost:3000 (ou 3001 se ocupada)
```

Precisa da API rodando em paralelo (`.venv/bin/python _local/api.py`). O `next.config.ts`
faz proxy de `/agent/*` para `http://127.0.0.1:8000`, então não há CORS envolvido — mude com
`AGENT_API_URL` se a API subir em outra porta.

Duas colunas: à esquerda a conversa com o agente, à direita **o SQL que foi entregue ao
Reports Service**, um card por relatório. Em cima dá para trocar `group_id` e `user_id` — é
assim que se testa o isolamento multi-tenant, inclusive mandando vazio para ver o guardrail
barrar.

O painel da direita marca em vermelho três coisas que o console detecta sozinho: filtro
injetado depois de `GROUP BY`/`ORDER BY`, ausência da coluna de saída `company_group_id` e
ausência de filtro de grupo no `WHERE`. É só heurística de tela — a validação de verdade é a
do agente —, mas serve para o problema saltar aos olhos em vez de ficar escondido no SQL.

## Limite conhecido

O `BaseAgent` daqui é uma **reimplementação**, não o código da empresa. O contrato é o mesmo
(`_create_llm`, `_build_system_prompt`, `_build_command`, `await agente(state)`), mas detalhes
do loop real podem divergir — em especial a injeção de `InjectedState`, que aqui é feita por
inspeção da assinatura da tool, e no projeto principal é o `ToolNode` do langgraph que faz.
