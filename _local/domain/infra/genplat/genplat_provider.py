"""GenplatProvider local — substitui `domain.infra.genplat.genplat_provider`.

Faz o que o GenPlat faz para este agente: entrega um LLM com a interface
`.with_structured_output(Schema).invoke(mensagens)`. A diferença é que aqui a chamada
vai direto para a API da OpenAI, sem o gateway interno.

Dois modos:

- **openai** — usado quando existe `OPENAI_API_KEY` no ambiente. Devolve um `ChatOpenAI`
  de verdade, então o caminho exercitado é idêntico ao de produção.
- **fake** — sem chave. Devolve um SQL roteirizado (via `GENPLAT_FAKE_SQL` ou o texto
  passado ao provider). Serve para exercitar prompt + validadores offline e é a base do
  golden set: você fixa o SQL de entrada e observa o que os validadores fazem com ele.

O agente não sabe a diferença — a interface é a mesma nos dois casos.
"""

import os
from typing import Any

SQL_FAKE_PADRAO = (
    "SELECT c.company_name AS nome_empresa, "
    "c.company_group_id AS company_group_id, "
    "COUNT(*) AS total_colaboradores "
    "FROM main.ifoodoffice_management.employee e "
    "INNER JOIN fintech_companies.companies c ON e.company_id = c.company_id "
    "WHERE e.deleted = false "
    "GROUP BY c.company_name, c.company_group_id "
    "LIMIT 1000"
)


class _EstruturadoFake:
    """Imita o retorno de `llm.with_structured_output(Schema)`."""

    def __init__(self, schema: Any, sql: str, logger: Any = None):
        self._schema = schema
        self._sql = sql
        self._logger = logger

    def invoke(self, mensagens: Any) -> Any:
        if self._logger:
            self._logger.log_information(
                "LLM fake respondendo",
                mensagens=len(mensagens) if hasattr(mensagens, "__len__") else "?",
                sql_length=len(self._sql),
            )
        # o schema é um pydantic BaseModel com um único campo `sql`
        return self._schema(sql=self._sql)


class _LLMFake:
    def __init__(self, sql: str, logger: Any = None, **kwargs: Any):
        self._sql = sql
        self._logger = logger
        self.kwargs = kwargs

    def with_structured_output(self, schema: Any) -> _EstruturadoFake:
        return _EstruturadoFake(schema, self._sql, self._logger)


class GenplatProvider:
    """Stand-in do provider do projeto principal.

    Args:
        logger: logger do agente (opcional)
        sql_fake: SQL devolvido no modo fake. Se ausente, usa `GENPLAT_FAKE_SQL`
            do ambiente e, por fim, `SQL_FAKE_PADRAO`.
        forcar_fake: ignora a `OPENAI_API_KEY` e usa sempre o modo fake.
    """

    def __init__(
        self,
        logger: Any = None,
        sql_fake: str | None = None,
        forcar_fake: bool = False,
    ):
        self.logger = logger
        self.sql_fake = sql_fake or os.getenv("GENPLAT_FAKE_SQL") or SQL_FAKE_PADRAO
        self.forcar_fake = forcar_fake

    @property
    def modo(self) -> str:
        if self.forcar_fake or not os.getenv("OPENAI_API_KEY"):
            return "fake"
        return "openai"

    def create_llm(
        self,
        model: str = "gpt-4.1",
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> Any:
        if self.modo == "fake":
            if self.logger:
                self.logger.log_information(
                    "LLM em modo fake (sem OPENAI_API_KEY)", model=model
                )
            return _LLMFake(self.sql_fake, self.logger, model=model)

        from langchain_openai import ChatOpenAI

        if self.logger:
            self.logger.log_information(
                "LLM OpenAI criado",
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
