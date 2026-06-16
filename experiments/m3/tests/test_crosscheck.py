"""Cross-check: does LLMServingSim's PD KV-transfer time scale as bytes/link_bw (Layer-1 physics)?

Fits the measured TTFT(link_bw) sweep to TTFT = A + M/bw over the transfer-limited points and checks
the 1/bw law. M (ns at 1 GB/s) equals the implied transferred bytes (1 GB/s = 1 byte/ns).
"""

import pytest

import crosscheck as cc

# Real M3 sim sweep (single_node_pd, Llama-3.1-8B bf16, 2048-token prompt). bw GB/s -> TTFT ns.
REAL_SWEEP = {1: 750994238, 2: 375990423, 4: 188488516, 8: 94737546, 16: 82965853, 32: 82965615, 64: 82965496}


def test_compute_floor_is_the_high_bw_plateau():
    assert cc.compute_floor_ns(REAL_SWEEP) == pytest.approx(82965496, rel=1e-3)


def test_transfer_limited_points_excludes_the_plateau():
    floor = cc.compute_floor_ns(REAL_SWEEP)
    pts = cc.transfer_limited_points(REAL_SWEEP, floor)
    assert set(pts.keys()) == {1, 2, 4}  # bw where transfer clearly dominates (ttft > 2*floor)


def test_fit_recovers_slope_on_synthetic_clean_data():
    # Clean synthetic: TTFT = 1e6 + 5e8/bw exactly.
    synth = {bw: 1e6 + 5e8 / bw for bw in (1, 2, 4, 8)}
    fit = cc.fit_transfer_model(synth, select=False)
    assert fit["M_ns_per_gbps"] == pytest.approx(5e8, rel=1e-6)
    assert fit["A_ns"] == pytest.approx(1e6, rel=1e-3)
    assert fit["r_squared"] == pytest.approx(1.0, abs=1e-9)


def test_fit_on_real_data_is_linear_in_inverse_bw():
    fit = cc.fit_transfer_model(REAL_SWEEP)  # auto-selects transfer-limited points
    # The bandwidth-limited regime is an essentially perfect 1/bw law.
    assert fit["r_squared"] >= 0.999
    # Implied transferred bytes ~ 0.7 GB (M ns at 1 GB/s == bytes).
    assert fit["implied_transfer_bytes"] == pytest.approx(7.5e8, rel=0.05)


def test_expected_kv_bytes_llama31_8b():
    # 32 layers x 2(K,V) x 8 kv-heads x 128 head_dim x 2 bytes (bf16) x 2048 tokens = 256 MiB.
    b = cc.expected_kv_bytes(input_toks=2048, n_layers=32, n_kv_heads=8, head_dim=128, dtype_bytes=2)
    assert b == 268435456


def test_verdict_pass_for_bandwidth_limited_transfer():
    v = cc.crosscheck_verdict(
        REAL_SWEEP, input_toks=2048, n_layers=32, n_kv_heads=8, head_dim=128, dtype_bytes=2
    )
    assert v["verdict"] == "PASS"  # transfer is bandwidth-limited, 1/bw law confirmed
    assert v["payload_factor"] == pytest.approx(7.5e8 / 268435456, rel=0.1)
    assert "rationale" in v and v["rationale"]
