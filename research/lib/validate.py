"""Validação de `data/raw/` — o que o dado tem de errado, contado e visível.

Três verificações obrigatórias (ADR 0005 §2), nesta ordem de gravidade:

1. **`ts` estritamente crescente.** Duplicatas exatas são removidas e
   contadas; retrocessos são contados e sinalizados, nunca reordenados em
   silêncio — um tick fora de ordem é sintoma de problema na fonte, e
   ordenar por cima esconde a causa.
2. **`ask >= bid` em toda linha.** Violação é spread negativo, que não existe
   no mundo. Contada e logada.
3. **Contagem de ticks por dia, com gráfico.** É a mais importante das três e
   a única que precisa de figura: um buraco de dois dias dentro de um bloco
   in-sample contamina o resultado em silêncio, e nenhuma estatística
   agregada o revela.

Nada aqui corrige o dado. `raw/` é imutável (ADR 0005 §2); este módulo
descreve, e quem decide o que fazer com o defeito é a camada seguinte.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# Abaixo disso um dia é suspeito o bastante para entrar no relatório.
# Não é um limiar de aprovação — é um limiar de ATENÇÃO. Um pregão normal de
# XAUUSD tem ordens de magnitude mais ticks que isto; qualquer coisa abaixo é
# meio-feriado, falha de coleta ou buraco na fonte, e os três precisam ser
# olhados por um humano antes de o dia entrar num bloco in-sample.
THIN_DAY_TICKS = 1_000


@dataclass
class ValidationReport:
    """Resultado da validação. Serializa para markdown; não é decorativo."""

    source: str
    rows: int = 0
    ts_first: pd.Timestamp | None = None
    ts_last: pd.Timestamp | None = None

    exact_duplicates: int = 0
    ts_duplicates: int = 0
    ts_backwards: int = 0
    ask_below_bid: int = 0
    non_positive_price: int = 0

    days_covered: int = 0
    days_missing: list[str] = field(default_factory=list)
    thin_days: list[tuple[str, int]] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        """Nenhum defeito estrutural. Dias finos NÃO desqualificam sozinhos."""
        return (
            self.ts_backwards == 0
            and self.ask_below_bid == 0
            and self.non_positive_price == 0
            and not self.days_missing
        )


def _weekdays_between(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """Dias úteis no intervalo.

    O mercado de ouro não negocia no sábado e abre domingo à noite (CLAUDE.md
    §10.6). Sábado ausente é normal e não é buraco; domingo tem sessão parcial
    e é contado à parte de um dia útil cheio.
    """
    return pd.bdate_range(start.normalize(), end.normalize(), freq="C", weekmask="Mon Tue Wed Thu Fri")


def ticks_per_day(frame: pd.DataFrame) -> pd.Series:
    """Contagem de ticks por dia UTC, indexada por data."""
    if frame.empty:
        return pd.Series(dtype="int64")
    counts = frame.groupby(frame["ts"].dt.date).size()
    counts.index = pd.to_datetime(counts.index)
    return counts.sort_index()


def validate(frame: pd.DataFrame, source: str = "raw") -> ValidationReport:
    """Roda as três verificações e devolve o relatório.

    Não modifica `frame`. As duplicatas exatas são *contadas* aqui; removê-las
    é decisão de quem escreve `curated/`.
    """
    rep = ValidationReport(source=source, rows=len(frame))
    if frame.empty:
        log.warning("%s: frame vazio", source)
        return rep

    rep.ts_first = frame["ts"].iloc[0]
    rep.ts_last = frame["ts"].iloc[-1]

    # --- 1. monotonicidade e duplicatas -------------------------------------
    rep.exact_duplicates = int(frame.duplicated().sum())
    rep.ts_duplicates = int(frame["ts"].duplicated().sum())

    # Retrocesso é diferente de empate: dois ticks no mesmo milissegundo são
    # normais num feed de tick; um tick que anda para trás não é.
    deltas = frame["ts"].diff()
    rep.ts_backwards = int((deltas < pd.Timedelta(0)).sum())

    # --- 2. sanidade de preço ------------------------------------------------
    rep.ask_below_bid = int((frame["ask"] < frame["bid"]).sum())
    rep.non_positive_price = int(((frame["bid"] <= 0) | (frame["ask"] <= 0)).sum())

    # --- 3. cobertura por dia -------------------------------------------------
    counts = ticks_per_day(frame)
    rep.days_covered = len(counts)

    if len(counts) > 1:
        expected = _weekdays_between(counts.index[0], counts.index[-1])
        present = set(counts.index.normalize())
        rep.days_missing = [
            d.strftime("%Y-%m-%d") for d in expected if d not in present
        ]

    rep.thin_days = [
        (d.strftime("%Y-%m-%d"), int(n)) for d, n in counts.items() if n < THIN_DAY_TICKS
    ]

    return rep


def validate_raw_tree(
    raw_root: str | Path, source: str | None = None
) -> tuple[ValidationReport, pd.DataFrame]:
    """Valida `raw/` inteira sem carregá-la inteira na memória.

    Percorre partição por partição e acumula. A única verificação que exige
    cuidado entre partições é a monotonicidade: um retrocesso na FRONTEIRA
    entre dois meses só aparece se o último `ts` do mês anterior for carregado
    para o mês seguinte — por isso `carry_last`.
    """
    from .loader import read_raw  # import tardio: evita ciclo na importação

    raw_root = Path(raw_root)
    partitions = sorted(raw_root.glob("year=*/month=*"))
    if not partitions:
        raise FileNotFoundError(f"nenhuma partição em {raw_root}")

    combined = ValidationReport(source=source or str(raw_root))
    all_counts: list[pd.Series] = []
    carry_last: pd.Timestamp | None = None

    for part in partitions:
        year = int(part.parent.name.split("=")[1])
        month = int(part.name.split("=")[1])
        frame = read_raw(raw_root, year=year, month=month)

        rep = validate(frame, source=f"{year}-{month:02d}")

        combined.rows += rep.rows
        combined.exact_duplicates += rep.exact_duplicates
        combined.ts_duplicates += rep.ts_duplicates
        combined.ts_backwards += rep.ts_backwards
        combined.ask_below_bid += rep.ask_below_bid
        combined.non_positive_price += rep.non_positive_price

        # Retrocesso na costura entre partições.
        if carry_last is not None and not frame.empty:
            if frame["ts"].iloc[0] < carry_last:
                combined.ts_backwards += 1
        if not frame.empty:
            carry_last = frame["ts"].iloc[-1]
            if combined.ts_first is None:
                combined.ts_first = frame["ts"].iloc[0]
            combined.ts_last = frame["ts"].iloc[-1]

        all_counts.append(ticks_per_day(frame))
        log.info("validado %s: %d linhas", part, rep.rows)

    counts = pd.concat(all_counts).groupby(level=0).sum().sort_index()
    combined.days_covered = len(counts)

    if len(counts) > 1:
        expected = _weekdays_between(counts.index[0], counts.index[-1])
        present = set(counts.index.normalize())
        combined.days_missing = [
            d.strftime("%Y-%m-%d") for d in expected if d not in present
        ]

    combined.thin_days = [
        (d.strftime("%Y-%m-%d"), int(n)) for d, n in counts.items() if n < THIN_DAY_TICKS
    ]

    return combined, counts.rename("ticks").to_frame()


def plot_ticks_per_day(
    frame: pd.DataFrame, out_png: str | Path, *, title: str = "Ticks por dia"
) -> Path:
    """Gráfico de ticks/dia a partir do frame completo."""
    return plot_ticks_per_day_from_counts(
        ticks_per_day(frame).rename("ticks").to_frame(), out_png, title=title
    )


def plot_ticks_per_day_from_counts(
    counts_df: pd.DataFrame, out_png: str | Path, *, title: str = "Ticks por dia"
) -> Path:
    """Gráfico de ticks/dia. É o artefato que torna um buraco visível.

    Recebe a contagem já agregada, e não o frame de ticks, para que `raw/`
    inteira nunca precise caber na memória de uma vez.

    Importa matplotlib aqui dentro, e não no topo, para que `validate()` possa
    rodar em ambiente sem backend gráfico.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    counts = counts_df["ticks"]
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.bar(counts.index, counts.values, width=1.0, linewidth=0)
    ax.axhline(THIN_DAY_TICKS, linestyle="--", linewidth=1, color="crimson")
    ax.set_title(title)
    ax.set_ylabel("ticks")
    ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)

    return out_png


def report_markdown(rep: ValidationReport, png_rel: str | None = None) -> str:
    """Relatório em markdown, pronto para `reports/`."""
    lines: list[str] = [
        f"# Validação de `raw/` — {rep.source}",
        "",
        "> Gerado por `research/lib/validate.py`. Nenhum número aqui é estimativa:",
        "> todos saíram da leitura do dado.",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Linhas | {rep.rows:,} |",
        f"| Primeiro tick | {rep.ts_first} |",
        f"| Último tick | {rep.ts_last} |",
        f"| Dias com dado | {rep.days_covered} |",
        "",
        "## Defeitos",
        "",
        "| Verificação | Ocorrências | Gravidade |",
        "|---|---|---|",
        f"| Linhas idênticas duplicadas | {rep.exact_duplicates:,} | remover em `curated/` |",
        f"| `ts` repetido (mesmo ms) | {rep.ts_duplicates:,} | normal em feed de tick |",
        f"| `ts` retrocedendo | {rep.ts_backwards:,} | **estrutural** |",
        f"| `ask < bid` | {rep.ask_below_bid:,} | **estrutural** |",
        f"| Preço ≤ 0 | {rep.non_positive_price:,} | **estrutural** |",
        "",
    ]

    if rep.days_missing:
        lines += [
            f"## Dias úteis sem nenhum tick — {len(rep.days_missing)}",
            "",
            "Cada um destes é um buraco. Um buraco dentro de um bloco in-sample contamina",
            "o resultado em silêncio; a decisão de excluir o período ou o bloco é de quem",
            "monta o teste, mas precisa ser tomada sabendo que o buraco existe.",
            "",
            "```",
            *rep.days_missing[:60],
            *(["..."] if len(rep.days_missing) > 60 else []),
            "```",
            "",
        ]
    else:
        lines += ["## Dias úteis sem nenhum tick", "", "Nenhum.", ""]

    if rep.thin_days:
        lines += [
            f"## Dias com menos de {THIN_DAY_TICKS:,} ticks — {len(rep.thin_days)}",
            "",
            "Não são necessariamente defeito: meio-feriado do ouro é real. Mas nenhum",
            "deles deve entrar num bloco de teste sem ter sido olhado.",
            "",
            "| Dia | Ticks |",
            "|---|---|",
            *[f"| {d} | {n:,} |" for d, n in rep.thin_days[:60]],
            "",
        ]

    if png_rel:
        lines += ["## Ticks por dia", "", f"![ticks por dia]({png_rel})", ""]

    lines += [
        "## Veredicto",
        "",
        (
            "**Sem defeito estrutural.**"
            if rep.clean
            else "**Defeito estrutural presente — ver tabela acima.**"
        ),
        "",
        "Ausência de defeito estrutural não é atestado de qualidade do dado. Diz apenas",
        "que o arquivo é internamente consistente; se ele representa o mercado é outra",
        "pergunta, e quem responde é a medição do gap de fonte (`CLAUDE.md` §11.2).",
    ]

    return "\n".join(lines)
