# 0004 — Repositório público, dados fora do repositório

**Data:** 2026-08-02
**Status:** aceito
**Decidido em:** debate no chat, 2026-08-02 — registrado como ADR na sessão de bootstrap

> Esta decisão estava listada em `STATE.md` como "pendente de ADR". Este arquivo quita a
> pendência. Nenhum conteúdo novo foi decidido aqui.

## Contexto

O repositório é público por decisão do usuário (`MksMike/ARROW`). Isso não é neutro para um
projeto que manipula dados de mercado licenciados, credenciais de corretora e resultados de
backtest.

## Decisão

**O código é público; os dados não.**

Nunca entram no repositório, sob nenhuma circunstância:

- Credenciais, número de conta, tokens, nomes de servidor de broker
- Arquivos de tick da Dukascopy e qualquer dataset derivado deles
- Qualquer identificador pessoal
- Caminhos absolutos de máquina — o GUID do terminal MT5 muda por instalação e vive em
  `tools/setup/local_paths.ps1`, não versionado

Duas razões independentes para os ticks: a redistribuição pode violar os termos da fonte, e o
volume inviabiliza o Git de qualquer forma — uma única captura de sete meses do cache do terminal
já passa de 400 MB por símbolo.

**Regra operacional acrescentada nesta sessão:** toda ferramenta externa que baixe dados para
dentro da árvore tem seu diretório de saída **e de cache** adicionados ao `.gitignore` antes do
primeiro `git add`.

O motivo é concreto, não hipotético. Durante esta própria sessão de bootstrap, um download de
ticks Dukascopy em andamento criou `data/dukascopy/` (coberto pela regra `data/`), mas também
`.dukascopy-cache/` e `download/` **na raiz do repositório** — nenhum dos dois previsto na lista
de `.gitignore` que o `CLAUDE.md` especificava. O `.gitignore` foi escrito antes do primeiro
`git add` e os três caminhos foram verificados com `git check-ignore` antes de qualquer commit.

## Alternativas rejeitadas

**Repositório privado.** Rejeitada pelo usuário. A decisão de visibilidade é dele; este ADR
registra as consequências operacionais, não a reabre.

**Versionar uma amostra pequena de ticks para reprodutibilidade.** Rejeitada: "amostra pequena"
não tem definição estável e o primeiro pedido de "só mais um mês" destrói a regra. A
reprodutibilidade é resolvida por `run_meta.json`, que registra dataset, período e commit hash —
não por versionar o dado.

## Consequências

- `reports/` **é** versionado, e portanto público. Nenhum relatório pode conter número de conta,
  nome de servidor ou identificador pessoal.
- Um clone limpo do repositório não roda backtest: precisa do passo de obtenção de dados. Isso é
  aceito e deve estar documentado no `README.md`.
- Snapshots do cache de tick do terminal (`.tkc`) ficam fora da árvore do repositório. São
  formato interno não documentado do MT5, amarrado à pasta do terminal e do servidor, e pela
  regra de não aceitar o que não pode ser auditado não são fonte oficial de nada.
