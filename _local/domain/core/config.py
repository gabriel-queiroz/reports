"""Config local — substitui `domain.core.config` do projeto principal.

Só existe para o `reports_service.generate_reports` conseguir importar `settings`.
Por padrão vem vazio: sem URL configurada, a chamada ao Reports Service falha cedo
e com mensagem clara, em vez de tentar bater num endpoint inexistente.
"""

import os


class _Settings:
    @property
    def reports_service_api_url(self) -> str:
        return os.getenv("REPORTS_SERVICE_API_URL", "")

    @property
    def requester_token(self) -> str:
        return os.getenv("REQUESTER_TOKEN", "")


settings = _Settings()
