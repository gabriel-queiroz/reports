# Documentação de Tabelas — Databricks (Unity Catalog)

Gerado a partir do `DESCRIBE TABLE` no catálogo `main`. Cada seção traz a relação de colunas com **nome**, **tipo**, **descrição** e, quando aplicável, os **valores de enum**.

---

## 1. `main.ifoodoffice_invoice_service.company_tax_invoice`

| nome_coluna | tipo | descrição | enum |
|---|---|---|---|
| company_id | string | Identifica a empresa associada à nota fiscal de imposto (UUID). | — |
| created_at | string | Timestamp ISO 8601 de criação do registro da nota fiscal. | — |
| deleted | boolean | Indicador de exclusão lógica (true = excluída, false = ativa). | — |
| id | string | Identificador único (PK) da nota fiscal (UUID). | — |
| numero_titulo | string | Número de referência externa do título fiscal; pode ser nulo. | — |
| receivable_asset_id | string | FK para o ativo a receber (receivable asset) correspondente. | — |
| tax_invoice_status | string | Status do ciclo de vida da nota fiscal. | AVAILABLE, PENDING |
| tax_invoice_url | string | URL de acesso ao documento fiscal; nula quando pendente. | — |
| type | string | Classificação do tipo de documento fiscal; pode ser nulo. | — |
| updated_at | string | Timestamp ISO 8601 da última modificação do registro. | — |
| airbyte_metadata | struct<_airbyte_ab_id:string,_airbyte_emitted_at:bigint> | Metadados técnicos de ingestão do Airbyte (id e timestamp de emissão). | — |
| product_type | string | Categoria de produto iFood Office associada à nota. | REWARD_VOUCHER, MEAL_VOUCHER, MOBILITY_VOUCHER, CARD_ISSUE |
| amount | double | Valor financeiro da nota fiscal em BRL; pode ser nulo. | — |
| company_cnpj | string | CNPJ (14 dígitos, sem formatação) da empresa. | — |
| group_id | string | UUID do grupo corporativo; nulo para empresas sem grupo. | — |

---

## 2. `main.ifood_benf_transaction_service.financial_account`

| nome_coluna | tipo | descrição | enum |
|---|---|---|---|
| created_at | string | Timestamp ISO 8601 de criação da conta financeira. | — |
| deleted | boolean | Indicador de exclusão lógica da conta. | — |
| group_id | string | UUID do grupo corporativo/empresa associado à conta. | — |
| id | string | Identificador único (PK) da conta financeira (UUID). | — |
| origin | string | Classificação de origem/canal de criação da conta. | COMPANY |
| product_type | string | Tipo de produto de benefício associado à conta. | MEAL_VOUCHER, MOBILITY_VOUCHER, CULTURE_VOUCHER |
| test | boolean | Flag de ambiente de teste (true = teste). | — |
| type | string | Categoria operacional da conta. | MAIN |
| updated_at | string | Timestamp ISO 8601 da última atualização da conta. | — |

---

## 3. `main.ifood_benf_transaction_service.financial_transaction`

| nome_coluna | tipo | descrição | enum |
|---|---|---|---|
| account_id | string | UUID da conta do cliente envolvida na transação. | — |
| amount | double | Valor monetário da transação (positivo = crédito, negativo = débito). | — |
| amount_currency | string | Código de moeda ISO 4217. | BRL |
| authorization_id | string | UUID da autorização que permitiu a transação. | — |
| created_at | string | Timestamp ISO 8601 de criação da transação. | — |
| deleted | boolean | Indicador de exclusão lógica (soft delete). | — |
| external_id | string | Identificador de sistema externo/parceiro para conciliação. | — |
| id | string | Identificador único (PK) da transação (UUID). | — |
| idempotence_id | string | Chave de idempotência para evitar processamento duplicado. | — |
| is_synced | boolean | Indica se a transação foi sincronizada com sistemas downstream. | — |
| justification | string | Justificativa/descrição legível da transação. | — |
| rubric | string | Categoria contábil da transação. | DISTRIBUTION, BILLING_PAID, DISTRIBUTION_WALLET |
| test | boolean | Flag de transação de teste (true = teste). | — |
| transaction_date | string | Data de negócio (ISO 8601) da execução da transação. | — |
| type | string | Classificação da transação (crédito ou débito). | CREDIT, DEBIT |
| updated_at | string | Timestamp ISO 8601 da última modificação da transação. | — |

---

## 4. `main.fintech_finance.receivable_assets`

| nome_coluna | tipo | descrição | enum |
|---|---|---|---|
| receivable_asset_id | string | Identificador único (PK) do ativo a receber (UUID). | — |
| type | string | Classificação do método de cobrança/pagamento. | INVOICED_BOLETO, BOLETO, PIX, STARK_PAY |
| status | string | Status de pagamento do ativo a receber. | PENDING, RECEIVED, CANCELED, EXPIRED |
| deleted | boolean | Indicador de exclusão lógica (soft delete). | — |
| product_type | string | Produto fintech ao qual o ativo se refere. | MEAL_VOUCHER, MOBILITY_VOUCHER, EDUCATION_VOUCHER, CULTURE_VOUCHER (entre outros) |
| company_group_id | string | UUID do grupo empresarial responsável pelo pagamento. | — |
| amount | double | Valor principal do ativo a receber em BRL. | — |
| interest_amount | double | Juros aplicados a ativos em atraso. | — |
| iof_tax_amount | double | Valor de IOF (Imposto sobre Operações Financeiras). | — |
| due_date | string | Data de vencimento do pagamento (YYYY-MM-DD). | — |
| bank_conciliation_date | string | Data de confirmação/conciliação bancária do pagamento (YYYY-MM-DD). | — |
| paid_at | timestamp | Timestamp de recebimento/confirmação do pagamento. | — |
| created_at | timestamp | Timestamp de criação do registro do ativo. | — |
| updated_at | timestamp | Timestamp da última modificação do registro. | — |
| ifood_benefits_profit | double | Margem de lucro gerada pelos serviços iFood Benefits neste ativo. | — |
| numero_titulo | string | Número externo do título para identificação de pagamento. | — |
| invoice_internal_number | string | Número interno da fatura (nosso número do boleto). | — |
| invoice_external_number | string | Número externo da fatura (visível ao cliente). | — |
| external_id | string | Identificador de sistema externo para integração. | — |
| aggregation_id | string | Identificador para agrupamento de ativos relacionados. | — |
| metadata | struct<manual_invoice_enabled:boolean,mv_order_id:string,financial_antecipation_invoice:boolean,billing_id:string,payerdocument:string> | Metadados estruturados do ativo (flags e referências de cobrança). Campos: `manual_invoice_enabled`, `mv_order_id`, `financial_antecipation_invoice`, `billing_id`, `payerdocument`. | — |
| pagar_me | struct<bank_slip_id:string,company_id:string,boleto_barcode:string,boleto_url:string,transaction_id:string,status:string> | Detalhes do processador de pagamento PagarMe para boletos. Campos: `bank_slip_id`, `company_id`, `boleto_barcode`, `boleto_url`, `transaction_id`, `status`. | status: paid, waiting_payment, refused |
| zoop | struct<bank_slip_id:string,company_id:string,boleto_barcode:string,boleto_url:string,transaction_id:string,status:string,zoop_boleto_id:string,numero_titulo:string,reference_number:string> | Detalhes do processador de pagamento Zoop para boletos. Campos: `bank_slip_id`, `company_id`, `boleto_barcode`, `boleto_url`, `transaction_id`, `status`, `zoop_boleto_id`, `numero_titulo`, `reference_number`. | — |
| asset_month | string | Chave de particionamento por mês (YYYY-MM). | — |
| amount_detail | struct<meal_voucher_value:double,mobility_voucher_value:double,culture_voucher_value:double,education_voucher_value:double,home_office_voucher_value:double,reward_voucher_value:double,pharmacy_voucher_value:double,flex_meal_voucher_value:double,ifood_flex_meal_voucher_value:double,pharmacy_voucher_v2_value:double> | Detalhamento do valor por tipo de voucher/benefício. Campos: `meal_voucher_value`, `mobility_voucher_value`, `culture_voucher_value`, `education_voucher_value`, `home_office_voucher_value`, `reward_voucher_value`, `pharmacy_voucher_value`, `flex_meal_voucher_value`, `ifood_flex_meal_voucher_value`, `pharmacy_voucher_v2_value`. | — |

> **Nota:** `asset_month` é a coluna de particionamento desta tabela.

---

## 5. `main.fintech_companies.companies`

| nome_coluna | tipo | descrição | enum |
|---|---|---|---|
| company_id | string | Identificador único (PK) da empresa (UUID). | — |
| company_name | string | Nome fantasia/comercial da empresa. | — |
| company_group_id | string | UUID do grupo empresarial/holding ao qual a empresa pertence. | — |
| company_group_name | string | Nome legível do grupo empresarial (via join). | — |
| social_name | string | Razão social (nome legal) da empresa. | — |
| cnpj | string | CNPJ (Cadastro Nacional da Pessoa Jurídica) em formato numérico. | — |
| commercial_address | struct<street:string,number:string,complement:string,postal_code:string,district:string,city:string,state:string,country:string,postal_code_validation_error:boolean,geo_loc_info:struct<latitude:double,longitude:double,centroid_id:string,microcentroid_id:string>> | Endereço comercial completo com enriquecimento geográfico. Campos principais: `street`, `number`, `complement`, `postal_code`, `district`, `city`, `state`, `country`, `postal_code_validation_error`, `geo_loc_info` (latitude/longitude/centroid). | — |
| delivery_address | struct<street:string,number:string,complement:string,postal_code:string,district:string,city:string,state:string,country:string,postal_code_validation_error:boolean,geo_loc_info:struct<latitude:double,longitude:double,centroid_id:string,microcentroid_id:string>> | Endereço de entrega (cartões/materiais) com enriquecimento geográfico. Mesma estrutura de `commercial_address`. | — |
| card_delivery_type | string | Método de entrega dos cartões de benefício. | PAP (individual), LOTE (em lote) |
| is_cardless | boolean | Indica se a empresa opera exclusivamente com cartões virtuais. | — |
| origin | string | Sistema de origem que criou o registro da empresa. | SALESFORCE, SELFSALES (entre outros) |
| created_at | string | Timestamp ISO de criação do registro da empresa. | — |
| updated_at | string | Timestamp ISO da última atualização do registro. | — |
| deleted | boolean | Indicador de exclusão lógica (true = excluída, false = ativa). | — |
| test | boolean | Flag de registro de teste (true = teste). | — |

---

## 6. `main.fintech_finance.ifood_benefits_recharges`

| nome_coluna | tipo | descrição | enum |
|---|---|---|---|
| order_item_id | string | Identificador único (PK) do item de pedido (UUID). | — |
| order_id | string | UUID do pedido (order) pai ao qual o item pertence. | — |
| product_key | string | Identifica o tipo de produto de benefício alocado. | FOOD_VOUCHER, MEAL_VOUCHER (entre outros) |
| voucher_group | string | Agrupamento de negócio para tipos de voucher. | PAT, LIVRE |
| order_item_status | string | Status de processamento do item de pedido. | CREATED, DISTRIBUTION_COMPLETE |
| order_status | string | Status padronizado do pedido de recarga da empresa. | DISTRIBUTION_COMPLETE (legado DISTRIBUTED mapeado) |
| release_month_11_10 | date | Mês de negócio alternativo (ciclo dia 11 ao dia 10) para cálculos financeiros. | — |
| update_date | string | Data de atualização (YYYY-MM-DD), derivada de `updated_at`. | — |
| update_month | string | Mês de atualização (YYYY-MM), derivado de `updated_at`. | — |
| schedule_date | string | Data em que a recarga foi originalmente agendada (YYYY-MM-DD). | — |
| amount | double | Valor financeiro do benefício alocado neste item. | — |
| cashback_amount | double | Valor de cashback/benefício adicional associado. | — |
| employee_id | string | UUID do funcionário que recebeu a recarga. | — |
| person_id | string | UUID da entidade de pessoa associada ao funcionário. | — |
| order_item_info | struct<created_at:timestamp,updated_at:timestamp,transaction_id:string,correlation_id:string,employee_id:string,person_id:string,deleted:boolean,test:boolean> | Trilha de auditoria e metadados do item. Campos: `created_at`, `updated_at`, `transaction_id`, `correlation_id`, `employee_id`, `person_id`, `deleted`, `test`. | — |
| order_info | struct<order_id:string,created_at:string,created_by:string,updated_by:string,order_status:string,company_group_id:string,distributed:string,distribute_on:string,payment_method:string,type:string,scheduled:string,authorization_id:string,balance_usage:string,custom_description:string,pre_eligible:boolean,source_system:string,bko_action:string,deleted:boolean,test:boolean> | Informações consolidadas do pedido (pagamento, agendamento, ciclo de vida). Campos: `order_id`, `created_at`, `created_by`, `updated_by`, `order_status`, `company_group_id`, `distributed`, `distribute_on`, `payment_method`, `type`, `scheduled`, `authorization_id`, `balance_usage`, `custom_description`, `pre_eligible`, `source_system`, `bko_action`, `deleted`, `test`. | — |
| company_group | struct<id:string,name:string,cnpj:string> | Informações do grupo empresarial. Campos: `id`, `name`, `cnpj`. | — |
| company | struct<id:string,name:string,cnpj:string> | Informações da empresa individual. Campos: `id`, `name`, `cnpj`. | — |
| account_parent | struct<account_parent_id:string,nome_da_conta:string,cnpj_account_parent:string,faixa_de_funcionarios:string,tamanho:string,employees_range_group:string,size:string> | Informações da conta pai no Salesforce com classificação de porte. Campos: `account_parent_id`, `nome_da_conta`, `cnpj_account_parent`, `faixa_de_funcionarios`, `tamanho`, `employees_range_group`, `size`. | — |
| group_billing_authority | boolean | Indica se o grupo empresarial possui autoridade de cobrança. | — |
| has_error | boolean | Flag rápida indicando se há erro (de pedido ou de item). | — |
| error_info | struct<has_order_error:boolean,order_error_reason:string,has_order_item_error:boolean,order_item_error_reason:string> | Consolidação de erros de pedido e de item. Campos: `has_order_error`, `order_error_reason`, `has_order_item_error`, `order_item_error_reason`. | — |

> **Nota:** `update_date` é a coluna de particionamento desta tabela.

---

## 7. `main.ifoodoffice_management.employee`

| nome_coluna | tipo | descrição | enum |
|---|---|---|---|
| admission_date | string | Data de admissão do funcionário (ISO). | — |
| born_date | string | Data de nascimento do funcionário (ISO). | — |
| company_id | string | UUID da empresa à qual o funcionário pertence. | — |
| created_at | string | Timestamp ISO de criação do registro do funcionário. | — |
| customer_account_id | string | UUID da conta de cliente para faturamento/cobrança. | — |
| deleted | boolean | Indicador de exclusão lógica (soft delete). | — |
| discharge_date | string | Data de desligamento/término do funcionário (ISO). | — |
| food_voucher_customer_account_id | string | UUID da conta de cliente para faturamento de vale-alimentação (food voucher). | — |
| id | string | Identificador único (PK) do funcionário (UUID). | — |
| job_role_id | string | UUID do cargo/função do funcionário. | — |
| logistic_grouper | string | Agrupamento logístico para operações/entregas. | — |
| meal_policy_id | string | UUID da política de benefício de refeição aplicada. | — |
| meal_voucher_customer_account_id | string | UUID da conta de cliente para faturamento de vale-refeição (meal voucher). | — |
| origin_channel | string | Canal de origem do cadastro/onboarding do funcionário. | PLATFORM_B2B, DRAFT |
| person_id | string | UUID da entidade de pessoa (dados pessoais). | — |
| profile_type | string | Categoria de perfil do funcionário. | REQUESTER |
| registration_number | string | Número de matrícula/registro oficial do funcionário. | — |
| standard_cost_center_id | string | UUID do centro de custo para alocação de despesas. | — |
| status | string | Status atual do funcionário no ciclo de vida. | ACTIVE, INACTIVE |
| tag_cost_center | string | Tag adicional de centro de custo para alocação flexível. | — |
| tag_recharge_filter | string | Tag para filtragem/categorização em operações de recarga. | — |
| test | boolean | Flag de registro de teste (true = teste). | — |
| test_mode | string | Especifica o tipo de modo de teste. | loadtest |
| updated_at | string | Timestamp ISO da última modificação do registro. | — |
| user_id | string | UUID do usuário de sistema associado ao funcionário (autenticação). | — |
| airbyte_metadata | struct<_airbyte_ab_id:string,_airbyte_emitted_at:bigint> | Metadados de ingestão do Airbyte (id e timestamp de emissão). | — |
| email_hash | string | Hash SHA-256 do e-mail do funcionário (proteção de PII). | — |
| name_hash | string | Hash SHA-256 do nome completo (proteção de PII). | — |
| cpf_hash | string | Hash SHA-256 do CPF (proteção de PII). | — |
| phone_number_hash | string | Hash SHA-256 do telefone (proteção de PII). | — |
