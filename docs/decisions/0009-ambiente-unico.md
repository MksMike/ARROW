# 0009 — Ambiente único: debate e implementação no mesmo lugar

**Data:** 2026-08-03
**Status:** aceito
**Decidido em:** sessão `ambiente-unico`, por decisão explícita do usuário

## Contexto

O projeto nasceu com três superfícies: chat para debate conceitual, Claude Code para
implementação, Cowork para análise. A fronteira se sustentava por artefato — task brief, ADR,
relatório de sessão.

O custo apareceu rápido, e está registrado no próprio repositório:

- O task brief v1 da sessão de microestrutura citava a `CLAUDE.md` §13.2 **que já não continha
  número**, porque a sessão `referencia` a tinha esvaziado.
- O v2 usava `σ = 2,590`, de **antes do terceiro reprocessamento da máscara**.
- O v3 trouxe, pela segunda vez, a fórmula de assinatura com `n` onde deve ser `(n−k)` — erro de
  +59% no extremo, com forma de curvatura, que teria refutado o próprio modelo por artefato.
- E construiu uma versão inteira sobre um piloto de **um mês**, cuja conclusão não sobreviveu aos
  quatro anos.

Nenhum desses é descuido. São a assinatura de **transporte de contexto com perda**: o estado do
repositório muda a cada sessão, e reenviá-lo por texto degrada.

Há um custo simétrico, e ele é meu. Com a implementação separada do debate, o Claude Code passou a
operar só a metade cética da §1 — encontrar defeito no que já foi especificado — e a ignorar a
metade que a §1 pede com a mesma força: **"Criativo na busca de edge. Propor abordagens não-óbvias
é desejável."** O resultado é que uma superfície especula sem verificar e a outra verifica sem
especular. As duas subaproveitadas, em espelho.

## Decisão

**Uma superfície. Debate, desenho experimental, matemática, implementação, análise e git
acontecem aqui.** Task brief deixa de ser formato de transporte.

O que a divisão comprava é substituído por mecanismo mais forte, não abandonado.

### 1. Pré-registro por ordem de commit

A separação entre especular e verificar deixa de ser *entre entidades* e passa a ser *entre
commits*.

**Uma hipótese, um limiar ou um critério de aprovação só valem se estiverem commitados ANTES do
commit que introduz o código que os mede.** A ordem é verificável no histórico do git por qualquer
pessoa, a qualquer momento.

Isto é mais forte que a divisão anterior. O brief do chat podia ser escrito depois de espiar o
dado e ninguém teria como saber; o commit carimba a sequência.

Medição cujo pré-registro não a precede no histórico **não conta**, e o relatório de sessão diz
isso explicitamente em vez de omitir.

### 2. Advogado do diabo obrigatório e escrito

Sem uma segunda entidade para objetar, a objeção tem de ser fabricada de propósito.

Todo ADR de hipótese, antes de qualquer medição, contém uma seção **"Por que isto provavelmente
está errado"**, com o argumento mais forte que eu conseguir construir contra a própria hipótese.
Não é ressalva de rodapé: é a alternativa concreta que explicaria a mesma observação sem que a
hipótese seja verdadeira.

Hipótese cuja seção adversarial é fraca não passou pelo teste — passou por mim de bom humor.

### 3. Registro de hipóteses, e a correção que ele exige

Com uma entidade gerando hipóteses livremente, **o problema de teste múltiplo piora, não
melhora.** A §7 já obriga registrar todo sensor testado, inclusive reprovado. Estende-se:

**Toda hipótese testada é registrada em `research/findings/`, inclusive as refutadas, e a
contagem acumulada aparece em `STATE.md`.** O número de hipóteses testadas é insumo da correção
para testes múltiplos — não uma curiosidade.

### 4. Não-complacência com o usuário, explicitada

A §1 já diz "nunca complacente". Com ambiente único isso deixa de ser postura e vira função: não
há outra superfície para discordar.

**Instrução do usuário que contradiga medição registrada recebe o número de volta, não
concordância.** Se o usuário reafirmar depois disso, a decisão é dele, é executada por inteiro, e
a divergência fica escrita no relatório de sessão.

### 5. Proposta ativa deixa de ser opcional

A §1 pede criatividade na busca de edge. Com ambiente único, **não propor é falha de função, não
prudência.** O Code passa a ser responsável por levantar hipóteses, não só por implementar as dos
outros.

Com a restrição do item 1: proposta vira ADR antes de virar medição.

## Alternativas rejeitadas

**Manter a divisão e melhorar o transporte** — por exemplo, o chat lendo o repositório no GitHub
antes de escrever cada brief. Rejeitada: já é o que se tentou, e os quatro defeitos listados no
contexto aconteceram mesmo com o `REFERENCIA-XAUUSD.md` publicado. O problema não é acesso, é que
o estado muda entre a leitura e o uso.

**Manter o chat só para hipóteses, trazendo o resto.** Rejeitada: é exatamente onde os erros
apareceram. As hipóteses do chat vinham com aritmética errada porque ele não roda nada. Separar
hipótese de verificação é a divisão que mais custa, não a que mais protege.

**Ambiente único sem pré-registro por commit.** Rejeitada, e é a alternativa perigosa: seria
trocar uma proteção real por conveniência. O item 1 não é burocracia — é a única coisa que impede
que hipótese e resultado sejam escritos na mesma respiração.

## Consequências

- A §14 do `CLAUDE.md` é reescrita. A §17.1 mantém o fato técnico — o Code é quem escreve — e
  perde a justificativa de fronteira entre superfícies.
- `docs/templates/task-brief-template.md` deixa de ser formato de transporte. Fica disponível para
  quando o usuário quiser entregar um escopo fechado, que é uso legítimo e diferente.
- O passo 1 da §6.2, "Hipótese → ADR", deixa de ser formalidade e passa a ser **verificável**: o
  commit do ADR precede o commit da medição, ou a medição não conta.
- O usuário deixa de ser transportador de contexto entre superfícies. Isso era trabalho dele e não
  produzia nada que o repositório não pudesse produzir.
- **Risco aceito e nomeado:** uma entidade que propõe e valida a própria hipótese tem interesse na
  sobrevivência dela. Os itens 1 a 3 existem contra isso e são o que este ADR tem de mais
  importante. Se algum dia um resultado favorável aparecer sem que o pré-registro o preceda no
  histórico, **esse resultado é nulo** — e a regra existe justamente para o momento em que for
  inconveniente aplicá-la.
