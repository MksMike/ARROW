"""CLI: lê a saída do `DataAudit.mq5` e emite o veredicto de fuso.

    .venv\\Scripts\\python.exe research\\audit_broker.py

Consome `data/audit/symbol_spec.csv` e `data/audit/daily_breaks.csv`, escritos
pelo `MQL5/Scripts/ARROW/DataAudit.mq5`, e produz `reports/broker-audit.md`.

## O veredicto de fuso

A manutenção do COMEX é 17:00–18:00 em Nova York — 21:00–22:00 UTC no verão
americano e 22:00–23:00 UTC no inverno, porque Nova York muda e UTC não. A
parada diária do símbolo acompanha essa manutenção. Portanto:

* **A parada desliza uma hora entre julho e janeiro** → o relógio do servidor é
  fixo, e a hipótese servidor = UTC da §10.7 se sustenta.
* **A parada fica na mesma hora nas duas estações** → o servidor acompanha o
  DST americano, e todo alinhamento com a Dukascopy precisa de conversão por
  data, não por constante.

Qualquer outro resultado é sinal de que a premissa sobre o horário do COMEX
está errada, e aí o achado é esse.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
AUDIT = REPO / "data" / "audit"
REPORTS = REPO / "reports"


def _verdict(breaks: pd.DataFrame) -> tuple[str, list[str]]:
    """Compara a hora da parada entre as duas estações."""
    L: list[str] = []

    if breaks.empty:
        return "SEM DADO", ["Nenhuma parada diária encontrada. O teste não respondeu nada."]

    # A moda é mais robusta que a média aqui: dias atípicos (véspera de feriado,
    # manutenção estendida) deslocam a média e não a moda.
    resumo = (
        breaks.groupby("estacao")["parada_inicio"]
        .agg(dias="size", moda=lambda s: s.mode().iloc[0] if not s.mode().empty else None)
        .reset_index()
    )

    L += [
        "| Estação | Dias com parada | Hora de início (moda) |",
        "|---|---|---|",
    ]
    for _, r in resumo.iterrows():
        L.append(f"| {r['estacao']} | {r['dias']} | **{r['moda']}** |")
    L.append("")

    inverno = resumo.loc[resumo["estacao"] == "inverno_janeiro", "moda"]
    verao = resumo.loc[resumo["estacao"] == "verao_julho", "moda"]

    if inverno.empty or verao.empty:
        return "INCONCLUSIVO", L + [
            "**Falta uma das estações.** O teste exige as duas — com uma só ele não distingue",
            "um servidor fixo de um que desloca. Baixar mais histórico M1 e repetir.",
        ]

    hi = int(str(inverno.iloc[0]).split(":")[0])
    hv = int(str(verao.iloc[0]).split(":")[0])
    delta = hi - hv

    if delta == 1:
        return "SERVIDOR FIXO", L + [
            f"A parada desliza **{delta} hora** entre julho ({verao.iloc[0]}) e janeiro",
            f"({inverno.iloc[0]}). O relógio do servidor **não observa DST** — ele é fixo, e o",
            "deslocamento observado é o DST americano se movendo por baixo dele.",
            "",
            "**A hipótese servidor = UTC da §10.7 se sustenta**, e o alinhamento com a Dukascopy",
            "(que é UTC) pode ser feito por constante. A máscara de sessão de",
            "`research/lib/sessions.py` está correta o ano inteiro.",
        ]

    if delta == 0:
        return "SERVIDOR COM DST", L + [
            f"A parada fica na **mesma hora** nas duas estações ({verao.iloc[0]}). O servidor",
            "**acompanha o DST americano**.",
            "",
            "**Consequência dura:** o alinhamento com a Dukascopy exige conversão **por data**, e",
            "não por constante. E a máscara de sessão de `research/lib/sessions.py`, que trata os",
            "horários da §10.6 como UTC fixos, **corta na hora errada durante metade do ano** —",
            "o que invalida o recorte por hora da auditoria de σ e obriga a refazê-la.",
        ]

    return "INESPERADO", L + [
        f"Diferença de **{delta} hora(s)** entre as estações — nem 0 nem 1.",
        "Isso não é compatível com nenhuma das duas hipóteses. A premissa de que a parada",
        "diária acompanha a manutenção do COMEX provavelmente está errada, e **esse** é o achado.",
        "Não seguir adiante assumindo fuso até isto ser explicado.",
    ]


def main() -> int:
    spec_path = AUDIT / "symbol_spec.csv"
    breaks_path = AUDIT / "daily_breaks.csv"

    if not spec_path.exists():
        print(f"ERRO: {spec_path} não existe. Rode DataAudit.mq5 no MT5 primeiro.")
        return 1

    spec = pd.read_csv(spec_path)
    breaks = pd.read_csv(breaks_path) if breaks_path.exists() else pd.DataFrame()

    veredicto, linhas = _verdict(breaks)

    L = [
        "# Auditoria do broker — spec do símbolo e fuso",
        "",
        "> Gerado por `research/audit_broker.py` a partir da saída do",
        "> `MQL5/Scripts/ARROW/DataAudit.mq5`. Nenhum número aqui é estimativa.",
        "",
        f"## Veredicto de fuso: **{veredicto}**",
        "",
        *linhas,
        "",
        "> **Por que não `TimeCurrent()` vs `TimeGMT()`:** essas duas funções medem o offset no",
        "> instante da chamada. Entregam uma estação só, e um servidor que desloca uma hora em",
        "> março produz leitura idêntica a um que nunca desloca.",
        "",
        "## Spec do símbolo",
        "",
        "A tabela da §13 é premissa não verificada. Estes são os valores que o servidor responde.",
        "",
    ]

    for sym, part in spec.groupby("symbol", sort=False):
        if sym == "-":
            continue
        L += [f"### `{sym}`", "", "| Campo | Valor | Unidade |", "|---|---|---|"]
        for _, r in part.iterrows():
            un = "" if pd.isna(r["unidade"]) else str(r["unidade"])
            L.append(f"| `{r['campo']}` | {r['valor']} | {un} |")
        L.append("")

    geral = spec[spec["symbol"] == "-"]
    if not geral.empty:
        L += ["### Relógio", "", "| Campo | Valor | Unidade |", "|---|---|---|"]
        for _, r in geral.iterrows():
            un = "" if pd.isna(r["unidade"]) else str(r["unidade"])
            L.append(f"| `{r['campo']}` | {r['valor']} | {un} |")
        L.append("")

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / "broker-audit.md"
    out.write_text("\n".join(L), encoding="utf-8", newline="\n")

    if breaks_path.exists() and not breaks.empty:
        breaks.to_csv(REPORTS / "daily-breaks.csv", index=False, lineterminator="\n")

    print(f"veredicto de fuso: {veredicto}")
    print(f"relatório: {out}")
    return 0 if veredicto in ("SERVIDOR FIXO", "SERVIDOR COM DST") else 2


if __name__ == "__main__":
    raise SystemExit(main())
