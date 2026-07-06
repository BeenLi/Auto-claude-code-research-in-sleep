"""Break-even math for compress-vs-raw transfer (M1_CHECKLIST Appendix A).

These tests encode the *derivation*, not the M1_CHECKLIST §3.3.2 example table,
whose listed thresholds are inconsistent with the formula (see M1_REPORT notes).

Symbols: S=chunk bytes, B=link bytes/s, C=compress input bytes/s,
D=decompress input bytes/s, alpha=compressed/original, T_fixed=fixed seconds.
"""

import pytest

import profitability as p


def test_simplified_threshold_no_overhead():
    # D >> B, T_fixed=0  =>  alpha < 1 - B/C = 0.5
    assert p.alpha_threshold_simplified(B=1e9, C=2e9, T_fixed=0.0, S=1_000_000) == pytest.approx(0.5)


def test_simplified_threshold_with_fixed_overhead():
    # 1 - B/C - B*T_fixed/S = 1 - 0.5 - 0.1 = 0.4
    assert p.alpha_threshold_simplified(B=1e9, C=2e9, T_fixed=1e-4, S=1_000_000) == pytest.approx(0.4)


def test_software_compress_never_profitable_when_bandwidth_exceeds_throughput():
    # B > C  =>  threshold negative  =>  never profitable (Appendix A insight #1)
    assert p.alpha_threshold_simplified(B=2e9, C=1e9, T_fixed=0.0, S=1_000_000) < 0


def test_full_threshold_finite_decompress():
    # (1/B - 1/C) / (1/B + 1/D) = 0.5e-9 / 1.25e-9 = 0.4
    assert p.alpha_threshold(B=1e9, C=2e9, D=4e9, T_fixed=0.0, S=1_000_000) == pytest.approx(0.4)


def test_finite_decompress_is_stricter_than_simplified():
    full = p.alpha_threshold(B=1e9, C=2e9, D=4e9, T_fixed=0.0, S=1_000_000)
    simp = p.alpha_threshold_simplified(B=1e9, C=2e9, T_fixed=0.0, S=1_000_000)
    assert full < simp  # competing decompress pulls the ceiling down


def test_full_reduces_to_simplified_as_D_grows():
    full = p.alpha_threshold(B=1e9, C=2e9, D=1e15, T_fixed=1e-4, S=1_000_000)
    simp = p.alpha_threshold_simplified(B=1e9, C=2e9, T_fixed=1e-4, S=1_000_000)
    assert full == pytest.approx(simp, rel=1e-3)


def test_is_profitable_brackets_threshold():
    kw = dict(B=1e9, C=2e9, D=4e9, T_fixed=0.0, S=1_000_000)  # threshold 0.4
    assert p.is_profitable(alpha=0.39, **kw) is True
    assert p.is_profitable(alpha=0.41, **kw) is False


def test_transfer_times_equal_at_threshold():
    kw = dict(B=1e9, C=2e9, D=4e9, T_fixed=0.0, S=1_000_000)
    thr = p.alpha_threshold(**kw)
    t_raw, t_comp = p.transfer_times(alpha=thr, **kw)
    assert t_comp == pytest.approx(t_raw)


def test_larger_chunks_widen_the_window():
    # B*T_fixed/S shrinks with S, so the ceiling rises with chunk size.
    small = p.alpha_threshold_simplified(B=1e9, C=4e9, T_fixed=5e-5, S=64_000)
    large = p.alpha_threshold_simplified(B=1e9, C=4e9, T_fixed=5e-5, S=16_000_000)
    assert large > small


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        p.alpha_threshold_simplified(B=0, C=2e9, T_fixed=0.0, S=1e6)
    with pytest.raises(ValueError):
        p.alpha_threshold(B=1e9, C=0, D=4e9, T_fixed=0.0, S=1e6)
    with pytest.raises(ValueError):
        p.alpha_threshold(B=1e9, C=2e9, D=4e9, T_fixed=0.0, S=0)


# ---- transform-aware extension (T_xform folding, M4a preliminary #2) ----
# t_comp gains two additive terms: S/X_fwd (sender transform) + S/X_inv
# (receiver inverse), both in ORIGINAL bytes/s; X=inf means free/absent.

INF = float("inf")


def test_transform_times_reduce_to_base_when_free():
    base = p.transfer_times(alpha=0.7, B=1e9, C=2e9, D=5e9, T_fixed=0.0, S=1_000_000)
    ext = p.transfer_times_with_transform(
        alpha=0.7, B=1e9, C=2e9, D=5e9, T_fixed=0.0, S=1_000_000, X_fwd=INF, X_inv=INF
    )
    assert ext == pytest.approx(base)


def test_transform_threshold_reduces_to_base_when_free():
    kw = dict(B=1e9, C=2e9, D=5e9, T_fixed=1e-5, S=1_000_000)
    assert p.alpha_threshold_with_transform(X_fwd=INF, X_inv=INF, **kw) == pytest.approx(
        p.alpha_threshold(**kw)
    )


def test_transform_costs_shrink_alpha_threshold():
    kw = dict(B=1e9, C=2e9, D=5e9, T_fixed=0.0, S=1_000_000)
    assert p.alpha_threshold_with_transform(X_fwd=2e9, X_inv=2e9, **kw) < p.alpha_threshold(**kw)


def test_transform_times_add_exactly_the_two_terms():
    S = 2_097_152
    base_raw, base_comp = p.transfer_times(alpha=0.7, B=1e9, C=2e9, D=5e9, T_fixed=0.0, S=S)
    raw, comp = p.transfer_times_with_transform(
        alpha=0.7, B=1e9, C=2e9, D=5e9, T_fixed=0.0, S=S, X_fwd=4e9, X_inv=2e9
    )
    assert raw == pytest.approx(base_raw)
    assert comp == pytest.approx(base_comp + S / 4e9 + S / 2e9)


def test_bandwidth_threshold_equalizes_transfer_times():
    kw = dict(alpha=0.704, C=12.5e9, D=3.3e9, T_fixed=2e-5, S=2_097_152, X_fwd=INF, X_inv=2e9)
    b_crit = p.bandwidth_threshold_with_transform(**kw)
    raw, comp = p.transfer_times_with_transform(B=b_crit, **kw)
    assert raw == pytest.approx(comp, rel=1e-9)


def test_bandwidth_threshold_monotone_in_inverse_throughput():
    kw = dict(alpha=0.704, C=12.5e9, D=3.3e9, T_fixed=0.0, S=2_097_152, X_fwd=INF)
    slow = p.bandwidth_threshold_with_transform(X_inv=1e9, **kw)
    fast = p.bandwidth_threshold_with_transform(X_inv=8e9, **kw)
    free = p.bandwidth_threshold_with_transform(X_inv=INF, **kw)
    assert slow < fast < free


def test_is_profitable_with_transform_brackets_threshold():
    kw = dict(B=1e9, C=4e9, D=5e9, T_fixed=0.0, S=1_000_000, X_fwd=8e9, X_inv=8e9)
    thr = p.alpha_threshold_with_transform(**kw)
    assert p.is_profitable_with_transform(alpha=thr - 0.01, **kw)
    assert not p.is_profitable_with_transform(alpha=thr + 0.01, **kw)


def test_transform_invalid_params_raise():
    kw = dict(alpha=0.7, B=1e9, C=2e9, D=5e9, T_fixed=0.0, S=1_000_000)
    with pytest.raises(ValueError):
        p.transfer_times_with_transform(X_fwd=0.0, X_inv=1e9, **kw)
    with pytest.raises(ValueError):
        p.transfer_times_with_transform(X_fwd=1e9, X_inv=-1.0, **kw)
