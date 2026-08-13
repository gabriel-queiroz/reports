# Divergências: `documentacao_tabelas_databricks.md` × `data/schema.md`

**Data:** 2026-08-13
**Método:** parse das duas fontes e diff coluna a coluna (nome, tipo, enum), por tabela.
**Fora de escopo por decisão:** `chargeback` e `chargeback_employee` — ambas ausentes do dump
do Databricks e explicitamente ignoradas nesta análise.

É levantamento para decisão. O andamento das decisões está na seção **9. Status**, no fim
do arquivo — o corpo da análise fica intacto como registro do que o dump mostrou.

---

## Resumo

| Tabela | Colunas no Databricks | Linhas no schema | Faltam no schema | Só no schema |
|---|---|---|---|---|
| `employee` | 30 | 12 | **18** | 0 |
| `receivable_assets` | 25 | 15 | **10** | 0 |
| `ifood_benefits_recharges` | 22 | 26¹ | **7** | 0 |
| `companies` | 15 | 10 | **5** | 0 |
| `company_tax_invoice` | 15 | 12 | **3** | 0 |
| `financial_account` | 9 | 12 | 0 | 3 |
| `financial_transaction` | 16 | 21 | 0 | 5 |

¹ o schema conta subcampos de struct como linhas separadas (`company_group.id` etc.).

---

## 1. ⛔ Contradições com respostas já marcadas como "confirmado"

Estas são as mais graves: já foram aplicadas ao `schema.md` e ao `sql_system.md` como fato
confirmado, e o dump do Databricks diz o contrário. **Precisam ser revertidas ou reconfirmadas.**

### 1.1 `employee` TEM data de admissão e de desligamento

| | |
|---|---|
| Registrado hoje | "**Lacunas conhecidas (confirmado)**: não há data de admissão nem de desligamento" (`schema.md` seção 7) |
| Databricks | `admission_date` (string, ISO) e `discharge_date` (string, ISO) |

Impacto: o `sql_system.md` hoje instrui explicitamente *"Se a pergunta pedir período de
desligamento/admissão, NÃO invente coluna e NÃO use `created_at` como substituto — o dado não
existe neste catálogo"*. Ou seja, o agente está **recusando uma pergunta que ele consegue
responder**. É a inversão exata do problema que estávamos combatendo.

### 1.2 `employee` TEM `person_id`

| | |
|---|---|
| Registrado hoje | "**Colunas que NÃO existem (confirmado)**: `employee_id`, `employee_name`, `person_id`, `hire_date`, `termination_date`" |
| Databricks | `person_id` existe (string, UUID da entidade de pessoa) |

`employee_id` e `employee_name` de fato não existem — essa parte está correta. Só `person_id`
precisa sair da lista de inexistentes. Note que `hire_date`/`termination_date` realmente não
existem: os nomes reais são `admission_date`/`discharge_date` (ver 1.1).

### 1.3 `companies` TEM `test`

| | |
|---|---|
| Registrado hoje | "**Confirmado que `test` NÃO existe** nesta tabela — filtrar `c.test = false` quebraria a query" |
| Databricks | `test` (boolean, "Flag de registro de teste") |

Impacto: o filtro `c.test = false` foi removido do prompt por causa dessa resposta. Ele era
válido — e provavelmente desejável, para não misturar empresa de teste em relatório.

### 1.4 `receivable_assets`: o status é `EXPIRED`, não `OVERDUE`

| | |
|---|---|
| Registrado hoje | "**Enums (confirmado)**: status é `OVERDUE` — `EXPIRED`, citado no prompt antigo, **não existe**" |
| Databricks | `status`: `PENDING, RECEIVED, CANCELED, EXPIRED` |

O prompt antigo estava certo e o catálogo é que estava errado — invertemos na direção errada.
Enum errado aqui gera relatório vazio sem erro nenhum.

### 1.5 Os structs de `receivable_assets` existem

| | |
|---|---|
| Registrado hoje | "os structs `pagar_me`, `zoop`, `metadata` e `amount_detail` seguem não documentados. Foram removidos do prompt até alguém confirmar" |
| Databricks | os quatro existem, com todos os subcampos |

---

## 2. Colunas que existem no Databricks e faltam no schema

### 2.1 `main.ifoodoffice_management.employee` — 18 faltando

| Coluna | Tipo | Enum / observação |
|---|---|---|
| `admission_date` | string | Data de admissão (ISO) — ver 1.1 |
| `discharge_date` | string | Data de desligamento (ISO) — ver 1.1 |
| `person_id` | string | UUID da entidade de pessoa — ver 1.2 |
| `updated_at` | string | Timestamp ISO da última modificação |
| `user_id` | string | UUID do usuário de sistema (autenticação) |
| `registration_number` | string | Número de matrícula do funcionário |
| `job_role_id` | string | UUID do cargo/função |
| `origin_channel` | string | `PLATFORM_B2B`, `DRAFT` |
| `profile_type` | string | `REQUESTER` |
| `meal_policy_id` | string | UUID da política de refeição |
| `standard_cost_center_id` | string | UUID do centro de custo |
| `tag_cost_center` | string | Tag adicional de centro de custo |
| `tag_recharge_filter` | string | Tag para filtragem em recargas |
| `logistic_grouper` | string | Agrupamento logístico |
| `customer_account_id` | string | UUID da conta de cliente (faturamento) |
| `meal_voucher_customer_account_id` | string | Conta de cliente do vale-refeição |
| `food_voucher_customer_account_id` | string | Conta de cliente do vale-alimentação |
| `airbyte_metadata` | struct | Metadados técnicos de ingestão |

Vários destes são candidatos óbvios a relatório B2B: matrícula, cargo, centro de custo,
data de admissão e de desligamento.

### 2.2 `main.fintech_finance.receivable_assets` — 10 faltando

| Coluna | Tipo | Observação |
|---|---|---|
| `asset_month` | string | **Coluna de partição** (YYYY-MM). O schema já a declara no bloco de partição, mas ela não está na lista de colunas |
| `updated_at` | timestamp | |
| `bank_conciliation_date` | string | Data de conciliação bancária (YYYY-MM-DD) |
| `ifood_benefits_profit` | double | Margem de lucro do iFood Benefits no ativo |
| `numero_titulo` | string | Número externo do título — **também existe aqui**, não só em `company_tax_invoice` |
| `aggregation_id` | string | Agrupamento de ativos relacionados |
| `metadata` | struct | `manual_invoice_enabled`, `mv_order_id`, `financial_antecipation_invoice`, `billing_id`, `payerdocument` |
| `pagar_me` | struct | `bank_slip_id`, `company_id`, `boleto_barcode`, `boleto_url`, `transaction_id`, `status` (enum: paid, waiting_payment, refused) |
| `zoop` | struct | idem PagarMe + `zoop_boleto_id`, `numero_titulo`, `reference_number` |
| `amount_detail` | struct | valor por tipo de voucher: meal, mobility, culture, education, home_office, reward, pharmacy, flex_meal, ifood_flex_meal, pharmacy_v2 |

`amount_detail` é o breakdown por benefício — provavelmente o campo mais pedido em relatório
financeiro, e hoje o agente não sabe que ele existe.

### 2.3 `main.fintech_finance.ifood_benefits_recharges` — 7 faltando

| Coluna | Tipo | Observação |
|---|---|---|
| `person_id` | string | UUID da pessoa (topo, além do que está no struct) |
| `voucher_group` | string | `PAT`, `LIVRE` |
| `release_month_11_10` | date | Mês de negócio alternativo (ciclo 11→10) para cálculo financeiro |
| `account_parent` | struct | Conta pai no Salesforce: `account_parent_id`, `nome_da_conta`, `cnpj_account_parent`, `faixa_de_funcionarios`, `tamanho`, `employees_range_group`, `size` |
| `group_billing_authority` | boolean | Grupo tem autoridade de cobrança |
| `has_error` | boolean | Flag rápida de erro |
| `error_info` | struct | `has_order_error`, `order_error_reason`, `has_order_item_error`, `order_item_error_reason` |

### 2.4 `main.fintech_companies.companies` — 5 faltando

| Coluna | Tipo | Observação |
|---|---|---|
| `test` | boolean | Ver 1.3 |
| `created_at` | string | |
| `updated_at` | string | |
| `origin` | string | `SALESFORCE`, `SELFSALES` (entre outros) |
| `delivery_address` | struct | Endereço de entrega, mesma estrutura de `commercial_address` |

### 2.5 `main.ifoodoffice_invoice_service.company_tax_invoice` — 3 faltando

| Coluna | Tipo | Observação |
|---|---|---|
| `type` | string | Classificação do documento fiscal (pode ser nulo) |
| `updated_at` | string | |
| `airbyte_metadata` | struct | Metadados de ingestão |

---

## 3. Colunas que estão só no schema

Não aparecem no dump do Databricks. Podem ser colunas técnicas omitidas do `DESCRIBE`, ou
resíduo de documentação antiga — **precisa confirmar antes de remover**.

| Tabela | Colunas |
|---|---|
| `financial_account` | `_origin_time`, `_processing_time`, `_timeid` |
| `financial_transaction` | `_origin_time`, `_processing_time`, `_timeid`, `dt`, `dt_partition` |

⚠️ Atenção: o schema declara `dt`/`dt_partition` como **partição obrigatória** de
`financial_transaction`. O dump não lista essas colunas nem declara partição nessa tabela.
Se elas não existirem, a regra de partição está mandando filtrar por coluna inexistente.

---

## 4. Divergência de caminho de tabela

| | |
|---|---|
| `schema.md`, prompts e código | `fintech_companies.companies` |
| Databricks | `main.fintech_companies.companies` |

Falta o catálogo `main.` em todas as referências à `companies` — inclusive no
`TABLE_RELATIONSHIPS` (`sql_validator.py`), no `schema_extractor.py` e nos exemplos de JOIN.
As outras seis tabelas usam `main.` corretamente. Confirmar se o ambiente resolve o catálogo
por padrão; se não resolver, todo JOIN com `companies` está quebrado.

---

## 5. Ponto de atenção no multi-tenant

`company_tax_invoice.group_id` tem a descrição: *"UUID do grupo corporativo; **nulo para
empresas sem grupo**"*.

Decidimos usar filtro direto `group_id = '<uuid>'` nessa tabela, dispensando o JOIN com
`companies`. Isso continua correto para isolamento (nulo nunca casa com o UUID), mas significa
que **notas de empresas sem grupo ficam invisíveis** — o que é o comportamento desejado num
relatório por grupo, e só vira problema se existir caso de empresa avulsa que deveria aparecer.
Vale confirmar com o time de negócio.

---

## 6. Enums documentados no Databricks e ausentes do schema

Nenhum destes está no `schema.md` hoje. São valores válidos para filtro — sem eles o agente
inventa o valor do `WHERE`.

| Tabela | Coluna | Valores |
|---|---|---|
| `employee` | `status` | `ACTIVE`, `INACTIVE` (já no schema) |
| `employee` | `origin_channel` | `PLATFORM_B2B`, `DRAFT` |
| `employee` | `profile_type` | `REQUESTER` |
| `employee` | `test_mode` | `loadtest` |
| `companies` | `card_delivery_type` | `PAP` (individual), `LOTE` (em lote) |
| `companies` | `origin` | `SALESFORCE`, `SELFSALES` (entre outros) |
| `recharges` | `voucher_group` | `PAT`, `LIVRE` |
| `recharges` | `order_status` | `DISTRIBUTION_COMPLETE` (legado `DISTRIBUTED` mapeado) |
| `receivable_assets` | `status` | `PENDING`, `RECEIVED`, `CANCELED`, `EXPIRED` |
| `receivable_assets` | `type` | `INVOICED_BOLETO`, `BOLETO`, `PIX`, `STARK_PAY` |
| `receivable_assets` | `product_type` | `MEAL_VOUCHER`, `MOBILITY_VOUCHER`, `EDUCATION_VOUCHER`, `CULTURE_VOUCHER` (entre outros) |
| `company_tax_invoice` | `tax_invoice_status` | `AVAILABLE`, `PENDING` |
| `company_tax_invoice` | `product_type` | `REWARD_VOUCHER`, `MEAL_VOUCHER`, `MOBILITY_VOUCHER`, `CARD_ISSUE` |
| `financial_account` | `origin` | `COMPANY` |
| `financial_account` | `type` | `MAIN` |
| `financial_account` | `product_type` | `MEAL_VOUCHER`, `MOBILITY_VOUCHER`, `CULTURE_VOUCHER` |
| `financial_transaction` | `type` | `CREDIT`, `DEBIT` |
| `financial_transaction` | `rubric` | `DISTRIBUTION`, `BILLING_PAID`, `DISTRIBUTION_WALLET` |
| `financial_transaction` | `amount_currency` | `BRL` |

---

## 7. Subcampos de struct que o schema documenta parcialmente

### `ifood_benefits_recharges.order_info`
O schema documenta 5 subcampos. O Databricks lista **19**:
`order_id`, `created_at`, `created_by`, `updated_by`, `order_status`, `company_group_id`,
`distributed`, `distribute_on`, `payment_method`, `type`, `scheduled`, `authorization_id`,
`balance_usage`, `custom_description`, `pre_eligible`, `source_system`, `bko_action`,
`deleted`, `test`.

Dois pontos importantes:
- **`order_info.company_group_id` existe** — é um segundo caminho de filtro multi-tenant nessa
  tabela, além de `company_group.id`. Decidir qual é o canônico.
- **`order_info.deleted` e `order_info.test` existem.** Confirmamos que a tabela não tem
  `deleted` *no topo*, e isso segue verdade — mas existe dentro do struct. Se o filtro de
  soft delete for necessário, o caminho é `order_info.deleted = false`.

### `ifood_benefits_recharges.order_item_info`
O schema marca como "subcampos não documentados". O Databricks lista 8:
`created_at`, `updated_at`, `transaction_id`, `correlation_id`, `employee_id`, `person_id`,
`deleted`, `test`. Também tem `deleted`/`test` aqui.

### `companies.commercial_address` e `delivery_address`
`street`, `number`, `complement`, `postal_code`, `district`, `city`, `state`, `country`,
`postal_code_validation_error`, `geo_loc_info` (`latitude`, `longitude`, `centroid_id`,
`microcentroid_id`). Nenhum documentado no schema.

---

## 9. Status das decisões

| Item | Decisão | Aplicado |
|---|---|---|
| 1.1 `employee.admission_date` / `discharge_date` | **Fora de escopo.** As colunas existem, mas não devem ser usadas. O agente segue recusando pergunta de período de admissão/desligamento e não usa `created_at` como substituto. A afirmação falsa de que "não existem" foi corrigida no catálogo. | ✅ |
| 1.2 `employee.person_id` | **Remover toda menção.** Não entra no catálogo e saiu da lista de colunas inexistentes. Removida também a linha `person_id` da seção 8 (`chargeback_employee`). | ✅ |
| 1.3 `companies.test` | **Manter como está.** A coluna existe, mas não é documentada nem usada como filtro padrão. A afirmação falsa de que "não existe" foi corrigida. | ✅ |
| 1.4 `receivable_assets.status` | **Documentar os dois.** `EXPIRED` como valor do dump, `OVERDUE` como possível legado. | ✅ |
| 1.5 structs de `receivable_assets` | **Fora de escopo.** `pagar_me`, `zoop`, `metadata` e `amount_detail` existem, mas não entram no catálogo. Seguindo o critério do 1.1, o schema não os menciona — nem para dizer que não devem ser usados. | ✅ |
| 2.1 `employee` (18 faltantes) | **Nenhuma entra.** Catálogo segue com as 12 colunas atuais. | ✅ |
| 2.2 `receivable_assets` (10) | **4 entram:** `asset_month` (partição), `bank_conciliation_date`, `numero_titulo`, `updated_at`. Ficam fora: os 4 structs (decisão 1.5), `aggregation_id` (técnico) e `ifood_benefits_profit` — margem do iFood, dado interno que não deve sair em relatório de cliente. | ✅ |
| 2.3 `ifood_benefits_recharges` (7) | **2 entram:** `voucher_group` (PAT/LIVRE) e `release_month_11_10`. Ficam fora: `person_id` (decisão 1.2), `account_parent`, `group_billing_authority`, `has_error`, `error_info`. | ✅ |
| 2.4 `companies` (5) | **3 entram:** `origin`, `created_at`, `updated_at`. Ficam fora: `test` (decisão 1.3) e `delivery_address`. | ✅ |
| 2.5 `company_tax_invoice` (3) | **2 entram:** `type` e `updated_at`. Fica fora: `airbyte_metadata`. | ✅ |
| 3 colunas só no schema (8) | pendente | |
| 4 caminho da `companies` (`main.`) | pendente | |
| 5 `group_id` nulo em notas fiscais | pendente | |
| 6 enums ausentes (19) | pendente | |
| 7 subcampos de struct | pendente | |
| Armadilha "tipos de data divergentes" | **Virou regra.** Nova regra 5 do `sql_system.md` manda filtrar conforme o Tipo declarado, com o caso do `update_month` (YYYY-MM) e o do `created_at` que muda de tipo entre tabelas. | ✅ |
| Armadilha "aliases repetidos" | **Resolvida no catálogo.** 51 aliases renomeados com sufixo da entidade — nenhum alias se repete entre tabelas. `company_group_id` preservado nas 2 ocorrências por ser o alias de saída obrigatório. | ✅ |
| Armadilha "alias igual à coluna física" | **Não é problema de catálogo.** `company_group_id` tem que ser esse alias por contrato; a correção é no `validate_alias_misuse`, já listada nas correções de código. | ✅ |
| Seção ARMADILHAS | **Removida do schema** (2.361 chars). Não descrevia dado — era nota de processo indo para o prompt a cada chamada. | ✅ |

---

## 8. O que o dump do Databricks não cobre

- `chargeback` e `chargeback_employee` — fora do escopo desta análise por decisão.
- Confirmação de qual coluna é partição em `financial_transaction` (o dump só declara partição
  para `receivable_assets` → `asset_month` e `ifood_benefits_recharges` → `update_date`).
- Se `employee` tem partição (o dump não declara nenhuma).

---

## 10. Herdado do `schema.md`

Estas duas listas viviam dentro do `schema.md` e por isso iam para o prompt a cada
chamada. Descrevem trabalho nosso, não dado — passam a viver aqui, e somem junto com
este arquivo quando forem executadas.

### Pendências ainda abertas (a confirmar no Databricks)

| # | Pendência | Impacto se ficar aberto |
|---|-----------|-------------------------|
| 1 | `ifood_benefits_recharges`: qual o tipo/formato de `update_date`, e ela ou `update_month` é a coluna de partição? | Partição errada = full scan numa tabela de ~93M linhas |
| 2 | `ifood_benefits_recharges`: quais os tipos e subcampos reais de `order_info` e `order_item_info`? | Aliases e tipos de `order_info.*` foram propostos, não confirmados |
| 3 | `chargeback_employee`: caminho completo, colunas reais, tipos e estratégia multi-tenant | Tabela documentada por inferência — **não liberar para o agente** até confirmar |
| 4 | `chargeback_employee`: `employee_name` e `tax_id` são dados em claro? | Muda o tratamento de LGPD do CSV entregue |

### Correções de código decorrentes das pendências já resolvidas

Não dependem de mais nenhuma confirmação — são consequência direta do que já foi confirmado:

| Onde | O quê |
|------|-------|
| `sql_validator.py:361-370` | `_has_valid_group_id_filter` deve aceitar `group_id` puro também para `chargeback` e `company_tax_invoice` (hoje só para `financial_account`/`financial_transaction`), senão rejeita filtro correto |
| `sql_validator.py:159-160` | `TABLE_RELATIONSHIPS["financeiro"]`: mover `chargeback` e `company_tax_invoice` de `tables` para `tables_with_direct_group_id` |
| `sql_validator.py:375-391` | `_financeiro_group_filter_clause` deve emitir `group_id = '<uuid>'` para as duas, em vez do filtro via alias de `companies` |
| `schema_extractor.py:12` | `chargeback` está mapeada para `recargas`; o domínio dela precisa ser decidido (hoje diverge do `TABLE_RELATIONSHIPS`) |
| `schema_extractor.py:10,17` | Remover `mv_employee_config` e `anticipation` do `TABLE_TO_DOMAIN` — **confirmado que não existem** |
| `sql_validator.py:139` | Remover `mv_employee_config` de `TABLE_RELATIONSHIPS["colaboradores"]["tables"]` pelo mesmo motivo |
| `sql_validator.py:563-579` e `tools/list_fields.py:19-27` | Quando `chargeback_employee` for confirmada, incluir `"## 8. Chargeback Employee"` nos mapas de domínio — sem isso os aliases dela não são validados |
