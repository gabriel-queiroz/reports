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

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Uso | Valores |
|--------|------|-------------|----------|-----------|-----|--------|
| `id` | STRING | `id_colaborador` | ID | UUID único do funcionário. Chave primária da tabela. | ✅ Essencial | — |

#### 👤 Dados Pessoais (hasheados por privacidade)
Todos os campos com sufixo `_hash` contêm SHA-256 do valor original. **Não contêm dados sensíveis legíveis.**

> **Decisão registrada:** estes quatro campos continuam sendo oferecidos ao usuário com os
> rótulos atuais ("Nome", "Email", "CPF", "Telefone"). Consequência conhecida e aceita: quem
> pedir esses campos recebe um CSV com os hashes SHA-256, não com os valores legíveis.
> Não é bug — se for para mudar, mexer aqui na coluna Exibição e nos aliases.

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Uso | Valores |
|--------|------|-------------|----------|-----------|-----|--------|
| `name_hash` | STRING | `nome` | Nome | SHA-256 hash do nome completo. Não recuperável, apenas para matching. | Relatórios | — |
| `email_hash` | STRING | `email` | Email | SHA-256 hash do email corporativo. Não recuperável. | Relatórios | — |
| `cpf_hash` | STRING | `cpf` | CPF | SHA-256 hash do CPF. Não recuperável por segurança. | Relatórios | — |
| `phone_number_hash` | STRING | `telefone` | Telefone | SHA-256 hash do telefone. Não recuperável. | Relatórios | — |
| `born_date` | STRING | `data_nascimento` | Data de Nascimento | Data de nascimento em ISO format (YYYY-MM-DD). Pode ser nula. | Opcional | — |

#### 📊 Status e Emprego (situação do colaborador)
Campos que indicam o estado atual do colaborador no sistema.

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Uso | Valores |
|--------|------|-------------|----------|-----------|-----|--------|
| `status` | STRING | `situacao_colaborador` | Situação | Status do colaborador: **ACTIVE** (ativo) ou **INACTIVE** (desligado/removido). Use para filtrar ativos vs. inativos. | ✅ Essencial | ACTIVE, INACTIVE |
| `company_id` | STRING | `id_empresa_colaborador` | Empresa | UUID da empresa/subsidiária onde o colaborador trabalha. **Obrigatório para filtros multi-tenant.** | ✅ Essencial | — |

#### 🔍 Metadata e Auditoria
Campos de controle, datas e flags técnicas.

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Uso | Valores |
|--------|------|-------------|----------|-----------|-----|--------|
| `deleted` | BOOLEAN | `deletado_colaborador` | Deletado | Flag de soft delete. `true` = registro marcado como deletado (lógico, não físico). Sempre filtrar `deleted = false`. | ✅ Filtro | — |
| `test` | BOOLEAN | `teste_colaborador` | Teste | Flag indicando dados de teste. `true` = registro de teste, `false` = produção. Filtrar conforme necessário. | Teste | — |
| `test_mode` | STRING | `modo_teste` | Modo de Teste | Modo de teste técnico (valor informacional). Ignorar em relatórios de produção. | Ignorar | loadtest |
| `created_at` | STRING | `data_criacao_colaborador` | Data de Criação | Timestamp ISO 8601 de quando o colaborador foi criado no sistema. | Auditoria | — |

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

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Valores |
|--------|------|-------------|----------|-----------|--------|
| `order_id` | STRING | `id_pedido` | Pedido | ID do pedido/transação | — |
| `order_item_id` | STRING | `id_item_pedido` | Item do Pedido | ID do item de recarga. É a granularidade desta tabela (uma linha por item) | — |
| `product_key` | STRING | `chave_produto` | Produto | FOOD_VOUCHER, MEAL_VOUCHER, MOBILITY_VOUCHER... | FOOD_VOUCHER, MEAL_VOUCHER (entre outros) |
| `order_status` | STRING | `situacao_pedido` | Situação do Pedido | Status no nível do pedido | DISTRIBUTION_COMPLETE (legado DISTRIBUTED mapeado) |
| `order_item_status` | STRING | `situacao_item_pedido` | Situação do Item | CREATED, DISTRIBUTION_COMPLETE | CREATED, DISTRIBUTION_COMPLETE |
| `amount` | DOUBLE | `valor_recarga` | Valor | Valor da recarga (R$) | — |
| `cashback_amount` | DOUBLE | `valor_cashback` | Cashback | Valor do cashback (R$) | — |
| `employee_id` | STRING | `id_colaborador_recarga` | Colaborador | ID do funcionário | — |
| `update_month` | STRING | `mes_atualizacao` | Mês de Atualização | Mês da atualização (YYYY-MM) | — |
| `update_date` | STRING | `data_atualizacao_recarga` | Data de Atualização | **Coluna de partição** — filtrar sempre que possível. Tipo/formato a confirmar | — |
| `schedule_date` | STRING | `data_agendamento` | Data de Agendamento | Data agendada (YYYY-MM-DD) | — |
| `voucher_group` | STRING | `grupo_voucher` | Grupo do Voucher | Agrupamento de negócio do voucher: **PAT** ou **LIVRE** | PAT, LIVRE |
| `release_month_11_10` | DATE | `mes_ciclo_11_10` | Mês do Ciclo (11→10) | Mês de negócio alternativo, ciclo do dia 11 ao dia 10, usado em cálculo financeiro | — |
| `company_group` | STRUCT | `grupo_empresa` | Grupo de Empresas | {id, name, cnpj} - Dados do grupo corporativo. **Usar para filtrar por group_id diretamente!** | — |
| `company` | STRUCT | `empresa` | Empresa | {id, name, cnpj} - Dados da companhia específica dentro do grupo | — |
| `order_item_info` | STRUCT | `info_item_pedido` | Info do Item | Metadados do item | — |

#### Campos de STRUCT (acessar com ponto — nunca selecionar o struct inteiro)

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Valores |
|--------|------|-------------|----------|-----------|--------|
| `company_group.id` | STRING | `id_grupo_recarga` | Grupo de Empresas | UUID do grupo corporativo. **Usar no filtro multi-tenant.** | — |
| `company_group.name` | STRING | `nome_grupo_empresa_recarga` | Nome do Grupo | Nome do grupo corporativo | — |
| `company_group.cnpj` | STRING | `cnpj_grupo` | CNPJ do Grupo | CNPJ do grupo corporativo | — |
| `company.id` | STRING | `id_empresa_recarga` | Empresa | UUID da empresa dentro do grupo | — |
| `company.name` | STRING | `nome_empresa_recarga` | Nome da Empresa | Nome da empresa | — |
| `company.cnpj` | STRING | `cnpj_empresa_recarga` | CNPJ da Empresa | CNPJ da empresa | — |
| `order_info.payment_method` | STRING | `forma_pagamento` | Forma de Pagamento | Meio de pagamento do pedido | — |
| `order_info.balance_usage` | STRING | `uso_saldo` | Uso de Saldo | Indicação de uso de saldo na recarga | — |
| `order_info.custom_description` | STRING | `descricao_personalizada` | Descrição | Descrição livre informada no pedido | — |
| `order_info.distributed` | TIMESTAMP | `data_distribuicao` | Data de Distribuição | Momento da distribuição. Usado como filtro temporal fino | — |
| `order_info.distribute_on` | STRING | `data_distribuicao_agendada` | Distribuição Agendada | Data agendada para distribuir | — |
| `order_info.order_id` | STRING | `id_pedido_info` | Pedido (info) | ID do pedido dentro do struct. Espelha `order_id` do topo | — |
| `order_info.order_status` | STRING | `situacao_pedido_info` | Situação do Pedido (info) | Status do pedido dentro do struct | — |
| `order_info.company_group_id` | STRING | `id_grupo_info_pedido` | Grupo de Empresas (info) | UUID do grupo. **Segundo caminho de filtro multi-tenant** — o canônico é `company_group.id` | — |
| `order_info.type` | STRING | `tipo_pedido` | Tipo do Pedido | Tipo do pedido de recarga | — |
| `order_info.scheduled` | STRING | `agendado` | Agendado | Indicação de agendamento do pedido | — |
| `order_info.authorization_id` | STRING | `id_autorizacao_pedido` | Autorização | ID da autorização associada ao pedido | — |
| `order_info.pre_eligible` | BOOLEAN | `pre_elegivel` | Pré-elegível | Marcação de pré-elegibilidade | — |
| `order_info.source_system` | STRING | `sistema_origem` | Sistema de Origem | Sistema que originou o pedido | — |
| `order_info.bko_action` | STRING | `acao_backoffice` | Ação de Backoffice | Ação executada via backoffice | — |
| `order_info.created_at` | STRING | `data_criacao_pedido` | Data de Criação do Pedido | Timestamp de criação do pedido | — |
| `order_info.created_by` | STRING | `criado_por` | Criado Por | Usuário que criou o pedido | — |
| `order_info.updated_by` | STRING | `atualizado_por` | Atualizado Por | Usuário da última atualização | — |
| `order_info.deleted` | BOOLEAN | `deletado_pedido` | Deletado (pedido) | Soft delete **dentro do struct**. A tabela não tem `deleted` no topo — se precisar filtrar, é por aqui | — |
| `order_info.test` | BOOLEAN | `teste_pedido` | Teste (pedido) | Flag de teste dentro do struct | — |
| `order_item_info.*` | STRUCT | - | - | ⚠️ Subcampos não documentados. Confirmar no Databricks antes de usar. | — |

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

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Valores |
|--------|------|-------------|----------|-----------|--------|
| `receivable_asset_id` | STRING | `id_ativo_recebivel` | Ativo Recebível | UUID único do ativo | — |
| `type` | STRING | `tipo_recebivel` | Tipo | BOLETO, INVOICED_BOLETO, PIX, STARK_PAY | INVOICED_BOLETO, BOLETO, PIX, STARK_PAY |
| `status` | STRING | `situacao_recebivel` | Situação | PENDING, RECEIVED, CANCELED, EXPIRED (`OVERDUE` pode aparecer em registros legados) | PENDING, RECEIVED, CANCELED, EXPIRED |
| `product_type` | STRING | `tipo_produto_recebivel` | Tipo de Produto | MEAL_VOUCHER, MOBILITY, CULTURE, etc. | MEAL_VOUCHER, MOBILITY_VOUCHER, EDUCATION_VOUCHER, CULTURE_VOUCHER (entre outros) |
| `company_group_id` | STRING | `company_group_id` | Grupo de Empresas | ID do grupo corporativo | — |
| `amount` | DOUBLE | `valor_recebivel` | Valor | Valor principal (R$) | — |
| `interest_amount` | DOUBLE | `valor_juros` | Juros | Valor de juros (R$) | — |
| `iof_tax_amount` | DOUBLE | `valor_iof` | IOF | Valor de IOF (R$) | — |
| `due_date` | STRING | `data_vencimento` | Data de Vencimento | Data de vencimento (YYYY-MM-DD) | — |
| `paid_at` | TIMESTAMP | `data_pagamento` | Data de Pagamento | Timestamp do pagamento | — |
| `created_at` | TIMESTAMP | `data_criacao_recebivel` | Data de Criação | Timestamp de criação | — |
| `invoice_internal_number` | STRING | `numero_interno_fatura` | Número Interno | Número interno da fatura | — |
| `invoice_external_number` | STRING | `numero_externo_fatura` | Número Externo | Número externo da fatura | — |
| `external_id` | STRING | `id_externo_recebivel` | ID Externo | ID externo | — |
| `asset_month` | STRING | `mes_ativo` | Mês do Ativo | **Coluna de partição** (YYYY-MM). Filtrar sempre | — |
| `bank_conciliation_date` | STRING | `data_conciliacao_bancaria` | Data de Conciliação | Data de confirmação/conciliação bancária (YYYY-MM-DD) | — |
| `numero_titulo` | STRING | `numero_titulo_recebivel` | Número do Título | Número externo do título, para identificação do pagamento | — |
| `updated_at` | TIMESTAMP | `data_atualizacao_recebivel` | Data de Atualização | Timestamp da última modificação do registro | — |
| `deleted` | BOOLEAN | `deletado_recebivel` | Deletado | Soft delete | — |


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

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Valores |
|--------|------|-------------|----------|-----------|--------|
| `company_id` | STRING | `id_empresa` | Empresa | UUID único | — |
| `cnpj` | STRING | `cnpj` | CNPJ | CNPJ (14 dígitos) | — |
| `company_name` | STRING | `nome_empresa` | Nome Fantasia | Nome fantasia | — |
| `social_name` | STRING | `razao_social` | Razão Social | Razão social | — |
| `company_group_id` | STRING | `company_group_id` | Grupo de Empresas | UUID do grupo corporativo | — |
| `company_group_name` | STRING | `nome_grupo_empresa` | Nome do Grupo | Nome do grupo | — |
| `card_delivery_type` | STRING | `tipo_entrega_cartao` | Tipo de Entrega | LOTE ou outro | PAP (individual), LOTE (em lote) |
| `is_cardless` | BOOLEAN | `sem_cartao` | Sem Cartão | Operação digital | — |
| `commercial_address` | STRUCT | `endereco_comercial` | Endereço Comercial | Endereço comercial | — |
| `origin` | STRING | `origem_cadastro` | Origem do Cadastro | Sistema que criou o registro: **SALESFORCE**, **SELFSALES** (entre outros) | SALESFORCE, SELFSALES (entre outros) |
| `created_at` | STRING | `data_criacao_empresa` | Data de Criação | Timestamp ISO de criação do registro da empresa | — |
| `updated_at` | STRING | `data_atualizacao_empresa` | Data de Atualização | Timestamp ISO da última atualização | — |
| `deleted` | BOOLEAN | `deletado_empresa` | Deletado | Soft delete | — |


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

> `group_id` é **nulo para empresas sem grupo**. O filtro por grupo nunca casa com nulo, então notas de empresa avulsa não aparecem em relatório por grupo — que é o comportamento esperado do isolamento.

> ⚠️ **Correção pendente no código**: mesma do `chargeback` — `_has_valid_group_id_filter` não reconhece `group_id` puro para esta tabela.

**Partição obrigatória**: nenhuma documentada.

**Filtros padrão**: `deleted = false`.

**Relacionamentos**: `receivable_asset_id` → `receivable_assets.receivable_asset_id` · `company_id` → `companies.company_id`

**Atenção**: `numero_titulo` é o nome **físico** da coluna (já em português) — não é alias. Usar `numero_titulo AS numero_titulo`.

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Valores |
|--------|------|-------------|----------|-----------|--------|
| `id` | STRING | `id_nota_fiscal` | Nota Fiscal (ID) | UUID da nota | — |
| `company_id` | STRING | `id_empresa_nota` | Empresa | UUID da empresa | — |
| `company_cnpj` | STRING | `cnpj_empresa_nota` | CNPJ | CNPJ (14 dígitos) | — |
| `group_id` | STRING | `id_grupo_nota` | Grupo | UUID do grupo | — |
| `receivable_asset_id` | STRING | `id_ativo_recebivel_nota` | Ativo Recebível | FK para receivable_assets | — |
| `numero_titulo` | STRING | `numero_titulo` | Número do Título | Número do título/boleto | — |
| `tax_invoice_status` | STRING | `situacao_nota_fiscal` | Situação | PENDING, AVAILABLE | AVAILABLE, PENDING |
| `tax_invoice_url` | STRING | `url_nota_fiscal` | URL | URL para download | — |
| `product_type` | STRING | `tipo_produto_nota` | Tipo de Produto | Tipo de produto | REWARD_VOUCHER, MEAL_VOUCHER, MOBILITY_VOUCHER, CARD_ISSUE |
| `amount` | DOUBLE | `valor_nota` | Valor | Valor em R$ | — |
| `deleted` | BOOLEAN | `deletado_nota` | Deletado | Soft delete | — |
| `type` | STRING | `tipo_documento_nota` | Tipo de Documento | Classificação do tipo de documento fiscal. Pode ser nulo | — |
| `created_at` | STRING | `data_criacao_nota` | Data de Criação | Criação | — |
| `updated_at` | STRING | `data_atualizacao_nota` | Data de Atualização | Timestamp ISO da última modificação | — |

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

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Valores |
|--------|------|-------------|----------|-----------|--------|
| `id` | STRING | `id_conta_financeira_conta` | Conta Financeira (ID) | UUID único da conta financeira da empresa cliente. Chave primária. | — |
| `group_id` | STRING | `id_grupo_conta` | Grupo | UUID do grupo corporativo da empresa. **Usar para filtros multi-tenant.** | — |
| `product_type` | STRING | `tipo_produto_conta` | Tipo de Produto | Produto ao qual a conta está vinculada (MEAL_VOUCHER, FOOD_VOUCHER, MOBILITY_VOUCHER, etc.). | MEAL_VOUCHER, MOBILITY_VOUCHER, CULTURE_VOUCHER |
| `type` | STRING | `tipo_conta` | Tipo | Tipo da conta financeira. | MAIN |
| `origin` | STRING | `origem` | Origem | Origem de criação da conta financeira. | COMPANY |
| `test` | BOOLEAN | `teste_conta` | Teste | Flag de dados de teste. `true` = teste, `false` = produção. | — |
| `deleted` | BOOLEAN | `deletado_conta` | Deletado | Soft delete. Filtrar `deleted = false`. | — |
| `created_at` | STRING | `data_criacao_conta` | Data de Criação | Timestamp ISO 8601 de criação da conta. | — |
| `updated_at` | STRING | `data_atualizacao_conta` | Data de Atualização | Timestamp ISO 8601 da última atualização da conta. | — |

---

## 11. Financial Transaction (Transação Financeira)

**Local**: `main.ifood_benf_transaction_service.financial_transaction`

**Descrição**: Registro dos dados relativos às movimentações de valor na conta financeira da empresa cliente do iFood Benefícios (B2B). Exemplos: entradas a partir da adição de saldo para consumo em recargas futuras, entradas a partir de estornos de recarga, saídas a partir de distribuições de recargas.

**Frequência**: D-1

**Domínio**: `financeiro`

**Multi-tenant**: não possui coluna de grupo. Exige `INNER JOIN main.ifood_benf_transaction_service.financial_account fa ON financial_transaction.account_id = fa.id` e filtro em `fa.group_id`.

**Partição obrigatória**: nenhuma confirmada. O dump do Databricks não declara partição para esta tabela e não lista as colunas `dt`/`dt_partition` que o catálogo antigo citava. Não filtrar por elas — coluna inexistente quebra a query.

**Filtros padrão**: `deleted = false`, `test = false`.

**Relacionamentos**: `account_id` → `financial_account.id`

### Colunas Principais

| Coluna | Tipo | Alias PT-BR | Exibição | Descrição | Valores |
|--------|------|-------------|----------|-----------|--------|
| `id` | STRING | `id_transacao_financeira` | Transação Financeira (ID) | UUID único da movimentação. Chave primária. | — |
| `account_id` | STRING | `id_conta_financeira_transacao` | Conta Financeira | FK para `financial_account.id`. | — |
| `amount` | DOUBLE | `valor_transacao` | Valor | Valor da movimentação (R$). | — |
| `amount_currency` | STRING | `moeda_valor` | Moeda | Moeda do valor (ex.: BRL). | BRL |
| `authorization_id` | STRING | `id_autorizacao` | Autorização | ID da autorização associada à movimentação. | — |
| `type` | STRING | `tipo_transacao` | Tipo | Tipo da movimentação (entrada, saída, estorno, etc.). | CREDIT, DEBIT |
| `rubric` | STRING | `rubrica` | Rubrica | Rubrica/classificação contábil da movimentação. | DISTRIBUTION, BILLING_PAID, DISTRIBUTION_WALLET |
| `justification` | STRING | `justificativa` | Justificativa | Justificativa/descrição da movimentação. | — |
| `transaction_date` | STRING | `data_transacao` | Data da Transação | Data da movimentação (YYYY-MM-DD). | — |
| `external_id` | STRING | `id_externo_transacao` | ID Externo | ID externo da movimentação. | — |
| `idempotence_id` | STRING | `id_idempotencia` | ID de Idempotência | Chave de idempotência da movimentação. | — |
| `is_synced` | BOOLEAN | `sincronizado` | Sincronizado | Indica se a movimentação foi sincronizada com sistemas externos. | — |
| `test` | BOOLEAN | `teste_transacao` | Teste | Flag de dados de teste. `true` = teste, `false` = produção. | — |
| `deleted` | BOOLEAN | `deletado_transacao` | Deletado | Soft delete. Filtrar `deleted = false`. | — |
| `created_at` | STRING | `data_criacao_transacao` | Data de Criação | Timestamp ISO 8601 de criação. | — |
| `updated_at` | STRING | `data_atualizacao_transacao` | Data de Atualização | Timestamp ISO 8601 da última atualização. | — |

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

> Para `financial_account` e `financial_transaction`, o campo de grupo é `group_id`.
> Use esse campo no filtro e exponha-o com o alias exato `company_group_id` — a coluna
> de saída do grupo usa sempre esse alias, sobrepondo o Alias PT-BR da tabela.

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

*Documentação atualizada em 2026-08-13 para suportar agente gerador de relatórios B2B do iFood Benefits.*
