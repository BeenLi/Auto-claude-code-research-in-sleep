"""TDD for the M1.5 analysis + go/no-go.

The milestone question: does an exponent-grouping transform move any dtype across the
0.75 profitability gate that M1 measured on RAW bytes — and does it survive on real
captured KV (not just the standard-normal synthetic generator, which inflates the
exponent plane)? The verdict is therefore decided on CAPTURED data; synthetic is breadth.
"""

import analyze_split as asx


def _rec(gen, dtype, raw, best, method="byte_transpose", perplane=None):
    return {
        "generation_method": gen, "dtype": dtype,
        "raw_alpha": raw, "best_split_alpha": best,
        "best_method": method, "best_perplane_alpha": perplane,
    }


def test_classify_rehabilitated_when_split_crosses_075():
    assert asx.classify(raw=0.80, split=0.70) == "rehabilitated"


def test_classify_improved_when_better_but_not_crossing():
    assert asx.classify(raw=0.80, split=0.755) == "improved"


def test_classify_regressed_when_split_worse():
    assert asx.classify(raw=0.716, split=0.843) == "regressed"


def test_classify_neutral_when_within_margin():
    assert asx.classify(raw=0.792, split=0.790) == "neutral"


def test_verdict_green_requires_rehabilitation_on_captured():
    recs = [
        _rec("captured", "bf16", 0.80, 0.70),       # crosses 0.75 on real KV
        _rec("captured", "fp8_e5m2", 0.73, 0.84, "bitplane"),  # split hurts fp8
    ]
    verdict, reason = asx.decide(recs)
    assert verdict == "GREEN"
    assert "bf16" in reason


def test_verdict_yellow_when_rehab_only_synthetic_not_captured():
    recs = [
        _rec("synthetic", "bf16", 0.792, 0.695),   # crosses on synthetic
        _rec("captured", "bf16", 0.80, 0.755),     # only improves on real KV, doesn't cross
    ]
    verdict, reason = asx.decide(recs)
    assert verdict == "YELLOW"


def test_verdict_red_when_no_captured_improvement():
    recs = [
        _rec("captured", "bf16", 0.80, 0.805),
        _rec("captured", "fp8_e5m2", 0.73, 0.84, "bitplane"),
    ]
    verdict, reason = asx.decide(recs)
    assert verdict == "RED"


def test_aggregate_picks_best_method_and_separates_generation():
    rows = [
        # captured bf16: byte_transpose 0.70 beats bitplane 0.69? pick the MIN (best)
        {"generation_method": "captured", "dtype": "bf16", "method": "byte_transpose",
         "alpha_raw": 0.80, "alpha_concat": 0.71, "alpha_perplane": None},
        {"generation_method": "captured", "dtype": "bf16", "method": "bitplane",
         "alpha_raw": 0.80, "alpha_concat": 0.69, "alpha_perplane": 0.69},
        {"generation_method": "synthetic", "dtype": "bf16", "method": "byte_transpose",
         "alpha_raw": 0.792, "alpha_concat": 0.701, "alpha_perplane": None},
    ]
    agg = asx.aggregate(rows)
    cap = [r for r in agg if r["generation_method"] == "captured" and r["dtype"] == "bf16"][0]
    assert cap["best_split_alpha"] == 0.69
    assert cap["best_method"] == "bitplane"
    assert abs(cap["raw_alpha"] - 0.80) < 1e-9
    # synthetic kept separate
    assert any(r["generation_method"] == "synthetic" for r in agg)
