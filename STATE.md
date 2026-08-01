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
| Branch | `session/2026-08-02-bootstrap` — **WIP, não mergeada, não pushada** |
| Aberta em | 2026-08-02 |
| Última atualização | 2026-08-02 |

> **Se Status = ABERTA numa máquina diferente da atual:** não iniciar trabalho. Avisar o usuário,
> mostrar máquina e horário, e perguntar se a sessão foi abandonada. Sessão abandonada é fechada
> manualmente com um commit próprio antes de qualquer outra coisa.

---

## Em andamento

Nada em execução. O bootstrap está completo na branch `session/2026-08-02-bootstrap`.

**A branch é WIP e não foi pushada.** Dois motivos, ambos aguardando o usuário:

1. O `CLAUDE.md` foi reescrito a partir do conteúdo de uma conversa, não copiado de um original.
   Ele é a fonte de autoridade do projeto e o repositório é público — precisa de revisão antes
   do push.
2. Merge em `main` depende dessa mesma revisão.

Enquanto isso não acontecer, **nenhuma outra máquina enxerga este trabalho.**

## Bloqueado

| Item | Bloqueado por |
|---|---|
| Primeiro sensor | Tese mecânica não escrita (CLAUDE.md §18 passo 3) |
| Primeiro sensor | Semântica de `confidence` no `SensorOut` não definida (CLAUDE.md §5.2) |
| Modelo de spread, `curated/`, `bars/` | `BrokerTickLogger` não existe — sem `broker/` não há modelo |
| Qualquer conclusão de Gate 2 | Capital inicial e drawdown tolerado não definidos (CLAUDE.md §13) |
| Substituição das estimativas de σ | auditoria Python sobre `raw/` não construída (CLAUDE.md §18 passo 5) |
| Calibração de normalização de sensor | mesma auditoria |

> **Desbloqueado pela revisão do `CLAUDE.md` de 2026-08-02:** o `k` de `T_min = (c/kσ)²` era a
> pendência que travava o Gate 1 inteiro. A revisão **removeu a fórmula** do Gate 1, que agora
> avalia T condicionado à sessão na faixa de 1 a 30 barras M1, sem derivá-lo do custo. A pendência
> deixou de existir por eliminação do requisito, não por resposta. O ADR 0003 continua válido no
> que decidiu — `c/(2R)` como métrica de edge exigido — mas sua última consequência listada está
> obsoleta.

## Próximo passo

A ordem é a da §18 do `CLAUDE.md` revisado, não a anterior.

1. **`.gitignore`** — feito e commitado antes de o download terminar (§18 passo 1).
2. **`Scripts/ARROW/BrokerTickLogger.mq5`** — o item urgente. Cada dia não coletado é verdade de
   campo perdida para sempre, e ele é o único insumo do modelo de spread. Puxar também o
   histórico ainda retido via `CopyTicks` antes que role para fora da janela.
3. **Tese** — duas ou três hipóteses mecânicas falsificáveis, escritas **antes** de olhar dado.
4. `research/lib/` — Dukascopy CSV → Parquet particionado por mês.

O task brief `camada-de-dados` (chat, 2026-08-02) cobre os itens 2 a 7 da §18 e ainda não foi
executado — ver "Decisões pendentes" abaixo quanto à numeração do ADR que ele pede.

## Decisões pendentes de ADR

| Assunto | Onde foi decidido | ADR |
|---|---|---|
| Camada de dados e paridade Python/MQL5 | task brief do chat, 2026-08-02 | **a escrever — ver nota** |
| Semântica de `confidence` | não decidido em lugar nenhum | falta debate |
| Tese mecânica do XAUUSD M1 | não decidido em lugar nenhum | falta debate |
| Capital inicial, drawdown, critério demo→real | não decidido em lugar nenhum | falta debate |

> **Colisão de numeração:** o task brief pede `docs/decisions/0001-camada-de-dados.md`, mas
> `0001` já é o ADR de namespace, escrito no bootstrap antes de o brief existir. O chat não tinha
> como saber. O próximo número livre é **0005**. Numeração de ADR nunca é reaproveitada
> (`docs/decisions/README.md`).

> As três pendências que este arquivo listava antes do bootstrap — contrato do sensor, custo como
> exigência de edge, repositório público — foram quitadas pelos ADRs 0002, 0003 e 0004.

---

## Últimas sessões

| Data | Máquina | Relatório |
|---|---|---|
| 2026-08-02 | PC-Home | [bootstrap](docs/sessions/2026-08-02-0700-bootstrap.md) |
