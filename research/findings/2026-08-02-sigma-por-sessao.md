# 2026-08-02 — σ por sessão: a premissa da sessão asiática está refutada

**Tipo:** auditoria de dado (não é teste de hipótese de sensor)
**Dado:** `data/raw/`, 240.344.662 ticks, 2022-08-01 a 2026-07-31
**Código:** `research/audit_sigma.py`
**Relatório completo:** `reports/sigma-auditoria.md`

## O que se acreditava

`CLAUDE.md` §13.2, antes desta medição: σ≈0,50 no asiático, ≈1,20 em Londres, ≈2,20 na
sobreposição LDN/NY, com a conclusão normativa de que **"a asiática é ~3× mais exigente em edge
para o mesmo tempo de exposição"**. Isso pressupõe razão σ_asiático / σ_sobreposição ≈ 0,23.

## O que foi medido

1.380.142 variações M1 entre minutos adjacentes, com máscara de sessão (§10.6) e feriados
(ADR 0006) aplicados.

| Ano | Preço mediano | Asiático | Sobrep. LDN/NY | Razão |
|---|---|---|---|---|
| 2022 | $1.736 | 0,300 | 0,709 | **0,42** |
| 2023 | $1.945 | 0,295 | 0,681 | **0,43** |
| 2024 | $2.380 | 0,485 | 0,926 | **0,52** |
| 2025 | $3.345 | 1,067 | 1,498 | **0,71** |
| 2026 | $4.597 | 2,500 | 3,318 | **0,75** |

## Conclusão

**A premissa está refutada, e já era imprecisa quando foi escrita.** Mesmo em 2022 a razão era
0,42 e não 0,23. Desde então subiu de forma monótona por cinco anos, sem um único ano de reversão,
até 0,75 — o perfil intradiário do ouro achatou.

Em 2026, a hora **1 UTC** (09:00 em Pequim, abertura da Shanghai Gold Exchange) é a segunda hora
mais volátil do dia, atrás apenas das 15 UTC. Em bps do preço, a hora 1 já aparecia entre as mais
altas no agregado de quatro anos — o fenômeno intensificou, não surgiu do nada.

**Não é artefato de medição.** O mesmo código sobre 2023 devolve o perfil clássico: asiático entre
0,59 e 1,00 da hora mediana, pico de 2,03 na sobreposição. A mudança está no mercado.

## Consequência prática

Filtrar por sessão para "evitar a asiática" não tem mais base empírica. Se `REGIME` ou `COST`
vierem a discriminar horário, o critério precisa sair de medição corrente e ser **remedido
periodicamente** — o próprio §2 diz que edge decai, e este achado é um exemplo de premissa que
decaiu em quatro anos.

## O que este achado NÃO diz

- **Não diz que a asiática é tão boa quanto a sobreposição para operar.** σ mede movimento, não
  previsibilidade. Um mercado pode ser volátil e sem edge algum.
- **Não sobrevive à mudança de nível de preço.** σ em dólares triplicou em dois anos, mas em bps
  subiu bem menos — a maior parte do salto é preço, não regime. Toda tabela em dólares aqui tem
  prazo de validade.
- **Está inflada por bid-ask bounce.** σ de fechamento a fechamento no M1 contém ruído de
  microestrutura que não é movimento aproveitável. Os tempos `T = (R/σ)²` derivados dela são o
  **melhor caso**, não a expectativa.
