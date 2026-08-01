# ARROW — contexto do projeto

> Documento de conhecimento. Explica **de onde as decisões vêm**. Para o quê e o como, ver
> `CLAUDE.md`. Para postura e protocolo, ver as instruções do projeto.

---

## Por que ARROW existe

ARROW sucede um projeto anterior (MKS-Engine) que acumulou EAs com camadas de patch, decisões
que só existiam como texto de conversa, e uma linhagem de código já abandonada conceitualmente.
O problema não era o código — era que **as decisões não estavam escritas**, e por isso eram
re-litigadas a cada mudança de contexto.

ARROW começa limpo com duas mudanças estruturais:

1. **Separação de superfícies:** debate no chat, implementação no Claude Code, análise no Cowork.
   A fronteira só se sustenta porque tem artefato no meio — ADR e relatório de sessão.
2. **Decisão escrita antes de código.** O que não está no repositório não existe.

O que atravessou do projeto anterior foram os princípios e os aprendizados. O código, não.

---

## Investigações já concluídas

Estas não precisam ser refeitas. Retomar qualquer uma exige hipótese nova, não parâmetro novo.

### Martingale, grid e recuperação por exposição — encerrado

Estudados e submetidos a simulação de Monte Carlo. Resultado: **ruína quase certa** em tamanhos
de stop realistas ao longo de um ano. Taxas de acerto de 72% a 92% conviviam com ruína — a
acurácia direcional necessária para o breakeven é extremamente alta e muito sensível ao tamanho
do stop.

Essa é a origem do princípio de que **win rate não é evidência de nada**. O mesmo erro reaparece
por outra porta em alvos curtos com stop largo: 85% de acerto e esperança negativa.

### Squeeze Momentum (LazyBear) — dissecado

Serve como modelo de como um indicador deve ser analisado antes de ser adotado:

- O input `mult` é morto: os multiplicadores se cancelam e a condição reduz a
  `stdev(close,20)/mean(TR,20) < 1`
- A razão é **adimensional** e por isso **não detecta compressão de volatilidade** — testado em
  GARCH, a razão vol pós-disparo/base ficou em 1,002. O que ela mede é eficiência de caminho,
  mesma família do Efficiency Ratio, e escala com √N: 41,3% das barras de um passeio aleatório
  ficam em "squeeze"
- O `val` distingue rampa de degrau corretamente, mas está em unidades de preço — o desvio-padrão
  escala linearmente com σ, sem escala calibrada
- O componente Donchian é quase inerte: correlação 0,9949 contra detrend só com SMA

Daí veio a regra de normalização do contrato do sensor: **adimensional e calibrado contra o
nulo**. Um valor em unidades de preço não significa nada de forma estável.

### Custo e horizonte — resolvido em debate

O spread é pedágio fixo pago na entrada, não sangria por tempo. Mas ele desloca **as duas
barreiras na mesma direção**: numa compra com alvo e stop líquidos de tamanho R, o bid precisa
subir `R+c` mas só cair `R−c`.

Consequência: sob caminho sem deriva, a esperança é exatamente `−c` para qualquer arranjo de
alvo e stop. A métrica útil é o **edge exigido**, `c/(2R)`.

A sessão não altera o custo — altera quanto tempo leva para R ficar grande o bastante, já que
R alcançável ≈ σ√T.

### Infraestrutura de dados — planejada, download iniciado

O broker fornece histórico de tick real limitado: a janela é móvel e cobre ~6-7 meses. O Gate 2
exige N ≥ 250 dias de negociação. A importação da Dukascopy não é contingência, é caminho crítico.

A solução desenhada: símbolo customizado no MT5 alimentado por ticks Dukascopy (XAUUSD desde
2003), clonando a spec do símbolo do broker — **XAUUSDm** — para herdar tick value, digits e
contract size.

O spread da Dukascopy não serve — precisa ser substituído por spread do broker calibrado por
bucket (hora × faixa de volatilidade). A diferença de expectância entre tick real e M1 OHLC é o
**gap de fidelidade**, e deve ser medida, não presumida.

Armadilha central: fuso. Há indício de que o servidor opera em UTC+0 — o intervalo diário do
símbolo coincide com a manutenção do COMEX — o que alinharia a Dukascopy diretamente. **Hipótese
não confirmada.**

---

## Método

A ordem é deliberada e não deve ser invertida:

1. Baseline aleatório **antes** do primeiro sensor. Se a régua vier depois, você já viu o
   resultado quando a construiu.
2. Sensor isolado num harness mínimo — sem filtro, sem sessão, sem confluência
3. Gates de sanidade, informação e execução
4. Só então composição, e só depois otimização

A unidade estatística é o **dia**, não o trade: trades no M1 são fortemente autocorrelacionados
dentro do dia, e contar trades como observações independentes infla a significância.

Testar muitos sensores garante que alguns passem por acaso — daí o limite de 3 iterações por
sensor, o registro obrigatório dos reprovados, e o limiar mais rígido para produção.

---

## Estado atual

Nada construído além do esqueleto do repositório. Repositório em `C:\dev\ARROW`, público no
GitHub como `MksMike/ARROW`.

**Existe:** `CLAUDE.md`, `STATE.md`, `.gitignore`, a árvore de diretórios, os ADRs 0001–0004 e
os templates de sessão e de task brief.

**Não existe:** nenhum sensor, nenhuma EA, nenhum `.mq5`, nenhuma medição. Todos os valores de σ
que aparecem nos documentos são **estimativas preliminares** aguardando substituição pelo
`DataAudit`. A tabela inteira da Seção 11 do `CLAUDE.md` é premissa não verificada.

**Dado bruto:** em 2026-08-02 um download de ticks Dukascopy XAUUSD foi iniciado para
`data/dukascopy/` (fora do versionamento). Existe também um snapshot do cache de tick do terminal
em `C:\dev\_mks-tick-snapshot-2026-07-30`, cobrindo 2026-01 a 2026-07 em formato `.tkc` — formato
interno não documentado do MT5, amarrado à pasta do terminal e do servidor. Pela regra de não
aceitar o que não pode ser auditado, ele é apólice de seguro, não fonte oficial de nada.

---

## Em aberto

**Operacional:** capital inicial, drawdown tolerado, critério para passar de demo a real.

**Técnico:** o `k` da fórmula `T_min = (c/kσ)²` do Gate 1 nunca foi definido. Enquanto não for,
o Gate 1 não é executável.

**Conceitual — e é o mais importante:** o projeto tem uma máquina de validação rigorosa e
nenhuma tese declarada. Não está escrito em lugar nenhum *o que se acredita que existe de
explorável* no XAUUSD M1, nem por quê. Sem isso, a construção de sensores vira busca cega, e
busca cega com muitos testes é exatamente o que a correção para testes múltiplos existe para
punir.

A primeira hipótese mecânica — o que gera o desequilíbrio que se pretende capturar — deveria ser
escrita antes do primeiro sensor.
