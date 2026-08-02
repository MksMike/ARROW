# 0007 — Foco único em XAUUSDm até existir catálogo validado

**Data:** 2026-08-02
**Status:** aceito
**Decidido em:** chat, 2026-08-02

## Contexto

O terminal tem `XAUUSDz`, o ativo equivalente numa conta Exness Zero, com estrutura de custo
diferente — spread menor e comissão explícita, contra spread-como-custo-total da conta Standard.
A sessão de bootstrap havia recomendado auditar os dois lado a lado, com o argumento de que a
comparação de custo sairia de medição em vez de premissa.

O `DataAudit` de 2026-08-02 não conseguiu selecionar `XAUUSDz`, e a pergunta voltou: vale a pena
resolver isso agora?

## Decisão

**Não. Enquanto não existir catálogo de sensores e indicadores testados e validados, o projeto
mede um único instrumento: `XAUUSDm` na conta Standard.**

Outros ativos, outras contas, outras corretoras e outros instrumentos (`XAUUSDz`, BTCUSD, o que
for) entram numa **bateria posterior**, e só depois de existirem simultaneamente:

- um catálogo de sensores aprovados nos Gates, com veredicto escrito
- um catálogo de indicadores testados e validados
- EAs de teste produzindo resultado consistente em `XAUUSDm`

## Por quê

O motivo imediato é foco. O motivo que sustenta a decisão é estatístico.

A §7 limita a **3 iterações de parâmetro** por sensor porque testar muitas variações garante que
alguma passe por acaso. Testar o mesmo sensor em N instrumentos é exatamente a mesma
multiplicação, com uma dimensão a mais e sem nenhum limite escrito. Um sensor que falha em
`XAUUSDm` e passa em `XAUUSDz` não descobriu nada sobre o mercado: descobriu que existem dois
sorteios em vez de um. E como as duas séries de preço são **praticamente o mesmo ativo**, a
correlação entre elas é quase total — o teste extra não traz informação independente, só chances
extras de aprovar ruído.

A ordem correta inverte isso: validar em um instrumento com o rigor todo e **depois** perguntar se
o resultado transporta. Aí a transferência é evidência a favor do sensor, porque foi prevista
antes de medida. Feita ao contrário, é seleção.

Há ainda um motivo de método. A §2 diz que o produto é a máquina de produzir e aposentar sensores,
não o sensor. Uma máquina que funciona num instrumento pode ser apontada para outro; uma máquina
construída tentando servir a vários ao mesmo tempo carrega generalização preventiva antes de ter
qualquer evidência de que ela é necessária — o que a §14 já proíbe.

## Alternativas rejeitadas

**Auditar `XAUUSDz` agora, só para registrar a spec.** Rejeitada. O custo não é a auditoria — é
que a spec registrada convida à comparação, a comparação convida ao teste, e o teste é o problema.
Nada impede auditar depois; a spec não é perecível como o tick.

**Coletar tick de `XAUUSDz` em paralelo, "já que a janela rola".** Rejeitada pelo mesmo motivo,
com uma ressalva honesta: é a única alternativa que perde algo irreversível, porque a janela de
retenção de tick do broker de fato rola. Aceita-se a perda. Quando a bateria posterior acontecer,
a coleta de `XAUUSDz` começa naquele momento e acumula a partir dali, exatamente como `XAUUSDm`
está fazendo agora.

**Manter BTCUSD como controle de "sensor genérico".** Rejeitada. A §14 já exclui outros
instrumentos, e um controle só tem valor depois que existe o que controlar.

## Consequências

- `DataAudit.mq5` passa a auditar um símbolo por padrão. `XAUUSDz` sai da §18.
- `data/broker/BTCUSDm-20260802.csv`, coletado por acidente, sai de `data/broker/` — que a ADR
  0005 define como ticks do `XAUUSDm` — e vai para `data/_fora-de-escopo/`. **Não é apagado:** é
  dado real e não custa nada guardar, mas não pode ficar onde `spread_model.py` vai varrer.
- A comparação de custo Standard × Zero fica registrada como **linha futura**, junto da ordem
  limitada na entrada (§13.2).
- Quando a bateria posterior for aberta, ela **exige ADR próprio** que declare, antes de medir,
  quantos instrumentos entram e qual a correção para testes múltiplos entre eles. Sem isso, é a
  mesma p-hacking que este ADR existe para evitar.
