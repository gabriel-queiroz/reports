"""Tool for listing available fields for a data domain.

Uses schema.md as the source of truth via LLM extraction to ensure
fields stay synchronized with actual schema documentation.
"""

import logging
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Domains reference for tool input validation
VALID_DOMAINS = Literal["colaboradores", "recargas", "financeiro"]

DOMAIN_MARKERS = {
    "colaboradores": "## 7. Employee (Colaboradores)",
    "recargas": "## 4. iFood Benefits Recharges (Recargas)",
    "financeiro": (
        "## 5. Receivable Assets (Ativos a Receber), "
        "## 6. Chargeback (Estornos), "
        "## 9. Company Tax Invoice (Notas Fiscais)"
    ),
}


def _get_schema_content() -> str:
    """Load schema.md content."""
    schema_path = Path(__file__).parent.parent / "data" / "schema.md"
    try:
        return schema_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error("Failed to load schema.md: %s", e)
        return ""


class ListFieldsInput(BaseModel):
    """Input for the list fields tool."""

    domain: VALID_DOMAINS = Field(description="The data domain to list fields for.")


@tool(args_schema=ListFieldsInput)
def list_fields(domain: VALID_DOMAINS) -> str:
    """Lists available fields for a specific data domain.

    Returns the schema documentation so the ReAct agent can extract the
    user-facing fields using the ``Exibição`` column.
    """
    logger.info("list_fields called for domain: %s", domain)

    schema_content = _get_schema_content()
    if not schema_content:
        return (
            f"Erro ao carregar schema. Não foi possível listar os campos para {domain}."
        )

    marker = DOMAIN_MARKERS.get(domain, "")

    return f"""Aqui está a documentação do schema para o domínio **{domain}**:

<schema_documentation>
{schema_content}
</schema_documentation>

Use a seção {marker} para montar a lista de campos disponíveis para "{domain}".
Use APENAS a coluna **Exibição** das tabelas (ex.: "Colaborador (ID)", "Nome", "Email").
NÃO use a coluna "Alias PT-BR" nem nomes técnicos de colunas (ex.: id_colaborador, data_criacao)."""
