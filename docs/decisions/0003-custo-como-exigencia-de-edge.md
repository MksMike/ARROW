# 0003 — Custo como exigência de edge: `c/(2R)`

**Data:** 2026-08-02
**Status:** aceito
**Decidido em:** debate no chat, 2026-08-02 — registrado como ADR na sessão de bootstrap

> Esta decisão estava listada em `STATE.md` como "pendente de ADR". Este arquivo quita a
> pendência. Nenhum conteúdo novo foi decidido aqui.

## Contexto

O tratamento usual do spread — "começa negativo e recupera" — é errado o bastante para produzir
estratégias que parecem viáveis e não são. O spread não é sangria por tempo, é **pedágio fixo
pago na entrada**; o resultado na saída já sai líquido. Mas ele não desloca apenas o ponto de
partida: desloca **as duas barreiras na mesma direção**.

Numa compra com alvo e stop líquidos de tamanho `R` e spread `c`, o bid precisa subir `R+c` para
o alvo ser atingido, mas basta cair `R−c` para o stop disparar.

## Decisão

Sob caminho sem deriva, a matemática de barreira dupla dá:

- `P(ganhar) = (R−c) / 2R`
- `Esperança = −c`, **exatamente**, para qualquer escolha de alvo e stop

Portanto o alvo e o stop não podem ser escolhidos para "melhorar a esperança" — eles não a
afetam. A única métrica operacional é o **acréscimo de acerto direcional necessário** para virar
a esperança:

```
edge exigido = c / (2R)
```

Com `c = $0,20`:

| Alvo/stop líquido | Acerto sem edge | Edge exigido |
|---|---|---|
| $0,30 | 16,7% | **+33 pp** |
| $0,50 | 30% | +20 pp |
| $1,00 | 40% | +10 pp |
| $3,00 | 46,7% | **+3,3 pp** |
| $5,00 | 48% | +2 pp |

**Decorrência normativa:** nenhum resultado é avaliado por win rate. Apenas por esperança em R e
t-stat sobre R agregado por dia.

**Decorrência sobre a sessão:** a sessão não altera o custo. Altera quanto tempo leva para `R`
ficar grande o bastante, já que `R` alcançável ≈ `σ√T`. Nenhuma sessão é proibida; a asiática é
~3× mais exigente em edge para o mesmo tempo de exposição.

**Decorrência sobre o alvo:** alvos abaixo de ~$1,00 líquido exigem 10 pp ou mais de acerto
direcional e são hipótese extraordinária, não ponto de partida.

## Alternativas rejeitadas

**Tratar o spread como custo por tempo, amortizado no holding.** Rejeitada: é factualmente
errado no modelo de execução do MT5. O spread é pago uma vez, na entrada.

**Buscar alvo curto com alta taxa de acerto.** Rejeitada com número: alvo +0,30 com stop −3,00
produz ~85% de trades vencedores e esperança de −$0,20. É a mesma matemática do martingale por
outra porta de entrada, e é a origem do princípio de que win rate não é evidência de nada.

**Entrar com ordem limitada para não pagar o spread.** Não rejeitada, mas **fora de escopo**. É
a única forma de não pagar o pedágio, ao custo de seleção adversa — quando a ordem é preenchida,
frequentemente é porque o preço continuou contra. Registrada como linha futura.

## Consequências

- O horizonte T do Gate 1 é derivado do custo, não escolhido: `T_opt = 4·T_min`, com
  `T_min = (c/kσ)²`.
- **`k` nunca foi definido.** A fórmula está escrita no Gate 1 do `CLAUDE.md` mas não é
  executável enquanto `k` não tiver valor e derivação. É a pendência mais concreta bloqueando o
  Gate 1, e é debate de chat.
- Os valores de σ que sustentam a tabela da Seção 11.2 são estimativas preliminares. O
  `DataAudit` os substitui antes de qualquer Gate 1.
