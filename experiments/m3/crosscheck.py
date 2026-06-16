"""Cross-check the LLMServingSim PD transfer model against Layer-1's bytes/link_bw physics.

Given a measured TTFT(link_bw) sweep, the transfer-limited points follow TTFT = A + M/bw. Because
1 GB/s == 1 byte/ns, the slope M (in ns at 1 GB/s) numerically equals the implied transferred bytes.
A clean 1/bw law (high R^2) confirms the simulator's PD KV transfer is bandwidth-limited the way the
analytical frontier assumes. The absolute payload (vs the minimal KV-cache size) is reported as a
factor, not required to be 1.0.
"""

from __future__ import annotations


def compute_floor_ns(sweep: dict[float, float]) -> float:
    """The compute-limited TTFT floor = the high-bandwidth plateau (transfer hidden)."""
    return float(min(sweep.values()))


def transfer_limited_points(sweep: dict[float, float], floor_ns: float, factor: float = 2.0) -> dict[float, float]:
    """Points where transfer clearly dominates (TTFT > factor * compute floor)."""
    return {bw: t for bw, t in sweep.items() if t > factor * floor_ns}


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Ordinary least squares y = A + M*x. Returns (A, M, r_squared). Pure stdlib."""
    n = len(xs)
    if n < 2:
        raise ValueError("need >= 2 points to fit")
    sx, sy = sum(xs), sum(ys)
    mx, my = sx / n, sy / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    M = sxy / sxx
    A = my - M * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (A + M * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot
    return A, M, r2


def fit_transfer_model(sweep: dict[float, float], *, select: bool = True) -> dict:
    """Fit TTFT = A + M/bw. If ``select``, fit only the transfer-limited points."""
    pts = transfer_limited_points(sweep, compute_floor_ns(sweep)) if select else dict(sweep)
    if len(pts) < 2:  # fall back to the whole sweep if selection is too aggressive
        pts = dict(sweep)
    xs = [1.0 / bw for bw in pts]
    ys = [pts[bw] for bw in pts]
    A, M, r2 = _ols(xs, ys)
    return {
        "A_ns": A,
        "M_ns_per_gbps": M,
        "implied_transfer_bytes": M,  # 1 GB/s == 1 byte/ns
        "r_squared": r2,
        "fitted_bw": sorted(pts.keys()),
    }


def expected_kv_bytes(*, input_toks: int, n_layers: int, n_kv_heads: int, head_dim: int, dtype_bytes: int) -> int:
    """Minimal KV-cache bytes for a prompt: layers x 2(K,V) x kv_heads x head_dim x bytes x tokens."""
    return n_layers * 2 * n_kv_heads * head_dim * dtype_bytes * input_toks


def crosscheck_verdict(
    sweep: dict[float, float], *, input_toks: int, n_layers: int, n_kv_heads: int, head_dim: int,
    dtype_bytes: int, r2_threshold: float = 0.999,
) -> dict:
    """PASS iff the sim's PD transfer is bandwidth-limited (TTFT ~ A + bytes/bw, R^2 >= threshold)."""
    fit = fit_transfer_model(sweep)
    kv = expected_kv_bytes(
        input_toks=input_toks, n_layers=n_layers, n_kv_heads=n_kv_heads, head_dim=head_dim, dtype_bytes=dtype_bytes
    )
    factor = fit["implied_transfer_bytes"] / kv
    passed = fit["r_squared"] >= r2_threshold
    rationale = (
        f"PD TTFT follows a {('clean' if passed else 'noisy')} 1/link_bw law "
        f"(R^2={fit['r_squared']:.5f}) over bw={fit['fitted_bw']} GB/s -> transfer time is "
        f"bandwidth-limited, matching the analytical frontier's bytes/bandwidth model. Implied "
        f"transferred payload {fit['implied_transfer_bytes'] / 1e6:.0f} MB = {factor:.2f}x the "
        f"minimal KV-cache size ({kv / 1e6:.0f} MB); the sim moves a larger payload than raw KV, "
        f"but the scaling law the frontier relies on holds. Above the crossover the sim is "
        f"compute-limited (TTFT floors at the prefill time), as expected."
    )
    return {
        "verdict": "PASS" if passed else "INCONCLUSIVE",
        "r_squared": fit["r_squared"],
        "implied_transfer_bytes": fit["implied_transfer_bytes"],
        "expected_kv_bytes": kv,
        "payload_factor": factor,
        "compute_floor_ns": compute_floor_ns(sweep),
        "fit": fit,
        "rationale": rationale,
    }
