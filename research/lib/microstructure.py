"""Dependência dos retornos de tick do bid, e densidade de tick.

## A pergunta

O piloto de 2026-06 mediu `ρ₁ = +0,0123` nos retornos de tick. Positivo
**refuta ruído iid**, que exige lag 1 negativo, e com dependência líquida
positiva o `rv` do ADR 0005 fica **deflacionado**, não inflacionado.

O que resta é uma suposição embutida, não uma dúvida sobre `rv`: **a
dependência está confinada ao lag 1?** Sob essa hipótese a curva de
subamostragem é determinada pelos dois extremos, e uma medição de dois pontos
já bastou. A grade de `k` só carrega informação se houver estrutura além do
lag 1.

## Definições

`r_i` é a variação de bid entre ticks consecutivos **dentro do mesmo minuto**.
Pares que cruzam a fronteira do minuto são descartados: a barra M1 é a unidade
e o intervalo entre o último tick de um minuto e o primeiro do seguinte não é
um retorno de tick.

`γ_j = E[r_i · r_{i+j}]`, também apenas para pares dentro do mesmo minuto.
Sem remoção de média: a média dos retornos de tick é de ordem `s²/n` e
removê-la introduz mais viés do que corrige nesta escala.

## A curva de assinatura, exata

Amostrando a cada `k`-ésimo tick e promediando sobre os `k` deslocamentos
iniciais, a variância realizada é **exatamente**

    RV_k = (1/k) · Σ_i (p_{i+k} − p_i)²        para todo i válido

Essa identidade é o que torna a promediação gratuita: os `k` deslocamentos
particionam os pares `(i, i+k)`, então somar sobre todos os pares e dividir por
`k` dá a média sobre deslocamentos, sem laço e sem viés de bloco parcial.

A esperança, sob covariância estacionária dentro do minuto:

    E[RV_k] = (n−k)·γ₀ + (2(n−k)/k) · Σ_{j=1}^{k−1} (k−j)·γ_j

**O fator `(n−k)` não é detalhe.** Subamostrar não cobre o minuto inteiro: a
fração perdida do span cresce com `k`. Usar `n` no lugar de `(n−k)` produz um
erro de +59% em `k=64` com `n=171`, e esse erro tem exatamente a forma de
curvatura — ou seja, seria lido como refutação do modelo quando é defeito do
estimador.

**Truncagem.** Medimos `γ_j` até `max_lag`. Para `k > max_lag+1` a previsão
assume `γ_j = 0` acima disso. Divergência entre medido e previsto nos `k`
grandes **é** o teste da truncagem — é o que responde a pergunta da sessão.

## O que esta medição NÃO responde

`γ₁` é o **líquido**. Momento em escala de tick entra positivo; quique de
cotação entra negativo. Os dois não são separáveis com série de bid apenas, e
nada aqui deve ser lido como estimativa de `η` nem de spread efetivo — `raw/` é
série de cotação, não de negócios, e o quique de Roll pressupõe alternância
entre lados em série de trades.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Grade de subamostragem e lags, fixadas pelo brief.
K_GRID = (1, 2, 4, 8, 16, 32, 64)
MAX_LAG = 8

# Barras abaixo disso ficam fora da grade de `k`: com menos de 128 ticks os
# `k` grandes não têm pontos suficientes em cima, e o ajuste vira extrapolação.
MIN_TICKS = 128


def _within_minute(minute: np.ndarray, lag: int) -> np.ndarray:
    """Máscara dos pares `(i, i+lag)` que caem no mesmo minuto."""
    return minute[lag:] == minute[:-lag]


def per_bar_stats(
    ts: pd.Series,
    bid: pd.Series,
    *,
    max_lag: int = MAX_LAG,
    k_grid: tuple[int, ...] = K_GRID,
) -> pd.DataFrame:
    """Estatísticas por barra M1, tudo em uma passada por lag/k.

    Devolve uma linha por minuto com:

    * `n_ticks`   — ticks no minuto
    * `n_changes` — ticks em que o bid mudou; `n_ticks − n_changes` é o
      número de retornos exatamente zero
    * `s_j`       — Σ `r_i·r_{i+j}` dentro do minuto, para `j = 0..max_lag`
    * `c_j`       — contagem de pares válidos para cada `j`
    * `rv_k`      — `RV_k` pela identidade acima, para cada `k` da grade
    * `rv_adr`    — `rv²` como o ADR 0005 define (ver `rv_adr0005`)

    As somas ficam **por barra e não agregadas** porque a agregação por dia é
    o que permite o bootstrap por blocos de um dia (cláusula pétrea 7), e a
    estratificação por quartil de `n` exige o valor de cada barra.
    """
    minute = ts.dt.floor("min").to_numpy()
    p = bid.to_numpy(dtype="float64")

    codes, uniq = pd.factorize(minute, sort=True)
    n_bars = len(uniq)

    out: dict[str, np.ndarray] = {}
    out["n_ticks"] = np.bincount(codes, minlength=n_bars).astype("int64")

    # retornos de tick, só dentro do minuto
    d = np.diff(p)
    same1 = _within_minute(minute, 1)
    r = np.where(same1, d, 0.0)
    # o código do minuto do retorno r_i é o do tick i+1 (mesmo minuto que i)
    rcode = codes[1:]

    out["n_changes"] = np.bincount(rcode[same1], weights=(d[same1] != 0.0), minlength=n_bars)

    # autocovariâncias: Σ r_i r_{i+j} com ambos no mesmo minuto
    for j in range(0, max_lag + 1):
        if j == 0:
            prod = np.where(same1, r * r, 0.0)
            valid = same1
            code_j = rcode
        else:
            if len(r) <= j:
                out[f"s_{j}"] = np.zeros(n_bars)
                out[f"c_{j}"] = np.zeros(n_bars)
                continue
            valid = same1[:-j] & same1[j:] & (rcode[:-j] == rcode[j:])
            prod = np.where(valid, r[:-j] * r[j:], 0.0)
            code_j = rcode[:-j]
        out[f"s_{j}"] = np.bincount(code_j, weights=prod, minlength=n_bars)
        out[f"c_{j}"] = np.bincount(code_j, weights=valid.astype("float64"), minlength=n_bars)

    # RV_k pela identidade: todas as diferenças de lag k, dentro do minuto, / k
    for k in k_grid:
        if len(p) <= k:
            out[f"rv_{k}"] = np.zeros(n_bars)
            continue
        samek = _within_minute(minute, k)
        dk = np.where(samek, p[k:] - p[:-k], 0.0)
        out[f"rv_{k}"] = np.bincount(codes[k:], weights=dk * dk, minlength=n_bars) / k

    frame = pd.DataFrame(out)
    frame.insert(0, "bar_time", pd.to_datetime(uniq, utc=True))
    return frame


def rv_adr0005(ts: pd.Series, bid: pd.Series) -> pd.DataFrame:
    """`rv²` como o ADR 0005 define, e a variante intra-minuto ao lado.

    O ADR manda que **o primeiro tick da barra use o último tick da barra
    anterior como referência**. Isso acrescenta um retorno por barra — o que
    atravessa a fronteira do minuto — e é justamente o que o piloto de
    2026-06 não incluiu.

    Reportar as duas torna o piloto reproduzível e deixa a diferença explícita,
    que é o que o critério 5 do brief mede.
    """
    minute = ts.dt.floor("min").to_numpy()
    p = bid.to_numpy(dtype="float64")
    codes, uniq = pd.factorize(minute, sort=True)
    n_bars = len(uniq)

    d = np.diff(p)
    same = _within_minute(minute, 1)

    intra = np.bincount(codes[1:][same], weights=d[same] ** 2, minlength=n_bars)
    cross = np.bincount(codes[1:][~same], weights=d[~same] ** 2, minlength=n_bars)

    tsv = ts.to_numpy()
    dt_s = (
        (pd.Series(tsv[1:][~same]) - pd.Series(tsv[:-1][~same])).dt.total_seconds().to_numpy()
    )
    gap_s = np.bincount(codes[1:][~same], weights=dt_s, minlength=n_bars)

    # O gap só é "de fronteira" quando os dois minutos são ADJACENTES. Depois da
    # parada diária ou do fim de semana o intervalo é de dezenas de minutos, e
    # incluí-lo faz a média explodir sem descrever nada da microestrutura — foi
    # o que o teste de fumaça mostrou: média de 27 s contra mediana de 0,4 s.
    mins = pd.to_datetime(uniq, utc=True)
    adjacente = np.zeros(n_bars, dtype=bool)
    adjacente[1:] = (mins[1:] - mins[:-1]) == pd.Timedelta(minutes=1)

    return pd.DataFrame(
        {
            "bar_time": mins,
            "rv2_intra": intra,
            "rv2_adr": intra + cross,
            "gap_fronteira_s": np.where(adjacente, gap_s, np.nan),
            "minuto_adjacente": adjacente,
        }
    )


def pool_gamma(bars: pd.DataFrame, max_lag: int = MAX_LAG) -> pd.Series:
    """`γ_j` agregada: Σ produtos ÷ Σ pares, sobre as barras dadas."""
    g = {}
    for j in range(max_lag + 1):
        c = bars[f"c_{j}"].sum()
        g[j] = bars[f"s_{j}"].sum() / c if c > 0 else np.nan
    return pd.Series(g, name="gamma")


def gamma_with_se(
    bars: pd.DataFrame,
    *,
    max_lag: int = MAX_LAG,
    n_boot: int = 1000,
    seed: int = 20260803,
) -> pd.DataFrame:
    """`γ_j` com erro-padrão por **block bootstrap com blocos de um dia**.

    Escolhido em vez de Newey-West por consistência com a §7 do `CLAUDE.md`,
    que manda exatamente isso para significância, e com a cláusula pétrea 7,
    que faz do dia a unidade estatística porque minutos dentro do dia são
    autocorrelacionados. Erro-padrão calculado sobre barras como se fossem
    independentes seria otimista pelo mesmo motivo que a §7 existe.

    O reamostreio é sobre **somas diárias**, não sobre barras: `γ_j` é razão de
    somas, então agregar por dia antes torna o bootstrap O(dias) em vez de
    O(barras) sem aproximação nenhuma.
    """
    if bars.empty:
        return pd.DataFrame()

    dia = bars["bar_time"].dt.floor("D")
    cols = [f"s_{j}" for j in range(max_lag + 1)] + [f"c_{j}" for j in range(max_lag + 1)]
    por_dia = bars.groupby(dia)[cols].sum()

    S = por_dia[[f"s_{j}" for j in range(max_lag + 1)]].to_numpy()
    C = por_dia[[f"c_{j}" for j in range(max_lag + 1)]].to_numpy()
    n_dias = len(por_dia)

    ponto = S.sum(axis=0) / np.where(C.sum(axis=0) > 0, C.sum(axis=0), np.nan)

    rng = np.random.default_rng(seed)
    amostras = np.empty((n_boot, max_lag + 1))
    for b in range(n_boot):
        idx = rng.integers(0, n_dias, n_dias)
        cs = C[idx].sum(axis=0)
        amostras[b] = S[idx].sum(axis=0) / np.where(cs > 0, cs, np.nan)

    return pd.DataFrame(
        {
            "lag": np.arange(max_lag + 1),
            "gamma": ponto,
            "erro_padrao": np.nanstd(amostras, axis=0, ddof=1),
            "n_dias": n_dias,
            "n_barras": len(bars),
        }
    ).set_index("lag")


def predict_rv(gamma: pd.Series, n: float, k: int) -> float:
    """`E[RV_k]` prevista pelos `γ_j` medidos.

    `E[RV_k] = (n−k)·γ₀ + (2(n−k)/k)·Σ_{j=1}^{k−1}(k−j)·γ_j`

    **`n` tem de ser a MÉDIA de `n_ticks`, não a mediana.** `RV_k` medido é uma
    média sobre barras, então a previsão também precisa ser. Como minutos
    movimentados são mais voláteis, `E[n·γ₀] > mediana(n)·γ₀`, e usar a mediana
    produz um offset constante em todos os `k` — o teste de fumaça deu +11,9%
    já em `k=1`, o que mascararia qualquer leitura da forma da curva.

    Para `k−1 > max_lag` a soma trunca, assumindo `γ_j = 0` acima. É a
    truncagem que a curva testa.
    """
    if n <= k:
        return np.nan
    max_lag = int(gamma.index.max())
    soma = sum((k - j) * gamma.get(j, 0.0) for j in range(1, min(k, max_lag + 1)))
    return (n - k) * gamma[0] + (2.0 * (n - k) / k) * soma


def repeated_bid_share(bars: pd.DataFrame) -> dict[str, float]:
    """Fração de ticks com bid idêntico ao anterior, e contagens."""
    nt = bars["n_ticks"].sum()
    nc = bars["n_changes"].sum()
    # n_changes conta retornos; o primeiro tick da barra não tem retorno
    n_ret = nt - len(bars)
    return {
        "n_ticks": float(nt),
        "n_retornos": float(n_ret),
        "n_changes": float(nc),
        "fracao_repetidos": float(1.0 - nc / n_ret) if n_ret > 0 else np.nan,
    }


def tick_density(bars: pd.DataFrame, by: str) -> pd.DataFrame:
    """Distribuição de `n_ticks` e `n_changes` por bucket.

    `by` = 'hora' (0–23 UTC) ou 'sessao'. Fecha a lacuna "Densidade de tick por
    sessão" da seção 8 do `REFERENCIA-XAUUSD.md`.
    """
    from .sigma import SESSOES_UTC

    b = bars.copy()
    h = b["bar_time"].dt.hour
    if by == "hora":
        b["_b"] = h
    elif by == "sessao":
        rot = pd.Series("fora", index=b.index)
        for nome, horas in SESSOES_UTC.items():
            rot[h.isin(list(horas))] = nome
        b["_b"] = rot
    else:
        raise ValueError(by)

    g = b.groupby("_b")
    out = pd.DataFrame(
        {
            "n_barras": g.size(),
            "ticks_p05": g["n_ticks"].quantile(0.05),
            "ticks_mediana": g["n_ticks"].median(),
            "ticks_p95": g["n_ticks"].quantile(0.95),
            "changes_mediana": g["n_changes"].median(),
            "abaixo_de_128": g["n_ticks"].apply(lambda s: int((s < MIN_TICKS).sum())),
        }
    )
    out["frac_repetidos"] = 1.0 - out["changes_mediana"] / (out["ticks_mediana"] - 1)
    return out
