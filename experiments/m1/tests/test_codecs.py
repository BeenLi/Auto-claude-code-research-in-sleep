"""Codec matrix: compress/decompress/ratio/throughput with bit-exact roundtrip.

BF3-relevant codecs (deflate, lz4) plus reference codecs (zstd, none). Module is
named m1_codecs (not codecs) to avoid shadowing the stdlib codecs module.
"""

import os

import pytest

import m1_codecs as cdc

RANDOM = os.urandom(65536)
ZEROS = b"\x00" * 65536


def test_available_codecs_include_bf3_and_reference():
    av = cdc.available_codecs()
    for name in ("deflate", "lz4", "zstd", "none"):
        assert name in av


def test_none_codec_is_identity():
    m = cdc.measure(ZEROS, "none")
    assert m.compressed_size == m.original_size == len(ZEROS)
    assert m.ratio == 1.0
    assert m.is_bit_exact is True


@pytest.mark.parametrize("codec,level", [("deflate", 6), ("lz4", 0), ("zstd", 3)])
def test_roundtrip_bit_exact_on_random(codec, level):
    blob = cdc.compress(RANDOM, codec, level)
    assert cdc.decompress(blob, codec) == RANDOM


@pytest.mark.parametrize("codec,level", [("deflate", 9), ("lz4", 9), ("zstd", 19)])
def test_low_entropy_data_compresses(codec, level):
    m = cdc.measure(ZEROS, codec, level)
    assert m.is_bit_exact is True
    assert m.ratio < 0.5


def test_high_entropy_data_barely_compresses():
    m = cdc.measure(RANDOM, "deflate", 9)
    assert m.ratio > 0.9


def test_measure_reports_throughput_and_ratio_definition():
    m = cdc.measure(ZEROS, "zstd", 3)
    assert m.compress_throughput_mbps > 0
    assert m.ratio == pytest.approx(m.compressed_size / m.original_size)
    assert m.codec == "zstd" and m.level == 3


def test_unknown_codec_raises():
    with pytest.raises(ValueError):
        cdc.compress(b"x", "brotli", 1)
    with pytest.raises(ValueError):
        cdc.measure(b"x", "brotli")


def test_representative_levels():
    assert cdc.codec_levels("deflate") == [1, 6, 9]
    assert cdc.codec_levels("zstd") == [1, 3, 19]
    assert cdc.codec_levels("lz4") == [0, 9]
