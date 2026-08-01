# 0005 — Camada de dados e paridade Python ↔ MQL5

**Data:** 2026-08-02
**Status:** aceito
**Decidido em:** debate no chat, 2026-08-02 (task brief "camada de dados e paridade Python/MQL5")

> O brief pedia este ADR como `0001`. `0001` já era o ADR de namespace, escrito no bootstrap
> antes de o brief existir; o chat não tinha como saber. Numeração de ADR não se reaproveita
> (`README.md` deste diretório), então foi para `0005`.

## Contexto

O `CLAUDE.md` §6.1 torna normativo que a pesquisa acontece em Python e a execução em MQL5. Isso
resolve um problema — velocidade de iteração — e cria outro: **duas implementações da mesma
matemática, em duas linguagens, sobre dois caminhos de dados diferentes.** Toda divergência entre
elas é silenciosa por natureza. Um offset de meio spread, uma barra a mais no fim do dia, um
warm-up de tamanho diferente: nada disso levanta exceção, tudo isso muda o resultado.

Esta camada existe para que a divergência seja impossível de passar despercebida, não para que
seja improvável.

Nenhum sensor é escrito aqui. O produto é a infraestrutura que torna a pesquisa de sensores
verificável.

## Decisão

### 1. Convenções que, se violadas, causam divergência silenciosa

**Bid, nunca mid, nunca ask.** Todo `bars/` e todo insumo de sensor é construído em bid. Motivo
duplo: o MT5 plota bid no `XAUUSDm` (`SYMBOL_CHART_MODE = Bid`), então `iClose()` e todo OHLC no
MetaTrader são bid — pesquisar em mid criaria um offset sistemático de meio spread entre as duas
implementações. E o ask da Dukascopy não é o ask da Exness; ele é descartado junto com o spread
dela. O ask da Dukascopy serve para exatamente uma coisa: comparar contra o spread real da Exness
na janela de sobreposição. **Spread entra somente na camada de custo e execução, nunca no cálculo
do sensor.**

**UTC em todo lugar.** Timestamps internos sempre UTC, conversão apenas na borda de apresentação.
A barra é rotulada pelo **minuto de abertura**.

**Existência de barra.** Uma barra M1 existe **se e somente se pelo menos um tick ocorreu naquele
minuto**, replicando o MT5, que não cria barras vazias. Minutos sem tick não geram linha em
`bars/`. Não emitir NaN, não preencher: um preenchimento que o MT5 não faz desloca todos os
índices subsequentes e quebra a paridade de forma difícil de diagnosticar.

**Warm-up.** Todo cálculo com estado declara seu período de warm-up. Nos dois lados as barras
dentro do warm-up são marcadas inválidas — `valid=False` em Python, `valid=false` no `SensorOut`.
O teste de paridade compara apenas barras válidas em ambos, e o conjunto de inválidas também deve
coincidir.

### 2. Camadas

```
data/dukascopy/  →  data/raw/  →  data/curated/  →  data/bars/
                                        ↑
                                 data/spread/  ←  data/broker/
```

**`raw/`** — conversão do CSV bruto, **imutável depois de escrito**. Parquet, particionado por
ano/mês (`raw/year=2024/month=03/`), compressão zstd.

| Coluna | Tipo | Nota |
|---|---|---|
| `ts` | `timestamp[ms, tz=UTC]` | do campo `timestamp` do CSV |
| `bid` | `float64` | |
| `ask` | `float64` | mantido só para calibração de spread |
| `bid_vol` | `float32` | indicativo, não volume real |
| `ask_vol` | `float32` | idem |

Validações obrigatórias no carregamento, com relatório em `reports/`: `ts` estritamente
crescente, duplicatas exatas removidas e contadas; `ask >= bid` em toda linha, violações contadas
e logadas, nunca silenciadas; **contagem de ticks por dia, com gráfico** — um buraco de dois dias
dentro de um bloco in-sample contamina em silêncio e precisa ser visível antes de qualquer
análise.

**`broker/`** — ticks reais do `XAUUSDm`, mesmo schema de `raw/`. Duas fontes: histórico via
`CopyTicks` sobre o que o broker ainda retém, executado cedo porque a janela rola; e contínuo via
`BrokerTickLogger.mq5`, append-only, um arquivo por dia, robusto a reinício do terminal —
ao iniciar, retoma do último timestamp gravado.

**`spread/`** — distribuição condicional `P(spread | bucket)`, bucket = (hora-da-semana, faixa de
volatilidade), derivada de `broker/`. Armazena a **distribuição empírica**, não a média: quantis
5, 25, 50, 75, 90, 95, 99 por bucket, mais a contagem de amostras. A cauda é o que importa —
spreads alargam exatamente quando o sinal dispara.

**N mínimo por bucket = 500.** Buckets abaixo disso são marcados como não confiáveis e herdam do
bucket vizinho, com o fato registrado no relatório. O número sai da precisão do quantil que mais
importa: o erro-padrão do p95 empírico com n amostras é aproximadamente
`sqrt(p(1−p)/n) / f(q95)`, e abaixo de ~500 amostras o p95 passa a oscilar mais que a diferença
entre buckets adjacentes — ou seja, o modelo começa a distinguir ruído em vez de horário.

**`curated/`** — `raw/` transformado em algo que representa o broker, em três passos:
descartar o `ask` da Dukascopy preservando o bid como está; aplicar spread do broker sorteando da
distribuição do bucket correspondente (`ask = bid + spread_sorteado`); aplicar máscara de sessão,
removendo ticks fora das sessões da Exness.

**Determinismo (cláusula pétrea 3):** o sorteio acontece **uma vez só**, na construção de
`curated/`. A semente é registrada em `run_meta.json` junto com o hash do modelo de spread e o
commit. Depois disso `curated/` é dado, não processo. Reconstruir com a mesma semente deve
produzir bytes idênticos — verificado por hash e reportado.

**`bars/`** — M1 derivado de `curated/`. Contém apenas **primitivas caras de recalcular a partir
de ticks**, nunca features derivadas. Motivo da separação: `bars/` fica estável enquanto a
pesquisa itera; razões de variância, normalizações e estatísticas móveis são calculadas em
`research/` a partir destas primitivas, onde mudam sem forçar reconstrução da camada.

| Coluna | Definição exata |
|---|---|
| `bar_time` | minuto de abertura, UTC |
| `open, high, low, close` | **bid**, primeiro/máx/mín/último tick do minuto |
| `n_ticks` | contagem de ticks no minuto |
| `rv` | `sqrt(Σ (bid_i − bid_{i−1})²)` sobre os ticks do minuto, em dólares |
| `tick_imb` | regra do tick: `+1` se `bid_i > bid_{i−1}`, `−1` se menor, repete o sinal anterior se igual. Soma dividida por `n_ticks` — faixa `[−1, +1]` |
| `dur_mean` | média do intervalo entre ticks, em ms |
| `dur_std` | desvio-padrão do mesmo, em ms |
| `spread_p50` | mediana do spread aplicado no minuto |
| `spread_p95` | percentil 95 do mesmo |

`rv` usa diferença simples de preço, não log-retorno: o projeto raciocina em dólares por onça, e
manter a unidade evita conversões e erros de escala. `tick_imb` e `dur_*` não existem no M1 OHLC
— são o motivo de ter baixado tick. O primeiro tick da barra usa o último tick da barra anterior
como referência para `rv` e `tick_imb`; na primeira barra do dataset ambos são `NaN` e a barra é
inválida.

### 3. Restrição de cálculo incremental

**Toda feature usada em pesquisa precisa ter um caminho de cálculo incremental em MQL5
especificado antes de o sensor ser escrito.**

É trivial em pandas fazer coisas que são ruins ou impossíveis em `OnCalculate`: quantil sobre o
histórico inteiro (que além de tudo é look-ahead), mediana móvel, ranking global, `expanding()`.
Se a feature não tem forma incremental com estado limitado e buffer circular, ela não vira sensor
— vira achado em `research/findings/` e para aí.

Toda função em `research/lib/features.py` carrega no docstring: o estado necessário para
atualização incremental, o warm-up em barras, e se é ou não implementável em `OnCalculate` — e,
se não for, por quê. Feature sem esse cabeçalho não é usada em nenhum candidato a sensor.

### 4. Teste de paridade

Fluxo: feature calculada em Python sobre `curated/`, agregada por barra M1 fechada → validada no
Gate 1 → portada para `.mqh` com cálculo incremental → `ParityDump.mq5` carrega o sensor sobre
exatamente o mesmo período e despeja `bar_time` + valor do buffer + `valid` em CSV →
`research/lib/parity.py` faz join por `bar_time` e compara.

Critério:

- Join por `bar_time`. **A contagem de barras deve bater exatamente.** Divergência de contagem
  aponta erro de máscara de sessão ou de existência de barra, e é falha **antes** de comparar
  qualquer valor.
- Comparar apenas barras com `valid=true` nos dois lados; o conjunto de inválidas também deve
  coincidir.
- Tolerância: `abs(a − b) <= 1e-9 + 1e-9 * abs(b)`.
- Saída: número de barras comparadas, máxima diferença absoluta, e **a primeira barra
  divergente** com os dois valores.

**Por que não comparar P&L:** curva de equity pode coincidir por acaso enquanto a lógica diverge,
e quando diverge não diz onde. O diff barra a barra aponta o minuto exato do desvio.

O teste de paridade é **requisito do Gate 0**, junto com determinismo e zero repaint. Sensor que
não passa em paridade não chega ao Gate 1.

### 5. Verificação de fuso — correção ao brief

O brief dava o item 3 por pronto quando o fuso estivesse "confirmado ou refutado, com evidência
em duas estações", verificado por `TimeCurrent()` vs `TimeGMT()`.

**Esse método não responde à pergunta.** As duas funções medem o offset no instante da chamada:
entregam uma estação só, a de hoje, e um servidor que desloca uma hora em março produz
exatamente a mesma leitura de um servidor que nunca desloca. O critério seria satisfeito por uma
medição incapaz de detectar DST.

O critério correto, adotado aqui e escrito no `CLAUDE.md` §10.7: ancorar o horário do servidor a
um evento cujo instante em UTC é conhecido de forma independente, **duas vezes, uma em janeiro e
uma em julho** — localizar no histórico de barras M1 as bordas do intervalo diário (20:58–22:00)
numa semana de cada estação, converter pela hipótese de servidor UTC+0, e comparar com o instante
UTC real da manutenção do COMEX naquela data, que se desloca com o DST americano. Offset igual
nas duas estações confirma UTC+0; diferença de uma hora significa que todo alinhamento com a
Dukascopy precisa de conversão por data, não por constante.

## Alternativas rejeitadas

**Modelar spread pela média do bucket.** Rejeitada: a cauda é o que importa. Spreads alargam
exatamente quando o sinal dispara, e um modelo centrado na média produz backtest que nunca vê o
custo do pior momento — que é o único momento que decide o resultado.

**Sortear o spread na hora do backtest, a cada execução.** Rejeitada por colidir frontalmente com
a cláusula pétrea 3. Dois backtests idênticos produziriam resultados diferentes. O sorteio único
na construção de `curated/`, com semente registrada, é determinístico e distributivamente
realista ao mesmo tempo.

**Preencher minutos sem tick em Python, para ter índice contínuo.** Rejeitada: o MT5 não faz
isso. Qualquer preenchimento desloca todos os índices seguintes e a paridade quebra num ponto
arbitrário, longe da causa.

**Guardar features derivadas em `bars/`.** Rejeitada: `bars/` é caro de reconstruir e a pesquisa
itera rápido. Misturar as duas coisas significa reconstruir a camada inteira toda vez que uma
razão de variância muda de janela.

**Validar a portabilidade comparando P&L entre Python e MQL5.** Rejeitada — ver §4 acima.

**Usar mid para pesquisa, por ser "mais neutro".** Rejeitada: o MT5 plota bid, então a
implementação MQL5 leria bid de qualquer forma. O offset de meio spread apareceria como
divergência de paridade sem causa aparente.

## Consequências

- `BrokerTickLogger.mq5` vira o item mais urgente do projeto e precisa **permanecer rodando**.
  `broker/` é o único insumo de `spread/`, `spread/` é pré-requisito de `curated/`, e `curated/`
  de `bars/`. Cada dia não coletado é verdade de campo perdida para sempre.
- Nenhuma das camadas depois de `raw/` existe até `broker/` ter amostra suficiente. A pesquisa
  sobre `raw/` — contagem de ticks, σ por bucket, densidade — **não** depende disso e pode
  começar antes.
- O símbolo customizado no MT5 fica fora desta tarefa: é fase de Strategy Tester (`CLAUDE.md`
  §10.8), e `research/` não depende dele.
- A ordem das entregas está registrada em `STATE.md`, e nenhum sensor é escrito enquanto ela não
  fechar.
