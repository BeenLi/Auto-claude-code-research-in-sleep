"""E0 sweep driver: synthetic corpus leg (real-KV capture is glue, validated on the box
— same convention as m1_5/m1_6)."""

import json

import run_e0


def test_run_synthetic_writes_variant_rows_all_bit_exact(tmp_path):
    out = tmp_path / "e0_synth.jsonl"
    summary = run_e0.run(
        out_path=out,
        models=["tiny"],
        dtypes=["bf16", "fp8_e5m2"],
        phases=["prefill"],
        tensor_types=["K"],
        seq_lens=[4096],
        layer_fracs=[0.0],
        chunk_sizes=[262144],
        methods=("raw", "byte_transpose", "chan"),
        seeds=[42],
        max_chunks_per_config=1,
    )
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    assert summary["bit_exact_failures"] == 0
    assert summary["rows_written"] == len(rows) > 0
    # every row carries all six pre-registered variants and analyze-ready keys
    for r in rows:
        assert set(r["alphas"]) == {"V0", "V1", "V2", "V3", "V4", "V5"}
        assert r["generation_method"] == "synthetic"
        for key in ("model_size", "dtype", "method", "chunk_size_bytes", "bit_exact", "seed"):
            assert key in r
    assert {r["method"] for r in rows} == {"raw", "byte_transpose", "chan"}
    assert {r["dtype"] for r in rows} == {"bf16", "fp8_e5m2"}


def test_rows_feed_analyze_directly(tmp_path):
    import analyze_e0

    out = tmp_path / "e0_synth.jsonl"
    run_e0.run(
        out_path=out, models=["tiny"], dtypes=["bf16"], phases=["prefill"],
        tensor_types=["K"], seq_lens=[4096], layer_fracs=[0.0], chunk_sizes=[262144],
        methods=("raw", "byte_transpose"), seeds=[42], max_chunks_per_config=1,
    )
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    res = analyze_e0.analyze(rows)  # synthetic-only: no claim stats, no crash
    assert res["claim_stats"] == {}
    assert ("tiny", "bf16", "byte_transpose", "V3") in res["synthetic_medians"]
