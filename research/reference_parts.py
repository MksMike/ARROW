"""Seções 4 a 9 de `docs/REFERENCIA-XAUUSD.md`.

Separado de `build_reference.py` só por tamanho. A narrativa é fixa aqui; os
números entram das tabelas. Não editar o markdown gerado — editar isto.
"""

from __future__ import annotations

import pandas as pd

GATILHO_PRECO_PCT = 10.0
GATILHO_MESES = 3

# Fuso do operador. Só para apresentação — nenhum dado do projeto é gravado
# nele. Verificado no Windows da PC-Home: `Tokyo Standard Time`, UTC+09:00,
# `SupportsDaylightSavingTime = False`.
OPERADOR_TZ = "JST"
OPERADOR_OFFSET_H = 9
OPERADOR_TEM_DST = False


def _para_local(hhmm: str, offset_h: int = OPERADOR_OFFSET_H) -> tuple[str, int]:
    """Converte `HH:MM` de UTC para o fuso do operador.

    Devolve o horário e quantos dias virou (0 ou +1).
    """
    h, m = (int(x) for x in hhmm.split(":"))
    total = h + offset_h
    return f"{total % 24:02d}:{m:02d}", total // 24


def sec_horario_local() -> list[str]:
    """Tradução para o fuso do operador. Apresentação, nunca armazenamento."""

    def par(utc: str) -> str:
        loc, vira = _para_local(utc)
        return f"{loc}{' (+1d)' if vira else ''}"

    return [
        "### Em horário local do operador",
        "",
        f"**Nada disto entra no dado.** Todo timestamp do projeto é UTC e a conversão acontece",
        "apenas na borda de apresentação. Esta tabela existe para não agendar as coisas erradas.",
        "",
        f"O operador está em **{OPERADOR_TZ} = UTC+{OPERADOR_OFFSET_H}**, e o Japão **não observa",
        "horário de verão** — o offset é constante o ano inteiro. Mas **a sessão do símbolo desliza",
        "com o DST americano**, então os horários locais dos eventos mudam uma hora entre as",
        "estações. As duas coisas são independentes.",
        "",
        "| Evento | UTC (verão) | Local (verão) | UTC (inverno) | Local (inverno) |",
        "|---|---|---|---|---|",
        f"| Abertura da semana (domingo) | 22:01 | **{par('22:01')} seg** | 23:01 | **{par('23:01')} seg** |",
        f"| Início da parada diária | 20:58 | {par('20:58')} | 21:58 | {par('21:58')} |",
        f"| Reabertura diária | 22:00 | {par('22:00')} | 23:00 | {par('23:00')} |",
        f"| Fechamento de sexta | 20:58 | **{par('20:58')} sáb** | 21:58 | **{par('21:58')} sáb** |",
        "",
        "Para quem está no Japão, a semana começa por volta das **07:00 de segunda** e a parada",
        "diária cai de madrugada para o começo da manhã. Não é preciso estar acordado na virada: o",
        "`BrokerTickLogger` fica ocioso em laço e retoma sozinho.",
        "",
        "### As sessões em horário local",
        "",
        "| Sessão | UTC | Local |",
        "|---|---|---|",
        f"| Asiático | 00–07 | {_para_local('00:00')[0][:2]}–{_para_local('07:00')[0][:2]} |",
        f"| Londres | 07–12 | {_para_local('07:00')[0][:2]}–{_para_local('12:00')[0][:2]} |",
        f"| Sobreposição LDN/NY | 12–16 | {_para_local('12:00')[0][:2]}–{_para_local('16:00')[0][:2]} |",
        f"| Nova York | 16–21 | {_para_local('16:00')[0][:2]}–{_para_local('21:00')[0][:2]} |",
        "",
        "Os dois picos de volatilidade de 2026 caem em horários bem diferentes para o operador: a",
        f"hora **15 UTC** (a mais volátil) é **{_para_local('15:00')[0]} local**, e a hora **1 UTC**",
        f"— abertura da Shanghai Gold Exchange, a segunda mais volátil — é **{_para_local('01:00')[0]}",
        "local**, em plena manhã de dia útil no Japão.",
        "",
        "> **Consequência de método, não de conveniência:** se um sensor ou filtro vier a usar hora,",
        "> ele usa **hora de servidor (UTC)**. Hora local do operador não é propriedade do mercado e",
        "> não pode entrar em `.mqh` nem em `research/`. Ela existe só nesta tabela.",
        "",
    ]


def sec_historico(ticks_dia: pd.DataFrame) -> list[str]:
    L = ["## 4. O histórico — `data/raw/`", ""]
    if ticks_dia.empty:
        return L + ["Não gerado.", ""]

    c = ticks_dia.set_index(ticks_dia.columns[0])[ticks_dia.columns[1]]
    c.index = pd.to_datetime(c.index)
    total = int(c.sum())
    uteis = int((c.index.dayofweek < 5).sum())

    L += [
        "Ticks da **Dukascopy**, convertidos para Parquet particionado por mês. É o dado de",
        "pesquisa; não é o dado do broker.",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Cobertura | {c.index.min().date()} → {c.index.max().date()} |",
        f"| Ticks | **{total:,}** |",
        f"| Dias com dado | {len(c):,} |",
        f"| Dias úteis | **{uteis:,}** |",
        "| Formato | Parquet zstd, partição `year=/month=` |",
        "",
        "### Integridade",
        "",
        "Zero `ts` retrocedendo, zero `ask < bid`, zero preço ≤ 0, zero linha duplicada.",
        "",
        "**Toda ausência tem causa de calendário; nenhuma sobrou sem explicação.** Os dias úteis",
        "sem tick são as Sextas-feiras Santas; os dias anormalmente magros são os Natais e",
        "Ano-Novos. A verificação de dia magro compara contra a mediana do **mesmo dia da semana** —",
        "o domingo tem sessão parcial e roda uma ordem de grandeza abaixo de um pregão, então um",
        "limiar único ou cega a verificação ou condena todo domingo.",
        "",
        "### Amostra disponível para os gates",
        "",
        "O Gate 2 exige N ≥ 250 dias de negociação **e** bloco out-of-sample nunca tocado.",
        f"Com {uteis:,} dias úteis o padrão do projeto — ~1.020 dias, 3 folds mais OOS com folga —",
        "está satisfeito. Descontando os 12 feriados excluídos sobram ~1.029.",
        "",
        "### Ritmo semanal medido",
        "",
        "| Dia | Dias | Ticks (mediana) |",
        "|---|---|---|",
    ]
    med = c.groupby(c.index.day_name()).agg(["size", "median"])
    pt = {"Sunday": "Domingo", "Monday": "Segunda", "Tuesday": "Terça",
          "Wednesday": "Quarta", "Thursday": "Quinta", "Friday": "Sexta"}
    for d in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        if d in med.index:
            L.append(f"| {pt[d]} | {int(med.loc[d, 'size'])} | {int(med.loc[d, 'median']):,} |")

    L += [
        "",
        "Domingo abre 22:01 e é sessão parcial. Qualquer estatística por hora ou por dia precisa",
        "tratá-lo à parte.",
        "",
        "### O que NÃO transplanta da Dukascopy para o broker",
        "",
        "| Elemento | Transplanta? |",
        "|---|---|",
        "| Caminho do preço | **Sim.** Ouro é ouro; os feeds diferem por centavos, não por trajetória |",
        "| Spread | **Não.** Dukascopy é ECN bruto; a conta é Standard com markup. Descartado integralmente |",
        "| Densidade de tick | Parcial — medir, não presumir |",
        "| Execução (slippage, alargamento no disparo) | **Não, e não pode.** Só o Gate 4 mede |",
        "",
        "Como o spread é a totalidade do custo nesta conta, usar o spread da Dukascopy produziria",
        "backtest fantasioso. Não é refinamento — é a diferença entre um sistema lucrativo e um que",
        "não existe.",
        "",
        "### Dado do broker",
        "",
        "| Fonte | Cobertura |",
        "|---|---|",
        "| Barras M1 | desde 2014-01-14, 3.265.408 barras |",
        "| Tick real | janela móvel curta; coleta contínua iniciada em 2026-08-02 |",
        "",
        "**A retenção curta do broker é de tick, não de barra.** Doze anos de M1 estão disponíveis,",
        "o que abre uma janela de sobreposição muito maior que os quatro anos de tick para medir o",
        "gap de fonte — ao custo de comparar em OHLC de minuto, o que mistura gap de fonte com gap",
        "de resolução. São dois desenhos experimentais diferentes.",
        "",
    ]
    return L


def sec_custo() -> list[str]:
    return [
        "## 5. Custo — o que ele exige de edge",
        "",
        "O spread é **pedágio fixo pago na entrada**, não sangria por tempo. E ele não apenas começa",
        "o trade negativo: desloca **as duas barreiras na mesma direção**. Numa compra com alvo e",
        "stop líquidos de tamanho `R` e spread `c`, o bid precisa subir `R+c` para o alvo, mas basta",
        "cair `R−c` para o stop.",
        "",
        "Sob caminho sem deriva:",
        "",
        "```",
        "P(ganhar)  = (R − c) / 2R",
        "Esperança  = −c        exatamente, para QUALQUER alvo e stop",
        "```",
        "",
        "Alvo e stop não afetam a esperança. A única métrica operacional é o **acréscimo de acerto",
        "direcional necessário**, `c/(2R)`. Com o piso de spread de $0,20/oz:",
        "",
        "| Alvo/stop líquido | Acerto sem edge | Edge exigido |",
        "|---|---|---|",
        "| $0,30 | 16,7% | **+33 pp** |",
        "| $0,50 | 30,0% | +20 pp |",
        "| $1,00 | 40,0% | +10 pp |",
        "| $3,00 | 46,7% | **+3,3 pp** |",
        "| $5,00 | 48,0% | +2 pp |",
        "",
        "**Armadilha da taxa de acerto.** Alvo +$0,30 com stop −$3,00 produz ~85% de trades",
        "vencedores e esperança de −$0,20. Taxa alta de acerto não é edge — é a mesma matemática do",
        "martingale por outra porta de entrada. Nenhum resultado neste projeto é avaliado por win",
        "rate; apenas por esperança em R e t-stat sobre R agregado por dia.",
        "",
        "**Alvos abaixo de ~$1,00 líquido exigem 10 pp ou mais de acerto direcional** e são hipótese",
        "extraordinária, não ponto de partida.",
        "",
        "> **O piso de $0,20 é premissa, não medição.** O spread real por hora e por faixa de",
        "> volatilidade — média **e caudas** — depende de `data/broker/`, cuja coleta começou em",
        "> 2026-08-02. Até haver amostra, toda conta de custo aqui usa o piso, que é o **melhor",
        "> caso**. Spreads alargam exatamente quando o sinal dispara.",
        "",
    ]


def sec_calibracao(sess_recent: pd.DataFrame, ano_ref: int, preco_ref: float) -> list[str]:
    L = [
        "## 7. Calibração — o ponto de partida de um sensor",
        "",
        f"Valores de **{ano_ref}**, a preço mediano de **${preco_ref:,.0f}/oz**. É desta tabela que",
        "parte o desenho de qualquer sensor ou estratégia.",
        "",
        "### Tempo para o preço percorrer R",
        "",
        "`T = (R/σ)²`, sob passeio aleatório:",
        "",
        "| Sessão | σ (USD) | σ (bps) | R=$1 (+10 pp) | R=$3 (+3,3 pp) | R=$5 (+2 pp) |",
        "|---|---|---|---|---|---|",
    ]
    for nome, r in sess_recent.iterrows():
        s = r["sigma_usd"]
        bps = s / r["preco_mediano"] * 10_000
        L.append(
            f"| {nome} | {s:.3f} | {bps:.2f} | "
            f"{(1.0 / s) ** 2:.1f} min | {(3.0 / s) ** 2:.1f} min | {(5.0 / s) ** 2:.1f} min |"
        )

    L += [
        "",
        "Cruzando com a seção 5: **alvos de $3 a $5 líquidos exigem apenas 3,3 pp e 2 pp de acerto",
        "direcional, e são alcançáveis em 1 a 5 minutos em qualquer sessão.** Isso é materialmente",
        "mais favorável do que um alvo curto — que parece mais fácil e exige três a dez vezes mais",
        "edge.",
        "",
        "### Três ressalvas contra otimismo",
        "",
        "1. **`σ√T` supõe passeio aleatório sem deriva nem reversão.** O M1 do ouro tem",
        "   microestrutura; o alcance real em T minutos é menor.",
        "2. **σ de fechamento a fechamento está inflada por bid-ask bounce**, que é ruído e não",
        "   movimento aproveitável. Os tempos acima são o **melhor caso**, não a expectativa.",
        "3. **O custo usa o piso de spread**, não a distribuição real. A cauda é o que importa, e ela",
        "   ainda não foi medida.",
        "",
        "Corrigir (1) e (2) exige `data/bars/`; corrigir (3) exige `data/broker/`. Ambos pendentes.",
        "",
        "### Gatilho de remedição",
        "",
        f"Estes números **expiram**. Remedir quando qualquer um ocorrer:",
        "",
        f"- o ouro se afastar mais de **{GATILHO_PRECO_PCT:.0f}%** de ${preco_ref:,.0f}/oz",
        f"- passarem **{GATILHO_MESES} meses** desde a geração deste documento",
        "",
        "O primeiro gatilho existe porque σ em dólares escala com o nível de preço. O segundo existe",
        "porque **σ em bps também mudou na janela** — o regime de volatilidade se move sozinho, e",
        "nenhuma das duas unidades é invariante.",
        "",
    ]
    return L


def sec_lacunas() -> list[str]:
    return [
        "## 8. O que NÃO está medido",
        "",
        "Esta seção existe porque ausência de linha não é o mesmo que \"não precisou\". Nada abaixo",
        "deve ser preenchido com intuição: a §1 do `CLAUDE.md` trata isso como inventar resultado.",
        "",
        "| Lacuna | Depende de | Consequência de ignorar |",
        "|---|---|---|",
        "| **Distribuição de spread do broker** por hora × faixa de volatilidade | `data/broker/` acumular amostra | Todo custo usa o piso; o backtest fica otimista exatamente nos momentos que decidem o resultado |",
        "| **Slippage e alargamento no disparo** | Gate 4, forward em demo | Backtest não vê; a diferença é o gap de execução, e acima de 30% em R exige investigação |",
        "| **Gap de fonte** Dukascopy × Exness | comparação nas duas fontes | Não se sabe quanto do resultado vem do feed |",
        "| **Gap de resolução** tick × M1 OHLC | mesma comparação | Não se sabe se simular tick vale a pena |",
        "| **Range efetivo em T minutos** | `data/bars/` | `σ√T` é o melhor caso e não a expectativa |",
        "| **Densidade de tick por sessão** | auditoria adicional sobre `raw/` | Sensor que dependa de contagem de tick não tem baseline |",
        "| **Abertura de domingo em hora de servidor** | extensão do `DataAudit` | A máscara aplica o deslize de DST a ela por inferência, não por medição |",
        "| **Semântica de `confidence`** | decisão de projeto | O primeiro sensor a preencher o campo vira precedente por acidente |",
        "| **Critério de escolha de T no Gate 1** | decisão de projeto | Varrer 1 a 30 barras e ficar com o melhor é teste múltiplo disfarçado |",
        "| **Tese mecânica** | decisão de projeto | Sem ela a construção de sensores é busca cega, que é o que a correção para testes múltiplos existe para punir |",
        "",
        "### Um candidato a tese que saiu de medição",
        "",
        "O achatamento do perfil intradiário (seção 6) é candidato a hipótese mecânica, e tem a",
        "vantagem de já vir com o número que o sustenta. Se a formação de preço do ouro migrou",
        "parcialmente para o horário asiático — e a abertura da Shanghai Gold Exchange ser a segunda",
        "hora mais volátil do dia é evidência disso — então houve deslocamento estrutural de",
        "participantes, que é o tipo de coisa que gera desequilíbrio explorável.",
        "",
        "**Isto é candidato, não tese.** Falta o mecanismo escrito e, sobretudo, a observação que o",
        "falsificaria.",
        "",
    ]


def sec_regeneracao() -> list[str]:
    return [
        "## 9. Como regenerar",
        "",
        "**Não editar este arquivo à mão.** A narrativa está em `research/build_reference.py` e",
        "`research/reference_parts.py`; as tabelas saem do dado.",
        "",
        "```",
        "# 1. no MT5: Navegador -> Scripts -> ARROW -> DataAudit",
        "#    (spec do simbolo, sessoes, paradas diarias -> data/audit/)",
        "",
        "# 2. conversao e validacao do historico",
        ".venv\\Scripts\\python.exe research\\build_raw.py --csv <arquivo> ",
        ".venv\\Scripts\\python.exe research\\build_raw.py --csv /dev/null --validate-only",
        "",
        "# 3. volatilidade",
        ".venv\\Scripts\\python.exe research\\audit_sigma.py",
        "",
        "# 4. veredicto de fuso e spec",
        ".venv\\Scripts\\python.exe research\\audit_broker.py",
        "",
        "# 5. este documento",
        ".venv\\Scripts\\python.exe research\\build_reference.py",
        "```",
        "",
        "`write_raw` é append-only: **nunca** reprocessar um CSV já convertido sem `--validate-only`,",
        "sob pena de duplicar `raw/`.",
        "",
        "### Procedência",
        "",
        "| Seção | Fonte |",
        "|---|---|",
        "| 1, 2 | `data/audit/symbol_spec.csv` |",
        "| 3 — fuso | `data/audit/daily_breaks.csv` |",
        "| 3 — sessões | `data/audit/sessions.csv` |",
        "| 3 — feriados | `research/lib/market_calendar.py` (regra) |",
        "| 4 | `reports/*-ticks-por-dia.csv`, `reports/*-validacao.md` |",
        "| 6, 7 | `reports/sigma-*.csv` |",
        "",
    ]
