# Plano de trabalho — agente de relatórios B2B

Ordem de execução para o que falta. Cada fase é independente o suficiente para virar um PR.
As fases 1 a 5 não dependem de ninguém de fora; as 6 a 8 dependem do time de dados ou do
Reports Service.

**Princípio que guiou tudo até aqui:** o `data/schema.md` é a fonte da verdade única. Prompt e
código **leem** o catálogo, não mantêm cópia própria. Toda vez que essa regra foi violada,
apareceu divergência.

---

## ✅ Já feito

| | O quê |
|---|---|
| ✅ | Repositório git com histórico por decisão; cache e lixo removidos |
| ✅ | `schema.md` como fonte da verdade: domínio, multi-tenant, partição, filtros padrão e relacionamentos por tabela |
| ✅ | Double check do catálogo contra o dump do Databricks; 13 divergências resolvidas |
| ✅ | Prompt parou de duplicar a estrutura das tabelas (−239 linhas no `sql_system.md`) |
| ✅ | Prompt parou de ensinar campo inexistente (5 colunas de employee, `chargeback_employee`, structs não confirmados, `EXPIRED`, `c.test`, `r.deleted`) |
| ✅ | Aliases únicos entre tabelas (51 renomeados); enums viraram coluna própria |
| ✅ | Structs documentados por inteiro (`order_info`, `order_item_info`, `commercial_address`) |
| ✅ | Validador alinhado ao catálogo: filtro direto por `group_id` em chargeback e notas fiscais |
| ✅ | `<pergunta>` marcada como dado, não instrução |

Resultado: prompt renderizado saiu de ~48,9k para ~44k caracteres, com muito mais conteúdo
correto dentro.

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

## Fase 5 — Bugs pontuais e limpeza

- [ ] **Race condition de tenant:** `self.group_id`/`self.user_id` são atributos de instância
      (`reports_react_agent/agent.py`), e a instância é única no grafo compilado. Com duas
      sessões concorrentes, o prompt de um usuário pode receber o UUID de outro. Passar pelo
      `state`.
- [ ] **Descasamento prompt × tool:** `agente.md` manda chamar
      `execute_query(pergunta=, dominio=, campos_desejados=, group_id=, user_id=)`; o schema é
      `question`, `domain`, `desired_fields`, sem os dois últimos.
- [ ] **`invoke` síncrono dentro de tool async** — bloqueia o event loop durante toda a chamada
      do LLM. Usar `ainvoke`.
- [ ] **`LIMIT 1000` fixo** truncando CSV sem avisar o usuário.
- [ ] **`list_fields`** devolve o `schema.md` inteiro a cada chamada; `DOMAIN_MARKERS["financeiro"]`
      não cita conta nem transação financeira.
- [ ] **Código morto:** `report_generator_agent.py` (fora do grafo e com path de schema quebrado),
      `generate_sql_tool`, `InvalidFieldsError`.

---

## Fase 6 — Medir (golden set)

- [ ] Conjunto de perguntas reais → SQL esperado, rodando os validadores em CI.

Enquanto não houver `EXPLAIN` nem status de report voltando, **esta é a única forma de saber se
uma mudança de prompt melhorou ou piorou a alucinação.** Sem ela, as fases 3 e 4 são feitas no
escuro.

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
