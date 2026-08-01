# 0001 — Namespace ARROW e estrutura de diretórios

**Data:** 2026-08-02
**Status:** aceito
**Decidido em:** sessão de bootstrap, Claude Code, PC-Home

## Contexto

Os documentos herdados (`CLAUDE.md`, `STATE.md`) chegaram ao repositório ARROW ainda intitulados
"MKS-Engine", e todo o namespace de código que eles especificam era `MKS`: `Include/MKS/`,
`Indicators/MKS/`, `Experts/MKS/`, `Scripts/MKS/`, as quatro junctions correspondentes, e o
símbolo customizado `XAUUSD.MKS`.

Isso contradiz o próprio `docs/CONTEXT.md`, que registra que do projeto anterior atravessaram os
princípios e os aprendizados, **não o código**. Além disso, o terminal MT5 desta máquina já tem
junctions ativas para `MKS-Engine` e `MKS-ULTIMATE` dentro de `MQL5\Include\`. Manter o namespace
`MKS` colocaria uma terceira árvore homônima ao lado de duas linhagens abandonadas, com risco
concreto de `#include` resolver para o projeto errado.

## Decisão

Todo o namespace passa a ser `ARROW`:

- `MQL5/Include/ARROW/`, `MQL5/Indicators/ARROW/`, `MQL5/Experts/ARROW/`, `MQL5/Scripts/ARROW/`
- Símbolo customizado `XAUUSD.ARROW` no grupo `Custom\ARROW`
- Títulos de `CLAUDE.md` e `STATE.md` corrigidos para ARROW

Os prefixos de arquivo da Seção 4.2 (`SNS_`, `IND_SNS_`, `HRN_SNS_`, `EA_`) já eram neutros e
permanecem inalterados.

A árvore da Seção 4.1 recebe três entradas que o protocolo da Seção 15 exigia mas que a árvore
não listava:

- `docs/sessions/` — exigido por §15.8, ausente da árvore
- `docs/templates/` — os dois templates do protocolo não tinham lugar declarado
- `docs/CONTEXT.md` — o documento de conhecimento não tinha lugar declarado

## Alternativas rejeitadas

**Manter `MKS` como namespace de código e mudar só os títulos.** Rejeitada por duas razões. A
primeira é a colisão real de junctions descrita acima — não é preocupação estética. A segunda é
que conviver com duas identidades é exatamente a classe de ambiguidade não escrita que motivou a
criação do ARROW; o custo de resolver isso cresce com cada arquivo criado, e é mínimo agora, com
a árvore vazia.

**Namespace `ARROW` nos diretórios mas `XAUUSD.MKS` no símbolo.** Rejeitada: o símbolo
customizado é referenciado por nome em todo backtest e em `run_meta.json`. Uma divergência ali
sobrevive a todo o histórico de resultados.

## Consequências

- As junctions do MT5 apontam para `ARROW`; as junctions existentes de `MKS-Engine` e
  `MKS-ULTIMATE` não são tocadas.
- Nenhum código precisou ser migrado — a decisão foi tomada com a árvore ainda vazia, que é o
  único momento em que ela é gratuita.
