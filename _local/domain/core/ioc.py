"""IoC local — substitui `domain.core.ioc` do projeto principal."""

from domain.core.logger import Logger

_logger: Logger | None = None


def get_logger() -> Logger:
    """Devolve o logger único do processo."""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


def set_logger(logger: Logger) -> None:
    """Permite o harness trocar o logger (ex.: modo silencioso)."""
    global _logger
    _logger = logger
