"""Per-chunk E0 measurement: one transform pass, all pre-registered codec variants.

Reuses m1_6/layout.py for the transforms (never copied) and e0_codecs for the
hardware-encoder proxies. Bit-exactness of transform∘invert AND of every variant's
decompress roundtrip is asserted per chunk (contract: any failure invalidates the row).
"""

from __future__ import annotations

import e0_codecs
import layout


def measure(chunk: bytes, dtype: str, method: str, *, head_dim: int, variant_ids=None) -> dict:
    if not chunk:
        raise ValueError("empty chunk")
    vids = tuple(variant_ids) if variant_ids else tuple(e0_codecs.VARIANTS)
    n = len(chunk) // layout.itemsize(dtype)

    if method == "raw":
        transformed = chunk
        invert_ok = True
    else:
        transformed = layout.transform(chunk, dtype, method, head_dim=head_dim)
        invert_ok = layout.invert(transformed, dtype, method, n, head_dim=head_dim) == chunk

    alphas, roundtrip_ok = {}, True
    for vid in vids:
        blob = e0_codecs.compress_variant(transformed, vid)
        alphas[vid] = len(blob) / len(chunk)
        roundtrip_ok = roundtrip_ok and e0_codecs.decompress_variant(blob, vid) == transformed

    return {
        "dtype": dtype,
        "method": method,
        "head_dim": head_dim,
        "original_size": len(chunk),
        "n_values": n,
        "alphas": alphas,
        "bit_exact": invert_ok and roundtrip_ok,
    }
