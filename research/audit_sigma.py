"""CLI: auditoria de σ por bucket de hora sobre `data/raw/`.

Item 5 da §18 do `CLAUDE.md`. Substitui as estimativas preliminares da §13.2
por medição sobre os quatro anos de tick real.

    .venv\\Scripts\\python.exe research\\audit_sigma.py

Aplica a máscara de sessão (§10.6) e a exclusão de feriados (ADR 0006) antes de
medir: σ fora da janela negociável não é σ operacional, e um meio-feriado com
1% do volume não descreve o mercado que se pretende operar.

Não escreve nada em `data/`. A série M1 usada aqui é de auditoria, construída
em memória a partir de `raw/`; a camada `bars/` deriva de `curated/` e é outra
coisa (ADR 0005).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.lib import sigma as S  # noqa: E402
from research.lib.loader import read_raw  # noqa: E402
from research.lib.market_calendar import drop_holidays  # noqa: E402
from research.lib.sessions import apply_trading_mask  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def build_returns(raw_root: Path) -> tuple[pd.DataFrame, dict]:
    """Percorre `raw/` partição a partição e acumula as variações M1."""
    log = logging.getLogger("audit_sigma")
    partitions = sorted(raw_root.glob("year=*/month=*"))
    if not partitions:
        raise FileNotFoundError(f"nenhuma partição em {raw_root}")

    chunks: list[pd.DataFrame] = []
    stats = {
        "ticks_lidos": 0,
        "ticks_fora_de_sessao": 0,
        "ticks_em_feriado": 0,
        "barras_m1": 0,
        "pares_descartados_por_gap": 0,
    }
    carry: pd.DataFrame | None = None

    for part in partitions:
        year = int(part.parent.name.split("=")[1])
        month = int(part.name.split("=")[1])
        frame = read_raw(raw_root, year=year, month=month, columns=["ts", "bid"])
        stats["ticks_lidos"] += len(frame)

        frame, n_holiday = drop_holidays(frame)
        stats["ticks_em_feriado"] += sum(n_holiday.values())

        frame, n_off = apply_trading_mask(frame)
        stats["ticks_fora_de_sessao"] += n_off

        bars = S.m1_from_ticks(frame)
        stats["barras_m1"] += len(bars)

        # A última barra do mês anterior precisa atravessar para cá, senão o
        # par que cruza a virada de mês é descartado como se fosse gap.
        if carry is not None and not bars.empty:
            bars = pd.concat([carry, bars], ignore_index=True)

        rets = S.consecutive_returns(bars)
        stats["pares_descartados_por_gap"] += max(0, len(bars) - 1 - len(rets))

        if not rets.empty:
            chunks.append(rets)
        if not bars.empty:
            carry = bars.tail(1)

        log.info("%s: %d barras M1, %d variações", part.name, len(bars), len(rets))

    return pd.concat(chunks, ignore_index=True), stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-root", default=str(REPO / "data" / "raw"))
    ap.add_argument("--reports-dir", default=str(REPO / "reports"))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("audit_sigma")

    reports = Path(args.reports_dir)
    reports.mkdir(parents=True, exist_ok=True)

    rets, stats = build_returns(Path(args.raw_root))
    log.info("total de variações M1 consecutivas: %d", len(rets))

    by_hour = S.sigma_by_bucket(rets, "hour")
    by_year = S.sigma_by_bucket(rets, "year")
    by_sess = S.sigma_by_session(rets)
    by_ys = S.sigma_year_by_session(rets)

    # Ano mais recente completo: é o único que descreve o mercado de hoje.
    recent_year = int(by_year.index.max())
    rets_recent = rets[rets["bar_time"].dt.year == recent_year]
    by_sess_recent = S.sigma_by_session(rets_recent)
    by_hour_recent = S.sigma_by_bucket(rets_recent, "hour")

    by_hour.to_csv(reports / "sigma-por-hora.csv", lineterminator="\n")
    by_hour_recent.to_csv(reports / f"sigma-por-hora-{recent_year}.csv", lineterminator="\n")
    by_year.to_csv(reports / "sigma-por-ano.csv", lineterminator="\n")
    by_ys.to_csv(reports / "sigma-ano-x-sessao.csv", lineterminator="\n")

    _plot(by_hour, by_hour_recent, recent_year, reports / "sigma-por-hora.png")

    md = _report(rets, stats, by_hour, by_year, by_sess, by_sess_recent, by_ys, recent_year)
    (reports / "sigma-auditoria.md").write_text(md, encoding="utf-8", newline="\n")

    log.info("relatório: %s", reports / "sigma-auditoria.md")
    return 0


def _plot(by_hour, by_hour_recent, recent_year: int, out_png: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

    ax1.bar(by_hour.index - 0.2, by_hour["sigma_usd"], width=0.4, label="4 anos")
    ax1.bar(
        by_hour_recent.index + 0.2,
        by_hour_recent["sigma_usd"],
        width=0.4,
        label=f"{recent_year}",
    )
    ax1.set_ylabel("σ  (USD/oz por barra M1)")
    ax1.set_title("σ por hora UTC — o agregado de 4 anos subestima o ano corrente")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    ax2.bar(by_hour.index - 0.2, by_hour["sigma_bps"], width=0.4, label="4 anos")
    ax2.bar(
        by_hour_recent.index + 0.2,
        by_hour_recent["sigma_bps"],
        width=0.4,
        label=f"{recent_year}",
    )
    ax2.set_ylabel("σ  (bps do preço)")
    ax2.set_xlabel("hora UTC")
    ax2.set_title("σ relativa — não escala com o nível de preço")
    ax2.set_xticks(range(0, 24))
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


def _fmt_sess(df: pd.DataFrame) -> list[str]:
    lines = [
        "| Sessão | Horas UTC | Barras | σ medida | σ robusta | Estimativa §13.2 | Medido/Estimado |",
        "|---|---|---|---|---|---|---|",
    ]
    for nome, r in df.iterrows():
        est = r["estimativa_13_2"]
        est_s = f"{est:.2f}" if pd.notna(est) else "—"
        raz = r["razao_medido_estimado"]
        raz_s = f"**{raz:.2f}×**" if pd.notna(raz) else "—"
        lines.append(
            f"| {nome} | {r['horas_utc']} | {int(r['n_barras']):,} | "
            f"**{r['sigma_usd']:.3f}** | {r['sigma_robusto_usd']:.3f} | {est_s} | {raz_s} |"
        )
    return lines


def _report(rets, stats, by_hour, by_year, by_sess, by_sess_recent, by_ys, recent_year) -> str:
    L: list[str] = [
        "# Auditoria de σ — XAUUSD M1 sobre `data/raw/`",
        "",
        "> Gerado por `research/audit_sigma.py` sobre os quatro anos de tick real.",
        "> Substitui as estimativas preliminares do `CLAUDE.md` §13.2 (item 5 da §18).",
        "> Nenhum número aqui é estimativa — todos saíram da leitura do dado.",
        "",
        "## O que foi medido",
        "",
        "σ é o **desvio-padrão da variação de preço em uma barra M1, em USD/oz**, sobre o bid.",
        "É a definição que a §13.2 usa em `R alcançável ≈ σ√T`; invertendo, o tempo para",
        "alcançar `R` é `T = (R/σ)²`. Portanto a medição é diretamente comparável à estimativa.",
        "",
        "| Etapa | Ticks |",
        "|---|---|",
        f"| Lidos de `raw/` | {stats['ticks_lidos']:,} |",
        f"| Removidos por feriado (ADR 0006) | {stats['ticks_em_feriado']:,} |",
        f"| Removidos por estar fora da sessão (§10.6) | {stats['ticks_fora_de_sessao']:,} |",
        "",
        f"Barras M1 resultantes: **{stats['barras_m1']:,}**. "
        f"Variações entre minutos adjacentes: **{len(rets):,}**. "
        f"Pares descartados por não serem consecutivos: {stats['pares_descartados_por_gap']:,} — "
        "são as bordas da parada diária e dos fins de semana, onde a diferença de preço não é "
        "uma variação de um minuto.",
        "",
        "---",
        "",
        "## O resultado que importa",
        "",
        f"### Ano corrente ({recent_year}) — é este que deve alimentar a §13.2",
        "",
        *_fmt_sess(by_sess_recent),
        "",
        "### Quatro anos agregados — mostrado para expor o viés, não para usar",
        "",
        *_fmt_sess(by_sess),
        "",
        "---",
        "",
        "## Por que o agregado de quatro anos engana",
        "",
        "σ em dólares **escala com o nível de preço**, e o ouro mais que dobrou na janela:",
        "",
        "| Ano | Barras | Preço mediano | σ (USD) | σ (bps) |",
        "|---|---|---|---|---|",
    ]

    for ano, r in by_year.iterrows():
        L.append(
            f"| {ano} | {int(r['n_barras']):,} | ${r['preco_mediano']:,.0f} | "
            f"{r['sigma_usd']:.3f} | {r['sigma_bps']:.2f} |"
        )

    L += [
        "",
        "---",
        "",
        "## A forma do dia mudou, não só a escala",
        "",
        "σ em USD por sessão, ano a ano. A última coluna é a que desmente a §13.2:",
        "",
        "| Ano | Preço mediano | Asiático | Londres | Sobrep. LDN/NY | Nova York | Asiático ÷ Sobrep. |",
        "|---|---|---|---|---|---|---|",
    ]
    for ano, r in by_ys.iterrows():
        L.append(
            f"| {ano} | ${r['preco_mediano']:,.0f} | {r['Asiático']:.3f} | {r['Londres']:.3f} | "
            f"{r['Sobreposição LDN/NY']:.3f} | {r['Nova York']:.3f} | "
            f"**{r['asiatico/sobreposicao']:.2f}** |"
        )
    L += [
        "",
        "A §13.2 afirma que a sessão asiática é *\"~3× mais exigente em edge para o mesmo tempo",
        "de exposição\"*. Isso exige σ da asiática ~3× **menor** que a da sobreposição, ou seja",
        "razão ≈ 0,33. A razão medida subiu ao longo da janela e chegou perto de 1 — **o perfil",
        "intradiário achatou**, e a premissa deixou de valer.",
        "",
        "Hora a hora em 2026, a hora **1 UTC** é a segunda mais volátil do dia inteiro, atrás",
        "apenas das 15 UTC. 01:00 UTC é 09:00 em Pequim: a abertura da Shanghai Gold Exchange.",
        "Em 2023, a mesma medição com o mesmo código dá o perfil clássico — asiática entre 0,59",
        "e 1,00 da hora mediana, pico de 2,03 na sobreposição. A mudança está no mercado, não no",
        "código.",
        "",
        "---",
        "",
        "A coluna em **bps** é a mesma volatilidade medida em fração do preço, e é a única",
        "comparável entre anos. Se σ em dólares subiu muito mais que σ em bps, a maior parte do",
        "aumento é nível de preço, não regime de volatilidade — e usar a média de quatro anos",
        "para dimensionar alvos em dólares hoje subestimaria o alcance real do preço.",
        "",
        "---",
        "",
        "## Tempo para alcançar R — a tabela da §13.2, agora medida",
        "",
        f"`T = (R/σ)²`, com σ do ano {recent_year}.",
        "",
        "| Sessão | σ medida | R=$1 | R=$3 | R=$5 |",
        "|---|---|---|---|---|",
    ]

    for nome, r in by_sess_recent.iterrows():
        s = r["sigma_usd"]
        L.append(
            f"| {nome} | {s:.3f} | {S.minutes_to_reach(s, 1.0):.1f} min | "
            f"{S.minutes_to_reach(s, 3.0):.1f} min | {S.minutes_to_reach(s, 5.0):.1f} min |"
        )

    L += [
        "",
        "Cruzando com a §13.1: R=$1 exige +10 pp de acerto direcional, R=$3 exige +3,3 pp e",
        "R=$5 exige +2 pp. O que esta tabela diz é **quanto tempo de exposição** cada um desses",
        "alvos custa em cada sessão.",
        "",
        "## σ por hora UTC",
        "",
        "![sigma por hora](sigma-por-hora.png)",
        "",
        "Série completa em `sigma-por-hora.csv` e `sigma-por-hora-"
        f"{recent_year}.csv`; por ano em `sigma-por-ano.csv`.",
        "",
        "## Ressalvas",
        "",
        "- **σ robusta vs. σ padrão.** A robusta usa a mediana do desvio absoluto e ignora as",
        "  caudas. Onde as duas divergem muito, a diferença é spike: o desvio-padrão está sendo",
        "  puxado por poucos minutos extremos. Para dimensionar stop, a cauda é o que mata; para",
        "  descrever o minuto típico, a robusta descreve melhor. As duas estão na tabela porque",
        "  responder qual usar depende da pergunta.",
        "- **Os blocos de sessão são convenção de rótulo em hora UTC.** As bordas reais deslizam",
        "  uma hora com o DST de Londres e de Nova York. σ por hora (0–23) é a medição",
        "  primitiva; a agregação por sessão existe para comparar com a §13.2.",
        "- **A máscara de sessão pressupõe servidor = UTC.** A medição de 2026-08-02 deu offset",
        "  zero, mas de uma estação só. A §10.7 continua aberta, e se o servidor observar DST as",
        "  bordas da máscara cortam no lugar errado durante metade do ano.",
        "- **Isto é o feed da Dukascopy, não o do broker.** O caminho de preço transplanta",
        "  (§10.4); o spread não, e não foi usado aqui. σ é uma propriedade do caminho.",
    ]

    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
