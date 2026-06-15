"""Synthetic-vs-captured cross-validation comparator (the M1 validity guard)."""

import pytest

import validate_overlap as vo


def test_ratio_summary_median_and_count():
    s = vo.ratio_summary([0.4, 0.5, 0.6, 0.9])
    assert s["n"] == 4
    assert s["p50"] == pytest.approx(0.55)  # median of 4 values


def test_identical_distributions_match():
    r = vo.compare_config([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    assert r.status == "match"
    assert r.abs_delta_p50 == pytest.approx(0.0)


def test_divergent_beyond_tolerance():
    r = vo.compare_config([0.4] * 5, [0.6] * 5, ratio_tol=0.05)
    assert r.status == "divergent"
    assert r.abs_delta_p50 == pytest.approx(0.2)


def test_within_tolerance_matches():
    r = vo.compare_config([0.50] * 5, [0.53] * 5, ratio_tol=0.05)
    assert r.status == "match"


def test_empty_inputs_raise():
    with pytest.raises(ValueError):
        vo.ratio_summary([])
    with pytest.raises(ValueError):
        vo.compare_config([], [0.5])
