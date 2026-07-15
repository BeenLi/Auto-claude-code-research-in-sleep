"""The pre-registered E0 decision rule (EVALUATION_CONTRACT_E0.md), implemented verbatim:

- medians per (model, dtype, method, variant)
- claim statistic: worst-of-modern {qwen, llama} for chan/chan_bt, worst-of-all for raw/bt
- per-dtype best path chosen under V3; GO-A iff alpha_V3 <= 0.75 AND delta_V3 <= +0.03
- STRONG_GO both paths / GO_A one path / GO_A_WEAK (delta <= 0.05) / NO_GO
- V0 must reproduce locked alphas within +-0.005
"""

import pytest

import analyze_e0

GPT2, QWEN, LLAMA = "gpt2", "qwen2.5-7b", "llama-3.1-8b"


def _row(model, dtype, method, alphas):
    return {"model_size": model, "dtype": dtype, "method": method,
            "generation_method": "captured", "bit_exact": True, "alphas": alphas}


def _rows(spec):
    """spec: {(model, dtype, method): {variant: alpha}} -> duplicated rows (median = value)."""
    rows = []
    for (model, dtype, method), alphas in spec.items():
        rows += [_row(model, dtype, method, alphas)] * 2
    return rows


def _alphas(v0, v3, v4=None):
    return {"V0": v0, "V1": v0 + 0.005, "V2": v0 + 0.005, "V3": v3,
            "V4": v4 if v4 is not None else v3 + 0.08, "V5": v0 + 0.06}


class TestClaimStatistic:
    def test_chan_uses_worst_of_modern_only(self):
        spec = {
            (GPT2, "fp8_e5m2", "chan"): _alphas(0.724, 0.744),
            (QWEN, "fp8_e5m2", "chan"): _alphas(0.704, 0.714),
            (LLAMA, "fp8_e5m2", "chan"): _alphas(0.699, 0.719),
        }
        res = analyze_e0.analyze(_rows(spec))
        # worst of {qwen 0.714, llama 0.719} = 0.719; gpt2 0.744 excluded
        assert res["claim_stats"][("fp8_e5m2", "chan", "V3")] == pytest.approx(0.719)

    def test_raw_and_bt_use_worst_of_all_models(self):
        spec = {
            (GPT2, "bf16", "byte_transpose"): _alphas(0.705, 0.735),
            (QWEN, "bf16", "byte_transpose"): _alphas(0.708, 0.718),
            (LLAMA, "bf16", "byte_transpose"): _alphas(0.706, 0.716),
        }
        res = analyze_e0.analyze(_rows(spec))
        assert res["claim_stats"][("bf16", "byte_transpose", "V3")] == pytest.approx(0.735)


def _full_spec(bf16_v3_delta, e5m2_v3_delta):
    """Both dtypes' claimable paths, with V3 = V0 + given delta on every model."""
    spec = {}
    for model, bf16_bt, bf16_cbt, e5m2_raw, e5m2_chan in (
        (GPT2, 0.705, 0.697, 0.730, 0.724),
        (QWEN, 0.708, 0.671, 0.732, 0.704),
        (LLAMA, 0.706, 0.690, 0.730, 0.699),
    ):
        spec[(model, "bf16", "byte_transpose")] = _alphas(bf16_bt, bf16_bt + bf16_v3_delta)
        spec[(model, "bf16", "chan_bt")] = _alphas(bf16_cbt, bf16_cbt + bf16_v3_delta)
        spec[(model, "fp8_e5m2", "raw")] = _alphas(e5m2_raw, e5m2_raw + e5m2_v3_delta)
        spec[(model, "fp8_e5m2", "chan")] = _alphas(e5m2_chan, e5m2_chan + e5m2_v3_delta)
    return spec


class TestVerdict:
    def test_strong_go_when_both_dtypes_survive(self):
        res = analyze_e0.analyze(_rows(_full_spec(0.01, 0.01)))
        assert res["verdict"] == "STRONG_GO"

    def test_no_go_when_both_paths_blow_the_gate(self):
        # +0.06 delta fails (b) strict and weak on every path, and pushes alphas > 0.75
        res = analyze_e0.analyze(_rows(_full_spec(0.06, 0.06)))
        assert res["verdict"] == "NO_GO"

    def test_go_a_when_one_dtype_survives(self):
        res = analyze_e0.analyze(_rows(_full_spec(0.01, 0.06)))
        assert res["verdict"] == "GO_A"
        assert res["paths"]["bf16"]["passes"] is True
        assert res["paths"]["fp8_e5m2"]["passes"] is False

    def test_weak_zone_yields_go_a_weak(self):
        # delta +0.04: fails strict (b), alpha still <= 0.75 and delta <= 0.05 on bf16
        # (bf16 chan_bt qwen 0.671+0.04=0.711, llama 0.690+0.04=0.730 -> worst 0.730 <= 0.75)
        res = analyze_e0.analyze(_rows(_full_spec(0.04, 0.06)))
        assert res["verdict"] == "GO_A_WEAK"

    def test_best_path_chosen_under_v3(self):
        res = analyze_e0.analyze(_rows(_full_spec(0.01, 0.01)))
        # e5m2: chan V3 worst-of-modern = 0.714 beats raw worst-of-all = 0.742
        assert res["paths"]["fp8_e5m2"]["method"] == "chan"


class TestV0Reproduction:
    def test_flags_deviation_beyond_5em3(self):
        spec = {(QWEN, "bf16", "byte_transpose"): _alphas(0.708, 0.718)}
        ref = {(QWEN, "bf16", "byte_transpose"): 0.720}  # 0.012 off
        res = analyze_e0.analyze(_rows(spec), reference=ref)
        assert res["v0_reproduction"]["ok"] is False
        assert len(res["v0_reproduction"]["failures"]) == 1

    def test_passes_within_tolerance(self):
        spec = {(QWEN, "bf16", "byte_transpose"): _alphas(0.708, 0.718)}
        ref = {(QWEN, "bf16", "byte_transpose"): 0.7105}
        res = analyze_e0.analyze(_rows(spec), reference=ref)
        assert res["v0_reproduction"]["ok"] is True


class TestHygiene:
    def test_non_bit_exact_rows_are_rejected(self):
        rows = _rows({(QWEN, "bf16", "byte_transpose"): _alphas(0.708, 0.718)})
        rows[0]["bit_exact"] = False
        with pytest.raises(ValueError, match="bit_exact"):
            analyze_e0.analyze(rows)

    def test_synthetic_rows_are_excluded_from_claim_stats(self):
        rows = _rows({(QWEN, "bf16", "byte_transpose"): _alphas(0.708, 0.718)})
        synth_row = _row("7b", "bf16", "byte_transpose", _alphas(0.5, 0.5))
        synth_row["generation_method"] = "synthetic"
        res = analyze_e0.analyze(rows + [synth_row])
        assert res["claim_stats"][("bf16", "byte_transpose", "V3")] == pytest.approx(0.718)


class TestCLI:
    def test_main_reads_corpus_and_reference_and_writes_verdict(self, tmp_path):
        import json

        corpus = tmp_path / "rows.jsonl"
        rows = _rows({
            (QWEN, "bf16", "byte_transpose"): _alphas(0.708, 0.718),
            (LLAMA, "bf16", "byte_transpose"): _alphas(0.709, 0.719),
            (GPT2, "bf16", "byte_transpose"): _alphas(0.705, 0.715),
        })
        corpus.write_text("\n".join(json.dumps(r) for r in rows))
        ref = tmp_path / "ref.json"
        ref.write_text(json.dumps({
            f"{QWEN}|bf16|byte_transpose": 0.708,
            f"{LLAMA}|bf16|byte_transpose": 0.709,
            f"{GPT2}|bf16|byte_transpose": 0.705,
        }))
        out = tmp_path / "verdict.json"
        rc = analyze_e0.main(["--corpus", str(corpus), "--reference", str(ref), "--out", str(out)])
        assert rc == 0
        res = json.loads(out.read_text())
        assert res["verdict"] == "GO_A"
        assert res["v0_reproduction"]["ok"] is True
        # keys serialized human-readably
        assert "bf16|byte_transpose|V3" in res["claim_stats"]


def test_locked_reference_file_matches_m16_results():
    """locked_reference.json must be derivable from m1_6/m16_results.json medians."""
    import json
    from pathlib import Path

    here = Path(analyze_e0.__file__).resolve().parent
    ref = json.loads((here / "locked_reference.json").read_text())
    m16 = json.loads((here.parent / "m1_6" / "m16_results.json").read_text())["alpha_concat_medians"]
    for key, val in ref.items():
        model, dtype, method = key.split("|")
        assert m16[f"captured_{model}"][dtype][method] == val
    # the claimable set: 3 models x (bf16: raw/bt/chan_bt + e5m2: raw/chan) = 15 entries
    assert len(ref) == 15
