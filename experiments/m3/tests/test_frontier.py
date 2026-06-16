"""Frontier physics: per-cell break-even with the chunk-coupled decompress rate D=alpha*D_egress(S)."""

import pytest

import frontier as fr


def test_unit_converters():
    assert fr.gbps_to_bps(8.0) == pytest.approx(1e9)  # 8 Gbit/s = 1e9 bytes/s
    assert fr.mbps_to_bps(17.0) == pytest.approx(17e6)


def test_cell_couples_d_input_to_alpha_times_egress():
    cell = fr.evaluate_cell(
        B_bps=fr.gbps_to_bps(10), S_bytes=2097152, alpha=0.715,
        C_bps=fr.gbps_to_bps(400), T_fixed_s=5e-6,
    )
    # D fed to profitability is alpha * egress(2MB) = 0.715 * 188 Gbps.
    assert cell.d_input_bps == pytest.approx(0.715 * 188.0 * 1.25e8)


def test_clearly_profitable_cell():
    # Low link rate (10 Gbps), line-rate FPGA compress (400 Gbps), 2 MB, best alpha.
    cell = fr.evaluate_cell(
        B_bps=fr.gbps_to_bps(10), S_bytes=2097152, alpha=0.715,
        C_bps=fr.gbps_to_bps(400), T_fixed_s=5e-6,
    )
    assert cell.profitable is True
    assert cell.gain_s > 0
    # Hand-computed T_raw ~ 1677 us, T_comp ~ 1335 us.
    assert cell.t_raw_s == pytest.approx(2097152 / fr.gbps_to_bps(10), rel=1e-6)
    assert cell.t_comp_s < cell.t_raw_s


def test_clearly_unprofitable_at_high_link_rate():
    # 400 Gbps link: wire is already cheap, overheads dominate -> not profitable.
    cell = fr.evaluate_cell(
        B_bps=fr.gbps_to_bps(400), S_bytes=2097152, alpha=0.715,
        C_bps=fr.gbps_to_bps(400), T_fixed_s=5e-6,
    )
    assert cell.profitable is False
    assert cell.gain_s < 0


def test_software_compress_never_pays_at_real_link_rates():
    # 17 MB/s software compress: unprofitable across every real link rate.
    for gbps in (1, 10, 25, 50, 100):
        cell = fr.evaluate_cell(
            B_bps=fr.gbps_to_bps(gbps), S_bytes=1048576, alpha=0.732,
            C_bps=fr.mbps_to_bps(17), T_fixed_s=5e-6,
        )
        assert cell.profitable is False, f"software unexpectedly paid at {gbps} Gbps"


def test_gain_increases_as_link_rate_drops():
    # Cheaper wire (lower B) -> compression more valuable -> larger gain (monotone).
    gains = [
        fr.evaluate_cell(
            B_bps=fr.gbps_to_bps(g), S_bytes=1048576, alpha=0.732,
            C_bps=fr.gbps_to_bps(100), T_fixed_s=5e-6,
        ).gain_s
        for g in (100, 50, 25, 10, 5)
    ]
    assert all(b > a for a, b in zip(gains, gains[1:])), gains


def test_sweep_grid_cardinality():
    cells = fr.sweep(
        B_list_gbps=[10, 50, 100, 200],
        S_list_bytes=[262144, 1048576, 2097152],
        alpha=0.732, C_bps=fr.gbps_to_bps(100), T_fixed_s=5e-6,
    )
    assert len(cells) == 4 * 3
    assert {(round(c.b_gbps), c.S_bytes) for c in cells} >= {(10, 262144), (200, 2097152)}
