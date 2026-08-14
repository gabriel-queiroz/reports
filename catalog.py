"""Leitura estruturada do `data/schema.md` — a fonte da verdade única.

É o único parser do arquivo: o `schema_extractor` monta a lista de tabelas do
prompt a partir daqui, e o `sql_guard` tira daqui a allowlist e a regra
multi-tenant de cada tabela. A alternativa seria um dicionário paralelo no
Python, e toda vez que isso foi feito neste projeto apareceu divergência.

O que é lido de cada seção `## N. Nome (Título)`:

- `**Local**: \\`caminho.completo\\`` → nome e caminho da tabela;
- `**Multi-tenant**: …` → como filtrar por grupo (é a linha que o
  `sql_guard` usa para montar o predicado);
- a tabela markdown de colunas (incluindo os campos de STRUCT).

Se a linha de multi-tenant de uma tabela deixar de ser reconhecida, a tabela
fica **fora** da allowlist — falha fechada, e os testes de catálogo apontam qual
seção mudou.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Estratégias de filtro multi-tenant, na ordem em que aparecem no schema.md.
DIRECT = "direct"  # a própria tabela tem a coluna de grupo
STRUCT = "struct"  # a coluna de grupo está dentro de um STRUCT
JOIN = "join"  # exige JOIN com outra tabela para chegar ao grupo
UNSUPPORTED = "unsupported"  # o catálogo não confirma caminho de grupo

_SECTION_RE = re.compile(r"^## \d+\.\s+(?P<titulo>.+)$", re.MULTILINE)
_LOCAL_RE = re.compile(r"\*\*Local(?:ização)?\*\*:\s*`([^`]+)`")
_TENANT_LINE_RE = re.compile(r"^\*\*Multi-tenant\*\*:\s*(?P<regra>.+)$", re.MULTILINE)

_UNSUPPORTED_RE = re.compile(
    r"não confirmado|não há coluna de grupo conhecida", re.IGNORECASE
)
_STRUCT_RE = re.compile(
    r"STRUCT embutido.*?filtrar direto em\s*`([\w.]+)`", re.IGNORECASE
)
_DIRECT_RE = re.compile(r"coluna direta\s*`([\w.]+)`", re.IGNORECASE)
_JOIN_RE = re.compile(
    r"Exige\s*`INNER JOIN\s+(?P<tabela>[\w.]+)\s+\w+\s+ON\s+[^`]+`"
    r".*?filtro em\s*`\w+\.(?P<coluna>\w+)`",
    re.IGNORECASE | re.DOTALL,
)

_ROW_RE = re.compile(r"^\|(?P<celulas>.+)\|\s*$", re.MULTILINE)

# Seção "📊 RELACIONAMENTOS": `tabela.coluna ──> tabela.coluna`, sempre com o
# nome físico das duas pontas. Linhas terminadas em `(grupo corporativo)` são
# nota de multi-tenant, não relacionamento entre tabelas.
_RELATIONSHIP_RE = re.compile(
    r"^(?P<esq_tabela>\w+)\.(?P<esq_coluna>[\w.]+)\s*──>\s*"
    r"(?P<dir_tabela>\w+)\.(?P<dir_coluna>[\w.]+)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class TenantRule:
    """Como uma tabela é restringida ao grupo de empresas da sessão."""

    strategy: str
    column: str | None = None  # coluna (ou caminho de struct) na própria tabela
    join_table: str | None = None  # nome curto da tabela de apoio
    join_column: str | None = None  # coluna de grupo na tabela de apoio

    @property
    def is_usable(self) -> bool:
        return self.strategy != UNSUPPORTED


@dataclass(frozen=True)
class Column:
    """Uma coluna do catálogo. `name` pode ser um caminho de struct (`a.b`)."""

    name: str
    type: str
    alias: str  # Alias PT-BR obrigatório na saída
    display: str  # Rótulo mostrado ao usuário


@dataclass(frozen=True)
class Table:
    """Uma tabela documentada no catálogo."""

    name: str  # employee
    path: str  # main.ifoodoffice_management.employee
    title: str  # "Employee (Colaboradores)"
    tenant: TenantRule
    columns: tuple[Column, ...]

    @property
    def path_parts(self) -> tuple[str, ...]:
        return tuple(part.lower() for part in self.path.split("."))

    @property
    def column_names(self) -> frozenset[str]:
        return frozenset(column.name.lower() for column in self.columns)

    @property
    def aliases(self) -> frozenset[str]:
        return frozenset(
            column.alias.lower() for column in self.columns if column.alias
        )

    def has_column(self, name: str) -> bool:
        return name.lower() in self.column_names

    def column_for_alias(self, alias: str) -> Column | None:
        """A coluna física por trás de um Alias PT-BR (`id_estorno` → `id`)."""
        for column in self.columns:
            if column.alias.lower() == alias.lower():
                return column
        return None


def schema_path() -> Path:
    """Caminho do `schema.md` — mesmo arquivo usado para montar o prompt."""
    return Path(__file__).parent / "data" / "schema.md"


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Table]:
    """Devolve o catálogo indexado pelo nome curto da tabela.

    O resultado é memoizado: o `schema.md` não muda em runtime.
    """
    return _parse_catalog(schema_path().read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def allowed_tables() -> dict[str, Table]:
    """Tabelas que o agente pode consultar.

    É o catálogo menos as tabelas sem caminho multi-tenant confirmado — hoje
    só a `chargeback_employee`, que o próprio `schema.md` marca como
    "confirmar antes de liberar para o agente".
    """
    return {
        name: table for name, table in load_catalog().items() if table.tenant.is_usable
    }


@lru_cache(maxsize=1)
def relationships() -> frozenset[frozenset[tuple[str, str]]]:
    """Chaves de JOIN declaradas no catálogo, como pares sem direção.

    Cada elemento é `{("employee", "company_id"), ("companies", "company_id")}`.
    É o que permite dizer que um `ON` liga as tabelas por onde o catálogo manda
    ligar — e não por uma coluna inventada.
    """
    content = schema_path().read_text(encoding="utf-8")
    return frozenset(
        frozenset(
            {
                (match.group("esq_tabela"), match.group("esq_coluna")),
                (match.group("dir_tabela"), match.group("dir_coluna")),
            }
        )
        for match in _RELATIONSHIP_RE.finditer(content)
    )


def is_declared_join(left: tuple[str, str], right: tuple[str, str]) -> bool:
    """O par `(tabela, coluna)` × `(tabela, coluna)` está no catálogo?"""
    return frozenset({left, right}) in relationships()


def declared_joins_between(first: str, second: str) -> list[str]:
    """Chaves de JOIN declaradas entre duas tabelas, prontas para a mensagem.

    A ordem segue a dos argumentos, para o erro sair na mesma ordem em que as
    tabelas aparecem na query.
    """
    ligacoes = []
    for par in relationships():
        if {tabela for tabela, _ in par} != {first, second}:
            continue
        esquerda = next(ponta for ponta in par if ponta[0] == first)
        direita = next(ponta for ponta in par if ponta[0] == second)
        ligacoes.append(f"{esquerda[0]}.{esquerda[1]} = {direita[0]}.{direita[1]}")
    return sorted(ligacoes)


def find_table(reference: str) -> Table | None:
    """Resolve uma referência de tabela do SQL contra o catálogo.

    Aceita o caminho completo (`main.ifoodoffice_management.employee`), o
    caminho parcial (`fintech_companies.companies`) ou o nome curto
    (`employee`) — desde que seja **sufixo** de um caminho documentado. Assim
    `outro_catalogo.employee` não passa por `employee`.
    """
    parts = tuple(part.lower() for part in reference.split(".") if part)
    if not parts:
        return None

    for table in allowed_tables().values():
        if table.path_parts[-len(parts) :] == parts:
            return table
    return None


# ------------------------------------------------------------------ parsing --


def _parse_catalog(content: str) -> dict[str, Table]:
    tables: dict[str, Table] = {}

    for section_title, section in _iter_sections(content):
        local = _LOCAL_RE.search(section)
        if not local:
            continue  # seções de texto (relacionamentos, filtros, tipos...)

        path = local.group(1).strip()
        name = path.split(".")[-1]
        tables[name] = Table(
            name=name,
            path=path,
            title=section_title,
            tenant=_parse_tenant_rule(section),
            columns=tuple(_parse_columns(section)),
        )

    return tables


def _iter_sections(content: str):
    """Fatia o documento nas seções `## N. Título`."""
    matches = list(_SECTION_RE.finditer(content))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        yield match.group("titulo").strip(), content[match.end() : end]


def _parse_tenant_rule(section: str) -> TenantRule:
    """Traduz a linha `**Multi-tenant**` em regra executável.

    O que não for reconhecido vira `UNSUPPORTED` — a tabela sai da allowlist em
    vez de entrar com um filtro adivinhado.
    """
    line = _TENANT_LINE_RE.search(section)
    if not line:
        return TenantRule(UNSUPPORTED)

    regra = line.group("regra")

    if _UNSUPPORTED_RE.search(regra):
        return TenantRule(UNSUPPORTED)

    struct = _STRUCT_RE.search(regra)
    if struct:
        return TenantRule(STRUCT, column=struct.group(1))

    direct = _DIRECT_RE.search(regra)
    if direct:
        return TenantRule(DIRECT, column=direct.group(1))

    join = _JOIN_RE.search(regra)
    if join:
        return TenantRule(
            JOIN,
            join_table=join.group("tabela").split(".")[-1],
            join_column=join.group("coluna"),
        )

    return TenantRule(UNSUPPORTED)


def _parse_columns(section: str):
    """Lê as linhas das tabelas markdown de colunas da seção.

    Cobre tanto "Colunas Principais" quanto o bloco de campos de STRUCT: as
    duas têm o mesmo formato `| Coluna | Tipo | Alias PT-BR | Exibição | …`.
    """
    seen: set[str] = set()

    for row in _ROW_RE.finditer(section):
        cells = [cell.strip() for cell in row.group("celulas").split("|")]
        if len(cells) < 4:
            continue

        name = cells[0].strip("`").strip()
        # pula cabeçalho e separador da tabela markdown
        if not name or name.lower() == "coluna" or set(name) <= {"-", ":"}:
            continue
        if not re.fullmatch(r"[\w.]+", name) or name in seen:
            continue

        seen.add(name)
        yield Column(
            name=name,
            type=cells[1].strip("`").strip(),
            alias=cells[2].strip("`").strip(),
            display=cells[3].strip(),
        )
