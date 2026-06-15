"""Compress-vs-raw break-even math for KV-cache transfer (M1_CHECKLIST Appendix A).

A chunk of S bytes either goes raw (T_raw = S/B) or compressed
(T_comp = S/C + alpha*S/B + alpha*S/D + T_fixed), where alpha = compressed/original.
Compression pays iff T_comp < T_raw, which solves to:

    alpha < (1/B - 1/C - T_fixed/S) / (1/B + 1/D)            [full]
    alpha < 1 - B/C - B*T_fixed/S          (when D >> B)      [simplified]

Units must be consistent: bytes and bytes/second; T_fixed in seconds.
"""

from __future__ import annotations


def _check_pos(**vals: float) -> None:
    for name, v in vals.items():
        if v <= 0:
            raise ValueError(f"{name} must be > 0, got {v}")


def transfer_times(
    *, alpha: float, B: float, C: float, D: float, T_fixed: float, S: float
) -> tuple[float, float]:
    """Return (T_raw, T_comp) seconds for sending one S-byte chunk."""
    _check_pos(B=B, C=C, D=D, S=S)
    t_raw = S / B
    t_comp = S / C + alpha * S / B + alpha * S / D + T_fixed
    return t_raw, t_comp


def alpha_threshold(*, B: float, C: float, D: float, T_fixed: float, S: float) -> float:
    """Max compression ratio that still pays, accounting for finite decompress D."""
    _check_pos(B=B, C=C, D=D, S=S)
    num = 1.0 / B - 1.0 / C - T_fixed / S
    denom = 1.0 / B + 1.0 / D
    return num / denom


def alpha_threshold_simplified(*, B: float, C: float, T_fixed: float, S: float) -> float:
    """Max compression ratio that pays when decompress is not a bottleneck (D >> B)."""
    _check_pos(B=B, C=C, S=S)
    return 1.0 - B / C - B * T_fixed / S


def is_profitable(*, alpha: float, B: float, C: float, D: float, T_fixed: float, S: float) -> bool:
    """True iff compressing this chunk beats sending it raw."""
    t_raw, t_comp = transfer_times(alpha=alpha, B=B, C=C, D=D, T_fixed=T_fixed, S=S)
    return t_comp < t_raw
