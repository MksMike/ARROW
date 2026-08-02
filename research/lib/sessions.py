"""Máscara de sessão do símbolo — quando dá para negociar.

## O relógio é fixo; o calendário não

Medido em 2026-08-02 por `MQL5/Scripts/ARROW/DataAudit.mq5`, sobre o histórico
M1 do broker, em duas estações (`reports/broker-audit.md`):

| Estação | Parada diária, hora de servidor | Dias |
|---|---|---|
| Julho (verão americano) | `20:58` → `22:02` | 16 de 16 |
| Janeiro (inverno americano) | `21:58` → `23:01` | 15 de 15 |

Deslize de exatamente **uma hora**, sem exceção em nenhum dos 31 dias.

Isso responde a §10.7 em duas partes, e é importante não confundi-las:

1. **O relógio do servidor é fixo — servidor = UTC.** A parada acompanha a
   manutenção do COMEX (17:00–18:00 em Nova York), que em UTC é 21:00–22:00 no
   verão e 22:00–23:00 no inverno. Se o servidor observasse DST, a parada
   ficaria na mesma hora nas duas estações. Ela desliza, logo o relógio não se
   mexe — o que se mexe é Nova York, por baixo dele.

2. **Mas a sessão configurada do símbolo DESLIZA junto.** Em janeiro existem
   barras até 21:57, e só então o buraco começa. Se a sessão terminasse às
   20:58 o ano inteiro, não haveria barra alguma entre 20:58 e 21:58.

A segunda parte é a que morde. Tratar `20:58` como constante do ano inteiro
**descarta uma hora real de negociação por dia durante o inverno americano** —
foi o que a primeira versão deste módulo fez, e foi corrigido aqui.

## O que foi medido e o que foi inferido

Medido: a parada diária, nas duas estações. Inferido, por estar ancorado no
mesmo horário e deslizar junto: o fechamento de sexta e a abertura de domingo.
A abertura de domingo **não foi medida** — o `DataAudit` filtra buracos acima
de 180 min e o fim de semana cai fora. Errar nela custa até uma hora de dado de
domingo, que é sessão parcial e de baixo volume; medir é trabalho de uma
extensão do `DataAudit`.

Horários de referência, no **verão americano** (§10.6). No inverno, tudo desloca
`+1 hora`:

* Domingo: 22:05–24:00
* Segunda a quinta: 00:00–20:58 e 22:01–24:00
* Sexta: 00:00–20:58
* Sábado: fechado
"""

from __future__ import annotations

import datetime as _dt

import pandas as pd

# Bordas no VERÃO americano, em minutos desde a meia-noite.
BREAK_START_SUMMER = 20 * 60 + 58    # 20:58
REOPEN_SUMMER = 22 * 60 + 1          # 22:01
SUNDAY_OPEN_SUMMER = 22 * 60 + 5     # 22:05

# No inverno tudo desloca uma hora, porque Nova York desloca e o servidor não.
WINTER_SHIFT_MIN = 60


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> _dt.date:
    """n-ésimo `weekday` (0=segunda) do mês. `n=1` é o primeiro."""
    d = _dt.date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + _dt.timedelta(days=offset + 7 * (n - 1))


def us_dst_bounds(year: int) -> tuple[_dt.date, _dt.date]:
    """Início e fim do horário de verão americano.

    Segundo domingo de março até o primeiro domingo de novembro. Regra em
    código e não em tabela: o cálculo tem de dar o mesmo resultado em qualquer
    máquina do projeto (cláusula pétrea 3).
    """
    return _nth_weekday(year, 3, 6, 2), _nth_weekday(year, 11, 6, 1)


def in_us_dst(ts: pd.Series) -> pd.Series:
    """`True` para os instantes dentro do horário de verão americano.

    A transição acontece às 02:00 hora local de Nova York; aqui é tratada na
    granularidade do dia. O erro máximo é de algumas horas em dois domingos por
    ano — domingos são sessão parcial, e o custo disso é menor que o de fingir
    precisão que a fonte não sustenta.
    """
    dates = ts.dt.date
    out = pd.Series(False, index=ts.index)
    for year in sorted({d.year for d in dates}):
        ini, fim = us_dst_bounds(year)
        out |= pd.Series([ini <= d < fim for d in dates], index=ts.index)
    return out


def trading_mask(ts: pd.Series) -> pd.Series:
    """`True` para os instantes em que o símbolo aceita negociação.

    `ts` precisa ser tz-aware em UTC — o que é o mesmo que hora de servidor,
    já que a medição da §10.7 fixou offset zero.
    """
    dow = ts.dt.dayofweek                     # 0 = segunda ... 6 = domingo
    minute_of_day = ts.dt.hour * 60 + ts.dt.minute

    shift = (~in_us_dst(ts)).astype(int) * WINTER_SHIFT_MIN

    break_start = BREAK_START_SUMMER + shift
    reopen = REOPEN_SUMMER + shift
    sunday_open = SUNDAY_OPEN_SUMMER + shift

    before_break = minute_of_day < break_start
    after_reopen = minute_of_day >= reopen

    weekday = dow <= 3                        # segunda a quinta
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
