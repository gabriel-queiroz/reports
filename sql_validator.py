"""O que sobrou da validação por string.

A validação do SQL — statement, tabelas, colunas, chaves de JOIN, filtro de
tenant e coluna de saída — está toda no `sql_guard`, que trabalha na AST e lê o
catálogo. Este módulo guarda apenas o tipo de erro que o resto do código já
trata e o campo de grupo citado no texto do prompt.
"""


class InvalidFieldsError(Exception):
    """Erro quando campos mencionados não existem na documentação.

    Legado: nada mais levanta. A fase 5 do `PLANO.md` remove o último `except`
    que ainda escuta por ele.
    """


class QueryNotAllowedError(Exception):
    """Erro quando a query não atende requisitos de segurança multi-tenant.

    É a base de `SqlGuardError` — quem já capturava este tipo continua
    capturando tudo que o guard levanta.
    """


# Campo de grupo citado na instrução de segurança do prompt de geração de SQL.
# O filtro de verdade é montado pelo `sql_guard` a partir do catálogo, tabela a
# tabela; aqui é só o texto que o LLM lê.
GROUP_ID_FIELD_MAPPING = {
    "colaboradores": "companies.company_group_id",
    "recargas": "companies.company_group_id",
    "financeiro": "companies.company_group_id",
}
