# iFood Benefícios - Database Schema (Completo)
# iFood Benefícios - Database Schema (Completo)

Documentação das tabelas Databricks do iFood Benefícios para geração de relatórios de IA.

**Fonte**: https://ifood.atlassian.net/wiki/spaces/IFE/pages/6599770142/Tabelas+do+Databricks

---

## 🇧🇷 INSTRUÇÃO IMPORTANTE - SEMPRE USE OS ALIASES EM PT-BR

**TODAS as queries geradas DEVEM usar os aliases em português brasileiro listados em cada tabela.**

Exemplo correto:
```sql
SELECT
  id AS id_colaborador,
  name_hash AS nome,
  email_hash AS email,
  created_at AS data_criacao
FROM main.ifoodoffice_management.employee
```

**⚠️ IMPORTANTE**: Os nomes entre `SELECT ... FROM` (id, name_hash, email_hash, created_at) são os nomes reais das colunas na tabela. Os nomes após `AS` (id_colaborador, nome, email, data_criacao) são os aliases em português que aparecem no resultado final.

Isso garante que:
- Os relatórios sejam entregues completamente em português
- Os nomes de campos sejam consistentes e legíveis para usuários brasileiros
- A documentação permaneça alinhada com a implementação

---

## 📋 TABELAS DISPONÍVEIS

1. **Employee** (Colaboradores)
2. **Companies** (Empresas)
3. **iFood Benefits Recharges** (Recargas)
4. **Receivable Assets** (Ativos a Receber)
5. **Chargeback** (Estornos)
6. **Company Tax Invoice** (Notas Fiscais)
7. **Financial Account** (Conta Financeira)
8. **Financial Transaction** (Transação Financeira)

---

## 7. Employee (Colaboradores)

**Local**: `main.ifoodoffice_management.employee`

**Descrição**: A tabela master de dados de funcionários da plataforma iFood Benefits. Centraliza informações de identidade e status de emprego.

**Volume de dados:** ~5,22M registros | **Última atualização:** 2026-07-22

### Categorias de Campos

#### 🔑 Identificação do Colaborador (identidade única)
Use para identificar e referenciar colaboradores nos relatórios.

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Uso |
|--------|------|-------------|----------|-----------|-----|
| `id` | STRING | `id_colaborador` | ID | UUID único do funcionário. Chave primária da tabela. | ✅ Essencial |
#### 👤 Dados Pessoais (hasheados por privacidade)
Todos os campos com sufixo `_hash` contêm SHA-256 do valor original. **Não contêm dados sensíveis legíveis.**

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Uso |
|--------|------|-------------|----------|-----------|-----|
| `name_hash` | STRING | `nome` | Nome | SHA-256 hash do nome completo. Não recuperável, apenas para matching. | Relatórios |
| `email_hash` | STRING | `email` | Email | SHA-256 hash do email corporativo. Não recuperável. | Relatórios |
| `cpf_hash` | STRING | `cpf` | CPF | SHA-256 hash do CPF. Não recuperável por segurança. | Relatórios |
| `phone_number_hash` | STRING | `telefone` | Telefone | SHA-256 hash do telefone. Não recuperável. | Relatórios |
| `born_date` | STRING | `data_nascimento` | Data de Nascimento | Data de nascimento em ISO format (YYYY-MM-DD). Pode ser nula. | Opcional |

#### 📊 Status e Emprego (situação do colaborador)
Campos que indicam o estado atual do colaborador no sistema.

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Uso |
|--------|------|-------------|----------|-----------|-----|
| `status` | STRING | `situacao` | Situação | Status do colaborador: **ACTIVE** (ativo) ou **INACTIVE** (desligado/removido). Use para filtrar ativos vs. inativos. | ✅ Essencial |
| `company_id` | STRING | `id_empresa` | Empresa | UUID da empresa/subsidiária onde o colaborador trabalha. **Obrigatório para filtros multi-tenant.** | ✅ Essencial |

#### 🔍 Metadata e Auditoria
Campos de controle, datas e flags técnicas.

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Uso |
|--------|------|-------------|----------|-----------|-----|
| `deleted` | BOOLEAN | `deletado` | Deletado | Flag de soft delete. `true` = registro marcado como deletado (lógico, não físico). Sempre filtrar `deleted = false`. | ✅ Filtro |
| `test` | BOOLEAN | `teste` | Teste | Flag indicando dados de teste. `true` = registro de teste, `false` = produção. Filtrar conforme necessário. | Teste |
| `test_mode` | STRING | `modo_teste` | Modo de Teste | Modo de teste técnico (valor informacional). Ignorar em relatórios de produção. | Ignorar |
| `created_at` | STRING | `data_criacao` | Data de Criação | Timestamp ISO 8601 de quando o colaborador foi criado no sistema. | Auditoria |

---

## 4. iFood Benefits Recharges (Recargas)

**Local**: `main.fintech_finance.ifood_benefits_recharges`

**Descrição**: Recargas de benefícios do iFood Benefits. Uma linha por transação individual de recarga.

**Volume**: ~93M registros | **Última atualização**: 2026-07-22

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `order_id` | STRING | `id_pedido` | Pedido | ID do pedido/transação |
| `product_key` | STRING | `chave_produto` | Produto | FOOD_VOUCHER, MEAL_VOUCHER, MOBILITY_VOUCHER... |
| `order_item_status` | STRING | `situacao_item_pedido` | Situação do Item | CREATED, DISTRIBUTION_COMPLETE |
| `amount` | DOUBLE | `valor` | Valor | Valor da recarga (R$) |
| `cashback_amount` | DOUBLE | `valor_cashback` | Cashback | Valor do cashback (R$) |
| `employee_id` | STRING | `id_colaborador` | Colaborador | ID do funcionário |
| `update_month` | STRING | `mes_atualizacao` | Mês de Atualização | Mês da atualização (YYYY-MM) |
| `schedule_date` | STRING | `data_agendamento` | Data de Agendamento | Data agendada (YYYY-MM-DD) |
| `company_group` | STRUCT | `grupo_empresa` | Grupo de Empresas | {id, name, cnpj} - Dados do grupo corporativo. **Usar para filtrar por group_id diretamente!** |
| `company` | STRUCT | `empresa` | Empresa | {id, name, cnpj} - Dados da companhia específica dentro do grupo |
| `order_item_info` | STRUCT | `info_item_pedido` | Info do Item | Metadados do item |


---

## 5. Receivable Assets (Ativos a Receber)

**Local**: `main.fintech_finance.receivable_assets`

**Descrição**: Ativos a receber (boletos, PIX e faturas) do iFood Office/Benefits. Uma linha por ativo/recebível.

**Particionada por**: `asset_month` (YYYY-MM) - **OBRIGATÓRIA em WHERE**

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `receivable_asset_id` | STRING | `id_ativo_recebivel` | Ativo Recebível | UUID único do ativo |
| `type` | STRING | `tipo` | Tipo | BOLETO, INVOICED_BOLETO, PIX |
| `status` | STRING | `situacao` | Situação | PENDING, RECEIVED, CANCELED, OVERDUE |
| `product_type` | STRING | `tipo_produto` | Tipo de Produto | MEAL_VOUCHER, MOBILITY, CULTURE, etc. |
| `company_group_id` | STRING | `company_group_id` | Grupo de Empresas | ID do grupo corporativo |
| `amount` | DOUBLE | `valor` | Valor | Valor principal (R$) |
| `interest_amount` | DOUBLE | `valor_juros` | Juros | Valor de juros (R$) |
| `iof_tax_amount` | DOUBLE | `valor_iof` | IOF | Valor de IOF (R$) |
| `due_date` | STRING | `data_vencimento` | Data de Vencimento | Data de vencimento (YYYY-MM-DD) |
| `paid_at` | TIMESTAMP | `data_pagamento` | Data de Pagamento | Timestamp do pagamento |
| `created_at` | TIMESTAMP | `data_criacao` | Data de Criação | Timestamp de criação |
| `invoice_internal_number` | STRING | `numero_interno_fatura` | Número Interno | Número interno da fatura |
| `invoice_external_number` | STRING | `numero_externo_fatura` | Número Externo | Número externo da fatura |
| `external_id` | STRING | `id_externo` | ID Externo | ID externo |
| `deleted` | BOOLEAN | `deletado` | Deletado | Soft delete |


---

## 3. Companies (Empresas)

**Localização:** `fintech_companies.companies`

**Descrição**: Master de dados cadastrais das empresas. Centraliza informações de identificação, endereços comerciais, geolocalização, grupo corporativo.

**Volume**: Centenas de milhares | **Última atualização**: 2026-07-22

### Colunas

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `company_id` | STRING | `id_empresa` | Empresa | UUID único |
| `cnpj` | STRING | `cnpj` | CNPJ | CNPJ (14 dígitos) |
| `company_name` | STRING | `nome_empresa` | Nome Fantasia | Nome fantasia |
| `social_name` | STRING | `razao_social` | Razão Social | Razão social |
| `company_group_id` | STRING | `company_group_id` | Grupo de Empresas | UUID do grupo corporativo |
| `company_group_name` | STRING | `nome_grupo_empresa` | Nome do Grupo | Nome do grupo |
| `card_delivery_type` | STRING | `tipo_entrega_cartao` | Tipo de Entrega | LOTE ou outro |
| `is_cardless` | BOOLEAN | `sem_cartao` | Sem Cartão | Operação digital |
| `commercial_address` | STRUCT | `endereco_comercial` | Endereço Comercial | Endereço comercial |
| `deleted` | BOOLEAN | `deletado` | Deletado | Soft delete |


---

## 6. Chargeback (Estornos)

**Local**: `main.ifoodoffice_recharge_chargeback.chargeback`

**Descrição**: Estornos (chargebacks) de recargas do iFood Office.

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `id` | STRING | `id_estorno` | Estorno (ID) | UUID único |
| `company_id` | STRING | `id_empresa` | Empresa | UUID da empresa |
| `company_name` | STRING | `nome_empresa` | Nome da Empresa | Nome da empresa |
| `group_id` | STRING | `id_grupo` | Grupo | UUID do grupo |
| `login` | STRING | `login` | Usuário | Usuário que solicitou |
| `chargeback_status` | STRING | `situacao_estorno` | Situação | Status (CONCLUDED, etc.) |
| `company_contract_type` | STRING | `tipo_contrato_empresa` | Tipo de Contrato | Tipo de contrato |
| `total_amount_recharged` | DOUBLE | `valor_total_recarregado` | Valor Recarregado | Valor recarregado |
| `total_amount_requested` | DOUBLE | `valor_total_solicitado` | Valor Solicitado | Valor solicitado |
| `total_chargeback_employees` | BIGINT | `total_colaboradores_estorno` | Total de Colaboradores | Total de funcionários |
| `total_divergent_chargeback_employees` | BIGINT | `total_colaboradores_divergencia_estorno` | Colaboradores com Divergência | Funcionários com divergência |
| `created_at` | STRING | `data_criacao` | Data de Criação | Criação (ISO 8601) |


---

## 9. Company Tax Invoice (Notas Fiscais)

**Local**: `main.ifoodoffice_invoice_service.company_tax_invoice`

**Descrição**: Notas fiscais (NF-e/NFS-e) emitidas para empresas clientes.

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `id` | STRING | `id_nota_fiscal` | Nota Fiscal (ID) | UUID da nota |
| `company_id` | STRING | `id_empresa` | Empresa | UUID da empresa |
| `company_cnpj` | STRING | `cnpj_empresa` | CNPJ | CNPJ (14 dígitos) |
| `group_id` | STRING | `id_grupo` | Grupo | UUID do grupo |
| `receivable_asset_id` | STRING | `id_ativo_recebivel` | Ativo Recebível | FK para receivable_assets |
| `numero_titulo` | STRING | `numero_titulo` | Número do Título | Número do título/boleto |
| `tax_invoice_status` | STRING | `situacao_nota_fiscal` | Situação | PENDING, AVAILABLE |
| `tax_invoice_url` | STRING | `url_nota_fiscal` | URL | URL para download |
| `product_type` | STRING | `tipo_produto` | Tipo de Produto | Tipo de produto |
| `amount` | DOUBLE | `valor` | Valor | Valor em R$ |
| `deleted` | BOOLEAN | `deletado` | Deletado | Soft delete |
| `created_at` | STRING | `data_criacao` | Data de Criação | Criação |

---

## 10. Financial Account (Conta Financeira)

**Local**: `main.ifood_benf_transaction_service.financial_account`

**Descrição**: Registro dos dados técnicos relativos à conta financeira da empresa cliente do iFood Benefícios (B2B). É a conta que viabiliza as movimentações de valor no Financeiro da Plataforma iFood Benefícios.

**Frequência**: D-1

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `id` | STRING | `id_conta_financeira` | Conta Financeira (ID) | UUID único da conta financeira da empresa cliente. Chave primária. |
| `group_id` | STRING | `id_grupo` | Grupo | UUID do grupo corporativo da empresa. **Usar para filtros multi-tenant.** |
| `product_type` | STRING | `tipo_produto` | Tipo de Produto | Produto ao qual a conta está vinculada (MEAL_VOUCHER, FOOD_VOUCHER, MOBILITY_VOUCHER, etc.). |
| `type` | STRING | `tipo` | Tipo | Tipo da conta financeira. |
| `origin` | STRING | `origem` | Origem | Origem de criação da conta financeira. |
| `test` | BOOLEAN | `teste` | Teste | Flag de dados de teste. `true` = teste, `false` = produção. |
| `deleted` | BOOLEAN | `deletado` | Deletado | Soft delete. Filtrar `deleted = false`. |
| `created_at` | STRING | `data_criacao` | Data de Criação | Timestamp ISO 8601 de criação da conta. |
| `updated_at` | STRING | `data_atualizacao` | Data de Atualização | Timestamp ISO 8601 da última atualização da conta. |
| `_origin_time` | STRING | `tempo_origem` | Tempo de Origem | Metadado técnico Databricks. Normalmente ignorado em relatórios. |
| `_processing_time` | STRING | `tempo_processamento` | Tempo de Processamento | Metadado técnico Databricks. Normalmente ignorado em relatórios. |
| `_timeid` | STRING | `timeid` | Time ID | Metadado técnico de particionamento. Normalmente ignorado em relatórios. |

---

## 11. Financial Transaction (Transação Financeira)

**Local**: `main.ifood_benf_transaction_service.financial_transaction`

**Descrição**: Registro dos dados relativos às movimentações de valor na conta financeira da empresa cliente do iFood Benefícios (B2B). Exemplos: entradas a partir da adição de saldo para consumo em recargas futuras, entradas a partir de estornos de recarga, saídas a partir de distribuições de recargas.

**Frequência**: D-1

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `id` | STRING | `id_transacao_financeira` | Transação Financeira (ID) | UUID único da movimentação. Chave primária. |
| `account_id` | STRING | `id_conta_financeira` | Conta Financeira | FK para `financial_account.id`. |
| `amount` | DOUBLE | `valor` | Valor | Valor da movimentação (R$). |
| `amount_currency` | STRING | `moeda_valor` | Moeda | Moeda do valor (ex.: BRL). |
| `authorization_id` | STRING | `id_autorizacao` | Autorização | ID da autorização associada à movimentação. |
| `type` | STRING | `tipo` | Tipo | Tipo da movimentação (entrada, saída, estorno, etc.). |
| `rubric` | STRING | `rubrica` | Rubrica | Rubrica/classificação contábil da movimentação. |
| `justification` | STRING | `justificativa` | Justificativa | Justificativa/descrição da movimentação. |
| `transaction_date` | STRING | `data_transacao` | Data da Transação | Data da movimentação (YYYY-MM-DD). |
| `external_id` | STRING | `id_externo` | ID Externo | ID externo da movimentação. |
| `idempotence_id` | STRING | `id_idempotencia` | ID de Idempotência | Chave de idempotência da movimentação. |
| `is_synced` | BOOLEAN | `sincronizado` | Sincronizado | Indica se a movimentação foi sincronizada com sistemas externos. |
| `test` | BOOLEAN | `teste` | Teste | Flag de dados de teste. `true` = teste, `false` = produção. |
| `deleted` | BOOLEAN | `deletado` | Deletado | Soft delete. Filtrar `deleted = false`. |
| `created_at` | STRING | `data_criacao` | Data de Criação | Timestamp ISO 8601 de criação. |
| `updated_at` | STRING | `data_atualizacao` | Data de Atualização | Timestamp ISO 8601 da última atualização. |
| `dt` | DATE | `data` | Data | Data de particionamento (YYYY-MM-DD). |
| `dt_partition` | STRING | `particao_data` | Partição de Data | Partição da tabela. |
| `_origin_time` | STRING | `tempo_origem` | Tempo de Origem | Metadado técnico Databricks. Normalmente ignorado em relatórios. |
| `_processing_time` | STRING | `tempo_processamento` | Tempo de Processamento | Metadado técnico Databricks. Normalmente ignorado em relatórios. |
| `_timeid` | STRING | `timeid` | Time ID | Metadado técnico de particionamento. Normalmente ignorado em relatórios. |

---

## 📊 RELACIONAMENTOS

```
employee ──via company_id──> ifood_benefits_recharges
       ├──via company_id──> companies

ifood_benefits_recharges ──via company_group.id──> receivable_assets

receivable_assets ──via company_group_id──> (grupo corporativo)
                └──via receivable_asset_id──> company_tax_invoice

chargeback ──via company_id──> companies

financial_transaction ──via account_id──> financial_account
financial_account ──via group_id──> (grupo corporativo)
```

---

## 🔐 FILTROS DE SEGURANÇA MULTI-TENANT

**Obrigatório em TODAS as queries. Escolha o método apropriado conforme a tabela:**

### Via JOIN (quando tabela não tem company_group_id embutido)
```sql
-- employee, chargeback - precisam de JOIN:
FROM main.ifoodoffice_management.employee e
INNER JOIN fintech_companies.companies c ON e.company_id = c.company_id
WHERE c.company_group_id = '{group_id}'
```

### Via STRUCT (quando company_group está embutido na tabela)
```sql
-- ifood_benefits_recharges - tem company_group STRUCT:
FROM main.fintech_finance.ifood_benefits_recharges
WHERE company_group.id = '{group_id}'  -- ← Acesso direto ao STRUCT
```

### Via Coluna Direta (quando company_group_id é coluna normal)
```sql
-- receivable_assets - tem company_group_id como coluna:
FROM main.fintech_finance.receivable_assets
WHERE company_group_id = '{group_id}'
```

### Via Coluna Direta `group_id` (financial_account)
```sql
-- financial_account - tem group_id como coluna normal:
FROM main.ifood_benf_transaction_service.financial_account
WHERE group_id = '{group_id}'
```

### Via JOIN com financial_account (financial_transaction)
```sql
-- financial_transaction - precisa de JOIN pela conta financeira:
FROM main.ifood_benf_transaction_service.financial_transaction ft
INNER JOIN main.ifood_benf_transaction_service.financial_account fa
  ON ft.account_id = fa.id
WHERE fa.group_id = '{group_id}'
```

Além do filtro, toda query deve incluir o `company_group_id` como coluna de saída
no `SELECT` (campo real da tabela, alias exato `company_group_id`).

> Para `financial_account` e `financial_transaction`, o campo de grupo é `group_id`
> (alias `id_grupo`). Use esse campo no filtro e na coluna de saída.

---

## 🎯 TIPOS DE DADOS

- **STRING**: Texto (UUIDs, nomes, CPF/CNPJ)
- **DOUBLE**: Valores monetários com precisão
- **INTEGER/BIGINT**: Números inteiros
- **BOOLEAN**: Verdadeiro/Falso
- **DATE**: Data (YYYY-MM-DD)
- **TIMESTAMP**: Data e hora (ISO 8601)
- **STRUCT**: Dados aninhados (usar `.campo` para expandir)

---

*Documentação atualizada em 2026-07-22 para suportar agente gerador de relatórios B2B do iFood Benefits.*
