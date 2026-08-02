# Sessão 2026-08-03-0100 — dependência em escala de tick

| Campo | Valor |
|---|---|
| Máquina | PC-Home |
| Branch | `session/2026-08-03-dependencia-tick` |
| Commits | `fbe8ce4..<encerramento>` |
| Duração | ~2 h |

## Objetivo declarado

Task brief v3 do chat: medir a estrutura de autocovariância dos retornos de tick do bid, lag a
lag, e a densidade de tick por sessão. Pergunta: **a dependência está confinada ao lag 1?**

## Feito

| Arquivo | O que mudou | Por quê |
|---|---|---|
| `research/lib/microstructure.py` | criado | γ_j com bootstrap diário, RV_k, rv do ADR 0005, bids repetidos, densidade |
| `research/audit_tickdep.py` | criado | CLI espelhando `audit_sigma.py`, com cache por barra |
| `research/findings/2026-08-03-*.md` | criado | O achado |
| `reports/dependencia-tick.md` | criado | Relatório |
| `reports/autocov-tick.csv`, `assinatura-variancia.csv/.png`, `densidade-tick.csv` | criados | Dados |

## Verificado

- [x] **Critério 2 — piloto reproduzido antes de rodar os quatro anos.** `E[rv²]` intra-minuto e
      `σ²` com **0,00%** de diferença; `ρ₁` com +0,88%, explicado por o piloto ter usado
      `pandas.Series.autocorr`, que remove média e inclui pares que cruzam a fronteira do minuto.
- [x] **Rodada completa** sobre 240.132.015 ticks úteis, 1.402.473 barras. Tempo **2.860 s**,
      pico de memória **3.975 MB**. Os seis arquivos escritos.
- [x] **Erro-padrão por block bootstrap de blocos diários**, 1.000 reamostragens, consistente com
      a §7 e com a cláusula pétrea 7.
- [x] **Curva de assinatura valida o modelo:** previsão pelos `γ_j` truncados no lag 8 reproduz o
      medido dentro de **1% até k=16**; desvio de 2,7% a 7,3% em k=64 mede a dependência acima do
      lag 8.
- [x] Constantes de máscara e commit registrados no cabeçalho do relatório.

### Números que NÃO saíram de execução

Nenhum. Nenhum backtest, nenhum sensor.

## Resultado

**Não, a dependência não está confinada ao lag 1 — e há um achado maior atrás disso.**

Em 2026 o lag 1 é o **menos** significativo dos cinco primeiros (|t| = 1,5, indistinguível de
zero); o pico está no lag 3 (|t| = 5,6). Mas o que importa mais: **`γ₁/γ₀` troca de sinal três
vezes em cinco anos** — −0,027 / +0,069 / +0,004 / −0,081 / −0,009 — e varia uma ordem de
grandeza. Não é propriedade estável do instrumento.

**O `ρ₁ = +0,0124` do piloto não sobrevive à amostra completa.** O ano inteiro de 2026 dá −0,0088.
O piloto não estava errado: estava medindo um mês. A premissa que o brief v3 aceitou — dependência
líquida positiva, logo `rv` deflacionado — vale para junho de 2026 e não como afirmação geral.

**O que sobrevive:** `rv` do ADR 0005 não está inflado por ruído de cotação. A dependência líquida
é de ordem 10⁻² relativa a γ₀, pequena demais para o mecanismo que as v1 e v2 temiam. Falsificada
por margem larga.

## Correções que precisei fazer no brief ao implementar

1. **A fórmula de previsão do critério 4 usa `n` onde deve ser `(n−k)`.** Subamostrar não cobre o
   minuto inteiro. Em k=64 com n=171 o erro é de +59% e tem forma de curvatura — seria lido como
   refutação do modelo. **É a segunda vez**: a v2 trazia o mesmo defeito como `m = n_ticks/k`.
2. **A previsão precisa da média de `n`, não da mediana.** `RV_k` medido é média sobre barras;
   minutos movimentados são mais voláteis, então `E[n·γ₀] > mediana(n)·γ₀`. No teste de fumaça
   isso dava offset constante de +11,9% já em k=1. Acrescentei a curva normalizada em k=1, que
   isola a forma do nível.
3. **O gap de fronteira precisa excluir minutos não adjacentes.** Com todos, a média dá 26,9 s
   contra mediana de 0,402 s — as barras logo após a parada diária têm "gap" de 62 minutos.

## Falha minha, corrigida no meio da sessão

Rodei a primeira vez com o **critério 6 sub-implementado**: ele pede `γ_j` com `n_changes` como
eixo e um veredicto sobre qual eixo descreve a escala, e eu só tinha contado bids repetidos
globalmente. Matei a rodada aos ~15 min, completei, e reiniciei com cache das estatísticas por
barra para que a próxima iteração não precise reler `raw/`.

## Critério 5 — gap de fronteira

O brief previa ~1,3 s. Medido: **média 2,206 s, mediana 0,821 s** — a previsão fica entre as duas,
nem confirmada nem refutada. A fronteira acrescenta **+2,55%** ao `rv²`, contra os 2,21 pp que o
brief atribuía a ela.

## Critério 6 — qual eixo

**Indistinguível.** Amplitude de `ρ₁` por quartil: 0,0259 em `n_ticks`, 0,0323 em `n_changes` —
menos de 1,5× uma da outra. Os dois eixos são colineares por construção e estes dados não os
separam. Reportado como tal, sem escolher um lado.

## Achados laterais que valem mais que o principal

**20,9% dos retornos de tick são exatamente zero.** O ADR 0005 define `tick_imb` como *"repete o
sinal anterior se igual"* — em um quinto dos ticks o sinal é **copiado**. Isso é injeção mecânica
de autocorrelação numa primitiva que `bars/` vai congelar, e é mais direto que o mecanismo que
esta sessão investigou.

**A densidade fecha a lacuna da seção 8 e traz um contraste novo:** a asiática tem mediana de 106
ticks contra 277 da sobreposição, e **58% das barras asiáticas ficam abaixo de 128 ticks**. A
variância por tick é a maior de todas as sessões (0,059 contra 0,040 da sobreposição). **A
asiática move mais por tick, com metade dos ticks** — ficou tão volátil quanto as outras sem
ficar tão líquida.

## Não feito, e por quê

- **Nenhum ADR escrito.** O brief é explícito e o resultado alimenta debate, não decisão do Code.
- **Nenhuma decisão sobre `bars/`.** A questão do `tick_imb` é nova e vai para o chat.
- **`REFERENCIA-XAUUSD.md` não tocado.** A ressalva 2 da seção 7 precisa de revisão à luz disto,
  mas é narrativa gerada e vira sessão própria.
- **`BrokerTickLogger` continua parado.** Ver abaixo — é o item mais urgente do projeto e não é
  desta sessão.

## Incidente — o logger morreu por colisão de Script

O log do terminal mostra:

```
18:48:11  BrokerTickLogger (XAUUSDm,M1)  retomando ... (1 no mesmo ms)
19:37:06  BrokerTickLogger (XAUUSDm,M1)  parado. 0 ticks gravados
19:37:08  DataAudit        (XAUUSDm,M1)  iniciando
```

**O MT5 permite um Script por gráfico.** Soltar o `DataAudit` no mesmo gráfico desalojou o logger.
Nenhum dado perdido — o mercado esteve fechado —, mas ele perderia a abertura.

Isso expõe que **Script é o artefato errado para coleta contínua**: morre com outro script no mesmo
gráfico, não sobrevive a reinício do terminal, e morre se o gráfico mudar de símbolo ou timeframe.
Um Expert Advisor não tem nenhum dos três. **Candidato a próxima sessão, com ADR.**

O mesmo log traz uma confirmação boa: `retomando ... (1 no mesmo ms)` com zero ticks regravados —
a correção de retomada, que eu só podia afirmar que compilava, está exercitada em produção.

## Perguntas para o chat

1. **`tick_imb` repete o sinal em 20,9% dos ticks.** Isso é decisão de especificação do ADR 0005 e
   injeta autocorrelação mecânica. Alternativas: manter, usar zero, ou excluir ticks sem mudança
   de bid do denominador. É debate, e é anterior à construção de `bars/`.
2. **A dependência de tick não é estável entre anos.** Qualquer sensor que a use como insumo
   precisa de critério de remedição, e a §2 já diz que edge decai.
3. **`BrokerTickLogger`: Script ou EA?** Estrutural, precisa de ADR.
4. As três de fundo seguem abertas: **T do Gate 1**, **`confidence`**, **tese mecânica**.

## Estado da árvore

- [x] `git status` limpo
- [x] Branch mergeada em `main`
- [x] `STATE.md` atualizado e sessão fechada
- [x] Push feito
