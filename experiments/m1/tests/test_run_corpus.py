"""Pure row-assembly used by the streaming corpus orchestrator."""

import m1_codecs
import manifest
import run_corpus
from synth import TensorSpec


def _spec():
    return TensorSpec(
        phase="prefill",
        tensor_type="K",
        dtype="bf16",
        num_heads=8,
        head_dim=64,
        seq_len=128,
        layer_idx=3,
        seed=42,
    )


def test_build_row_populates_full_schema():
    chunk = b"\x00\x01" * 2048  # 4096 bytes
    m = m1_codecs.measure(chunk, "deflate", 6)
    row = run_corpus.build_row(
        spec=_spec(),
        model_size="7b",
        chunk=chunk,
        measurement=m,
        generation_method="synthetic",
        seed=42,
    )
    d = row.to_dict()
    assert set(d) == set(manifest.SCHEMA_FIELDS)
    assert d["chunk_size_bytes"] == 4096
    assert d["phase"] == "prefill" and d["tensor_type"] == "K"
    assert d["model_size"] == "7b" and d["layer_idx"] == 3
    assert d["codec"] == "deflate" and d["level"] == 6
    assert d["generation_method"] == "synthetic"
    assert 0.0 <= d["shannon_entropy"] <= 8.0
    assert d["compress_time_us_p50"] > 0
    assert d["ratio"] == m.ratio


def test_build_row_chunk_id_is_descriptive():
    chunk = b"x" * 4096
    m = m1_codecs.measure(chunk, "none")
    row = run_corpus.build_row(
        spec=_spec(),
        model_size="7b",
        chunk=chunk,
        measurement=m,
        generation_method="synthetic",
        seed=42,
    )
    assert row.chunk_id == "prefill_K_bf16_7b_128_layer3_4KB_seed42"


def test_model_configs_have_known_scales():
    assert "7b" in run_corpus.MODEL_CONFIGS
    cfg = run_corpus.MODEL_CONFIGS["7b"]
    assert cfg["num_heads"] > 0 and cfg["head_dim"] > 0 and cfg["num_layers"] > 0
