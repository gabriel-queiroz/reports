"""Tool for listing available fields for a data domain.

Monta a lista a partir do catálogo (`schema.md`), tabela a tabela, usando a
coluna **Exibição**. Antes esta tool devolvia o `schema.md` **inteiro** a cada
chamada e pedia para o LLM extrair os campos: ~44k caracteres por chamada, e a
lista saía diferente a cada vez.
"""

import logging
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from domain.agents.reports_b2b.catalog import find_table
from domain.agents.reports_b2b.schema_extractor import extract_tables_by_domain

logger = logging.getLogger(__name__)

# Domains reference for tool input validation
VALID_DOMAINS = Literal["colaboradores", "recargas", "financeiro"]

# O STRUCT inteiro nunca é campo de relatório — só os caminhos de dentro dele,
# que já vêm listados como colunas próprias no catálogo.
_TIPOS_NAO_EXIBIVEIS = {"STRUCT"}


class ListFieldsInput(BaseModel):
    """Input for the list fields tool."""

    domain: VALID_DOMAINS = Field(description="The data domain to list fields for.")


@tool(args_schema=ListFieldsInput)
def list_fields(domain: VALID_DOMAINS) -> str:
    """Lists available fields for a specific data domain.

    Returns the user-facing field names (``Exibição`` column) grouped by table.
    """
    logger.info("list_fields called for domain: %s", domain)

    tabelas = extract_tables_by_domain().get(domain, [])
    if not tabelas:
        return f"Não há domínio '{domain}' no catálogo."

    blocos = []
    for caminho in tabelas:
        tabela = find_table(caminho)
        if tabela is None:
            continue

        campos = [
            f"- {coluna.display}"
            for coluna in tabela.columns
            if coluna.display and coluna.type.upper() not in _TIPOS_NAO_EXIBIVEIS
        ]
        if campos:
            blocos.append(f"**{tabela.title}**\n" + "\n".join(campos))

    if not blocos:
        return f"Não há campos catalogados para o domínio '{domain}'."

    return (
        f"Campos disponíveis no domínio **{domain}**:\n\n"
        + "\n\n".join(blocos)
        + "\n\nApresente estes nomes ao usuário exatamente como estão aqui. "
        "Não invente campos e não mostre nomes técnicos de colunas."
    )
