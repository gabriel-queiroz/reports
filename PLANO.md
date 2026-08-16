# Plano de trabalho — agente de relatórios B2B

Ordem de execução para o que falta. Cada fase é independente o suficiente para virar um PR.
As fases 1 a 5 não dependem de ninguém de fora — **estão fechadas**; as 6 a 8 dependem do time
de dados ou do Reports Service.

**Princípio que guiou tudo até aqui:** o `data/schema.md` é a fonte da verdade única. Prompt e
código **leem** o catálogo, não mantêm cópia própria. Toda vez que essa regra foi violada,
apareceu divergência.

**Onde a segurança do SQL vive agora:** `guardrails.py` (borda), `catalog.py` (o que o
`schema.md` diz) e `sql_guard.py` (o que a AST tem de cumprir). Os três são código do agente,
sem dependência de infra da empresa, e viajam junto com ele.

## Como levar para o projeto principal

1. Copiar os arquivos do agente (raiz `.py`, `data/`, `report_generator/`, `tools/`,
   `reports_react_agent/`) para `domain/agents/reports_b2b/` — os imports absolutos já são os
   de produção e não mudam.
2. Copiar `tests/` junto. O único ponto de contato com este repositório é o `try/except` do
   `tests/conftest.py`, que vira no-op quando o `domain` real existe.
3. Adicionar **`sqlglot`** às dependências.
4. Deixar `_local/` para trás — é andaime.

---

## ✅ Já feito

| | O quê |
|---|---|
| ✅ | Repositório git com histórico por decisão; cache e lixo removidos |
| ✅ | `schema.md` como fonte da verdade: domínio, multi-tenant, partição, filtros padrão e relacionamentos por tabela |
| ✅ | Double check do catálogo contra o dump do Databricks; 13 divergências resolvidas. O dump saiu do repositório — recuperável em `git show 4ba6b86:documentacao_tabelas_databricks.md` |
| ✅ | Prompt parou de duplicar a estrutura das tabelas (−239 linhas no `sql_system.md`) |
| ✅ | Prompt parou de ensinar campo inexistente (5 colunas de employee, `chargeback_employee`, structs não confirmados, `EXPIRED`, `c.test`, `r.deleted`) |
| ✅ | 51 aliases renomeados para reduzir colisão entre tabelas; enums viraram coluna própria. **Restam 8 aliases repetidos** — inofensivos: a resolução do guard é por alias de tabela no escopo, nunca global (`company_group_id` é repetido de propósito; quatro são de `chargeback_employee`, que está fora da allowlist) |
| ✅ | Structs documentados por inteiro: `order_info` (19/19) e `order_item_info` (8/8) |
| ✅ | Validador alinhado ao catálogo: filtro direto por `group_id` em chargeback e notas fiscais |
| ✅ | `<pergunta>` marcada como dado, não instrução |
| ✅ | Fases 1 a 5 (abaixo): guardrails de borda, guard de AST, validação de coluna, retry com realimentação e a limpeza |

Resultado: o `sql_system` renderizado saiu de ~48,9k para ~42,8k caracteres, com muito mais
conteúdo correto dentro. A validação por string virou AST alimentada pelo catálogo, com 143 testes —
cada bug conhecido virou um caso de regressão.

---

## ✅ Fase 1 — Guardrails de borda

Barato, isolado, fecha o único caminho de SQL injection literal. Tudo em `guardrails.py`
— sem dependência de LLM, langchain ou infra, para viajar junto com o agente.

- [x] Validar `group_id` como UUID (`uuid.UUID(...)`) no `__call__` do agente, **antes** de
      qualquer f-string. O que circula daqui para frente é `str(UUID(...))` — canônico, sem
      como carregar aspas ou comentário. Mesma validação repetida em `execute_query` e em
      `_generate_sql_internal`, que é onde o valor de fato vira f-string.
- [x] Recusar `group_id` ausente em vez do default `"unknown"` (`tools/execute_query.py`),
      que gerava query para um tenant inexistente e passava pela validação do
      `reports_service`.
- [x] Sanitizar a pergunta antes do prompt: limite de tamanho (4000), remoção de caracteres
      de controle e invisíveis (Cc/Cf) e das sequências que fecham `<pergunta>`.

**Validação:** `tests/test_guardrails.py` (unidade) e `tests/test_edge_guardrails.py`
(bordas reais: o LLM não chega a ser chamado com tenant inválido, e o payload de injeção
não fecha a tag no prompt). 52 testes, `.venv/bin/python -m pytest tests/`.

---

## ✅ Fase 2 — Guard de AST (sqlglot)

Substitui a validação por string. Está em `sql_guard.py`, com a allowlist e as regras de
tenant vindo de `catalog.py`, que lê o `schema.md` — nada de tabela hardcoded no código.

- [x] Parse com dialeto `databricks`; exigir **um** statement e que seja `SELECT`/`WITH`/`UNION`.
- [x] Allowlist de tabelas a partir do catálogo. Uma tabela sem caminho multi-tenant
      confirmado (hoje `chargeback_employee`) fica **fora** — falha fechada.
- [x] Injetar o predicado de tenant via AST em **todo escopo** que lê tabela base (não só o
      externo): o `where()` do sqlglot parentiza o que já estava lá, matando o bug de
      precedência (`WHERE a OR b AND filtro`).
- [x] Verificar a presença do filtro na **conjunção de topo** do `WHERE`, no AST. Filtro
      dentro de um ramo de `OR` não conta mais como filtro.
- [x] Enviar ao Reports Service o SQL **regerado a partir da AST** (`comments=False`), não a
      string do LLM.

**Bugs eliminados** (todos viraram teste de regressão em `tests/test_sql_guard.py`):
- `_inject_filter_in_query_with_where` injetava o `AND` **depois** do `ORDER BY`/`GROUP BY`
  → SQL inválido. Era o caminho comum, porque o prompt obriga `LIMIT`.
- Injeção dentro de subquery quando o único `WHERE` estava lá.
- Predicado caindo dentro do `ON` de um `LEFT JOIN`.
- `_extract_companies_table_alias` retornando `"ON"` quando o JOIN não tem alias.
- Domínio `recargas` sem filtro nenhum (a injeção era pulada por inteiro).
- `;`, DML/DDL e comentário smuggling.

`validate_mandatory_joins`, `validate_company_group_id_in_select` e todo o injetor por string
(`validate_group_id_present`, `_inject_filter_in_query_with_where`, `_rewrite_query_with_where`,
`_extract_companies_table_alias`) foram **removidos** — o guard faz tudo isso no AST, e o erro
de JOIN faltando agora nomeia a tabela de apoio que o catálogo manda usar. O `sql_validator`
encolheu de 833 para ~370 linhas.

**Dependência nova:** `sqlglot` (Python puro, sem extensão nativa) — precisa entrar no
`pyproject`/`requirements` do projeto principal junto com o agente.

---

## ✅ Fase 3 — Validação de coluna contra o catálogo

- [x] Com a AST, checar por tabela: a coluna existe? é da tabela certa (resolução por alias)?
      é alias PT-BR usado como coluna física? a chave de JOIN é a declarada (seção
      RELACIONAMENTOS do `schema.md`)?
- [x] Erro nomeia a coluna e sugere a real: "`id_estorno` é o Alias PT-BR de `chargeback.id`,
      não uma coluna. No SELECT use `chargeback.id AS id_estorno`; em WHERE, JOIN e GROUP BY
      use a coluna física `id`." Para campo inventado, a sugestão sai por proximidade.
- [x] `validate_alias_misuse` **aposentado**. Os falsos positivos (`c.cnpj`,
      `c.company_group_id` em `GROUP BY`) viraram teste de que a query passa, e o erro real
      em SQL multi-linha virou teste de que agora é pego.
- [x] `validate_fields` e `extract_fields_from_documentation` removidos.

Alias de saída em `ORDER BY`/`GROUP BY`/`HAVING` continua válido (o Spark resolve) — o que é
recusado é o alias que não foi declarado no `SELECT`. Escopo que lê CTE ou subquery é pulado:
quem valida as colunas de lá é o `SELECT` de dentro.

O `sql_validator` ficou com três coisas (duas exceções e o campo citado no prompt) e some de
vez quando a fase 5 tirar o último `except InvalidFieldsError`.

---

## ✅ Fase 4 — Fazer o retry funcionar

- [x] O erro do guard volta como mensagem para o LLM, junto com a query rejeitada. Vai como
      turno de `user`: o structured output ocupa o turno do assistente.
- [x] `temperature=0` — geração de SQL não se beneficia de variedade, e determinismo é o que
      torna o golden set (fase 6) capaz de medir mudança de prompt.
- [x] `max_tokens` de 1024 → 4096.
- [x] Uniformizado: tudo passa pelo mesmo `SqlGuardError` e pelo mesmo `MAX_SQL_ATTEMPTS`.
      Não existe mais validação que levanta sem retry nem retry que reenvia o prompt idêntico.

---

## ✅ Fase 5 — Bugs pontuais e limpeza

- [x] **Race condition de tenant:** `group_id`/`user_id` saíram dos atributos de instância. O
      UUID canônico segue no `state`, que é por sessão. Reproduzido antes de corrigir: com o
      código antigo, duas sessões concorrentes fazem a sessão A receber o grupo de B.
- [x] **Descasamento prompt × tool:** `agente.md` agora descreve `question`, `domain` e
      `desired_fields` — os três parâmetros que existem —, e um teste compara o texto do prompt
      com o `ExecuteQueryInput`.
- [x] **`invoke` síncrono dentro de tool async:** `_generate_sql_internal` virou `async` e usa
      `ainvoke`.
- [x] ~~**`LIMIT` fixo:** virou `MAX_REPORT_ROWS`, garantido pelo guard.~~ **Revertido** — ver
      "Decisões de produto" abaixo. Não há mais teto de linhas.
- [x] **`list_fields`:** monta a lista do catálogo, por tabela, com a coluna *Exibição*. Saiu de
      ~44k caracteres por chamada para 0,3k–1,5k conforme o domínio. O `DOMAIN_MARKERS`, que esquecia
      conta e transação financeira, deixou de existir — o mapa de domínios é um só.
- [x] **Código morto:** `report_generator_agent.py`, `generate_sql_tool`, `GenerateSQLInput`,
      `InvalidFieldsError` e, com eles, o `sql_validator.py` inteiro. `GROUP_ID_FIELD_MAPPING`
      foi junto: apontava `companies.company_group_id` para todos os domínios, contradizendo o
      catálogo na própria instrução de segurança do prompt.

---

## ✅ Decisões de produto (posteriores às fases 1–5)

Mudanças de recorte, não de arquitetura. Todas no `schema.md` e nos prompts — o mecanismo
(catálogo como fonte da verdade) não mudou.

- [x] **Sem teto de linhas.** `MAX_REPORT_ROWS` e `_enforce_row_limit` removidos; o guard não
      injeta nem reduz `LIMIT`. O que o LLM escrever a pedido do usuário ("as 10 maiores")
      passa intacto. A tool não devolve mais `row_limit`, e o prompt não avisa de teto.
      ⚠️ Sem a fase 7, um relatório de recargas varre ~93M linhas sem que ninguém aqui saiba.
- [x] **Campos de `companies` reduzidos** a CNPJ, Nome Fantasia e Licença (`company_group_name`,
      alias `licenca`). Razão social, endereço comercial e seus 13 subcampos, tipo de entrega,
      sem cartão, origem e datas saíram do catálogo — hoje são `ColumnNotFoundError`.
- [x] **Colunas de encanamento escondidas** via `Exibição` vazia: existem para o guard (JOIN,
      filtro multi-tenant, filtro padrão) e não aparecem no `list_fields`. São
      `companies.company_id`, `companies.company_group_id`, `companies.deleted` e, em
      `employee`, `status`, `deleted`, `test` e `test_mode`.
- [x] **`list_fields` ligada ao fluxo.** O `agente.md` mandava "liste os campos disponíveis" e
      **nunca citava a ferramenta** — o modelo listava de memória e inventava campo
      (`Cargo`, `Matrícula`, `Departamento`). Agora o passo 3 obriga a chamada, e uma regra
      geral proíbe citar nome de campo que não veio dela, inclusive como exemplo.
- [x] **`ifood_benefits_recharges.update_date` removida**; a partição declarada passou a ser
      `update_month` (`YYYY-MM`). Ver pendência 1 do `DIVERGENCIAS.md`.
- [x] **`order_item_info.person_id` adicionada** — o struct passou a bater 8/8 com o físico.

Pendente e **não registrado em nenhum outro lugar**: `order_info.distributed` está como
`TIMESTAMP` no catálogo e `string` no dump físico, e é oferecido como "filtro temporal fino".
Se o formato não for ISO ordenável, a comparação de data devolve resultado errado em silêncio.

---

## Fase 6 — Medir (golden set)

- [ ] Conjunto de perguntas reais → SQL esperado, rodando os validadores em CI.
- [ ] Caso mais barato e que já pegou bug real: **pergunta → lista de campos apresentada** deve
      ser subconjunto do que a `list_fields` devolve. Foi assim que apareceu o agente
      oferecendo `Cargo` e `Matrícula`, que não existem no catálogo — alucinação de
      apresentação, que nenhum validador de SQL enxerga.

Enquanto não houver `EXPLAIN` nem status de report voltando, **esta é a única forma de saber se
uma mudança de prompt melhorou ou piorou a alucinação.**

Metade da infraestrutura já está de pé: `tests/` roda em CI, o `temperature=0` torna a geração
repetível e o `ProviderEspiao` do `conftest.py` fixa a resposta do LLM por tentativa. O que
falta é o insumo que só o time tem — as **perguntas reais** e o SQL que se espera delas. Hoje
os testes cobrem o guard (SQL de entrada → veredito); o golden set cobre o degrau de cima
(pergunta → SQL).

---

## Fase 7 — Fechar o loop com o Reports Service

- [ ] Consultar status pelo `report_id` (ou receber callback) e devolver o erro ao agente e aos logs.
- [ ] Preview de ~10 linhas + contagem antes de gerar o CSV.

Hoje o `execute_query` faz o POST, recebe o id e responde `status: "success"` — o agente promete
o CSV e **nunca fica sabendo se a query rodou**. Se o SQL for inválido, ninguém aqui descobre.
É o buraco que faz a alucinação ser invisível em produção.

O preview ataca a alucinação semântica (período/filtro errados), que nenhum validador estático pega.

---

## Fase 8 — EXPLAIN / dry-run

- [ ] Validar tabela, coluna, tipo e sintaxe pelo engine real antes de enfileirar o relatório.

Última porque depende de acesso que ainda não existe. Quando chegar, torna a fase 3 quase
redundante — vira defesa em profundidade em vez de defesa principal.

---

## Em paralelo — não bloqueia nenhuma fase

Pendências que só o Databricks responde, e as correções de código que dependem delas:
ver `DIVERGENCIAS.md`. Esse arquivo é temporário e deve sumir quando esvaziar.
