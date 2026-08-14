"""Ponte para o código do agente, que fica na raiz do repositório.

O agente importa a si mesmo por caminho absoluto (`domain.agents.reports_b2b.…`),
exatamente como faz no projeto principal. Em vez de copiar os arquivos para cá — o que
criaria duas versões do mesmo código — este pacote aponta o próprio `__path__` para a
raiz do repositório.

Efeito: `domain.agents.reports_b2b.sql_guard` carrega `./sql_guard.py`, sem que
nenhum arquivo do agente precise ser alterado. Quando o agente voltar para o projeto
real, nada aqui vai junto.

Nota: o `__init__.py` da raiz **não** é executado (este arquivo ocupa o lugar dele), o
que evita importar o subgrafo inteiro só para chegar num validador.
"""

from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[4]

__path__ = [str(_RAIZ)]
