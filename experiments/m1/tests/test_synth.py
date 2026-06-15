"""Synthetic KV tensor generation (M1_CHECKLIST §1.2.1, method A).

Structural/reproducibility invariants only — statistical realism is validated
separately against HF captures (validate_overlap), not asserted here.
"""

import numpy as np
import pytest

import synth


def _spec(**kw):
    base = dict(
        phase="prefill",
        tensor_type="K",
        dtype="bf16",
        num_heads=8,
        head_dim=64,
        seq_len=128,
        layer_idx=0,
        seed=42,
    )
    base.update(kw)
    return synth.TensorSpec(**base)


def test_shape_matches_spec():
    arr = synth.generate_kv_tensor(_spec())
    assert arr.shape == (128, 8, 64)


@pytest.mark.parametrize("dtype,itemsize", [("bf16", 2), ("fp8_e4m3", 1), ("fp8_e5m2", 1)])
def test_dtype_itemsize_and_byte_count(dtype, itemsize):
    assert synth.dtype_itemsize(dtype) == itemsize
    arr = synth.generate_kv_tensor(_spec(dtype=dtype))
    assert synth.to_bytes(arr) and len(synth.to_bytes(arr)) == 128 * 8 * 64 * itemsize


def test_deterministic_for_same_spec():
    assert synth.to_bytes(synth.generate_kv_tensor(_spec())) == synth.to_bytes(
        synth.generate_kv_tensor(_spec())
    )


def test_different_seed_changes_bytes():
    assert synth.to_bytes(synth.generate_kv_tensor(_spec(seed=1))) != synth.to_bytes(
        synth.generate_kv_tensor(_spec(seed=2))
    )


def test_k_and_v_differ():
    assert synth.to_bytes(synth.generate_kv_tensor(_spec(tensor_type="K"))) != synth.to_bytes(
        synth.generate_kv_tensor(_spec(tensor_type="V"))
    )


def test_not_degenerate_constant_buffer():
    import entropy

    h = entropy.shannon_entropy_bits_per_byte(synth.to_bytes(synth.generate_kv_tensor(_spec())))
    assert h > 1.0  # real KV bytes are not a constant fill


def test_unsupported_dtype_raises():
    with pytest.raises(ValueError):
        synth.generate_kv_tensor(_spec(dtype="int4"))
    with pytest.raises(ValueError):
        synth.dtype_itemsize("int4")
