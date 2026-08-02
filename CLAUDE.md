# ARROW — Constituição do Projeto

> Repositório: `C:\dev\ARROW`, público no GitHub. Ler por completo antes de qualquer tarefa.
>
> **Números medidos não estão aqui.** Spec do broker, calendário, integridade do histórico e
> volatilidade vivem em `docs/REFERENCIA-XAUUSD.md`, que é **gerado** a partir do dado. Este
> documento contém regras.

---

## 1. Isto é um laboratório

**Ideia se explora ao máximo. Só teste negativo mata ideia** — não regra, não ADR, não julgamento
prévio meu. **Rejeitar é decisão do usuário.**

Se algo colide com um ADR, eu **informo e sigo explorando**. Nunca descarto por conta própria.

A ordem é **explorar → dar forma → só então checar restrição**. Inverter é como a exploração
morre. Se uma restrição morder, a resposta nunca é "não", é uma das quatro:

1. a versão que satisfaz a restrição — quase sempre existe, porque a restrição costuma ser de
   forma e não de conteúdo;
2. **"colide com a pétrea N, e o número é este"** — com o número;
3. **exceção com escopo**: um ADR pode estar certo em geral e errado para um componente. A
   exceção nomeia o componente, argumenta **por mecanismo e não por resultado**, e é commitada
   antes da medição que a favorece. Três exceções ao mesmo ADR obrigam a revisá-lo — duas, no
   caso do ADR 0002;
4. o ADR novo que supersede o que atrapalha.

**Só as cláusulas pétreas da §3 recusam.** E mesmo elas recusam *construir*, jamais *investigar*.

> **Caso resolvido.** Pedido: *"um sensor que preveja até onde o próximo candle pode chegar"*.
> Errado responder *"o ADR 0005 congelou as primitivas"* ou *"falta a tese"*. Certo: é função
> `VOLATILITY` ou `STRUCTURE`; prever alcance é prever dispersão condicional; explorar o que "até
> onde" significa; achar o mecanismo; **e só então** dar a forma que o contrato exige.

### Postura

- **Criativo na busca de edge, cético na validação.** Propor não é opcional — é função.
- **Adversarial com o próprio trabalho.** Resultado favorável vem acompanhado da explicação mais
  plausível de por que pode ser artefato.
- **Nunca complacente, inclusive com o usuário.** Instrução que contradiga medição registrada
  recebe o número de volta. Se ele reafirmar, é decisão dele e se executa por inteiro.
- **Nunca inventar resultado.** Nenhum número sem execução real e logada. "Não foi medido" é
  resposta obrigatória quando for o caso.

---

## 2. Objetivo

Uma **máquina que produz e aposenta sensores continuamente** para XAUUSD M1 no MetaTrader 5.
O produto não é uma EA nem um sensor: edge decai, e o ativo durável é o pipeline.

Três assimetrias que orientam prioridade:

1. **O filtro vale mais que o sinal.** O edge vem de *não operar* quando o sinal não vale nada.
   `REGIME` e `COST` concentram provavelmente a maior parte do ganho.
2. **Muitos sensores medíocres batem um excelente.** Sharpe de fontes independentes soma em
   quadratura: três não correlacionados com Sharpe 1 dão √3 ≈ 1,73, e um solitário com 1,73 é
   muito mais provável de ser sobreajuste.
3. **A pesquisa acontece em Python, não em MQL5.** MQL5 é linguagem de execução. Nenhum sensor é
   escrito em MQL5 antes de a hipótese sobreviver a um teste em `research/`.

---

## 3. Cláusulas pétreas

Restrições, não preferências. Discordância vira ADR e a implementação para.

1. **Fonte única de verdade.** A matemática de um sensor vive em exatamente um `.mqh`. Indicador e
   EA incluem esse arquivo. Nunca reimplementada, nem por performance.
2. **Sensor não executa.** Gerador puro de sinal. Sem decisão de entrada, gestão, filtro de
   sessão, checagem de spread ou chamada de trading.
3. **Determinismo.** Nada auto-adaptativo, de aprendizado online, ou dependente de wall-clock em
   backtest ou produção. Dois backtests idênticos produzem resultados idênticos.
4. **Zero repaint, zero look-ahead.** O valor da barra N é fixado no fechamento de N.
5. **Proibição de recuperação por exposição.** Martingale, grid, averaging down, aumento de lote
   após perda — sob qualquer nome. Estressados por Monte Carlo: ruína quase certa.
6. **Edge antes de composição.** Nada é combinado ou otimizado antes de passar os gates isolado.
7. **O dia é a unidade estatística.** Trades no M1 são autocorrelacionados dentro do dia.
   Significância sempre sobre R agregado por dia.
8. **Custo é premissa.** Todo teste com spread calibrado do broker. Nenhum resultado sem custo é
   reportado, nem como preliminar.
9. **Win rate não é evidência.** Alvo curto com stop largo dá 85% de acerto e esperança negativa.
   Só esperança em R e t-stat diário contam.

---

## 4. Arquitetura

```
Sensores (.mqh)  →  Registry (função → sensor)  →  Execução (EA)
    puro                  binding                  ordens, risco, sessão
```

Um sensor nunca sabe que uma EA existe. Uma EA nunca sabe qual sensor concreto está usando.

```
docs/           decisions/  sensors/  templates/  REFERENCIA-XAUUSD.md (gerado)
research/       lib/  findings/  notebooks/          ← a pesquisa acontece aqui
MQL5/           Include/ARROW/{Core,Sensors,Registry,Execution}
                Indicators/ARROW/  Experts/ARROW/{Harness,Infra,Live}  Scripts/ARROW/
tools/setup/    junctions.ps1, local_paths.ps1 (não versionado)
reports/        saídas de teste, versionadas
data/           NUNCA versionado — dukascopy/ raw/ spread/ broker/ curated/ bars/
```

| Artefato | Padrão |
|---|---|
| Core do sensor | `Include/ARROW/Sensors/SNS_<FUNC>_<Nome>.mqh` |
| Indicador | `Indicators/ARROW/IND_SNS_<FUNC>_<Nome>.mq5` |
| Harness | `Experts/ARROW/Harness/HRN_SNS_<FUNC>_<Nome>.mq5` |
| EA de produção | `Experts/ARROW/Live/EA_<Nome>_v<Maj>.<Min>.mq5` |
| EA que não negocia | `Experts/ARROW/Infra/EA_<Nome>.mq5` |
| Ficha do sensor | `docs/sensors/SNS_<FUNC>_<Nome>.md` |
| Achado | `research/findings/AAAA-MM-DD-<slug>.md` |

Identificadores em inglês; documentação e comentários em português.

---

## 5. Contrato do sensor

Toda EA se liga a uma **função**, nunca a um sensor concreto. Trocar sensor é alterar uma linha no
Registry.

`REGIME` · `DIRECTION` · `MOMENTUM` · `VOLATILITY` · `EXHAUSTION` · `STRUCTURE` · `COST`

Novas funções exigem ADR. Sensores da mesma função são drop-in entre si.

```mql5
struct SensorOut
{
   double   value;        // sinal normalizado, adimensional
   double   confidence;   // [0.0, 1.0]
   bool     valid;        // false durante warm-up
   datetime bar_time;     // barra FECHADA a que o valor se refere
};
```

**Normalização (ADR 0002):** `value` é adimensional e calibrado contra a hipótese nula. Sob
passeio aleatório com a volatilidade do instrumento, `E[value] = 0` e `SD[value] = 1`. Sem escala
comum, sensores da mesma função não são intercambiáveis e limiares não transferem — foi o defeito
do `val` do Squeeze Momentum, em unidades de preço, e da sua razão de compressão, que escalava
com √N.

Todo core documenta no cabeçalho: distribuição sob o nulo, constante de normalização, e como ela
foi obtida.

> **`confidence` não tem semântica definida.** Nenhum código deve escrever nele, ler dele ou
> ramificar sobre ele até isso ser decidido — o primeiro uso vira precedente por acidente.

**Proibido dentro de um sensor:** gate ou threshold que descarte informação (o corte é da camada
de execução); estado dependente de ordem de chamada ou wall-clock; chamada de trading; leitura de
sessão, spread ou conta; `Print` fora do canal padronizado.

---

## 6. Ciclo de vida

1. **Hipótese** → ADR em `docs/decisions/`: qual desequilíbrio se acredita existir, por que
   produziria retorno previsível, e **qual observação o falsificaria**. Fórmula sem mecanismo é
   fórmula procurando emprego.

   **O ADR é commitado antes do commit que introduz o código que o mede.** A ordem é verificável
   no git; medição cujo pré-registro não a precede **não conta**. Duas frases dizendo por que a
   hipótese provavelmente está errada — sem segunda superfície para objetar, a objeção é
   fabricada de propósito.

2. **Teste barato em `research/`** — Python. Se não sobreviver, vira `finding` negativo e para.
3. **Core** `.mqh` com normalização calibrada.
4. **Indicador**, casca visual fina, sem lógica própria.
5. **Harness** — EA mínima: um sensor, stop e alvo em múltiplos de ATR, sem filtro nem sessão.
6. **Baseline aleatório** — executado **antes**, mesmo período, mesma contagem de trades. É a régua.
7. **Gates 0 a 4.**
8. **Veredicto** em `docs/sensors/`, para aprovados e reprovados.
9. **Produção ou arquivo.** Nunca deletar um reprovado.

**Sonda × hipótese.** Sonda é medição exploratória: rápida, sem pré-registro, sem subagente — e
**não vale como evidência**. Hipótese exige o caminho acima. Todo resultado **citado** para
justificar decisão vira hipótese retroativamente, mesmo nascendo sonda.

---

## 7. Gates

Escritos antes de medir. Alterar limiar depois de ver o resultado invalida o teste.

**Gate 0 — sanidade (eliminatório).** Determinismo por hash de dois recálculos · zero repaint ·
sem look-ahead · warm-up declarado com `valid=false` antes dele · compila sem warnings ·
**paridade Python ↔ MQL5** barra a barra dentro de `1e-9` relativo, com contagem de barras e
conjunto de inválidas coincidindo. Comparar P&L não substitui: curva parecida esconde lógica
divergente e não diz onde.

**Gate 1 — conteúdo informacional, sem execução.** IC de Spearman entre `value` e o retorno
futuro no horizonte T · T condicionado à sessão, faixa de 1 a 30 barras M1 · monotonicidade por
decil · block bootstrap com blocos de um dia, ≥1000 reamostragens · **aprovação:** limite inferior
do IC a 95% afastado de zero, no sinal esperado.

> **Como T é escolhido dentro da faixa continua em aberto.** Varrer os 30 e ficar com o melhor é
> teste múltiplo disfarçado de metodologia.

**Gate 2 — execução (harness).** Custos reais por bucket · comparação obrigatória contra o
baseline aleatório · **exige todos:** esperança em R > 0 após custos; t-stat ≥ 2,0 sobre R
agregado por dia; esperança > 0 para long **e** short independentemente; N ≥ 250 dias;
walk-forward com parâmetros fixados in-sample e bloco out-of-sample nunca tocado.

**Gate 3 — contribuição marginal.** O que importa é o que o sensor **acrescenta**: ele deve
elevar o Sharpe do portfólio, não só ter Sharpe positivo isolado. Um com t=2,2 e correlação 0,1
vale mais que um com t=3,0 e correlação 0,8. Correlação acima de 0,7 com sensor existente da mesma
função: escolher um dos dois.

**Gate 4 — forward em demo.** Mínimo 60 dias de negociação em conta demo real. **O gap entre
backtest e forward é medição obrigatória**, não impressão. Gap acima de 30% em R exige
investigação antes de capital real.

**Testes múltiplos.** Todo sensor testado é registrado em `docs/sensors/`, **inclusive
reprovados**. Toda hipótese testada vai para `research/findings/`, **inclusive refutadas**, com
contagem acumulada em `STATE.md`. Máximo de 3 iterações de parâmetro por sensor — a quarta é
p-hacking. Sensor de produção: **t-stat ≥ 3,0**.

**Kill.** Reprovado após 3 iterações é arquivado com o registro. Não volta sem **hipótese nova
escrita** — mecanismo diferente, não parâmetro diferente.

**Re-teste.** Todo sensor em produção é reavaliado trimestralmente contra os Gates 2 e 3 sobre
dados novos. t-stat abaixo de 2,0 em dois trimestres consecutivos = aposentadoria.

---

## 8. Dados — as convenções que causam divergência silenciosa

Camadas: `dukascopy/ → raw/ → curated/ → bars/`, com `spread/ ← broker/`. `raw/` é **imutável**;
toda transformação produz camada nova com código versionado e semente registrada.

- **Bid, nunca mid, nunca ask.** O MT5 plota bid (medido: `SYMBOL_CHART_MODE = Bid`), então
  `iClose()` é bid. Pesquisar em mid cria offset de meio spread entre Python e MQL5, e a paridade
  do Gate 0 quebra sem causa aparente. Spread entra só na camada de custo.
- **UTC em todo lugar**, conversão só na borda de apresentação. Barra rotulada pelo minuto de
  abertura. Servidor = UTC, relógio fixo — **mas a sessão do símbolo desliza com o DST americano**
  (`research/lib/sessions.py`). A máscara já esteve errada três vezes.
- **Existência de barra:** uma barra M1 existe se e somente se ≥1 tick ocorreu no minuto,
  replicando o MT5. Não preencher minutos vazios — preenchimento que o MT5 não faz desloca todos
  os índices seguintes.
- **Feriados excluídos de `curated/`** por calendário **declarado por regra**, nunca inferido do
  dado: feriado e buraco de coleta se parecem, e excluir todo dia magro faria o buraco sumir em
  silêncio (ADR 0006).
- **Cálculo incremental obrigatório.** Feature sem forma incremental de estado limitado em
  `OnCalculate` não vira sensor — vira achado em `research/findings/` e para aí. Quantil sobre
  histórico inteiro, ranking global e `expanding()` são triviais em pandas e impossíveis ou
  look-ahead em MQL5.
- **`bars/`:** as sete primitivas que não dependem de spread saem de `raw/` direto; `spread_p50` e
  `spread_p95` ficam nulas até `spread/` existir (ADR 0005, emendado pelo 0010). O Gate 1 é "sem
  execução" e nunca exigiu spread.

**O que NÃO transplanta da Dukascopy:** o spread (ECN bruto contra Standard com markup —
descartado integralmente) e a execução (só o Gate 4 mede). O caminho de preço transplanta.

**Logging — schema fixo, contrato entre MQL5 e Python:**

```
trades.csv   trade_id, run_id, sensor_set, open_time_utc, close_time_utc, direction,
             entry_price, exit_price, sl_price, tp_price, atr_at_entry,
             spread_entry_points, commission, slippage_points,
             r_realized, mae_r, mfe_r, bars_held, exit_reason, session, sensor_values_json
signals.csv  bar_time_utc, sensor_name, value, confidence, valid,
             decision, reject_reason, spread_points, atr, equity
run_meta.json  run_id, símbolo, período, modelo do tester, dataset, commit hash, todos os inputs
```

`reject_reason` é obrigatório e específico: `SPREAD_ABOVE_CAP: spread=47 cap=30`, não "filtro
bloqueou". Diagnosticar por que uma EA não operou é leitura de CSV, nunca reexecução com prints.

---

## 9. Armadilhas do MQL5

- `BarsCalculated()` antes de `CopyBuffer()` — sem isso, desalinhamento silencioso
- Buffers de setas não limpos em ticks incrementais — setas fantasma
- **3 dígitos: 1 point = $0,001.** Filtros de spread em pontos são contraintuitivos. Logar unidade
- Filtro de spread nunca acima do stop de emergência na ordem de avaliação — durante spikes
  bloqueia justamente o stop que precisava disparar
- Contract size do ouro é 100 oz, não 100.000 — a matemática de lote difere de FX
- `OnCalculate` com `prev_calculated` incorreto em recálculo de histórico
- **Um Script por gráfico**: o segundo desaloja o primeiro. Coleta contínua é EA, não Script
- MQL5 só escreve em `<terminal>\MQL5\Files\`. A junction `Files\ARROW → data` é a ponte

---

## 10. Como trabalhar

**Ambiente único.** Debate, desenho experimental, matemática, implementação, análise e git
acontecem aqui.

**Subagentes verificam.** Existem porque quem propõe e valida a própria hipótese tem interesse na
sobrevivência dela. Três mandatos, fixos aqui e não compostos caso a caso:

| Papel | Mandato |
|---|---|
| Implementador independente | Implementa a medição **a partir do pré-registro, sem ver minha implementação**. Dois caminhos que concordam produzem número real; se divergem, a divergência é o achado |
| Refutador | Tenta matar a hipótese. Assume refutado em caso de dúvida |
| Auditor de convenção | Confere máscara, feriados, bid-não-mid, blocos de um dia |

Revisar meu código não é mandato de verificação — quem lê o que escrevi herda meus erros. O
veredito é commitado antes de eu revisar qualquer coisa; senão eu itero até concordarem.

**Regras:** ADR antes de mudança estrutural e antes de hipótese · edições cirúrgicas · compilar e
ler o log antes de dizer que terminou · nunca reabrir pétrea · nunca reportar número que não saiu
de execução real · commits pequenos, mensagem dizendo o porquê.

**Sessão.** `STATE.md` é a primeira leitura e vence sobre memória de conversa. Trabalho em branch
`session/AAAA-MM-DD-<slug>`, merge em `main`, push. **A mensagem de commit é o registro da
sessão** — não há relatório separado. Nunca encerrar com alteração não commitada.

**Precedência:** ADR vence sobre prosa · o que não está em ADR é sugestão, não decisão ·
`STATE.md` vence sobre memória · **medição vence sobre os três**, e a derrubada vira ADR novo.

---

## 11. Fora de escopo

Martingale, grid ou recuperação por exposição · otimização antes do Gate 2 · componentes
auto-adaptativos em produção · sensor em MQL5 antes de sobreviver em `research/` · outros
instrumentos, contas ou corretoras além de `XAUUSDm` Standard, até existir catálogo validado
(ADR 0007) · outros timeframes além de M1 · refatoração estética · painéis e dashboards.

## 12. Estado

Em `STATE.md`. Números medidos em `docs/REFERENCIA-XAUUSD.md`.
