"""Conversão Dukascopy CSV → `data/raw/` em Parquet particionado.

`raw/` é **imutável depois de escrito** (ADR 0005 §2). Este módulo é o único
que escreve nela. Nenhuma transformação de conteúdo acontece aqui além de
renomear colunas e tipar: o filtro de sessão, a substituição de spread e a
agregação em barras são camadas posteriores, cada uma com seu próprio código
versionado.

Por que Parquet particionado por mês e não o CSV: um único ano de tick de
XAUUSD passa de 3 GB em CSV. `pd.read_csv` sobre isso inviabiliza iteração, e
a pesquisa depende de iterar. Particionar por ano/mês permite carregar só o
bloco de interesse.

O CSV do `dukascopy-node` vem como::

    timestamp,askPrice,bidPrice,askVolume,bidVolume
    1659312000143,1762.516,1762.078,0.00012,0.00018

Duas armadilhas nesse cabeçalho, ambas silenciosas se ignoradas:

* **`ask` vem ANTES de `bid`.** Ler posicionalmente inverte os dois e produz
  um deslocamento de um spread inteiro, com o sinal trocado, em todo o
  dataset. Aqui as colunas são lidas por nome, nunca por posição.
* **`timestamp` é epoch em MILISSEGUNDOS, UTC.** Tratar como segundos joga
  tudo para 1970.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

log = logging.getLogger(__name__)

# Mapeamento explícito CSV → esquema de `raw/` (ADR 0005 §2).
# Escrito por nome justamente para não depender da ordem das colunas.
_COLUMN_MAP = {
    "timestamp": "ts",
    "bidPrice": "bid",
    "askPrice": "ask",
    "bidVolume": "bid_vol",
    "askVolume": "ask_vol",
}

# Esquema de `raw/`. Fixo — é contrato entre esta camada e todas as seguintes.
RAW_SCHEMA = pa.schema(
    [
        pa.field("ts", pa.timestamp("ms", tz="UTC")),
        pa.field("bid", pa.float64()),
        pa.field("ask", pa.float64()),
        pa.field("bid_vol", pa.float32()),
        pa.field("ask_vol", pa.float32()),
    ]
)

# Um ano de tick não cabe confortavelmente na memória. Ler em pedaços e
# agrupar por mês antes de escrever.
DEFAULT_CHUNK_ROWS = 5_000_000


@dataclass
class LoadStats:
    """O que a conversão viu. Vira relatório; não é decorativo."""

    source: str
    rows_read: int = 0
    rows_written: int = 0
    partitions: int = 0

    @property
    def rows_dropped(self) -> int:
        return self.rows_read - self.rows_written

    def __str__(self) -> str:
        return (
            f"{self.source}: {self.rows_read:,} lidas, "
            f"{self.rows_written:,} escritas, "
            f"{self.rows_dropped:,} descartadas, "
            f"{self.partitions} partições"
        )


def read_dukascopy_csv(
    path: str | Path, chunk_rows: int = DEFAULT_CHUNK_ROWS
) -> Iterator[pd.DataFrame]:
    """Lê o CSV em pedaços, já com nomes e tipos de `raw/`.

    Não valida nada — validação é responsabilidade de `validate.py`, para que
    a conversão e o julgamento sobre a qualidade do dado fiquem separados.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV não encontrado: {path}")

    reader = pd.read_csv(
        path,
        usecols=list(_COLUMN_MAP.keys()),
        dtype={
            "timestamp": "int64",
            "bidPrice": "float64",
            "askPrice": "float64",
            "bidVolume": "float32",
            "askVolume": "float32",
        },
        chunksize=chunk_rows,
    )

    for chunk in reader:
        chunk = chunk.rename(columns=_COLUMN_MAP)
        # epoch em MILISSEGUNDOS, UTC — ver docstring do módulo.
        chunk["ts"] = pd.to_datetime(chunk["ts"], unit="ms", utc=True)
        yield chunk[["ts", "bid", "ask", "bid_vol", "ask_vol"]]


def write_raw(
    frame: pd.DataFrame,
    raw_root: str | Path,
    *,
    compression: str = "zstd",
) -> int:
    """Escreve um DataFrame em `raw/year=YYYY/month=MM/`.

    Devolve o número de partições tocadas. Append-only por construção: cada
    chamada gera arquivos com nome único dentro da partição, então reprocessar
    um CSV **duplica** em vez de sobrescrever. Isso é deliberado — `raw/` é
    imutável, e apagar é uma decisão explícita de quem opera, não um efeito
    colateral de rodar o loader duas vezes.
    """
    raw_root = Path(raw_root)
    if frame.empty:
        return 0

    frame = frame.copy()
    frame["year"] = frame["ts"].dt.year.astype("int32")
    frame["month"] = frame["ts"].dt.month.astype("int32")

    touched = 0
    for (year, month), part in frame.groupby(["year", "month"], sort=True):
        target = raw_root / f"year={year}" / f"month={month:02d}"
        target.mkdir(parents=True, exist_ok=True)

        table = pa.Table.from_pandas(
            part[["ts", "bid", "ask", "bid_vol", "ask_vol"]],
            schema=RAW_SCHEMA,
            preserve_index=False,
        )

        # Nome único por bloco: o loader pode ser chamado em pedaços e não
        # deve sobrescrever o que já está na partição.
        seq = len(list(target.glob("part-*.parquet")))
        out = target / f"part-{seq:05d}.parquet"
        pq.write_table(table, out, compression=compression)

        touched += 1
        log.debug("escrito %s (%d linhas)", out, len(part))

    return touched


def load_csv_to_raw(
    csv_path: str | Path,
    raw_root: str | Path,
    *,
    chunk_rows: int = DEFAULT_CHUNK_ROWS,
    compression: str = "zstd",
) -> LoadStats:
    """Converte um CSV inteiro para `raw/`. Ponto de entrada normal."""
    csv_path = Path(csv_path)
    stats = LoadStats(source=csv_path.name)

    for chunk in read_dukascopy_csv(csv_path, chunk_rows=chunk_rows):
        stats.rows_read += len(chunk)
        stats.partitions += write_raw(chunk, raw_root, compression=compression)
        stats.rows_written += len(chunk)
        log.info("%s: %d linhas processadas", csv_path.name, stats.rows_read)

    return stats


def read_raw(
    raw_root: str | Path,
    *,
    year: int | None = None,
    month: int | None = None,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Lê `raw/` de volta, opcionalmente restrito a um ano/mês.

    Restringir é o caso normal: carregar quatro anos de tick de uma vez é
    justamente o que a partição existe para evitar.
    """
    raw_root = Path(raw_root)
    if not raw_root.exists():
        raise FileNotFoundError(f"raw/ não existe: {raw_root}")

    if year is not None and month is not None:
        source = raw_root / f"year={year}" / f"month={month:02d}"
    elif year is not None:
        source = raw_root / f"year={year}"
    else:
        source = raw_root

    if not source.exists():
        raise FileNotFoundError(f"partição não existe: {source}")

    table = pq.read_table(source, columns=columns)
    frame = table.to_pandas()

    # A ordem entre arquivos de uma partição não é garantida pelo Parquet.
    # Toda camada seguinte assume `ts` crescente.
    if "ts" in frame.columns:
        frame = frame.sort_values("ts", kind="stable").reset_index(drop=True)

    return frame
