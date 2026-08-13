# iFood Benefícios - Database Schema (Completo)

Documentação das tabelas Databricks do iFood Benefícios para geração de relatórios de IA.

**Fonte**: https://ifood.atlassian.net/wiki/spaces/IFE/pages/6599770142/Tabelas+do+Databricks

> **Este arquivo é a fonte da verdade única do catálogo.** Regras de domínio, partição,
> filtro multi-tenant e relacionamento vivem aqui — não no prompt nem no código.
>
> ⚠️ **Não renumere nem renomeie os headings `## N. Nome`.** Eles são usados como chave
> literal por `sql_validator.py` (`get_valid_aliases_for_domain`, `extract_fields_from_documentation`)
> e por `tools/list_fields.py` (`DOMAIN_MARKERS`). Se o texto mudar, a extração de aliases
> devolve vazio **em silêncio** e a validação passa a aprovar tudo.
>
> ⚠️ Use sempre `**Local**:` (o regex de `schema_extractor.py` não reconhece outras variações).

---

## 🇧🇷 INSTRUÇÃO IMPORTANTE - SEMPRE USE OS ALIASES EM PT-BR

**TODAS as queries geradas DEVEM usar os aliases em português brasileiro listados em cada tabela.**

Exemplo correto:
```sql
SELECT
  e.id AS id_colaborador,
  e.name_hash AS nome,
  e.email_hash AS email,
  e.created_at AS data_criacao,
  c.company_group_id AS company_group_id
FROM main.ifoodoffice_management.employee e
INNER JOIN fintech_companies.companies c ON e.company_id = c.company_id
WHERE e.deleted = false
  AND c.company_group_id = '{group_id}'
```

**⚠️ IMPORTANTE**: Os nomes entre `SELECT ... FROM` (id, name_hash, email_hash, created_at) são os nomes reais das colunas na tabela. Os nomes após `AS` (id_colaborador, nome, email, data_criacao) são os aliases em português que aparecem no resultado final.

Isso garante que:
- Os relatórios sejam entregues completamente em português
- Os nomes de campos sejam consistentes e legíveis para usuários brasileiros
- A documentação permaneça alinhada com a implementação

---

## 📋 TABELAS DISPONÍVEIS

Os números abaixo são os das seções deste arquivo (não são sequenciais: o catálogo
original tinha mais tabelas). **São chave literal para o código — não renumerar.**

- **7. Employee** (Colaboradores) — domínio `colaboradores`
- **3. Companies** (Empresas) — transversal
- **4. iFood Benefits Recharges** (Recargas) — domínio `recargas`
- **5. Receivable Assets** (Ativos a Receber) — domínio `financeiro`
- **6. Chargeback** (Estornos) — domínio em conflito (ver seção)
- **9. Company Tax Invoice** (Notas Fiscais) — domínio `financeiro`
- **10. Financial Account** (Conta Financeira) — domínio `financeiro`
- **11. Financial Transaction** (Transação Financeira) — domínio `financeiro`

---

## 7. Employee (Colaboradores)

**Local**: `main.ifoodoffice_management.employee`

**Descrição**: A tabela master de dados de funcionários da plataforma iFood Benefits. Centraliza informações de identidade e status de emprego.

**Volume de dados:** ~5,22M registros | **Última atualização:** 2026-07-22

**Domínio**: `colaboradores`

**Multi-tenant**: não possui coluna de grupo. Exige `INNER JOIN fintech_companies.companies c ON employee.company_id = c.company_id` e filtro em `c.company_group_id`.

**Partição obrigatória**: nenhuma documentada.

**Filtros padrão**: `deleted = false`, `test = false`.

**Relacionamentos**: `company_id` → `companies.company_id` · `id` → `ifood_benefits_recharges.employee_id`

**Lacunas conhecidas**: não há data de admissão nem de desligamento. Só existe `status` (ACTIVE/INACTIVE) e `created_at`. Perguntas sobre "desligados no período X" **não têm resposta possível** neste catálogo — o agente deve dizer isso, não improvisar coluna.

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

**Domínio**: `recargas`

**Multi-tenant**: STRUCT embutido — filtrar direto em `company_group.id`. JOIN com `companies` é opcional.

**Partição obrigatória**: nenhuma confirmada. Usar `update_month` (YYYY-MM) como filtro temporal. ⚠️ O `sql_system.md` manda particionar por `update_date`, coluna que não existe neste catálogo.

**Filtros padrão**: nenhum confirmado. ⚠️ Os exemplos do prompt usam `deleted = false`, coluna não documentada aqui.

**Relacionamentos**: `employee_id` → `employee.id` · `company_group.id` → `receivable_assets.company_group_id`

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

#### Campos de STRUCT (acessar com ponto — nunca selecionar o struct inteiro)

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `company_group.id` | STRING | `id_grupo` | Grupo de Empresas | UUID do grupo corporativo. **Usar no filtro multi-tenant.** |
| `company_group.name` | STRING | `nome_grupo_empresa` | Nome do Grupo | Nome do grupo corporativo |
| `company_group.cnpj` | STRING | `cnpj_grupo` | CNPJ do Grupo | CNPJ do grupo corporativo |
| `company.id` | STRING | `id_empresa` | Empresa | UUID da empresa dentro do grupo |
| `company.name` | STRING | `nome_empresa` | Nome da Empresa | Nome da empresa |
| `company.cnpj` | STRING | `cnpj_empresa` | CNPJ da Empresa | CNPJ da empresa |
| `order_item_info.*` | STRUCT | - | - | ⚠️ Subcampos não documentados. Confirmar no Databricks antes de usar. |


---

## 5. Receivable Assets (Ativos a Receber)

**Local**: `main.fintech_finance.receivable_assets`

**Descrição**: Ativos a receber (boletos, PIX e faturas) do iFood Office/Benefits. Uma linha por ativo/recebível.

**Particionada por**: `asset_month` (YYYY-MM) - **OBRIGATÓRIA em WHERE**

**Domínio**: `financeiro`

**Multi-tenant**: coluna direta `company_group_id`. Não exige JOIN.

**Filtros padrão**: `deleted = false`.

**Relacionamentos**: `receivable_asset_id` → `company_tax_invoice.receivable_asset_id` · `company_group_id` ← `ifood_benefits_recharges.company_group.id`

**Divergências com o prompt** (a confirmar no Databricks): o `sql_system.md` cita o status `EXPIRED` (aqui: `OVERDUE`), o tipo `STARK_PAY` (não listado) e os structs `pagar_me`, `zoop`, `metadata`, `amount_detail` (não documentados).

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

**Local**: `fintech_companies.companies`

**Descrição**: Master de dados cadastrais das empresas. Centraliza informações de identificação, endereços comerciais, geolocalização, grupo corporativo.

**Volume**: Centenas de milhares | **Última atualização**: 2026-07-22

**Domínio**: transversal — usada por todos os domínios como ponte para o filtro multi-tenant.

**Multi-tenant**: coluna direta `company_group_id`.

**Alias obrigatório**: quando entrar por JOIN, usar o alias `c` (exigido pelo prompt e pelo `sql_validator.py`).

**Filtros padrão**: `deleted = false`. ⚠️ Os exemplos do prompt filtram `c.test = false`, coluna **não documentada** nesta tabela.

**Relacionamentos**: `company_id` ← `employee.company_id`, `chargeback.company_id`, `company_tax_invoice.company_id`

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

**Domínio**: ⚠️ **conflito a resolver** — `schema_extractor.py` classifica como `recargas`; o `TABLE_RELATIONSHIPS` (`sql_validator.py`) e a descrição de domínios do agente classificam como `financeiro`. Enquanto os dois existirem, o domínio escolhido pelo LLM muda quais validações rodam.

**Multi-tenant**: possui `group_id` direto (UUID do grupo). ⚠️ **conflito a resolver** — o `sql_system.md` e o `TABLE_RELATIONSHIPS` exigem JOIN com `companies`, e o `_has_valid_group_id_filter` só aceita `group_id` puro para `financial_account`/`financial_transaction`. Hoje um filtro correto `ch.group_id = '<uuid>'` é **rejeitado** pela validação.

**Partição obrigatória**: nenhuma documentada. ⚠️ O `sql_system.md` manda particionar/filtrar por `updated_at`, coluna que não existe nesta tabela.

**Filtros padrão**: nenhum — esta tabela não tem `deleted` nem `test`.

**Relacionamentos**: `company_id` → `companies.company_id`

**Divergências com o prompt** (a confirmar no Databricks): `origin` e `updated_at` são citados no `sql_system.md` mas não existem aqui; a tabela `chargeback_employee`, descrita com 9 campos no prompt, não está neste catálogo.

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

**Domínio**: `financeiro`

**Multi-tenant**: possui `group_id` direto. ⚠️ **conflito a resolver** — o `sql_system.md:116-127` e o `TABLE_RELATIONSHIPS` exigem JOIN com `companies` para esta tabela, o que é desnecessário se o `group_id` daqui for o UUID do grupo.

**Partição obrigatória**: nenhuma documentada.

**Filtros padrão**: `deleted = false`.

**Relacionamentos**: `receivable_asset_id` → `receivable_assets.receivable_asset_id` · `company_id` → `companies.company_id`

**Atenção**: `numero_titulo` é o nome **físico** da coluna (já em português) — não é alias. Usar `numero_titulo AS numero_titulo`.

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

**Domínio**: `financeiro`

**Multi-tenant**: coluna direta `group_id` (atenção: **não** se chama `company_group_id`). Não exige JOIN.

**Partição obrigatória**: nenhuma documentada.

**Filtros padrão**: `deleted = false`, `test = false`.

**Relacionamentos**: `id` ← `financial_transaction.account_id`

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

**Domínio**: `financeiro`

**Multi-tenant**: não possui coluna de grupo. Exige `INNER JOIN main.ifood_benf_transaction_service.financial_account fa ON financial_transaction.account_id = fa.id` e filtro em `fa.group_id`.

**Partição obrigatória**: `dt` (DATE) / `dt_partition`.

**Filtros padrão**: `deleted = false`, `test = false`.

**Relacionamentos**: `account_id` → `financial_account.id`

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
employee.id              ──> ifood_benefits_recharges.employee_id
employee.company_id      ──> companies.company_id

ifood_benefits_recharges.company_group.id ──> companies.company_group_id
ifood_benefits_recharges.company.id       ──> companies.company_id

receivable_assets.company_group_id   ──> companies.company_group_id
receivable_assets.receivable_asset_id ──> company_tax_invoice.receivable_asset_id

chargeback.company_id          ──> companies.company_id
chargeback.group_id            ──> (grupo corporativo)

company_tax_invoice.company_id ──> companies.company_id
company_tax_invoice.group_id   ──> (grupo corporativo)

financial_transaction.account_id ──> financial_account.id
financial_account.group_id       ──> (grupo corporativo)
```

> A chave é sempre `tabela.coluna → tabela.coluna`, com o nome **físico** das duas pontas.
> `ifood_benefits_recharges` **não** tem `company_id` de topo — a ligação com empresa é pelo
> struct `company.id`, e com colaborador é por `employee_id`.

---

## 🔐 FILTROS DE SEGURANÇA MULTI-TENANT

**Obrigatório em TODAS as queries. Escolha o método apropriado conforme a tabela:**

### Via JOIN (quando tabela não tem company_group_id embutido)
> ⚠️ `chargeback` e `company_tax_invoice` aparecem aqui por herança do prompt antigo, mas
> ambas possuem `group_id` próprio. Ver a seção de cada tabela — conflito ainda não resolvido.
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

## ⚠️ ARMADILHAS DO CATÁLOGO

Divergências reais entre tabelas deste mesmo arquivo. Não são erros de digitação — são
o que o catálogo é hoje, e cada uma já causou ou causa query errada.

### 1. O mesmo conceito de data tem tipo diferente conforme a tabela

| Coluna | Tabela | Tipo | Formato |
|--------|--------|------|---------|
| `created_at` | employee, chargeback, company_tax_invoice, financial_account, financial_transaction | STRING | ISO 8601 |
| `created_at` | **receivable_assets** | **TIMESTAMP** | — |
| `paid_at` | receivable_assets | TIMESTAMP | — |
| `due_date` | receivable_assets | STRING | YYYY-MM-DD |
| `update_month` | ifood_benefits_recharges | STRING | **YYYY-MM** |
| `schedule_date` | ifood_benefits_recharges | STRING | YYYY-MM-DD |
| `transaction_date` | financial_transaction | STRING | YYYY-MM-DD |
| `dt` | financial_transaction | DATE | YYYY-MM-DD |

Filtrar período numa coluna STRING é **comparação de texto**: funciona por ser ISO, mas só
se o filtro usar o mesmo comprimento de string. `update_month` é YYYY-MM — comparar com
`'2026-07-01'` não faz o que parece.

### 2. Aliases PT-BR repetidos em tabelas diferentes

| Alias | Aponta para |
|-------|-------------|
| `id_conta_financeira` | `financial_account.id` **e** `financial_transaction.account_id` (colunas distintas) |
| `id_empresa` | `company_id` (employee, chargeback, company_tax_invoice) e `company.id` (recargas) |
| `id_grupo` | `group_id` (chargeback, company_tax_invoice, financial_account) e `company_group.id` (recargas) |
| `valor` | `amount` em recargas, receivable_assets, company_tax_invoice, financial_transaction |
| `tipo` | `type` em receivable_assets, financial_account, financial_transaction |
| `situacao` | `status` em employee e em receivable_assets |
| `data_criacao` | `created_at` em cinco tabelas |

Em query com JOIN, dois campos com o mesmo alias produzem **colunas duplicadas no CSV**.
Ao cruzar tabelas, desambiguar no alias (ex.: `valor_recarga`, `valor_nota`).

### 3. Quatro aliases são idênticos ao nome físico da coluna

`company_group_id`, `cnpj`, `login`, `numero_titulo`.

Contradizem a regra do topo deste arquivo ("o que vem depois do `AS` é o nome em português")
e são a causa dos falsos positivos do `validate_alias_misuse`, que hoje reprova query
correta que filtre por `c.cnpj` ou agrupe por `c.company_group_id`.

---

## ⏳ PENDÊNCIAS — a confirmar no Databricks

Itens que este catálogo **não** consegue resolver sozinho. Enquanto estiverem abertos, a
validação de colunas herda o erro deles. Cada um vira uma correção no `sql_system.md`, no
`sql_validator.py` ou aqui — nunca uma invenção do LLM.

| # | Pendência | Impacto se ficar aberto |
|---|-----------|-------------------------|
| 1 | `employee` tem coluna de admissão/desligamento? O prompt cita `hire_date` e `termination_date`. | Pergunta comum ("desligados em julho") sem resposta possível → LLM inventa coluna |
| 2 | `employee`: existem `employee_id`, `employee_name`, `person_id`? O prompt afirma que sim. | Prompt ensina 5 colunas que este catálogo não tem |
| 3 | `ifood_benefits_recharges`: existe `deleted`? Qual é a partição real (`update_month`? `update_date`?) | Filtro obrigatório do prompt pode não existir; partição errada = full scan |
| 4 | `ifood_benefits_recharges`: existem `order_item_id`, `order_status`, struct `order_info`? | Prompt descreve struct `order_info`; catálogo só tem `order_item_info` |
| 5 | `chargeback`: o `group_id` é o UUID do grupo (mesmo de `company_group_id`)? Existem `origin` e `updated_at`? | Decide se JOIN com `companies` é necessário e se a validação atual está rejeitando query correta |
| 6 | `company_tax_invoice`: o `group_id` é o UUID do grupo? | Mesmo caso do item 5 |
| 7 | Existe a tabela `chargeback_employee`? E `mv_employee_config`, `anticipation`, `anticipation_receivable`? | Citadas no prompt e no código, ausentes do catálogo |
| 8 | `companies` tem `test`? | Exemplo canônico do prompt usa `c.test = false` |
| 9 | `receivable_assets`: status `EXPIRED` ou `OVERDUE`? Tipo `STARK_PAY` existe? Structs `pagar_me`/`zoop`/`metadata`/`amount_detail`? | Enum errado = relatório vazio silencioso |
| 10 | Os campos `_hash` de `employee` devem ser oferecidos ao usuário? Hoje aparecem como "Nome", "CPF", "Email" e entregam SHA-256. | Usuário pede "Nome, CPF, Email" e recebe CSV de hashes |

---

*Documentação atualizada em 2026-07-22 para suportar agente gerador de relatórios B2B do iFood Benefits.*
