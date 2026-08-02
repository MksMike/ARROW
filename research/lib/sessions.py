"""Máscara de sessão do símbolo — quando dá para negociar.

Horários do `CLAUDE.md` §10.6, em hora de servidor. A medição de 2026-08-02
registrada em `data/broker/_offset_log.csv` deu **offset = 0**, ou seja
servidor = UTC — mas de **uma estação só**. O teste das duas estações da §10.7
segue pendente, e é ele que distingue um servidor UTC fixo de um que desloca
com o DST.

Consequência prática: enquanto a §10.7 não fechar, tratar os horários abaixo
como UTC é uma **premissa**, não um fato. Se o servidor observar DST, todas as
bordas deslizam uma hora no inverno americano e esta máscara passa a cortar no
lugar errado durante metade do ano.

Sessões de **negociação** (não de cotação — cotação abre alguns minutos antes e
não é hora em que se pode operar):

* Domingo: 22:05–24:00
* Segunda a quinta: 00:00–20:58 e 22:01–24:00
* Sexta: 00:00–20:58
* Sábado: fechado
"""

from __future__ import annotations

import pandas as pd

# Parada diária: o intervalo de manutenção do símbolo.
BREAK_START = (20, 58)
BREAK_END = (22, 0)


def trading_mask(ts: pd.Series) -> pd.Series:
    """`True` para os instantes em que o símbolo aceita negociação.

    `ts` precisa ser tz-aware em UTC. Ver o aviso do módulo sobre a premissa
    servidor = UTC.
    """
    dow = ts.dt.dayofweek          # 0 = segunda ... 6 = domingo
    minute_of_day = ts.dt.hour * 60 + ts.dt.minute

    break_start = BREAK_START[0] * 60 + BREAK_START[1]   # 20:58 -> 1258
    reopen = 22 * 60 + 1                                  # 22:01
    sunday_open = 22 * 60 + 5                             # 22:05

    before_break = minute_of_day < break_start
    after_reopen = minute_of_day >= reopen

    weekday = dow <= 3                       # segunda a quinta
    friday = dow == 4
    saturday = dow == 5
    sunday = dow == 6

    return (
        (weekday & (before_break | after_reopen))
        | (friday & before_break)
        | (sunday & (minute_of_day >= sunday_open))
    ) & ~saturday


def apply_trading_mask(
    frame: pd.DataFrame, ts_column: str = "ts"
) -> tuple[pd.DataFrame, int]:
    """Remove ticks fora da sessão de negociação.

    Devolve o frame filtrado e quantos ticks saíram. A contagem não é opcional:
    uma máscara que não reporta o que cortou é indistinguível de um bug de
    borda, e o resultado sai menor sem que ninguém saiba por quê.
    """
    if frame.empty:
        return frame, 0

    keep = trading_mask(frame[ts_column])
    removed = int((~keep).sum())
    return frame.loc[keep].reset_index(drop=True), removed
