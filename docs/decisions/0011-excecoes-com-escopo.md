# 0011 — Exceção com escopo: um ADR pode não valer para um componente

**Data:** 2026-08-03
**Status:** aceito
**Decidido em:** sessão `excecoes`, por decisão explícita do usuário

## Contexto

O ADR 0010 estabeleceu que ADR não recusa ideia, e listou três respostas para quando uma restrição
morde: a versão que a satisfaz, o número que sustenta a colisão com uma pétrea, ou o ADR que
supersede o que atrapalha.

**Faltou a quarta, e é a mais útil no dia a dia.** Um ADR pode estar certo em geral e errado para
um componente específico, e nesse caso nem obedecer nem revogar são a resposta.

O caso concreto já existe. O ADR 0002 exige saída adimensional com `E=0` e `SD=1` sob o nulo, e a
razão está escrita: sem escala comum, sensores da mesma função não são intercambiáveis e limiares
não transferem. Isso é decisivo para `VOLATILITY` ou `MOMENTUM`.

Mas um sensor `STRUCTURE` que reporta **onde está um nível** é intrinsecamente uma coordenada de
preço. Forçá-lo a `E=0, SD=1` pode destruir a informação em vez de padronizá-la — e a razão de ser
do ADR 0002, intercambiabilidade dentro da função, continua satisfeita se todos os `STRUCTURE`
usarem a mesma convenção alternativa entre si.

Obedecer cegamente perde o sensor. Revogar o ADR 0002 quebra as outras seis funções. **A resposta
certa é uma exceção com escopo declarado.**

## Decisão

**Todo ADR admite exceção com escopo.** A exceção é ela própria um ADR, e vale sob quatro
condições.

### 1. Justificada por mecanismo, nunca por resultado

A exceção tem de argumentar **por que a razão de ser do ADR original não se aplica àquele
componente**. É argumento que se faz sem ver medição nenhuma.

**Está proibido justificar exceção por resultado.** *"Este sensor funciona muito bem mas viola o
ADR N, então vamos exceptuar"* é o mecanismo que destrói a proteção do projeto inteiro: toda regra
passaria a dobrar na direção do número que apareceu, e número bom aparece por acaso o tempo todo —
é exatamente o que a correção para testes múltiplos da §7 existe para punir.

### 2. Commitada antes da medição que se beneficia dela

Mesmo mecanismo do pré-registro do ADR 0009, e pela mesma razão. A ordem é verificável no
histórico do git.

**Exceção cujo commit não precede a medição que a favorece é nula**, e a medição que dependia dela
também. Sem essa regra o item 1 é intenção; com ela, é verificável por qualquer pessoa.

### 3. Escopo nomeado, e visível de dentro do componente

A exceção nomeia **exatamente** a que componente se aplica. Não vale "sensores de estrutura em
geral" — vale `SNS_STR_<Nome>`, nominalmente.

E o componente carrega no cabeçalho a linha que declara sob qual exceção ele opera. Quem abre o
`.mqh` descobre ali, sem precisar caçar ADR.

### 4. Não pode contornar cláusula pétrea

Exceção vale sobre ADR. **As pétreas da §3 não admitem exceção**, e uma exceção cujo efeito
prático seja violar uma delas é recusada — com o número que sustenta a recusa, conforme a §1.

Se a exceção parece necessária e esbarra numa pétrea, o que existe é uma incompatibilidade real,
e ela vira debate sobre a pétrea — não exceção silenciosa por baixo dela.

## Três exceções ao mesmo ADR revisam o ADR

**Se o mesmo ADR precisar de exceção três vezes, o errado é o ADR, não os componentes.** A
terceira dispara revisão obrigatória da regra, e essa revisão é sessão própria.

O limite espelha as 3 iterações de parâmetro da §7 pela mesma lógica: a quarta vez que se contorna
a mesma coisa não é caso particular, é padrão. Regra que precisa ser contornada sistematicamente
está descrevendo mal o mundo.

Isto atende o que o usuário pediu — *"ou rever se a ADR realmente faz sentido"* — sem deixar a
revisão dependendo de alguém lembrar. Vira gatilho.

## O que a exceção precisa conter

Além do formato normal de ADR:

- **Qual ADR**, e qual trecho dele
- **Qual componente**, nominalmente
- **Por que a razão de ser do ADR original não se aplica ali** — o argumento de mecanismo
- **O que a exceção NÃO libera** — a fronteira, explícita
- **O que a tornaria errada** — falsificador da própria exceção
- **Contador**: quantas exceções este ADR já acumulou

## Por que isto provavelmente está errado

Seção exigida pelo ADR 0009 §2.

**O argumento mais forte contra:** exceção com escopo é a porta pela qual toda regra morre por
mil cortes. Cada exceção é defensável isoladamente e o conjunto delas esvazia o ADR sem que
ninguém tenha decidido esvaziá-lo. O contador de três é defesa fraca contra isso — três exceções
já podem ter destruído a intercambiabilidade que o ADR 0002 protege, e a revisão chegaria depois
do estrago.

**A defesa é parcial e vale registrar como tal.** O item 3 obriga escopo nominal, o que impede
exceção genérica; o gatilho de três força revisão antes que vire cultura. Mas **nada aqui impede
que dois componentes com exceções diferentes deixem de ser intercambiáveis entre si** — que é
precisamente o dano que o ADR 0002 existe para evitar.

Mitigação registrada como dívida: quando o segundo sensor da mesma função receber exceção, a
revisão **tem de acontecer ali**, não na terceira. O limite de três vale para ADRs de método; para
o ADR 0002 especificamente, dois já é sinal.

## Alternativas rejeitadas

**Exceção por decisão pontual, sem ADR.** Rejeitada: seria decisão sem registro, e a §17.6 diz que
o que não está em ADR não é decisão, é sugestão. Exceção não registrada é a forma mais rápida de
o projeto voltar a re-litigar tudo.

**Permitir exceção justificada por resultado, desde que registrada.** Rejeitada, e é a alternativa
tentadora. Registrar não conserta: o problema não é opacidade, é que o critério passa a ser o
número. Um projeto que excepta suas regras diante de bons resultados não tem regras — tem
preferências.

**Nunca exceptuar; ou obedecer ou superseder.** Rejeitada por ser o estado anterior, e é o que
motivou este ADR. Superseder um ADR inteiro para acomodar um componente quebra os outros que
dependiam dele.

## Consequências

- A §16.1 do `CLAUDE.md` ganha a quarta resposta.
- Exceções entram no índice de ADRs marcadas como tal, com o ADR que exceptuam.
- **Dívida:** o gatilho de revisão é 3 para ADRs de método e **2 para o ADR 0002**, pela razão da
  seção adversarial. Isso não está no texto do 0002 e deveria estar — fica registrado em
  `STATE.md`.
