"""Measurement-row schema, chunk-id naming, and JSONL I/O for the M1 corpus.

JSONL (not parquet) is the portable on-disk format so the Mac dev venv needs no
pyarrow; a separate step on the box converts the accumulated JSONL to parquet
(M1_CHECKLIST §4.1.1) for analysis.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path

SCHEMA_FIELDS = [
    "chunk_id",
    "phase",
    "tensor_type",
    "dtype",
    "model_size",
    "seq_len",
    "layer_idx",
    "chunk_size_bytes",
    "shannon_entropy",
    "codec",
    "level",
    "original_size",
    "compressed_size",
    "ratio",
    "compress_time_us_p50",
    "compress_throughput_mbps",
    "is_bit_exact",
    "generation_method",
]

_KB = 1024
_MB = 1024 * 1024


def humanize_bytes(n: int) -> str:
    if n >= _MB and n % _MB == 0:
        return f"{n // _MB}MB"
    if n >= _KB and n % _KB == 0:
        return f"{n // _KB}KB"
    return f"{n}B"


def _humanize_seq(seq_len: int) -> str:
    return f"{seq_len // 1024}k" if seq_len % 1024 == 0 else str(seq_len)


def make_chunk_id(
    *,
    phase: str,
    tensor_type: str,
    dtype: str,
    model_size: str,
    seq_len: int,
    layer_idx: int,
    chunk_size_bytes: int,
    seed: int,
) -> str:
    return (
        f"{phase}_{tensor_type}_{dtype}_{model_size}_{_humanize_seq(seq_len)}"
        f"_layer{layer_idx}_{humanize_bytes(chunk_size_bytes)}_seed{seed}"
    )


@dataclass
class MeasurementRow:
    chunk_id: str
    phase: str
    tensor_type: str
    dtype: str
    model_size: str
    seq_len: int
    layer_idx: int
    chunk_size_bytes: int
    shannon_entropy: float
    codec: str
    level: object
    original_size: int
    compressed_size: int
    ratio: float
    compress_time_us_p50: float
    compress_throughput_mbps: float
    is_bit_exact: bool
    generation_method: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def write_jsonl(rows, path, *, append: bool = False) -> None:
    path = Path(path)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as f:
        for row in rows:
            d = row.to_dict() if isinstance(row, MeasurementRow) else row
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


def read_jsonl(path) -> list[dict]:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
