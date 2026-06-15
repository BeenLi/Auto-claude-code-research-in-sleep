"""Boundary-aligned chunk extraction (M1_CHECKLIST §1.3.2)."""

import pytest

import chunking


def test_drops_trailing_partial_by_default():
    buf = b"x" * 10000
    chunks = list(chunking.iter_chunks(buf, 4096))
    assert len(chunks) == 2
    assert all(len(c) == 4096 for c in chunks)


def test_keeps_trailing_partial_when_requested():
    buf = b"x" * 10000
    chunks = list(chunking.iter_chunks(buf, 4096, drop_last_partial=False))
    assert len(chunks) == 3
    assert len(chunks[-1]) == 10000 - 2 * 4096


def test_chunks_are_contiguous_and_nonoverlapping():
    buf = bytes(range(256)) * 8  # 2048 bytes
    chunks = list(chunking.iter_chunks(buf, 500))
    assert b"".join(chunks) == buf[: 500 * len(chunks)]


def test_n_chunks_matches_iteration():
    for drop in (True, False):
        assert chunking.n_chunks(10000, 4096, drop_last_partial=drop) == len(
            list(chunking.iter_chunks(b"x" * 10000, 4096, drop_last_partial=drop))
        )


def test_chunk_larger_than_buffer():
    assert list(chunking.iter_chunks(b"x" * 100, 4096)) == []
    kept = list(chunking.iter_chunks(b"x" * 100, 4096, drop_last_partial=False))
    assert len(kept) == 1 and len(kept[0]) == 100


def test_invalid_chunk_size_raises():
    with pytest.raises(ValueError):
        list(chunking.iter_chunks(b"x", 0))
    with pytest.raises(ValueError):
        chunking.n_chunks(100, -1)
