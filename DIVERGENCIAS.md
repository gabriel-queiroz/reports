# Divergências em aberto: `documentacao_tabelas_databricks.md` × `data/schema.md`

**Análise de:** 2026-08-13 — diff coluna a coluna (nome, tipo, enum), por tabela.
**Fora de escopo por decisão:** `chargeback` e `chargeback_employee`.

Arquivo temporário: **some quando tudo aqui estiver resolvido.** O que já foi decidido saiu
daqui — está aplicado no `schema.md` e registrado nos commits.

---

## 1. ⏸ Caminho da `companies` — mudança acoplada a código

| | |
|---|---|
| `schema.md`, prompts e código | `fintech_companies.companies` |
| Databricks | `main.fintech_companies.companies` |

As outras seis tabelas usam `main.` corretamente; só a `companies` não.

**Testado:** trocar o catálogo para o caminho completo faz o `validate_mandatory_joins`
**rejeitar toda query de colaboradores** — os padrões casam `JOIN FINTECH_COMPANIES.COMPANIES`
e não reconhecem o `main.` no meio. Schema e código têm que mudar no mesmo deploy (ver seção 4).

Se o warehouse resolve o catálogo padrão como `main`, hoje funciona por acidente feliz.

---

## 2. Enums documentados no Databricks e ausentes do schema

Valores válidos para filtro. Sem eles, o modelo inventa o valor do `WHERE` — e enum errado
devolve relatório vazio sem erro nenhum.

| Tabela | Coluna | Valores | Já no schema? |
|---|---|---|---|
| `companies` | `card_delivery_type` | `PAP` (individual), `LOTE` (em lote) | parcial |
| `companies` | `origin` | `SALESFORCE`, `SELFSALES` (entre outros) | ✅ |
| `recharges` | `voucher_group` | `PAT`, `LIVRE` | ✅ |
| `recharges` | `order_status` | `DISTRIBUTION_COMPLETE` (legado `DISTRIBUTED` mapeado) | não |
| `recharges` | `product_key` | `FOOD_VOUCHER`, `MEAL_VOUCHER` (entre outros) | parcial |
| `receivable_assets` | `status` | `PENDING`, `RECEIVED`, `CANCELED`, `EXPIRED` | ✅ |
| `receivable_assets` | `type` | `INVOICED_BOLETO`, `BOLETO`, `PIX`, `STARK_PAY` | ✅ |
| `receivable_assets` | `product_type` | `MEAL_VOUCHER`, `MOBILITY_VOUCHER`, `EDUCATION_VOUCHER`, `CULTURE_VOUCHER` (entre outros) | parcial |
| `company_tax_invoice` | `tax_invoice_status` | `AVAILABLE`, `PENDING` | parcial |
| `company_tax_invoice` | `product_type` | `REWARD_VOUCHER`, `MEAL_VOUCHER`, `MOBILITY_VOUCHER`, `CARD_ISSUE` | não |
| `financial_account` | `origin` | `COMPANY` | não |
| `financial_account` | `type` | `MAIN` | não |
| `financial_account` | `product_type` | `MEAL_VOUCHER`, `MOBILITY_VOUCHER`, `CULTURE_VOUCHER` | não |
| `financial_transaction` | `type` | `CREDIT`, `DEBIT` | não |
| `financial_transaction` | `rubric` | `DISTRIBUTION`, `BILLING_PAID`, `DISTRIBUTION_WALLET` | não |
| `financial_transaction` | `amount_currency` | `BRL` | não |

---

## 3. Subcampos de struct documentados pela metade

### `ifood_benefits_recharges.order_info`
O schema documenta 5 subcampos, com **aliases e tipos propostos por mim, não confirmados**.
O Databricks lista 19: `order_id`, `created_at`, `created_by`, `updated_by`, `order_status`,
`company_group_id`, `distributed`, `distribute_on`, `payment_method`, `type`, `scheduled`,
`authorization_id`, `balance_usage`, `custom_description`, `pre_eligible`, `source_system`,
`bko_action`, `deleted`, `test`.

Dois pontos que mudam decisão:
- **`order_info.company_group_id` existe** — é um segundo caminho de filtro multi-tenant nessa
  tabela, além de `company_group.id`. Definir qual é o canônico.
- **`order_info.deleted` e `order_info.test` existem.** A tabela não tem `deleted` no topo (isso
  segue verdade), mas tem dentro do struct. Se o filtro de soft delete for necessário, o caminho
  é `order_info.deleted = false`.

### `ifood_benefits_recharges.order_item_info`
O schema marca como "subcampos não documentados". O Databricks lista 8: `created_at`,
`updated_at`, `transaction_id`, `correlation_id`, `employee_id`, `person_id`, `deleted`, `test`.

### `companies.commercial_address`
`street`, `number`, `complement`, `postal_code`, `district`, `city`, `state`, `country`,
`postal_code_validation_error`, `geo_loc_info` (`latitude`, `longitude`, `centroid_id`,
`microcentroid_id`). Nenhum documentado no schema — hoje o struct está lá como linha única.

---

## 4. Correções de código

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
| `sql_validator.py:287-300`, `:341`, `:170`, `schema_extractor.py:70-74` | **Caminho da `companies`** (seção 1): aceitar o prefixo `main.` em `companies_patterns`, no regex de `_extract_companies_table_alias`, em `TABLE_RELATIONSHIPS["company_filter_table"]` e no append hardcoded do `schema_extractor` |

---

## 5. Pendências que só o Databricks responde

| # | Pendência | Impacto se ficar aberto |
|---|-----------|-------------------------|
| 1 | `ifood_benefits_recharges`: qual o tipo/formato de `update_date`, e ela ou `update_month` é a coluna de partição? | Partição errada = full scan numa tabela de ~93M linhas |
| 2 | `ifood_benefits_recharges`: tipos reais dos subcampos de `order_info` e `order_item_info` | Aliases e tipos de `order_info.*` foram propostos, não confirmados |
| 3 | `chargeback_employee`: caminho completo, colunas reais, tipos e estratégia multi-tenant | Tabela documentada por inferência — **não liberar para o agente** até confirmar |
| 4 | `chargeback_employee`: `employee_name` e `tax_id` são dados em claro? | Muda o tratamento de LGPD do CSV entregue |
| 5 | `financial_transaction` tem coluna de partição? | O dump não declara nenhuma; o catálogo antigo citava `dt`/`dt_partition`, que não constam |
| 6 | `employee` tem coluna de partição? | O dump não declara nenhuma |
