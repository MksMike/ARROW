# STATE — ARROW

> Arquivo de estado vivo. **Primeira coisa lida em toda sessão.**
> Escrito exclusivamente pelo Claude Code.
> Se este arquivo contradiz sua memória de contexto, **este arquivo vence**.

---

## Sessão

| Campo | Valor |
|---|---|
| Status | `FECHADA` |
| Máquina | PC-Home |
| Branch | `main` — sessao mergeada e pushada |
| Aberta em | 2026-08-02 |
| Última atualização | 2026-08-03 |
| Última sessão | `ambiente-unico` |

> **Se Status = ABERTA numa máquina diferente da atual:** não iniciar trabalho. Avisar o usuário,
> mostrar máquina e horário, e perguntar se a sessão foi abandonada. Sessão abandonada é fechada
> manualmente com um commit próprio antes de qualquer outra coisa.

---

## Em andamento

Nada em execução no repositório.

**`BrokerTickLogger` está armado em `XAUUSDm` desde 2026-08-02 09:48 UTC** e aguardando a
abertura do mercado — domingo 22:05 UTC. O gargalo da camada de dados deixou de ser a instalação
e passou a ser o tempo: `spread/` precisa de amostra acumulada.

## Coleta de tick do broker — AÇÃO NECESSÁRIA, UMA VEZ SÓ

O coletor virou **Expert Advisor** (ADR 0008). Ele morreu duas vezes em 24 h como Script — uma por
reinício do terminal, outra por colisão com o `DataAudit` no mesmo gráfico. Um EA não tem nenhum
dos dois problemas.

**Instalar, uma vez:**

1. Navegador → **Assessores Especialistas** → ARROW → Infra → `EA_BrokerTickLogger`
2. Arrastar para **um gráfico dedicado** — qualquer símbolo serve, o EA não herda do gráfico
3. Confirmar no log: `ARROW EA_BrokerTickLogger v1.00: XAUUSDm, digits=3, offset servidor-UTC = 0 s`
4. Confirmar que a **carinha aparece no canto do gráfico** — é como se sabe que está vivo

A partir daí ele reanexa sozinho a cada reinício do terminal, convive com scripts, e sobrevive à
troca de símbolo ou timeframe do gráfico. Emite batimento no log a cada 30 min e, se parar,
**registra o motivo traduzido** — a morte anterior foi silenciosa e isso foi o pior dela.

> **O EA não negocia.** Verificado por busca textual: não contém `OrderSend`, `PositionOpen`,
> `PositionClose`, `PositionModify`, `CTrade` nem `MqlTradeRequest`. Numa conta com alavancagem
> 1:2000 e sem proteção do broker, a ausência das chamadas vale mais que qualquer flag.

O Script `Scripts/ARROW/BrokerTickLogger.mq5` foi **removido**. Manter os dois seria pior que
manter o Script: os dois escrevem no mesmo arquivo do dia, e rodando juntos duplicariam ticks em
silêncio.

## Histórico: coleta armada em 2026-08-02## Histórico: coleta armada em 2026-08-02

**`BrokerTickLogger.mq5` está rodando em `XAUUSDm` desde 2026-08-02 09:48 UTC**, na versão
corrigida. Aguarda a abertura de domingo 22:05 UTC (07:05 JST de segunda) para gravar o primeiro
tick de sessão.

**Conferir na manhã seguinte:** `data/broker/XAUUSDm-20260803.csv` deve existir e crescer. O
arquivo de 2026-08-02 nasce primeiro e vira à meia-noite UTC — os dois são normais, porque o nome
segue a data UTC do tick e não a local.

Se não aparecer, o script caiu ou foi removido do gráfico; o log do Especialistas diz o motivo.

**A correção da retomada foi exercitada.** O restart de 09:48 aconteceu com o mercado fechado e o
último arquivo datado de sexta — exatamente o cenário do bug. `XAUUSDm-20260731.csv` continua com
**uma** linha de dado, não duas. O caminho de retomada com mercado **aberto** segue não testado.

### Histórico: o que a primeira execução expôs

**Se ele não aparecer no Navegador:** o terminal enumera `MQL5\Scripts` na inicialização, e a
junction `Scripts\ARROW` foi criada em 2026-08-02 07:25 com o terminal já rodando desde 28/07.
**Reiniciar o MT5** resolve. Os arquivos estão no disco — conferido pelo caminho do terminal.

Para reinstalar, se o script cair: Navegador → Scripts → ARROW → arrastar
`BrokerTickLogger` para qualquer gráfico. O símbolo não depende do gráfico. Deixar
`InpBackfill = false`; ligar apenas com consciência de que o backfill atravessa fronteira de DST
em potencial. **Não remover do gráfico** — cada dia não coletado é perdido para sempre.

### O que aconteceu na primeira execução

**Coletou `BTCUSDm`.** O script foi solto num gráfico de BTCUSDm e `InpSymbol` herdava o símbolo
do gráfico. Gravou `data/broker/BTCUSDm-20260802.csv` — 4.863 linhas. A §14 exclui outros
instrumentos, e a ADR 0005 define `data/broker/` como ticks do `XAUUSDm`; esse arquivo
**contamina a camada** e envenenaria o modelo de spread sem levantar erro.

> **Resolvido (ADR 0007):** o arquivo saiu de `data/broker/` e foi para `data/_fora-de-escopo/`.
> Não foi apagado — é dado real e guardar não custa nada —, mas não podia ficar onde
> `spread_model.py` vai varrer.

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
| Modelo de spread, `curated/`, `bars/` | `broker/` sem amostra — coleta armada em 2026-08-02, primeiro tick de sessão só em 22:05 UTC |
| Qualquer conclusão de Gate 2 | Capital inicial e drawdown tolerado não definidos (CLAUDE.md §13) |
| Calibração de normalização de sensor | precisa de gerador de passeio aleatório calibrado com a σ medida (ADR 0002) |

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

1. **Conferir que a coleta pegou a abertura** (ver acima). Depois disso, só o tempo separa
   `broker/` de ter amostra para `spread_model.py`.
2. ~~Auditoria de σ sobre `raw/`~~ — **feita**, ver "Medições feitas" abaixo. Falta a
   **densidade de tick por sessão**, que é o resto do passo 5 da §18.
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

### Medições feitas

> **Tudo que foi medido vive em [`docs/REFERENCIA-XAUUSD.md`](docs/REFERENCIA-XAUUSD.md)**, que é
> **gerado** por `research/build_reference.py` e não deve ser editado à mão. O `CLAUDE.md` deixou
> de conter número medido e aponta para lá. Esta seção guarda só o que mudou de estado.

**Dependência em escala de tick e densidade.** Autocovariância dos retornos de tick por lag,
curva de assinatura, gap de fronteira, bids repetidos, densidade por hora e sessão.
`reports/dependencia-tick.md`, `research/findings/2026-08-03-dependencia-escala-tick.md`.

- **A dependência NÃO está confinada ao lag 1.** Em 2026 o lag 1 é o menos significativo dos
  cinco primeiros (|t| = 1,5, indistinguível de zero); o pico está no lag 3 (|t| = 5,6).
- **E não é propriedade estável.** `γ₁/γ₀` troca de sinal três vezes em cinco anos — −0,027 /
  +0,069 / +0,004 / −0,081 / −0,009 — e varia uma ordem de grandeza.
- **O `ρ₁ = +0,0124` do piloto de 2026-06 não sobrevive ao ano inteiro**, que dá −0,0088. O
  piloto não estava errado: estava medindo um mês.
- **`rv` do ADR 0005 NÃO está inflado por ruído de cotação.** A dependência líquida é de ordem
  10⁻² relativa a γ₀ — pequena demais para o mecanismo `s² + 2n·η²`. Hipótese levantada no chat
  e falsificada por margem larga.
- **20,9% dos retornos de tick são exatamente zero.** O ADR 0005 define `tick_imb` como *repete o
  sinal anterior se igual* — em um quinto dos ticks o sinal é copiado, o que é injeção mecânica
  de autocorrelação numa primitiva que `bars/` vai congelar.
- **Densidade por sessão medida** (fecha a lacuna da seção 8): asiática com mediana de 106 ticks
  contra 277 da sobreposição, e **58% das barras asiáticas abaixo de 128 ticks**. A variância por
  tick da asiática é a maior de todas — ela move mais por tick, com metade dos ticks.

**Fuso — §10.7 FECHADA.** Servidor = UTC, relógio fixo. A parada diária desliza exatamente uma
hora entre julho (`20:58`) e janeiro (`21:58`), sem exceção em 31 dias. `reports/broker-audit.md`.

> **Mas a sessão configurada do símbolo desliza com o DST americano**, e a primeira versão da
> máscara em `research/lib/sessions.py` cravava 20:58 o ano inteiro — descartando 1,36 milhão de
> ticks de negociação real no inverno. Corrigido e reprocessado. **O achado de σ sobreviveu
> intacto**: a razão asiático/sobreposição ficou idêntica em todos os cinco anos, porque as horas
> 0–15 não chegam perto da parada. Só Nova York mexeu, +0,0013.

**Spec do símbolo confirmada** — dígitos, point, contract size, stops, volumes, swap e rollover
batem com o servidor. Três adições: `SYMBOL_CHART_MODE = Bid` (a premissa da §10.3 virou fato),
tick value ¥15,7427 por dois caminhos independentes, e **histórico M1 do broker desde 2014-01-14
com 3.265.408 barras** — a retenção curta é de tick, não de barra.

**σ por sessão e por hora** — `reports/sigma-auditoria.md`, sobre 1.380.142 barras M1. A §13.2
deixou de conter estimativa e passou a conter medição.

**A premissa de que a sessão asiática é ~3× mais exigente foi refutada.** A razão
σ_asiático/σ_sobreposição subiu monotonicamente por cinco anos — 0,42 → 0,43 → 0,52 → 0,71 →
**0,75** — contra os ~0,23 que a afirmação exigia. Em 2026 a hora 1 UTC (abertura da Shanghai
Gold Exchange) é a segunda hora mais volátil do dia. Registrado em
`research/findings/2026-08-02-sigma-por-sessao.md`.

**σ em dólares triplicou em dois anos** (0,586 → 2,594), mas em bps do preço subiu bem menos
(2,46 → 5,64): a maior parte é nível de preço, não regime. **Toda tabela em dólares precisa ser
remedida quando o ouro mudar de patamar.**

**Ressalva registrada:** σ de fechamento a fechamento no M1 está inflada por bid-ask bounce, então
os tempos `T = (R/σ)²` da §13.2 são o melhor caso, não a expectativa.

### Download da Dukascopy — CONCLUÍDO

Os quatro segmentos anuais baixados e convertidos, 11 GB de CSV em `data/dukascopy/`.
Parâmetros `-bs 10 -bp 500` (§10.1). Os CSVs são descartáveis e reconstituíveis; `raw/` não.

## Decisões pendentes de ADR

| Assunto | Onde foi decidido | ADR |
|---|---|---|
| ~~Ambiente único~~ | usuário, 2026-08-03 | **0009 — escrito** |
| Camada de dados e paridade Python/MQL5 | task brief do chat, 2026-08-02 | **0005 — escrito** |
| Foco único em XAUUSDm | chat, 2026-08-02 | **0007 — escrito** |
| Exclusão dos feriados do dataset | chat, 2026-08-02 | **0006 — escrito** |
| Definição de `tick_imb` no ADR 0005 | medição feita — 20,9% dos ticks copiam o sinal | falta debate |
| ~~`BrokerTickLogger`: Script ou EA~~ | incidente de 2026-08-02 | **0008 — escrito** |
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

## Hipóteses testadas

Contagem acumulada, exigida pelo ADR 0009 §3. É insumo da correção para testes múltiplos (§7),
não estatística decorativa. Toda hipótese entra aqui, **inclusive as refutadas**.

| # | Hipótese | Veredicto | Registro |
|---|---|---|---|
| 1 | `rv` do ADR 0005 estaria dominado por ruído de cotação | **refutada** | `research/findings/2026-08-03-dependencia-escala-tick.md` |
| 2 | A dependência de tick estaria confinada ao lag 1 | **refutada** | idem |

**Total: 2 testadas, 2 refutadas, 0 sobreviventes.**

## Pendência de documentação

A seção 7 do `REFERENCIA-XAUUSD.md`, ressalva 2, atribui ao bid-ask bounce uma inflação de σ que a
aritmética não sustenta: para σ inflar 5% seria preciso η ≈ 0,56/oz, quase três vezes o piso de
spread. E afirma que corrigir isso exige `data/bars/`, quando sai de `raw/` direto. As duas
afirmações estão refutadas por medição. `reference_parts.py` precisa de revisão de narrativa —
**sessão própria**, porque o documento é gerado.

## Últimas sessões

| Data | Máquina | Relatório |
|---|---|---|
| 2026-08-03 | PC-Home | [ambiente único](docs/sessions/2026-08-03-0430-ambiente-unico.md) |
| 2026-08-03 | PC-Home | [coletor vira EA](docs/sessions/2026-08-03-0330-logger-ea.md) |
| 2026-08-03 | PC-Home | [dependência em escala de tick](docs/sessions/2026-08-03-0100-dependencia-tick.md) |
| 2026-08-02 | PC-Home | [documento de referência](docs/sessions/2026-08-02-2030-referencia.md) |
| 2026-08-02 | PC-Home | [foco único em XAUUSDm](docs/sessions/2026-08-02-2000-foco-xauusd.md) |
| 2026-08-02 | PC-Home | [DataAudit e fechamento da §10.7](docs/sessions/2026-08-02-1930-dataaudit.md) |
| 2026-08-02 | PC-Home | [auditoria de σ](docs/sessions/2026-08-02-1900-sigma.md) |
| 2026-08-02 | PC-Home | [símbolo e retomada do logger](docs/sessions/2026-08-02-1840-logger-simbolo.md) |
| 2026-08-02 | PC-Home | [exclusão dos feriados](docs/sessions/2026-08-02-1720-feriados.md) |
| 2026-08-02 | PC-Home | [`raw/` dos quatro anos](docs/sessions/2026-08-02-1615-raw-4-anos.md) |
| 2026-08-02 | PC-Home | [camada de dados](docs/sessions/2026-08-02-0730-camada-de-dados.md) |
| 2026-08-02 | PC-Home | [bootstrap](docs/sessions/2026-08-02-0700-bootstrap.md) |
