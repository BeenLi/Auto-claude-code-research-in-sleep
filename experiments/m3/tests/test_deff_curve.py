"""M2 decompress-throughput curve D_eff(chunk), with the egress->input units reconciliation.

The measured M2 table is EGRESS (decompressed-output) Gib/s. profitability.py's D term consumes
COMPRESSED-INPUT bytes, so the frontier must feed D = alpha * d_egress. These tests pin both the
interpolation and that reconciliation (see EVALUATION_CONTRACT_M3.md).
"""

import math

import pytest

import deff_curve as dc

GBPS_TO_BPS = 1e9 / 8.0  # bits/s -> bytes/s


def test_returns_measured_value_at_a_measured_point():
    # 256 KB -> 141 Gbps egress (EXPERIMENT_LOG.md L181).
    assert dc.d_egress_gbps(262144) == pytest.approx(141.0)


def test_all_four_amortized_measured_points_exact():
    for chunk, gbps in [(65536, 75.0), (262144, 141.0), (1048576, 180.0), (2097152, 188.0)]:
        assert dc.d_egress_gbps(chunk) == pytest.approx(gbps)


def test_monotonic_non_decreasing_in_chunk_size():
    sizes = [4096, 16384, 65536, 131072, 262144, 524288, 1048576, 2097152]
    vals = [dc.d_egress_gbps(s) for s in sizes]
    assert all(b >= a for a, b in zip(vals, vals[1:])), vals


def test_interpolation_between_points_lies_between_neighbors():
    # 512 KB sits between 256 KB (141) and 1 MB (180).
    v = dc.d_egress_gbps(524288)
    assert 141.0 <= v <= 180.0


def test_clamps_below_smallest_point():
    # Below the smallest measured chunk, clamp to the smallest value (no extrapolation past data).
    assert dc.d_egress_gbps(1024) == pytest.approx(6.5)


def test_clamps_above_largest_point_to_ceiling():
    # Above the largest tested chunk, hold the measured ceiling (188 Gbps).
    assert dc.d_egress_gbps(8 * 1024 * 1024) == pytest.approx(188.0)


def test_egress_bytes_per_second_conversion():
    assert dc.d_egress_bytes_per_s(2097152) == pytest.approx(188.0 * GBPS_TO_BPS)


def test_d_input_is_alpha_times_egress_units_reconciliation():
    # The log's "~135 Gbps input" ~= 0.72 * 188 Gbps egress at 2 MB.
    alpha = 0.72
    d_in_gbps = dc.d_input_bytes_per_s(2097152, alpha) / GBPS_TO_BPS
    assert d_in_gbps == pytest.approx(0.72 * 188.0)
    assert d_in_gbps == pytest.approx(135.36, abs=0.5)


def test_is_amortized_gate_at_256kb():
    assert dc.is_amortized(262144) is True
    assert dc.is_amortized(262143) is False
    assert dc.is_amortized(65536) is False


def test_within_tested_range_flag():
    assert dc.is_within_tested_range(2097152) is True
    assert dc.is_within_tested_range(4 * 1024 * 1024) is False
