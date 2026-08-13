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
  e.created_at AS data_criacao_colaborador,
  c.company_group_id AS company_group_id
FROM main.ifoodoffice_management.employee e
INNER JOIN fintech_companies.companies c ON e.company_id = c.company_id
WHERE e.deleted = false
  AND c.company_group_id = '<uuid-do-grupo>'
```

**⚠️ IMPORTANTE**: Os nomes entre `SELECT ... FROM` (id, name_hash, email_hash, created_at) são os nomes reais das colunas na tabela. Os nomes após `AS` (id_colaborador, nome, email, data_criacao_colaborador) são os aliases em português que aparecem no resultado final.

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
- **8. Chargeback Employee** (Estorno por Colaborador) — ⚠️ não confirmada, não liberar ainda
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

**Colunas que NÃO existem** (confirmado no dump do Databricks): `employee_id`, `employee_name`. O `sql_system.md` as listava como "campos principais" — era invenção do prompt. Os equivalentes reais são `id` e `name_hash`.

**Situação do colaborador**: use `status` (`ACTIVE` / `INACTIVE`). As colunas disponíveis para relatório são exatamente as listadas abaixo — nenhuma outra.

### Categorias de Campos

#### 🔑 Identificação do Colaborador (identidade única)
Use para identificar e referenciar colaboradores nos relatórios.

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Uso |
|--------|------|-------------|----------|-----------|-----|
| `id` | STRING | `id_colaborador` | ID | UUID único do funcionário. Chave primária da tabela. | ✅ Essencial |

#### 👤 Dados Pessoais (hasheados por privacidade)
Todos os campos com sufixo `_hash` contêm SHA-256 do valor original. **Não contêm dados sensíveis legíveis.**

> **Decisão registrada:** estes quatro campos continuam sendo oferecidos ao usuário com os
> rótulos atuais ("Nome", "Email", "CPF", "Telefone"). Consequência conhecida e aceita: quem
> pedir esses campos recebe um CSV com os hashes SHA-256, não com os valores legíveis.
> Não é bug — se for para mudar, mexer aqui na coluna Exibição e nos aliases.

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
| `status` | STRING | `situacao_colaborador` | Situação | Status do colaborador: **ACTIVE** (ativo) ou **INACTIVE** (desligado/removido). Use para filtrar ativos vs. inativos. | ✅ Essencial |
| `company_id` | STRING | `id_empresa_colaborador` | Empresa | UUID da empresa/subsidiária onde o colaborador trabalha. **Obrigatório para filtros multi-tenant.** | ✅ Essencial |

#### 🔍 Metadata e Auditoria
Campos de controle, datas e flags técnicas.

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Uso |
|--------|------|-------------|----------|-----------|-----|
| `deleted` | BOOLEAN | `deletado_colaborador` | Deletado | Flag de soft delete. `true` = registro marcado como deletado (lógico, não físico). Sempre filtrar `deleted = false`. | ✅ Filtro |
| `test` | BOOLEAN | `teste_colaborador` | Teste | Flag indicando dados de teste. `true` = registro de teste, `false` = produção. Filtrar conforme necessário. | Teste |
| `test_mode` | STRING | `modo_teste` | Modo de Teste | Modo de teste técnico (valor informacional). Ignorar em relatórios de produção. | Ignorar |
| `created_at` | STRING | `data_criacao_colaborador` | Data de Criação | Timestamp ISO 8601 de quando o colaborador foi criado no sistema. | Auditoria |

---

## 4. iFood Benefits Recharges (Recargas)

**Local**: `main.fintech_finance.ifood_benefits_recharges`

**Descrição**: Recargas de benefícios do iFood Benefits. Uma linha por transação individual de recarga.

**Volume**: ~93M registros | **Última atualização**: 2026-07-22

**Domínio**: `recargas`

**Multi-tenant**: STRUCT embutido — filtrar direto em `company_group.id`. JOIN com `companies` é opcional.

**Partição obrigatória**: `update_date` (confirmado que existe, junto com `update_month`). Usar `update_month` (YYYY-MM) como filtro temporal legível. ⚠️ Falta confirmar o **tipo/formato** de `update_date` e qual das duas é de fato a coluna de partição.

**Filtros padrão**: nenhum — esta tabela **não tem** `deleted` nem `test` (confirmado). Filtrar `r.deleted = false` aqui quebra a query.

**Relacionamentos**: `employee_id` → `employee.id` · `company_group.id` → `receivable_assets.company_group_id`

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `order_id` | STRING | `id_pedido` | Pedido | ID do pedido/transação |
| `order_item_id` | STRING | `id_item_pedido` | Item do Pedido | ID do item de recarga. É a granularidade desta tabela (uma linha por item) |
| `product_key` | STRING | `chave_produto` | Produto | FOOD_VOUCHER, MEAL_VOUCHER, MOBILITY_VOUCHER... |
| `order_status` | STRING | `situacao_pedido` | Situação do Pedido | Status no nível do pedido |
| `order_item_status` | STRING | `situacao_item_pedido` | Situação do Item | CREATED, DISTRIBUTION_COMPLETE |
| `amount` | DOUBLE | `valor_recarga` | Valor | Valor da recarga (R$) |
| `cashback_amount` | DOUBLE | `valor_cashback` | Cashback | Valor do cashback (R$) |
| `employee_id` | STRING | `id_colaborador_recarga` | Colaborador | ID do funcionário |
| `update_month` | STRING | `mes_atualizacao` | Mês de Atualização | Mês da atualização (YYYY-MM) |
| `update_date` | STRING | `data_atualizacao_recarga` | Data de Atualização | **Coluna de partição** — filtrar sempre que possível. Tipo/formato a confirmar |
| `schedule_date` | STRING | `data_agendamento` | Data de Agendamento | Data agendada (YYYY-MM-DD) |
| `company_group` | STRUCT | `grupo_empresa` | Grupo de Empresas | {id, name, cnpj} - Dados do grupo corporativo. **Usar para filtrar por group_id diretamente!** |
| `company` | STRUCT | `empresa` | Empresa | {id, name, cnpj} - Dados da companhia específica dentro do grupo |
| `order_item_info` | STRUCT | `info_item_pedido` | Info do Item | Metadados do item |

#### Campos de STRUCT (acessar com ponto — nunca selecionar o struct inteiro)

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `company_group.id` | STRING | `id_grupo_recarga` | Grupo de Empresas | UUID do grupo corporativo. **Usar no filtro multi-tenant.** |
| `company_group.name` | STRING | `nome_grupo_empresa_recarga` | Nome do Grupo | Nome do grupo corporativo |
| `company_group.cnpj` | STRING | `cnpj_grupo` | CNPJ do Grupo | CNPJ do grupo corporativo |
| `company.id` | STRING | `id_empresa_recarga` | Empresa | UUID da empresa dentro do grupo |
| `company.name` | STRING | `nome_empresa_recarga` | Nome da Empresa | Nome da empresa |
| `company.cnpj` | STRING | `cnpj_empresa_recarga` | CNPJ da Empresa | CNPJ da empresa |
| `order_info.payment_method` | STRING | `forma_pagamento` | Forma de Pagamento | Meio de pagamento do pedido |
| `order_info.balance_usage` | STRING | `uso_saldo` | Uso de Saldo | Indicação de uso de saldo na recarga |
| `order_info.custom_description` | STRING | `descricao_personalizada` | Descrição | Descrição livre informada no pedido |
| `order_info.distributed` | TIMESTAMP | `data_distribuicao` | Data de Distribuição | Momento da distribuição. Usado como filtro temporal fino |
| `order_info.distribute_on` | STRING | `data_distribuicao_agendada` | Distribuição Agendada | Data agendada para distribuir |
| `order_item_info.*` | STRUCT | - | - | ⚠️ Subcampos não documentados. Confirmar no Databricks antes de usar. |

> Os aliases PT-BR de `order_info.*` foram propostos aqui (não vinham do catálogo original)
> e os tipos ainda não foram confirmados — ajustar quando alguém validar no Databricks.


---

## 5. Receivable Assets (Ativos a Receber)

**Local**: `main.fintech_finance.receivable_assets`

**Descrição**: Ativos a receber (boletos, PIX e faturas) do iFood Office/Benefits. Uma linha por ativo/recebível.

**Particionada por**: `asset_month` (YYYY-MM) - **OBRIGATÓRIA em WHERE**

**Domínio**: `financeiro`

**Multi-tenant**: coluna direta `company_group_id`. Não exige JOIN.

**Filtros padrão**: `deleted = false`.

**Relacionamentos**: `receivable_asset_id` → `company_tax_invoice.receivable_asset_id` · `company_group_id` ← `ifood_benefits_recharges.company_group.id`

**Enums**: o dump do Databricks lista `status` como `PENDING, RECEIVED, CANCELED, EXPIRED`. `OVERDUE` está documentado aqui como possível valor legado — ao filtrar por vencidos, considerar os dois. `STARK_PAY` é tipo válido.

**Colunas disponíveis**: exatamente as listadas abaixo — nenhuma outra.

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `receivable_asset_id` | STRING | `id_ativo_recebivel` | Ativo Recebível | UUID único do ativo |
| `type` | STRING | `tipo_recebivel` | Tipo | BOLETO, INVOICED_BOLETO, PIX, STARK_PAY |
| `status` | STRING | `situacao_recebivel` | Situação | PENDING, RECEIVED, CANCELED, EXPIRED (`OVERDUE` pode aparecer em registros legados) |
| `product_type` | STRING | `tipo_produto_recebivel` | Tipo de Produto | MEAL_VOUCHER, MOBILITY, CULTURE, etc. |
| `company_group_id` | STRING | `company_group_id` | Grupo de Empresas | ID do grupo corporativo |
| `amount` | DOUBLE | `valor_recebivel` | Valor | Valor principal (R$) |
| `interest_amount` | DOUBLE | `valor_juros` | Juros | Valor de juros (R$) |
| `iof_tax_amount` | DOUBLE | `valor_iof` | IOF | Valor de IOF (R$) |
| `due_date` | STRING | `data_vencimento` | Data de Vencimento | Data de vencimento (YYYY-MM-DD) |
| `paid_at` | TIMESTAMP | `data_pagamento` | Data de Pagamento | Timestamp do pagamento |
| `created_at` | TIMESTAMP | `data_criacao_recebivel` | Data de Criação | Timestamp de criação |
| `invoice_internal_number` | STRING | `numero_interno_fatura` | Número Interno | Número interno da fatura |
| `invoice_external_number` | STRING | `numero_externo_fatura` | Número Externo | Número externo da fatura |
| `external_id` | STRING | `id_externo_recebivel` | ID Externo | ID externo |
| `deleted` | BOOLEAN | `deletado_recebivel` | Deletado | Soft delete |


---

## 3. Companies (Empresas)

**Local**: `fintech_companies.companies`

**Descrição**: Master de dados cadastrais das empresas. Centraliza informações de identificação, endereços comerciais, geolocalização, grupo corporativo.

**Volume**: Centenas de milhares | **Última atualização**: 2026-07-22

**Domínio**: transversal — usada por todos os domínios como ponte para o filtro multi-tenant.

**Multi-tenant**: coluna direta `company_group_id`.

**Alias obrigatório**: quando entrar por JOIN, usar o alias `c` (exigido pelo prompt e pelo `sql_validator.py`).

**Filtros padrão**: `deleted = false`. A coluna `test` **existe** na tabela física, mas por decisão do time (2026-08-13) não é documentada nem usada como filtro padrão — relatórios não separam empresa de teste.

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
| `deleted` | BOOLEAN | `deletado_empresa` | Deletado | Soft delete |


---

## 6. Chargeback (Estornos)

**Local**: `main.ifoodoffice_recharge_chargeback.chargeback`

**Descrição**: Estornos (chargebacks) de recargas do iFood Office.

**Domínio**: ⚠️ **conflito a resolver** — `schema_extractor.py` classifica como `recargas`; o `TABLE_RELATIONSHIPS` (`sql_validator.py`) e a descrição de domínios do agente classificam como `financeiro`. Enquanto os dois existirem, o domínio escolhido pelo LLM muda quais validações rodam.

**Multi-tenant**: coluna direta `group_id` — **confirmado que é o UUID do grupo de empresas**, mesmo valor de `companies.company_group_id`. Filtrar `chargeback.group_id = '<uuid>'`. **JOIN com `companies` não é necessário.**

> ⚠️ **Correção pendente no código**: `_has_valid_group_id_filter` (`sql_validator.py:361-370`) só aceita `group_id` puro para `financial_account`/`financial_transaction`, e o `TABLE_RELATIONSHIPS` lista `chargeback` entre as tabelas que exigem JOIN com `companies`. Enquanto isso não mudar, o filtro correto acima é **rejeitado** pela validação.

**Partição obrigatória**: `updated_at` (confirmado que a coluna existe). Confirmar se é de fato a coluna de partição.

**Filtros padrão**: nenhum — esta tabela não tem `deleted` nem `test`.

**Relacionamentos**: `company_id` → `companies.company_id` · `group_id` → grupo corporativo (direto)

**Divergência restante**: a tabela `chargeback_employee`, descrita com 9 campos no `sql_system.md`, não está neste catálogo (pendência aberta).

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
| `updated_at` | STRING | `data_atualizacao` | Data de Atualização | Atualização (ISO 8601). Usar como filtro temporal / partição |
| `origin` | STRING | `origem` | Origem | Origem do estorno: BACKOFFICE ou B2B |
| `created_at` | STRING | `data_criacao` | Data de Criação | Criação (ISO 8601) |


---

## 8. Chargeback Employee (Estorno por Colaborador)

**Local**: `main.ifoodoffice_recharge_chargeback.chargeback_employee` — ⚠️ caminho **inferido** do schema da `chargeback`, ainda não confirmado.

**Descrição**: Detalhe do estorno no nível do colaborador. Uma linha por colaborador dentro de um estorno.

**Domínio**: o mesmo da `chargeback` (ver o conflito registrado na seção 6).

**Multi-tenant**: ⚠️ **não confirmado**. Não há coluna de grupo conhecida nesta tabela. O caminho provável é `INNER JOIN chargeback ch ON chargeback_employee.chargeback_id = ch.id` e filtro em `ch.group_id`. **Confirmar antes de liberar esta tabela para o agente.**

**Partição obrigatória**: não confirmada.

**Filtros padrão**: não confirmados (não se sabe se tem `deleted`/`test`).

**Relacionamentos**: `chargeback_id` → `chargeback.id` · `employee_id` → `employee.id`

**Privacidade**: ⚠️ diferente de `employee`, aqui `employee_name` e `tax_id` (CPF) aparecem **sem sufixo `_hash`**. Confirmar se são dados em claro antes de expor em relatório — isso muda o tratamento de LGPD do CSV.

### Colunas Principais

> ⚠️ Lista herdada do `sql_system.md` antigo e **não conferida coluna a coluna** no Databricks.
> Os tipos e os aliases PT-BR abaixo foram propostos aqui, não vieram do catálogo original.

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `chargeback_id` | STRING | `id_estorno` | Estorno (ID) | FK para `chargeback.id` |
| `chargeback_employee_status` | STRING | `situacao_estorno_colaborador` | Situação | Status do estorno para aquele colaborador |
| `employee_id` | STRING | `id_colaborador` | Colaborador | UUID do colaborador |
| `employee_name` | STRING | `nome_colaborador` | Nome do Colaborador | Nome do colaborador (ver nota de privacidade) |
| `provider` | STRING | `saldo` | Saldo | Provedor/saldo utilizado |
| `reason` | STRING | `motivo` | Motivo | Motivo: rescisão, valor indevido, solicitação indevida |
| `tax_id` | STRING | `cpf_colaborador` | CPF | CPF do colaborador (ver nota de privacidade) |
| `total_recharged_value` | DOUBLE | `valor_total_recarregado` | Valor Recarregado | Valor recarregado |
| `total_requested_value` | DOUBLE | `valor_total_solicitado` | Valor Solicitado | Valor solicitado |

---

## 9. Company Tax Invoice (Notas Fiscais)

**Local**: `main.ifoodoffice_invoice_service.company_tax_invoice`

**Descrição**: Notas fiscais (NF-e/NFS-e) emitidas para empresas clientes.

**Domínio**: `financeiro`

**Multi-tenant**: coluna direta `group_id` — **confirmado que é o UUID do grupo de empresas**. Filtrar `company_tax_invoice.group_id = '<uuid>'`. **JOIN com `companies` não é necessário** (segue útil quando o relatório precisar do nome da empresa).

> ⚠️ **Correção pendente no código**: mesma do `chargeback` — `_has_valid_group_id_filter` não reconhece `group_id` puro para esta tabela.

**Partição obrigatória**: nenhuma documentada.

**Filtros padrão**: `deleted = false`.

**Relacionamentos**: `receivable_asset_id` → `receivable_assets.receivable_asset_id` · `company_id` → `companies.company_id`

**Atenção**: `numero_titulo` é o nome **físico** da coluna (já em português) — não é alias. Usar `numero_titulo AS numero_titulo`.

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição |
|--------|------|-------------|----------|-----------|
| `id` | STRING | `id_nota_fiscal` | Nota Fiscal (ID) | UUID da nota |
| `company_id` | STRING | `id_empresa_nota` | Empresa | UUID da empresa |
| `company_cnpj` | STRING | `cnpj_empresa_nota` | CNPJ | CNPJ (14 dígitos) |
| `group_id` | STRING | `id_grupo_nota` | Grupo | UUID do grupo |
| `receivable_asset_id` | STRING | `id_ativo_recebivel_nota` | Ativo Recebível | FK para receivable_assets |
| `numero_titulo` | STRING | `numero_titulo` | Número do Título | Número do título/boleto |
| `tax_invoice_status` | STRING | `situacao_nota_fiscal` | Situação | PENDING, AVAILABLE |
| `tax_invoice_url` | STRING | `url_nota_fiscal` | URL | URL para download |
| `product_type` | STRING | `tipo_produto_nota` | Tipo de Produto | Tipo de produto |
| `amount` | DOUBLE | `valor_nota` | Valor | Valor em R$ |
| `deleted` | BOOLEAN | `deletado_nota` | Deletado | Soft delete |
| `created_at` | STRING | `data_criacao_nota` | Data de Criação | Criação |

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
| `id` | STRING | `id_conta_financeira_conta` | Conta Financeira (ID) | UUID único da conta financeira da empresa cliente. Chave primária. |
| `group_id` | STRING | `id_grupo_conta` | Grupo | UUID do grupo corporativo da empresa. **Usar para filtros multi-tenant.** |
| `product_type` | STRING | `tipo_produto_conta` | Tipo de Produto | Produto ao qual a conta está vinculada (MEAL_VOUCHER, FOOD_VOUCHER, MOBILITY_VOUCHER, etc.). |
| `type` | STRING | `tipo_conta` | Tipo | Tipo da conta financeira. |
| `origin` | STRING | `origem` | Origem | Origem de criação da conta financeira. |
| `test` | BOOLEAN | `teste_conta` | Teste | Flag de dados de teste. `true` = teste, `false` = produção. |
| `deleted` | BOOLEAN | `deletado_conta` | Deletado | Soft delete. Filtrar `deleted = false`. |
| `created_at` | STRING | `data_criacao_conta` | Data de Criação | Timestamp ISO 8601 de criação da conta. |
| `updated_at` | STRING | `data_atualizacao_conta` | Data de Atualização | Timestamp ISO 8601 da última atualização da conta. |
| `_origin_time` | STRING | `tempo_origem_conta` | Tempo de Origem | Metadado técnico Databricks. Normalmente ignorado em relatórios. |
| `_processing_time` | STRING | `tempo_processamento_conta` | Tempo de Processamento | Metadado técnico Databricks. Normalmente ignorado em relatórios. |
| `_timeid` | STRING | `timeid_conta` | Time ID | Metadado técnico de particionamento. Normalmente ignorado em relatórios. |

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
| `account_id` | STRING | `id_conta_financeira_transacao` | Conta Financeira | FK para `financial_account.id`. |
| `amount` | DOUBLE | `valor_transacao` | Valor | Valor da movimentação (R$). |
| `amount_currency` | STRING | `moeda_valor` | Moeda | Moeda do valor (ex.: BRL). |
| `authorization_id` | STRING | `id_autorizacao` | Autorização | ID da autorização associada à movimentação. |
| `type` | STRING | `tipo_transacao` | Tipo | Tipo da movimentação (entrada, saída, estorno, etc.). |
| `rubric` | STRING | `rubrica` | Rubrica | Rubrica/classificação contábil da movimentação. |
| `justification` | STRING | `justificativa` | Justificativa | Justificativa/descrição da movimentação. |
| `transaction_date` | STRING | `data_transacao` | Data da Transação | Data da movimentação (YYYY-MM-DD). |
| `external_id` | STRING | `id_externo_transacao` | ID Externo | ID externo da movimentação. |
| `idempotence_id` | STRING | `id_idempotencia` | ID de Idempotência | Chave de idempotência da movimentação. |
| `is_synced` | BOOLEAN | `sincronizado` | Sincronizado | Indica se a movimentação foi sincronizada com sistemas externos. |
| `test` | BOOLEAN | `teste_transacao` | Teste | Flag de dados de teste. `true` = teste, `false` = produção. |
| `deleted` | BOOLEAN | `deletado_transacao` | Deletado | Soft delete. Filtrar `deleted = false`. |
| `created_at` | STRING | `data_criacao_transacao` | Data de Criação | Timestamp ISO 8601 de criação. |
| `updated_at` | STRING | `data_atualizacao_transacao` | Data de Atualização | Timestamp ISO 8601 da última atualização. |
| `dt` | DATE | `data` | Data | Data de particionamento (YYYY-MM-DD). |
| `dt_partition` | STRING | `particao_data` | Partição de Data | Partição da tabela. |
| `_origin_time` | STRING | `tempo_origem_transacao` | Tempo de Origem | Metadado técnico Databricks. Normalmente ignorado em relatórios. |
| `_processing_time` | STRING | `tempo_processamento_transacao` | Tempo de Processamento | Metadado técnico Databricks. Normalmente ignorado em relatórios. |
| `_timeid` | STRING | `timeid_transacao` | Time ID | Metadado técnico de particionamento. Normalmente ignorado em relatórios. |

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
> Só `employee` precisa deste caminho. `chargeback` e `company_tax_invoice` já foram
> resolvidas: têm `group_id` próprio (ver abaixo).
```sql
-- employee - unica tabela que precisa de JOIN com companies:
FROM main.ifoodoffice_management.employee e
INNER JOIN fintech_companies.companies c ON e.company_id = c.company_id
WHERE c.company_group_id = '<uuid-do-grupo>'
```

### Via STRUCT (quando company_group está embutido na tabela)
```sql
-- ifood_benefits_recharges - tem company_group STRUCT:
FROM main.fintech_finance.ifood_benefits_recharges
WHERE company_group.id = '<uuid-do-grupo>'  -- ← Acesso direto ao STRUCT
```

### Via Coluna Direta (quando company_group_id é coluna normal)
```sql
-- receivable_assets - tem company_group_id como coluna:
FROM main.fintech_finance.receivable_assets
WHERE company_group_id = '<uuid-do-grupo>'
```

### Via Coluna Direta `group_id` (financial_account, chargeback, company_tax_invoice)
```sql
-- financial_account, chargeback e company_tax_invoice tem group_id como coluna normal.
-- Confirmado: o group_id destas tabelas e o mesmo UUID de companies.company_group_id.
FROM main.ifood_benf_transaction_service.financial_account
WHERE group_id = '<uuid-do-grupo>'

FROM main.ifoodoffice_recharge_chargeback.chargeback
WHERE group_id = '<uuid-do-grupo>'

FROM main.ifoodoffice_invoice_service.company_tax_invoice
WHERE group_id = '<uuid-do-grupo>'
```

### Via JOIN com financial_account (financial_transaction)
```sql
-- financial_transaction - precisa de JOIN pela conta financeira:
FROM main.ifood_benf_transaction_service.financial_transaction ft
INNER JOIN main.ifood_benf_transaction_service.financial_account fa
  ON ft.account_id = fa.id
WHERE fa.group_id = '<uuid-do-grupo>'
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

## ⏳ PENDÊNCIAS — a confirmar no Databricks

Itens que este catálogo **não** consegue resolver sozinho. Enquanto estiverem abertos, a
validação de colunas herda o erro deles. Cada um vira uma correção no `sql_system.md`, no
`sql_validator.py` ou aqui — nunca uma invenção do LLM.

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

### Resolvidas

| Pendência | Resolução |
|-----------|-----------|
| `employee` tem `employee_id`/`employee_name`? | **Não existem.** São `id` e `name_hash`. Invenção do prompt, removida do `sql_system.md`. |
| `ifood_benefits_recharges` tem `deleted`? | **Não existe** (nem `test`). Filtrar `r.deleted = false` quebra a query — removido dos exemplos do prompt. |
| `ifood_benefits_recharges` tem `order_item_id`/`order_status`/`order_info`? | **Existem.** O catálogo é que estava incompleto — as três foram adicionadas à seção 4. |
| `update_date` existe em `ifood_benefits_recharges`? | **Existe**, junto com `update_month`. Adicionada ao catálogo; tipo e papel de partição ainda a confirmar (pendência 1). |
| O `group_id` de `chargeback` é o UUID do grupo? | **Sim.** Filtro direto `ch.group_id = '<uuid>'`; JOIN com `companies` deixa de ser obrigatório. Gera correção no `sql_validator.py`. |
| `chargeback` tem `origin` e `updated_at`? | **As duas existem.** Adicionadas ao catálogo; `updated_at` é o filtro temporal/partição. |
| O `group_id` de `company_tax_invoice` é o UUID do grupo? | **Sim.** Filtro direto; JOIN com `companies` vira opcional (só para dados cadastrais da empresa). |
| `chargeback_employee` existe? | **Existe.** Documentada na seção 8 por inferência, marcada como não liberada até confirmarem caminho, colunas e multi-tenant. |
| `mv_employee_config`, `anticipation`, `anticipation_receivable` existem? | **Nenhuma existe.** Saem do `TABLE_TO_DOMAIN` e do `TABLE_RELATIONSHIPS` (ver correções de código). |
| `companies` tem `test`? | **Existe** (dump do Databricks). Decisão: não documentar nem filtrar por ela. |
| `receivable_assets`: `EXPIRED` ou `OVERDUE`? `STARK_PAY` existe? | Dump lista **`EXPIRED`**; `OVERDUE` fica documentado como possível legado. **`STARK_PAY` existe.** |
| Oferecer os campos `_hash` de `employee` ao usuário? | **Manter como está.** Decisão de produto: seguem oferecidos como "Nome"/"Email"/"CPF"/"Telefone", entregando SHA-256. Registrado na seção 7 como comportamento aceito. |

---

*Documentação atualizada em 2026-07-22 para suportar agente gerador de relatórios B2B do iFood Benefits.*
