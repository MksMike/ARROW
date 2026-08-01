# Sessão <AAAA-MM-DD-HHMM> — <slug>

> Salvar como `docs/sessions/AAAA-MM-DD-HHMM-slug.md`.
> Escrito para ser lido **a frio pela outra superfície**. Nenhum contexto assumido:
> caminhos completos, decisões explícitas, nada de "aquele arquivo que a gente mexeu".

| Campo | Valor |
|---|---|
| Máquina | |
| Branch | |
| Commits | `<sha_inicial>..<sha_final>` |
| Duração | |

## Objetivo declarado

O que esta sessão se propôs a fazer, em uma frase. Se o objetivo mudou no meio, registrar os dois
e por que mudou.

## Feito

| Arquivo | O que mudou | Por quê |
|---|---|---|
| `MQL5/...` | | |

## Verificado

- [ ] Compilou limpo — colar a linha final do log
- [ ] Rodou no Strategy Tester — período, símbolo, dataset (tick real ou M1 OHLC)
- [ ] Resultado: **nenhum número aqui que não tenha saído de execução real**

Se nada foi verificado, escrever `Nada verificado` explicitamente. Ausência de linha não é
o mesmo que "não precisou".

## Não feito, e por quê

A parte que mais se perde e a mais importante. Tudo que foi cogitado e deixado de fora:
tentativas abandonadas, caminhos que não deram certo, escopo cortado por tempo. Sem isso a
próxima sessão repete o mesmo erro.

## Decisões tomadas dentro da sessão

Toda escolha estrutural feita aqui e não decidida previamente em ADR. Cada linha vira ADR ou
vira pergunta para o chat — nunca fica só neste relatório.

| Decisão | Alternativa rejeitada | Vira ADR? |
|---|---|---|
| | | |

## Perguntas para o chat

Coisas que exigem debate conceitual e não deviam ter sido decididas no meio da implementação.

## Estado da árvore

- [ ] `git status` limpo
- [ ] Branch mergeada em `main` **ou** marcada como WIP em `STATE.md`
- [ ] `STATE.md` atualizado e sessão fechada
- [ ] Push feito
