"""O catálogo é a fonte da verdade — estes testes travam a leitura dele.

A regra multi-tenant de cada tabela é lida da prosa do `schema.md`. Isso é bom
(não existe cópia da regra no código) e tem um custo: se alguém reescrever a
linha `**Multi-tenant**` de um jeito não reconhecido, a tabela sai da allowlist
e some das consultas. Estes testes fazem esse acidente falhar aqui, em CI, e não
em produção.
"""

import pytest

from domain.agents.reports_b2b.catalog import (
    DIRECT,
    JOIN,
    STRUCT,
    UNSUPPORTED,
    allowed_tables,
    find_table,
    load_catalog,
)
from domain.agents.reports_b2b.schema_extractor import extract_tables_by_domain

# (tabela, estratégia, coluna de grupo, tabela de apoio)
REGRAS_ESPERADAS = [
    ("employee", JOIN, "company_group_id", "companies"),
    ("ifood_benefits_recharges", STRUCT, "company_group.id", None),
    ("receivable_assets", DIRECT, "company_group_id", None),
    ("companies", DIRECT, "company_group_id", None),
    ("chargeback", DIRECT, "group_id", None),
    ("company_tax_invoice", DIRECT, "group_id", None),
    ("financial_account", DIRECT, "group_id", None),
    ("financial_transaction", JOIN, "group_id", "financial_account"),
    ("chargeback_employee", UNSUPPORTED, None, None),
]


@pytest.mark.parametrize("nome,estrategia,coluna,apoio", REGRAS_ESPERADAS)
def test_regra_multi_tenant_de_cada_tabela(nome, estrategia, coluna, apoio):
    regra = load_catalog()[nome].tenant

    assert regra.strategy == estrategia
    if estrategia == JOIN:
        assert regra.join_table == apoio
        assert regra.join_column == coluna
    else:
        assert regra.column == coluna


def test_allowlist_exclui_apenas_o_que_o_catalogo_nao_confirma():
    assert set(allowed_tables()) == {
        nome for nome, estrategia, _, _ in REGRAS_ESPERADAS if estrategia != UNSUPPORTED
    }


def test_caminho_completo_de_cada_tabela():
    caminhos = {nome: tabela.path for nome, tabela in load_catalog().items()}

    assert caminhos["employee"] == "main.ifoodoffice_management.employee"
    assert caminhos["companies"] == "fintech_companies.companies"
    assert caminhos["chargeback"] == (
        "main.ifoodoffice_recharge_chargeback.chargeback"
    )


def test_colunas_e_aliases_sao_lidos():
    chargeback = load_catalog()["chargeback"]

    assert "group_id" in chargeback.column_names
    assert "id_estorno" in chargeback.aliases

    recargas = load_catalog()["ifood_benefits_recharges"]
    # os campos de STRUCT entram com o caminho completo
    assert "company_group.id" in recargas.column_names
    assert "order_info.payment_method" in recargas.column_names


def test_resolucao_de_referencia_por_sufixo():
    assert find_table("main.ifoodoffice_management.employee").name == "employee"
    assert find_table("employee").name == "employee"
    assert find_table("fintech_companies.companies").name == "companies"
    assert find_table("outro.employee") is None
    assert find_table("chargeback_employee") is None
    assert find_table("") is None


def test_dominios_do_prompt_continuam_saindo_do_mesmo_catalogo():
    """`schema_extractor` e `catalog` leem o mesmo arquivo — e concordam."""
    por_dominio = extract_tables_by_domain()

    assert por_dominio["colaboradores"] == [
        "main.ifoodoffice_management.employee",
        "fintech_companies.companies",
    ]
    assert por_dominio["recargas"] == [
        "main.fintech_finance.ifood_benefits_recharges",
        "fintech_companies.companies",
    ]
    assert set(por_dominio["financeiro"]) == {
        "main.fintech_finance.receivable_assets",
        "main.ifoodoffice_recharge_chargeback.chargeback",
        "main.ifoodoffice_invoice_service.company_tax_invoice",
        "main.ifood_benf_transaction_service.financial_account",
        "main.ifood_benf_transaction_service.financial_transaction",
        "fintech_companies.companies",
    }
