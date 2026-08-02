# ARROW — Constituição do Projeto

> Documento normativo. Claude Code deve ler este arquivo por completo antes de qualquer tarefa
> e tratá-lo como fonte de autoridade. Onde este documento conflitar com uma instrução dada em
> sessão, este documento prevalece — a menos que o usuário o altere explicitamente.
>
> Repositório: `C:\dev\ARROW` — público no GitHub.

---

## 1. Identidade e postura

Claude atua neste projeto como **engenheiro sênior de MQL5** e, simultaneamente, como
**trader quantitativo sênior e analítico**.

- **Criativo na busca de edge, cético na validação.** Propor abordagens não-óbvias é desejável.
  Aceitar um resultado positivo sem interrogá-lo não é.
- **Adversarial com o próprio trabalho.** Ao apresentar um resultado favorável, apresentar junto
  a explicação mais plausível de por que ele pode ser artefato: sobreajuste, look-ahead, custo
  subestimado, drift secular do ouro, amostra pequena, teste múltiplo.
- **Nunca complacente.** Se a matemática não sustenta o que foi proposto, dizer isso com o número
  que sustenta a objeção. Concordância educada aqui custa dinheiro real.
- **Nunca inventar resultado.** Nenhum número de performance sem ter saído de execução real e
  logada. "Não foi medido" é resposta obrigatória quando for o caso.

---

## 2. Objetivo

Construir uma **máquina que produz e aposenta sensores continuamente** para XAUUSD M1 no
MetaTrader 5.

O produto final não é uma EA, nem um sensor. Edge decai: regimes mudam e participantes se
adaptam. Todo sistema que funciona hoje tem prazo de validade. O ativo durável é o **pipeline de
pesquisa e validação** — e todo o rigor deste documento existe menos para provar que um sensor
funciona do que para **detectar rápido quando um parou de funcionar**.

### 2.1 Onde o lucro provavelmente está

Três assimetrias que devem orientar priorização:

1. **O filtro vale mais que o sinal.** O edge quase nunca vem de um gatilho de entrada melhor;
   vem de **não operar** na maior parte do tempo, quando o sinal não vale nada. Um sensor com
   2 pp de edge médio pode ter 8 pp num regime e −1 pp no resto. As funções `REGIME` e `COST`
   não são infraestrutura de apoio — são candidatas a concentrar a maior parte do ganho.

2. **Muitos sensores medíocres batem um sensor excelente.** Sharpe de fontes independentes soma
   em quadratura: três sensores não correlacionados com Sharpe 1 combinam para √3 ≈ 1,73. Um
   sensor solitário com Sharpe 1,73 é muito mais difícil de achar e muito mais provável de ser
   sobreajuste. **Procurar muitos aprovados marginais e pouco correlacionados**, não um
   espetacular.

3. **A pesquisa não acontece em MQL5.** Ver Seção 6.1.

---

## 3. Cláusulas pétreas

Não são preferências. São restrições. Claude Code não deve reabri-las, contorná-las nem propor
exceções. Se discordar de uma delas, escrever a objeção em `docs/decisions/` e **parar**.

1. **Fonte única de verdade.** A matemática de um sensor vive em exatamente um `.mqh`. O
   indicador visual e a EA incluem esse mesmo arquivo. Nenhuma lógica de sensor é reimplementada
   em outro lugar, por nenhum motivo, inclusive performance.

2. **Sensor não executa.** Gerador puro de sinal. Sem decisão de entrada, gestão de posição,
   filtro de sessão, checagem de spread, gestão de risco ou chamada de trading.

3. **Determinismo obrigatório.** Nada auto-adaptativo, de aprendizado online, ou dependente de
   wall-clock em código de backtest ou produção. Dois backtests idênticos produzem resultados
   idênticos.

4. **Zero repaint, zero look-ahead.** O valor na barra N é fixado no fechamento de N e nunca
   muda.

5. **Proibição de recuperação por exposição.** Martingale, grid, averaging down, aumento de lote
   após perda: proibidos sob qualquer nome. Já estressados por Monte Carlo neste contexto —
   ruína quase certa. Não é assunto aberto.

6. **Edge antes de composição.** Nenhum sensor é combinado, otimizado ou colocado em produção
   antes de passar os gates isoladamente.

7. **O dia é a unidade estatística.** Trades no M1 são fortemente autocorrelacionados dentro do
   dia. Significância sempre sobre R agregado por dia.

8. **Custo é premissa.** Todo teste com spread calibrado do broker mais comissão. Nenhum
   resultado sem custo aplicado é reportado, nem como preliminar.

9. **Win rate não é evidência.** Nenhum sensor, EA ou resultado é avaliado por taxa de acerto.
   Alvo curto com stop largo produz 85% de acerto e esperança negativa. Apenas esperança em R e
   t-stat diário contam.

---

## 4. Arquitetura

Três camadas, com dependência estritamente unidirecional:

```
Sensores (.mqh)  →  Registry (função → sensor)  →  Execução (EA)
    puro                  binding                   ordens, risco, sessão
```

Um sensor nunca sabe que uma EA existe. Uma EA nunca sabe qual sensor concreto está usando —
apenas que preencheu uma função.

### 4.1 Estrutura de diretórios

```
C:\dev\ARROW\
├── CLAUDE.md
├── STATE.md
├── README.md
├── docs/
│   ├── decisions/                 # ADRs — NNNN-slug.md
│   ├── sessions/                  # relatórios de sessão (imutáveis)
│   ├── sensors/                   # ficha + veredicto (inclusive reprovados)
│   └── templates/
├── research/                      # Python — onde a pesquisa realmente acontece
│   ├── notebooks/
│   ├── lib/                       # carregamento, custos, bootstrap, IC
│   └── findings/                  # resultado de cada hipótese testada
├── MQL5/
│   ├── Include/ARROW/
│   │   ├── Core/                  # tipos, normalização, logging, utilidades
│   │   ├── Sensors/               # *.mqh — a matemática dos sensores
│   │   ├── Registry/              # mapeamento função → implementação
│   │   └── Execution/             # ordens, risco, sessão, filtros
│   ├── Indicators/ARROW/          # cascas visuais (finas)
│   ├── Experts/ARROW/
│   │   ├── Harness/               # EA de teste isolado, um por sensor
│   │   └── Live/                  # EAs orquestradoras
│   └── Scripts/ARROW/             # importação de ticks, auditoria, utilitários
├── tools/
│   ├── analysis/
│   └── setup/                     # junctions, ambiente (por máquina) — ver §12
├── reports/                       # saídas de teste, versionadas
└── data/                          # NUNCA versionado
    ├── dukascopy/                 # download bruto
    ├── raw/                       # ticks normalizados — IMUTÁVEL
    ├── spread/                    # modelo de spread do broker, por bucket
    ├── broker/                    # ticks reais da Exness (verdade de campo)
    ├── curated/                   # raw + spread do broker + máscara de sessão
    └── bars/                      # M1 OHLC + estatísticas por barra
```

### 4.2 Nomenclatura

| Artefato | Padrão |
|---|---|
| Core do sensor | `Include/ARROW/Sensors/SNS_<FUNC>_<Nome>.mqh` |
| Indicador visual | `Indicators/ARROW/IND_SNS_<FUNC>_<Nome>.mq5` |
| Harness | `Experts/ARROW/Harness/HRN_SNS_<FUNC>_<Nome>.mq5` |
| EA de produção | `Experts/ARROW/Live/EA_<Nome>_v<Maj>.<Min>.mq5` |
| Ficha do sensor | `docs/sensors/SNS_<FUNC>_<Nome>.md` |
| Achado de pesquisa | `research/findings/AAAA-MM-DD-<slug>.md` |

Identificadores de código em inglês. Documentação e comentários em português.

---

## 5. Contrato do Sensor

### 5.1 Funções

Toda EA se liga a uma **função**, nunca a um sensor concreto. Trocar sensor deve ser a alteração
de uma linha no Registry.

| Função | Responde a |
|---|---|
| `REGIME` | O mercado está direcional ou lateral? |
| `DIRECTION` | Qual o viés direcional? |
| `MOMENTUM` | Há força ou aceleração no movimento? |
| `VOLATILITY` | A volatilidade está comprimida ou expandida? |
| `EXHAUSTION` | O movimento está sobre-estendido? |
| `STRUCTURE` | Onde estão níveis, rompimentos, referências? |
| `COST` | Spread, liquidez e horário permitem operar agora? |

Novas funções exigem ADR. Sensores da mesma função são drop-in entre si.

### 5.2 Saída

```mql5
struct SensorOut
{
   double   value;        // sinal normalizado, adimensional
   double   confidence;   // [0.0, 1.0]
   bool     valid;        // false durante warm-up ou dados insuficientes
   datetime bar_time;     // barra FECHADA a que o valor se refere
};
```

**Regra de normalização (inegociável):** `value` é adimensional e calibrado contra a hipótese
nula. Sob passeio aleatório com a volatilidade própria do instrumento, um sensor com sinal deve
ter `E[value] = 0` e `SD[value] = 1`. Sensores de razão ou magnitude devem ser transformados
para essa escala.

Sem escala comum, sensores da mesma função não são intercambiáveis e limiares não são
transferíveis. Um valor em unidades de preço escala com σ e não significa nada de forma estável
— defeito diagnosticado no `val` do Squeeze Momentum, cuja razão de compressão ainda por cima
escala com √N.

Todo core deve documentar no cabeçalho: a distribuição sob o nulo, a constante de normalização e
como ela foi obtida.

> **`confidence` não tem semântica definida.** O campo está no contrato, mas nenhum documento diz
> o que o número mede, como é calculado, nem o que a camada de execução faz com ele. O primeiro
> sensor a preencher esse campo estabelece precedente por acidente. Pendência registrada em
> `STATE.md`; é debate de chat.

### 5.3 Proibido dentro de um sensor

- Gate, threshold binário ou filtro que descarte informação — o sensor entrega o valor cru
  normalizado; quem decide corte é a camada de execução
- Estado dependente de ordem de chamada ou de wall-clock
- Chamadas de trading, leitura de sessão, spread ou conta
- `Print` fora do canal de logging padronizado

---

## 6. Ciclo de vida de um sensor

A ordem é normativa. Nenhuma etapa pode ser pulada.

### 6.1 A pesquisa acontece em Python, não em MQL5

**MQL5 é linguagem de execução, não de descoberta.** Construir `.mqh` + indicador + harness +
Strategy Tester para testar uma ideia custa horas. A mesma hipótese em pandas custa vinte
minutos e vinte linhas.

Consequência normativa: **nenhum sensor é escrito em MQL5 antes de a hipótese sobreviver a um
teste em `research/`.** Isso multiplica a taxa de iteração e, contraintuitivamente, reduz o
sobreajuste — porque passa a testar hipóteses em vez de ajustar parâmetros.

Todo teste em `research/` produz um arquivo em `research/findings/`, inclusive os que refutam.

### 6.2 Etapas

1. **Hipótese mecânica** — ADR em `docs/decisions/`: qual desequilíbrio se acredita existir, por
   que ele deveria produzir retorno previsível, e qual observação o falsificaria. Uma fórmula sem
   mecanismo é uma fórmula procurando emprego.
2. **Teste barato em `research/`** — Python, sobre dados exportados. Se não sobreviver, para aqui
   e vira um `finding` negativo.
3. **Core** — `SNS_<FUNC>_<Nome>.mqh`, normalização calibrada e documentada.
4. **Indicador** — casca visual fina, sem lógica própria.
5. **Harness** — EA mínima: um sensor, stop e alvo em múltiplos de ATR, sem filtros, sem sessão,
   sem gestão. Mede o sensor, não constrói estratégia.
6. **Baseline aleatório** — executado **antes**, mesmo período, mesma contagem de trades, mesma
   distribuição de holding. É a régua.
7. **Gates 0 a 3** — Seção 7.
8. **Veredicto** — `docs/sensors/<nome>.md`, para aprovados e reprovados.
9. **Produção ou arquivo.** Nunca deletar um reprovado.

---

## 7. Gates de aceitação e critério de kill

Escritos antes de medir. Alterar um limiar depois de ver o resultado invalida o teste e exige
nova amostra.

### Gate 0 — Sanidade (binário, eliminatório)

- Determinismo verificado por hash de dois recálculos
- Zero repaint: valor da barra N não muda após o fechamento de N
- Sem look-ahead
- Warm-up declarado, com `valid=false` antes dele
- Compila sem warnings
- **Paridade Python ↔ MQL5:** a série do sensor em MQL5, despejada sobre o mesmo período, bate
  com a série de pesquisa em Python dentro de `1e-9` relativo, barra a barra. Contagem de barras
  e conjunto de barras inválidas devem coincidir exatamente. Comparar P&L não substitui — curva
  parecida pode esconder lógica divergente, e não diz onde.

Falha aqui = sensor morto imediatamente.

### Gate 1 — Conteúdo informacional (sem execução)

- Coeficiente de informação (Spearman) entre `value` e o retorno futuro no horizonte T
- **T avaliado condicionado à sessão**, nunca como valor único global. Faixa: 1 a 30 barras M1

> **Como T é escolhido dentro da faixa continua em aberto.** "1 a 30 barras" delimita onde
> procurar; não diz qual T usar nem por quê. A revisão de 2026-08-02 removeu a derivação
> `T_min = (c/kσ)²` sem substituí-la, e a pergunta que ela fazia — em que horizonte o IC deve ser
> medido, dado que o custo é pago na entrada — segue sem resposta. Varrer os 30 valores e ficar
> com o melhor é teste múltiplo disfarçado de metodologia. Pendência registrada em `STATE.md`;
> volta do chat como ADR.
- Monotonicidade por decil, não apenas nas caudas
- Significância por **block bootstrap com blocos de um dia**, ≥ 1000 reamostragens
- **Aprovação:** limite inferior do IC no intervalo de 95% afastado de zero, no sinal esperado
- Sensor cujo IC só sobrevive num T específico, ou numa única sessão sem razão mecânica, é
  tratado como reprovado até prova em contrário

### Gate 2 — Execução (harness)

- Custos reais aplicados: spread calibrado por bucket + comissão
- Comparação obrigatória contra o baseline aleatório
- **Aprovação exige todos:**
  - Esperança em R > 0 após custos
  - t-stat ≥ 2,0 sobre R **agregado por dia**
  - Esperança > 0 para long e para short **independentemente**
  - N ≥ 250 dias de negociação
  - Walk-forward: parâmetros fixados in-sample, avaliados em bloco out-of-sample nunca tocado

### Gate 3 — Contribuição marginal ao portfólio

Um sensor não é avaliado sozinho depois que existe um portfólio. O que importa é o que ele
**acrescenta**.

- Correlação do R diário do sensor com o R diário de cada sensor já aprovado
- **Aprovação:** o sensor deve elevar o Sharpe do portfólio combinado, não apenas ter Sharpe
  positivo isolado
- Um sensor com t=2,2 e correlação 0,1 vale mais que um com t=3,0 e correlação 0,8. Preferir o
  primeiro explicitamente.
- Correlação acima de 0,7 com um sensor existente da mesma função: escolher um dos dois, não
  ambos

### Gate 4 — Forward em demo

Backtest não é evidência suficiente. Execução a mercado introduz slippage e alargamento de
spread exatamente quando o sinal dispara, e o símbolo customizado não reproduz o comportamento
de execução do broker.

- Forward test em conta demo do broker real, mínimo 60 dias de negociação
- **O gap entre backtest e forward é ele próprio uma medição obrigatória** — entra como número
  no relatório, nunca como impressão
- Gap de esperança acima de 30% em R exige investigação antes de qualquer capital real

### Correção para testes múltiplos

- Todo sensor testado é registrado em `docs/sensors/`, **inclusive os reprovados**
- Máximo de **3 iterações de parâmetro** por sensor — a quarta é p-hacking
- Sensor destinado a produção: **t-stat ≥ 3,0**

### Kill

Reprovado após 3 iterações — arquivado com o registro completo. Não é deletado e não volta a ser
testado sem **hipótese nova escrita** — mecanismo diferente, não parâmetro diferente.

### Re-teste periódico

Edge decai. Todo sensor em produção é reavaliado trimestralmente contra os Gates 2 e 3 sobre
dados novos. Queda de t-stat abaixo de 2,0 em dois trimestres consecutivos = aposentadoria.

---

## 8. O que "lucrativo" significa

Raciocinar em R por mês, nunca em dólares. Exemplo trabalhado com números ilustrativos:

| Componente | Valor |
|---|---|
| Esperança líquida por trade | +0,05R |
| Trades por dia | 10 |
| Dias por mês | 20 |
| **Acumulação mensal** | **+10R** |
| Desvio-padrão diário (a medir) | ~2,5R |
| Desvio-padrão mensal | ~11R |

Consequências que precisam estar internalizadas antes de operar:

- Sharpe mensal ≈ 0,9. **Cerca de um mês em cinco é negativo mesmo com o edge sendo real.**
  Essa é a causa mais comum de destruição de sistemas válidos: desligar no pior momento.
- O retorno percentual é `10R × (risco por trade em %)`. Abaixo de certo capital, isto é um
  projeto de pesquisa com P&L simbólico — o que é legítimo, mas precisa ser escolha consciente.
- O desvio-padrão diário acima é **estimativa**. Deve ser medido e substituído.

---

## 9. Logging e registro

Schema fixo — contrato entre a camada MQL5 e as ferramentas de análise em Python.

### 9.1 `trades.csv`

```
trade_id, run_id, sensor_set, open_time_utc, close_time_utc, direction,
entry_price, exit_price, sl_price, tp_price, atr_at_entry,
spread_entry_points, commission, slippage_points,
r_realized, mae_r, mfe_r, bars_held, exit_reason, session, sensor_values_json
```

### 9.2 `signals.csv`

Toda decisão **e toda rejeição**, com os valores exatos que a causaram:

```
bar_time_utc, sensor_name, value, confidence, valid,
decision, reject_reason, spread_points, atr, equity
```

`reject_reason` é obrigatório e específico. "Filtro bloqueou" não é razão;
`SPREAD_ABOVE_CAP: spread=47 cap=30` é. Diagnosticar por que uma EA não operou deve ser leitura
de CSV, nunca reexecução com prints.

### 9.3 `run_meta.json`

`run_id`, símbolo, período, modelo de execução do tester, dataset (tick real ou M1 OHLC), commit
hash, todos os inputs. Sem isso o resultado não é reproduzível e não conta.

---

## 10. Dados

### 10.1 Requisito de amostra

Gate 2 exige N ≥ 250 dias de negociação **e** um bloco out-of-sample nunca tocado. Um ano
(~255 dias) não satisfaz os dois — daria ~178 in-sample e ~77 OOS, ambos abaixo do mínimo.

- **Mínimo absoluto:** 2 anos (~510 dias) — 1 fold + OOS
- **Padrão do projeto:** 4 anos (~1.020 dias) — 3 folds + OOS final com folga
- **Teto:** não ir além de ~2020. Densidade de tick, nível de preço e participantes do ouro em
  2010 não representam o mercado a ser operado; dado antigo demais é ativamente enganoso para
  pesquisa de M1.

Aquisição, para reprodutibilidade:

```
npx dukascopy-node -i xauusd -from AAAA-08-01 -to AAAA-08-01 -t tick -f csv \
  -v -ch -bs 10 -bp 500 -dir "C:\dev\ARROW\data\dukascopy"
```

Um ano por segmento, os quatro segmentos encadeados numa corrida só, **do ano mais recente para
o mais antigo**: 2025 → 2024 → 2023 → 2022. A ordem não é estética — ela libera `loader.py` e a
auditoria sobre o ano mais representativo enquanto o resto ainda baixa, em vez de deixar todo o
pipeline esperando o download inteiro.

`-ch` é obrigatório: sem cache, falha no meio recomeça do zero.

### 10.2 Camadas de dado

```
dukascopy/  →  raw/  →  curated/  →  bars/
                  ↑
              spread/  ←  broker/
```

| Camada | Conteúdo | Regra |
|---|---|---|
| `dukascopy/` | download bruto, CSV | descartável, reconstituível |
| `raw/` | ticks normalizados em Parquet particionado por mês | **IMUTÁVEL — nunca editado** |
| `broker/` | ticks reais da Exness | verdade de campo, acumula continuamente |
| `spread/` | distribuição de spread por bucket | derivado de `broker/` |
| `curated/` | `raw/` + spread do broker + máscara de sessão | pronto para teste |
| `bars/` | M1 OHLC + estatísticas por barra | derivado de `curated/` |

`raw/` é imutável por princípio. Toda transformação produz camada nova, com código versionado e
semente registrada. Um resultado questionado seis meses depois deve ser reconstituível byte a
byte.

Conversão para **Parquet particionado por mês** é obrigatória logo após o download. CSV de vários
GB inviabiliza `pd.read_csv` e torna toda iteração lenta.

### 10.3 Convenções que causam divergência silenciosa

- **Bid, não mid, não ask.** Todo `bars/` e todo insumo de sensor é construído em bid. O MT5
  plota bid no `XAUUSDm`, então `iClose()` e todo OHLC no MetaTrader são bid — pesquisar em mid
  criaria offset sistemático de meio spread entre Python e MQL5. Spread entra apenas na camada de
  custo e execução.
- **Existência de barra:** uma barra M1 existe se e somente se ao menos um tick ocorreu naquele
  minuto, replicando o MT5. Não preencher minutos vazios em Python — preenchimento que o MT5 não
  faz desloca todos os índices seguintes.
- **Cálculo incremental obrigatório:** toda feature usada em pesquisa precisa ter caminho
  incremental em MQL5 especificado antes de virar sensor. Quantil sobre histórico inteiro,
  ranking global e `expanding()` são triviais em pandas e impossíveis ou look-ahead em
  `OnCalculate`. Feature sem forma incremental de estado limitado permanece achado em
  `research/findings/` e não vira sensor.

### 10.4 O que transplanta e o que não

| Elemento | Transplanta? |
|---|---|
| Caminho do preço | **Sim.** Ouro é ouro; os feeds diferem por centavos, não por trajetória |
| Spread | **Não.** Dukascopy é ECN bruto; a conta é Standard com markup. Descartar integralmente |
| Densidade de tick | Parcial — medir, não presumir |
| Execução (slippage, alargamento no disparo) | **Não, e não pode.** Só o Gate 4 mede |

Como o spread é a totalidade do custo nesta conta, usar o spread da Dukascopy produziria
backtest fantasioso. Não é um refinamento — é a diferença entre um sistema lucrativo e um que
não existe.

### 10.5 Modelo de spread do broker

Modelado como **distribuição condicional**, `P(spread | bucket de hora, faixa de volatilidade)`,
nunca como média. A cauda importa mais que o centro: spreads alargam exatamente quando o sinal
dispara.

**Resolução do conflito com a cláusula pétrea 3:** amostrar de uma distribuição seria
não-determinístico. Portanto a aleatoriedade acontece **uma vez só, na construção de
`curated/`**, com semente registrada em `run_meta.json`. Depois disso é dado. Determinístico,
reproduzível e distributivamente realista ao mesmo tempo.

O modelo depende inteiramente de `broker/`, e o broker retém pouco histórico de tick. A coleta
contínua de ticks reais deve começar **imediatamente** e rodar sem interrupção — cada dia não
coletado é verdade de campo perdida para sempre.

### 10.6 Máscara de sessão

A Dukascopy negocia nos horários dela; a Exness tem intervalo diário e fecha sexta mais cedo.
**Ticks fora das sessões da Exness devem ser removidos em `curated/`.** Sem isso, o backtest
opera em janelas onde não haveria execução possível, e o resultado infla em silêncio — as bordas
são justamente onde o preço se move sem que se possa reagir.

Sessões do símbolo **no verão americano**: domingo 22:00–24:00 (negociação a partir de 22:05);
segunda a quinta 00:00–20:58 e 22:00–24:00; sexta 00:00–20:58; sábado fechado.

**No inverno americano tudo desloca +1 hora.** Medido, não suposto (§10.7): a parada diária é
`20:58→22:02` em julho e `21:58→23:01` em janeiro, sem exceção em 31 dias amostrados. O relógio
do servidor é fixo; o que se move é o calendário do COMEX por baixo dele, e a sessão configurada
do símbolo acompanha.

Tratar `20:58` como constante do ano inteiro **descarta uma hora real de negociação por dia
durante o inverno** — na prática 1,36 milhão de ticks nos quatro anos de `raw/`. Implementado com
a regra de DST em `research/lib/sessions.py`.

### 10.7 Fuso — CONFIRMADO

**Servidor = UTC, relógio fixo.** Medido em 2026-08-02 por `MQL5/Scripts/ARROW/DataAudit.mq5`
sobre o histórico M1 do broker; veredicto em `reports/broker-audit.md`.

| Estação | Parada diária (hora de servidor) | Dias |
|---|---|---|
| Julho (verão americano) | `20:58` → `22:02` | 16 de 16 |
| Janeiro (inverno americano) | `21:58` → `23:01` | 15 de 15 |

O teste não precisou de fonte externa: o símbolo se testa contra si mesmo. A manutenção do COMEX
é 17:00–18:00 em Nova York, o que em UTC é 21:00–22:00 no verão e 22:00–23:00 no inverno, porque
Nova York muda e UTC não. Logo, se o relógio do servidor observasse DST a parada ficaria na mesma
hora nas duas estações; **ela desliza exatamente uma hora, sem uma única exceção em 31 dias.** O
relógio não se mexe.

Consequências, e a segunda é a que mais custa:

1. **Alinhamento com a Dukascopy por constante**, não por data. As duas são UTC.
2. **Mas a sessão configurada do símbolo desliza com o DST americano** (§10.6). Em janeiro há
   barras M1 até 21:57; se a sessão terminasse às 20:58 o ano inteiro, não existiria barra
   nenhuma entre 20:58 e 21:58. Toda máscara de sessão precisa da regra de DST.

**Por que não `TimeCurrent()` vs `TimeGMT()`:** essas funções medem o offset no instante da
chamada. Entregam uma estação só, e um servidor que desloca uma hora em março produz leitura
idêntica a um que nunca desloca. O offset instantâneo foi medido em zero e é consistente com o
resultado — mas sozinho ele não teria respondido nada.

Todo timestamp interno em UTC; conversão apenas na borda.

### 10.8 Símbolo customizado no MT5

Necessário **apenas** para a fase do Strategy Tester. A pesquisa em `research/` não depende dele.

- `CustomSymbolCreate(nome, caminho, "XAUUSDm")` para herdar tick value, digits e contract size
- **Sessões não são clonadas** — exigem `CustomSymbolSetSessionQuote` e
  `CustomSymbolSetSessionTrade` explícitos
- Importação por script MQL5 com `CustomTicksReplace`, nunca pela GUI
- Preencher `time_msc` e flags `TICK_FLAG_BID|TICK_FLAG_ASK`; array crescente
- Validar tick value: 1 lote, movimento de $1 = $100

---

## 11. Arquitetura de testes

Quatro camadas. A terceira não é o que parece.

| # | Camada | Onde | Mede |
|---|---|---|---|
| 1 | Pesquisa | Python sobre `bars/` | IC, monotonicidade, bootstrap |
| 2 | Simulação de execução | Python sobre `curated/` | Esperança em R com spread real |
| 3 | Strategy Tester | MT5, símbolo customizado | **Consistência da implementação** |
| 4 | Forward | Demo do broker real | Execução |

### 11.1 O papel do Strategy Tester

A função principal do backtest no MT5 **não é descobrir se o sensor funciona** — isso já foi
respondido nas camadas 1 e 2, mais rápido e mais barato. A função é **provar que o código MQL5
faz o que o Python disse que faz**.

Se o Python deu +0,05R e o MT5 dá +0,05R sobre o mesmo dado, a implementação está correta. Se
divergem, há bug — e o bug é a descoberta, não o resultado.

Consequência: divergência entre camada 2 e camada 3 é tratada como **defeito a investigar**,
nunca como "o tester está mais certo".

### 11.2 Os três gaps

Um "gap de fidelidade" único não diz o que consertar. São três, medidos separadamente:

| Gap | Compara | Isola |
|---|---|---|
| **Fonte** | Dukascopy vs Exness, mesmo modelo de spread | O feed de preço difere? |
| **Resolução** | Tick real vs M1 OHLC, mesma fonte | Simular tick vale a pena? |
| **Execução** | Backtest vs forward demo | Quanto custa slippage? |

Cada um é um número obrigatório no relatório do sensor. Gap de execução acima de 30% em R exige
investigação antes de qualquer capital real.

---

## 12. Infraestrutura multi-máquina

| Máquina | Papel |
|---|---|
| PC-Home | Base. Dev completo, MT5, compilação, Strategy Tester |
| PC-Escritório | Dev e compilação |
| Laptop | Dev e compilação |
| S23 Ultra | Somente leitura e revisão — não compila MQL5 |

O nome da máquina **não é derivável do hostname** e não pode ser adivinhado. É declarado em
`tools/setup/local_paths.ps1`, não versionado, junto do caminho do terminal e do `metaeditor64`.

### Junctions

O caminho do MQL5 é `%APPDATA%\MetaQuotes\Terminal\<GUID>\MQL5\` e **o GUID muda por
instalação**. Portanto:

- `tools/setup/junctions.ps1` lê o caminho de um arquivo local **não versionado**
- Junctions de `MQL5\Include\ARROW`, `MQL5\Indicators\ARROW`, `MQL5\Experts\ARROW` e
  `MQL5\Scripts\ARROW` para dentro do repositório
- Nenhum caminho absoluto de máquina entra em arquivo versionado

### Compilação

```
metaeditor64.exe /compile:"<caminho>" /log
```

Compilar e ler o log é obrigatório antes de declarar qualquer tarefa concluída.

### 12.1 Dados nunca entram no Git

O histórico de ticks tem vários GB. Um único arquivo acima de 100 MB é **rejeitado pelo GitHub no
push** — mas o commit local já existe nesse ponto, e desfazer exige reescrita de histórico.
Remover o arquivo depois não encolhe o repositório: o histórico retém o blob para sempre.

Por isso a proteção é em camadas, não só o `.gitignore`.

**`.gitignore` obrigatório — commitado ANTES de qualquer download terminar.** O arquivo na raiz é
a versão normativa; o bloco abaixo é o mínimo que ele deve conter:

```
# dados — nunca versionados
data/
download/
.dukascopy-cache/
*.csv
*.parquet
*.bi5
*.zip
!reports/**/*.csv

# binários e artefatos MQL5
*.ex5
*.ex4
MQL5/Files/
**/tester/

# local, por máquina
tools/setup/local_paths.*
!tools/setup/local_paths.example.*
.env
*.log

# python
__pycache__/
.ipynb_checkpoints/
```

Três entradas merecem explicação porque a ausência delas anula a regra que as cerca:

- `download/` é o diretório **padrão** do `dukascopy-node`. Se o `-dir` for omitido, o download
  cai em `C:\dev\ARROW\download\` — dentro do repositório e fora de `data/`.
- `.dukascopy-cache/` é o cache do `-ch`, criado na **raiz** do diretório de trabalho e composto
  de `.json`. Nenhuma outra regra da lista o alcança.
- As duas negações existem porque a regra imediatamente acima delas engoliria algo que precisa
  ser versionado: `*.csv` mataria os CSVs pequenos que a regra 4 abaixo autoriza em `reports/`, e
  `local_paths.*` mataria o próprio modelo, deixando uma máquina nova sem ponto de partida.

**Regras operacionais:**

1. **`-dir` sempre explícito**, apontando para `data/dukascopy`. Nunca rodar o downloader sem ele.
2. **Nunca `git add -A` nem `git add .`** neste repositório. Adicionar por caminho.
3. **Verificação antes de todo commit:** nenhum arquivo staged acima de 5 MB. Se houver, parar e
   investigar antes de commitar — não commitar e limpar depois.
   ```
   git diff --cached --name-only | ForEach-Object { if ((Get-Item $_).Length -gt 5MB) { $_ } }
   ```
4. **`reports/` é versionado, mas só aceita markdown, PNG e CSV pequeno.** Saída volumosa de
   teste vai para `data/`, e o relatório referencia o caminho em vez de embutir o conteúdo.

**Se dado já foi commitado:** se ainda não houve push, `git reset` até antes do commit resolve.
Se já houve push, é reescrita de histórico com `git filter-repo` e force-push — tratar como
incidente, escrever no relatório de sessão, e verificar que nenhuma outra máquina tinha puxado o
commit antes.

### 12.2 Repositório público

Código público, dados não. **Nunca entram:** credenciais, número de conta, tokens, nome de
servidor, arquivos de tick da Dukascopy (volume, e a redistribuição pode violar os termos da
fonte), ticks do broker, qualquer identificador pessoal.

---

## 13. Restrições operacionais

| Parâmetro | Valor |
|---|---|
| Broker / conta | Exness, Standard |
| Símbolo | `XAUUSDm` |
| Dígitos | 3 — 1 point = $0,001/oz |
| Tamanho de contrato | 100 XAU |
| Moeda de lucro / moeda da conta | USD / **JPY** |
| Spread | Flutuante, piso 0,20 = **$20/lote round-trip** |
| Comissão | Zero — o spread é o custo total |
| Nível de Stops | 0 |
| Volume | mín 0,01 / máx 200 / passo 0,01 |
| Margem | ~¥31.844/lote — **1:2000** |
| Swap compra / venda | **−482,5 pontos** ($48/lote/noite) / 0. Quarta ×3 |
| Capital inicial | `<<PENDENTE>>` |
| Drawdown máximo tolerado | `<<PENDENTE>>` |
| Critério para passar de demo a real | `<<PENDENTE>>` |

**Confirmada por medição** em 2026-08-02 (`reports/broker-audit.md`): dígitos, point, contract
size, nível de stops, volumes, swap e rollover ×3 batem com o servidor. Duas adições medidas:

- `SYMBOL_CHART_MODE = Bid` — o MT5 **de fato** plota bid, o que era premissa da §10.3
- Tick value **¥15,7427** por tick de 1 lote, e ¥15.743 para um movimento de $1/oz. Os dois
  saem de caminhos independentes (`SYMBOL_TRADE_TICK_VALUE` e `OrderCalcProfit`) e batem entre
  si; implicam USDJPY ≈ 157,4
- Histórico M1 do broker desde **2014-01-14**, 3.265.408 barras. A retenção curta é de **tick**,
  não de barra — o que abre 12 anos de sobreposição para medir o gap de fonte da §11.2

O spread não foi medido com o mercado aberto e continua sendo premissa. `XAUUSDz` não foi
auditado: o script não conseguiu selecioná-lo.

### 13.1 O custo como exigência de edge

O spread é **pedágio fixo pago na entrada**, não custo por unidade de tempo. Mas ele desloca **as
duas barreiras na mesma direção**: numa compra com alvo e stop líquidos de tamanho `R`, o bid
precisa subir `R+c` para ganhar e só cair `R−c` para perder.

Sob caminho sem deriva: P(ganhar) = `(R−c)/2R` e esperança = **exatamente −c**, para qualquer
escolha de alvo e stop. A métrica operacional é o **acréscimo de acerto necessário**, `c/(2R)`:

| Alvo/stop líquido | Acerto sem edge | Edge exigido |
|---|---|---|
| $0,30 | 16,7% | **+33 pp** |
| $1,00 | 40% | +10 pp |
| $3,00 | 46,7% | **+3,3 pp** |
| $5,00 | 48% | +2 pp |

Alvos abaixo de ~$1,00 líquido exigem 10 pp ou mais e são hipótese extraordinária, não ponto de
partida.

### 13.2 Onde a sessão entra

A sessão não altera o custo. Altera **quanto tempo leva para R ficar grande o bastante**, já que
R alcançável ≈ σ√T.

**Medido**, não estimado: `research/audit_sigma.py` sobre 1.380.142 barras M1 dos quatro anos de
`raw/`, com máscara de sessão e feriados aplicados. Relatório em `reports/sigma-auditoria.md`.
σ é o desvio-padrão da variação de preço em uma barra M1, em USD/oz, sobre o bid.

**Valores de 2026** (ouro ~$4.597) — `T = (R/σ)²`:

| Sessão (UTC) | σ medida | R=$1 (exige 10 pp) | R=$3 (exige 3,3 pp) | R=$5 (exige 2 pp) |
|---|---|---|---|---|
| Asiático 00–07 | **2,50** | 0,2 min | 1,4 min | 4,0 min |
| Londres 07–12 | **2,25** | 0,2 min | 1,8 min | 5,0 min |
| Sobreposição LDN/NY 12–16 | **3,32** | 0,1 min | 0,8 min | 2,3 min |
| Nova York 16–21 | **2,42** | 0,2 min | 1,5 min | 4,3 min |

**A afirmação de que a asiática é ~3× mais exigente está morta.** Ela exigia σ da asiática ~3×
menor que a da sobreposição. A razão medida subiu de forma monótona ao longo da janela — 0,42 em
2022, 0,43, 0,52, 0,71, **0,75 em 2026** — e o perfil intradiário achatou. Em 2026 a hora **1
UTC** (09:00 em Pequim, abertura da Shanghai Gold Exchange) é a segunda hora mais volátil do dia
inteiro. Em 2023 o mesmo código dá o perfil clássico, com pico na sobreposição: a mudança está no
mercado, não na medição.

**σ em dólares triplicou em dois anos**, de 0,586 em 2024 para 2,594 em 2026 — mas em pontos-base
do preço subiu bem menos, de 2,46 para 5,64 bps. Boa parte do salto é nível de preço, não regime.
Toda tabela em dólares tem prazo de validade e **deve ser remedida quando o ouro mudar de
patamar**; a série por ano está em `reports/sigma-ano-x-sessao.csv`.

**Ressalva contra otimismo.** `σ√T` supõe passeio aleatório sem deriva nem reversão, e a σ acima é
de fechamento a fechamento no M1 — portanto **contaminada por bid-ask bounce**, que infla σ sem
representar movimento aproveitável. Os tempos da tabela são, por construção, o **melhor caso**. O
alcance real em T minutos é menor, e quanto menor é pergunta em aberto até `bars/` existir e
permitir medir o range efetivo.

Nenhuma sessão é proibida. Com σ ≈ 2,5 em qualquer sessão, alvos de $3 a $5 líquidos — que exigem
apenas 3,3 pp e 2 pp de acerto direcional (§13.1) — são alcançáveis em 1 a 5 minutos. Isso é
materialmente mais favorável do que as estimativas antigas sugeriam.

Ordem limitada na entrada é a única forma de não pagar o spread — ao custo de seleção adversa.
Linha futura, fora do escopo atual.

### 13.3 Consequências operacionais da spec

- **Conta em JPY com lucro em USD:** todo trade carrega conversão USDJPY. R é imune; equity,
  drawdown e agregação em ienes não. Limites de risco definidos em R; curva em JPY reportada
  separadamente.
- **Alavancagem ~1:2000:** margem não é restrição e o broker não protege de nada. Todo controle
  de risco vive na EA. **Stop obrigatório em toda ordem, sem exceção.**
- **Swap assimétrico:** longs pagam $48/lote/noite, shorts zero, quarta ×3. Um trade que vaze
  para overnight contamina o backtest inteiro. **Fechamento forçado antes do intervalo diário é
  regra dura.**
- **Nível de Stops = 0:** favorável — SL/TP apertados são tecnicamente permitidos.

---

## 14. Fora de escopo

- Qualquer forma de martingale, grid ou recuperação por exposição
- Otimização de parâmetros antes do Gate 2 ter sido passado isoladamente
- Componentes auto-adaptativos ou de aprendizado online em produção
- Sensor escrito em MQL5 antes de a hipótese sobreviver a teste em `research/`
- Outros instrumentos ou timeframes além de XAUUSD M1 (M5/M15/M30 apenas como contexto macro)
- Refatoração estética ou reorganização não solicitada
- Painéis e dashboards em MQL5 além do necessário para visualizar sensores

---

## 15. Armadilhas conhecidas do MQL5

- `BarsCalculated()` antes de `CopyBuffer()` — sem isso, desalinhamento silencioso
- Buffers de setas não limpos em ticks incrementais — setas fantasma empilhadas
- **3 dígitos: 1 point = $0,001.** Filtros de spread em pontos se comportam de forma
  contraintuitiva. Sempre logar unidade e valor.
- Filtro de spread nunca acima do stop de emergência na ordem de avaliação — durante spikes,
  bloqueia justamente o stop que precisava disparar
- Arredondamento de volume achatando progressões silenciosamente
- Contract size do ouro é 100 oz, não 100.000 — a matemática de lote difere de FX
- `OnCalculate` com `prev_calculated` incorreto em recálculo de histórico

---

## 16. Como Claude Code deve trabalhar

**Divisão de superfícies:**

- **Chat:** debate conceitual, desenho experimental, matemática, decisão de arquitetura
- **Claude Code:** implementação, refatoração, compilação, git
- **Cowork:** análise dos CSVs, estatística, relatórios

Se uma tarefa exigir debate conceitual aberto, dizer isso e sugerir levá-la ao chat em vez de
decidir sozinho no meio da implementação.

**Regras:**

1. Antes de mudança estrutural, ADR em `docs/decisions/` — contexto, decisão, alternativas
   rejeitadas e por quê
2. Edições cirúrgicas. Não reescrever arquivo inteiro quando um trecho resolve
3. Compilar e ler o log antes de dizer que terminou
4. Verificar balanceamento de chaves e parênteses antes de entregar
5. Nunca reabrir cláusula pétrea. Objeção vai para ADR, e a implementação para
6. Nunca reportar número que não saiu de execução real e logada
7. Ao concluir um sensor, atualizar `docs/sensors/<nome>.md`
8. Commits pequenos, mensagem descrevendo o porquê

---

## 17. Protocolo de sessão e sincronização

### 17.1 Um escritor só

**O Claude Code é a única entidade que escreve no repositório.** O chat não tem acesso ao disco
nem permissão de push — fato técnico, não convenção.

- O chat produz task briefs, ADRs e propostas de delta para `STATE.md`
- O usuário **não copia arquivos gerados no chat diretamente para o repo**
- Isso elimina por construção o conflito "arquivo do chat sobrescrevendo árvore de trabalho"

### 17.2 `STATE.md`

Na raiz. **Primeira leitura obrigatória de toda sessão, em qualquer superfície.** Se contradiz o
contexto carregado ou a memória da conversa, **`STATE.md` vence**.

Escrito exclusivamente pelo Code. O chat propõe o delta; nunca edita.

### 17.3 Trava por sessão

`STATE.md` declara `Status: ABERTA | FECHADA` e a máquina. Se `ABERTA` numa máquina diferente, o
Code não inicia: avisa com máquina e horário e pergunta se foi abandonada. Sessão abandonada é
fechada com commit próprio antes de qualquer outra coisa.

### 17.4 Ritual de abertura

1. `git pull --rebase`
2. Ler `STATE.md` e checar a trava
3. Ler `CLAUDE.md` e o índice de `docs/decisions/`
4. Criar branch `session/AAAA-MM-DD-<slug>`
5. Marcar `Status: ABERTA` + máquina + branch, commit
6. Só então começar

### 17.5 Ritual de encerramento

1. Compilar; nada é declarado pronto sem log limpo
2. Escrever `docs/sessions/AAAA-MM-DD-HHMM-<slug>.md`
3. Converter em ADR toda decisão estrutural da sessão
4. Atualizar `STATE.md`: fechar sessão, pendências, próximo passo
5. Mergear em `main` **ou** marcar como WIP em `STATE.md`
6. `git push` e confirmar `git status` limpo

**Nunca encerrar com alterações não commitadas.** Com quatro máquinas, trabalho não commitado é
trabalho perdido ou duplicado.

### 17.6 Precedência em caso de contradição

1. O que está em **ADR** vence
2. Se nenhum lado está em ADR, **não é decisão, é sugestão** — vai para debate no chat
3. `STATE.md` vence sobre memória de conversa em qualquer superfície

O que não está no repositório não existe. Isso resolve também a perda por compactação de
contexto.

---

## 18. Estado atual

Nenhum sensor validado. Nenhuma medição real. **Em curso:** uma corrida única de download
cobrindo 4 anos de ticks Dukascopy (2022-08 a 2026-08) para `data/dukascopy/`, encadeando os
segmentos anuais de 2025 para 2022 (§10.1).

**Próximos passos na ordem:**

1. **`.gitignore` commitado agora, antes de o download terminar** (§12.1). Uma vez que dado entra
   no histórico, remover não encolhe o repositório.
2. **`Scripts/ARROW/BrokerTickLogger.mq5` — começa hoje, roda ininterrupto.** Loga bid/ask do
   `XAUUSDm` para `data/broker/`. É o único insumo do modelo de spread, e o broker retém pouco
   histórico. Cada dia não coletado é verdade de campo perdida para sempre. Puxar também o que
   já existe via `CopyTicks` antes que role para fora da janela de retenção.
3. **Tese** — duas ou três hipóteses mecânicas falsificáveis, escritas antes de olhar dado. Sem
   isso, a construção de sensores é busca cega, e a correção para testes múltiplos existe
   justamente para punir busca cega.
4. `research/lib/` — conversão Dukascopy CSV → Parquet particionado por mês, carregamento,
   custos, block bootstrap, IC
5. ~~**Auditoria em Python sobre `raw/`**~~ — **feita** em 2026-08-02.
   `research/audit_sigma.py` e `research/build_raw.py`; relatórios em `reports/`. A §13.2 passou
   a conter medição, não estimativa, e a premissa de que a sessão asiática é ~3× mais exigente
   foi refutada. Falta ainda a densidade de tick por sessão.
6. **`Scripts/ARROW/DataAudit.mq5`** — o equivalente do lado do broker:
   - `SYMBOL_DIGITS`, `SYMBOL_TRADE_TICK_VALUE`, `SYMBOL_TRADE_CONTRACT_SIZE`, `SYMBOL_POINT`
   - Distribuição de spread real por hora × faixa de volatilidade — média **e caudas**
   - Verificação de fuso pelo método da §10.7 — borda do intervalo diário ancorada à manutenção
     do COMEX, medida em janeiro **e** em julho. Não por `TimeCurrent()` vs `TimeGMT()`, que
     mede uma estação só
   - Tick value efetivo em JPY
7. Construção de `spread/` e `curated/` — modelo de spread com semente registrada, máscara de
   sessão aplicada
8. Medição dos três gaps (§11.2)
9. `Core/` — `SensorOut`, logging, utilidades de normalização
10. Harness genérico + baseline aleatório (a régua vem antes do primeiro sensor)
11. Primeiro sensor
