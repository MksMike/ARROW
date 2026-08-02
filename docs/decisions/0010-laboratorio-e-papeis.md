# 0010 — O laboratório: ADR restringe forma, não fecha pergunta

**Data:** 2026-08-03
**Status:** aceito
**Decidido em:** sessão `laboratorio`, por decisão explícita do usuário

## Contexto

O ADR 0009 unificou o ambiente. Faltava dizer **como se trabalha dentro dele**, e a ausência
produziu duas patologias que o usuário nomeou e que o repositório confirma.

**Primeira: os ADRs viraram muro.** O acoplamento é mensurável. A §18 impõe a fila
`broker/ → spread/ → curated/ → bars/ → sensores`, e o ADR 0005 faz `bars/` derivar de
`curated/`. Mas **sete das nove colunas de `bars/` não dependem de spread**, e o Gate 1 —
"conteúdo informacional, **sem execução**" — não exige spread para nada. O resultado é que nenhum
sensor chega ao Gate 1 antes de `data/broker/` acumular semanas de amostra, por uma dependência
que o Gate 1 não tem. Isso não é rigor; é acoplamento errado.

**Segunda: eu fiquei mais travado que as regras.** Identifiquei o achado da sessão asiática e o
classifiquei como "material para o chat" em vez de escrever a hipótese. Depois do ADR 0009, que
tornou propor um dever, encerrei uma sessão dizendo *"quando você quiser, escrevo o ADR"* —
pedindo licença para cumprir obrigação que eu mesmo havia acabado de escrever. Nenhum ADR me
proibia.

O risco que isso cria é existencial para o projeto. A §2 diz que o produto é uma **máquina que
produz e aposenta sensores continuamente**. Uma máquina que não consegue começar não é máquina.

## Decisão

### 1. ADR nunca é resposta a "podemos tentar X?"

**Nenhuma ideia é recusada por ADR.** ADR registra decisão tomada; não é veto sobre pergunta nova.

Quando uma ideia chega, a ordem é **explorar → dar forma → só então checar restrição** — nessa
ordem, sempre. Checar restrição antes de explorar é como a exploração morre.

Se uma restrição morder de verdade, a resposta **não é "não"**. É uma das três:

- **a versão que satisfaz a restrição** — quase sempre existe, porque a restrição costuma ser de
  forma e não de conteúdo;
- **"colide com a cláusula pétrea N, e o número que sustenta é este"** — com o número, conforme
  a §1;
- **"o ADR que atrapalha é o M, e ele deveria mudar"** — seguido do ADR novo que o supersede.
  ADR é revisável por construção. *"O ADR M diz não"* não é resposta; *"o ADR M diz não, e vejamos
  se deveria"* é.

### 2. Só as pétreas recusam, e só recusam construir

As cláusulas pétreas da §3 continuam duras e não são renegociáveis. Elas existem contra ruína, e
a de recuperação por exposição já foi estressada por Monte Carlo.

**Mas mesmo elas recusam construir, nunca investigar.** Debater por que martingale arruína é
trabalho legítimo; construí-lo não é. A distinção importa porque entender o mecanismo de uma coisa
proibida é frequentemente o caminho para achar a versão permitida que funciona.

### 3. Caso resolvido, para não haver dúvida

> **"Quero um sensor que tente prever até onde o próximo candle pode chegar."**

Resposta **errada**, e é a que este ADR existe para proibir: *"o ADR 0005 congelou as primitivas
de `bars/`"*, ou *"a §18 diz que primeiro vem `broker/`"*, ou *"falta a tese"*.

Resposta **certa**: isso é uma função `VOLATILITY` ou `STRUCTURE` — prever alcance é prever
dispersão condicional. Explorar o que "até onde" significa: range do candle, máximo favorável,
ou o percentil da distribuição condicional. Achar o mecanismo que faria isso ser previsível.
Depois, e só depois, dar a forma que o contrato exige: saída adimensional com `E=0` e `SD=1` sob
o nulo (ADR 0002), sem gate interno (§5.3), com caminho incremental em `OnCalculate` (§10.3).

**Nenhum ADR diz não a essa ideia.** Eles dizem qual forma a resposta precisa ter.

### 4. Dois níveis, para o processo não matar a fluidez

| | Sonda | Hipótese |
|---|---|---|
| O que é | Medição exploratória, para orientar | Afirmação que poderia justificar construir sensor |
| Pré-registro | **Não exige** | **Exige** — ADR antes do código (ADR 0009) |
| Subagentes | Não | Sim |
| Pode ser citada como evidência | **Não** | Sim |

A sonda é o que torna o laboratório utilizável: medir para ver, rápido, sem cerimônia. O preço é
que ela **não vale como prova** e fica marcada como sonda no relatório.

Isto não é abstrato. **O piloto de 2026-06 era uma sonda e foi tratado como evidência** — um
brief inteiro foi construído sobre ele, e a conclusão não sobreviveu aos quatro anos. Com os dois
níveis, a sonda teria orientado e a hipótese teria sido medida antes de virar premissa.

**Gatilho de promoção:** todo resultado **citado** para justificar decisão vira hipótese
retroativamente e precisa do caminho completo — mesmo tendo nascido sonda. Citar é o gatilho, não
a intenção original. Esta regra existe contra a tentação de chamar de sonda o que se quer testar
rápido.

### 5. Papéis

**Claude Code — o laboratório.** Explora ideias com o usuário, de forma generativa e não
defensiva. Transforma ideia vaga em forma testável: mecanismo, falsificador, normalização,
caminho incremental. Escreve o ADR de hipótese. Implementa. E argumenta contra as próprias ideias
com honestidade (§1) — o que **não** é o mesmo que recusá-las antes de explorar.

**Subagentes — a verificação.** Existem porque quem propõe e valida a própria hipótese tem
interesse na sobrevivência dela; é o risco que o ADR 0009 nomeou e não resolveu. Eles restauram a
separação que a divisão chat/Code dava, **sem reintroduzir a perda de contexto**, porque leem o
mesmo repositório em vez de receber estado por texto.

Três mandatos, e são **fixos nesta constituição, não compostos caso a caso** — se eu escrevesse o
prompt de cada verificador, eu escolheria o quanto ele aperta:

| Papel | Mandato |
|---|---|
| **Implementador independente** | Implementa a medição **a partir do pré-registro**, sem ver minha implementação. Dois caminhos independentes que concordam produzem número real; se divergem, a divergência é o achado |
| **Refutador** | Tenta matar a hipótese. Assume refutado em caso de dúvida. Procura a explicação mundana que produziria a mesma observação |
| **Auditor de convenção** | Confere máscara de sessão, feriados, bid-não-mid, blocos de um dia. São as convenções que já quebraram três vezes |

**Revisar meu código não é o mandato do implementador independente.** Um verificador que lê o que
escrevi herda meus erros. O erro do fator `(n−k)` sobreviveu a duas versões de brief porque só
existia uma derivação; duas derivações independentes o teriam pego na primeira.

**O veredito é commitado antes de eu revisar qualquer coisa.** Sem isso eu itero até o subagente
concordar, que é p-hacking com passos extras. E vale o limite da §7: **hipótese que precisa de
mais de três rodadas de objeção para sobreviver não sobreviveu — foi lixada.**

### 6. `bars/` desacopla de `curated/`

Consequência imediata do bloqueio descrito no contexto, e o ADR 0005 fica emendado neste ponto:

**As sete primitivas que não dependem de spread são construídas a partir de `raw/`, agora.**
`spread_p50` e `spread_p95` ficam nulas até `spread/` existir.

Gate 1 roda sobre a parte livre de spread — é o que ele sempre exigiu, já que é explicitamente
"sem execução". Gate 2 continua exigindo custo, corretamente, porque a cláusula pétrea 8 é sobre
execução e o Gate 2 é o gate de execução.

Isto **não afrouxa nada**: põe a dependência onde ela sempre esteve.

## Por que isto provavelmente está errado

Seção exigida pelo ADR 0009 §2, aplicada a este próprio ADR.

**O argumento mais forte contra:** afrouxar a barreira de entrada de ideias aumenta o número de
hipóteses testadas, e a §7 existe porque testar muitas garante que algumas passem por acaso. Um
laboratório fluido pode virar uma máquina de gerar falsos positivos com aparência de método.

**A defesa, e ela é parcial:** o contador de hipóteses do ADR 0009 §3 existe exatamente para isso,
e o gatilho de promoção do item 4 impede que sondas entrem na conta como se fossem evidência. Mas
é defesa contábil, não estrutural — **se o número de hipóteses testadas crescer rápido, a correção
para testes múltiplos precisa endurecer, e isso ainda não está quantificado.** Fica registrado
como dívida deste ADR.

**Segundo argumento:** desacoplar `bars/` de `curated/` cria uma janela em que sensores são
validados no Gate 1 sobre dado sem custo aplicado, e o custo é a restrição que mais mata neste
projeto — `c/(2R)` exige 3,3 pp para R=$3. Um sensor pode passar no Gate 1 com folga e morrer no
Gate 2 por completo. **A defesa é que isso já era verdade** e o Gate 2 continua no lugar; mas o
risco real é psicológico, de apego a um sensor que passou no gate barato.

## Alternativas rejeitadas

**Afrouxar as cláusulas pétreas junto.** Rejeitada sem hesitação. Elas não são o que trava —
nenhuma pétrea impediu um único sensor até hoje. O que travava era acoplamento de arquitetura
confundido com restrição de conteúdo.

**Remover ou suspender os ADRs.** Rejeitada. O problema nunca foi existirem; foi serem usados como
veto em vez de registro. Sem eles a §17.6 perde o topo da precedência e o projeto volta a
re-litigar decisão a cada sessão — que é literalmente por que o ARROW existe (`docs/CONTEXT.md`).

**Manter como está e confiar em bom senso.** Rejeitada pela evidência: o bom senso já falhou nas
duas direções nesta mesma semana — ADR usado como muro, e eu pedindo licença para cumprir dever
escrito.

## Consequências

- A §1 ganha a regra de que ADR não recusa ideia; a §16 é reescrita com o modelo de laboratório,
  os dois níveis e os mandatos de subagente.
- O ADR 0005 fica **emendado** no ponto do acoplamento `bars/` ↔ `curated/`. Não é superseded: o
  resto dele continua valendo inteiro.
- Subagentes passam a ser parte do método, não ferramenta ocasional.
- **Dívida registrada:** a correção para testes múltiplos precisa ser quantificada em função do
  número de hipóteses testadas. Hoje a §7 tem limite por sensor (3 iterações) e nenhum limite por
  projeto.
