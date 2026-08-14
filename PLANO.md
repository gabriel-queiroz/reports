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

## Fase 2 — Guard de AST (sqlglot)

Substitui a validação por string. Resolve de uma vez os bugs estruturais que a análise
inicial levantou e que continuam de pé.

- [ ] Parse com dialeto `databricks`; exigir **um** statement e que seja `SELECT`/`WITH`.
- [ ] Allowlist de tabelas a partir do catálogo (não hardcoded).
- [ ] Injetar o predicado de tenant no `WHERE` do escopo externo via AST — o sqlglot
      parentiza corretamente, matando o bug de precedência (`WHERE a OR b AND filtro`).
- [ ] Verificar a presença do filtro **no AST**, não por regex: hoje o `_has_valid_group_id_filter`
      aceita o UUID em qualquer lugar do texto, inclusive dentro de um ramo de `OR`.
- [ ] Enviar ao Reports Service o SQL **regerado a partir da AST**, não a string do LLM.

**Bugs que isto elimina** (todos reproduzidos em `sql_validator.py`):
- `_inject_filter_in_query_with_where` procura `LIMIT` primeiro e injeta o `AND` **depois** do
  `ORDER BY`/`GROUP BY` → SQL inválido. Como o prompt obriga `LIMIT`, é o caminho comum.
- Injeção dentro de subquery quando o único `WHERE` está lá — query externa fica sem filtro.
- Predicado caindo dentro do `ON` de um `LEFT JOIN`, onde não filtra nada.
- `_extract_companies_table_alias` retorna `"ON"` quando o JOIN não tem alias.
- Nenhuma barreira contra `;`, DML/DDL ou comentário smuggling.

**Validação:** transformar os casos acima em testes de regressão.

---

## Fase 3 — Validação de coluna contra o catálogo

- [ ] Com a AST, checar por tabela: a coluna existe? é da tabela certa (resolução por alias)?
      é alias PT-BR usado como coluna física? a chave de JOIN é a declarada?
- [ ] Erro deve nomear a coluna e sugerir a real ("`id_estorno` não existe em `chargeback`;
      você quis dizer `id`, cujo alias é `id_estorno`").
- [ ] Aposentar o `validate_alias_misuse`. Ele reprova query correta (`c.cnpj`,
      `c.company_group_id` em `GROUP BY` — inclusive o exemplo do próprio prompt) e deixa
      passar o erro real quando o SQL vem multi-linha.
- [ ] Remover `validate_fields` e `extract_fields_from_documentation` (código morto que
      validava a *pergunta*, não o SQL).

---

## Fase 4 — Fazer o retry funcionar

- [ ] Realimentar o erro do validador como mensagem para o LLM. Hoje o `continue` do
      `generate_query_tool.py` reinvoca **o prompt idêntico** — o retry é decorativo.
- [ ] `temperature=0` (hoje 0.2).
- [ ] Subir `max_tokens` (hoje 1024): relatório com muitos campos trunca o structured output,
      e o erro chega ao usuário parecendo alucinação.
- [ ] Uniformizar: `validate_mandatory_joins` levanta sem retry, as outras duas tentam duas vezes.

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
