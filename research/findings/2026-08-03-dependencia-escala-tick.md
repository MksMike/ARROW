# 2026-08-03 — a dependência de tick não está confinada ao lag 1, e não é estável

**Tipo:** auditoria de dado (não é teste de hipótese de sensor)
**Dado:** `data/raw/`, 240.132.015 ticks úteis, 2022-08-01 a 2026-07-31
**Código:** `research/audit_tickdep.py`, `research/lib/microstructure.py`
**Relatório completo:** `reports/dependencia-tick.md`

## A pergunta

O piloto de 2026-06 mediu `ρ₁ = +0,0124` nos retornos de tick do bid. A sessão perguntava se a
dependência está **confinada ao lag 1** — se estivesse, a curva de subamostragem seria determinada
pelos dois extremos e a medição de dois pontos já teria bastado.

## A resposta: não, e por dois motivos diferentes

### 1. Há estrutura significativa além do lag 1

Em 2026, com erro-padrão por block bootstrap de blocos diários (1.000 reamostragens):

| lag | γ_j/γ₀ | \|t\| |
|---|---|---|
| 1 | −0,00875 | **1,5** |
| 2 | +0,00545 | 2,7 |
| 3 | −0,00518 | **5,6** |
| 4 | −0,00237 | 3,4 |
| 5 | −0,00187 | 3,0 |
| 6–8 | < 0,0005 | ≤ 1,0 |

**O lag 1 é o menos significativo dos cinco primeiros.** O pico está no lag 3.

### 2. E a dependência não é uma propriedade estável do instrumento

Esta é a parte que importa mais. `γ₁/γ₀` por ano:

| 2022 | 2023 | 2024 | 2025 | 2026 | domingo |
|---|---|---|---|---|---|
| −0,0268 (2,7) | **+0,0689 (21,9)** | +0,0037 (0,3) | −0,0807 (2,3) | −0,0088 (1,5) | **−0,1692 (3,7)** |

**Troca de sinal três vezes em cinco anos e varia uma ordem de grandeza.** 2023 é um outlier com
estrutura enorme — seis dos sete lags seguintes também significativos. 2024 e 2026 têm lag 1
indistinguível de zero.

O domingo é qualitativamente diferente: −0,169, a maior magnitude de todas e negativa, que é o
que se espera de quique de cotação em mercado fino. Isso valida a decisão do brief de mantê-lo
como estrato próprio.

## O que isso faz com o piloto

**`ρ₁ = +0,0124` de 2026-06 não sobrevive à amostra completa.** O ano inteiro de 2026 dá −0,0088,
com |t| = 1,5 — indistinguível de zero, e de sinal oposto.

O piloto foi reproduzido exatamente (`E[rv²]` e `σ²` com 0,00% de diferença; `ρ₁` com +0,88%,
explicado pelo `autocorr` remover média e incluir pares que cruzam a fronteira do minuto). Ele
não estava errado: **estava medindo um mês.**

Consequência: a premissa que o brief v3 aceitou — *"positivo refuta ruído iid, e com dependência
líquida positiva `rv` fica deflacionado"* — vale para junho de 2026 e não vale como afirmação
geral. O sinal da dependência líquida depende do período.

## O que continua valendo

**`rv` do ADR 0005 não está inflado por ruído de cotação.** Isso sobrevive: a dependência líquida,
qualquer que seja seu sinal no período, é de ordem 10⁻² relativa a γ₀ — pequena demais para o
mecanismo de `s² + 2n·η²` que as versões 1 e 2 do brief temiam. A hipótese de contaminação está
falsificada, e por margem larga.

**O modelo de covariância estacionária dentro do minuto se sustenta.** A curva de assinatura
prevista pelos `γ_j` **truncados no lag 8** reproduz a medida dentro de **1% até k=16**:

| k | 2 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|
| erro de forma (2026) | 0,00% | +0,03% | +0,16% | +0,93% | +2,95% | +6,90% |

O desvio crescente em k=32 e 64 é a medida direta da dependência **acima** do lag 8: existe, e é
pequena.

## Achados laterais que valem mais que o principal

**20,9% dos retornos de tick são exatamente zero** — o bid não mudou. Varia de 12,5% em 2026 a
29,1% em 2024. Isso importa porque o ADR 0005 define `tick_imb` como *"repete o sinal anterior se
igual"*: **em um quinto dos ticks o sinal é copiado**, o que é injeção mecânica de autocorrelação
numa primitiva que `bars/` vai congelar. Não é o mesmo defeito que esta sessão investigou, e é
mais direto.

**A densidade de tick por sessão fecha a lacuna da seção 8 do documento de referência**, e traz um
contraste que o σ sozinho não mostrava:

| Sessão | ticks (mediana) | mudanças | abaixo de 128 | σ 2026 | variância por tick |
|---|---|---|---|---|---|
| Asiático | 106 | 79 | 58% das barras | 2,500 | **0,059** |
| Londres | 140 | 102 | 44% | 2,245 | 0,036 |
| Nova York | 133 | 96 | 48% | 2,417 | 0,044 |
| Sobreposição LDN/NY | 277 | 213 | 13% | 3,318 | 0,040 |

**A sessão asiática move mais por tick, com metade dos ticks.** Ela tem a maior variância por tick
de todas e a menor densidade. Isso é uma caracterização diferente da que o achatamento de σ deu:
a asiática ficou tão volátil quanto as outras **sem** ficar tão líquida quanto elas.

Para desenho de sensor isso é material: qualquer primitiva que dependa de contagem de tick
— `rv`, `tick_imb`, `dur_mean`, `dur_std` — tem base amostral muito menor na asiática, e **58% das
barras asiáticas nem chegam a 128 ticks**.

## O que este achado NÃO diz

- **Não estima `η`.** O que se mede é a dependência **líquida**: momento em escala de tick entra
  positivo, quique de cotação entra negativo, e os dois não são separáveis com série de bid
  apenas. Nada aqui é estimativa de ruído de cotação nem de spread efetivo.
- **Não decide nada sobre `bars/`.** A definição de `rv` do ADR 0005 sai desta sessão sem
  objeção do mecanismo que estava sob suspeita, mas a questão do `tick_imb` é nova e é debate.
- **Não separa os dois eixos.** `n_ticks` e `n_changes` dão amplitudes de `ρ₁` por quartil de
  0,0259 e 0,0323 — a menos de 1,5× uma da outra. São colineares por construção; estes dados não
  distinguem qual governa a escala.
- **É Dukascopy, não o broker.** O caminho de preço transplanta; a densidade de tick é parcial e
  precisa ser remedida contra `data/broker/` quando houver amostra.
