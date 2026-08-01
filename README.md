# ARROW

Biblioteca de **sensores validados estatisticamente** para XAUUSD no M1 do MetaTrader 5, mais um
mecanismo de orquestração que os combina.

O produto final não é uma EA. É a biblioteca.

---

## O que este repositório é

Um projeto de pesquisa quantitativa com uma máquina de validação deliberadamente hostil ao
próprio autor. Cada sensor é uma hipótese isolada, testada contra um baseline aleatório, com
custo real aplicado, e arquivada com veredicto — **inclusive quando reprovada**.

As regras não são preferências de estilo. Estão em [CLAUDE.md](CLAUDE.md) e são normativas:

- **Sensor não executa.** A matemática vive num `.mqh`; ordens, risco e sessão vivem noutra
  camada. Um sensor nunca sabe que uma EA existe.
- **Saída adimensional.** Sob passeio aleatório, todo sensor tem `E[value] = 0` e `SD[value] = 1`.
  Sem escala comum não há intercambiabilidade e limiares não transferem.
- **O dia é a unidade estatística.** Trades no M1 são autocorrelacionados dentro do dia; contá-los
  como observações independentes infla a significância.
- **Custo é premissa.** Nenhum resultado sem spread aplicado é reportado, nem como preliminar.
- **Win rate não é evidência de nada.** Alvo curto com stop largo produz 85% de acerto e
  esperança negativa.
- **Zero martingale, grid ou recuperação por exposição.** Assunto encerrado por Monte Carlo.

## Onde olhar

| Arquivo | O que é |
|---|---|
| [STATE.md](STATE.md) | Estado vivo. Primeira leitura de qualquer sessão. Vence sobre memória. |
| [CLAUDE.md](CLAUDE.md) | A constituição. Normativa. |
| [docs/CONTEXT.md](docs/CONTEXT.md) | De onde as decisões vêm. |
| [docs/decisions/](docs/decisions/) | ADRs. Decisão sem ADR não é decisão, é sugestão. |
| [docs/sensors/](docs/sensors/) | Ficha e veredicto de cada sensor, aprovados e mortos. |
| [docs/sessions/](docs/sessions/) | Relatórios de sessão. Imutáveis. |

## Estado

Início. **Nenhum sensor validado, nenhuma EA, nenhuma medição.** Todo valor numérico que aparece
nos documentos é estimativa preliminar aguardando o `DataAudit`.

## Dados

O código é público; os dados não. Ticks da Dukascopy e qualquer dataset derivado ficam em `data/`,
fora do versionamento — redistribuição pode violar os termos da fonte, e o volume inviabiliza o
Git de qualquer forma. Credenciais, número de conta e nome de servidor de broker nunca entram
aqui.

## Ambiente

MetaTrader 5, XAUUSD M1. A pasta `MQL5` do terminal aponta para dentro deste repositório via
junctions criadas por `tools/setup/junctions.ps1`, que lê caminho e identidade da máquina de um
arquivo local não versionado. Nenhum caminho absoluto de máquina entra em arquivo versionado.

```powershell
Copy-Item tools\setup\local_paths.example.ps1 tools\setup\local_paths.ps1
# editar local_paths.ps1 com os caminhos desta máquina, então:
pwsh -File tools\setup\junctions.ps1
```
