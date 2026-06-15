"""Extract boundary-aligned, non-overlapping byte chunks from a tensor buffer."""

from __future__ import annotations

from typing import Iterator


def _check(chunk_size: int) -> None:
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be > 0, got {chunk_size}")


def n_chunks(total_bytes: int, chunk_size: int, *, drop_last_partial: bool = True) -> int:
    _check(chunk_size)
    full = total_bytes // chunk_size
    if drop_last_partial:
        return full
    return full + (1 if total_bytes % chunk_size else 0)


def iter_chunks(buf, chunk_size: int, *, drop_last_partial: bool = True) -> Iterator[bytes]:
    _check(chunk_size)
    mv = memoryview(buf)
    total = len(mv)
    offset = 0
    while offset + chunk_size <= total:
        yield bytes(mv[offset : offset + chunk_size])
        offset += chunk_size
    if not drop_last_partial and offset < total:
        yield bytes(mv[offset:total])
