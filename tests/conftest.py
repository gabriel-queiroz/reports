"""Resolução de imports para os testes.

Os testes importam o agente pelo caminho de produção
(`domain.agents.reports_b2b.…`). No projeto principal o pacote `domain` já
existe e o bloco abaixo não faz nada — este arquivo pode ir junto sem ajuste.

Fora dele, cai na camada de `_local/`, que é o andaime descartável.
"""

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent

try:  # projeto principal: o `domain` real está instalado
    import domain  # noqa: F401
except ModuleNotFoundError:  # repositório isolado: usa o andaime de `_local/`
    sys.path.insert(0, str(_RAIZ / "_local"))
    sys.path.insert(0, str(_RAIZ))
