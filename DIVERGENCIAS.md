# Divergências em aberto: `documentacao_tabelas_databricks.md` × `data/schema.md`

**Análise de:** 2026-08-13 — diff coluna a coluna (nome, tipo, enum), por tabela.
**Fora de escopo por decisão:** `chargeback` e `chargeback_employee`.

Arquivo temporário: **some quando tudo aqui estiver resolvido.** O que já foi decidido saiu
daqui — está aplicado no `schema.md` e registrado nos commits.

---

## 1. Correções de código

Não dependem de confirmação de ninguém — são consequência do que já foi decidido.

| Onde | O quê |
|------|-------|
| `sql_validator.py:361-370` | `_has_valid_group_id_filter` deve aceitar `group_id` puro também para `chargeback` e `company_tax_invoice` (hoje só para `financial_account`/`financial_transaction`), senão rejeita filtro correto |
| `sql_validator.py:159-160` | `TABLE_RELATIONSHIPS["financeiro"]`: mover `chargeback` e `company_tax_invoice` de `tables` para `tables_with_direct_group_id` |
| `sql_validator.py:375-391` | `_financeiro_group_filter_clause` deve emitir `group_id = '<uuid>'` para as duas, em vez do filtro via alias de `companies` |
| `schema_extractor.py:12` | `chargeback` está mapeada para `recargas`; o domínio dela precisa ser decidido (hoje diverge do `TABLE_RELATIONSHIPS`) |
| `schema_extractor.py:10,17` | Remover `mv_employee_config` e `anticipation` do `TABLE_TO_DOMAIN` — confirmado que não existem |
| `sql_validator.py:139` | Remover `mv_employee_config` de `TABLE_RELATIONSHIPS["colaboradores"]["tables"]` pelo mesmo motivo |
| `sql_validator.py:563-579` e `tools/list_fields.py:19-27` | Quando `chargeback_employee` for confirmada, incluir `"## 8. Chargeback Employee"` nos mapas de domínio — sem isso os aliases dela não são validados |

---

## 2. Pendências que só o Databricks responde

| # | Pendência | Impacto se ficar aberto |
|---|-----------|-------------------------|
| 1 | `ifood_benefits_recharges`: qual o tipo/formato de `update_date`, e ela ou `update_month` é a coluna de partição? | Partição errada = full scan numa tabela de ~93M linhas |
| 2 | `ifood_benefits_recharges`: tipos reais dos subcampos de `order_info` e `order_item_info` | Aliases e tipos de `order_info.*` foram propostos, não confirmados |
| 3 | `chargeback_employee`: caminho completo, colunas reais, tipos e estratégia multi-tenant | Tabela documentada por inferência — **não liberar para o agente** até confirmar |
| 4 | `chargeback_employee`: `employee_name` e `tax_id` são dados em claro? | Muda o tratamento de LGPD do CSV entregue |
| 5 | `financial_transaction` tem coluna de partição? | O dump não declara nenhuma; o catálogo antigo citava `dt`/`dt_partition`, que não constam |
| 6 | `employee` tem coluna de partição? | O dump não declara nenhuma |
