"""E0b: NetZIP-algorithm (MICRO'25 Zenodo artifact, MIT) ported to our KV corpus.

Reimplemented with numpy+ml_dtypes to replicate the artifact's torch semantics exactly
(compression_ratio_calculation.py): bit_group_bfloat16, byte_group_bfloat16,
difference_encode_bfloat16 with a 1st-percentile base. Declared adaptations (contract
E0b): the cross-iteration diff arms are N/A for KV (no previous iteration); the min-base
arm uses the SAME buffer's 1st percentile (intra-buffer base). An on-box equivalence
check against the artifact's own torch code guards the port."""

import numpy as np
import pytest

import netzip_kv


def _bf16_chunk(n=4096, seed=7) -> bytes:
    import ml_dtypes

    rng = np.random.default_rng(seed)
    return rng.standard_normal(n).astype(ml_dtypes.bfloat16).tobytes()


class TestByteGroup:
    def test_low_bytes_then_high_bytes(self):
        # artifact: arr_bytes[:,0] (low) concat arr_bytes[:,1] (high), little-endian int16
        data = np.array([0x0201, 0x0403], dtype="<i2").tobytes()  # bytes: 01 02 03 04
        assert netzip_kv.byte_group(data) == bytes([0x01, 0x03, 0x02, 0x04])

    def test_size_preserved(self):
        data = _bf16_chunk()
        assert len(netzip_kv.byte_group(data)) == len(data)


class TestBitGroup:
    def test_size_preserved(self):
        data = _bf16_chunk()
        assert len(netzip_kv.bit_group(data)) == len(data)

    def test_plane_structure_known_answer(self):
        # 8 values of 0x0001: bit-plane 0 is all-ones (packs to one 0xFF byte,
        # bitorder little), planes 1..15 all zero.
        data = np.full(8, 1, dtype="<i2").tobytes()
        out = netzip_kv.bit_group(data)
        assert len(out) == 16
        assert out[0] == 0xFF
        assert set(out[1:]) == {0}


class TestDiffMin:
    def test_base_is_first_percentile_of_same_buffer(self):
        data = _bf16_chunk()
        base = netzip_kv.min_base(data)
        import ml_dtypes

        vals = np.frombuffer(data, dtype=ml_dtypes.bfloat16).astype(np.float32)
        assert base == pytest.approx(np.percentile(vals, 1))

    def test_output_size_preserved(self):
        data = _bf16_chunk()
        assert len(netzip_kv.diff_min(data)) == len(data)


class TestMeasure:
    def test_alphas_for_all_arms_and_codecs(self):
        data = _bf16_chunk(65536)
        rows = netzip_kv.measure(data)
        arms = {r["situation"] for r in rows}
        assert {"original", "bit_grouped", "byte_grouped",
                "diff_min_encoded", "diff_min_bit_grouped", "diff_min_byte_grouped"} <= arms
        codecs = {r["codec"] for r in rows}
        assert {"lz4-1", "zlib-1", "zlib-6", "zstd-1"} <= codecs
        for r in rows:
            assert 0 < r["alpha"] < 2

    def test_byte_grouped_zlib6_equals_our_byte_transpose_alpha(self):
        # their byte_group IS a 2-byte SoA de-interleave; under the same codec it must
        # yield the same compressed size as our layout byte_transpose (plane order may
        # differ low/high-first, so compare against both plane orders' min/max window)
        import zlib

        import layout

        data = _bf16_chunk(65536)
        theirs = len(zlib.compress(netzip_kv.byte_group(data), 6))
        ours = len(zlib.compress(layout.transform(data, "bf16", "byte_transpose", head_dim=64), 6))
        assert abs(theirs - ours) / ours < 0.02  # identical mechanism, order-of-planes tolerance
