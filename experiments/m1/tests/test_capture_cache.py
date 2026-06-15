"""KV extraction must handle every transformers cache shape (regression: 5.x DynamicCache).

Pure dispatch — tested with fakes so no torch/transformers needed locally.
"""

import pytest

import capture_hf_kv as cap


class _FakeLayer:
    def __init__(self, k, v):
        self.keys = k
        self.values = v


class _FakeCacheLayers:  # transformers 5.x: cache.layers[i].keys/.values
    def __init__(self, pairs):
        self.layers = [_FakeLayer(k, v) for k, v in pairs]


class _FakeCacheLists:  # older: cache.key_cache / cache.value_cache
    def __init__(self, pairs):
        self.key_cache = [k for k, _ in pairs]
        self.value_cache = [v for _, v in pairs]


def test_kv_layers_from_legacy_tuple():
    past = (("k0", "v0"), ("k1", "v1"))
    assert cap._kv_layers(past) == [("k0", "v0"), ("k1", "v1")]


def test_kv_layers_from_dynamiccache_layers():
    past = _FakeCacheLayers([("k0", "v0"), ("k1", "v1")])
    assert cap._kv_layers(past) == [("k0", "v0"), ("k1", "v1")]


def test_kv_layers_from_keycache_lists():
    past = _FakeCacheLists([("k0", "v0"), ("k1", "v1")])
    assert cap._kv_layers(past) == [("k0", "v0"), ("k1", "v1")]


def test_kv_layers_unsupported_raises():
    with pytest.raises(TypeError):
        cap._kv_layers(object())
