# STATE — ARROW

> Arquivo de estado vivo. **Primeira coisa lida em toda sessão, em qualquer superfície.**
> Escrito exclusivamente pelo Claude Code. O chat propõe deltas; nunca edita este arquivo.
> Se este arquivo contradiz sua memória de contexto, **este arquivo vence**.

---

## Sessão

| Campo | Valor |
|---|---|
| Status | `ABERTA` |
| Máquina | PC-Home |
| Branch | `session/2026-08-02-camada-de-dados` |
| Aberta em | 2026-08-02 |
| Última atualização | 2026-08-02 |

> **Se Status = ABERTA numa máquina diferente da atual:** não iniciar trabalho. Avisar o usuário,
> mostrar máquina e horário, e perguntar se a sessão foi abandonada. Sessão abandonada é fechada
> manualmente com um commit próprio antes de qualquer outra coisa.

---

## Em andamento

Camada de dados, conforme ADR 0005. Itens 1 e 2 do brief: `BrokerTickLogger.mq5` e
`loader.py` + `validate.py`.

O bootstrap foi mergeado em `main` e pushado — o repositório remoto deixou de estar vazio.

## Bloqueado

| Item | Bloqueado por |
|---|---|
| Gate 1 | Escolha de T dentro da faixa de 1 a 30 barras não tem critério — ver nota abaixo |
| Primeiro sensor | Tese mecânica não escrita (CLAUDE.md §18 passo 3) |
| Primeiro sensor | Semântica de `confidence` no `SensorOut` não definida (CLAUDE.md §5.2) |
| Modelo de spread, `curated/`, `bars/` | `BrokerTickLogger` não existe — sem `broker/` não há modelo |
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

1. **`Scripts/ARROW/BrokerTickLogger.mq5` em produção contínua** — precisa estar anexado a um
   gráfico de `XAUUSDm` no MT5 e **permanecer rodando**. Cada dia não coletado é verdade de campo
   perdida para sempre, e `broker/` é o único insumo do modelo de spread.
2. **`research/lib/loader.py` + `validate.py`** — Dukascopy CSV → Parquet particionado por mês,
   com relatório de gaps e gráfico de ticks/dia em `reports/`.

Depois disso, e não antes: `DataAudit.mq5`, `spread_model.py`, `curate.py`, `bars.py`,
`parity.py` + `ParityDump.mq5` (ADR 0005, ordem da §7 do brief).

**Nenhum sensor. Nenhuma feature derivada além das nove primitivas de `bars/`.**

## Download da Dukascopy

Uma corrida única em andamento, cobrindo 2022-08 a 2026-08 em segmentos anuais encadeados, na
ordem **2025 → 2024 → 2023 → 2022** — o ano mais recente primeiro, para liberar `loader.py` e a
auditoria antes de o resto chegar. Parâmetros `-bs 10 -bp 500` (§10.1).

A corrida anterior, com `-bs 1 -bp 2000`, foi **morta**. O CSV
`data/dukascopy/xauusd-tick-2022-08-01-2023-08-01.csv` que ela deixou é resto daquela tentativa,
não entrega da corrida atual.

## Decisões pendentes de ADR

| Assunto | Onde foi decidido | ADR |
|---|---|---|
| Camada de dados e paridade Python/MQL5 | task brief do chat, 2026-08-02 | **0005 — escrito** |
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
| 2026-08-02 | PC-Home | [bootstrap](docs/sessions/2026-08-02-0700-bootstrap.md) |
