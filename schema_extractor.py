"""Extrai domínios e tabelas do schema.md - fonte de verdade única."""

import re
from pathlib import Path
from typing import Dict, List

# Mapeamento de nomes de tabelas no schema para domínios
TABLE_TO_DOMAIN = {
    "employee": "colaboradores",
    "ifood_benefits_recharges": "recargas",
    # chargeback é financeiro (estornos), alinhado ao TABLE_RELATIONSHIPS do
    # sql_validator e à descrição de domínios do agente
    "chargeback": "financeiro",
    "company_tax_invoice": "financeiro",
    "receivable_assets": "financeiro",
    "financial_account": "financeiro",
    "financial_transaction": "financeiro",
}


def _get_schema_path() -> Path:
    """Retorna o caminho do schema.md."""
    return Path(__file__).parent / "data" / "schema.md"


def _load_schema_content() -> str:
    """Carrega o conteúdo do schema.md."""
    schema_path = _get_schema_path()
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    return schema_path.read_text(encoding="utf-8")


def extract_tables_by_domain() -> Dict[str, List[str]]:
    """
    Extrai todas as tabelas do schema.md organizadas por domínio.

    Procura por padrões:
    - **Local**: `tabela.caminho`
    - **Localização**: `tabela.caminho`

    Retorna um dict com domínios mapeados para suas tabelas.
    """
    schema_content = _load_schema_content()

    # Inicializar resultado com listas vazias
    result: Dict[str, List[str]] = {
        "colaboradores": [],
        "recargas": [],
        "financeiro": [],
    }

    # Padrão para encontrar Local/Localização com backticks
    # Captura: **Local**: `main.schema.table`
    # ou: **Localização:** `main.schema.table`
    pattern = r"\*\*Local(?:ização)?\*\*:\s*`([^`]+)`"

    for match in re.finditer(pattern, schema_content):
        table_path = match.group(1).strip()

        # Extrair nome da tabela (última parte após o ponto)
        table_name = table_path.split(".")[-1]

        # Determinar o domínio baseado no nome da tabela
        domain = TABLE_TO_DOMAIN.get(table_name)

        if domain and table_path not in result[domain]:
            result[domain].append(table_path)

    # Garantir que fintech_companies.companies está em todos os domínios
    # (necessário para JOIN com company_group_id)
    for domain in result:
        if "fintech_companies.companies" not in result[domain]:
            result[domain].append("fintech_companies.companies")

    return result


def get_tables_for_domain(domain: str) -> str:
    """
    Retorna as tabelas de um domínio como string separada por vírgula.

    Args:
        domain: Nome do domínio (colaboradores, recargas, financeiro)

    Returns:
        String com tabelas separadas por vírgula e espaço
    """
    tables_by_domain = extract_tables_by_domain()
    tables = tables_by_domain.get(domain, [])
    return ", ".join(tables)


def get_all_tables_for_sql_generation() -> str:
    """
    Retorna TODAS as tabelas de todos os domínios como string separada por vírgula.

    Isso permite que o LLM veja todos os relacionamentos entre tabelas
    e gere SQL com JOINs corretos mesmo quando precisar consultar tabelas
    de outros domínios para responder a pergunta completamente.

    Returns:
        String com todas as tabelas separadas por vírgula e espaço
    """
    tables_by_domain = extract_tables_by_domain()

    all_tables = []
    for domain, tables in tables_by_domain.items():
        all_tables.extend(tables)

    # Remove duplicatas mantendo ordem
    unique_tables = []
    for table in all_tables:
        if table not in unique_tables:
            unique_tables.append(table)

    return ", ".join(unique_tables)
