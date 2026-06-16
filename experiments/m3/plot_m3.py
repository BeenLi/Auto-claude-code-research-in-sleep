"""M3 figures: Figure 3 (profitability frontier heatmap) and Figure 4 (policy comparison).

Data preparation is pure stdlib and unit-tested. Rendering lazily imports matplotlib so this module
imports fine on machines without it; render where matplotlib is available (e.g. myDevbox).
"""

from __future__ import annotations

import frontier as fr
import policies as pol

GBPS_TO_BPS = fr.GBPS_TO_BPS


def frontier_grid(
    *, B_list_gbps: list[float], S_list_bytes: list[int], alpha: float, C_bps: float, T_fixed_s: float
) -> dict:
    """Build the Figure-3 grid: gain (microseconds) and profitable-bool per (chunk row, link col)."""
    gain_us, profitable = [], []
    for s in S_list_bytes:
        gain_row, prof_row = [], []
        for b in B_list_gbps:
            cell = fr.evaluate_cell(
                B_bps=fr.gbps_to_bps(b), S_bytes=s, alpha=alpha, C_bps=C_bps, T_fixed_s=T_fixed_s
            )
            gain_row.append(cell.gain_s * 1e6)
            prof_row.append(cell.profitable)
        gain_us.append(gain_row)
        profitable.append(prof_row)
    return {"b_gbps": list(B_list_gbps), "s_bytes": list(S_list_bytes), "gain_us": gain_us, "profitable": profitable}


def policy_comparison(
    *, B_list_gbps: list[float], S_bytes: int, alpha: float, C_bps: float, T_fixed_s: float
) -> dict:
    """Build the Figure-4 table: per-policy bytes-on-wire and transfer time, normalized to raw."""
    bytes_norm: dict[str, list[float]] = {p: [] for p in pol.POLICIES}
    time_norm: dict[str, list[float]] = {p: [] for p in pol.POLICIES}
    for b in B_list_gbps:
        raw = pol.outcome("raw", alpha=alpha, B_bps=fr.gbps_to_bps(b), C_bps=C_bps, S_bytes=S_bytes, T_fixed_s=T_fixed_s)
        for p in pol.POLICIES:
            o = pol.outcome(p, alpha=alpha, B_bps=fr.gbps_to_bps(b), C_bps=C_bps, S_bytes=S_bytes, T_fixed_s=T_fixed_s)
            bytes_norm[p].append(o.bytes_on_wire / raw.bytes_on_wire)
            time_norm[p].append(o.transfer_time_s / raw.transfer_time_s)
    return {"b_gbps": list(B_list_gbps), "bytes_on_wire_norm": bytes_norm, "transfer_time_norm": time_norm}


def render_frontier_heatmap(grid: dict, out_path: str, *, title: str = "M3 Figure 3 — profitability frontier") -> None:  # pragma: no cover
    """Render the Figure-3 heatmap (gain vs link rate x chunk). Lazy matplotlib import."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    data = grid["gain_us"]
    im = ax.imshow(data, aspect="auto", origin="lower", cmap="RdYlGn")
    ax.set_xticks(range(len(grid["b_gbps"])), [f"{b:g}" for b in grid["b_gbps"]])
    ax.set_yticks(range(len(grid["s_bytes"])), [f"{s // 1024} KB" for s in grid["s_bytes"]])
    ax.set_xlabel("link bandwidth B (Gbps)")
    ax.set_ylabel("chunk size S")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="gain per chunk (us)  [>0 = compression pays]")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def render_policy_comparison(tbl: dict, out_path: str, *, title: str = "M3 Figure 4 — policy comparison") -> None:  # pragma: no cover
    """Render the Figure-4 policy comparison (transfer time vs link rate). Lazy matplotlib import."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    for p in pol.POLICIES:
        ax.plot(tbl["b_gbps"], tbl["transfer_time_norm"][p], marker="o", label=p)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xlabel("link bandwidth B (Gbps)")
    ax.set_ylabel("transfer time (normalized to raw)")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
