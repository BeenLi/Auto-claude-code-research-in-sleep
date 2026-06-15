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
