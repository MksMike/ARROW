# Validação de `raw/` — xauusd-2022-08_2026-08

> Gerado por `research/lib/validate.py`. Nenhum número aqui é estimativa:
> todos saíram da leitura do dado.

| Campo | Valor |
|---|---|
| Linhas | 240,344,662 |
| Primeiro tick | 2022-08-01 00:00:00.143000+00:00 |
| Último tick | 2026-07-31 20:59:02.882000+00:00 |
| Dias com dado | 1245 |

## Defeitos

| Verificação | Ocorrências | Gravidade |
|---|---|---|
| Linhas idênticas duplicadas | 0 | remover em `curated/` |
| `ts` repetido (mesmo ms) | 0 | normal em feed de tick |
| `ts` retrocedendo | 0 | **estrutural** |
| `ask < bid` | 0 | **estrutural** |
| Preço ≤ 0 | 0 | **estrutural** |

## Cobertura — 4 dia(s) útil(eis) sem nenhum tick

**Não é veredicto, é pergunta.** Um destes é feriado de mercado, e nesse caso a
ausência é o dado correto: o ouro não negocia na Sexta-feira Santa, no Natal nem
no Ano-Novo. Outro é buraco de coleta, e aí contamina em silêncio qualquer bloco
in-sample que o contenha. Os dois se parecem aqui; separá-los é decisão de quem
monta o teste, e precisa ser tomada olhando a lista, não ignorando-a.

```
2023-04-07
2024-03-29
2025-04-18
2026-04-03
```

## Dias anormalmente magros — 8

Comparados contra a mediana do MESMO dia da semana, não contra um limiar
único: o domingo tem sessão parcial e roda numa ordem de grandeza abaixo de
um pregão. Entram aqui os dias abaixo de 20% da mediana do
seu dia da semana, ou abaixo do piso absoluto de 1,000 ticks.

Não são necessariamente defeito — meio-feriado do ouro é real. Mas nenhum
deles deve entrar num bloco de teste sem ter sido olhado.

| Dia | Ticks | Mediana do dia da semana | Motivo |
|---|---|---|---|
| 2022-12-26 | 2,505 | 208,485 | 1% da mediana de Monday |
| 2023-01-02 | 4,650 | 208,485 | 2% da mediana de Monday |
| 2023-12-25 | 1,993 | 208,485 | 1% da mediana de Monday |
| 2024-01-01 | 2,220 | 208,485 | 1% da mediana de Monday |
| 2024-12-25 | 1,754 | 219,334 | 1% da mediana de Wednesday |
| 2025-01-01 | 2,093 | 219,334 | 1% da mediana de Wednesday |
| 2025-12-25 | 9,779 | 224,895 | 4% da mediana de Thursday |
| 2026-01-01 | 7,245 | 224,895 | 3% da mediana de Thursday |

## Ticks por dia

![ticks por dia](xauusd-2022-08_2026-08-ticks-por-dia.png)

## Veredicto

**Sem defeito estrutural.**

Ausência de defeito estrutural não é atestado de qualidade do dado. Diz apenas
que o arquivo é internamente consistente; se ele representa o mercado é outra
pergunta, e quem responde é a medição do gap de fonte (`CLAUDE.md` §11.2).