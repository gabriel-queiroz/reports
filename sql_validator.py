"""SQL validation and security checks for reports generation."""

import logging
import re

logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================


class InvalidFieldsError(Exception):
    """Erro quando campos mencionados não existem na documentação."""


class QueryNotAllowedError(Exception):
    """Erro quando a query não atende requisitos de segurança multi-tenant."""


class InvalidAliasUsageError(Exception):
    """Erro quando alias PT-BR é usado como nome de campo real."""


# ============================================================================
# VALIDAÇÃO DE CAMPOS CONTRA DOCUMENTAÇÃO
# ============================================================================


def extract_fields_from_documentation(tables_doc: str, domain: str) -> set[str]:
    """
    Extrai todos os campos disponíveis da documentação para um domínio.

    Args:
        tables_doc: Conteúdo completo de tabelas.md
        domain: Nome do domínio (colaboradores, recargas, financeiro)

    Returns:
        Set com nomes de campos em português (ex: company_id, status_cartao, etc)
    """
    fields = set()

    # Mapear domínios para seções da documentação
    domain_map = {
        "colaboradores": ["## 7. Employee"],
        "recargas": ["## 4. iFood Benefits Recharges", "## 6. Chargeback"],
        "financeiro": [
            "## 9. Company Tax Invoice",
            "## 5. Receivable Assets",
            "## 10. Financial Account",
            "## 11. Financial Transaction",
        ],
    }

    sections = domain_map.get(domain, [])

    for section in sections:
        if section not in tables_doc:
            continue

        # Encontra a seção
        start = tables_doc.find(section)
        if start == -1:
            continue

        # Encontra o fim (próxima seção com #)
        next_hash = tables_doc.find("\n# ", start + 1)
        end = next_hash if next_hash != -1 else len(tables_doc)

        section_content = tables_doc[start:end]

        # Extrai campos das linhas de código (```...```)
        lines = section_content.split("\n")
        in_code_block = False

        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block and line.strip():
                # Tenta extrair campo (primeira coluna antes de espaço/tab)
                parts = line.split()
                if parts and parts[0] and not parts[0].startswith("#"):
                    field = parts[0].strip()
                    # Remove caracteres especiais
                    clean_field = re.sub(r"[^a-zA-Z0-9_\.]", "", field)
                    if clean_field and len(clean_field) > 2:  # Ignore muito curtos
                        fields.add(clean_field)

    return fields


def validate_fields(
    question: str, available_fields: set[str]
) -> tuple[bool, list[str]]:
    """
    Valida se a pergunta menciona apenas campos que existem.

    Args:
        question: Pergunta do usuário
        available_fields: Set de campos válidos

    Returns:
        (válido: bool, campos_inválidos: list)
    """
    # Tenta extrair possíveis nomes de campos da pergunta
    # Procura por padrões como "company_name", "status_cartao", etc
    words = re.findall(r"\b[a-z_]+[a-z0-9_]*\b", question.lower())

    suspicious_fields = [p for p in words if "_" in p or len(p) > 4]

    invalid_fields = [c for c in suspicious_fields if c not in available_fields]

    return len(invalid_fields) == 0, invalid_fields


# ============================================================================
# VALIDAÇÃO DE FILTRO MULTI-TENANT (group_id)
# ============================================================================

# Mapeamento de quais campos de group_id usar para cada domínio
# A restrição é aplicada via WHERE clause no SQL gerado
GROUP_ID_FIELD_MAPPING = {
    "colaboradores": "companies.company_group_id",
    "recargas": "companies.company_group_id",
    "financeiro": "companies.company_group_id",
}


# ============================================================================
# MAPEAMENTO DE RELACIONAMENTOS OBRIGATÓRIOS PARA MULTI-TENANT
# ============================================================================
# Documenta qual padrão de JOIN é necessário para cada domínio
# filtrar por company_group_id
TABLE_RELATIONSHIPS = {
    "colaboradores": {
        "tables": ["employee"],
        "company_filter_table": "fintech_companies.companies",
        "join_field": "company_id",
        "has_embedded_company_group": False,
        "description": (
            "A tabela employee tem company_id mas NÃO tem company_group_id - "
            "requer JOIN com companies"
        ),
    },
    "recargas": {
        "tables": ["ifood_benefits_recharges"],
        "has_embedded_company_group": True,
        "embedded_field": "company_group.id",
        "description": (
            "Tabela ifood_benefits_recharges tem STRUCT company_group "
            "com company_group_id e company_group.name embutidos - "
            "NÃO requer JOIN com companies"
        ),
    },
    "financeiro": {
        # Nenhuma tabela do domínio exige JOIN com companies: chargeback e
        # company_tax_invoice têm group_id próprio (confirmado no catálogo).
        "tables": [],
        "tables_with_direct_group_id": [
            "receivable_assets",
            "financial_account",
            "chargeback",
            "company_tax_invoice",
        ],
        "tables_with_custom_group_join": {
            "financial_transaction": {
                "join_table_key": "financial_account",
                "join_table": "main.ifood_benf_transaction_service.financial_account",
                "join_field": "account_id",
                "join_table_alias": "fa",
                "group_id_column": "group_id",
            },
        },
        "company_filter_table": "fintech_companies.companies",
        "join_field": "company_id",
        "has_embedded_company_group": False,
        "description": (
            "receivable_assets tem company_group_id direto; financial_account, "
            "chargeback e company_tax_invoice têm group_id direto (é o UUID do "
            "grupo); financial_transaction requer JOIN com financial_account."
        ),
    },
}


# Tabelas cuja coluna `group_id` É o UUID do grupo de empresas — confirmado no
# catálogo. Nelas o filtro multi-tenant é direto, sem JOIN com companies.
TABLES_WITH_DIRECT_GROUP_ID = (
    "financial_account",
    "financial_transaction",
    "chargeback",
    "company_tax_invoice",
)


def _references_table(sql: str, table_name: str) -> bool:
    """Verifica se o SQL referencia uma tabela pelo nome (case-insensitive)."""
    return re.search(rf"\b{re.escape(table_name)}\b", sql, re.IGNORECASE) is not None


def validate_mandatory_joins(sql: str, domain: str) -> None:
    """
    Valida que o SQL inclui os JOINs obrigatórios para filtrar por company_group_id.

    Exceções:
    - Se a tabela tem STRUCT company_group embutido (como ifood_benefits_recharges),
      JOIN é OPCIONAL (pode usar company_group.id diretamente)
    - Se é consulta direto em companies (já tem company_group_id nativa)

    Para tabelas sem company_group_id embutido, JOIN é OBRIGATÓRIO com
    fintech_companies.companies para aplicar filtro de segurança multi-tenant.

    Args:
        sql: SQL gerado pelo LLM
        domain: Domínio (colaboradores, recargas, financeiro)

    Raises:
        QueryNotAllowedError: Se JOIN obrigatório estiver faltando
    """
    domain_config = TABLE_RELATIONSHIPS.get(domain)
    if not domain_config:
        return

    # Se a tabela tem company_group STRUCT embutido, JOIN é OPCIONAL
    if domain_config.get("has_embedded_company_group"):
        logger.info(
            "Domain '%s' has embedded company_group STRUCT - JOIN validation skipped",
            domain,
        )
        return

    sql_upper = sql.upper()

    # Se é consulta direto na tabela companies (já tem company_group_id nativa)
    if "FINTECH_COMPANIES.COMPANIES" in sql_upper or (
        sql_upper.startswith("SELECT")
        and "FROM" in sql_upper
        and sql_upper.find("COMPANIES") > sql_upper.find("FROM")
        and sql_upper.find("JOIN") == -1
    ):
        # Verificar se é realmente uma query que começa direto com companies
        from_idx = sql_upper.find("FROM")
        if from_idx != -1:
            after_from = sql_upper[from_idx + 5 :].strip()
            if after_from.startswith("FINTECH_COMPANIES.COMPANIES") or (
                after_from.startswith("COMPANIES") and "JOIN" not in after_from[:100]
            ):
                return

    # Tabelas com company_group_id direto (ex: receivable_assets) não precisam de JOIN
    direct_group_tables = domain_config.get("tables_with_direct_group_id", [])
    if direct_group_tables:
        join_required_tables = domain_config.get("tables", [])
        uses_direct_table = any(
            _references_table(sql, table) for table in direct_group_tables
        )
        uses_join_required_table = any(
            _references_table(sql, table) for table in join_required_tables
        )
        if uses_direct_table and not uses_join_required_table:
            logger.info(
                "Query uses a table with direct company_group_id (%s) - "
                "JOIN validation skipped",
                direct_group_tables,
            )
            return

    # Tabelas que precisam de JOIN intermediário (ex: financial_transaction ->
    # financial_account). Se a query usa uma dessas tabelas e já faz o JOIN com a
    # tabela intermediária, o filtro de group_id será validado depois.
    custom_group_joins = domain_config.get("tables_with_custom_group_join", {})
    if custom_group_joins:
        companies_join_tables = domain_config.get("tables", [])
        for table_name, join_rule in custom_group_joins.items():
            if _references_table(sql, table_name):
                join_table_key = join_rule["join_table_key"]
                if not _references_table(sql, join_table_key):
                    raise QueryNotAllowedError(
                        f"Domínio '{domain}': A query que usa '{table_name}' "
                        f"deve incluir JOIN com "
                        f"{join_rule['join_table']} (alias "
                        f"{join_rule['join_table_alias']}) via "
                        f"{join_rule['join_field']} = {join_rule['join_table_alias']}.id "
                        f"para filtrar por group_id."
                    )

                # Se a query não usa nenhuma tabela que exige JOIN com companies,
                # o JOIN intermediário já é suficiente.
                if not any(_references_table(sql, t) for t in companies_join_tables):
                    logger.info(
                        "Query uses table '%s' with custom group join - "
                        "companies JOIN validation skipped",
                        table_name,
                    )
                    return

    # Para domínios que NÃO têm embedded company_group, validar JOIN com companies
    # Procurar por JOIN com companies
    companies_patterns = [
        "INNER JOIN FINTECH_COMPANIES.COMPANIES",
        "LEFT JOIN FINTECH_COMPANIES.COMPANIES",
        "RIGHT JOIN FINTECH_COMPANIES.COMPANIES",
        "FULL JOIN FINTECH_COMPANIES.COMPANIES",
        "JOIN FINTECH_COMPANIES.COMPANIES",
        "INNER JOIN COMPANIES",
        "LEFT JOIN COMPANIES",
        "RIGHT JOIN COMPANIES",
        "FULL JOIN COMPANIES",
        "JOIN COMPANIES",
    ]

    has_companies_join = any(pattern in sql_upper for pattern in companies_patterns)

    if not has_companies_join:
        join_field = domain_config.get("join_field", "company_id")
        error_msg = (
            f"Domínio '{domain}': A query OBRIGATORIAMENTE deve incluir JOIN com "
            f"fintech_companies.companies para filtrar por company_group_id.\n\n"
            f"Motivo: {domain_config['description']}\n\n"
            f"Padrão obrigatório:\n"
            f"INNER JOIN fintech_companies.companies c ON "
            f"<tabela>.{join_field} = c.company_id\n"
            f"WHERE ... AND c.company_group_id = '{{group_id}}'\n\n"
            f"Não é permitido filtrar por company_group_id sem este JOIN "
            f"porque as tabelas neste domínio não possuem a coluna company_group_id."
        )
        logger.warning("Mandatory JOIN validation failed for domain=%s", domain)
        raise QueryNotAllowedError(error_msg)


def _extract_companies_table_alias(sql: str) -> str:
    """
    Extrai o alias usado na tabela fintech_companies.companies.

    Procura por padrões como:
    - INNER JOIN fintech_companies.companies c ON
    - INNER JOIN fintech_companies.companies AS c ON
    - LEFT JOIN fintech_companies.companies companies ON

    Se não encontrar, retorna 'c' como padrão.

    Args:
        sql: SQL gerado pelo LLM

    Returns:
        O alias encontrado (ex: 'c', 'comp', 'companies') ou 'c' como padrão
    """
    # Padrão: JOIN fintech_companies.companies [AS] <alias>
    # Captura o alias após "fintech_companies.companies"
    # Nota: (?:(?:INNER|LEFT|RIGHT|FULL|CROSS)\s+)? permite join type
    # com whitespace OU nenhum join type
    match = re.search(
        r"(?:(?:INNER|LEFT|RIGHT|FULL|CROSS)\s+)?JOIN\s+fintech_companies\.companies\s+(?:AS\s+)?(\w+)",
        sql,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return "c"


def _has_valid_group_id_filter(sql: str, group_id: str) -> bool:
    """Verifica se a query já tem um filtro de group_id/company_group_id correto."""
    if re.search(
        rf"\b(?:[\w\.]+\.)?company_group_id\s*=\s*'{re.escape(group_id)}'",
        sql,
        flags=re.IGNORECASE,
    ):
        return True

    # `group_id` puro só vale para as tabelas cujo group_id É o UUID do grupo
    if any(
        _references_table(sql, table) for table in TABLES_WITH_DIRECT_GROUP_ID
    ) and re.search(
        rf"\b(?:[\w\.]+\.)?group_id\s*=\s*'{re.escape(group_id)}'",
        sql,
        flags=re.IGNORECASE,
    ):
        return True

    return False


def _financeiro_group_filter_clause(sql: str, group_id: str) -> str:
    """Retorna a cláusula de filtro de group_id correta para o domínio financeiro."""
    if _references_table(sql, "financial_transaction"):
        # financial_transaction precisa de JOIN com financial_account (alias fa)
        return f"fa.group_id = '{group_id}'"

    if _references_table(sql, "financial_account"):
        # financial_account tem group_id direto
        return f"group_id = '{group_id}'"

    if _references_table(sql, "receivable_assets"):
        # receivable_assets tem company_group_id direto
        return f"company_group_id = '{group_id}'"

    if _references_table(sql, "chargeback") or _references_table(
        sql, "company_tax_invoice"
    ):
        # ambas têm group_id direto — o group_id delas é o UUID do grupo
        return f"group_id = '{group_id}'"

    # fallback: filtro via JOIN com companies
    actual_alias = _extract_companies_table_alias(sql)
    return f"{actual_alias}.company_group_id = '{group_id}'"


def validate_group_id_present(
    sql: str, group_id_field: str, group_id: str, domain: str = None
) -> str:
    """
    Valida que o SQL contém o filtro de segurança multi-tenant obrigatório.
    Se faltar a cláusula WHERE, reescreve a query completamente com WHERE.

    Estratégia:
    1. Se domain tem embedded_company_group (como recargas), retorna SQL sem modificar
       (o LLM já deve gerar com r.company_group.id = '{group_id}')
    2. Extrai o alias real usado para fintech_companies.companies
    3. Normaliza o group_id_field para usar o alias correto
    4. Se tem WHERE: injeta AND group_id_filter antes de LIMIT/ORDER BY/OFFSET/fim
    5. Se não tem WHERE: reescreve a query com WHERE clause injetada no lugar correto

    Args:
        sql: SQL gerado pelo LLM
        group_id_field: Nome do campo para filtrar (ex: companies.company_group_id)
        group_id: UUID do grupo de empresa
        domain: Domínio para verificar se tem embedded_company_group

    Returns:
        SQL corrigido com filtro garantidamente presente uma única vez

    Raises:
        QueryNotAllowedError: Se não conseguir injetar o filtro de forma válida
    """
    # Se o domínio tem embedded_company_group, não injetar filtro genérico
    # (o LLM já deve ter gerado com r.company_group.id = '{group_id}')
    if domain:
        domain_config = TABLE_RELATIONSHIPS.get(domain, {})
        if domain_config.get("has_embedded_company_group"):
            logger.info(
                "Domain '%s' has embedded company_group - skipping filter injection",
                domain,
            )
            return sql

    # Se já existe um filtro válido de group_id/company_group_id com o UUID correto,
    # não reescrevemos. Isso preserva filtros diretos de tabelas como
    # receivable_assets (ra.company_group_id) e financial_account (group_id),
    # além do filtro via JOIN já correto.
    if _has_valid_group_id_filter(sql, group_id):
        return sql

    # O domínio financeiro tem estratégias de filtro por tabela.
    if domain == "financeiro":
        filter_clause = _financeiro_group_filter_clause(sql, group_id)
        if re.search(r"\bWHERE\b", sql, re.IGNORECASE):
            return _inject_filter_in_query_with_where(sql, filter_clause)
        return _rewrite_query_with_where(sql, filter_clause, group_id_field, group_id)

    # Demais domínios (ex.: colaboradores): normaliza para o alias de companies.
    actual_alias = _extract_companies_table_alias(sql)

    # Normaliza o group_id_field para usar o alias correto
    # Se o campo era "companies.company_group_id",
    # substitui por "<alias>.company_group_id"
    normalized_group_id_field = group_id_field.replace("companies.", f"{actual_alias}.")

    filter_clause = f"{normalized_group_id_field} = '{group_id}'"

    # Remove ocorrências inválidas de group_id já presentes (com qualquer alias)
    cleaned_sql = re.sub(
        rf"\s*AND\s+[\w\.]+\.company_group_id\s*=\s*'{re.escape(group_id)}'",
        "",
        sql,
        flags=re.IGNORECASE,
    )

    sql_upper_cleaned = cleaned_sql.upper()

    # CASO 1: A query já tem WHERE clause
    if re.search(r"\bWHERE\b", sql_upper_cleaned):
        return _inject_filter_in_query_with_where(cleaned_sql, filter_clause)

    # CASO 2: A query NÃO tem WHERE clause - reescrever completamente
    return _rewrite_query_with_where(
        cleaned_sql, filter_clause, group_id_field, group_id
    )


def _inject_filter_in_query_with_where(sql: str, filter_clause: str) -> str:
    """
    Injeta o filtro AND em uma query que já tem WHERE clause.
    Injeta ANTES de LIMIT/ORDER BY/OFFSET ou no final.
    """
    sql_upper = sql.upper()

    # Procurar pela última ocorrência de LIMIT (em caso de UNION)
    limit_idx = sql_upper.rfind("LIMIT")
    if limit_idx != -1:
        return sql[:limit_idx] + f" AND {filter_clause} " + sql[limit_idx:]

    # Procurar por ORDER BY
    order_idx = sql_upper.rfind("ORDER BY")
    if order_idx != -1:
        return sql[:order_idx] + f" AND {filter_clause} " + sql[order_idx:]

    # Procurar por OFFSET
    offset_idx = sql_upper.rfind("OFFSET")
    if offset_idx != -1:
        return sql[:offset_idx] + f" AND {filter_clause} " + sql[offset_idx:]

    # Procurar por HAVING (para queries com GROUP BY)
    having_idx = sql_upper.rfind("HAVING")
    if having_idx != -1:
        return sql[:having_idx] + f" AND {filter_clause} " + sql[having_idx:]

    # Procurar por GROUP BY
    group_idx = sql_upper.rfind("GROUP BY")
    if group_idx != -1:
        return sql[:group_idx] + f" AND {filter_clause} " + sql[group_idx:]

    # Nenhuma cláusula final - injetar no final
    return sql + f" AND {filter_clause}"


def _rewrite_query_with_where(
    sql: str, filter_clause: str, group_id_field: str, group_id: str
) -> str:
    """
    Reescreve uma query que não tem WHERE clause para incluir WHERE obrigatório.

    Estratégia: encontra o primeiro GROUP BY, ORDER BY, HAVING, LIMIT, OFFSET
    ou usa o final da query, e injeta WHERE lá.
    """
    sql_upper = sql.upper()

    # Encontrar o primeiro ponto de inserção (em ordem de prioridade)
    # Procuramos pelo PRIMEIRO (não último) porque estamos criando WHERE
    keyword_positions = {}

    for keyword in ["GROUP BY", "HAVING", "ORDER BY", "LIMIT", "OFFSET"]:
        idx = sql_upper.find(keyword)
        if idx != -1:
            keyword_positions[keyword] = idx

    # Encontrar a palavra-chave mais próxima (primeira a aparecer)
    if keyword_positions:
        first_keyword = min(keyword_positions, key=keyword_positions.get)
        idx = keyword_positions[first_keyword]
        return sql[:idx] + f" WHERE {filter_clause} " + sql[idx:]
    else:
        # Nenhuma cláusula final - o filtro vai no final
        return sql + f" WHERE {filter_clause}"


# ============================================================================
# VALIDAÇÃO DE ALUCINAÇÃO DE ALIASES PT-BR
# ============================================================================


def get_valid_aliases_for_domain(tables_doc: str, domain: str) -> dict[str, set[str]]:
    """
    Extrai todos os aliases PT-BR válidos da documentação para um domínio.

    Retorna um mapa: { "tabela": {"alias1", "alias2", ...} }

    Args:
        tables_doc: Conteúdo completo de schema.md
        domain: Nome do domínio (colaboradores, recargas, financeiro)

    Returns:
        Dict mapeando tabelas para sets de aliases válidos
    """
    aliases_map = {}

    # Mapeamento de domínios para seções da documentação
    domain_map = {
        "colaboradores": [
            ("## 7. Employee", "employee"),
        ],
        "recargas": [
            ("## 4. iFood Benefits Recharges", "ifood_benefits_recharges"),
            ("## 6. Chargeback", "chargeback"),
            ("## 3. Companies", "companies"),
        ],
        "financeiro": [
            ("## 9. Company Tax Invoice", "company_tax_invoice"),
            ("## 5. Receivable Assets", "receivable_assets"),
            ("## 10. Financial Account", "financial_account"),
            ("## 11. Financial Transaction", "financial_transaction"),
            ("## 6. Chargeback", "chargeback"),
            ("## 3. Companies", "companies"),
        ],
    }

    sections = domain_map.get(domain, [])

    for section_header, table_name in sections:
        if section_header not in tables_doc:
            continue

        # Encontra a seção
        start = tables_doc.find(section_header)
        if start == -1:
            continue

        # Encontra o fim (próxima seção com ##)
        next_section = tables_doc.find("\n## ", start + 1)
        end = next_section if next_section != -1 else len(tables_doc)

        section_content = tables_doc[start:end]

        # Procura pela tabela de colunas com o formato:
        # | Coluna | Tipo | Alias PT-BR | Descrição |
        aliases = set()

        # Procura linhas que começam com | (linhas de tabela markdown)
        for line in section_content.split("\n"):
            line = line.strip()
            # Ignora header e separador da tabela
            if not line.startswith("|") or "---" in line or "Coluna" in line:
                continue

            # Parse da linha: | coluna | tipo | alias | descrição |
            parts = [p.strip() for p in line.split("|")]
            # parts[0] é vazio (antes do primeiro |)
            # parts[1] é coluna, parts[2] é tipo, parts[3] é alias, parts[4] é descrição

            if len(parts) >= 4:
                alias = parts[3]  # Coluna "Alias PT-BR"
                if alias and alias != "-" and "alias" not in alias.lower():
                    # Remove caracteres especiais e adiciona ao set
                    clean_alias = re.sub(r"[^a-zA-Z0-9_]", "", alias).lower()
                    if clean_alias and len(clean_alias) > 2:
                        aliases.add(clean_alias)

        if aliases:
            aliases_map[table_name] = aliases

    return aliases_map


def validate_alias_misuse(sql: str, tables_doc: str, domain: str) -> list[str]:
    """
    Valida se aliases PT-BR estão sendo usados como nomes de campos reais no SQL.

    Detecta os seguintes cenários de erro:
    1. Aliases em SELECT: SELECT id_estorno (sem AS antes)
    2. Aliases em WHERE: WHERE id_estorno = 123
    3. Aliases em JOIN ON: ON ch.id_estorno = ...
    4. Aliases em GROUP BY: GROUP BY id_estorno
    5. Aliases em HAVING: HAVING id_estorno > 10
    6. Aliases em ORDER BY: ORDER BY id_estorno ASC

    Ignora:
    - Aliases dentro de strings (single/double quotes)
    - Aliases dentro de comentários (-- e /* */)
    - Aliases após AS (uso correto)

    Args:
        sql: SQL gerado para validar
        tables_doc: Conteúdo de schema.md com mapeamento de aliases
        domain: Domínio para extrair aliases válidos

    Returns:
        list[str]: Lista de erros encontrados (vazio = OK)
                   Cada erro inclui localização (linha) e contexto

    Raises:
        InvalidAliasUsageError: Se aliases forem usados incorretamente
    """
    errors = []

    # Obter aliases válidos para o domínio
    aliases_map = get_valid_aliases_for_domain(tables_doc, domain)

    if not aliases_map:
        # Nenhum alias válido encontrado para o domínio
        return []

    # Coletar todos os aliases válidos
    all_aliases = set()
    for aliases in aliases_map.values():
        all_aliases.update(aliases)

    if not all_aliases:
        return []

    # Remover strings do SQL para evitar falsos positivos
    sql_cleaned = _remove_strings_and_comments(sql)
    sql_lines = sql_cleaned.split("\n")

    # Para cada alias válido, procurar uso indevido
    for alias in all_aliases:
        # Padrões a verificar (em ordem de importância)
        patterns = [
            # 1. Em SELECT (sem AS antes)
            (r"\bSELECT\b.*\b" + re.escape(alias) + r"\b(?!\s+AS\b)", "SELECT"),
            # 2. Em WHERE
            (r"\bWHERE\b.*\b" + re.escape(alias) + r"\b", "WHERE"),
            # 3. Em JOIN ON
            (r"\bON\b.*\b" + re.escape(alias) + r"\b", "JOIN ON"),
            # 4. Em GROUP BY
            (r"\bGROUP\s+BY\b.*\b" + re.escape(alias) + r"\b", "GROUP BY"),
            # 5. Em HAVING
            (r"\bHAVING\b.*\b" + re.escape(alias) + r"\b", "HAVING"),
            # 6. Em ORDER BY
            (r"\bORDER\s+BY\b.*\b" + re.escape(alias) + r"\b", "ORDER BY"),
        ]

        for pattern, clause_type in patterns:
            for line_num, line in enumerate(sql_lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    # Verificar que não é após AS (uso correto)
                    if not re.search(
                        r"\bAS\s+" + re.escape(alias) + r"\b", line, re.IGNORECASE
                    ):
                        # Extrair contexto (snippet do SQL)
                        snippet = line.strip()[:80]
                        errors.append(
                            f"Alias '{alias}' usado em {clause_type} clause "
                            f"(linha {line_num}): {snippet}..."
                        )

    return errors


def _remove_strings_and_comments(sql: str) -> str:
    """
    Remove strings e comentários do SQL para evitar falsos positivos na validação.

    Remove:
    - Strings entre single quotes (')
    - Strings entre double quotes (")
    - Strings entre backticks (`)
    - Comentários com -- (até fim da linha)
    - Comentários com /* ... */

    Args:
        sql: SQL original

    Returns:
        SQL com strings e comentários removidos
    """
    result = []
    i = 0

    while i < len(sql):
        # Verificar comentário /* ... */
        if i < len(sql) - 1 and sql[i : i + 2] == "/*":
            end = sql.find("*/", i + 2)
            if end != -1:
                result.append(" " * (end + 2 - i))  # Manter espaços
                i = end + 2
            else:
                # Comentário não fechado - remover resto
                result.append(" " * (len(sql) - i))
                break
        # Verificar comentário --
        elif i < len(sql) - 1 and sql[i : i + 2] == "--":
            end = sql.find("\n", i)
            if end != -1:
                result.append(" " * (end - i))
                i = end
            else:
                result.append(" " * (len(sql) - i))
                break
        # Verificar string
        elif sql[i] in ("'", '"', "`"):
            quote = sql[i]
            result.append(" ")  # Substituir abertura de string
            i += 1
            # Procurar fechamento
            while i < len(sql):
                if sql[i] == quote:
                    if i + 1 < len(sql) and sql[i + 1] == quote:
                        # Escape: '' or "" dentro da string
                        result.append("  ")
                        i += 2
                    else:
                        # Fim da string
                        result.append(" ")
                        i += 1
                        break
                else:
                    result.append(" ")
                    i += 1
        else:
            result.append(sql[i])
            i += 1

    return "".join(result)


def validate_company_group_id_in_select(sql: str) -> list[str]:
    """Garante que o SELECT expõe company_group_id como coluna de saída.

    A coluna deve ser proveniente de um campo real da tabela (não de um
    literal/constante), com alias exato ``company_group_id``.

    Args:
        sql: SQL gerado pelo LLM

    Returns:
        Lista de erros (vazia quando a coluna está presente e válida)
    """
    cleaned_sql = _remove_strings_and_comments(sql)

    pattern = re.compile(
        r"\b([A-Za-z][A-Za-z0-9_\.]*)\s+AS\s+company_group_id\b",
        re.IGNORECASE,
    )

    for match in pattern.finditer(cleaned_sql):
        expression = match.group(1)
        if expression.upper() not in {"SELECT", "DISTINCT", "ALL"}:
            return []

    return [
        "SELECT deve incluir a coluna do grupo com alias `company_group_id`, "
        "usando o campo real da tabela. Exemplos: "
        "c.company_group_id AS company_group_id, "
        "r.company_group.id AS company_group_id, "
        "company_group_id AS company_group_id ou "
        "group_id AS company_group_id."
    ]
