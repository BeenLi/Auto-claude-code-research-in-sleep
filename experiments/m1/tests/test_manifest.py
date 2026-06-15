"""Measurement-row schema, chunk-id naming, and JSONL I/O (M1_CHECKLIST §4.1.1, §1.3.4)."""

import manifest


def _row(**kw):
    base = dict(
        chunk_id="prefill_K_bf16_7b_8k_layer16_1MB_seed42",
        phase="prefill",
        tensor_type="K",
        dtype="bf16",
        model_size="7b",
        seq_len=8192,
        layer_idx=16,
        chunk_size_bytes=1048576,
        shannon_entropy=6.82,
        codec="deflate",
        level=6,
        original_size=1048576,
        compressed_size=523456,
        ratio=0.499,
        compress_time_us_p50=2340.0,
        compress_throughput_mbps=448.0,
        is_bit_exact=True,
        generation_method="synthetic",
    )
    base.update(kw)
    return manifest.MeasurementRow(**base)


def test_make_chunk_id_matches_checklist_example():
    cid = manifest.make_chunk_id(
        phase="prefill",
        tensor_type="K",
        dtype="bf16",
        model_size="7b",
        seq_len=8192,
        layer_idx=16,
        chunk_size_bytes=1048576,
        seed=42,
    )
    assert cid == "prefill_K_bf16_7b_8k_layer16_1MB_seed42"


def test_humanize_sizes():
    assert manifest.humanize_bytes(4096) == "4KB"
    assert manifest.humanize_bytes(262144) == "256KB"
    assert manifest.humanize_bytes(16777216) == "16MB"


def test_row_to_dict_has_all_schema_fields():
    d = _row().to_dict()
    for field in manifest.SCHEMA_FIELDS:
        assert field in d
    assert set(d.keys()) == set(manifest.SCHEMA_FIELDS)


def test_jsonl_roundtrip(tmp_path):
    rows = [_row(), _row(codec="lz4", level=9, generation_method="captured")]
    path = tmp_path / "corpus.jsonl"
    manifest.write_jsonl(rows, path)
    assert manifest.read_jsonl(path) == [r.to_dict() for r in rows]


def test_jsonl_appends_across_calls(tmp_path):
    # streaming corpus writes incrementally; appends must accumulate
    path = tmp_path / "corpus.jsonl"
    manifest.write_jsonl([_row()], path)
    manifest.write_jsonl([_row(codec="zstd", level=3)], path, append=True)
    assert len(manifest.read_jsonl(path)) == 2
