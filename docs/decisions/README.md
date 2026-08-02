# Índice de ADRs

> Leitura obrigatória na abertura de sessão (`CLAUDE.md` §15.4).
>
> Decisão sem ADR não é decisão, é sugestão (§15.7). Em caso de contradição entre superfícies,
> o que está escrito em ADR vence.

| # | Título | Status | Origem |
|---|---|---|---|
| [0001](0001-namespace-arrow-e-estrutura-de-diretorios.md) | Namespace ARROW e estrutura de diretórios | aceito | Code, bootstrap 2026-08-02 |
| [0002](0002-contrato-do-sensor.md) | Contrato do sensor: `SensorOut` e normalização contra o nulo | aceito | chat 2026-08-02 |
| [0003](0003-custo-como-exigencia-de-edge.md) | Custo como exigência de edge: `c/(2R)` | aceito | chat 2026-08-02 |
| [0004](0004-repositorio-publico-dados-fora-do-repo.md) | Repositório público, dados fora do repositório | aceito | chat 2026-08-02 |
| [0005](0005-camada-de-dados-e-paridade.md) | Camada de dados e paridade Python ↔ MQL5 | aceito | chat 2026-08-02 |
| [0006](0006-feriados-excluidos-do-dataset.md) | Feriados de mercado excluídos do dataset | aceito | chat 2026-08-02 |

## Pendentes de ADR

Decisões que ainda não existem e que bloqueiam trabalho. Cada uma é debate de chat, não escolha
de implementação.

| Assunto | Bloqueia | Onde está registrado |
|---|---|---|
| Escolha de T dentro da faixa de 1 a 30 barras | Gate 1 | `CLAUDE.md` §7, `STATE.md` |
| Semântica de `confidence` no `SensorOut` | Primeiro sensor | ADR 0002, `CLAUDE.md` §5.2 |
| Tese mecânica — o que se acredita explorável no XAUUSD M1 | Primeiro sensor | `CLAUDE.md` §18 passo 3 |
| Capital inicial, drawdown tolerado, critério demo→real | Conclusão de Gate 2 | `CLAUDE.md` §13 |

A revisão do `CLAUDE.md` de 2026-08-02 removeu a fórmula `T_min = (c/kσ)²` do Gate 1, mas **isso
não fechou a pendência** — apagou a derivação sem substituí-la. A pergunta que ela fazia, em que
horizonte medir o IC, segue aberta, e "1 a 30 barras" é faixa de busca, não critério de escolha.
Permanece na lista.

## Convenção

`NNNN-slug-em-portugues.md`, numeração sequencial, nunca reaproveitada. Um ADR aceito não é
editado para mudar de ideia — escreve-se um novo que o supersede, e o antigo passa a
`Status: superseded por NNNN`.
