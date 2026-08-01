# 0002 — Contrato do sensor: `SensorOut` e normalização contra o nulo

**Data:** 2026-08-02
**Status:** aceito
**Decidido em:** debate no chat, 2026-08-02 — registrado como ADR na sessão de bootstrap

> Esta decisão estava listada em `STATE.md` como "pendente de ADR". Este arquivo quita a
> pendência. Nenhum conteúdo novo foi decidido aqui.

## Contexto

O objetivo do projeto é uma biblioteca de sensores **intercambiáveis**: trocar o sensor que
responde por uma função deve ser a alteração de uma linha no Registry. Intercambiabilidade exige
duas coisas — assinatura idêntica e **escala idêntica**.

A segunda é a que costuma ser esquecida, e o Squeeze Momentum (LazyBear) é o caso de estudo. Sua
dissecação mostrou dois defeitos independentes:

- O `val` distingue rampa de degrau corretamente, mas está em **unidades de preço**. O
  desvio-padrão escala linearmente com σ, então o mesmo valor numérico significa coisas
  diferentes na sessão asiática e na sobreposição Londres/NY.
- A razão de compressão é adimensional, mas escala com `√N` e não mede compressão de
  volatilidade coisa nenhuma — sob GARCH, a razão vol pós-disparo/base ficou em 1,002, e 41,3%
  das barras de um passeio aleatório caem em "squeeze".

Sem escala comum, limiares não são transferíveis entre sensores nem entre sessões, e a promessa
de drop-in é falsa.

## Decisão

Todo sensor expõe exatamente esta estrutura:

```mql5
struct SensorOut
{
   double   value;        // sinal normalizado, adimensional
   double   confidence;   // [0.0, 1.0]
   bool     valid;        // false durante warm-up ou dados insuficientes
   datetime bar_time;     // barra FECHADA a que o valor se refere
};
```

**Regra de normalização, inegociável:** `value` é adimensional e calibrado contra a hipótese
nula. Sob passeio aleatório com a volatilidade própria do instrumento, um sensor com sinal deve
ter `E[value] = 0` e `SD[value] = 1`. Sensores de razão ou de magnitude são transformados para
essa escala, não deixados na escala nativa.

Todo core de sensor documenta no cabeçalho: a distribuição sob o nulo, a constante de
normalização usada, e **como ela foi obtida**.

O sensor entrega o valor cru normalizado. Nenhum gate, threshold binário ou filtro que descarte
informação vive dentro dele — quem decide corte é a camada de execução.

## Alternativas rejeitadas

**Deixar cada sensor na sua escala nativa e normalizar no Registry.** Rejeitada: empurra a
calibração para longe de quem conhece a matemática do sensor, e a constante de normalização
deixa de ser documentada junto da derivação que a justifica.

**Normalizar por z-score de janela móvel dentro do sensor.** Rejeitada por dois motivos. Cria
estado dependente de janela, que colide com a exigência de determinismo, e normaliza contra a
distribuição *empírica recente* em vez de contra o **nulo** — o que apaga exatamente o sinal que
se quer medir, já que um regime persistentemente anômalo é normalizado de volta para zero.

**Incluir um `signal` binário na struct, ao lado do `value`.** Rejeitada: é a cláusula pétrea 2
por outra porta. Um sensor que emite decisão binária já embutiu um limiar, e o limiar pertence à
execução.

## Consequências

- A calibração da constante de normalização precisa de um gerador de passeio aleatório com a
  volatilidade medida do instrumento — o que torna o `DataAudit` pré-requisito de qualquer
  sensor, não apenas do Gate 1.
- `confidence` está declarado no contrato mas sua semântica ainda não foi definida em lugar
  nenhum. Pendência aberta.
