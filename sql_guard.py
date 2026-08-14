"""Guard de AST: a última palavra sobre o SQL que o LLM escreveu.

Substitui a validação por string do `sql_validator`. A diferença que importa
não é de estilo: com AST o filtro de tenant é **injetado na estrutura** e
verificado **na estrutura**, então some a classe inteira de bugs em que o filtro
existia no texto mas não filtrava nada — dentro de um ramo de `OR`, depois do
`GROUP BY`, dentro de uma subquery ou no `ON` de um `LEFT JOIN`.

O que este módulo garante, nesta ordem:

1. o SQL faz parse no dialeto do Databricks;
2. é **um** statement, e é `SELECT` (ou `WITH`/`UNION` de selects);
3. nenhum nó de DML/DDL em lugar nenhum da árvore;
4. toda tabela referenciada está na allowlist do catálogo (`schema.md`);
5. **todo escopo** que lê uma tabela base tem o predicado de tenant no topo do
   `WHERE`, com o UUID da sessão — injetado via AST quando faltar;
6. o `SELECT` externo expõe `company_group_id` como coluna de saída;
7. o SQL devolvido é **regerado a partir da AST**, nunca a string do LLM.

A regra de tenant de cada tabela vem do `catalog`, que a lê do `schema.md`.
Nada aqui é hardcoded por tabela.
"""

import sqlglot
from sqlglot import exp

from domain.agents.reports_b2b.catalog import (
    DIRECT,
    JOIN,
    STRUCT,
    Table,
    allowed_tables,
    find_table,
)
from domain.agents.reports_b2b.guardrails import validate_group_id
from domain.agents.reports_b2b.sql_validator import QueryNotAllowedError

DIALECT = "databricks"

# Nós que não podem aparecer em consulta de relatório, em nenhuma profundidade.
# `Command` é o que o sqlglot devolve para o que ele não sabe analisar — deixar
# passar seria justamente o caso perigoso.
_FORBIDDEN_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.TruncateTable,
    exp.Command,
    exp.Use,
    exp.Set,
    exp.Grant,
)


class SqlGuardError(QueryNotAllowedError):
    """Base dos erros do guard — é um `QueryNotAllowedError` para quem já trata."""


class SqlSyntaxError(SqlGuardError):
    """O SQL não faz parse no dialeto do Databricks."""


class StatementNotAllowedError(SqlGuardError):
    """Mais de um statement, ou statement que não é consulta."""


class TableNotAllowedError(SqlGuardError):
    """Tabela fora do catálogo (ou sem caminho multi-tenant confirmado)."""


class TenantFilterError(SqlGuardError):
    """Não há como amarrar o escopo ao grupo da sessão."""


class OutputColumnError(SqlGuardError):
    """Falta a coluna de saída `company_group_id`."""


def guard_query(sql: str, group_id: str) -> str:
    """Valida, amarra ao tenant e devolve o SQL regerado a partir da AST.

    Args:
        sql: SQL como o LLM escreveu.
        group_id: UUID do grupo da sessão (revalidado aqui).

    Returns:
        SQL equivalente, gerado a partir da AST, com o filtro de tenant
        garantido em todo escopo que lê tabela base.

    Raises:
        SqlGuardError: qualquer violação — todas são `QueryNotAllowedError`.
    """
    group_id = validate_group_id(group_id)

    root = _parse_single_query(sql)
    _reject_forbidden_nodes(root)
    _check_tables_are_allowed(root)

    for select in root.find_all(exp.Select):
        _enforce_tenant_scope(select, group_id)

    _check_group_column_in_output(root)

    return root.sql(dialect=DIALECT, comments=False)


# ------------------------------------------------------------ 1, 2 e 3: forma --


def _parse_single_query(sql: str):
    """Exige um único statement de leitura."""
    try:
        statements = [stmt for stmt in sqlglot.parse(sql, dialect=DIALECT) if stmt]
    except sqlglot.ParseError as e:
        raise SqlSyntaxError(f"SQL inválido para o Databricks: {e}") from e

    if not statements:
        raise SqlSyntaxError("SQL vazio.")

    if len(statements) > 1:
        raise StatementNotAllowedError(
            f"A query deve ter um único statement; vieram {len(statements)}. "
            "Não use ';' para encadear comandos."
        )

    root = statements[0]
    if not isinstance(root, (exp.Select, exp.SetOperation)):
        raise StatementNotAllowedError(
            f"Só é permitido SELECT (com WITH/UNION); veio "
            f"{type(root).__name__.upper()}."
        )

    return root


def _reject_forbidden_nodes(root) -> None:
    for node in root.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            raise StatementNotAllowedError(
                f"Comando não permitido em consulta de relatório: "
                f"{type(node).__name__.upper()}."
            )


# ---------------------------------------------------------- 4: allowlist --


def _check_tables_are_allowed(root) -> None:
    """Toda tabela referenciada precisa estar no catálogo.

    Nomes de CTE também aparecem como `Table` na AST e são ignorados — eles
    apontam para um `SELECT` que já é validado por conta própria.
    """
    cte_names = {cte.alias_or_name.lower() for cte in root.find_all(exp.CTE)}

    for node in root.find_all(exp.Table):
        reference = _qualified_name(node)
        if reference.lower() in cte_names:
            continue

        if find_table(reference) is None:
            raise TableNotAllowedError(
                f"A tabela `{reference}` não está no catálogo de tabelas "
                f"permitidas. Use uma destas: "
                f"{', '.join(sorted(t.path for t in allowed_tables().values()))}."
            )


def _qualified_name(table: exp.Table) -> str:
    return ".".join(part for part in (table.catalog, table.db, table.name) if part)


# --------------------------------------------------- 5: predicado de tenant --


def _enforce_tenant_scope(select: exp.Select, group_id: str) -> None:
    """Garante o filtro de grupo no `WHERE` deste escopo (mutação in-place).

    Só age em escopos que leem tabela base: um `SELECT` que lê apenas CTE ou
    subquery já está coberto pelo escopo de dentro.
    """
    sources = _base_sources(select)
    if not sources:
        return

    predicate = _tenant_predicate(sources, group_id)
    if predicate is None:
        raise TenantFilterError(_missing_join_message(sources))

    if _has_predicate(select, predicate):
        return

    select.where(predicate, dialect=DIALECT, copy=False)

    # O `where()` do sqlglot conecta com AND no topo (parentizando o que já
    # estava lá). Conferir depois de injetar é barato e fecha a porta para
    # qualquer surpresa do builder.
    if not _has_predicate(select, predicate):  # pragma: no cover - defensivo
        raise TenantFilterError(
            "Não foi possível garantir o filtro de grupo na consulta."
        )


def _base_sources(select: exp.Select) -> list[tuple[Table, str]]:
    """Tabelas do catálogo lidas diretamente por este escopo, com seus aliases."""
    nodes = []

    # sqlglot 30 guarda o FROM em `from_`; versões anteriores, em `from`.
    from_clause = select.args.get("from_") or select.args.get("from")
    if from_clause is not None:
        nodes.append(from_clause.this)
    for join in select.args.get("joins") or []:
        nodes.append(join.this)

    sources = []
    for node in nodes:
        if not isinstance(node, exp.Table):
            continue
        table = find_table(_qualified_name(node))
        if table is not None:
            sources.append((table, node.alias_or_name))
    return sources


def _tenant_predicate(
    sources: list[tuple[Table, str]], group_id: str
) -> exp.EQ | None:
    """Monta `<coluna de grupo> = '<uuid>'` a partir das regras do catálogo.

    Percorre as fontes na ordem em que aparecem (FROM primeiro) e usa a
    primeira que resolve: coluna direta, caminho de STRUCT ou a tabela de apoio
    quando ela também está neste escopo.
    """
    by_name = {table.name: alias for table, alias in sources}

    for table, alias in sources:
        rule = table.tenant

        if rule.strategy in (DIRECT, STRUCT):
            return _equals(f"{alias}.{rule.column}", group_id)

        if rule.strategy == JOIN and rule.join_table in by_name:
            return _equals(f"{by_name[rule.join_table]}.{rule.join_column}", group_id)

    return None


def _equals(column_path: str, group_id: str) -> exp.EQ:
    parts = column_path.split(".")
    keys = ("col", "table", "db", "catalog")
    column = exp.column(**dict(zip(keys, reversed(parts))))
    return exp.EQ(this=column, expression=exp.Literal.string(group_id))


def _has_predicate(select: exp.Select, predicate: exp.EQ) -> bool:
    """Procura o predicado na conjunção de topo do `WHERE`.

    Só conta o que está no topo: um filtro dentro de um ramo de `OR` não
    restringe nada, e é exatamente isso que a validação por regex aceitava.
    """
    where = select.args.get("where")
    if where is None:
        return False

    alvo = predicate.sql(dialect=DIALECT).lower()
    return any(
        conjunct.sql(dialect=DIALECT).lower() == alvo
        for conjunct in _top_level_conjuncts(where.this)
    )


def _top_level_conjuncts(condition: exp.Expression):
    """Decompõe `a AND b AND c`, atravessando parênteses."""
    if isinstance(condition, exp.And):
        yield from _top_level_conjuncts(condition.left)
        yield from _top_level_conjuncts(condition.right)
    elif isinstance(condition, exp.Paren):
        yield from _top_level_conjuncts(condition.this)
    else:
        yield condition


def _missing_join_message(sources: list[tuple[Table, str]]) -> str:
    """Erro acionável: diz qual JOIN falta, com o texto do catálogo."""
    pendentes = [table for table, _ in sources if table.tenant.strategy == JOIN]
    if pendentes:
        table = pendentes[0]
        rule = table.tenant
        return (
            f"A tabela `{table.name}` não tem coluna de grupo: o mesmo SELECT "
            f"precisa de INNER JOIN com `{rule.join_table}` para filtrar por "
            f"`{rule.join_column}`."
        )

    return (
        "Não foi possível determinar por qual coluna filtrar o grupo de "
        "empresas neste SELECT."
    )


# ------------------------------------------- 6: coluna de saída do grupo --


def _check_group_column_in_output(root) -> None:
    """O CSV precisa carregar o grupo: `… AS company_group_id` no SELECT externo."""
    for select in _outermost_selects(root):
        if not any(_is_group_output(item) for item in select.expressions):
            raise OutputColumnError(
                "O SELECT deve expor a coluna de grupo com o alias exato "
                "`company_group_id`, a partir de um campo real da tabela "
                "(ex.: `c.company_group_id AS company_group_id`, "
                "`r.company_group.id AS company_group_id`, "
                "`fa.group_id AS company_group_id`)."
            )


def _outermost_selects(root):
    """Os SELECTs que definem as colunas de saída (os ramos de um UNION)."""
    if isinstance(root, exp.SetOperation):
        yield from _outermost_selects(root.left)
        yield from _outermost_selects(root.right)
    elif isinstance(root, exp.Select):
        yield root


def _is_group_output(item: exp.Expression) -> bool:
    if isinstance(item, exp.Alias):
        return (
            item.alias.lower() == "company_group_id"
            and isinstance(item.this, exp.Column)
        )
    # coluna sem alias já sai com o nome certo
    return isinstance(item, exp.Column) and item.name.lower() == "company_group_id"
