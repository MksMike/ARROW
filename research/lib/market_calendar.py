"""Calendário de feriados do mercado de ouro — dias excluídos do dataset.

Decisão registrada no ADR 0006: os dias de feriado são **removidos** de
`curated/`, e portanto de `bars/` e de todo teste. `raw/` permanece intacta —
ela é imutável por princípio (`CLAUDE.md` §10.2) e continua contendo os ticks
desses dias.

## Por que declarado, e não inferido do dado

A tentação óbvia é excluir o que a validação achou magro ou ausente. Isso está
errado, e o erro é o mesmo que o `validate.py` alerta: **um feriado e um buraco
de coleta se parecem no gráfico.** Excluir automaticamente tudo que é magro faz
o buraco de coleta desaparecer em silêncio — que é exatamente o defeito que a
camada de validação existe para tornar visível.

Então a direção se inverte: o calendário é **declarado por regra**, e o dado é
comparado contra ele. Dia magro que está no calendário é feriado, e sai. Dia
magro que **não** está é anomalia, e grita.

## As regras

* **Sexta-feira Santa** — dois dias antes da Páscoa, calculada pelo computus
  gregoriano anônimo. O mercado de ouro fecha por completo.
* **Natal (25/12) e Ano-Novo (01/01)** — sessão encurtada, tipicamente 1% a 4%
  do volume de um pregão normal.
* **Regra de observância:** feriado de data fixa que cai no domingo é observado
  na segunda seguinte; no sábado, na sexta anterior. O ouro abre domingo à
  noite, então na prática só a regra do domingo aparece.

Verificado contra os quatro anos de `raw/` (2022-08 a 2026-07): a regra
reproduz **exatamente** os 12 dias que a validação encontrou empiricamente —
4 Sextas-feiras Santas ausentes e 8 meio-feriados de fim de ano — sem sobra
nem falta dos dois lados.
"""

from __future__ import annotations

import datetime as _dt
from typing import Iterable

import pandas as pd


def easter(year: int) -> _dt.date:
    """Domingo de Páscoa pelo computus gregoriano anônimo.

    Algoritmo fechado, sem tabela e sem dependência externa — importa porque
    o cálculo precisa dar o mesmo resultado em qualquer máquina do projeto
    (cláusula pétrea 3).
    """
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    lam = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lam) // 451
    month, day = divmod(h + lam - 7 * m + 114, 31)
    return _dt.date(year, month, day + 1)


def good_friday(year: int) -> _dt.date:
    """Sexta-feira Santa: dois dias antes da Páscoa."""
    return easter(year) - _dt.timedelta(days=2)


def _observed(day: _dt.date) -> _dt.date:
    """Data efetiva de um feriado de data fixa.

    Domingo → segunda seguinte. Sábado → sexta anterior. Nos quatro anos de
    `raw/` só a regra do domingo se manifesta, porque o ouro não negocia no
    sábado de qualquer forma.
    """
    if day.weekday() == 6:      # domingo
        return day + _dt.timedelta(days=1)
    if day.weekday() == 5:      # sábado
        return day - _dt.timedelta(days=1)
    return day


def holidays_for_year(year: int) -> dict[_dt.date, str]:
    """Feriados do mercado de ouro num ano civil, com o nome de cada um."""
    return {
        good_friday(year): "Sexta-feira Santa",
        _observed(_dt.date(year, 12, 25)): "Natal",
        _observed(_dt.date(year, 1, 1)): "Ano-Novo",
    }


def holidays_between(
    start: _dt.date | pd.Timestamp, end: _dt.date | pd.Timestamp
) -> dict[_dt.date, str]:
    """Feriados no intervalo fechado `[start, end]`."""
    start = pd.Timestamp(start).date()
    end = pd.Timestamp(end).date()

    out: dict[_dt.date, str] = {}
    for year in range(start.year, end.year + 1):
        for day, name in holidays_for_year(year).items():
            if start <= day <= end:
                out[day] = name
    return dict(sorted(out.items()))


def is_holiday(day: _dt.date | pd.Timestamp) -> bool:
    """`True` se a data é feriado de mercado."""
    day = pd.Timestamp(day).date()
    return day in holidays_for_year(day.year)


def drop_holidays(
    frame: pd.DataFrame, ts_column: str = "ts"
) -> tuple[pd.DataFrame, dict[_dt.date, int]]:
    """Remove os ticks que caem em feriado de mercado.

    Devolve o frame filtrado e quantos ticks saíram por dia — a contagem não é
    opcional. Uma exclusão que não reporta o que excluiu é indistinguível de um
    bug de filtro, e o resultado sai menor sem que ninguém saiba por quê.
    """
    if frame.empty:
        return frame, {}

    dates = frame[ts_column].dt.date
    lo, hi = dates.min(), dates.max()
    cal = holidays_between(lo, hi)

    mask = dates.isin(cal.keys())
    removed = frame.loc[mask, ts_column].dt.date.value_counts().to_dict()

    return frame.loc[~mask].reset_index(drop=True), dict(sorted(removed.items()))


def classify_days(days: Iterable[str]) -> tuple[list[str], list[str]]:
    """Separa uma lista de datas ISO entre feriados conhecidos e anomalias.

    É o cruzamento que impede um buraco de coleta de se disfarçar de feriado.
    Devolve `(feriados, anomalias)`.
    """
    known: list[str] = []
    unknown: list[str] = []
    for d in days:
        if is_holiday(pd.Timestamp(d)):
            known.append(d)
        else:
            unknown.append(d)
    return known, unknown
