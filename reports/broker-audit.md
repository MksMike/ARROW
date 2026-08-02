# Auditoria do broker — spec do símbolo e fuso

> Gerado por `research/audit_broker.py` a partir da saída do
> `MQL5/Scripts/ARROW/DataAudit.mq5`. Nenhum número aqui é estimativa.

## Veredicto de fuso: **SERVIDOR FIXO**

| Estação | Dias com parada | Hora de início (moda) |
|---|---|---|
| inverno_janeiro | 15 | **21:58** |
| verao_julho | 16 | **20:58** |

A parada desliza **1 hora** entre julho (20:58) e janeiro
(21:58). O relógio do servidor **não observa DST** — ele é fixo, e o
deslocamento observado é o DST americano se movendo por baixo dele.

**A hipótese servidor = UTC da §10.7 se sustenta**, e o alinhamento com a Dukascopy
(que é UTC) pode ser feito por constante. A máscara de sessão de
`research/lib/sessions.py` está correta o ano inteiro.

> **Por que não `TimeCurrent()` vs `TimeGMT()`:** essas duas funções medem o offset no
> instante da chamada. Entregam uma estação só, e um servidor que desloca uma hora em
> março produz leitura idêntica a um que nunca desloca.

## Spec do símbolo

A tabela da §13 é premissa não verificada. Estes são os valores que o servidor responde.

### `XAUUSDm`

| Campo | Valor | Unidade |
|---|---|---|
| `digits` | 3 |  |
| `point` | 0.00100000 |  |
| `trade_tick_value` | 15.74270000 | JPY |
| `trade_tick_size` | 0.00100000 |  |
| `trade_contract_size` | 100.00 |  |
| `currency_base` | XAU |  |
| `currency_profit` | USD |  |
| `currency_margin` | XAU |  |
| `volume_min` | 0.01 |  |
| `volume_max` | 200.00 |  |
| `volume_step` | 0.01 |  |
| `stops_level` | 0 | points |
| `freeze_level` | 0 | points |
| `spread_current` | 260 | points |
| `spread_float` | true |  |
| `swap_long` | -482.5000 |  |
| `swap_short` | 0.0000 |  |
| `swap_mode` | 1 |  |
| `swap_rollover3days` | 3 |  |
| `chart_mode` | 0 |  |
| `trade_exemode` | 2 |  |
| `trade_calc_mode` | 0 |  |
| `trade_mode` | 4 |  |
| `filling_mode` | 3 |  |
| `expiration_mode` | 15 |  |
| `order_mode` | 127 |  |
| `margin_initial` | 0.0000 |  |
| `margin_maintenance` | 0.0000 |  |
| `path` | Standard\Forex\XAUUSDm |  |
| `description` | Gold vs US Dollar |  |
| `margem_1lote_compra` | 31844.00 | JPY |
| `margem_1lote_venda` | 31830.00 | JPY |
| `lucro_1lote_move_1usd` | 15743.00 | JPY |
| `m1_primeira_barra` | 2014.01.14 00:00 |  |
| `m1_barras` | 3265408 |  |
| `tick_primeira_data` | 2014.01.14 00:00 |  |

### Relógio

| Campo | Valor | Unidade |
|---|---|---|
| `offset_instantaneo_servidor_menos_gmt` | 0 | segundos |
| `hora_servidor` | 2026.08.02 11:38:00 |  |
| `hora_gmt` | 2026.08.02 11:38:00 |  |
