# STATE — ARROW

> Primeira leitura de toda sessão. Vence sobre memória de conversa.
> Escrito só pelo Claude Code. Números medidos: `docs/REFERENCIA-XAUUSD.md`.

| | |
|---|---|
| Status | `FECHADA` |
| Máquina | PC-Home |
| Branch | `main` |
| Atualizado | 2026-08-03 |

---

## Ação do usuário — em aberto

Nenhuma. O `EA_BrokerTickLogger` está rodando em `XAUUSDm` desde 2026-08-03 03:49 UTC e coleta
sozinho. Sobrevive a reinício do terminal e convive com scripts; só para se for removido do
gráfico ou o gráfico for fechado, e nesse caso escreve o motivo no log.

---

## Bloqueado

| Item | Por quê |
|---|---|
| Gate 1 | Escolha de T dentro da faixa de 1 a 30 barras não tem critério |
| Primeiro sensor | Semântica de `confidence` não definida — nenhum código deve usar o campo |
| `spread/`, `curated/`, colunas de spread em `bars/` | `data/broker/` acumulando desde 2026-08-03; precisa de N≥500 por bucket |
| Conclusão de Gate 2 | Capital inicial e drawdown tolerado não definidos |

**Nada mais está bloqueado.** As sete primitivas de `bars/` que não dependem de spread saem de
`raw/` direto (ADR 0005 emendado pelo 0010), então o caminho até o Gate 1 não espera o broker.

---

## Estado dos dados

**`data/raw/` — completa.** 240.344.662 ticks, `2022-08-01` → `2026-07-31`, 1,4 GB em Parquet
zstd, 48 partições mensais. Zero defeito estrutural. 1.041 dias úteis — o requisito de amostra
(~1.020) está satisfeito. Toda ausência tem causa de calendário: 4 Sextas-feiras Santas ausentes
e 8 meio-feriados de Natal/Ano-Novo.

**`data/broker/` — acumulando** desde 2026-08-03. Único insumo do modelo de spread.

**`data/dukascopy/` — 11 GB**, descartável e reconstituível.

Medições feitas, todas em `docs/REFERENCIA-XAUUSD.md`: spec do símbolo, fuso (servidor = UTC,
relógio fixo), σ por sessão/hora/ano, densidade de tick, custo e calibração.

---

## Hipóteses testadas

Contagem acumulada — insumo da correção para testes múltiplos (§7), não estatística decorativa.

| # | Hipótese | Veredicto | Registro |
|---|---|---|---|
| 1 | `rv` do ADR 0005 estaria dominado por ruído de cotação | **refutada** | `research/findings/2026-08-03-dependencia-escala-tick.md` |
| 2 | A dependência de tick estaria confinada ao lag 1 | **refutada** | idem |
| 3 | `rv²/n_ticks` preveria volatilidade futura (ADR 0013) | **refutada** | `research/findings/2026-08-03-info-por-cotacao-refutada.md` |

**3 testadas · 3 refutadas · 0 sobreviventes · 0 sensores validados**

Réguas medidas, para as próximas: `IC(rv, variância futura) = 0,86` em T=15 — todo sensor de
`VOLATILITY` tem de bater isso. E 66% da variância de posto de `info` era explicada só por
(ano, hora): **IC agrupado é majoritariamente relógio**, e o condicionamento por (dia,hora) é
obrigatório.

---

## Decisões pendentes

| Assunto | Situação |
|---|---|
| **Tese mecânica** | Não escrita. Candidata medida: o perfil intradiário achatou de forma monótona em cinco anos, a abertura da Shanghai Gold Exchange virou a 2ª hora mais volátil, e a asiática tem metade dos ticks com a maior variância por tick. Falta o mecanismo e o falsificador |
| Semântica de `confidence` | Não decidida |
| Critério de escolha de T no Gate 1 | Não decidido |
| Definição de `tick_imb` | 20,9% dos ticks copiam o sinal anterior — injeção mecânica de autocorrelação numa primitiva que `bars/` vai congelar |
| **Definição de `n_ticks`** | **Conta atualizações de ask**: dos ticks que não mexem o bid, 99,74–100% mexem o ask, e 8,3–31,1% da massa de `n_ticks` é ask da Dukascopy — que o ADR 0005 manda descartar. Afeta `tick_imb`, `dur_mean`, `dur_std` e todo sensor que conte tick |
| Capital, drawdown, critério demo→real | Não decididos |
| Correção para testes múltiplos por **projeto**, não só por sensor | Dívida do ADR 0010 |
| Gatilho de revisão do ADR 0002 é 2 exceções — não está no texto dele | Dívida do ADR 0011 |

---

## Próximo passo

**Corrigir `bars.py` antes de qualquer medição.** Onze defeitos encontrados; `data/bars/` foi
apagada porque estava corrompida (`dur_mean`/`dur_std` erradas por 10⁶, barra-fantasma duplicada
por fronteira de mês). `research/audit_ic.py` não executa — `ra -= ra.mean()` sobre array read-only
do pandas 3.0. Lista completa em `research/findings/2026-08-03-info-por-cotacao-refutada.md`.

**Depois:** próximo sensor. Ordem: ADR de hipótese com falsificador → commit → medição → verificação por subagentes → veredito.

---

## Pendência de documentação

`docs/CONTEXT.md` ainda descreve a separação chat / Claude Code como pilar do projeto. Obsoleto
desde o ADR 0009.

## Últimas sessões

Registro completo nas mensagens de commit. Relatórios anteriores a 2026-08-03 estão em
`docs/sessions/`; a prática foi encerrada pelo ADR 0012.
