"""σ por minuto, por bucket de hora — o insumo que substitui as estimativas.

O `CLAUDE.md` §13.2 diz, com aviso explícito de que são estimativas
preliminares: asiático σ≈0,50, Londres σ≈1,20, sobreposição LDN/NY σ≈2,20. É
com esses números que se decide qual alvo em R é alcançável em quanto tempo, e
portanto se um sensor tem chance de pagar o pedágio do spread. Medi-los é o
item 5 da §18.

## A definição, e por que ela é essa

`σ` é o **desvio-padrão da variação de preço em UMA barra M1, em dólares por
onça**, medido sobre o bid.

A §13.2 usa `R alcançável ≈ σ√T`, que é o escalonamento de passeio aleatório.
Invertendo, o tempo para alcançar `R` é `T = (R/σ)²`. A definição acima
reproduz a tabela da §13.2 exatamente — com σ=0,50 e R=$1 dá T=4 min, que é o
que lá está escrito. Ou seja: a medição é diretamente comparável à estimativa,
e não uma grandeza parecida.

## A armadilha do nível de preço

**σ em dólares escala com o preço do ouro.** O ouro saiu de ~$1.760 em agosto
de 2022 para ~$4.050 em 2026 — 2,3×. Uma média de quatro anos mistura os dois
regimes e **subestima a volatilidade de hoje**, que é a única que importa para
operar amanhã.

Por isso tudo aqui é reportado em três formas:

* **σ em dólares, por ano** — o número operacional, e só o ano mais recente
  deve alimentar a §13.2
* **σ em dólares, quatro anos** — só para mostrar o quanto o agregado engana
* **σ relativo, em pontos-base do preço** — a grandeza que não escala com o
  nível, e a única honesta para comparar 2022 com 2026

## Barras consecutivas, e só

A variação de uma barra M1 só faz sentido entre minutos **adjacentes**. Se a
barra anterior está a 62 minutos de distância porque houve a parada diária, a
diferença de preço entre elas não é uma variação de um minuto — é o gap da
parada, e tratá-la como tal infla σ na hora exata em que o mercado reabre.
Todo cálculo aqui descarta pares não consecutivos e conta quantos descartou.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# Estimativas preliminares da §13.2, para comparação lado a lado.
# Não são referência de verdade — são exatamente o que esta medição substitui.
ESTIMATIVAS_13_2 = {"Asiático": 0.50, "Londres": 1.20, "Sobreposição LDN/NY": 2.20}

# Blocos de sessão em hora UTC. Convenção de rótulo, não fato de mercado: as
# bordas reais deslizam uma hora com o DST de Londres e de Nova York, e o
# projeto ainda não fechou a §10.7. σ por hora (0–23) é a medição primitiva;
# isto aqui é agregação para poder comparar com a tabela da §13.2.
SESSOES_UTC = {
    "Asiático": range(0, 7),
    "Londres": range(7, 12),
    "Sobreposição LDN/NY": range(12, 16),
    "Nova York": range(16, 21),
}


def m1_from_ticks(frame: pd.DataFrame) -> pd.DataFrame:
    """Fecha os ticks em barras M1 de bid.

    **Não** escreve `data/bars/`. A camada `bars/` deriva de `curated/` (ADR
    0005) e ainda não existe; isto é uma série de auditoria, em memória, feita
    direto de `raw/`.
    """
    if frame.empty:
        return pd.DataFrame(columns=["bar_time", "close", "n_ticks"])

    minute = frame["ts"].dt.floor("min")
    grouped = frame.groupby(minute, sort=True)

    out = pd.DataFrame(
        {
            "close": grouped["bid"].last(),
            "n_ticks": grouped.size(),
        }
    )
    out.index.name = "bar_time"
    return out.reset_index()


def consecutive_returns(bars: pd.DataFrame) -> pd.DataFrame:
    """Variação de preço entre minutos ADJACENTES.

    Devolve as colunas `bar_time`, `d` (variação em dólares) e `close`.
    Descarta os pares separados por mais de um minuto — ver docstring do
    módulo.
    """
    if len(bars) < 2:
        return pd.DataFrame(columns=["bar_time", "d", "close"])

    bars = bars.sort_values("bar_time", kind="stable")
    gap = bars["bar_time"].diff()
    d = bars["close"].diff()

    consec = gap == pd.Timedelta(minutes=1)
    return pd.DataFrame(
        {
            "bar_time": bars.loc[consec, "bar_time"],
            "d": d.loc[consec],
            "close": bars.loc[consec, "close"],
        }
    ).dropna()


def _robust_sigma(x: np.ndarray) -> float:
    """σ pela mediana do desvio absoluto, escalada para a normal.

    Reportada ao lado do desvio-padrão porque o M1 do ouro tem spikes, e o
    desvio-padrão é dominado por eles. Se as duas divergirem muito, isso é
    informação sobre a distribuição — não um detalhe de implementação a
    esconder.
    """
    if x.size == 0:
        return float("nan")
    med = np.median(x)
    return float(1.4826 * np.median(np.abs(x - med)))


def sigma_by_bucket(
    rets: pd.DataFrame, by: str = "hour"
) -> pd.DataFrame:
    """σ por bucket. `by` = 'hour' (0–23 UTC) ou 'year'."""
    if rets.empty:
        return pd.DataFrame()

    if by == "hour":
        key = rets["bar_time"].dt.hour
        key.name = "hour"
    elif by == "year":
        key = rets["bar_time"].dt.year
        key.name = "year"
    else:
        raise ValueError(f"bucket desconhecido: {by}")

    rows = []
    for bucket, part in rets.groupby(key, sort=True):
        d = part["d"].to_numpy(dtype="float64")
        preco = float(part["close"].median())
        sd = float(d.std(ddof=1)) if d.size > 1 else float("nan")
        rows.append(
            {
                key.name: bucket,
                "n_barras": int(d.size),
                "sigma_usd": sd,
                "sigma_robusto_usd": _robust_sigma(d),
                "preco_mediano": preco,
                # bps do preço: a grandeza que NÃO escala com o nível, e a
                # única que permite comparar 2022 com 2026.
                "sigma_bps": (sd / preco * 10_000) if preco else float("nan"),
            }
        )

    return pd.DataFrame(rows).set_index(key.name)


def sigma_by_session(rets: pd.DataFrame) -> pd.DataFrame:
    """σ agregada nos blocos de sessão da §13.2, para comparação direta."""
    if rets.empty:
        return pd.DataFrame()

    hour = rets["bar_time"].dt.hour
    rows = []
    for nome, horas in SESSOES_UTC.items():
        part = rets.loc[hour.isin(list(horas))]
        if part.empty:
            continue
        d = part["d"].to_numpy(dtype="float64")
        preco = float(part["close"].median())
        sd = float(d.std(ddof=1))
        rows.append(
            {
                "sessao": nome,
                "horas_utc": f"{min(horas):02d}–{max(horas) + 1:02d}",
                "n_barras": int(d.size),
                "sigma_usd": sd,
                "sigma_robusto_usd": _robust_sigma(d),
                "preco_mediano": preco,
                "estimativa_13_2": ESTIMATIVAS_13_2.get(nome, float("nan")),
            }
        )

    out = pd.DataFrame(rows).set_index("sessao")
    out["razao_medido_estimado"] = out["sigma_usd"] / out["estimativa_13_2"]
    return out


def sigma_year_by_session(rets: pd.DataFrame) -> pd.DataFrame:
    """Matriz ano × sessão de σ, e a razão asiática / sobreposição.

    Esta última coluna é a que interessa mais. A §13.2 afirma que "a asiática é
    ~3× mais exigente em edge para o mesmo tempo de exposição", o que só vale
    se σ da asiática for ~3× menor que a da sobreposição. Se essa razão se
    mover ao longo dos anos, a afirmação não é uma propriedade do ouro — é uma
    propriedade da época em que foi escrita.
    """
    if rets.empty:
        return pd.DataFrame()

    year = rets["bar_time"].dt.year
    hour = rets["bar_time"].dt.hour

    rows = []
    for y, part_y in rets.groupby(year, sort=True):
        h = part_y["bar_time"].dt.hour
        row = {"ano": int(y), "preco_mediano": float(part_y["close"].median())}
        for nome, horas in SESSOES_UTC.items():
            p = part_y.loc[h.isin(list(horas)), "d"]
            row[nome] = float(p.std(ddof=1)) if len(p) > 1 else float("nan")
        rows.append(row)

    out = pd.DataFrame(rows).set_index("ano")
    out["asiatico/sobreposicao"] = out["Asiático"] / out["Sobreposição LDN/NY"]
    return out


def minutes_to_reach(sigma: float, r_usd: float) -> float:
    """Minutos para o preço percorrer `R`, sob passeio aleatório: `T = (R/σ)²`.

    É a inversão exata de `R alcançável ≈ σ√T`, que é como a §13.2 raciocina.
    """
    if not sigma or np.isnan(sigma):
        return float("nan")
    return (r_usd / sigma) ** 2
