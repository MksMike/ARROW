"""Gap de fonte — Dukascopy contra Exness no mesmo período (§11.2).

    .venv\\Scripts\\python.exe research\\audit_gap_fonte.py

Quatro anos de pesquisa se apoiam na afirmação da §8 de que **o caminho de preço
transplanta** e só o spread não. Isso nunca foi verificado; é a premissa mais
cara do projeto, porque se ela cair, todo σ, toda densidade e toda calibração
medidos sobre `raw/` descrevem outro mercado.

Compara `data/broker_hist/` (tick real da Exness) contra `data/raw/` (Dukascopy)
sobre a janela de sobreposição.

## O que se mede, e o que cada resultado significa

1. **Caminho de preço, barra a barra.** OHLC de bid em M1 nas duas fontes. Se o
   `close` bater dentro de centavos, a §8 se sustenta. Se divergir em ordem de
   grandeza comparável a σ (~2,6 USD em 2026), **os quatro anos descrevem outro
   ativo** e a calibração inteira precisa ser refeita sobre o broker.

2. **σ por barra.** É o número que alimenta a calibração da §7 da REFERENCIA. Se
   σ_exness ≠ σ_dukascopy, os tempos `T = (R/σ)²` estão errados.

3. **Densidade de tick.** A §8 já diz que é "parcial, medir não presumir". A
   sonda de 2026-08-03 deu broker 1,8× a 3,3× a Dukascopy nas horas asiáticas.
   Aqui vira medição sobre um mês.

4. **Spread.** Esperado divergir e **não é falha**: a §8 diz que a Dukascopy é
   ECN bruto e a conta é Standard com markup, e que o spread dela é descartado
   por inteiro. Medir a razão diz o tamanho do markup, que é insumo do modelo de
   `spread/`.

## O que este script NÃO faz

Não conclui sobre execução. Slippage e alargamento no disparo só o Gate 4 mede
(§7), e nenhuma comparação de feed histórico substitui isso.

Não é a medição do gap de resolução (tick contra M1 OHLC) — essa é outra, sobre
a mesma fonte, e está fora daqui.
"""

from __future__ import annotations

import argparse
import glob
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.lib.loader import read_raw  # noqa: E402
from research.lib.market_calendar import drop_holidays  # noqa: E402
from research.lib.sessions import apply_trading_mask  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def m1(f: pd.DataFrame) -> pd.DataFrame:
    """OHLC de bid, n_ticks e spread mediano por minuto."""
    m = f["ts"].dt.floor("min")
    g = f.groupby(m)
    out = pd.DataFrame({
        "open": g["bid"].first(), "high": g["bid"].max(),
        "low": g["bid"].min(), "close": g["bid"].last(),
        "n_ticks": g.size(),
    })
    if "ask" in f.columns:
        out["spread_p50"] = g.apply(lambda x: float((x["ask"] - x["bid"]).median()),
                                    include_groups=False)
    out.index.name = "bar_time"
    return out.reset_index()


def carregar_broker(root: Path) -> pd.DataFrame:
    arqs = sorted(glob.glob(str(root / "XAUUSDm-*.csv")))
    if not arqs:
        raise FileNotFoundError(f"nenhum CSV em {root} — rode TickBackfill.mq5 no MT5")
    d = pd.concat([pd.read_csv(a) for a in arqs], ignore_index=True)
    d["ts"] = pd.to_datetime(d["ts"], utc=True)
    return d.sort_values("ts", kind="stable").reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--broker-hist", default=str(REPO / "data" / "broker_hist"))
    ap.add_argument("--raw-root", default=str(REPO / "data" / "raw"))
    ap.add_argument("--reports-dir", default=str(REPO / "reports"))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("gap_fonte")

    ex = carregar_broker(Path(args.broker_hist))
    log.info("Exness: %d ticks, %s → %s", len(ex), ex["ts"].min(), ex["ts"].max())

    lo, hi = ex["ts"].min(), ex["ts"].max()
    meses = sorted({(t.year, t.month) for t in [lo, hi]} |
                   {(d.year, d.month) for d in pd.date_range(lo, hi, freq="D")})
    duk = pd.concat([read_raw(Path(args.raw_root), year=a, month=m, columns=["ts", "bid", "ask"])
                     for a, m in meses if (Path(args.raw_root) / f"year={a}" / f"month={m:02d}").exists()],
                    ignore_index=True)
    duk = duk[(duk["ts"] >= lo) & (duk["ts"] <= hi)].reset_index(drop=True)
    log.info("Dukascopy na mesma janela: %d ticks", len(duk))

    # Mesma mascara nas duas, senao a comparacao mistura gap de fonte com
    # diferenca de populacao -- o erro que ja apareceu no cruzamento do sigma.
    ex, _ = drop_holidays(ex);  ex, _ = apply_trading_mask(ex)
    duk, _ = drop_holidays(duk); duk, _ = apply_trading_mask(duk)

    be, bd = m1(ex), m1(duk)
    j = be.merge(bd, on="bar_time", suffixes=("_ex", "_duk"), how="inner")
    log.info("barras em comum: %d (exness %d, dukascopy %d)", len(j), len(be), len(bd))

    d_close = j["close_ex"] - j["close_duk"]
    ret_ex = j["close_ex"].diff()
    ret_duk = j["close_duk"].diff()

    L = [
        "# Gap de fonte — Exness contra Dukascopy",
        "",
        "> Gerado por `research/audit_gap_fonte.py`. Mede a premissa da §8 de que o caminho de",
        "> preço transplanta e só o spread não.",
        "",
        "| | |",
        "|---|---|",
        f"| Janela | {lo} → {hi} |",
        f"| Ticks Exness | {len(ex):,} |",
        f"| Ticks Dukascopy | {len(duk):,} |",
        f"| Barras M1 em comum | {len(j):,} |",
        f"| Barras só na Exness | {len(be) - len(j):,} |",
        f"| Barras só na Dukascopy | {len(bd) - len(j):,} |",
        "",
        "## 1. Caminho de preço — a premissa que sustenta quatro anos",
        "",
        "| Estatística de `close_exness − close_dukascopy` | USD/oz |",
        "|---|---|",
        f"| média | {d_close.mean():+.4f} |",
        f"| mediana | {d_close.median():+.4f} |",
        f"| desvio-padrão | {d_close.std():.4f} |",
        f"| p05 | {d_close.quantile(.05):+.4f} |",
        f"| p95 | {d_close.quantile(.95):+.4f} |",
        f"| \\|diferença\\| mediana | {d_close.abs().median():.4f} |",
        f"| \\|diferença\\| p99 | {d_close.abs().quantile(.99):.4f} |",
        "",
        f"**Correlação dos retornos M1: {ret_ex.corr(ret_duk):.6f}** (Pearson), "
        f"{ret_ex.corr(ret_duk, method='spearman'):.6f} (Spearman).",
        "",
        "## 2. σ por barra M1 — alimenta a calibração",
        "",
        "| Fonte | σ (USD/oz) |",
        "|---|---|",
        f"| Exness | {ret_ex.std():.4f} |",
        f"| Dukascopy | {ret_duk.std():.4f} |",
        f"| **razão Exness/Dukascopy** | **{ret_ex.std() / ret_duk.std():.4f}** |",
        "",
        "## 3. Densidade de tick",
        "",
        "| Fonte | n_ticks mediano |",
        "|---|---|",
        f"| Exness | {j['n_ticks_ex'].median():.0f} |",
        f"| Dukascopy | {j['n_ticks_duk'].median():.0f} |",
        f"| **razão** | **{j['n_ticks_ex'].median() / max(j['n_ticks_duk'].median(), 1):.2f}×** |",
        "",
    ]

    if "spread_p50_ex" in j and "spread_p50_duk" in j:
        L += [
            "## 4. Spread — esperado divergir, e não é falha",
            "",
            "A §8 diz que a Dukascopy é ECN bruto e a conta é Standard com markup, e que o spread",
            "dela é descartado por inteiro. A razão abaixo é o tamanho do markup.",
            "",
            "| | Exness | Dukascopy | razão |",
            "|---|---|---|---|",
            f"| mediana | {j['spread_p50_ex'].median():.4f} | {j['spread_p50_duk'].median():.4f} | "
            f"**{j['spread_p50_ex'].median() / max(j['spread_p50_duk'].median(), 1e-9):.2f}×** |",
            f"| p95 | {j['spread_p50_ex'].quantile(.95):.4f} | {j['spread_p50_duk'].quantile(.95):.4f} | |",
            "",
        ]

    L += [
        "## Leitura",
        "",
        "A §8 se sustenta se a diferença de `close` for pequena diante de σ. Com σ ≈ 2,6 USD em",
        "2026, diferença mediana de centavos é ruído de feed; diferença de décimos já desloca",
        "sistematicamente stop e alvo.",
        "",
        "**Este relatório não conclui sobre execução.** Slippage e alargamento no disparo só o",
        "Gate 4 mede.",
        "",
    ]

    rep = Path(args.reports_dir); rep.mkdir(parents=True, exist_ok=True)
    (rep / "gap-fonte.md").write_text("\n".join(L), encoding="utf-8", newline="\n")
    j.to_csv(rep / "gap-fonte-barras.csv", index=False, lineterminator="\n")

    log.info("relatório: %s", rep / "gap-fonte.md")
    log.info("|Δclose| mediana = %.4f USD | razão σ = %.4f | razão densidade = %.2fx",
             d_close.abs().median(), ret_ex.std() / ret_duk.std(),
             j["n_ticks_ex"].median() / max(j["n_ticks_duk"].median(), 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
