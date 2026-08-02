# 0008 — O coletor de tick é Expert Advisor, não Script

**Data:** 2026-08-03
**Status:** aceito
**Decidido em:** sessão `logger-ea`, a partir do incidente de 2026-08-02

## Contexto

`data/broker/` é o único insumo do modelo de spread (ADR 0005), e a janela de retenção de tick do
broker é móvel: **cada hora não coletada é verdade de campo perdida para sempre.** É o único item
do projeto cujo custo cresce com o relógio.

O coletor foi implementado como Script MQL5 e **morreu duas vezes em vinte e quatro horas**, por
mecanismos diferentes:

| Quando | Causa |
|---|---|
| 2026-08-02, ~09:47 UTC | Reinício do terminal — Script não sobrevive |
| 2026-08-02, 10:37 UTC | `DataAudit` solto no mesmo gráfico — o MT5 permite **um Script por gráfico**, e o segundo desaloja o primeiro |

O log do terminal registra a segunda com dois segundos entre a morte e o nascimento do intruso:

```
19:37:06  BrokerTickLogger (XAUUSDm,M1)  parado. 0 ticks gravados
19:37:08  DataAudit        (XAUUSDm,M1)  iniciando
```

Havia um terceiro mecanismo esperando: trocar o símbolo ou o timeframe do gráfico também mata um
Script.

Nenhum dado foi perdido — o mercado esteve fechado nas duas ocasiões. **Isso foi sorte, não
projeto.**

## Decisão

O coletor passa a ser **Expert Advisor**, em
`MQL5/Experts/ARROW/Infra/EA_BrokerTickLogger.mq5`. O Script é **removido**.

Um EA não tem nenhum dos três mecanismos de morte:

- **Sobrevive a reinício do terminal** — o MT5 reanexa EAs ao gráfico automaticamente, e `OnInit`
  retoma do último arquivo gravado.
- **Convive com scripts** no mesmo gráfico. O acidente de 2026-08-02 deixa de ser possível.
- **Sobrevive à troca de símbolo ou timeframe** — `REASON_CHARTCHANGE` desinicializa e reinicializa,
  e a retomada pelo arquivo cobre o intervalo.

E resolve um problema que o Script tinha e ninguém tinha nomeado: **um EA aparece no canto do
gráfico.** Hoje não há como saber se a coleta está viva sem abrir o log do terminal.

### O que foi acrescentado além da conversão

**Motivo da parada, traduzido.** A morte anterior foi silenciosa: o Script escreveu "parado" e
ninguém viu. `OnDeinit` agora registra o código traduzido, e distingue parada temporária
(recompilação, troca de parâmetros — reanexa sozinho) de **parada definitiva** (removido do
gráfico, gráfico fechado), que emite aviso explícito de que a coleta não reinicia sozinha.

**Batimento periódico.** A cada 30 minutos, quantos ticks foram gravados e em qual arquivo. Um
coletor vivo tem de ser distinguível de um morto sem abrir o CSV.

**O motor é o timer, não o `OnTick`.** `OnTick` só dispara para o símbolo **do gráfico**, e o
símbolo de coleta não herda do gráfico (ADR 0007 e o incidente do BTCUSDm). Com
`EventSetMillisecondTimer` o EA funciona em qualquer gráfico; `OnTick` fica como acelerador quando
os dois coincidem.

### Diretório novo: `Experts/ARROW/Infra/`

A §4.1 previa `Experts/ARROW/Harness/` — EA de teste por sensor — e `Experts/ARROW/Live/` — EAs
orquestradoras. Um coletor não é nenhum dos dois.

Colocá-lo em `Live/` seria pior que desarrumado: a §4.1 descreve aquele diretório como EAs
orquestradoras, e alguém poderia razoavelmente supor que **tudo ali dentro pode enviar ordem**.
`Infra/` declara o oposto.

### Prova de que não negocia

O arquivo não contém `OrderSend`, `PositionOpen`, `PositionClose`, `PositionModify`, `CTrade`,
`MqlTradeRequest`, `.Buy(` nem `.Sell(`. A ausência é verificável por busca textual, e foi
verificada nesta sessão.

Não é formalidade. Um EA roda continuamente numa conta com alavancagem 1:2000 e sem proteção do
broker (`REFERENCIA-XAUUSD.md` §2). Um coletor que **possa** emitir ordem por acidente é um risco
que não precisa existir, e a ausência das chamadas é mais forte que qualquer flag de configuração.

## Alternativas rejeitadas

**Manter o Script e tomar cuidado.** Rejeitada pelo histórico: duas mortes em 24 horas, e as duas
por operação normal — reiniciar o terminal e rodar uma auditoria. "Tomar cuidado" é pedir que o
operador lembre de uma restrição não escrita em nenhum lugar da interface, indefinidamente.

**Manter os dois, EA e Script.** Rejeitada, e é a alternativa mais perigosa das três: os dois
escrevem no mesmo arquivo do dia. Rodando juntos, ambos apendariam ticks ao mesmo CSV e o
resultado seria duplicação silenciosa — pior que a perda que se quer evitar, porque um arquivo
duplicado parece íntegro.

**Serviço MQL5 (`Services/`) em vez de EA.** Considerada seriamente: um Service não precisa de
gráfico e sobrevive a tudo que um EA sobrevive. Rejeitada por diagnosticabilidade — um Service é
invisível na interface, e a lição do incidente é justamente que a morte silenciosa foi o problema.
O EA aparece no canto do gráfico. Fica registrada como alternativa a reconsiderar se um dia a
coleta precisar rodar sem gráfico aberto.

## Consequências

- `MQL5/Scripts/ARROW/BrokerTickLogger.mq5` é removido. O que ele aprendeu — retomada pelo arquivo
  mais recente, símbolo que não herda do gráfico, offset registrado — está inteiro no EA.
- A instalação passa a ser: arrastar o EA para **um gráfico dedicado**. Continua sendo ação
  humana; o que muda é que ela precisa acontecer **uma vez**, não a cada reinício.
- `Experts/ARROW/Infra/` entra na §4.1 como abrigo de EAs de infraestrutura que não negociam.
- O `DataAudit` continua sendo Script, e correto: ele roda uma vez e termina. A conversão vale
  para o que precisa **permanecer** rodando.
