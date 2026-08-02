# XAUUSD — referência medida

**Gerado por `research/build_reference.py` em 2026-08-02. Não editar à mão.**

Este documento é a **fonte única de tudo que foi medido** neste projeto: spec do broker,
calendário, integridade do histórico e volatilidade. O `CLAUDE.md` continua sendo a
constituição — regras, gates, cláusulas pétreas — e aponta para cá em vez de repetir
número.

## Como usar

Ler isto **antes** de discutir sensor, indicador, estratégia ou desenho de teste. A
calibração inicial de qualquer sensor parte daqui.

Três regras de leitura:

1. **Nenhum número aqui é estimativa.** Todos saíram de execução real e logada. Onde algo
   não foi medido, está escrito que não foi — e a seção final lista tudo que falta.
2. **σ em pontos-base é a grandeza de calibração**; σ em dólares é instantâneo datado. Ver
   a seção de volatilidade para o porquê.
3. **O que este documento não diz, não se sabe.** Não preencher lacuna com intuição de
   mercado: a §1 do `CLAUDE.md` trata isso como inventar resultado.

---

## 1. Instrumento e conta

| Campo | Valor |
|---|---|
| Símbolo | **`XAUUSDm`** |
| Descrição | Gold vs US Dollar |
| Caminho | `Standard\Forex\XAUUSDm` |
| Corretora / conta | Exness, Standard |
| Moeda de lucro | USD |
| Moeda de margem | XAU |
| Moeda da conta | **JPY** |
| Modo de cálculo | `0` — Forex |
| Modo de negociação | `4` — acesso completo |
| Execução | `2` — Market (a mercado, sem requote — slippage possível) |

**Execução a mercado** significa que não há requote: a ordem preenche ao preço
disponível. O custo disso é slippage, que **não** aparece em backtest e só o Gate 4
mede (`CLAUDE.md` §7).

### Ordens aceitas

| Campo | Valor |
|---|---|
| Tipos de ordem | `127` — mercado, limit, stop, stop-limit, SL, TP, close-by |
| Políticas de preenchimento | `3` — FOK (tudo ou nada), IOC (tudo ou parcial) |
| Modos de validade | `15` — GTC, DAY, data específica, dia específico |

Todos os tipos de ordem estão liberados, incluindo **SL e TP anexados**, que combinados com
nível de stops zero permitem stops apertados sem restrição técnica. Ordem limitada está
disponível — é a única forma de não pagar o spread, ao custo de seleção adversa, e está
registrada como linha futura.

O projeto mede **este instrumento e mais nenhum** até existir catálogo de sensores
validados (ADR 0007). `XAUUSDz`, BTCUSD, outras contas e outras corretoras entram numa
bateria posterior, com ADR próprio declarando a correção para testes múltiplos.

## 2. Spec do símbolo — medida

Lida do servidor por `MQL5/Scripts/ARROW/DataAudit.mq5`.

### Preço e tamanho

| Campo | Valor | Unidade |
|---|---|---|
| Dígitos | 3 |  |
| Point | 0.00100000 | USD/oz |
| Tick size | 0.00100000 | USD/oz |
| Contract size | 100.00 | XAU |
| Plotagem do gráfico | `0` — Bid |  |

**`chart_mode = Bid` é a base da convenção mais importante do projeto.** O MT5 plota bid,
logo `iClose()` e todo OHLC no MetaTrader são bid. Toda pesquisa em Python **tem** que ser
em bid; pesquisar em mid criaria um offset sistemático de meio spread entre as duas
implementações, e a paridade do Gate 0 quebraria sem causa aparente.

1 point = **$0,001/oz**. Com contract size de 100, um movimento de $1/oz vale $100 por
lote. Filtros de spread em pontos se comportam de forma contraintuitiva nessa escala —
sempre logar unidade junto do valor.

### Custo e execução

| Campo | Valor | Unidade |
|---|---|---|
| Spread | flutuante | — |
| Nível de stops | 0 | points |
| Nível de freeze | 0 | points |
| Volume mínimo | 0.01 | lotes |
| Volume máximo | 200.00 | lotes |
| Passo de volume | 0.01 | lotes |

**Nível de stops = 0** é favorável e incomum: SL e TP colados ao preço são tecnicamente
permitidos. Não confundir com serem *viáveis* — a §5 mostra o que o custo exige.

### Swap

| Campo | Valor | Unidade |
|---|---|---|
| Modo | `1` — em pontos |  |
| Compra | -482.5000 | points |
| Venda | 0.0000 | points |
| Rollover triplo | 3 | dia da semana |

**Swap assimétrico e brutal.** Compra paga ~$48/lote/noite; venda não paga nada. Na
quarta-feira o débito é triplicado. Um único trade que vaze para overnight contamina o
backtest inteiro — por isso o fechamento forçado antes da parada diária é regra dura,
tanto em teste quanto em produção.

### Margem e sizing em ienes

| Campo | Valor | Unidade |
|---|---|---|
| Tick value | 15.74270000 | JPY por tick, 1 lote |
| Lucro de 1 lote em movimento de $1/oz | 15743.00 | JPY |
| Margem de 1 lote — compra | 31844.00 | JPY |
| Margem de 1 lote — venda | 31830.00 | JPY |

Os dois primeiros saem de caminhos independentes — `SYMBOL_TRADE_TICK_VALUE` e
`OrderCalcProfit` — e batem: 1.000 × 15.7427 = 15,742.7.
Isso implica **USDJPY ≈ 157.43** e fecha a conta de sizing na moeda da conta.

**Consequência da conta em JPY com lucro em USD:** R é adimensional e imune à
conversão, mas equity, drawdown e agregação diária em ienes **não são**. Todo limite
de risco se define em R; a curva em JPY é reportada à parte.

**Alavancagem derivada: 1:1,999.** Valor de contrato de 100 oz a
$4,043.81 convertido a USDJPY ≈ 157.43 dá ¥63,660,519, contra
margem de ¥31,844. Não é premissa — sai da divisão de dois campos medidos.

**Margem não é restrição, e o broker não oferece proteção alguma.** Todo controle de
risco vive na EA. **Stop obrigatório em toda ordem, sem exceção.**

## 3. Calendário — sessões, fuso e feriados

### Fuso: servidor = UTC, relógio fixo

| Estação | Dias amostrados | Início da parada diária |
|---|---|---|
| Janeiro (inverno americano) | 15 | **21:58** |
| Julho (verão americano) | 16 | **20:58** |

A manutenção do COMEX é 17:00–18:00 em Nova York, o que em UTC é 21:00–22:00 no verão
e 22:00–23:00 no inverno — porque Nova York muda e UTC não. A parada acompanha, e
**desliza exatamente uma hora entre as estações, sem exceção nos dias amostrados**.
Se o relógio do servidor observasse DST, ela ficaria parada.

**Conclusão: o relógio do servidor é fixo e igual a UTC.** O alinhamento com a
Dukascopy, que também é UTC, pode ser feito por constante e não por data.

> **Mas a sessão configurada do símbolo desliza com o DST americano.** As duas coisas
> são independentes e confundi-las custa caro: tratar as bordas como fixas em UTC
> descarta uma hora de negociação real por dia durante o inverno. A máscara em
> `research/lib/sessions.py` implementa a regra de DST.

`TimeCurrent()` vs `TimeGMT()` **não** responde isso: mede o offset no instante da
chamada, entrega uma estação só, e um servidor que desloca em março lê igual a um que
nunca desloca.

### Sessões

**Lidas do servidor** por `SymbolInfoSessionQuote` / `SymbolInfoSessionTrade`, não
transcritas. Configuração vigente na leitura — verão americano; no inverno tudo
desloca +1 hora.

| Dia | Cotação | Negociação |
|---|---|---|
| domingo | 22:01–00:00 | 22:01–00:00 |
| segunda | 00:00–20:58, 22:00–00:00 | 00:00–20:58, 22:00–00:00 |
| terca | 00:00–20:58, 22:00–00:00 | 00:00–20:58, 22:00–00:00 |
| quarta | 00:00–20:58, 22:00–00:00 | 00:00–20:58, 22:00–00:00 |
| quinta | 00:00–20:58, 22:00–00:00 | 00:00–20:58, 22:00–00:00 |
| sexta | 00:00–20:58 | 00:00–20:58 |
| sabado | fechado | fechado |

**Cotação e negociação abrem juntas** em todos os dias — não há janela em que o preço
se move sem que se possa operar. A máscara em `research/lib/sessions.py` implementa
exatamente este cronograma, com a regra de DST.

### Feriados de mercado

O ouro **fecha por completo** na Sexta-feira Santa e tem **sessão encurtada** — 1% a 4% do
volume normal — no Natal e no Ano-Novo. Data fixa que cai no domingo é observada na
segunda seguinte.

Os 12 feriados da janela de `raw/` são **excluídos de `curated/`** e de todo teste
(ADR 0006). `raw/` os mantém: é imutável.

O calendário é **declarado por regra** em `research/lib/market_calendar.py`, não inferido
do dado. A direção importa: feriado e buraco de coleta se parecem num gráfico de
ticks/dia, e excluir automaticamente todo dia magro faria o buraco desaparecer em
silêncio. O dado é comparado **contra** o calendário; o que sobra é anomalia e grita.

Próximos feriados (2026–2027):

| Data | Feriado |
|---|---|
| 2026-12-25 | Natal |
| 2027-01-01 | Ano-Novo |
| 2027-03-26 | Sexta-feira Santa |
| 2027-12-24 | Natal |

### Em horário local do operador

**Nada disto entra no dado.** Todo timestamp do projeto é UTC e a conversão acontece
apenas na borda de apresentação. Esta tabela existe para não agendar as coisas erradas.

O operador está em **JST = UTC+9**, e o Japão **não observa
horário de verão** — o offset é constante o ano inteiro. Mas **a sessão do símbolo desliza
com o DST americano**, então os horários locais dos eventos mudam uma hora entre as
estações. As duas coisas são independentes.

| Evento | UTC (verão) | Local (verão) | UTC (inverno) | Local (inverno) |
|---|---|---|---|---|
| Abertura da semana (domingo) | 22:01 | **07:01 (+1d) seg** | 23:01 | **08:01 (+1d) seg** |
| Início da parada diária | 20:58 | 05:58 (+1d) | 21:58 | 06:58 (+1d) |
| Reabertura diária | 22:00 | 07:00 (+1d) | 23:00 | 08:00 (+1d) |
| Fechamento de sexta | 20:58 | **05:58 (+1d) sáb** | 21:58 | **06:58 (+1d) sáb** |

Para quem está no Japão, a semana começa por volta das **07:00 de segunda** e a parada
diária cai de madrugada para o começo da manhã. Não é preciso estar acordado na virada: o
`BrokerTickLogger` fica ocioso em laço e retoma sozinho.

### As sessões em horário local

| Sessão | UTC | Local |
|---|---|---|
| Asiático | 00–07 | 09–16 |
| Londres | 07–12 | 16–21 |
| Sobreposição LDN/NY | 12–16 | 21–01 |
| Nova York | 16–21 | 01–06 |

Os dois picos de volatilidade de 2026 caem em horários bem diferentes para o operador: a
hora **15 UTC** (a mais volátil) é **00:00 local**, e a hora **1 UTC**
— abertura da Shanghai Gold Exchange, a segunda mais volátil — é **10:00
local**, em plena manhã de dia útil no Japão.

> **Consequência de método, não de conveniência:** se um sensor ou filtro vier a usar hora,
> ele usa **hora de servidor (UTC)**. Hora local do operador não é propriedade do mercado e
> não pode entrar em `.mqh` nem em `research/`. Ela existe só nesta tabela.

## 4. O histórico — `data/raw/`

Ticks da **Dukascopy**, convertidos para Parquet particionado por mês. É o dado de
pesquisa; não é o dado do broker.

| Campo | Valor |
|---|---|
| Cobertura | 2022-08-01 → 2026-07-31 |
| Ticks | **240,344,662** |
| Dias com dado | 1,245 |
| Dias úteis | **1,041** |
| Formato | Parquet zstd, partição `year=/month=` |

### Integridade

Zero `ts` retrocedendo, zero `ask < bid`, zero preço ≤ 0, zero linha duplicada.

**Toda ausência tem causa de calendário; nenhuma sobrou sem explicação.** Os dias úteis
sem tick são as Sextas-feiras Santas; os dias anormalmente magros são os Natais e
Ano-Novos. A verificação de dia magro compara contra a mediana do **mesmo dia da semana** —
o domingo tem sessão parcial e roda uma ordem de grandeza abaixo de um pregão, então um
limiar único ou cega a verificação ou condena todo domingo.

### Amostra disponível para os gates

O Gate 2 exige N ≥ 250 dias de negociação **e** bloco out-of-sample nunca tocado.
Com 1,041 dias úteis o padrão do projeto — ~1.020 dias, 3 folds mais OOS com folga —
está satisfeito. Descontando os 12 feriados excluídos sobram ~1.029.

### Ritmo semanal medido

| Dia | Dias | Ticks (mediana) |
|---|---|---|
| Domingo | 204 | 6,847 |
| Segunda | 209 | 208,485 |
| Terça | 209 | 213,087 |
| Quarta | 209 | 219,334 |
| Quinta | 209 | 224,895 |
| Sexta | 205 | 220,309 |

Domingo abre 22:01 e é sessão parcial. Qualquer estatística por hora ou por dia precisa
tratá-lo à parte.

### O que NÃO transplanta da Dukascopy para o broker

| Elemento | Transplanta? |
|---|---|
| Caminho do preço | **Sim.** Ouro é ouro; os feeds diferem por centavos, não por trajetória |
| Spread | **Não.** Dukascopy é ECN bruto; a conta é Standard com markup. Descartado integralmente |
| Densidade de tick | Parcial — medir, não presumir |
| Execução (slippage, alargamento no disparo) | **Não, e não pode.** Só o Gate 4 mede |

Como o spread é a totalidade do custo nesta conta, usar o spread da Dukascopy produziria
backtest fantasioso. Não é refinamento — é a diferença entre um sistema lucrativo e um que
não existe.

### Dado do broker

| Fonte | Cobertura |
|---|---|
| Barras M1 | desde 2014-01-14, 3.265.408 barras |
| Tick real | janela móvel curta; coleta contínua iniciada em 2026-08-02 |

**A retenção curta do broker é de tick, não de barra.** Doze anos de M1 estão disponíveis,
o que abre uma janela de sobreposição muito maior que os quatro anos de tick para medir o
gap de fonte — ao custo de comparar em OHLC de minuto, o que mistura gap de fonte com gap
de resolução. São dois desenhos experimentais diferentes.

## 5. Custo — o que ele exige de edge

O spread é **pedágio fixo pago na entrada**, não sangria por tempo. E ele não apenas começa
o trade negativo: desloca **as duas barreiras na mesma direção**. Numa compra com alvo e
stop líquidos de tamanho `R` e spread `c`, o bid precisa subir `R+c` para o alvo, mas basta
cair `R−c` para o stop.

Sob caminho sem deriva:

```
P(ganhar)  = (R − c) / 2R
Esperança  = −c        exatamente, para QUALQUER alvo e stop
```

Alvo e stop não afetam a esperança. A única métrica operacional é o **acréscimo de acerto
direcional necessário**, `c/(2R)`. Com o piso de spread de $0,20/oz:

| Alvo/stop líquido | Acerto sem edge | Edge exigido |
|---|---|---|
| $0,30 | 16,7% | **+33 pp** |
| $0,50 | 30,0% | +20 pp |
| $1,00 | 40,0% | +10 pp |
| $3,00 | 46,7% | **+3,3 pp** |
| $5,00 | 48,0% | +2 pp |

**Armadilha da taxa de acerto.** Alvo +$0,30 com stop −$3,00 produz ~85% de trades
vencedores e esperança de −$0,20. Taxa alta de acerto não é edge — é a mesma matemática do
martingale por outra porta de entrada. Nenhum resultado neste projeto é avaliado por win
rate; apenas por esperança em R e t-stat sobre R agregado por dia.

**Alvos abaixo de ~$1,00 líquido exigem 10 pp ou mais de acerto direcional** e são hipótese
extraordinária, não ponto de partida.

> **O piso de $0,20 é premissa, não medição.** O spread real por hora e por faixa de
> volatilidade — média **e caudas** — depende de `data/broker/`, cuja coleta começou em
> 2026-08-02. Até haver amostra, toda conta de custo aqui usa o piso, que é o **melhor
> caso**. Spreads alargam exatamente quando o sinal dispara.

## 6. Volatilidade medida

σ é o **desvio-padrão da variação de preço em uma barra M1**, sobre o bid, com máscara de
sessão e feriados aplicados. É a definição que sustenta `R alcançável ≈ σ√T`; invertendo,
`T = (R/σ)²`.

### Qual unidade usar para calibrar

**Pontos-base do preço para σ; dólares para custo.** As duas grandezas têm naturezas
diferentes, e forçar uma unidade só é que seria o erro:

- **σ escala com o nível de preço.** Expressá-la em dólares é exatamente o defeito
  diagnosticado no `val` do Squeeze Momentum, e o contrato do sensor (`CLAUDE.md` §5.2) já
  exige saída adimensional. Calibrar contra bps é coerente com ele.
- **O spread não escala.** É pedágio fixo de $0,20/oz, não fração de nada. `c/(2R)` é
  genuinamente uma conta em dólares.

### σ por ano — as duas componentes separadas

| Ano | Preço mediano | σ (USD) | σ (bps) |
|---|---|---|---|
| 2022 | $1,737 | 0.433 | **2.49** |
| 2023 | $1,945 | 0.421 | **2.16** |
| 2024 | $2,379 | 0.583 | **2.45** |
| 2025 | $3,345 | 1.136 | **3.39** |
| 2026 | $4,601 | 2.595 | **5.64** |

Na janela o preço multiplicou por **2.65×**, σ em dólares por **5.99×** e
σ em bps por **2.26×**. Parte do salto em dólares é nível de preço e parte é
regime de volatilidade genuinamente maior. **As duas componentes existem** — nenhuma das
duas unidades é invariante, e é por isso que o gatilho de remedição da seção 7 é duplo.

### A forma do dia mudou

σ em USD por sessão, ano a ano:

| Ano | Asiático | Londres | Sobrep. LDN/NY | Nova York | Asiático ÷ Sobrep. |
|---|---|---|---|---|---|
| 2022 | 0.300 | 0.409 | 0.709 | 0.379 | **0.42** |
| 2023 | 0.295 | 0.360 | 0.681 | 0.376 | **0.43** |
| 2024 | 0.485 | 0.486 | 0.926 | 0.504 | **0.52** |
| 2025 | 1.067 | 1.028 | 1.498 | 1.018 | **0.71** |
| 2026 | 2.500 | 2.245 | 3.318 | 2.417 | **0.75** |

**A última coluna subiu de forma monótona, de 0.42 a 0.75, sem um único ano de
reversão: o perfil intradiário do ouro achatou.**

Isso desmente a ideia de que a sessão asiática é ~3× mais exigente em edge para o mesmo
tempo de exposição — essa afirmação exigiria razão ≈ 0,23. Ela já estava errada no início
da janela (0.42) e ficou pior.

Em 2026 a hora **1 UTC** — 09:00 em Pequim, abertura da Shanghai Gold Exchange — é a
segunda hora mais volátil do dia inteiro. O mesmo código sobre 2023 isolado devolve o
perfil clássico, com pico na sobreposição: **a mudança está no mercado, não na medição**.

> **Consequência para desenho de sensor:** filtrar sessão para “evitar a asiática” não tem
> mais base empírica. Se `REGIME` ou `COST` discriminarem horário, o critério precisa sair
> de medição corrente e ser remedido — este é um exemplo concreto de premissa que decaiu em
> quatro anos.

### σ por hora UTC — 2026

| Hora | Barras | σ (USD) | σ (bps) | σ robusta (USD) |
|---|---|---|---|---|
| 00 | 8,999 | 2.683 | 5.82 | 1.690 |
| 01 | 9,000 | 3.565 | 7.74 | 2.135 |
| 02 | 9,000 | 2.598 | 5.64 | 1.589 |
| 03 | 9,000 | 1.985 | 4.31 | 1.216 |
| 04 | 9,000 | 1.606 | 3.49 | 0.993 |
| 05 | 9,000 | 2.206 | 4.80 | 1.408 |
| 06 | 9,000 | 2.391 | 5.21 | 1.497 |
| 07 | 9,000 | 2.171 | 4.73 | 1.423 |
| 08 | 9,000 | 2.329 | 5.07 | 1.438 |
| 09 | 9,000 | 2.148 | 4.67 | 1.305 |
| 10 | 9,000 | 1.966 | 4.28 | 1.245 |
| 11 | 9,000 | 2.567 | 5.59 | 1.290 |
| 12 | 9,000 | 2.602 | 5.67 | 1.675 |
| 13 | 8,998 | 3.373 | 7.34 | 2.365 |
| 14 | 8,998 | 3.390 | 7.36 | 2.387 |
| 15 | 9,000 | 3.793 | 8.23 | 2.031 |
| 16 | 8,998 | 2.672 | 5.80 | 1.572 |
| 17 | 8,880 | 2.384 | 5.17 | 1.364 |
| 18 | 8,849 | 2.575 | 5.59 | 1.260 |
| 19 | 8,754 | 2.305 | 4.99 | 1.186 |
| 20 | 8,439 | 2.088 | 4.53 | 0.989 |
| 21 | 2,552 | 2.393 | 4.81 | 1.179 |
| 22 | 6,107 | 2.271 | 5.04 | 1.142 |
| 23 | 8,857 | 2.681 | 5.83 | 1.309 |

A hora ausente é a parada diária. **σ robusta** usa a mediana do desvio absoluto e ignora
as caudas; onde ela diverge muito da padrão, a diferença é spike. Para dimensionar stop a
cauda é o que mata; para descrever o minuto típico a robusta descreve melhor.

## 7. Calibração — o ponto de partida de um sensor

Valores de **2026**, a preço mediano de **$4,601/oz**. É desta tabela que
parte o desenho de qualquer sensor ou estratégia.

### Tempo para o preço percorrer R

`T = (R/σ)²`, sob passeio aleatório:

| Sessão | σ (USD) | σ (bps) | R=$1 (+10 pp) | R=$3 (+3,3 pp) | R=$5 (+2 pp) |
|---|---|---|---|---|---|
| Asiático | 2.500 | 5.43 | 0.2 min | 1.4 min | 4.0 min |
| Londres | 2.245 | 4.88 | 0.2 min | 1.8 min | 5.0 min |
| Sobreposição LDN/NY | 3.318 | 7.21 | 0.1 min | 0.8 min | 2.3 min |
| Nova York | 2.417 | 5.25 | 0.2 min | 1.5 min | 4.3 min |

Cruzando com a seção 5: **alvos de $3 a $5 líquidos exigem apenas 3,3 pp e 2 pp de acerto
direcional, e são alcançáveis em 1 a 5 minutos em qualquer sessão.** Isso é materialmente
mais favorável do que um alvo curto — que parece mais fácil e exige três a dez vezes mais
edge.

### Três ressalvas contra otimismo

1. **`σ√T` supõe passeio aleatório sem deriva nem reversão.** O M1 do ouro tem
   microestrutura; o alcance real em T minutos é menor.
2. **σ de fechamento a fechamento está inflada por bid-ask bounce**, que é ruído e não
   movimento aproveitável. Os tempos acima são o **melhor caso**, não a expectativa.
3. **O custo usa o piso de spread**, não a distribuição real. A cauda é o que importa, e ela
   ainda não foi medida.

Corrigir (1) e (2) exige `data/bars/`; corrigir (3) exige `data/broker/`. Ambos pendentes.

### Gatilho de remedição

Estes números **expiram**. Remedir quando qualquer um ocorrer:

- o ouro se afastar mais de **10%** de $4,601/oz
- passarem **3 meses** desde a geração deste documento

O primeiro gatilho existe porque σ em dólares escala com o nível de preço. O segundo existe
porque **σ em bps também mudou na janela** — o regime de volatilidade se move sozinho, e
nenhuma das duas unidades é invariante.

## 8. O que NÃO está medido

Esta seção existe porque ausência de linha não é o mesmo que "não precisou". Nada abaixo
deve ser preenchido com intuição: a §1 do `CLAUDE.md` trata isso como inventar resultado.

| Lacuna | Depende de | Consequência de ignorar |
|---|---|---|
| **Distribuição de spread do broker** por hora × faixa de volatilidade | `data/broker/` acumular amostra | Todo custo usa o piso; o backtest fica otimista exatamente nos momentos que decidem o resultado |
| **Slippage e alargamento no disparo** | Gate 4, forward em demo | Backtest não vê; a diferença é o gap de execução, e acima de 30% em R exige investigação |
| **Gap de fonte** Dukascopy × Exness | comparação nas duas fontes | Não se sabe quanto do resultado vem do feed |
| **Gap de resolução** tick × M1 OHLC | mesma comparação | Não se sabe se simular tick vale a pena |
| **Range efetivo em T minutos** | `data/bars/` | `σ√T` é o melhor caso e não a expectativa |
| **Densidade de tick por sessão** | auditoria adicional sobre `raw/` | Sensor que dependa de contagem de tick não tem baseline |
| **Abertura de domingo em hora de servidor** | extensão do `DataAudit` | A máscara aplica o deslize de DST a ela por inferência, não por medição |
| **Semântica de `confidence`** | decisão de projeto | O primeiro sensor a preencher o campo vira precedente por acidente |
| **Critério de escolha de T no Gate 1** | decisão de projeto | Varrer 1 a 30 barras e ficar com o melhor é teste múltiplo disfarçado |
| **Tese mecânica** | decisão de projeto | Sem ela a construção de sensores é busca cega, que é o que a correção para testes múltiplos existe para punir |

### Um candidato a tese que saiu de medição

O achatamento do perfil intradiário (seção 6) é candidato a hipótese mecânica, e tem a
vantagem de já vir com o número que o sustenta. Se a formação de preço do ouro migrou
parcialmente para o horário asiático — e a abertura da Shanghai Gold Exchange ser a segunda
hora mais volátil do dia é evidência disso — então houve deslocamento estrutural de
participantes, que é o tipo de coisa que gera desequilíbrio explorável.

**Isto é candidato, não tese.** Falta o mecanismo escrito e, sobretudo, a observação que o
falsificaria.

## 9. Como regenerar

**Não editar este arquivo à mão.** A narrativa está em `research/build_reference.py` e
`research/reference_parts.py`; as tabelas saem do dado.

```
# 1. no MT5: Navegador -> Scripts -> ARROW -> DataAudit
#    (spec do simbolo, sessoes, paradas diarias -> data/audit/)

# 2. conversao e validacao do historico
.venv\Scripts\python.exe research\build_raw.py --csv <arquivo> 
.venv\Scripts\python.exe research\build_raw.py --csv /dev/null --validate-only

# 3. volatilidade
.venv\Scripts\python.exe research\audit_sigma.py

# 4. veredicto de fuso e spec
.venv\Scripts\python.exe research\audit_broker.py

# 5. este documento
.venv\Scripts\python.exe research\build_reference.py
```

`write_raw` é append-only: **nunca** reprocessar um CSV já convertido sem `--validate-only`,
sob pena de duplicar `raw/`.

### Procedência

| Seção | Fonte |
|---|---|
| 1, 2 | `data/audit/symbol_spec.csv` |
| 3 — fuso | `data/audit/daily_breaks.csv` |
| 3 — sessões | `data/audit/sessions.csv` |
| 3 — feriados | `research/lib/market_calendar.py` (regra) |
| 4 | `reports/*-ticks-por-dia.csv`, `reports/*-validacao.md` |
| 6, 7 | `reports/sigma-*.csv` |

