# Sessão 2026-08-03-0430 — ambiente único

| Campo | Valor |
|---|---|
| Máquina | PC-Home |
| Branch | `session/2026-08-03-ambiente-unico` |
| Commits | `f3d6868..<encerramento>` |
| Duração | ~20 min |

## Objetivo declarado

Eliminar a divisão chat / Claude Code e tornar este o ambiente completo de desenvolvimento —
debate, estratégia, implementação e análise. Por decisão explícita do usuário, que autorizou
alterar o `CLAUDE.md`.

## Feito

| Arquivo | O que mudou | Por quê |
|---|---|---|
| `docs/decisions/0009-ambiente-unico.md` | criado | Mudança estrutural exige ADR |
| `CLAUDE.md` §1 | não-complacência vale para o usuário; propor vira função | Sem segunda superfície, ambas viram função |
| `CLAUDE.md` §6.2 | pré-registro verificável por ordem de commit + seção adversarial | Substitui a fronteira entre superfícies |
| `CLAUDE.md` §7 | registro de hipóteses, com contagem acumulada | Teste múltiplo piora com ambiente único |
| `CLAUDE.md` §16 | reescrita: uma superfície | Era a §14 antiga |
| `CLAUDE.md` §17.1, §17.2, §17.6 | fronteira removida; medição vence | Precedência atualizada |
| `STATE.md` | contador de hipóteses testadas | Exigido pelo ADR 0009 §3 |

## Verificado

- [x] As oito substituições no `CLAUDE.md` aplicadas com âncora exata — nenhuma por aproximação.
- [x] Contador de hipóteses instalado em `STATE.md` com as duas já testadas, ambas refutadas.
- [x] `git status` limpo após o commit.

### Números que NÃO saíram de execução

Nenhum. Sessão de processo; nenhuma medição.

## O que motivou

O custo do transporte de contexto entre superfícies está registrado no próprio repositório, e não
é hipótese:

- brief v1 citando a §13.2 **que já não continha número**
- brief v2 usando `σ = 2,590`, de antes do terceiro reprocessamento da máscara
- brief v3 trazendo, **pela segunda vez**, a fórmula de assinatura com `n` onde deve ser `(n−k)`
- e uma versão inteira construída sobre um piloto de um mês, cuja conclusão não sobreviveu aos
  quatro anos

Nenhum é descuido. São a assinatura de reenviar por texto um estado que muda a cada sessão.

Há um custo simétrico, e é meu: com a implementação separada do debate, passei a operar só a
metade cética da §1 e a ignorar a que ela pede com a mesma força — propor. Uma superfície
especulava sem verificar; a outra verificava sem especular.

## O que a divisão comprava, e o que substitui

Três coisas, e eliminá-las sem substituto seria pior que o problema:

| O que a divisão comprava | O que substitui |
|---|---|
| Separar quem especula de quem verifica | **Ordem de commit.** O ADR precede o código que mede, e o git carimba a sequência |
| Forçar artefato escrito na fronteira | O ADR continua; perde a fronteira, mantém a obrigação |
| Limiar fixado antes de medir | Mesmo mecanismo: commit antes |

**A substituição é mais forte que o original.** O brief do chat podia ser escrito depois de espiar
o dado e ninguém teria como saber. O histórico do git não permite isso.

## Decisões tomadas dentro da sessão

| Decisão | Alternativa rejeitada | Vira ADR? |
|---|---|---|
| Ambiente único | Manter divisão e melhorar o transporte | **ADR 0009** |
| Pré-registro por ordem de commit | Ambiente único sem pré-registro | ADR 0009 — seria trocar proteção real por conveniência |
| Seção adversarial obrigatória em ADR de hipótese | Confiar na §1 | ADR 0009 — sem outra entidade, a objeção tem de ser fabricada |
| Contador de hipóteses em `STATE.md` | Só registrar findings | ADR 0009 — a contagem é insumo da correção, não curiosidade |
| Medição vence sobre ADR e `STATE.md` na §17.6 | Manter ADR no topo | não — é constatação: já aconteceu quatro vezes |

## O risco que fica, nomeado

Uma entidade que propõe e valida a própria hipótese tem interesse na sobrevivência dela. Os três
mecanismos do ADR 0009 existem contra isso.

**Se algum dia um resultado favorável aparecer sem que o pré-registro o preceda no histórico, esse
resultado é nulo.** A regra existe para o momento em que for inconveniente aplicá-la, e está
escrita agora justamente porque ainda não é.

## Não feito, e por quê

- **Nenhuma hipótese proposta nesta sessão.** A mudança de processo veio primeiro, de propósito:
  propor antes de o pré-registro existir seria começar pelo lado errado da regra que acabou de ser
  escrita.
- **`docs/templates/task-brief-template.md` mantido.** Deixa de ser transporte, continua servindo
  para o usuário delimitar escopo fechado.
- **`docs/CONTEXT.md` não revisado**, embora descreva a separação de superfícies como um dos dois
  pilares do projeto. É documento de conhecimento e a revisão é sessão própria.

## Próximo passo

Com o pré-registro em vigor, a primeira hipótese pode ser escrita. A candidata que saiu de medição
está no relatório da sessão `dependencia-tick`: **a correlação entre o retorno da sessão asiática
e os primeiros minutos de Londres deve estar subindo ao longo de cinco anos**, se a formação de
preço migrou parcialmente para o horário asiático.

Ela é ADR antes de ser código, com falsificador e seção adversarial — e a medição sai de `raw/`,
sem depender de `broker/`.

## Estado da árvore

- [x] `git status` limpo
- [x] Branch mergeada em `main`
- [x] `STATE.md` atualizado e sessão fechada
- [x] Push feito
