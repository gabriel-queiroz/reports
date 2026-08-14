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
| `domain/agents/base/base_agent.py` | `domain.agents.base.base_agent` | ⚠️ Só o suficiente para importar. **Não** tem o loop ReAct |
| `domain/agents/graph/agent_state.py` | `domain.agents.graph.agent_state` | Campos usados pelo agente |
| `domain/agents/i18n/pt_br.py` | `domain.agents.i18n.pt_br` | Mensagem de erro |
| `harness.py` | — | CLI que exercita o fluxo real de geração de SQL |

A ponte merece nota: em vez de copiar os arquivos do agente para dentro de um pacote
`domain/`, o `__init__.py` aponta o `__path__` para a raiz. Assim existe **uma** cópia do
código, e o import absoluto do agente continua resolvendo.

## Instalação

```bash
uv venv .venv
uv pip install --python .venv/bin/python pydantic langchain-core langchain-openai langgraph
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
query foi **aceita** pelos validadores. É o bug do `_inject_filter_in_query_with_where`
descrito na fase 2 do `PLANO.md`, agora reproduzível com um comando.

Também dá para reproduzir o buraco do domínio `recargas`, onde uma query sem nenhum filtro de
grupo passa por todas as validações:

```bash
.venv/bin/python _local/harness.py "recargas de julho" --dominio recargas \
  --sql "SELECT r.order_id AS id_pedido, r.company_group.id AS company_group_id \
         FROM main.fintech_finance.ifood_benefits_recharges r \
         WHERE r.update_month >= '2026-07' LIMIT 1000"
```

## Limite conhecido

O `BaseAgent` daqui **não** implementa o loop ReAct — só permite importar o agente. Testar o
grafo de ponta a ponta (tools, confirmação com o usuário, `execute_query` chamando o Reports
Service) exige o `BaseAgent` real ou uma reimplementação fiel. O harness ataca a geração de
SQL, que é onde estão as fases 2 a 4 do plano.
