# 2026-08-03 — `rv²/n_ticks` refutada pelo próprio falsificador

**Hipótese:** ADR 0013, pré-registrada em `3f184cd`
**Veredito:** **REFUTADA**
**Verificação:** implementador independente + auditor de convenção + refutador (lente de artefato)

## O que matou

O falsificador 2 do próprio ADR: *"se o IC desaparecer ao condicionar por `rv` ou por `n_ticks`
separadamente, `info` não acrescenta nada."*

| | T=1 | T=5 | T=15 | T=30 |
|---|---|---|---|---|
| IC bruto | +0,32 | +0,51 | — | +0,57 |
| **IC \| `rv`** | **−0,016** | **−0,032** | **−0,063** | **−0,041** |
| IC \| `n_ticks` | +0,27 | +0,48 | — | +0,55 |

**Não desaparece: inverte de sinal, e continua afastado de zero.** Foi pior do que o ADR previa.

E o baseline nunca foi zero — era `rv`:

| | T=1 | T=5 | T=10 | T=30 |
|---|---|---|---|---|
| `rv` sozinho | **+0,41** | **+0,66** | **+0,70** | **+0,71** |
| `info` | +0,32 | +0,51 | +0,55 | +0,57 |
| `n_ticks` sozinho | +0,34 | +0,53 | +0,56 | +0,54 |

**`info` perde para os dois ingredientes dela.** Dividir `rv²` por `n_ticks` não acrescenta
informação — destrói. Confiabilidade split-half dentro de (dia,hora): `rv²` 0,766 contra `info`
0,561; 43,9% da variação aproveitável de `info` é ruído de estimação.

## Três coisas que a hipótese não previa

**A sonda que a motivou era artefato de período misturado.** Os 0,059 contra 0,040 dividiam σ de
2026 pela mediana de ticks dos **quatro anos**. Casando o período, a razão Ásia/Sobreposição vira
1,024 — e **0,830 pela grandeza que o ADR pré-registra**, sinal invertido. O único número empírico
do ADR não sobrevive a ser recalculado com a própria definição dele.

**O ADR errou o motivo de estar errado.** A seção adversarial previa dominância por `1/n_ticks` e
indicador de hora do dia disfarçado. Medido: `Spearman(info, n_ticks) = +0,21` — **positivo** — e
`Spearman(info, rv) = +0,80`. E o teste intra-hora que o ADR exigia **passa**: +0,50 agrupado,
positivo nas 24 horas. `info` discrimina dentro da hora; só não discrimina nada que `rv` já não
discrimine melhor.

**O mecanismo escrito é de spread, e spread não transplanta.** `rv²/n_ticks` é, algebricamente, a
**média do quadrado do passo de bid por tick** — `sqrt(mediana) = $0,104`. Mede granularidade de
cotação do feed, não chegada de informação. E tamanho de passo e contagem de tick sobem **juntos**
(+0,21), o oposto de "o formador alarga e recota menos".

## Achado que vale além desta hipótese

**`n_ticks` conta atualizações de ask.** Dos ticks que não mexem o bid, **99,74% a 100% mexem o
ask**; conforme o mês, **8,3% a 31,1%** da massa de `n_ticks` é atualização de ask da Dukascopy.

O ADR 0005 manda descartar o ask da Dukascopy por inteiro. Mas `n_ticks` entra em `tick_imb`,
`dur_mean`, `dur_std` e em qualquer sensor que conte tick. **Isso é defeito na definição da camada
`bars/`, não desta hipótese**, e precisa de decisão antes de `bars/` ser congelada.

**E a régua ficou medida:** `IC(rv, variância futura) = 0,86` em T=15. Todo sensor de `VOLATILITY`
tem que bater isso.

**E o agrupamento engana:** 66,0% da variância de posto de `info` é explicada só por (ano, hora).
Dentro de (dia,hora) o IC cai de 0,745 para 0,033, e em T=30 fica em −0,005 **afastado de zero no
sinal errado**. Vale para todo sensor futuro: IC agrupado é majoritariamente relógio.

## O que eu contribuí de número: nada

`research/audit_ic.py` **não executava**. `ra -= ra.mean()` sobre array read-only do pandas 3.0;
`ValueError` na primeira chamada, confirmado por execução. Todos os números acima vêm dos
verificadores independentes.

Onze defeitos no que escrevi. Achei seis sozinho — duplicata de barra por fronteira de mês,
adjacência calculada antes do filtro (1.090 observações com o gap de 62 min tratado como retorno
de 1 min), custo de bootstrap de 11 h, teste bilateral contra pré-registro unilateral, controle
com menos reamostragem que o teste principal, e teste múltiplo não contabilizado.

Os outros cinco vieram do auditor, e um deles é meu de forma constrangedora: **`dur_mean` e
`dur_std` erradas por fator 10⁶** — `raw/` é `timestamp[ms]`, `.astype('int64')` já devolve
milissegundos, e eu divido por 1e6. **Introduzi esse bug ao "corrigir" um aviso de fuso**; a versão
anterior estava certa.

Faltaram também: o `ffill` do sinal propagando o gap noturno para dentro de barras válidas, o bloco
do bootstrap ser dia civil UTC em vez de dia de pregão, e o rótulo de sessão fixo em UTC enquanto a
sessão desliza com o DST.

## Por que isto conta como resultado

O sensor teria sido entregue com IC de +0,51, que parece ótimo, sobre um script que não roda, com
duas de sete primitivas erradas por 10⁶, sem nunca ser comparado contra `rv` sozinho, motivado por
uma sonda que era artefato, e com normalização impossível.

A separação entre quem propõe e quem verifica pegou tudo isso **na primeira vez que foi usada**.
