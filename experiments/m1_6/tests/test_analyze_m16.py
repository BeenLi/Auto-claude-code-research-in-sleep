"""TDD for the M1.6 verdict (analyze_m16.py) — pre-registered criteria from
refine-logs/EVALUATION_CONTRACT_M1.6.md:

GREEN  : captured bf16 alpha* <= 0.65 or captured fp8_e5m2 alpha* <= 0.70 (worst model)
YELLOW : captured bf16 alpha* <= 0.695 or captured fp8_e5m2 alpha* <= 0.72
RED    : otherwise (no method beats the M1.5 baselines by > 0.01 on captured KV)
Disqualifiers: any bit-exact failure => RED; synthetic rows never drive the verdict.
"""

import analyze_m16


def _row(gen, model, dtype, method, alpha, raw=0.80, bit_exact=True):
    return {
        "generation_method": gen, "model_size": model, "dtype": dtype, "method": method,
        "alpha_concat": alpha, "alpha_raw": raw, "bit_exact": bit_exact,
        "head_dim": 64, "inverse_cost_class": "permutation",
    }


def _grid(bf16_gpt2, bf16_qwen, e5m2_gpt2=0.73, e5m2_qwen=0.73):
    rows = []
    for model, a_bf, a_e5 in (("gpt2", bf16_gpt2, e5m2_gpt2), ("qwen2.5-7b", bf16_qwen, e5m2_qwen)):
        rows.append(_row("captured", model, "bf16", "byte_transpose", 0.705))
        rows.append(_row("captured", model, "bf16", "chan_bt", a_bf))
        rows.append(_row("captured", model, "fp8_e5m2", "chan", a_e5, raw=0.73))
    # synthetic rows must not drive the verdict
    rows.append(_row("synthetic", "7b", "bf16", "chan_bt", 0.55))
    return rows


def test_green_when_captured_bf16_crosses_065_on_both_models():
    agg = analyze_m16.aggregate(_grid(0.63, 0.64))
    verdict, reason = analyze_m16.decide(agg)
    assert verdict == "GREEN"
    assert "bf16" in reason


def test_green_when_captured_e5m2_crosses_070():
    agg = analyze_m16.aggregate(_grid(0.705, 0.705, e5m2_gpt2=0.69, e5m2_qwen=0.695))
    verdict, _ = analyze_m16.decide(agg)
    assert verdict == "GREEN"


def test_yellow_when_bf16_improves_but_not_past_065():
    agg = analyze_m16.aggregate(_grid(0.67, 0.675))
    verdict, _ = analyze_m16.decide(agg)
    assert verdict == "YELLOW"


def test_red_when_no_improvement_over_m15():
    agg = analyze_m16.aggregate(_grid(0.703, 0.706))
    verdict, _ = analyze_m16.decide(agg)
    assert verdict == "RED"


def test_verdict_uses_worst_model():
    # gpt2 GREEN-level but qwen only YELLOW-level -> YELLOW overall
    agg = analyze_m16.aggregate(_grid(0.63, 0.68))
    verdict, _ = analyze_m16.decide(agg)
    assert verdict == "YELLOW"


def test_synthetic_only_gain_never_green():
    rows = [
        _row("captured", "gpt2", "bf16", "chan_bt", 0.704),
        _row("captured", "qwen2.5-7b", "bf16", "chan_bt", 0.707),
        _row("synthetic", "7b", "bf16", "chan_bt", 0.50),
    ]
    verdict, _ = analyze_m16.decide(analyze_m16.aggregate(rows))
    assert verdict == "RED"


def test_bit_exact_failure_is_disqualifying():
    rows = _grid(0.60, 0.60)
    rows[1]["bit_exact"] = False
    verdict, reason = analyze_m16.decide(analyze_m16.aggregate(rows))
    assert verdict == "RED"
    assert "bit" in reason.lower()


def test_model_disagreement_is_flagged():
    agg = analyze_m16.aggregate(_grid(0.60, 0.649))  # both GREEN but spread > 0.01
    verdict, reason = analyze_m16.decide(agg)
    assert verdict == "GREEN"
    assert "disagree" in reason.lower() or "spread" in reason.lower()
