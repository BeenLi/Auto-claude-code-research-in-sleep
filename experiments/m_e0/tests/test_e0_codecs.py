"""E0 hardware-encoder-proxy deflate variants (EVALUATION_CONTRACT_E0.md, table in
"Scope and method"). Each variant must stay a standard zlib stream (or a concatenation
of independent standard zlib streams for the 32KB-blocked ones) so the commodity-decode
claim is preserved."""

import os
import zlib

import numpy as np
import pytest

import e0_codecs


def _skewed(n: int, seed: int = 0) -> bytes:
    """Highly skewed byte distribution: dynamic Huffman should beat Z_FIXED clearly."""
    rng = np.random.default_rng(seed)
    return bytes(rng.choice([0, 1, 2, 255], size=n, p=[0.85, 0.10, 0.04, 0.01]).astype(np.uint8))


def _random(n: int, seed: int = 1) -> bytes:
    return bytes(np.random.default_rng(seed).integers(0, 256, size=n, dtype=np.uint8))


class TestVariantRegistry:
    def test_contract_variants_present(self):
        # V0..V5 exactly as pre-registered in EVALUATION_CONTRACT_E0.md
        assert set(e0_codecs.VARIANTS) == {"V0", "V1", "V2", "V3", "V4", "V5"}

    def test_v0_is_locked_alpha_baseline(self):
        v = e0_codecs.VARIANTS["V0"]
        assert v.level == 6 and v.strategy == "default" and v.block_size is None

    def test_v3_is_hw_dyn_proxy(self):
        v = e0_codecs.VARIANTS["V3"]
        assert v.level == 1 and v.strategy == "default" and v.block_size == 32 * 1024

    def test_v4_is_hw_static_proxy(self):
        v = e0_codecs.VARIANTS["V4"]
        assert v.level == 1 and v.strategy == "fixed" and v.block_size == 32 * 1024


class TestRoundtrip:
    @pytest.mark.parametrize("vid", ["V0", "V1", "V2", "V3", "V4", "V5"])
    @pytest.mark.parametrize("payload", ["skewed", "random", "empty_ish"])
    def test_bit_exact_roundtrip(self, vid, payload):
        data = {
            "skewed": _skewed(100_000),
            "random": _random(100_000),
            "empty_ish": b"\x00" * 100_000,
        }[payload]
        blob = e0_codecs.compress_variant(data, vid)
        assert e0_codecs.decompress_variant(blob, vid) == data

    @pytest.mark.parametrize("vid", ["V2", "V3", "V4"])
    def test_non_multiple_block_tail(self, vid):
        # 100_000 is not a multiple of 32768: tail block must roundtrip too
        data = _skewed(100_000)
        assert len(data) % (32 * 1024) != 0
        blob = e0_codecs.compress_variant(data, vid)
        assert e0_codecs.decompress_variant(blob, vid) == data


class TestStandardStreamProperty:
    def test_whole_chunk_variants_are_one_stock_zlib_stream(self):
        data = _skewed(100_000)
        for vid in ("V0", "V1", "V5"):
            blob = e0_codecs.compress_variant(data, vid)
            assert zlib.decompress(blob) == data  # stock decoder, no custom framing

    def test_blocked_variant_blocks_are_independent_stock_zlib_streams(self):
        # Independence = each 32KB block is its own complete zlib stream: a stock
        # decompressobj must terminate exactly at the block boundary and the next
        # stream must start there (this is what "no cross-block history" means, and
        # what lets a BF3-class engine decode block-by-block).
        data = _skewed(100_000)
        blob = e0_codecs.compress_variant(data, "V3")
        out, rest, n_streams = b"", blob, 0
        while rest:
            d = zlib.decompressobj()
            out += d.decompress(rest)
            assert d.eof, "each segment must be a complete stream"
            rest = d.unused_data
            n_streams += 1
        assert out == data
        assert n_streams == 4  # ceil(100_000 / 32768)


class TestHardwareProxySemantics:
    def test_fixed_strategy_loses_to_dynamic_on_skewed_bytes(self):
        # Z_FIXED uses the RFC1951 fixed Huffman table: on a highly skewed byte
        # distribution it must be strictly worse than dynamic Huffman at equal level.
        data = _skewed(200_000)
        dyn = len(e0_codecs.compress_variant(data, "V1"))
        fixed = len(e0_codecs.compress_variant(data, "V4"))
        assert fixed > dyn

    def test_blocking_severs_cross_block_history(self):
        # One 16KB random page repeated 8x: whole-chunk deflate reaps LZ matches at
        # 16KB distance; independent 32KB blocks only reap the intra-block repeat.
        page = _random(16 * 1024)
        data = page * 8
        whole = len(e0_codecs.compress_variant(data, "V1"))
        blocked = len(e0_codecs.compress_variant(data, "V3"))
        assert blocked > whole * 1.5

    def test_level1_weakens_match_search_vs_level6(self):
        # English-ish text with long-range redundancy: level 1 must not beat level 6.
        data = (b"the quick brown fox jumps over the lazy dog. " * 3000)[:100_000]
        l1 = len(e0_codecs.compress_variant(data, "V1"))
        l6 = len(e0_codecs.compress_variant(data, "V0"))
        assert l1 >= l6


class TestAlpha:
    def test_alpha_includes_container_overhead(self):
        # Random data is incompressible: every zlib segment adds container bytes, so
        # alpha > 1 and the blocked variant carries more overhead than whole-chunk.
        data = _random(64 * 1024)
        a_whole = e0_codecs.alpha(data, "V0")
        a_blocked = e0_codecs.alpha(data, "V3")
        assert a_whole > 1.0
        assert a_blocked > a_whole

    def test_alpha_matches_stock_zlib_for_v0(self):
        data = _skewed(64 * 1024)
        assert e0_codecs.alpha(data, "V0") == pytest.approx(
            len(zlib.compress(data, 6)) / len(data)
        )
