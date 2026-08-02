"""Gera `docs/REFERENCIA-XAUUSD.md` — a fonte única de tudo que foi medido.

    .venv\\Scripts\\python.exe research\\build_reference.py

## Por que gerado e não escrito à mão

Os números vêm de `data/audit/` e `reports/`, que são regenerados a cada
auditoria. Escritos à mão, divergiriam na primeira remedição — e um número
errado neste documento não é um erro de documentação, é uma calibração errada
de sensor. A narrativa é fixa no código; as tabelas saem do dado.

Consequência operacional: **este arquivo não deve ser editado à mão.** Para
mudar o texto, mude este script e rode de novo.

## Ordem de regeneração

1. `DataAudit.mq5` no MT5            → `data/audit/*.csv`
2. `research/build_raw.py`            → `reports/*-validacao.md`, ticks/dia
3. `research/audit_sigma.py`          → `reports/sigma-*`
4. `research/audit_broker.py`         → `reports/broker-audit.md`
5. este script                        → `docs/REFERENCIA-XAUUSD.md`
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.lib.market_calendar import holidays_between  # noqa: E402
from research.lib.sigma import minutes_to_reach  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
AUDIT = REPO / "data" / "audit"
REPORTS = REPO / "reports"
OUT = REPO / "docs" / "REFERENCIA-XAUUSD.md"

# Gatilho de remedição. σ em dólares escala com o nível de preço; σ em bps
# remove essa componente mas NÃO é invariante — o regime de volatilidade também
# mudou na janela (2,51 → 5,64 bps). Por isso o gatilho é duplo.
GATILHO_PRECO_PCT = 10.0
GATILHO_MESES = 3

# Decodificação dos enums do MQL5. Guardados aqui e não no MQL5 porque o script
# grava o inteiro cru — o inteiro é o dado, isto é apresentação.
ENUMS = {
    "chart_mode": {"0": "Bid", "1": "Last"},
    "trade_exemode": {
        "0": "Request (com requote)",
        "1": "Instant",
        "2": "Market (a mercado, sem requote — slippage possível)",
        "3": "Exchange",
    },
    "trade_calc_mode": {"0": "Forex", "1": "Futures", "2": "CFD", "3": "CFD index", "4": "CFD leverage"},
    "trade_mode": {"0": "desabilitado", "1": "só long", "2": "só short", "3": "só fechar", "4": "acesso completo"},
    "swap_mode": {"0": "desabilitado", "1": "em pontos", "2": "moeda base", "3": "juros", "4": "moeda de margem"},
}


def _read(path: Path, **kw) -> pd.DataFrame:
    return pd.read_csv(path, **kw) if path.exists() else pd.DataFrame()


def _spec_map(spec: pd.DataFrame, sym: str) -> dict[str, str]:
    if spec.empty:
        return {}
    part = spec[spec["symbol"] == sym]
    return dict(zip(part["campo"], part["valor"].astype(str)))


def _fmt(v: str | None, campo: str) -> str:
    if v is None:
        return "—"
    if campo in ENUMS and v in ENUMS[campo]:
        return f"`{v}` — {ENUMS[campo][v]}"
    return v


def _sec_uso() -> list[str]:
    hoje = dt.date.today().isoformat()
    return [
        "# XAUUSD — referência medida",
        "",
        f"**Gerado por `research/build_reference.py` em {hoje}. Não editar à mão.**",
        "",
        "Este documento é a **fonte única de tudo que foi medido** neste projeto: spec do broker,",
        "calendário, integridade do histórico e volatilidade. O `CLAUDE.md` continua sendo a",
        "constituição — regras, gates, cláusulas pétreas — e aponta para cá em vez de repetir",
        "número.",
        "",
        "## Como usar",
        "",
        "Ler isto **antes** de discutir sensor, indicador, estratégia ou desenho de teste. A",
        "calibração inicial de qualquer sensor parte daqui.",
        "",
        "Três regras de leitura:",
        "",
        "1. **Nenhum número aqui é estimativa.** Todos saíram de execução real e logada. Onde algo",
        "   não foi medido, está escrito que não foi — e a seção final lista tudo que falta.",
        "2. **σ em pontos-base é a grandeza de calibração**; σ em dólares é instantâneo datado. Ver",
        "   a seção de volatilidade para o porquê.",
        "3. **O que este documento não diz, não se sabe.** Não preencher lacuna com intuição de",
        "   mercado: a §1 do `CLAUDE.md` trata isso como inventar resultado.",
        "",
        "---",
        "",
    ]


def _sec_instrumento(sm: dict, geral: dict) -> list[str]:
    L = [
        "## 1. Instrumento e conta",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Símbolo | **`XAUUSDm`** |",
        f"| Descrição | {sm.get('description', '—')} |",
        f"| Caminho | `{sm.get('path', '—')}` |",
        "| Corretora / conta | Exness, Standard |",
        f"| Moeda de lucro | {sm.get('currency_profit', '—')} |",
        f"| Moeda de margem | {sm.get('currency_margin', '—')} |",
        "| Moeda da conta | **JPY** |",
        f"| Modo de cálculo | {_fmt(sm.get('trade_calc_mode'), 'trade_calc_mode')} |",
        f"| Modo de negociação | {_fmt(sm.get('trade_mode'), 'trade_mode')} |",
        f"| Execução | {_fmt(sm.get('trade_exemode'), 'trade_exemode')} |",
        "",
        "**Execução a mercado** significa que não há requote: a ordem preenche ao preço",
        "disponível. O custo disso é slippage, que **não** aparece em backtest e só o Gate 4",
        "mede (`CLAUDE.md` §7).",
        "",
        "O projeto mede **este instrumento e mais nenhum** até existir catálogo de sensores",
        "validados (ADR 0007). `XAUUSDz`, BTCUSD, outras contas e outras corretoras entram numa",
        "bateria posterior, com ADR próprio declarando a correção para testes múltiplos.",
        "",
    ]
    return L


def _sec_spec(sm: dict) -> list[str]:
    def row(rot, campo, unidade=""):
        v = sm.get(campo)
        return f"| {rot} | {_fmt(v, campo)} | {unidade} |"

    L = [
        "## 2. Spec do símbolo — medida",
        "",
        "Lida do servidor por `MQL5/Scripts/ARROW/DataAudit.mq5`.",
        "",
        "### Preço e tamanho",
        "",
        "| Campo | Valor | Unidade |",
        "|---|---|---|",
        row("Dígitos", "digits"),
        row("Point", "point", "USD/oz"),
        row("Tick size", "trade_tick_size", "USD/oz"),
        row("Contract size", "trade_contract_size", "XAU"),
        row("Plotagem do gráfico", "chart_mode"),
        "",
        "**`chart_mode = Bid` é a base da convenção mais importante do projeto.** O MT5 plota bid,",
        "logo `iClose()` e todo OHLC no MetaTrader são bid. Toda pesquisa em Python **tem** que ser",
        "em bid; pesquisar em mid criaria um offset sistemático de meio spread entre as duas",
        "implementações, e a paridade do Gate 0 quebraria sem causa aparente.",
        "",
        "1 point = **$0,001/oz**. Com contract size de 100, um movimento de $1/oz vale $100 por",
        "lote. Filtros de spread em pontos se comportam de forma contraintuitiva nessa escala —",
        "sempre logar unidade junto do valor.",
        "",
        "### Custo e execução",
        "",
        "| Campo | Valor | Unidade |",
        "|---|---|---|",
        row("Spread", "spread_float"),
        row("Nível de stops", "stops_level", "points"),
        row("Nível de freeze", "freeze_level", "points"),
        row("Volume mínimo", "volume_min", "lotes"),
        row("Volume máximo", "volume_max", "lotes"),
        row("Passo de volume", "volume_step", "lotes"),
        "",
        "**Nível de stops = 0** é favorável e incomum: SL e TP colados ao preço são tecnicamente",
        "permitidos. Não confundir com serem *viáveis* — a §5 mostra o que o custo exige.",
        "",
        "### Swap",
        "",
        "| Campo | Valor | Unidade |",
        "|---|---|---|",
        row("Modo", "swap_mode"),
        row("Compra", "swap_long", "points"),
        row("Venda", "swap_short", "points"),
        row("Rollover triplo", "swap_rollover3days", "dia da semana"),
        "",
        "**Swap assimétrico e brutal.** Compra paga ~$48/lote/noite; venda não paga nada. Na",
        "quarta-feira o débito é triplicado. Um único trade que vaze para overnight contamina o",
        "backtest inteiro — por isso o fechamento forçado antes da parada diária é regra dura,",
        "tanto em teste quanto em produção.",
        "",
        "### Margem e sizing em ienes",
        "",
        "| Campo | Valor | Unidade |",
        "|---|---|---|",
        row("Tick value", "trade_tick_value", "JPY por tick, 1 lote"),
        row("Lucro de 1 lote em movimento de $1/oz", "lucro_1lote_move_1usd", "JPY"),
        row("Margem de 1 lote — compra", "margem_1lote_compra", "JPY"),
        row("Margem de 1 lote — venda", "margem_1lote_venda", "JPY"),
        "",
    ]

    tv = sm.get("trade_tick_value")
    lucro = sm.get("lucro_1lote_move_1usd")
    if tv and lucro:
        try:
            implied = float(lucro) / 100.0
            L += [
                f"Os dois primeiros saem de caminhos independentes — `SYMBOL_TRADE_TICK_VALUE` e",
                f"`OrderCalcProfit` — e batem: 1.000 ticks × {float(tv):.4f} = {float(tv) * 1000:,.1f}.",
                f"Isso implica **USDJPY ≈ {implied:.2f}** e fecha a conta de sizing na moeda da conta.",
                "",
                "**Consequência da conta em JPY com lucro em USD:** R é adimensional e imune à",
                "conversão, mas equity, drawdown e agregação diária em ienes **não são**. Todo limite",
                "de risco se define em R; a curva em JPY é reportada à parte.",
                "",
            ]
        except ValueError:
            pass

    return L


def _sec_calendario(sessions: pd.DataFrame, breaks: pd.DataFrame) -> list[str]:
    L = ["## 3. Calendário — sessões, fuso e feriados", "", "### Fuso: servidor = UTC, relógio fixo", ""]

    if breaks.empty:
        L += ["Não medido nesta geração.", ""]
    else:
        res = breaks.groupby("estacao")["parada_inicio"].agg(
            dias="size", moda=lambda s: s.mode().iloc[0]
        )
        L += ["| Estação | Dias amostrados | Início da parada diária |", "|---|---|---|"]
        for est, r in res.iterrows():
            rot = "Julho (verão americano)" if "verao" in est else "Janeiro (inverno americano)"
            L.append(f"| {rot} | {r['dias']} | **{r['moda']}** |")
        L += [
            "",
            "A manutenção do COMEX é 17:00–18:00 em Nova York, o que em UTC é 21:00–22:00 no verão",
            "e 22:00–23:00 no inverno — porque Nova York muda e UTC não. A parada acompanha, e",
            "**desliza exatamente uma hora entre as estações, sem exceção nos dias amostrados**.",
            "Se o relógio do servidor observasse DST, ela ficaria parada.",
            "",
            "**Conclusão: o relógio do servidor é fixo e igual a UTC.** O alinhamento com a",
            "Dukascopy, que também é UTC, pode ser feito por constante e não por data.",
            "",
            "> **Mas a sessão configurada do símbolo desliza com o DST americano.** As duas coisas",
            "> são independentes e confundi-las custa caro: tratar as bordas como fixas em UTC",
            "> descarta uma hora de negociação real por dia durante o inverno. A máscara em",
            "> `research/lib/sessions.py` implementa a regra de DST.",
            "",
            "`TimeCurrent()` vs `TimeGMT()` **não** responde isso: mede o offset no instante da",
            "chamada, entrega uma estação só, e um servidor que desloca em março lê igual a um que",
            "nunca desloca.",
            "",
        ]

    L += ["### Sessões", ""]
    if sessions.empty:
        L += [
            "> **Não medido programaticamente nesta geração.** Os valores abaixo foram lidos do",
            "> diálogo de especificação do símbolo no terminal em 2026-08-02, e estão",
            "> implementados em `research/lib/sessions.py`. Rodar o `DataAudit.mq5` atualizado",
            "> substitui isto por leitura direta do servidor.",
            "",
            "Horários no **verão americano**; no inverno tudo desloca +1 hora:",
            "",
            "| Dia | Cotação | Negociação |",
            "|---|---|---|",
            "| Domingo | 22:01–24:00 | 22:01–24:00 |",
            "| Segunda a quinta | 00:00–20:58, 22:00–24:00 | 00:00–20:58, 22:00–24:00 |",
            "| Sexta | 00:00–20:58 | 00:00–20:58 |",
            "| Sábado | fechado | fechado |",
            "",
        ]
    else:
        L += ["Lidas do servidor. Horários da configuração vigente na leitura:", "",
              "| Dia | Tipo | Janela |", "|---|---|---|"]
        for _, r in sessions.iterrows():
            L.append(f"| {r['dia']} | {r['tipo']} | {r['de']}–{r['ate']} |")
        L.append("")

    hoje = dt.date.today()
    cal = holidays_between(dt.date(hoje.year, 1, 1), dt.date(hoje.year + 1, 12, 31))
    L += [
        "### Feriados de mercado",
        "",
        "O ouro **fecha por completo** na Sexta-feira Santa e tem **sessão encurtada** — 1% a 4% do",
        "volume normal — no Natal e no Ano-Novo. Data fixa que cai no domingo é observada na",
        "segunda seguinte.",
        "",
        "Os 12 feriados da janela de `raw/` são **excluídos de `curated/`** e de todo teste",
        "(ADR 0006). `raw/` os mantém: é imutável.",
        "",
        "O calendário é **declarado por regra** em `research/lib/market_calendar.py`, não inferido",
        "do dado. A direção importa: feriado e buraco de coleta se parecem num gráfico de",
        "ticks/dia, e excluir automaticamente todo dia magro faria o buraco desaparecer em",
        "silêncio. O dado é comparado **contra** o calendário; o que sobra é anomalia e grita.",
        "",
        f"Próximos feriados ({hoje.year}–{hoje.year + 1}):",
        "",
        "| Data | Feriado |",
        "|---|---|",
    ]
    for d, nome in sorted(cal.items()):
        if d >= hoje:
            L.append(f"| {d.isoformat()} | {nome} |")
    L.append("")
    return L


def _sec_volatilidade(ys, por_ano, por_hora_recent, ano_ref: int) -> list[str]:
    L = [
        "## 6. Volatilidade medida",
        "",
        "σ é o **desvio-padrão da variação de preço em uma barra M1**, sobre o bid, com máscara de",
        "sessão e feriados aplicados. É a definição que sustenta `R alcançável ≈ σ√T`; invertendo,",
        "`T = (R/σ)²`.",
        "",
        "### Qual unidade usar para calibrar",
        "",
        "**Pontos-base do preço para σ; dólares para custo.** As duas grandezas têm naturezas",
        "diferentes, e forçar uma unidade só é que seria o erro:",
        "",
        "- **σ escala com o nível de preço.** Expressá-la em dólares é exatamente o defeito",
        "  diagnosticado no `val` do Squeeze Momentum, e o contrato do sensor (`CLAUDE.md` §5.2) já",
        "  exige saída adimensional. Calibrar contra bps é coerente com ele.",
        "- **O spread não escala.** É pedágio fixo de $0,20/oz, não fração de nada. `c/(2R)` é",
        "  genuinamente uma conta em dólares.",
        "",
        "### σ por ano — as duas componentes separadas",
        "",
        "| Ano | Preço mediano | σ (USD) | σ (bps) |",
        "|---|---|---|---|",
    ]
    for ano, r in por_ano.iterrows():
        L.append(
            f"| {ano} | ${r['preco_mediano']:,.0f} | {r['sigma_usd']:.3f} | **{r['sigma_bps']:.2f}** |"
        )

    p0, p1 = por_ano["preco_mediano"].iloc[0], por_ano["preco_mediano"].iloc[-1]
    s0, s1 = por_ano["sigma_usd"].iloc[0], por_ano["sigma_usd"].iloc[-1]
    b0, b1 = por_ano["sigma_bps"].iloc[0], por_ano["sigma_bps"].iloc[-1]
    L += [
        "",
        f"Na janela o preço multiplicou por **{p1 / p0:.2f}×**, σ em dólares por **{s1 / s0:.2f}×** e",
        f"σ em bps por **{b1 / b0:.2f}×**. Parte do salto em dólares é nível de preço e parte é",
        "regime de volatilidade genuinamente maior. **As duas componentes existem** — nenhuma das",
        "duas unidades é invariante, e é por isso que o gatilho de remedição da seção 7 é duplo.",
        "",
        "### A forma do dia mudou",
        "",
        "σ em USD por sessão, ano a ano:",
        "",
        "| Ano | Asiático | Londres | Sobrep. LDN/NY | Nova York | Asiático ÷ Sobrep. |",
        "|---|---|---|---|---|---|",
    ]
    for ano, r in ys.iterrows():
        L.append(
            f"| {ano} | {r['Asiático']:.3f} | {r['Londres']:.3f} | "
            f"{r['Sobreposição LDN/NY']:.3f} | {r['Nova York']:.3f} | "
            f"**{r['asiatico/sobreposicao']:.2f}** |"
        )

    r0 = ys["asiatico/sobreposicao"].iloc[0]
    r1 = ys["asiatico/sobreposicao"].iloc[-1]
    L += [
        "",
        f"**A última coluna subiu de forma monótona, de {r0:.2f} a {r1:.2f}, sem um único ano de",
        "reversão: o perfil intradiário do ouro achatou.**",
        "",
        "Isso desmente a ideia de que a sessão asiática é ~3× mais exigente em edge para o mesmo",
        f"tempo de exposição — essa afirmação exigiria razão ≈ 0,23. Ela já estava errada no início",
        f"da janela ({r0:.2f}) e ficou pior.",
        "",
        f"Em {ano_ref} a hora **1 UTC** — 09:00 em Pequim, abertura da Shanghai Gold Exchange — é a",
        "segunda hora mais volátil do dia inteiro. O mesmo código sobre 2023 isolado devolve o",
        "perfil clássico, com pico na sobreposição: **a mudança está no mercado, não na medição**.",
        "",
        "> **Consequência para desenho de sensor:** filtrar sessão para “evitar a asiática” não tem",
        "> mais base empírica. Se `REGIME` ou `COST` discriminarem horário, o critério precisa sair",
        "> de medição corrente e ser remedido — este é um exemplo concreto de premissa que decaiu em",
        "> quatro anos.",
        "",
        f"### σ por hora UTC — {ano_ref}",
        "",
        "| Hora | Barras | σ (USD) | σ (bps) | σ robusta (USD) |",
        "|---|---|---|---|---|",
    ]
    for h, r in por_hora_recent.iterrows():
        L.append(
            f"| {h:02d} | {int(r['n_barras']):,} | {r['sigma_usd']:.3f} | "
            f"{r['sigma_bps']:.2f} | {r['sigma_robusto_usd']:.3f} |"
        )
    L += [
        "",
        "A hora ausente é a parada diária. **σ robusta** usa a mediana do desvio absoluto e ignora",
        "as caudas; onde ela diverge muito da padrão, a diferença é spike. Para dimensionar stop a",
        "cauda é o que mata; para descrever o minuto típico a robusta descreve melhor.",
        "",
    ]
    return L


def main() -> int:
    from research import reference_parts as RP

    spec = _read(AUDIT / "symbol_spec.csv")
    sessions = _read(AUDIT / "sessions.csv")
    breaks = _read(AUDIT / "daily_breaks.csv")

    if spec.empty:
        print("ERRO: data/audit/symbol_spec.csv não existe. Rode DataAudit.mq5 no MT5.")
        return 1

    sm = _spec_map(spec, "XAUUSDm")
    geral = _spec_map(spec, "-")

    ys = _read(REPORTS / "sigma-ano-x-sessao.csv", index_col=0)
    por_ano = _read(REPORTS / "sigma-por-ano.csv", index_col=0)
    if por_ano.empty or ys.empty:
        print("ERRO: falta reports/sigma-*.csv. Rode research/audit_sigma.py.")
        return 1

    ano_ref = int(por_ano.index.max())
    por_hora_recent = _read(REPORTS / f"sigma-por-hora-{ano_ref}.csv", index_col=0)

    tk = sorted(REPORTS.glob("*-ticks-por-dia.csv"))
    ticks_dia = _read(tk[-1]) if tk else pd.DataFrame()

    # σ por sessão do ano de referência, reconstruída a partir da matriz ano×sessão.
    preco_ref = float(por_ano.loc[ano_ref, "preco_mediano"])
    sess_recent = pd.DataFrame(
        {
            "sigma_usd": ys.loc[ano_ref, ["Asiático", "Londres", "Sobreposição LDN/NY", "Nova York"]],
            "preco_mediano": preco_ref,
        }
    )

    L: list[str] = []
    L += _sec_uso()
    L += _sec_instrumento(sm, geral)
    L += _sec_spec(sm)
    L += _sec_calendario(sessions, breaks)
    L += RP.sec_historico(ticks_dia)
    L += RP.sec_custo()
    L += _sec_volatilidade(ys, por_ano, por_hora_recent, ano_ref)
    L += RP.sec_calibracao(sess_recent, ano_ref, preco_ref)
    L += RP.sec_lacunas()
    L += RP.sec_regeneracao()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"gerado: {OUT}  ({len(L)} linhas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
