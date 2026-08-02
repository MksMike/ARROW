"""CLI: Dukascopy CSV → `data/raw/` + relatório de validação em `reports/`.

Uso normal, um CSV anual por vez::

    .venv\\Scripts\\python.exe research\\build_raw.py \\
        --csv data/dukascopy/xauusd-tick-2025-08-01-2026-08-01.csv

Uso para verificar o pipeline sem esperar o download inteiro::

    ... --limit-rows 2000000 --raw-root <caminho temporario>

AVISO: nunca rodar sobre um CSV que ainda está sendo baixado. A última linha
estará truncada, e o erro aparece muito depois, como um tick com preço
impossível no meio de `raw/`.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.lib import validate as V  # noqa: E402
from research.lib.loader import load_csv_to_raw  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", required=True, help="CSV do dukascopy-node")
    ap.add_argument("--raw-root", default=str(REPO / "data" / "raw"))
    ap.add_argument("--reports-dir", default=str(REPO / "reports"))
    ap.add_argument("--chunk-rows", type=int, default=5_000_000)
    ap.add_argument(
        "--limit-rows",
        type=int,
        default=0,
        help="Processar só as N primeiras linhas. Para verificar o pipeline, não para produzir raw/.",
    )
    ap.add_argument("--slug", default=None, help="Nome do relatório em reports/")
    ap.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Revalidar raw/ sem converter nada. Obrigatório ao reprocessar: "
            "write_raw é append-only, então rodar a conversão duas vezes sobre "
            "o mesmo CSV DUPLICA o dado em raw/ em vez de sobrescrever."
        ),
    )
    ap.add_argument(
        "--skip-validate",
        action="store_true",
        help=(
            "Converter sem validar. Para encadear vários CSVs: a validação "
            "percorre raw/ INTEIRA, então rodá-la a cada arquivo revalida o que "
            "já passou. Encadear com --skip-validate e fechar com --validate-only."
        ),
    )
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    log = logging.getLogger("build_raw")

    csv_path = Path(args.csv)
    raw_root = Path(args.raw_root)
    reports = Path(args.reports_dir)
    slug = args.slug or csv_path.stem

    if args.validate_only:
        log.info("validate-only: nada será convertido")
    elif args.limit_rows:
        log.warning(
            "MODO LIMITADO: %d linhas. O resultado NÃO é raw/ de produção.",
            args.limit_rows,
        )
        from research.lib.loader import read_dukascopy_csv, write_raw

        remaining = args.limit_rows
        read = written = parts = 0
        for chunk in read_dukascopy_csv(csv_path, chunk_rows=args.chunk_rows):
            if remaining <= 0:
                break
            chunk = chunk.iloc[:remaining]
            remaining -= len(chunk)
            read += len(chunk)
            parts += write_raw(chunk, raw_root)
            written += len(chunk)
        log.info("%d linhas lidas, %d escritas, %d partições", read, written, parts)
    else:
        stats = load_csv_to_raw(
            csv_path, raw_root, chunk_rows=args.chunk_rows
        )
        log.info("%s", stats)

    if args.skip_validate:
        log.info("skip-validate: conversão feita, raw/ NÃO foi validada")
        return 0

    log.info("validando %s", raw_root)
    rep, counts = V.validate_raw_tree(raw_root, source=slug)

    reports.mkdir(parents=True, exist_ok=True)
    png = reports / f"{slug}-ticks-por-dia.png"
    V.plot_ticks_per_day_from_counts(counts, png, title=f"Ticks por dia — {slug}")

    md = reports / f"{slug}-validacao.md"
    md.write_text(V.report_markdown(rep, png_rel=png.name), encoding="utf-8")

    csv_out = reports / f"{slug}-ticks-por-dia.csv"
    counts.to_csv(csv_out)

    log.info("relatório: %s", md)
    log.info("gráfico:   %s", png)
    log.info("série:     %s", csv_out)

    if not rep.clean:
        log.error("DEFEITO ESTRUTURAL — ver %s", md)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
