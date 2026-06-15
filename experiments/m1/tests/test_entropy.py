"""Byte-level Shannon entropy in bits/byte (M1_CHECKLIST §1.3.3)."""

import pytest

import entropy


def test_constant_bytes_zero_entropy():
    assert entropy.shannon_entropy_bits_per_byte(b"\xff" * 1000) == pytest.approx(0.0)


def test_uniform_256_symbols_is_eight_bits():
    assert entropy.shannon_entropy_bits_per_byte(bytes(range(256))) == pytest.approx(8.0)


def test_two_equally_likely_symbols_is_one_bit():
    assert entropy.shannon_entropy_bits_per_byte(b"\x00\x01" * 1000) == pytest.approx(1.0)


def test_empty_is_zero():
    assert entropy.shannon_entropy_bits_per_byte(b"") == pytest.approx(0.0)


def test_bounded_zero_to_eight():
    import os

    h = entropy.shannon_entropy_bits_per_byte(os.urandom(8192))
    assert 0.0 <= h <= 8.0
    assert h > 7.5  # random bytes are near-maximal entropy
