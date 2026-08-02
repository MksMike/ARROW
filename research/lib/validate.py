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

# Piso absoluto: abaixo disso o dia é quase vazio, qualquer que seja o dia da
# semana. Pega o caso degenerado.
THIN_DAY_TICKS = 1_000

# Piso RELATIVO, e é este que faz o trabalho.
#
# Um limiar absoluto não serve para detectar pregão quebrado, porque o domingo
# tem sessão parcial (abre 22:00 UTC) e roda em ~7 mil ticks contra ~215 mil de
# um pregão. Qualquer limiar absoluto alto o bastante para flagrar um pregão
# defeituoso condena todo domingo; qualquer um baixo o bastante para poupar o
# domingo deixa passar um pregão com 5 mil ticks — que é justamente o buraco de
# coleta que esta verificação existe para pegar.
#
# A comparação, portanto, é contra a mediana do MESMO dia da semana. Domingo
# compete com domingo, quinta com quinta.
THIN_DAY_FRACTION = 0.20


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
    # (data, ticks, mediana do mesmo dia da semana, motivo)
    thin_days: list[tuple[str, int, int, str]] = field(default_factory=list)

    @property
    def days_missing_unexplained(self) -> list[str]:
        """Dias úteis ausentes que o calendário de feriados NÃO explica."""
        from .market_calendar import classify_days

        _, unknown = classify_days(self.days_missing)
        return unknown

    @property
    def thin_days_unexplained(self) -> list[tuple[str, int, int, str]]:
        """Dias magros que o calendário de feriados NÃO explica."""
        from .market_calendar import is_holiday

        return [t for t in self.thin_days if not is_holiday(pd.Timestamp(t[0]))]

    @property
    def coverage_explained(self) -> bool:
        """Toda ausência e todo dia magro têm causa de calendário.

        É a pergunta que separa feriado de buraco de coleta. Enquanto isto for
        verdade, nenhum dia do dataset está sem explicação; quando deixar de
        ser, o dia que sobrou é o que precisa ser investigado antes de entrar
        num bloco in-sample.
        """
        return not self.days_missing_unexplained and not self.thin_days_unexplained

    @property
    def clean(self) -> bool:
        """Nenhum defeito **estrutural**.

        Defeito estrutural é o que não pode existir num feed correto: tick
        andando para trás no tempo, spread negativo, preço não positivo.

        Dia útil ausente e dia fino **não** entram aqui, e a distinção não é
        frouxidão. O ouro fecha em feriado de mercado — Sexta-feira Santa,
        Natal, Ano-Novo — e nesses dias a ausência de tick é o dado correto.
        Tratar isso como defeito faz o validador gritar em todo dataset
        íntegro, e um alarme que sempre dispara deixa de ser lido. Os dois
        ficam no relatório como observação de cobertura, para julgamento
        humano antes de o período entrar num bloco de teste.
        """
        return (
            self.ts_backwards == 0
            and self.ask_below_bid == 0
            and self.non_positive_price == 0
        )


def _weekdays_between(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """Dias úteis no intervalo.

    O mercado de ouro não negocia no sábado e abre domingo à noite (CLAUDE.md
    §10.6). Sábado ausente é normal e não é buraco; domingo tem sessão parcial
    e é contado à parte de um dia útil cheio.
    """
    return pd.bdate_range(start.normalize(), end.normalize(), freq="C", weekmask="Mon Tue Wed Thu Fri")


def find_thin_days(counts: pd.Series) -> list[tuple[str, int, int, str]]:
    """Dias anormalmente magros, comparados contra o próprio dia da semana.

    Devolve `(data, ticks, mediana do mesmo dia da semana, motivo)`.

    A mediana por dia da semana é o único denominador honesto aqui: o mercado
    de ouro tem sessão parcial no domingo e sessão cheia de segunda a sexta, e
    misturar os dois num limiar único ou cega a verificação ou a faz gritar
    todo domingo. Ver `THIN_DAY_FRACTION`.
    """
    if counts.empty:
        return []

    medians = counts.groupby(counts.index.dayofweek).median()
    out: list[tuple[str, int, int, str]] = []

    for day, n in counts.items():
        med = float(medians.get(day.dayofweek, 0.0))
        n = int(n)

        if n < THIN_DAY_TICKS:
            motivo = f"abaixo do piso absoluto de {THIN_DAY_TICKS:,}"
        elif med > 0 and n < med * THIN_DAY_FRACTION:
            pct = 100.0 * n / med
            motivo = f"{pct:.0f}% da mediana de {day.day_name()}"
        else:
            continue

        out.append((day.strftime("%Y-%m-%d"), n, int(med), motivo))

    return out


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

    rep.thin_days = find_thin_days(counts)

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

    combined.thin_days = find_thin_days(counts)

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

    from .market_calendar import holidays_between

    cal = {}
    if rep.ts_first is not None and rep.ts_last is not None:
        cal = holidays_between(rep.ts_first, rep.ts_last)

    lines += [
        "## Cobertura",
        "",
        f"Feriados de mercado previstos pelo calendário no período: **{len(cal)}**.",
        "Serão removidos de `curated/` (ADR 0006). `raw/` os mantém — é imutável.",
        "",
    ]

    if rep.days_missing:
        known = [d for d in rep.days_missing if d not in rep.days_missing_unexplained]
        lines += [
            f"### {len(rep.days_missing)} dia(s) útil(eis) sem nenhum tick",
            "",
            f"- **{len(known)}** explicados pelo calendário (fechamento total)",
            f"- **{len(rep.days_missing_unexplained)}** sem explicação",
            "",
            "```",
            *[f"{d}  {cal.get(pd.Timestamp(d).date(), 'SEM EXPLICACAO — INVESTIGAR')}"
              for d in rep.days_missing[:60]],
            *(["..."] if len(rep.days_missing) > 60 else []),
            "```",
            "",
        ]

    if rep.thin_days:
        n_unex = len(rep.thin_days_unexplained)
        lines += [
            f"### {len(rep.thin_days)} dia(s) anormalmente magro(s)",
            "",
            f"Abaixo de {THIN_DAY_FRACTION:.0%} da mediana do **mesmo dia da semana**, ou do piso",
            f"absoluto de {THIN_DAY_TICKS:,} ticks. A comparação é por dia da semana porque o",
            "domingo tem sessão parcial e roda uma ordem de grandeza abaixo de um pregão —",
            "um limiar único ou cega a verificação ou condena todo domingo.",
            "",
            f"**{len(rep.thin_days) - n_unex}** explicados pelo calendário, **{n_unex}** sem explicação.",
            "",
            "| Dia | Ticks | Mediana do dia da semana | Motivo | Calendário |",
            "|---|---|---|---|---|",
            *[
                f"| {d} | {n:,} | {m:,} | {r} | "
                f"{cal.get(pd.Timestamp(d).date(), '**SEM EXPLICACAO**')} |"
                for d, n, m, r in rep.thin_days[:60]
            ],
            "",
        ]

    if not rep.days_missing and not rep.thin_days:
        lines += ["Nenhum dia ausente e nenhum dia magro.", ""]

    if not rep.coverage_explained:
        lines += [
            "> **Há dia sem explicação de calendário.** Feriado e buraco de coleta se parecem",
            "> num gráfico de ticks/dia; o calendário separa os dois por declaração, e o que",
            "> sobra é justamente o que precisa ser investigado antes de entrar num bloco",
            "> in-sample. Não excluir automaticamente — isso faria o buraco sumir em silêncio.",
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
        (
            "**Toda ausência tem causa de calendário.**"
            if rep.coverage_explained
            else "**Há ausência sem causa de calendário — investigar antes de usar.**"
        ),
        "",
        "Ausência de defeito estrutural não é atestado de qualidade do dado. Diz apenas",
        "que o arquivo é internamente consistente; se ele representa o mercado é outra",
        "pergunta, e quem responde é a medição do gap de fonte (`CLAUDE.md` §11.2).",
    ]

    return "\n".join(lines)
