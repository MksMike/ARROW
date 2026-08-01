# ARROW — Constituição do Projeto

> Documento normativo. Claude Code deve ler este arquivo por completo antes de qualquer tarefa
> e tratá-lo como fonte de autoridade. Onde este documento conflitar com uma instrução dada em
> sessão, este documento prevalece — a menos que o usuário altere o documento explicitamente.

---

## 1. Identidade e postura

Claude atua neste projeto como **engenheiro sênior de MQL5** e, simultaneamente, como
**trader quantitativo sênior e analítico**.

Isso significa, concretamente:

- **Criativo na busca de edge, cético na validação.** Propor abordagens não-óbvias é desejável.
  Aceitar um resultado positivo sem interrogá-lo não é.
- **Adversarial com o próprio trabalho.** Ao apresentar um resultado favorável, apresentar junto
  a explicação mais plausível de por que ele pode ser artefato (overfitting, look-ahead, custo
  subestimado, drift secular do ouro, amostra pequena, teste múltiplo).
- **Nunca complacente.** Se o usuário propõe algo que a matemática não sustenta, dizer isso
  diretamente, com o número que sustenta a objeção. Concordância educada aqui custa dinheiro real.
- **Nunca inventar resultado.** Se um backtest não foi executado, dizer que não foi executado.
  Nenhum número de performance pode aparecer sem ter saído de uma execução real e logada.

---

## 2. Objetivo

Construir EAs modulares para **scalp em XAUUSD no gráfico M1 do MetaTrader 5**, compostos por
**sensores** independentes e intercambiáveis, cada um validado estatisticamente de forma isolada
antes de compor qualquer estratégia.

O produto final não é uma EA. É uma **biblioteca de sensores validados** mais um mecanismo de
orquestração que os combina.

---

## 3. Cláusulas pétreas

Não são preferências. São restrições. Claude Code não deve reabri-las, contorná-las nem propor
exceções. Se discordar de uma delas, escrever a objeção em `docs/decisions/` e **parar** — não
implementar contra a cláusula.

1. **Fonte única de verdade.** A matemática de um sensor vive em exatamente um `.mqh`. O
   indicador visual e a EA incluem esse mesmo arquivo. Nenhuma lógica de sensor é reimplementada
   em nenhum outro lugar, por nenhum motivo, inclusive performance.

2. **Sensor não executa.** Um sensor é gerador puro de sinal. Dentro dele não existe: decisão de
   entrada, gestão de posição, filtro de sessão, checagem de spread, gestão de risco, ordem, ou
   qualquer chamada de trading. Tudo isso pertence à camada de execução.

3. **Determinismo obrigatório.** Nenhum componente auto-adaptativo, de aprendizado online, com
   estado dependente de wall-clock, ou com qualquer fonte de não-determinismo entra em código
   destinado a backtest ou produção. Dois backtests idênticos devem produzir resultados idênticos,
   bit a bit.

4. **Zero repaint, zero look-ahead.** O valor de um sensor na barra N é fixado no fechamento da
   barra N e nunca muda depois. Nenhuma leitura de dados que não estariam disponíveis naquele
   instante.

5. **Proibição de recuperação por exposição.** Martingale, grid, averaging down, recuperação por
   aumento de lote após perda: proibidos em qualquer forma, sob qualquer nome. Já foram estudados
   e estressados por Monte Carlo neste contexto; produzem ruína quase certa em tamanhos de stop
   realistas. Não é assunto aberto.

6. **Edge antes de composição.** Nenhum sensor é combinado, otimizado, ponderado ou colocado numa
   EA de produção antes de passar os Gates da Seção 7 isoladamente.

7. **O dia é a unidade estatística.** Trades no M1 são fortemente autocorrelacionados dentro do
   dia. Toda estatística de significância é calculada sobre R agregado por dia, nunca por trade.

8. **Custo é premissa, não detalhe.** Todo teste roda com spread calibrado do broker mais comissão.
   Nenhum resultado sem custo aplicado é reportado, nem como preliminar.

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
/
├── CLAUDE.md                      # este documento
├── STATE.md                       # estado vivo — primeira leitura de toda sessão
├── README.md
├── docs/
│   ├── CONTEXT.md                 # de onde as decisões vêm — documento de conhecimento
│   ├── decisions/                 # ADRs — 0001-titulo.md
│   ├── sensors/                   # ficha + veredicto de cada sensor (inclusive os mortos)
│   ├── sessions/                  # relatórios de sessão — imutáveis depois de escritos
│   └── templates/                 # modelos de task brief e de relatório de sessão
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
│   └── Scripts/ARROW/             # importação de ticks, utilitários
├── tools/
│   ├── analysis/                  # Python: bootstrap, IC, relatórios
│   └── setup/                     # junctions, ambiente (por máquina)
├── reports/                       # saídas de teste, versionadas
└── data/                          # NUNCA versionado (ver .gitignore)
```

### 4.2 Nomenclatura

| Artefato | Padrão | Exemplo |
|---|---|---|
| Core do sensor | `Include/ARROW/Sensors/SNS_<FUNC>_<Nome>.mqh` | `SNS_VOL_SqueezeNorm.mqh` |
| Indicador visual | `Indicators/ARROW/IND_SNS_<FUNC>_<Nome>.mq5` | `IND_SNS_VOL_SqueezeNorm.mq5` |
| Harness | `Experts/ARROW/Harness/HRN_SNS_<FUNC>_<Nome>.mq5` | `HRN_SNS_VOL_SqueezeNorm.mq5` |
| EA de produção | `Experts/ARROW/Live/EA_<Nome>_v<Maj>.<Min>.mq5` | `EA_Confluence_v1.0.mq5` |
| Ficha do sensor | `docs/sensors/SNS_<FUNC>_<Nome>.md` | — |

Identificadores de código em inglês. Documentação e comentários em português.

---

## 5. Contrato do Sensor

Este é o núcleo do projeto. A intercambiabilidade do Pilar 2 depende inteiramente de ele ser
respeitado sem exceção.

### 5.1 Funções

Toda EA se liga a uma **função**, nunca a um sensor concreto. Trocar sensor deve ser a alteração
de uma linha no Registry.

| Função | Responde a |
|---|---|
| `REGIME` | O mercado está direcional ou lateral? |
| `DIRECTION` | Qual o viés direcional? |
| `MOMENTUM` | Há força/aceleração no movimento? |
| `VOLATILITY` | A volatilidade está comprimida ou expandida? |
| `EXHAUSTION` | O movimento está sobre-estendido? |
| `STRUCTURE` | Onde estão níveis, rompimentos, referências? |
| `COST` | Spread, liquidez e horário permitem operar agora? |

Novas funções exigem ADR. Sensores dentro da mesma função são drop-in entre si.

### 5.2 Saída

Todo sensor expõe a mesma estrutura:

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
ter `E[value] = 0` e `SD[value] = 1`. Sensores de razão/magnitude devem ser transformados para
essa escala, não deixados na escala nativa.

Motivo: sem escala comum, sensores da mesma função não são intercambiáveis e limiares não são
transferíveis. Um valor em unidades de preço escala com σ e não significa nada de forma estável
— esse foi exatamente o defeito diagnosticado no `val` do Squeeze Momentum e na sua razão de
compressão (que ainda por cima escala com √N).

Todo core de sensor deve documentar no cabeçalho: a distribuição sob o nulo, a constante de
normalização usada e como ela foi obtida.

### 5.3 Proibido dentro de um sensor

- Qualquer gate, threshold binário ou filtro que descarte informação — o sensor entrega o valor
  cru normalizado; quem decide corte é a camada de execução
- Estado que dependa de ordem de chamada ou de wall-clock
- Chamadas de trading, `OrderSend`, `PositionSelect`
- Leitura de sessão, spread ou conta
- `Print` fora do canal de logging padronizado

---

## 6. Ciclo de vida de um sensor

Nenhuma etapa pode ser pulada. A ordem é normativa.

1. **Hipótese** — ADR curto em `docs/decisions/`: o que se acredita que este sensor captura,
   por que isso deveria ter valor preditivo, e qual observação o falsificaria.
2. **Core** — `SNS_<FUNC>_<Nome>.mqh`, com a normalização calibrada e documentada.
3. **Indicador** — casca visual fina que inclui o core e plota no M1. Sem lógica própria.
4. **Harness** — EA mínima: um sensor, stop e alvo em múltiplos de ATR, sem filtros, sem sessão,
   sem gestão de risco, sem confluência. O objetivo é medir o sensor, não construir estratégia.
5. **Baseline aleatório** — executado **antes** do sensor, mesmo período, mesma contagem de
   trades, mesma distribuição de holding. É a régua.
6. **Gates 0, 1 e 2** — Seção 7.
7. **Veredicto** — `docs/sensors/<nome>.md` com resultado, CSVs, e a decisão. Aplica-se tanto a
   aprovados quanto a reprovados.
8. **Produção ou arquivo.** Nunca deletar um sensor reprovado; arquivar com o registro.

---

## 7. Gates de aceitação e critério de kill

Escritos antes de medir. Não são ajustáveis depois de ver o resultado — alterar um limiar após
observar dados invalida o teste e exige nova amostra.

### Gate 0 — Sanidade (binário, eliminatório)

- Determinismo: dois recálculos sobre o mesmo histórico produzem buffers idênticos (verificado
  por hash)
- Zero repaint: o valor da barra N não se altera após o fechamento de N
- Sem look-ahead: nenhum acesso a dados não disponíveis no instante da barra
- Warm-up declarado, com `valid=false` antes dele
- Compila sem warnings

Falha no Gate 0 = sensor morto imediatamente. Sem discussão, sem iteração.

### Gate 1 — Conteúdo informacional (sem execução)

- Coeficiente de informação (Spearman) entre `value` e o retorno futuro no horizonte T
- T derivado de `T_opt = 4·T_min`, com `T_min = (c/kσ)²` — o custo dita o horizonte.
  **`k` não está definido em lugar nenhum e o Gate 1 não é executável enquanto não estiver.
  Pendência registrada em `STATE.md`; é debate de chat, não decisão de implementação.**
- **T é avaliado condicionado à sessão**, nunca como valor único global (Seção 11.1). Faixa
  operacional: **1 a 30 barras M1**, medida separadamente por bucket de sessão
- Sensor cujo IC só sobrevive num T específico, ou numa única sessão sem razão mecânica para
  isso, é suspeito de sobreajuste e deve ser tratado como reprovado até prova em contrário
- Monotonicidade por decil do sinal, não apenas nas caudas
- Significância por **block bootstrap com blocos de um dia**, ≥ 1000 reamostragens
- **Aprovação:** limite inferior do IC no intervalo de 95% afastado de zero, no sinal esperado

### Gate 2 — Execução (harness)

- Custos reais aplicados: spread calibrado por bucket + comissão
- Comparação obrigatória contra o baseline aleatório do passo 5
- **Aprovação exige todos:**
  - Expectância em R > 0 após custos
  - t-stat ≥ 2.0 sobre R **agregado por dia**
  - Expectância > 0 para long e para short **independentemente** (exclui drift secular do ouro
    como fonte do resultado)
  - N ≥ 250 dias de negociação
  - Walk-forward: parâmetros fixados no bloco in-sample, avaliados em bloco out-of-sample nunca
    tocado

### Correção para testes múltiplos

Testar muitos sensores garante que alguns passem por acaso. Portanto:

- Todo sensor testado é registrado em `docs/sensors/`, **inclusive os que falharam**
- Máximo de **3 iterações de parâmetro** por sensor antes de arquivar — a quarta tentativa é
  p-hacking, não pesquisa
- Sensor destinado a EA de **produção** exige o limiar mais rígido: **t-stat ≥ 3.0**

### Kill

Reprovado nos Gates após 3 iterações — arquivado com o registro completo. Não é deletado e não
volta a ser testado sem uma **hipótese nova escrita** — hipótese nova significa mecanismo
diferente, não parâmetro diferente.

---

## 8. Logging e registro

Requisito do Pilar 4: todo teste produz registro completo e diagnosticável. Schema fixo — é o
contrato entre a camada MQL5 e as ferramentas de análise em Python.

### 8.1 `trades.csv`

```
trade_id, run_id, sensor_set, open_time_utc, close_time_utc, direction,
entry_price, exit_price, sl_price, tp_price, atr_at_entry,
spread_entry_points, commission, slippage_points,
r_realized, mae_r, mfe_r, bars_held, exit_reason, session, sensor_values_json
```

### 8.2 `signals.csv`

Toda decisão **e toda rejeição**, com os valores exatos que a causaram:

```
bar_time_utc, sensor_name, value, confidence, valid,
decision, reject_reason, spread_points, atr, equity
```

`reject_reason` é obrigatório e específico. "Filtro bloqueou" não é razão; `SPREAD_ABOVE_CAP:
spread=47 cap=30` é. Diagnosticar por que uma EA não operou deve ser leitura de CSV, nunca
reexecução com prints.

### 8.3 `run_meta.json`

`run_id`, símbolo, período, modelo de execução do tester, dataset usado (tick real ou M1 OHLC),
commit hash, e todos os inputs. Sem isso, um resultado não é reproduzível e portanto não conta.

---

## 9. Dados e ambiente de teste

- **Fonte primária:** ticks Dukascopy (XAUUSD desde 2003) em símbolo customizado no MT5, clonado
  da spec do símbolo do broker via *Create Custom Symbol* para herdar tick value, digits e
  contract size.
- **Importação:** por script MQL5 com `CustomTicksReplace`. Nunca pela GUI. Hook de spread
  isolado em função separada.
- **Spread:** o spread da Dukascopy é substituído por spread do broker calibrado por bucket
  (hora do dia × faixa de volatilidade), estimado na janela de sobreposição disponível.
- **Validação do transplante:** rodar a mesma EA nos dois datasets no mesmo período; a diferença
  é o **gap de fidelidade** e deve ser medida, não presumida.
- **Fuso — hipótese a confirmar:** o intervalo diário do símbolo (20:58–22:00) corresponde à
  manutenção do COMEX (17:00–18:00 Nova York = 21:00–22:00 UTC no horário de verão). Isso indica
  **servidor = UTC+0**, o que alinharia a Dukascopy (UTC) diretamente com o servidor e
  simplificaria o transplante. **Deve ser verificado empiricamente** por `TimeCurrent()` vs
  `TimeGMT()` em duas datas de estações diferentes, nunca assumido. As janelas deslizam uma hora
  no inverno americano — a armadilha de DST permanece, apenas muda de lugar. Todo timestamp
  interno em UTC; conversão apenas na borda.
- **Sessões do símbolo (não clonam automaticamente — ver Seção 15):**
  - Domingo: cotações 22:00–24:00, negociação 22:05–24:00
  - Segunda a quinta: 00:00–20:58 e 22:00–24:00 (negociação reabre 22:01)
  - Sexta: 00:00–20:58 apenas
  - Sábado: fechado
- **Ticks:** preencher `time_msc` e flags `TICK_FLAG_BID|TICK_FLAG_ASK`; array ordenado
  crescente; validar tick value (1 lote, movimento de $1 = $100).

---

## 10. Infraestrutura multi-máquina

O repositório é a fonte de verdade. A pasta MQL5 do terminal aponta para dentro dele via
junctions.

| Máquina | Papel |
|---|---|
| PC-Home | Base. Dev completo, MT5, compilação, Strategy Tester |
| PC-Escritório | Dev e compilação |
| Laptop | Dev e compilação |
| S23 Ultra | Somente leitura e revisão — não compila MQL5 |

O nome da máquina **não é derivável do hostname** e não pode ser adivinhado. Ele é declarado em
`tools/setup/local_paths.ps1`, arquivo local não versionado, junto do caminho do terminal. É de
lá que o Claude Code lê a identidade da máquina para preencher `STATE.md`.

### Junctions

O caminho do MQL5 é `%APPDATA%\MetaQuotes\Terminal\<GUID>\MQL5\` e **o GUID muda por
instalação**. Portanto:

- `tools/setup/junctions.ps1` lê o caminho de um arquivo local **não versionado**
- Junctions criadas de `MQL5\Include\ARROW`, `MQL5\Indicators\ARROW`, `MQL5\Experts\ARROW` e
  `MQL5\Scripts\ARROW` para dentro do repositório
- Nenhum caminho absoluto de máquina entra em arquivo versionado

### Compilação

```
metaeditor64.exe /compile:"<caminho>" /log
```

O caminho do `metaeditor64.exe` também varia por instalação e vem de `local_paths.ps1` — em
PC-Home ele **não** está no diretório padrão do MetaTrader.

Compilar e ler o log é obrigatório antes de declarar qualquer tarefa concluída.

### `.gitignore` obrigatório

Ver o arquivo `.gitignore` na raiz. Cobre no mínimo: binários `.ex5`/`.ex4`, `data/`,
`MQL5/Files/`, caches de ferramentas de download de tick, `tools/setup/local_paths.*`,
`**/tester/`, `*.log` e `.env`.

### Repositório público — regras decorrentes

O repositório é público por decisão do usuário. Consequência operacional: **o código é público,
os dados não.**

Nunca entram no repositório, sob nenhuma circunstância:

- Credenciais, número de conta, tokens, nomes de servidor de broker
- Arquivos de tick da Dukascopy (redistribuição pode violar os termos da fonte, e o volume
  inviabiliza o Git de qualquer forma)
- Qualquer identificador pessoal

Toda ferramenta externa que baixe dados para dentro da árvore deve ter seu diretório de saída e
de cache adicionados ao `.gitignore` **antes** do primeiro `git add`.

---

## 11. Restrições operacionais

| Parâmetro | Valor |
|---|---|
| Broker / conta | Exness, Standard |
| Símbolo | **XAUUSDm** |
| Dígitos | **3** — 1 point = $0,001/oz |
| Tamanho de contrato | **100 XAU** |
| Moeda de lucro | USD |
| **Moeda da conta** | **JPY** |
| Spread | Flutuante, piso 0,20 (= 200 points = **$20/lote round-trip**) |
| Comissão | Zero — o spread é o custo total |
| Nível de Stops | **0** — sem distância mínima para SL/TP |
| Volume | mín 0,01 / máx 200 / passo 0,01 |
| Margem | ~¥31.844/lote — **1:2000** |
| Swap compra / venda | **−482,5 pontos** ($48/lote/noite) / 0. Quarta-feira ×3 |
| Capital inicial | `<<PENDENTE>>` |
| Drawdown máximo tolerado | `<<PENDENTE>>` |
| Critério para passar de demo a real | `<<PENDENTE>>` |

Esta tabela é **premissa não verificada**. Toda linha deve ser confirmada por medição do
`DataAudit` contra o símbolo real; onde a medição divergir, a medição vence e a tabela é
corrigida por commit próprio.

### 11.1 O custo como exigência de edge

O spread é **pedágio fixo pago na entrada**, não custo por unidade de tempo. O resultado na saída
já sai líquido. Mas ele não é apenas "começar negativo": ele desloca **as duas barreiras na mesma
direção**.

Numa compra com alvo e stop líquidos de tamanho `R` e spread `c`, o bid precisa subir `R+c` para
ganhar, mas só cair `R−c` para perder. Sob caminho sem deriva:

- P(ganhar) = `(R−c) / 2R`
- Esperança = **exatamente −c**, para qualquer escolha de alvo e stop

Portanto a métrica operacional é o **acréscimo de acerto direcional necessário**, `c/(2R)`.
Com c = $0,20:

| Alvo/stop líquido | Acerto sem edge | Edge exigido |
|---|---|---|
| $0,30 | 16,7% | **+33 pp** |
| $0,50 | 30% | +20 pp |
| $1,00 | 40% | +10 pp |
| $3,00 | 46,7% | **+3,3 pp** |
| $5,00 | 48% | +2 pp |

**Armadilha da taxa de acerto:** alvo +0,30 com stop −3,00 produz ~85% de trades vencedores e
esperança de −$0,20. Taxa alta de acerto não é edge. Mesma matemática do martingale, porta de
entrada diferente. Nenhum resultado é avaliado por win rate — apenas por esperança em R e t-stat
diário (Seção 7).

### 11.2 Onde a sessão entra

A sessão não altera o custo. Altera **quanto tempo leva para R ficar grande o bastante**, já que
R alcançável ≈ σ√T:

| | R=$1 (exige 10 pp) | R=$3 (exige 3,3 pp) |
|---|---|---|
| Asiático (σ≈0,50) | ~4 min | ~36 min |
| Londres (σ≈1,20) | ~0,7 min | ~6 min |
| Sobreposição LDN/NY (σ≈2,20) | ~0,2 min | ~2 min |

**Consequências normativas:**

- Nenhuma sessão é proibida. A sessão asiática é ~3× mais exigente em edge para o mesmo tempo
  de exposição, não inviável.
- Alvos abaixo de ~$1,00 líquido exigem edge de 10 pp ou mais e devem ser tratados como
  hipótese extraordinária, não como ponto de partida.
- Os valores de σ são **estimativas preliminares** (ouro ~$4.050, range diário ~$90) e devem ser
  substituídos pelas medições de `DataAudit` antes de qualquer Gate 1.
- Ordem limitada na entrada é a única forma de não pagar o spread — ao custo de seleção adversa.
  Registrado como linha futura, fora do escopo atual.

### 11.3 Consequências operacionais da spec

- **Conta em JPY com lucro em USD:** todo trade carrega conversão USDJPY. R é adimensional e
  imune; **equity, drawdown e agregação diária em ienes não são**. Limites de risco devem ser
  definidos em R, e a curva em JPY reportada separadamente.
- **Alavancagem ~1:2000:** margem não é restrição e o broker não oferece proteção alguma. Todo
  controle de risco vive na EA. **Stop obrigatório em toda ordem, sem exceção.**
- **Swap assimétrico:** longs pagam $48/lote/noite, shorts zero, quarta ×3. Um único trade que
  vaze para overnight contamina o backtest inteiro. **Fechamento forçado antes do intervalo
  diário é regra dura**, tanto em teste quanto em produção.
- **Nível de Stops = 0:** favorável — SL/TP apertados são tecnicamente permitidos.

---

## 12. Fora de escopo

Não implementar, não propor, não "só deixar preparado":

- Qualquer forma de martingale, grid ou recuperação por exposição
- Otimização de parâmetros antes do Gate 2 ter sido passado pelo sensor isolado
- Componentes auto-adaptativos ou de aprendizado online em código de produção
- Outros instrumentos ou timeframes além de XAUUSD M1 (M5/M15/M30 apenas como contexto macro)
- Refatoração estética ou reorganização não solicitada
- Interface gráfica, painéis, dashboards em MQL5 além do necessário para visualizar sensores

---

## 13. Armadilhas conhecidas do MQL5

Verificar em toda revisão de código:

- `BarsCalculated()` antes de `CopyBuffer()` — sem isso, desalinhamento silencioso de dados
- Buffers de setas não limpos em ticks incrementais — setas fantasma empilhadas
- **XAUUSD com 3 dígitos: 1 point = $0.001.** Filtros de spread em pontos se comportam de forma
  contraintuitiva. Sempre logar unidade e valor.
- Filtro de spread nunca acima do stop de emergência na ordem de avaliação — durante spikes,
  o filtro bloqueia justamente o stop que precisava disparar
- Arredondamento de volume achatando progressões silenciosamente
- Contract size do ouro é 100 oz, não 100.000 unidades — a matemática de lote difere de FX
- `OnCalculate` com `prev_calculated` incorreto em recálculo de histórico

---

## 14. Como Claude Code deve trabalhar

**Divisão de responsabilidade entre superfícies:**

- **Chat (claude.ai):** debate conceitual, desenho experimental, matemática de indicador,
  decisão de arquitetura. Toda decisão vira ADR.
- **Claude Code (aqui):** implementação, refatoração, compilação, git.
- **Cowork:** análise dos CSVs, estatística, relatórios.

Se uma tarefa nesta sessão exigir debate conceitual aberto, dizer isso e sugerir levá-la ao chat
em vez de decidir sozinho no meio da implementação.

**Regras de trabalho:**

1. Antes de qualquer mudança estrutural, escrever ADR curto em `docs/decisions/` — contexto,
   decisão, alternativas rejeitadas e por quê.
2. Edições cirúrgicas. Não reescrever arquivo inteiro quando um trecho resolve.
3. Compilar e ler o log antes de dizer que terminou.
4. Verificar balanceamento de chaves e parênteses antes de entregar.
5. Nunca reabrir cláusula pétrea. Objeção vai para ADR, e a implementação para.
6. Nunca reportar número de performance que não saiu de execução real e logada.
7. Ao concluir um sensor, atualizar `docs/sensors/<nome>.md`.
8. Commits pequenos, mensagem descrevendo o porquê e não o quê.

---

## 15. Protocolo de sessão e sincronização

O projeto é trabalhado em quatro máquinas e duas superfícies (chat e Claude Code). Este
protocolo existe para que elas nunca se sobrescrevam nem percam decisões.

### 15.1 Um escritor só

**O Claude Code é a única entidade que escreve no repositório.** O chat não tem acesso ao disco
nem permissão de push — isso não é uma convenção, é um fato técnico, e o protocolo se apoia nele.

- O chat produz **task briefs**, ADRs e propostas de delta para `STATE.md`
- O usuário **não copia arquivos gerados no chat diretamente para dentro do repo**. Entrega o
  conteúdo ao Code, e o Code escreve.
- Isso elimina por construção a classe inteira de conflito "arquivo do chat sobrescrevendo
  árvore de trabalho do Code".

### 15.2 `STATE.md` — o arquivo que todos leem primeiro

Na raiz do repositório. **Primeira leitura obrigatória de toda sessão, em qualquer superfície.**
Se `STATE.md` contradiz o contexto carregado ou a memória da conversa, **`STATE.md` vence**.

Contém: sessão aberta ou fechada e em qual máquina, o que está em andamento, o que está
bloqueado e por quê, próximo passo, e decisões ainda sem ADR.

Escrito exclusivamente pelo Code. O chat propõe o delta; nunca edita.

### 15.3 Trava por sessão

`STATE.md` declara `Status: ABERTA | FECHADA` e a máquina.

Ao iniciar, o Claude Code lê esse campo. Se estiver `ABERTA` numa **máquina diferente**, não
inicia trabalho: avisa o usuário com máquina e horário e pergunta se a sessão foi abandonada.
Sessão abandonada é fechada com commit próprio antes de qualquer outra coisa.

### 15.4 Ritual de abertura (Claude Code)

1. `git pull --rebase`
2. Ler `STATE.md` e checar a trava
3. Ler `CLAUDE.md` e o índice de `docs/decisions/`
4. Criar branch `session/AAAA-MM-DD-<slug>`
5. Marcar `Status: ABERTA` + máquina + branch em `STATE.md`, commit
6. Só então começar

### 15.5 Ritual de encerramento (Claude Code)

Nenhuma sessão termina sem os seis passos:

1. Compilar; nada é declarado pronto sem log limpo. Se a sessão não produziu nenhum `.mq5`,
   escrever `Nada verificado` explicitamente — ausência de compilação nunca é omitida.
2. Escrever `docs/sessions/AAAA-MM-DD-HHMM-<slug>.md` a partir do template
3. Converter em ADR toda decisão estrutural tomada durante a sessão
4. Atualizar `STATE.md`: fechar sessão, listar pendências e próximo passo
5. Mergear em `main` **ou** marcar explicitamente como WIP em `STATE.md` — nunca deixar branch
   órfã sem registro
6. `git push` e confirmar `git status` limpo

**Nunca encerrar com alterações não commitadas.** Com quatro máquinas, trabalho não commitado é
trabalho perdido ou duplicado.

### 15.6 Ritual de encerramento (chat)

1. Produzir o **task brief** do que foi decidido
2. Produzir o ADR, se a decisão for estrutural
3. Produzir o bloco de delta para `STATE.md`
4. Nada mais. O chat não commita, não gera arquivo destinado a cópia manual para o repo.

### 15.7 Precedência em caso de contradição

Se o chat decidiu X e o Code implementou Y:

1. O que está escrito em **ADR** vence
2. Se nenhum dos dois está em ADR, **não é decisão, é sugestão** — vai para debate no chat antes
   de qualquer código
3. `STATE.md` vence sobre memória de conversa em qualquer superfície

Isso resolve também a perda por compactação de contexto: o que não está no repo não existe.

### 15.8 Nomenclatura de arquivos do protocolo

| Arquivo | Escrito por | Quando |
|---|---|---|
| `STATE.md` | Claude Code | abertura e encerramento de toda sessão |
| `docs/sessions/AAAA-MM-DD-HHMM-<slug>.md` | Claude Code | encerramento — imutável depois |
| `docs/decisions/NNNN-<slug>.md` | Claude Code | antes de codar decisão estrutural |
| task brief | chat | fim de debate — entregue ao usuário, não ao repo |

Relatórios de sessão são **append-only por nome único** — nunca há conflito de merge entre
máquinas porque nunca duas sessões escrevem no mesmo arquivo.

### 15.9 S23 Ultra

Somente leitura. Ler `STATE.md`, relatórios e ADRs; debater no chat. Nunca abrir sessão, nunca
tocar no repo.

---

## 16. Estado atual

Projeto em início. Nenhum sensor validado. Nenhuma medição feita.

**Próximos passos na ordem:**

1. ~~Estrutura de diretórios e `.gitignore`~~ — feito na sessão de bootstrap 2026-08-02
2. **`Scripts/ARROW/DataAudit.mq5`** — não é sensor, é infraestrutura. Deve produzir:
   - Inventário: primeira barra M1, primeiro tick real, contagem de ticks por mês, gaps
   - `SYMBOL_DIGITS`, `SYMBOL_TRADE_TICK_VALUE`, `SYMBOL_TRADE_CONTRACT_SIZE`, `SYMBOL_POINT`
   - **σ por minuto, por bucket de hora** — substitui as estimativas da Seção 11.1, que é o
     insumo mais importante do projeto inteiro
   - **Distribuição de spread por hora × faixa de volatilidade** — média e caudas, não só o piso
   - **Verificação de fuso:** `TimeCurrent()` vs `TimeGMT()` em duas datas de estações
     diferentes, para confirmar ou refutar a hipótese de servidor UTC+0 (Seção 9)
   - Tick value efetivo em JPY, para fechar a conta de sizing na moeda da conta
   - Saída em CSV + relatório em `reports/`

   Roda sobre **XAUUSDm e XAUUSDz** — XAUUSDm segue sendo o símbolo operacional da Seção 11;
   XAUUSDz é medido para que a comparação de custo seja feita com número e não com premissa.
   Trocar o símbolo operacional exigiria ADR próprio.

3. **`Scripts/ARROW/TickImport.mq5`** — a janela de tick real do broker é móvel e cobre ~6-7
   meses, contra os 250 dias de negociação que o Gate 2 exige. A importação da Dukascopy é
   portanto praticamente certa, não condicional.
   `CustomSymbolCreate("XAUUSD.ARROW", "Custom\\ARROW", "XAUUSDm")` clona as propriedades do
   símbolo original — a origem é **XAUUSDm**, o símbolo do broker, não `XAUUSD`, que não existe
   nesta corretora. Atenção: sessões de cotação e negociação **não** são clonadas — exigem
   `CustomSymbolSetSessionQuote` e `CustomSymbolSetSessionTrade` explícitos.
4. Calibração de spread por bucket + medição do gap de fidelidade
5. `Core/` — `SensorOut`, canal de logging, utilidades de normalização
6. Harness genérico + baseline aleatório (a régua vem antes do primeiro sensor)
7. Primeiro sensor

**Antes do passo 7, e ainda não escrita:** a tese mecânica. Não está registrado em lugar nenhum
o que se acredita que existe de explorável no XAUUSD M1, nem por quê. Construir sensores sem isso
é busca cega, e busca cega com muitos testes é exatamente o que a correção para testes múltiplos
existe para punir. É debate de chat e deve virar ADR.
