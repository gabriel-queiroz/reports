"""Logger local — substitui `domain.core.logger` do projeto principal.

Imprime no stdout em vez de mandar para o observability da empresa. A interface
(`log_information`, `log_warning`, `log_error`) é a mesma que o agente já usa, então
o código do agente não muda.
"""

from typing import Any

_CINZA, _AMARELO, _VERMELHO, _RESET = "\033[90m", "\033[33m", "\033[31m", "\033[0m"


def _formatar(campos: dict[str, Any]) -> str:
    partes = []
    for chave, valor in campos.items():
        texto = str(valor)
        if len(texto) > 220:
            texto = texto[:220] + "…"
        partes.append(f"{chave}={texto}")
    return " ".join(partes)


class Logger:
    """Stand-in do Logger do projeto principal."""

    def __init__(self, verboso: bool = True):
        self.verboso = verboso

    def log_information(self, mensagem: str, **campos: Any) -> None:
        if self.verboso:
            print(f"{_CINZA}  · {mensagem}{_RESET} {_formatar(campos)}".rstrip())

    def log_warning(self, mensagem: str, **campos: Any) -> None:
        print(f"{_AMARELO}  ! {mensagem}{_RESET} {_formatar(campos)}".rstrip())

    def log_error(self, mensagem: str, erro: Exception | None = None, **campos: Any) -> None:
        detalhe = f" erro={erro}" if erro else ""
        print(f"{_VERMELHO}  ✗ {mensagem}{detalhe}{_RESET} {_formatar(campos)}".rstrip())
