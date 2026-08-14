"""Camada externa para exercitar o agente de relatórios sem a infra da empresa.

Chama o código real — `_generate_sql_internal` de
`report_generator/tools/generate_query_tool.py` — com a camada `_local/domain` no lugar
do `domain` do projeto principal. Nenhum arquivo do agente é alterado.

Uso:

    .venv/bin/python _local/harness.py "colaboradores ativos por empresa" \\
        --dominio colaboradores

    # alimentando um SQL específico nos validadores (modo fake, sem LLM)
    .venv/bin/python _local/harness.py "qualquer" --dominio financeiro \\
        --sql "SELECT ch.id AS id_estorno ... "

    # com LLM de verdade
    OPENAI_API_KEY=sk-... .venv/bin/python _local/harness.py "..." --dominio recargas

Sem `OPENAI_API_KEY` o provider entra em modo fake e devolve o SQL roteirizado, o que
permite testar prompt + validadores offline.
"""

import argparse
import asyncio
import sys
import traceback
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ / "_local"))  # camada domain local
sys.path.insert(0, str(_RAIZ))

VERDE, VERMELHO, AZUL, CINZA, RESET = (
    "\033[32m",
    "\033[31m",
    "\033[36m",
    "\033[90m",
    "\033[0m",
)

GROUP_ID_EXEMPLO = "550e8400-e29b-41d4-a716-446655440000"


def titulo(texto: str) -> None:
    print(f"\n{AZUL}{'─' * 72}\n{texto}\n{'─' * 72}{RESET}")


def main() -> int:
    p = argparse.ArgumentParser(description="Harness do agente de relatórios B2B")
    p.add_argument("pergunta", help="pergunta do usuário, reescrita e autocontida")
    p.add_argument(
        "--dominio",
        default="colaboradores",
        choices=["colaboradores", "recargas", "financeiro"],
    )
    p.add_argument("--group-id", default=GROUP_ID_EXEMPLO)
    p.add_argument("--sql", help="força este SQL no modo fake (ignora o LLM)")
    p.add_argument("--fake", action="store_true", help="força modo fake mesmo com chave")
    p.add_argument("--mostrar-prompt", action="store_true")
    args = p.parse_args()

    from domain.core.ioc import get_logger
    from domain.infra.genplat.genplat_provider import GenplatProvider

    logger = get_logger()
    provider = GenplatProvider(logger, sql_fake=args.sql, forcar_fake=args.fake)

    titulo(f"ENTRADA  ·  modo do LLM: {provider.modo}")
    print(f"  pergunta : {args.pergunta}")
    print(f"  domínio  : {args.dominio}")
    print(f"  group_id : {args.group_id}")

    # os prompts reais, montados do mesmo jeito que em produção
    from domain.agents.reports_b2b.report_generator.prompts import (
        sql_system_prompt,
        sql_user_prompt,
    )
    from domain.agents.reports_b2b.schema_extractor import (
        get_all_tables_for_sql_generation,
    )
    from domain.agents.reports_b2b.sql_validator import GROUP_ID_FIELD_MAPPING

    campo = GROUP_ID_FIELD_MAPPING.get(args.dominio, "companies.company_group_id")
    sistema = sql_system_prompt(
        restricao_group_id=f"Query MUST filter by {campo} = '{args.group_id}'",
        documentacao_tabelas=(_RAIZ / "data" / "schema.md").read_text(encoding="utf-8"),
        group_id=args.group_id,
    )
    usuario = sql_user_prompt(
        dominio=args.dominio,
        tabelas=get_all_tables_for_sql_generation(),
        pergunta=args.pergunta,
        group_id=args.group_id,
    )

    titulo("PROMPT")
    print(f"  system : {len(sistema):>7} chars")
    print(f"  user   : {len(usuario):>7} chars")
    print(f"  total  : {len(sistema) + len(usuario):>7} chars")
    if args.mostrar_prompt:
        print(f"\n{CINZA}{sistema}\n\n{usuario}{RESET}")

    titulo("GERAÇÃO + VALIDAÇÃO  (fluxo real de _generate_sql_internal)")
    from domain.agents.reports_b2b.report_generator.tools.generate_query_tool import (
        _generate_sql_internal,
    )

    try:
        sql = asyncio.run(
            _generate_sql_internal(args.pergunta, args.dominio, args.group_id, provider)
        )
    except Exception as erro:  # noqa: BLE001 — o harness quer ver qualquer falha
        titulo("RESULTADO")
        print(f"{VERMELHO}  REJEITADO: {type(erro).__name__}{RESET}")
        print(f"\n{CINZA}{traceback.format_exc()}{RESET}")
        return 1

    titulo("RESULTADO")
    print(f"{VERDE}  ACEITO{RESET}  ({len(sql)} chars)\n")
    print(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
