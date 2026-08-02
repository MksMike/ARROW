# 0006 — Feriados de mercado excluídos do dataset

**Data:** 2026-08-02
**Status:** aceito
**Decidido em:** chat, 2026-08-02 — pergunta levantada no relatório de sessão `raw-4-anos`

## Contexto

A validação de `raw/` sobre os quatro anos (2022-08 a 2026-07) encontrou 12 dias que destoam do
resto do dataset:

- **4 dias úteis sem nenhum tick** — as quatro Sextas-feiras Santas do período. O mercado de ouro
  fecha por completo.
- **8 dias com 1% a 4% do volume normal** — todos os Natais e Ano-Novos, incluindo os observados
  `2022-12-26` e `2023-01-02`, quando a data caiu no domingo. Sessão encurtada.

Nenhum deles é defeito de dado: são o calendário do mercado. Mas eles não podem simplesmente
ficar, porque um dia com 1% do volume normal tem σ, densidade de tick e comportamento de spread
que não têm nada a ver com o mercado que se pretende operar. Deixá-los dentro contamina três
coisas ao mesmo tempo: a calibração de normalização dos sensores (`CLAUDE.md` §5.2, que calibra
contra a volatilidade própria do instrumento), a estatística diária do Gate 2 (cláusula pétrea 7,
onde o dia é a unidade), e o modelo de spread por bucket (§10.5).

## Decisão

**Os 12 dias de feriado são removidos de `curated/`, e portanto de `bars/` e de todo teste.**

`raw/` permanece intacta. Ela é imutável por princípio (§10.2) e continua contendo os ticks
desses dias — a exclusão é uma camada de transformação, não uma edição da fonte. Um resultado
questionado seis meses depois continua reconstituível.

### O calendário é declarado por regra, não inferido do dado

Esta é a parte que importa mais que a exclusão em si.

A implementação óbvia seria excluir o que a validação achou magro ou ausente. **Isso está
errado**, e o erro é exatamente o que o próprio relatório de validação alertava: um feriado e um
buraco de coleta se parecem num gráfico de ticks/dia. Excluir automaticamente tudo que é magro
faz o buraco de coleta desaparecer em silêncio — que é o defeito preciso que a camada de
validação existe para tornar visível.

Então a direção se inverte. O calendário vive em `research/lib/market_calendar.py` e é gerado por
regra fechada:

- **Sexta-feira Santa** — dois dias antes da Páscoa, pelo computus gregoriano anônimo. Algoritmo
  sem tabela e sem dependência externa, porque o cálculo tem que dar o mesmo resultado em
  qualquer máquina do projeto (cláusula pétrea 3).
- **Natal (25/12) e Ano-Novo (01/01)** — sessão encurtada.
- **Observância:** data fixa que cai no domingo é observada na segunda seguinte; no sábado, na
  sexta anterior. Na prática só a regra do domingo aparece, porque o ouro não negocia no sábado.

E o dado é comparado **contra** o calendário, não o contrário. `validate.py` classifica cada dia
ausente ou magro em duas caixas: explicado pelo calendário, ou **sem explicação**. O segundo caso
faz o relatório dizer isso em destaque e o `build_raw.py` sair com código 3.

### Verificação

A regra reproduz **exatamente** os 12 dias encontrados empiricamente nos quatro anos — 12 gerados,
12 observados, zero sobrando de cada lado. O relatório
`reports/xauusd-2022-08_2026-08-validacao.md` mostra a classificação dia a dia, e a validação
atual fecha com "4 explicados, 0 sem explicação" e "8 explicados, 0 sem explicação".

Isso não prova que a regra está certa para sempre — prova que ela está certa nesta janela, e
qualquer divergência futura vira anomalia visível em vez de exclusão silenciosa.

## Alternativas rejeitadas

**Manter os feriados como dias de zero trade.** Rejeitada. Não seriam dias de zero trade: o
sensor calcularia normalmente sobre 2.000 ticks e a execução poderia disparar. Um dia com 1% do
volume entra na agregação diária do Gate 2 com o mesmo peso de um pregão cheio, e a unidade
estatística é o dia (cláusula pétrea 7). Isso não é conservador, é ruído com peso de sinal.

**Manter e deixar o filtro `COST` decidir.** É a opção mais alinhada com a §2.1 — "o filtro vale
mais que o sinal" — e foi considerada seriamente. Rejeitada por ordem de construção: exigiria que
`COST` existisse e estivesse validado antes do primeiro Gate 2, invertendo a §18, e faria a
qualidade de todo resultado inicial depender de um sensor que ainda não passou por gate nenhum.
Fica registrada como **linha futura**: quando `COST` existir e for validado, faz sentido reabrir
e medir se ele reproduz a exclusão sozinho. Isso seria evidência a favor do sensor, não motivo
para mudar o dataset.

**Excluir automaticamente todo dia magro, sem calendário.** Rejeitada — é a inversão descrita
acima, e apaga buraco de coleta em silêncio.

**Excluir a semana inteira do feriado.** Rejeitada por não ter fundamento medido. Os dias ao
redor do Natal aparecem com volume normal no gráfico de ticks/dia; excluí-los seria descartar
amostra por superstição, e a §10.1 já mostra que amostra é o recurso escasso do projeto.

## Consequências

- `curate.py`, quando for escrito, aplica `drop_holidays()` junto da máscara de sessão (ADR 0005
  §2). A função devolve a contagem do que removeu por dia, e essa contagem entra no relatório —
  uma exclusão que não reporta o que excluiu é indistinguível de um bug de filtro.
- A perda de amostra é de **12 dias em 1.041 dias úteis**, ou 1,2%. O requisito da §10.1 continua
  satisfeito com folga (1.029 dias contra o padrão de ~1.020).
- Nenhum outro feriado de mercado do ouro aparece nesta janela. Se um dataset futuro incluir um,
  ele surgirá como anomalia sem explicação — que é o comportamento desejado, e não uma falha.
