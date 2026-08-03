# 0013 — Hipótese: informatividade por cotação

**Data:** 2026-08-03
**Status:** **REFUTADA** em 2026-08-03 — ver `research/findings/2026-08-03-info-por-cotacao-refutada.md`

> **Veredito.** O falsificador 2 disparou: o IC parcial condicionado a `rv` não desaparece, **inverte**
> (−0,032 em T=5, afastado de zero). E `rv` sozinho bate `info` em todos os horizontes. A sonda que
> motivou a hipótese era artefato de período misturado — recalculada com a definição deste próprio
> ADR, ela inverte de sinal.
**Função candidata:** `VOLATILITY` (possivelmente `REGIME`)

> Pré-registro (§6). Este ADR é commitado **antes** do código que o mede. Medição cujo commit não
> venha depois deste não conta.

## A grandeza

```
info = rv² / n_ticks
```

Variância de preço por cotação emitida, dentro da barra M1. Ambas as entradas já são primitivas
especificadas de `bars/` e saem de `raw/` sem depender de `broker/`.

Não é volatilidade (`rv` sozinho) nem atividade (`n_ticks` sozinho). É a razão.

## Mecanismo

Quando fluxo informado domina, o formador de mercado alarga e recota menos — cada atualização de
cotação carrega mais movimento. Quando o formador domina, há muitas cotações e pouco deslocamento
líquido.

Se isso for verdade, `info` alta marca minutos em que **informação está chegando**. E chegada de
informação é agrupada no tempo, então deveria prever volatilidade elevada nos minutos seguintes.

Medido (sonda, não evidência): 0,059 na sessão asiática contra 0,040 na sobreposição LDN/NY —
apesar de a asiática ter **metade** dos ticks e σ quase igual.

## O que a falsifica

1. **IC de Spearman** entre `value` e a volatilidade realizada futura no horizonte T, condicionado
   à sessão, com limite inferior do intervalo de 95% **não afastado de zero** → morre. Critério do
   Gate 1, sem limiar especial.
2. **Controle obrigatório:** se o IC desaparecer ao condicionar por `rv` **ou** por `n_ticks`
   separadamente, `info` não acrescenta nada e é proxy disfarçado de uma das duas. Isso mata a
   hipótese mesmo que o IC bruto passe.

## Por que isto provavelmente está errado

`n_ticks` varia uma ordem de grandeza entre sessões enquanto `rv` varia bem menos, então `info`
pode ser dominada mecanicamente por `1/n_ticks` — ou seja, um indicador de hora do dia disfarçado,
e hora do dia a máscara de sessão já captura.

E o contraste que motivou a hipótese é **entre sessões**, não dentro delas: diferença entre
sessões já é conhecida e não é aproveitável. A hipótese só vale se `info` discriminar **dentro** de
uma mesma hora.

## Forma exigida pelo contrato

- **Normalização (ADR 0002):** calibrar contra passeio aleatório com `n_ticks` casado, de modo que
  `E[value] = 0` e `SD[value] = 1` sob o nulo. A constante e sua derivação vão no cabeçalho do core.
- **Sem gate interno** (§5.3): entrega o valor cru normalizado.
- **Incremental** (§8): `rv` e `n_ticks` são acumuladores de barra; a razão é O(1) e o warm-up é o
  da normalização.
- **`confidence` não é preenchido** — sem semântica definida.

## O que este ADR não afirma

Nada sobre direção, nada sobre esperança em R, nada sobre custo. É Gate 1 — conteúdo
informacional, sem execução. Passar aqui não sugere que sobreviva ao Gate 2, onde o spread de
$0,20 exige 3,3 pp de acerto para R=$3.
