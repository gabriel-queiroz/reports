"""Validações legadas por string.

A segurança do SQL — statement, tabelas, filtro de tenant e coluna de saída —
está no `sql_guard`, que trabalha na AST. O que continua aqui é o que a fase 3
do `PLANO.md` vai aposentar (validação de alias e de campos da pergunta).
"""

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
# FILTRO MULTI-TENANT (group_id)
# ============================================================================
# A validação e a injeção do filtro mudaram para o `sql_guard`, que trabalha na
# AST. O que sobrou aqui é o campo citado no texto do prompt.

GROUP_ID_FIELD_MAPPING = {
    "colaboradores": "companies.company_group_id",
    "recargas": "companies.company_group_id",
    "financeiro": "companies.company_group_id",
}


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

