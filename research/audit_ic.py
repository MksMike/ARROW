"""Gate 1 para a hipótese do ADR 0013 — informatividade por cotação.

    .venv\\Scripts\\python.exe research\\audit_ic.py

Mede o conteúdo informacional de `info = rv²/n_ticks` sobre `data/bars/`,
conforme a §7: IC de Spearman contra o alvo futuro no horizonte T, condicionado
à sessão, com block bootstrap de blocos de um dia.

## O alvo, e por que não é `rv`

O alvo é a **variância realizada de fechamento a fechamento** nas T barras
seguintes — não a soma de `rv` futuro.

`info` tem `rv` no numerador. Usar `rv` futuro como alvo criaria circularidade
mecânica: qualquer persistência de `rv` apareceria como IC positivo sem que
`info` acrescentasse nada. Fechamento a fechamento é construído de outra
grandeza (`close`), então a previsão tem de atravessar de uma para a outra.

## Nenhum T é escolhido

A §7 mantém em aberto **como** T se escolhe dentro da faixa de 1 a 30. Enquanto
isso não for decidido, varrer os 30 e ficar com o melhor é teste múltiplo
disfarçado de metodologia. Aqui o IC é reportado **para toda a faixa**, e o
veredito é sobre a curva inteira sobreviver — nunca sobre o melhor ponto.

## Os dois falsificadores do ADR 0013

1. Limite inferior do IC a 95% não afastado de zero → morre.
2. **Controle:** se o IC parcial, condicionado a `rv` ou a `n_ticks`
   separadamente, colapsar, `info` é proxy disfarçado de uma das duas e morre
   **mesmo que o IC bruto passe**.

O controle é feito por correlação de Spearman parcial sobre os postos: regride-se
o posto de `info` e o posto do alvo contra o posto do controle, e correlacionam-se
os resíduos. É a forma que preserva a natureza de posto do IC.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.lib import bars as B  # noqa: E402
from research.lib.sigma import SESSOES_UTC  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
T_GRID = list(range(1, 31))
N_BOOT = 1000
SEED = 20260803


def alvo_futuro(close: np.ndarray, adjacente: np.ndarray, T: int) -> np.ndarray:
    """Variância realizada fecha-a-fecha nas T barras seguintes.

    Só soma retornos entre barras adjacentes; qualquer buraco na janela invalida
    a observação inteira, para não misturar gap de sessão com movimento.
    """
    n = len(close)
    r2 = np.full(n, np.nan)
    d = np.diff(close)
    ok = adjacente[1:]
    r2[1:] = np.where(ok, d * d, np.nan)

    # soma corrida de T termos a partir de i+1
    s = pd.Series(r2)
    fwd = s.rolling(T, min_periods=T).sum().shift(-T).to_numpy()
    return fwd


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 30:
        return np.nan
    ra = pd.Series(a[m]).rank().to_numpy()
    rb = pd.Series(b[m]).rank().to_numpy()
    ra -= ra.mean(); rb -= rb.mean()
    den = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / den) if den > 0 else np.nan


def spearman_parcial(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """IC de `a` contra `b`, controlando por `c`, sobre postos."""
    m = np.isfinite(a) & np.isfinite(b) & np.isfinite(c)
    if m.sum() < 30:
        return np.nan
    ra = pd.Series(a[m]).rank().to_numpy()
    rb = pd.Series(b[m]).rank().to_numpy()
    rc = pd.Series(c[m]).rank().to_numpy()

    def resid(y):
        X = np.column_stack([np.ones_like(rc), rc])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        return y - X @ beta

    ea, eb = resid(ra), resid(rb)
    ea -= ea.mean(); eb -= eb.mean()
    den = np.sqrt((ea * ea).sum() * (eb * eb).sum())
    return float((ea * eb).sum() / den) if den > 0 else np.nan


def ic_com_ic95(df: pd.DataFrame, col_v: str, col_y: str,
                controle: str | None = None,
                n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """IC pontual e intervalo de 95% por block bootstrap de blocos de um dia."""
    v = df[col_v].to_numpy()
    y = df[col_y].to_numpy()
    c = df[controle].to_numpy() if controle else None

    ponto = spearman_parcial(v, y, c) if controle else spearman(v, y)

    dias = df["dia"].to_numpy()
    uniq = np.unique(dias)
    idx_por_dia = {d: np.flatnonzero(dias == d) for d in uniq}

    rng = np.random.default_rng(seed)
    amostras = np.empty(n_boot)
    for b in range(n_boot):
        esc = rng.choice(uniq, size=len(uniq), replace=True)
        sel = np.concatenate([idx_por_dia[d] for d in esc])
        amostras[b] = (spearman_parcial(v[sel], y[sel], c[sel]) if controle
                       else spearman(v[sel], y[sel]))
    lo, hi = np.nanpercentile(amostras, [2.5, 97.5])
    return {"ic": ponto, "lo": float(lo), "hi": float(hi),
            "afastado_de_zero": bool(lo > 0 or hi < 0), "n": int(np.isfinite(v * y).sum())}


def monotonicidade(df: pd.DataFrame, col_v: str, col_y: str) -> pd.DataFrame:
    """Mediana do alvo por decil do sinal. A §7 exige monotonicidade, não só caudas."""
    d = df[[col_v, col_y]].dropna()
    if len(d) < 100:
        return pd.DataFrame()
    d = d.assign(decil=pd.qcut(d[col_v].rank(method="first"), 10, labels=False) + 1)
    return d.groupby("decil")[col_y].agg(mediana="median", n="size").reset_index()


def carregar(bars_root: Path, log: logging.Logger) -> pd.DataFrame:
    partes = sorted(Path(bars_root).glob("year=*/month=*/bars.parquet"))
    if not partes:
        raise FileNotFoundError(f"nenhuma barra em {bars_root}")
    f = pd.concat([pd.read_parquet(p) for p in partes], ignore_index=True)
    f = f.sort_values("bar_time", kind="stable").reset_index(drop=True)
    log.info("%d barras lidas de %d partições", len(f), len(partes))

    # adjacencia entre barras consecutivas, para o alvo nao atravessar buraco
    adj = np.zeros(len(f), dtype=bool)
    bt = f["bar_time"].to_numpy()
    adj[1:] = (bt[1:] - bt[:-1]) == np.timedelta64(60, "s")
    f["adjacente"] = adj

    f["info"] = np.where(f["n_ticks"] > 0, f["rv"] ** 2 / f["n_ticks"], np.nan)
    f["dia"] = f["bar_time"].dt.floor("D")
    f["hora"] = f["bar_time"].dt.hour
    f["ano"] = f["bar_time"].dt.year

    rot = pd.Series("fora", index=f.index)
    for nome, horas in SESSOES_UTC.items():
        rot[f["hora"].isin(list(horas))] = nome
    f["sessao"] = rot
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bars-root", default=str(REPO / "data" / "bars"))
    ap.add_argument("--reports-dir", default=str(REPO / "reports"))
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--ano", type=int, default=None, help="restringir a um ano")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("audit_ic")

    f = carregar(Path(args.bars_root), log)
    f = f[f["valid"]].copy()
    if args.ano:
        f = f[f["ano"] == args.ano].copy()
    log.info("%d barras válidas em análise", len(f))

    linhas, mono_rows = [], []
    for T in T_GRID:
        f[f"y{T}"] = alvo_futuro(f["close"].to_numpy(), f["adjacente"].to_numpy(), T)

        for sess in ["TODAS"] + list(SESSOES_UTC.keys()):
            sub = f if sess == "TODAS" else f[f["sessao"] == sess]
            sub = sub[np.isfinite(sub["info"]) & np.isfinite(sub[f"y{T}"])]
            if len(sub) < 500:
                continue

            bruto = ic_com_ic95(sub, "info", f"y{T}", n_boot=args.n_boot)
            linha = {"T": T, "sessao": sess, "n": bruto["n"],
                     "ic": bruto["ic"], "lo": bruto["lo"], "hi": bruto["hi"],
                     "passa_bruto": bruto["afastado_de_zero"]}

            # Falsificador 2: controles. Só na varredura completa (sessao TODAS)
            # e num subconjunto de T, porque cada um custa n_boot regressoes.
            if sess == "TODAS" and T in (1, 2, 3, 5, 10, 20, 30):
                for ctrl in ("rv", "n_ticks"):
                    r = ic_com_ic95(sub, "info", f"y{T}", controle=ctrl,
                                    n_boot=max(200, args.n_boot // 5))
                    linha[f"ic_ctrl_{ctrl}"] = r["ic"]
                    linha[f"passa_ctrl_{ctrl}"] = r["afastado_de_zero"]
            linhas.append(linha)

        if T in (1, 5, 10, 30):
            m = monotonicidade(f, "info", f"y{T}")
            if not m.empty:
                m.insert(0, "T", T)
                mono_rows.append(m)
        f.drop(columns=[f"y{T}"], inplace=True)
        log.info("T=%d concluído", T)

    res = pd.DataFrame(linhas)
    mono = pd.concat(mono_rows, ignore_index=True) if mono_rows else pd.DataFrame()

    rep = Path(args.reports_dir); rep.mkdir(parents=True, exist_ok=True)
    suf = f"-{args.ano}" if args.ano else ""
    res.to_csv(rep / f"ic-info{suf}.csv", index=False, lineterminator="\n")
    if not mono.empty:
        mono.to_csv(rep / f"ic-info-decis{suf}.csv", index=False, lineterminator="\n")

    log.info("gravado: %s", rep / f"ic-info{suf}.csv")

    t = res[res["sessao"] == "TODAS"]
    log.info("=== resumo (todas as sessões) ===")
    log.info("T com IC afastado de zero: %d de %d", int(t["passa_bruto"].sum()), len(t))
    if "passa_ctrl_rv" in t:
        c = t.dropna(subset=["passa_ctrl_rv"])
        log.info("sobrevive ao controle por rv:      %d de %d",
                 int(c["passa_ctrl_rv"].sum()), len(c))
        log.info("sobrevive ao controle por n_ticks: %d de %d",
                 int(c["passa_ctrl_n_ticks"].sum()), len(c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
