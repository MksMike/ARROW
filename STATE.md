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
| Branch | `session/2026-08-02-bootstrap` |
| Aberta em | 2026-08-02 |
| Última atualização | 2026-08-02 |

> **Se Status = ABERTA numa máquina diferente da atual:** não iniciar trabalho. Avisar o usuário,
> mostrar máquina e horário, e perguntar se a sessão foi abandonada. Sessão abandonada é fechada
> manualmente com um commit próprio antes de qualquer outra coisa.

---

## Em andamento

Bootstrap do repositório: árvore de diretórios, `.gitignore`, documentos normativos, ADRs
0001–0004 e junctions. Sessão de escopo fechado — não produz nenhum `.mq5`.

## Bloqueado

| Item | Bloqueado por |
|---|---|
| Gate 1 inteiro | `k` de `T_min = (c/kσ)²` nunca foi definido (CLAUDE.md §7, ADR 0003) |
| Primeiro sensor | Tese mecânica não escrita (docs/CONTEXT.md) |
| Primeiro sensor | Semântica de `confidence` no `SensorOut` não definida (ADR 0002) |
| Qualquer conclusão de Gate 2 | Capital inicial e drawdown tolerado não definidos (CLAUDE.md §11) |
| Substituição das estimativas de σ | `DataAudit` ainda não construído |
| Calibração de normalização de sensor | `DataAudit` ainda não construído (ADR 0002) |

## Próximo passo

1. `Scripts/ARROW/DataAudit.mq5` — rodando sobre **XAUUSDm e XAUUSDz**. Produz inventário de
   tick, spec do símbolo, σ por bucket de hora, distribuição de spread por hora × faixa de
   volatilidade, verificação de fuso (`TimeCurrent()` vs `TimeGMT()` em duas estações), tick
   value efetivo em JPY. Saída em CSV + relatório em `reports/`.

   Exige o terminal aberto com gráfico para executar o Script — não é verificável só por linha
   de comando. Sessão própria.

2. `Scripts/ARROW/TickImport.mq5` — a janela de tick real do broker cobre ~6-7 meses contra os
   250 dias que o Gate 2 exige, então a importação é caminho crítico, não contingência.

## Decisões pendentes de ADR

| Assunto | Onde foi decidido | ADR |
|---|---|---|
| Valor e derivação do `k` do Gate 1 | não decidido em lugar nenhum | falta debate |
| Semântica de `confidence` | não decidido em lugar nenhum | falta debate |
| Tese mecânica do XAUUSD M1 | não decidido em lugar nenhum | falta debate |
| Capital inicial, drawdown, critério demo→real | não decidido em lugar nenhum | falta debate |

> As três pendências que este arquivo listava antes do bootstrap — contrato do sensor, custo como
> exigência de edge, repositório público — foram quitadas pelos ADRs 0002, 0003 e 0004.

---

## Últimas sessões

| Data | Máquina | Relatório |
|---|---|---|
| — | — | — |
