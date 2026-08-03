"""`data/bars/` — M1 com as primitivas do ADR 0005.

O ADR 0005 fazia `bars/` derivar de `curated/`, que precisa do spread do broker.
O ADR 0010 emendou: **as sete primitivas que não dependem de spread saem de
`raw/` direto**, e `spread_p50`/`spread_p95` ficam nulas até `spread/` existir.
O Gate 1 é "sem execução" e nunca exigiu spread.

## As colunas, exatamente como o ADR 0005 define

| coluna | definição |
|---|---|
| `bar_time` | minuto de abertura, UTC |
| `open,high,low,close` | **bid**, primeiro/máx/mín/último tick do minuto |
| `n_ticks` | contagem de ticks no minuto |
| `rv` | `sqrt(Σ (bid_i − bid_{i−1})²)` sobre os ticks do minuto, em dólares |
| `tick_imb` | `+1` se subiu, `−1` se desceu, **repete o sinal anterior se igual**; soma ÷ `n_ticks` |
| `dur_mean` | média do intervalo entre ticks, em ms |
| `dur_std` | desvio-padrão do mesmo, em ms |
| `spread_p50`, `spread_p95` | **nulas** — dependem de `spread/` |

**O primeiro tick da barra usa o último tick da barra anterior como referência**
para `rv` e `tick_imb` — só quando os minutos são adjacentes. Na primeira barra,
e depois de qualquer buraco, `rv` e `tick_imb` são `NaN` e a barra é inválida.

## Defeito conhecido em `tick_imb`

A regra "repete o sinal anterior se igual" copia o sinal em **20,9% dos ticks**
(medido em `research/findings/2026-08-03-dependencia-escala-tick.md`) — injeção
mecânica de autocorrelação. A decisão sobre isso está pendente; aqui a
especificação é implementada **como está escrita**, e a coluna `imb_copiado`
registra a fração copiada por barra para que a decisão futura seja informada.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

COLUNAS = [
    "bar_time", "open", "high", "low", "close", "n_ticks",
    "rv", "tick_imb", "dur_mean", "dur_std", "spread_p50", "spread_p95",
    "imb_copiado", "valid",
]


def bars_from_ticks(ts: pd.Series, bid: pd.Series) -> pd.DataFrame:
    """Constrói as barras M1 de um bloco de ticks já mascarado."""
    if len(ts) == 0:
        return pd.DataFrame(columns=COLUNAS)

    minuto = ts.dt.floor("min")
    codes, uniq = pd.factorize(minuto.to_numpy(), sort=True)
    n_bars = len(uniq)
    p = bid.to_numpy(dtype="float64")

    g = pd.DataFrame({"c": codes, "p": p}).groupby("c")["p"]
    out = pd.DataFrame({
        "bar_time": pd.to_datetime(uniq, utc=True),
        "open": g.first().to_numpy(),
        "high": g.max().to_numpy(),
        "low": g.min().to_numpy(),
        "close": g.last().to_numpy(),
        "n_ticks": np.bincount(codes, minlength=n_bars),
    })

    # --- retornos de tick, incluindo o que cruza a fronteira do minuto -------
    # O ADR manda o primeiro tick da barra referenciar o ultimo da anterior.
    # Isso so vale se os minutos forem ADJACENTES: depois da parada diaria o
    # "retorno" seria o gap de 62 minutos, que nao e retorno de tick.
    d = np.diff(p)
    dono = codes[1:]                      # a qual barra o retorno pertence
    cruza = codes[1:] != codes[:-1]

    mins = pd.to_datetime(uniq, utc=True)
    adj = np.zeros(n_bars, dtype=bool)
    adj[1:] = (mins[1:] - mins[:-1]) == pd.Timedelta(minutes=1)

    # retorno valido: dentro do minuto, ou cruzando fronteira entre adjacentes
    valido = ~cruza | adj[dono]

    # --- rv -----------------------------------------------------------------
    rv2 = np.bincount(dono[valido], weights=d[valido] ** 2, minlength=n_bars)
    out["rv"] = np.sqrt(rv2)

    # --- tick_imb: sinal com arrasto do anterior quando zero -----------------
    # "repete o sinal anterior se igual" = ultimo sinal nao-nulo. Vetorizavel
    # como forward-fill do sinal com zero tratado como ausente.
    sg = np.sign(d)
    s = pd.Series(np.where(sg == 0, np.nan, sg)).ffill().to_numpy()
    s = np.nan_to_num(s, nan=0.0)          # antes do primeiro movimento: 0

    soma = np.bincount(dono[valido], weights=s[valido], minlength=n_bars)
    n_ret = np.bincount(dono[valido], minlength=n_bars)
    with np.errstate(invalid="ignore", divide="ignore"):
        out["tick_imb"] = np.where(n_ret > 0, soma / out["n_ticks"].to_numpy(), np.nan)

    copiados = np.bincount(dono[valido], weights=(sg[valido] == 0).astype(float),
                           minlength=n_bars)
    with np.errstate(invalid="ignore", divide="ignore"):
        out["imb_copiado"] = np.where(n_ret > 0, copiados / n_ret, np.nan)

    # --- duracoes entre ticks, em ms ----------------------------------------
    # int64 direto: converter tz-aware para datetime64[ms] avisa e nao acrescenta nada
    dt_ms = np.diff(ts.astype("int64").to_numpy() // 1_000_000)
    sm = np.bincount(dono[valido], weights=dt_ms[valido], minlength=n_bars)
    sq = np.bincount(dono[valido], weights=dt_ms[valido] ** 2.0, minlength=n_bars)
    with np.errstate(invalid="ignore", divide="ignore"):
        media = np.where(n_ret > 0, sm / n_ret, np.nan)
        var = np.where(n_ret > 1, sq / n_ret - media ** 2, np.nan)
    out["dur_mean"] = media
    out["dur_std"] = np.sqrt(np.clip(var, 0, None))

    # --- dependem de spread/, ainda inexistente ------------------------------
    out["spread_p50"] = np.nan
    out["spread_p95"] = np.nan

    # Barra invalida quando nao ha referencia da barra anterior: rv e tick_imb
    # ficam definidos so pelo que aconteceu dentro do minuto, o que nao e o que
    # o ADR especifica.
    out["valid"] = adj & (out["n_ticks"].to_numpy() > 0)
    out.loc[~out["valid"], ["rv", "tick_imb", "imb_copiado"]] = np.nan

    return out[COLUNAS]


def build(raw_root: Path, out_root: Path, log_: logging.Logger | None = None) -> dict:
    """Percorre `raw/` partição a partição e escreve `bars/` particionada igual."""
    from .market_calendar import drop_holidays
    from .sessions import apply_trading_mask

    lg = log_ or log
    partes = sorted(Path(raw_root).glob("year=*/month=*"))
    if not partes:
        raise FileNotFoundError(f"nenhuma partição em {raw_root}")

    stats = {"ticks": 0, "feriado": 0, "fora_sessao": 0, "barras": 0, "invalidas": 0}
    carry: pd.DataFrame | None = None

    for parte in partes:
        ano = int(parte.parent.name.split("=")[1])
        mes = int(parte.name.split("=")[1])
        f = pd.read_parquet(parte, columns=["ts", "bid"]).sort_values("ts", kind="stable")
        stats["ticks"] += len(f)

        f, fer = drop_holidays(f)
        stats["feriado"] += sum(fer.values())
        f, fora = apply_trading_mask(f)
        stats["fora_sessao"] += fora
        if f.empty:
            continue

        # O ultimo tick do mes anterior atravessa, senao a primeira barra do mes
        # perde a referencia e sai invalida sem motivo.
        if carry is not None:
            f = pd.concat([carry, f], ignore_index=True)

        b = bars_from_ticks(f["ts"], f["bid"])
        carry = f.tail(1)

        # a primeira barra do bloco pode ser continuacao do mes anterior
        if len(b) and carry is not None and parte is not partes[0]:
            pass

        alvo = Path(out_root) / f"year={ano}" / f"month={mes:02d}"
        alvo.mkdir(parents=True, exist_ok=True)
        b.to_parquet(alvo / "bars.parquet", compression="zstd", index=False)

        stats["barras"] += len(b)
        stats["invalidas"] += int((~b["valid"]).sum())
        lg.info("%s: %d barras (%d inválidas)", parte.name, len(b), int((~b["valid"]).sum()))

    return stats


def read(bars_root: Path, year: int | None = None) -> pd.DataFrame:
    """Lê `bars/` de volta, ordenada por `bar_time`."""
    root = Path(bars_root)
    alvo = root / f"year={year}" if year else root
    if not alvo.exists():
        raise FileNotFoundError(alvo)
    f = pd.read_parquet(alvo)
    return f.sort_values("bar_time", kind="stable").reset_index(drop=True)
