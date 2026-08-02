# STATE — ARROW

> Arquivo de estado vivo. **Primeira coisa lida em toda sessão, em qualquer superfície.**
> Escrito exclusivamente pelo Claude Code. O chat propõe deltas; nunca edita este arquivo.
> Se este arquivo contradiz sua memória de contexto, **este arquivo vence**.

---

## Sessão

| Campo | Valor |
|---|---|
| Status | `FECHADA` |
| Máquina | PC-Home |
| Branch | `main` — sessão mergeada e pushada |
| Aberta em | 2026-08-02 |
| Última atualização | 2026-08-02 |
| Última sessão | `logger-simbolo` |

> **Se Status = ABERTA numa máquina diferente da atual:** não iniciar trabalho. Avisar o usuário,
> mostrar máquina e horário, e perguntar se a sessão foi abandonada. Sessão abandonada é fechada
> manualmente com um commit próprio antes de qualquer outra coisa.

---

## Em andamento

Nada em execução. O download da Dukascopy terminou e `raw/` está completa.

**Nada está coletando tick do broker** — ver "Ação que depende do usuário" logo abaixo. É o único
gargalo da camada de dados, e é o único item cujo custo cresce a cada hora parada.

## Ação que depende do usuário — urgente

**`BrokerTickLogger.mq5` compila limpo e ainda não está coletando XAUUSDm.**

Foi executado em 2026-08-02 08:23 UTC e a execução expôs dois defeitos, ambos corrigidos —
**o script precisa ser rodado de novo, na versão nova.** Ver "O que aconteceu na primeira
execução" abaixo.

**Se ele não aparecer no Navegador:** o terminal enumera `MQL5\Scripts` na inicialização, e a
junction `Scripts\ARROW` foi criada em 2026-08-02 07:25 com o terminal já rodando desde 28/07.
**Reiniciar o MT5** resolve. Os arquivos estão no disco — conferido pelo caminho do terminal.

Para colocar em produção, no MT5 de PC-Home:

1. Abrir um gráfico de **`XAUUSDm`** (qualquer timeframe — o script lê tick, não barra)
2. Navegador → Scripts → ARROW → arrastar `BrokerTickLogger` para o gráfico
3. Deixar `InpBackfill = false` na primeira execução; ligar depois, se quiser puxar o histórico
   ainda retido, sabendo que ele atravessa fronteira de DST em potencial
4. **Não remover do gráfico.** Confirmar que `data/broker/xauusdm-AAAAMMDD.csv` aparece e cresce

Enquanto isso não acontecer, `spread/`, `curated/` e `bars/` seguem impossíveis, e **cada dia é
perdido para sempre** — a janela de retenção do broker rola.

### O que aconteceu na primeira execução

**Coletou `BTCUSDm`.** O script foi solto num gráfico de BTCUSDm e `InpSymbol` herdava o símbolo
do gráfico. Gravou `data/broker/BTCUSDm-20260802.csv` — 4.863 linhas. A §14 exclui outros
instrumentos, e a ADR 0005 define `data/broker/` como ticks do `XAUUSDm`; esse arquivo
**contamina a camada** e envenenaria o modelo de spread sem levantar erro.

> **Pendente de decisão do usuário:** apagar `data/broker/BTCUSDm-20260802.csv`. Não apago dado
> sem autorização. Enquanto ele existir, `spread_model.py` não pode varrer `broker/*.csv` cegamente.

`InpSymbol` agora tem padrão `XAUUSDm` e não herda do gráfico; qualquer outro símbolo emite aviso
explícito no log.

**Um tick de XAUUSDm gravado, e correto.** `XAUUSDm-20260731.csv` tem uma linha:
`2026-07-31 20:57:59.775`. Domingo o ouro só abre 22:00, então esse é o último tick de sexta,
imediatamente antes da parada diária das 20:58 — confirmação independente da spec de sessão da
§10.6.

**Bug de retomada no fim de semana, corrigido.** A retomada procurava o arquivo pela data de
*parede*; os arquivos são nomeados pela data do *tick*. Com mercado aberto coincidem; fechado,
divergem — e a evidência está na listagem, com o arquivo em `20260731` contra a data de parede
`20260802`. Cada restart de fim de semana duplicaria uma linha em silêncio. Agora a retomada
busca o arquivo mais recente do símbolo, independente do estado do mercado.

### Primeira medição real do offset do servidor

`data/broker/_offset_log.csv` registra **`offset_seconds = 0`** em 2026-08-02 08:23 UTC:
**o servidor opera em UTC.** É a primeira evidência medida a favor da hipótese da §10.7, e vem de
**uma estação só** (agosto, verão do norte). Não fecha a questão: o teste das duas estações segue
pendente, e é justamente ele que distingue um servidor UTC fixo de um que desloca com o DST.

## Bloqueado

| Item | Bloqueado por |
|---|---|
| Gate 1 | Escolha de T dentro da faixa de 1 a 30 barras não tem critério — ver nota abaixo |
| Primeiro sensor | Tese mecânica não escrita (CLAUDE.md §18 passo 3) |
| Primeiro sensor | Semântica de `confidence` no `SensorOut` não definida (CLAUDE.md §5.2) |
| Modelo de spread, `curated/`, `bars/` | `BrokerTickLogger` existe e compila, mas não está rodando — sem `broker/` não há modelo |
| Qualquer conclusão de Gate 2 | Capital inicial e drawdown tolerado não definidos (CLAUDE.md §13) |
| Substituição das estimativas de σ | auditoria Python sobre `raw/` não construída (CLAUDE.md §18 passo 5) |
| Calibração de normalização de sensor | mesma auditoria |

> **O horizonte T do Gate 1 continua em aberto.** A revisão do `CLAUDE.md` de 2026-08-02 removeu
> a derivação `T_min = (c/kσ)²`, mas **apagar a fórmula não respondeu a pergunta que ela fazia**:
> em que horizonte o IC deve ser medido, dado que o custo é pago na entrada. O que sobrou —
> "1 a 30 barras M1, condicionado à sessão" — é uma faixa de busca, não um critério de escolha.
> Varrer os 30 valores e ficar com o melhor é teste múltiplo disfarçado de metodologia, e a §7
> trata exatamente isso como reprovação.
>
> Isto é decisão pendente, **não requisito eliminado**. Volta do chat como ADR. Enquanto não
> voltar, nenhum Gate 1 é executado.
>
> O ADR 0003 segue válido no que decidiu — `c/(2R)` como métrica de edge exigido. Apenas a última
> consequência que ele lista, que apontava para a fórmula, perdeu o referente no `CLAUDE.md`.

## Próximo passo

Enquanto a tese e a semântica de `confidence` não voltarem do chat, o trabalho segue pelo ADR
0005 e para antes de qualquer sensor.

1. **Colocar o `BrokerTickLogger` em produção** — ver acima. É do usuário, não meu, e agora é o
   único bloqueio da camada de dados.
2. **Auditoria em Python sobre `raw/`** (§18 passo 5) — desbloqueada, e agora sobre os quatro
   anos inteiros: **σ por minuto por bucket de hora**, que substitui as estimativas preliminares
   das §13.1/13.2, mais densidade de tick por sessão. É o insumo mais importante do projeto e não
   depende de `broker/`.
3. `DataAudit.mq5`, depois `spread_model.py`, `curate.py`, `bars.py`, `parity.py` +
   `ParityDump.mq5` (ADR 0005, ordem da §7 do brief). Do `spread_model.py` em diante tudo
   depende de `broker/`.

> **Nunca reprocessar um CSV já convertido.** `write_raw` é append-only: rodar `build_raw.py`
> outra vez sobre um dos quatro CSVs **duplicaria** o dado em `raw/` em vez de sobrescrever. Para
> revalidar, `--validate-only`. Para encadear conversões novas, `--skip-validate` e fechar com
> `--validate-only`.

**Nenhum sensor. Nenhuma feature derivada além das nove primitivas de `bars/`.**

## Estado dos dados

### `data/raw/` — COMPLETA, quatro anos

| | |
|---|---|
| Cobertura | `2022-08-01 00:00:00.143 UTC` → `2026-07-31 20:59:02.882 UTC` |
| Ticks | **240.344.662** |
| Tamanho | 1,4 GB em Parquet zstd, 48 partições mensais, 94 arquivos |
| Defeito estrutural | **nenhum** — 0 retrocesso de `ts`, 0 `ask < bid`, 0 preço ≤ 0, 0 duplicata |
| Dias com dado | 1.245, sendo **1.041 dias úteis** |
| Relatório | `reports/xauusd-2022-08_2026-08-validacao.md` |

**O requisito de amostra da §10.1 está satisfeito pela primeira vez.** 1.041 dias úteis contra o
padrão do projeto de ~1.020 (3 folds + OOS final com folga). Antes disso nem o mínimo absoluto de
2 anos era atingido.

**Toda ausência no dataset tem explicação de calendário; nenhuma sobrou sem causa.**

- 4 dias úteis sem nenhum tick: `2023-04-07`, `2024-03-29`, `2025-04-18`, `2026-04-03` — as
  quatro **Sextas-feiras Santas** do período. O ouro não negocia.
- 8 dias anormalmente magros (1% a 4% da mediana do mesmo dia da semana): todos os **Natais e
  Ano-Novos**, incluindo os observados `2022-12-26` e `2023-01-02`. Sessão encurtada, não buraco.

Os 12 serão **removidos de `curated/`** (ADR 0006). `raw/` os mantém — é imutável. A validação
cruza dia ausente/magro contra o calendário declarado em `research/lib/market_calendar.py` e
marca como anomalia o que sobrar; hoje sobra zero. Perda de amostra: 12 dias em 1.041 (1,2%), o
que deixa 1.029 contra o padrão de ~1.020 da §10.1 — continua satisfeito.

Continuidade entre os quatro segmentos de download conferida: o CSV de 2024 termina em
`1754006399345` e o de 2025 começa em `1754006400000` — 655 ms. Sem buraco nas emendas, o que
importa porque o Gate 2 exige bloco out-of-sample contíguo.

O último tick cai exatamente na borda do intervalo diário do símbolo (20:58). É evidência
independente a favor da hipótese de servidor UTC+0 da §10.7 — **de uma estação só**, portanto não
substitui o teste das duas.

### `data/broker/` — vazio

Nada coletado. Ver "Ação que depende do usuário". **É o único gargalo restante da camada de
dados:** `raw/` está pronta, e `spread/`, `curated/` e `bars/` dependem só de `broker/`.

### Download da Dukascopy — CONCLUÍDO

Os quatro segmentos anuais baixados e convertidos, 11 GB de CSV em `data/dukascopy/`.
Parâmetros `-bs 10 -bp 500` (§10.1). Os CSVs são descartáveis e reconstituíveis; `raw/` não.

## Decisões pendentes de ADR

| Assunto | Onde foi decidido | ADR |
|---|---|---|
| Camada de dados e paridade Python/MQL5 | task brief do chat, 2026-08-02 | **0005 — escrito** |
| Exclusão dos feriados do dataset | chat, 2026-08-02 | **0006 — escrito** |
| Escolha de T dentro da faixa do Gate 1 | não decidido em lugar nenhum | falta debate |
| Semântica de `confidence` | não decidido em lugar nenhum | falta debate |
| Tese mecânica do XAUUSD M1 | não decidido em lugar nenhum | falta debate |
| Capital inicial, drawdown, critério demo→real | não decidido em lugar nenhum | falta debate |

> **`confidence` não deve ser usado por nada até o chat decidir o que ele significa.** O campo
> existe no `SensorOut` e permanece no contrato, mas nenhum código deve escrever nele, ler dele ou
> ramificar sobre ele. O primeiro uso vira definição por acidente, e definição por acidente é o
> que este arquivo existe para impedir.

> **Colisão de numeração, resolvida:** o task brief pedia `0001-camada-de-dados.md`, mas `0001`
> já era o ADR de namespace, escrito no bootstrap antes de o brief existir. Foi para **0005**.
> Numeração de ADR nunca é reaproveitada (`docs/decisions/README.md`).

> As três pendências que este arquivo listava antes do bootstrap — contrato do sensor, custo como
> exigência de edge, repositório público — foram quitadas pelos ADRs 0002, 0003 e 0004.

---

## Últimas sessões

| Data | Máquina | Relatório |
|---|---|---|
| 2026-08-02 | PC-Home | [símbolo e retomada do logger](docs/sessions/2026-08-02-1840-logger-simbolo.md) |
| 2026-08-02 | PC-Home | [exclusão dos feriados](docs/sessions/2026-08-02-1720-feriados.md) |
| 2026-08-02 | PC-Home | [`raw/` dos quatro anos](docs/sessions/2026-08-02-1615-raw-4-anos.md) |
| 2026-08-02 | PC-Home | [camada de dados](docs/sessions/2026-08-02-0730-camada-de-dados.md) |
| 2026-08-02 | PC-Home | [bootstrap](docs/sessions/2026-08-02-0700-bootstrap.md) |
