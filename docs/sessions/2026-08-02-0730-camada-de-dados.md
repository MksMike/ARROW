# Sessão 2026-08-02-0730 — camada de dados

| Campo | Valor |
|---|---|
| Máquina | PC-Home |
| Branch | `session/2026-08-02-camada-de-dados` |
| Commits | `46580e0..<encerramento>` |
| Duração | ~50 min |

## Objetivo declarado

Instalar a constituição revisada, registrar o task brief da camada de dados como ADR, e executar
os dois primeiros itens dele: `BrokerTickLogger.mq5` em produção contínua e
`loader.py` + `validate.py`.

O objetivo não mudou. O escopo cresceu em dois pontos, ambos por obstáculo técnico descoberto
durante a implementação e descritos em "Decisões".

## Feito

| Arquivo | O que mudou | Por quê |
|---|---|---|
| `CLAUDE.md` | §10.7 reescrita, §10.1 atualizada, Gate 1 marcado, §18 corrigida | Ver "Correções" |
| `.gitignore` | três furos fechados | O bloco da §12.1 não protegia o que dizia proteger |
| `STATE.md` | pendências, download, ordem de trabalho | Estado real, não o herdado |
| `docs/decisions/0005-*.md` | criado | Task brief da camada de dados vira ADR |
| `tools/setup/junctions.ps1` | quinta junction `Files\ARROW` → `data` | MQL5 não escreve fora do sandbox |
| `MQL5/Scripts/ARROW/BrokerTickLogger.mq5` | criado | Coleta contínua de tick do broker |
| `research/lib/loader.py` | criado | Dukascopy CSV → `raw/` Parquet particionado |
| `research/lib/validate.py` | criado | Três verificações + gráfico de ticks/dia |
| `research/build_raw.py` | criado | CLI das duas etapas acima |
| `research/requirements.txt` | criado | Versões fixadas — reconstituibilidade (§10.2) |
| `reports/xauusd-2025-08_2026-08-*` | criados | Relatório, gráfico e série da validação |

## Verificado

- [x] **`BrokerTickLogger.mq5` compilou limpo.** Linha final do log:
      `Result: 0 errors, 0 warnings, 536 ms elapsed, cpu='X64 Regular'`
- [x] **Junctions**: as cinco resolvem, round-trip de escrita testado, segunda execução do script
      reporta "já aponta para o repo" nas cinco (idempotente).
- [x] **`raw/` construída e validada** sobre `2025-08-01 → 2026-08-01`:
      **91.480.835 ticks**, 4,39 GB de CSV → **522 MB** de Parquet zstd em 12 partições mensais.
      Primeiro tick `2025-08-01 00:00:00 UTC`, último `2026-07-31 20:59:02.882 UTC`.
      Zero `ts` retrocedendo, zero `ask < bid`, zero preço ≤ 0, zero linha duplicada.
- [x] **Round-trip do loader conferido contra o CSV de origem**: `bid` e `ask` batem valor a
      valor, `ts` em UTC, `2022-08-01 00:00:00.143` reconstruído corretamente de
      `1659312000143`.
- [x] `git check-ignore` nos dois sentidos: `data/`, `.dukascopy-cache/`, `download/`,
      `local_paths.ps1` e `.venv/` bloqueados; `reports/**/*.csv` e `local_paths.example.ps1`
      versionáveis.
- [x] Regra 3 da §12.1 rodada antes de cada commit: nenhum arquivo staged acima de 5 MB.
      Maior blob do histórico inteiro do repositório: `CLAUDE.md`, 38 KB.

### Números que NÃO saíram de execução

Nenhum. Não houve backtest, não houve sensor, não houve Strategy Tester nesta sessão.

## Não feito, e por quê

- **`BrokerTickLogger` não está rodando.** Compila limpo, mas o critério de pronto do brief é
  "rodando ininterrupto no PC-Home", e um Script MQL5 precisa ser **anexado a um gráfico de
  `XAUUSDm` no terminal por um humano**. Não consigo fazer isso por linha de comando. **O item 1
  do brief está incompleto, e é o urgente do projeto** — cada dia não coletado é verdade de campo
  perdida para sempre.
- **A retomada sem duplicar não foi exercitada.** A lógica existe (`ScanFileTail` + contagem de
  ticks no mesmo milissegundo) e o raciocínio está no código, mas ela só é testável com o script
  rodando de verdade e sendo reiniciado. **Não afirmo que funciona; afirmo que compila.**
- **O backfill via `CopyTicks` não foi testado**, pelo mesmo motivo, e está desligado por padrão.
- **`raw/` cobre um ano, não quatro.** O download roda 2025 → 2024 → 2023 → 2022 e só 2025
  terminou. Convertê-lo agora foi deliberado: o ano mais recente é o mais representativo e libera
  a auditoria. Os outros três exigem rodar `build_raw.py` conforme cada CSV fechar. Verifiquei
  que o CSV de 2025 estava estável (delta 0 em 20 s) antes de tocá-lo — rodar sobre arquivo em
  escrita produz última linha truncada.
- **O CSV `2022-08-01_2023-08-01` (173 MB) é resto da corrida morta** e está truncado. Não foi
  convertido e não deve ser.
- **σ por bucket de hora não foi medido.** É o item 5 da §18 e o insumo mais importante do
  projeto; depende de `raw/`, que agora existe para um ano. Fica para a próxima sessão.
- **`DataAudit.mq5`, `spread_model.py`, `curate.py`, `bars.py`, `parity.py`, `ParityDump.mq5`**
  — itens 3 a 7 do brief, fora do escopo combinado para esta sessão.

## Decisões tomadas dentro da sessão

| Decisão | Alternativa rejeitada | Vira ADR? |
|---|---|---|
| Quinta junction `Files\ARROW` → `data`, e o script recusa iniciar sem ela | Gravar dentro da pasta do terminal e copiar depois | ADR 0005 (consequência) |
| Offset servidor→UTC aplicado no ato e registrado em `_offset_log.csv` | Gravar hora de servidor crua e converter depois | ADR 0005 §5 |
| Backfill desligado por padrão e marcado à parte no log de offset | Backfill automático ao iniciar | ADR 0005 §5 |
| `bid_vol`/`ask_vol` = 0 em `broker/`, documentado como dado inexistente | Repetir o volume do tick nos dois lados | não — é limitação registrada, não escolha |
| Dia útil ausente deixa de contar como defeito estrutural | Manter `days_missing` em `clean` | não — era erro de critério, corrigido |
| `--validate-only` obrigatório para reprocessar | Tornar `write_raw` idempotente por sobrescrita | não — `raw/` é imutável por princípio (§10.2) |
| Versões fixadas em `requirements.txt` | Deixar solto | não — §10.2 exige reconstituibilidade |

### Correções aplicadas ao `CLAUDE.md`

1. **§10.7 — critério de fuso reescrito.** `TimeCurrent()` vs `TimeGMT()` mede o offset no
   instante da chamada: entrega uma estação só, e um servidor que desloca uma hora em março
   produz leitura idêntica a um que nunca desloca. O critério era satisfeito por uma medição
   incapaz de detectar DST. Substituído por ancoragem da borda do intervalo diário à manutenção
   do COMEX, medida em janeiro **e** em julho. §18 item 6 alinhada.
2. **§10.1 — comando de aquisição atualizado** para `-bs 10 -bp 500` e para a corrida única na
   ordem 2025 → 2024 → 2023 → 2022, com o motivo da ordem registrado.
3. **§7 Gate 1 — a escolha de T marcada como pendência aberta.** A revisão removeu
   `T_min = (c/kσ)²` sem substituí-la; "1 a 30 barras" é faixa de busca, não critério. Varrer os
   30 e ficar com o melhor é teste múltiplo disfarçado de metodologia.
4. **§5.2 — `confidence` marcado como sem semântica definida**, com instrução de não usar o campo.
5. **§4.1 — `tools/` devolvido à árvore.** A §12 inteira depende de `tools/setup/junctions.ps1`.
6. **§12.1 — três furos do `.gitignore` fechados**: `.dukascopy-cache/` ausente da lista e não
   alcançado por nenhuma outra regra; `*.csv` matando os CSVs que a regra 4 autoriza em
   `reports/`; `local_paths.*` matando o próprio modelo versionado.

## Perguntas para o chat

1. **Qual o critério de escolha de T no Gate 1?** É a pendência que trava o gate inteiro.
   Removeram a fórmula sem colocar nada no lugar.
2. **O que `confidence` significa?** Segue sem definição. Nenhum código usa o campo, por decisão
   registrada no `STATE.md`.
3. **A tese mecânica.** Continua não escrita, e é o passo 3 da §18.
4. **`2026-04-03` (Sexta-feira Santa) deve ser excluído dos blocos de teste ou tratado como dia
   normal de zero trades?** O validador agora o apresenta como pergunta em vez de veredicto, mas
   a política precisa ser decidida antes de existir walk-forward.
5. **A borda de `2026-07-31 20:59:02.882 UTC`** cai exatamente no início do intervalo diário do
   símbolo. É a primeira evidência independente a favor da hipótese de servidor UTC+0 da §10.7 —
   mas é uma estação só, e por isso mesmo não substitui o teste das duas.

## Estado da árvore

- [x] `git status` limpo
- [x] Branch mergeada em `main`
- [x] `STATE.md` atualizado e sessão fechada
- [x] Push feito
