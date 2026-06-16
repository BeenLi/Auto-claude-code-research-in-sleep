"""The plotting data-prep (pure stdlib). Rendering itself (matplotlib) is exercised on myDevbox."""

import pytest

import frontier as fr
import plot_m3 as pm


def test_frontier_grid_dimensions():
    g = pm.frontier_grid(
        B_list_gbps=[10, 50, 100, 200], S_list_bytes=[262144, 1048576, 2097152],
        alpha=0.732, C_bps=fr.gbps_to_bps(100), T_fixed_s=5e-6,
    )
    assert g["b_gbps"] == [10, 50, 100, 200]
    assert g["s_bytes"] == [262144, 1048576, 2097152]
    assert len(g["gain_us"]) == 3  # one row per chunk size
    assert all(len(row) == 4 for row in g["gain_us"])  # one col per link rate


def test_frontier_grid_profitable_matches_cells():
    B, S = [10, 400], [2097152]
    g = pm.frontier_grid(
        B_list_gbps=B, S_list_bytes=S, alpha=0.715, C_bps=fr.gbps_to_bps(400), T_fixed_s=5e-6,
    )
    # 10 Gbps profitable, 400 Gbps not (from the frontier physics).
    assert g["profitable"][0][0] is True
    assert g["profitable"][0][1] is False


def test_policy_comparison_table_has_all_policies():
    tbl = pm.policy_comparison(
        B_list_gbps=[10, 50, 100], S_bytes=2097152, alpha=0.715, C_bps=fr.gbps_to_bps(400), T_fixed_s=5e-6,
    )
    assert set(tbl["bytes_on_wire_norm"].keys()) == {"raw", "always", "static", "gate"}
    # raw is always 1.0 bytes-on-wire (normalized); gate never exceeds raw.
    assert all(v == pytest.approx(1.0) for v in tbl["bytes_on_wire_norm"]["raw"])
    assert all(g <= r + 1e-9 for g, r in zip(
        tbl["transfer_time_norm"]["gate"], tbl["transfer_time_norm"]["raw"]))
