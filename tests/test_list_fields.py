"""Fase 5 — `list_fields` monta a lista do catálogo, em vez de despejar o arquivo."""

import pytest

from domain.agents.reports_b2b.catalog import find_table, load_catalog, schema_path
from domain.agents.reports_b2b.schema_extractor import extract_tables_by_domain
from domain.agents.reports_b2b.tools.list_fields import list_fields

DOMINIOS = ["colaboradores", "recargas", "financeiro"]


def listar(dominio: str) -> str:
    return list_fields.func(dominio)


@pytest.mark.parametrize("dominio", DOMINIOS)
def test_resposta_e_a_lista_de_campos_e_nao_o_schema_inteiro(dominio):
    saida = listar(dominio)
    schema = schema_path().read_text(encoding="utf-8")

    assert len(saida) < len(schema) / 10
    assert "<schema_documentation>" not in saida
    assert "**Local**" not in saida


@pytest.mark.parametrize("dominio", DOMINIOS)
def test_usa_a_coluna_exibicao_e_nao_o_alias_tecnico(dominio):
    saida = listar(dominio)

    assert "- Data de Criação" in saida
    assert "data_criacao" not in saida
    assert "company_group_id" not in saida


def test_financeiro_inclui_conta_e_transacao_financeira():
    """`DOMAIN_MARKERS["financeiro"]` não citava nenhuma das duas."""
    saida = listar("financeiro")

    assert "Financial Account" in saida
    assert "Financial Transaction" in saida
    assert "Company Tax Invoice" in saida
    assert "Receivable Assets" in saida
    assert "Chargeback (Estornos)" in saida


def test_struct_inteiro_nao_e_oferecido_como_campo():
    """O catálogo é explícito: nunca selecionar o struct inteiro."""
    recargas = load_catalog()["ifood_benefits_recharges"]
    structs = [c for c in recargas.columns if c.type.upper() == "STRUCT"]
    assert structs, "o catálogo deveria documentar structs nesta tabela"

    oferecidos = listar("recargas").count("\n- ")
    catalogados = sum(
        1
        for caminho in extract_tables_by_domain()["recargas"]
        for coluna in find_table(caminho).columns
        if coluna.display and coluna.type.upper() != "STRUCT"
    )

    assert oferecidos == catalogados


def test_dominio_sem_catalogo_responde_sem_estourar():
    assert "não há domínio" in listar("inexistente").lower()
