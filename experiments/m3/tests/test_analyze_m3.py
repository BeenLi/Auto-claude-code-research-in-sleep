"""Profitable-region detection and the GREEN/YELLOW/RED go/no-go verdict."""

import pytest

import analyze_m3 as an
import frontier as fr


def test_b_crit_matches_closed_form_at_2mb_fpga100():
    # B_crit = (1-alpha) / (1/C + 1/D_egress(S) + T_fixed/S). At 2MB/alpha0.732/C=100Gbps -> ~17 Gbps.
    bc = an.b_crit_gbps(S_bytes=2097152, alpha=0.732, C_bps=fr.gbps_to_bps(100), T_fixed_s=5e-6)
    assert bc == pytest.approx(17.4, abs=1.5)


def test_b_crit_ceiling_with_free_compress_is_one_minus_alpha_times_egress():
    # With free compress AND no fixed cost, decompress caps the region at exactly (1-alpha)*D_egress.
    bc = an.b_crit_gbps(S_bytes=2097152, alpha=0.732, C_bps=fr.gbps_to_bps(1e9), T_fixed_s=0.0)
    assert bc == pytest.approx((1 - 0.732) * 188.0, abs=1.0)


def test_b_crit_monotonic_in_compress_throughput():
    bcs = [
        an.b_crit_gbps(S_bytes=2097152, alpha=0.732, C_bps=fr.gbps_to_bps(c), T_fixed_s=5e-6)
        for c in (25, 50, 100, 400)
    ]
    assert all(b >= a for a, b in zip(bcs, bcs[1:])), bcs


def test_b_crit_larger_for_better_alpha():
    worse = an.b_crit_gbps(S_bytes=2097152, alpha=0.75, C_bps=fr.gbps_to_bps(100), T_fixed_s=5e-6)
    better = an.b_crit_gbps(S_bytes=2097152, alpha=0.715, C_bps=fr.gbps_to_bps(100), T_fixed_s=5e-6)
    assert better > worse


def test_b_crit_zero_when_never_profitable():
    # alpha = 1.0 (no compression) -> no profitable region.
    assert an.b_crit_gbps(S_bytes=2097152, alpha=1.0, C_bps=fr.gbps_to_bps(100), T_fixed_s=5e-6) == pytest.approx(0.0, abs=0.1)


def test_verdict_red_when_no_region():
    v = an.verdict(alpha=1.0, C_band_gbps=[25, 50, 100], chunk_bytes=2097152, T_fixed_s=5e-6)
    assert v["verdict"] == "RED"


def test_verdict_yellow_for_narrow_region():
    # Measured envelope: region exists but sits below the mainstream-DC threshold (100 Gbps).
    v = an.verdict(alpha=0.732, C_band_gbps=[25, 50, 100], chunk_bytes=2097152, T_fixed_s=5e-6)
    assert v["verdict"] == "YELLOW"
    assert 0 < v["region_max_gbps"] < an.DATACENTER_GBPS


def test_verdict_green_when_region_reaches_datacenter_rates():
    # A hypothetical ultra-compressible dtype (alpha 0.1) pushes the region past 100 Gbps.
    # NOTE: realistic KV alpha (~0.73) structurally cannot reach GREEN under the 188 Gbps egress
    # ceiling -- that is the honest M3 finding; this case only exercises the GREEN branch.
    v = an.verdict(alpha=0.1, C_band_gbps=[100, 400], chunk_bytes=2097152, T_fixed_s=5e-6)
    assert v["verdict"] == "GREEN"
    assert v["region_max_gbps"] >= an.DATACENTER_GBPS


def test_verdict_has_rationale_and_provenance():
    v = an.verdict(alpha=0.732, C_band_gbps=[25, 50, 100], chunk_bytes=2097152, T_fixed_s=5e-6)
    assert "rationale" in v and isinstance(v["rationale"], str) and v["rationale"]
    assert v["chunk_bytes"] == 2097152
