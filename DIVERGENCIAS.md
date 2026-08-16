# Divergências em aberto: dump do Databricks × `data/schema.md`

**Análise de:** 2026-08-13 — diff coluna a coluna (nome, tipo, enum), por tabela.

O dump que serviu de base (`documentacao_tabelas_databricks.md`) foi removido do repositório.
Para reconferir qualquer afirmação abaixo sobre "o dump", recupere-o do git:
`git show 4ba6b86:documentacao_tabelas_databricks.md`.
**Fora de escopo por decisão:** `chargeback` e `chargeback_employee`.

Arquivo temporário: **some quando tudo aqui estiver resolvido.** O que já foi decidido saiu
daqui — está aplicado no `schema.md` e registrado nos commits.

---

## 1. Correções de código

✅ **Resolvidas** — e o mecanismo que as gerava foi embora junto. As regras de multi-tenant,
as colunas e as chaves de JOIN não são mais listas paralelas em Python: o `catalog.py` lê tudo
do `schema.md`, então corrigir o catálogo já corrige o código. O `sql_validator.py`, onde
essas listas viviam (`TABLE_RELATIONSHIPS`, `_has_valid_group_id_filter`,
`_financeiro_group_filter_clause`), não existe mais.

Continua valendo uma pendência, agora com outro endereço:

| Onde | O quê |
|------|-------|
| `data/schema.md` (seção 8) e `schema_extractor.py` (`TABLE_TO_DOMAIN`) | Quando `chargeback_employee` for confirmada, escrever a linha `**Multi-tenant**` dela de forma reconhecível e mapear a tabela para um domínio. Enquanto isso não acontecer, o guard a mantém **fora** da allowlist — que é o comportamento desejado |

---

## 2. Pendências que só o Databricks responde

| # | Pendência | Impacto se ficar aberto |
|---|-----------|-------------------------|
| 1 | `ifood_benefits_recharges`: `update_month` é de fato a coluna de partição? (`update_date` saiu do catálogo — o agente não a usa mais) | Se a partição real for outra coluna, o filtro por `update_month` vira full scan numa tabela de ~93M linhas |
| 2 | `ifood_benefits_recharges`: tipos reais dos subcampos de `order_info` e `order_item_info` | Aliases e tipos de `order_info.*` foram propostos, não confirmados |
| 3 | `chargeback_employee`: caminho completo, colunas reais, tipos e estratégia multi-tenant | Tabela documentada por inferência — **não liberar para o agente** até confirmar |
| 4 | `chargeback_employee`: `employee_name` e `tax_id` são dados em claro? | Muda o tratamento de LGPD do CSV entregue |
| 5 | `financial_transaction` tem coluna de partição? | O dump não declara nenhuma; o catálogo antigo citava `dt`/`dt_partition`, que não constam |
| 6 | `employee` tem coluna de partição? | O dump não declara nenhuma |
