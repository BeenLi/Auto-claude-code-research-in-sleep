"""The four compared policies: raw / always / static-threshold / wr_zipguard_gate."""

import pytest

import frontier as fr
import policies as pol


def _knobs(gbps_link, S, alpha=0.732, C_gbps=100):
    return dict(
        alpha=alpha, B_bps=fr.gbps_to_bps(gbps_link), C_bps=fr.gbps_to_bps(C_gbps),
        S_bytes=S, T_fixed_s=5e-6,
    )


def test_policy_names():
    assert set(pol.POLICIES) == {"raw", "always", "static", "gate"}


def test_raw_never_compresses():
    assert pol.decide("raw", **_knobs(10, 1048576)) is False


def test_always_always_compresses():
    assert pol.decide("always", **_knobs(400, 1048576)) is True


def test_static_threshold_respects_min_chunk():
    # default static threshold = 256 KB amortization gate.
    assert pol.decide("static", **_knobs(10, 262144)) is True
    assert pol.decide("static", **_knobs(10, 131072)) is False


def test_static_threshold_is_overridable():
    assert pol.decide("static", static_threshold_bytes=1048576, **_knobs(10, 524288)) is False
    assert pol.decide("static", static_threshold_bytes=1048576, **_knobs(10, 1048576)) is True


def test_gate_matches_cell_profitability():
    # The gate compresses iff the cell is actually profitable (by construction).
    for gbps, S in [(5, 2097152), (50, 1048576), (400, 2097152)]:
        k = _knobs(gbps, S)
        cell = fr.evaluate_cell(**k)
        assert pol.decide("gate", **k) is cell.profitable


def test_gate_bypasses_software_compress_everywhere():
    # With hopeless software compress (17 MB/s = 0.136 Gbps), the gate sends raw at every link rate.
    sw_compress_gbps = fr.mbps_to_bps(17) / fr.GBPS_TO_BPS  # 17 MB/s expressed in Gbps
    for gbps in (1, 10, 50, 100):
        assert pol.decide("gate", **_knobs(gbps, 1048576, C_gbps=sw_compress_gbps)) is False


def test_outcome_bytes_on_wire_and_time():
    k = _knobs(10, 2097152, alpha=0.715, C_gbps=400)
    raw_out = pol.outcome("raw", **k)
    gate_out = pol.outcome("gate", **k)
    assert raw_out.bytes_on_wire == 2097152
    # This cell is profitable, so the gate compresses: fewer bytes, less time than raw.
    assert gate_out.bytes_on_wire == pytest.approx(0.715 * 2097152)
    assert gate_out.transfer_time_s < raw_out.transfer_time_s


def test_always_compress_loses_to_raw_in_bad_regime():
    # always-compress eats the penalty where compression does not pay (high link rate).
    k = _knobs(400, 2097152, alpha=0.715, C_gbps=400)
    assert pol.outcome("always", **k).transfer_time_s > pol.outcome("raw", **k).transfer_time_s
