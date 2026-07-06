"""Per-chunk float-split compressibility measurement (M1.5).

Reuses the canonical M1 codec matrix (``m1_codecs``) so M1.5 and M1 can never disagree
on what "deflate" means. For one KV chunk it reports:

- ``alpha_raw``    : deflate on the raw interleaved bytes (reproduces M1).
- ``alpha_concat`` : deflate on the whole transformed buffer as ONE stream — the alpha
                     WR-ZipGuard can claim end-to-end, since commodity BF3 decompresses a
                     single standard deflate stream and the receiver then un-splits.
- ``perplane``     : (bitplane only) deflate sign+exp, store mantissa RAW — the DietGPU-style
                     ceiling — plus the per-plane alphas that expose the mechanism.
- ``transform_throughput_mbps`` : sender-side cost of the transform (a permutation/gather).

Bit-exactness of transform∘invert AND of the deflate roundtrip is asserted; a False here
would mean the receiver could not reconstruct the KV, which is disqualifying.
"""

from __future__ import annotations

import statistics
import time

import floatsplit as fs
import m1_codecs


def _csize(data: bytes, codec: str, level) -> int:
    return len(m1_codecs.compress(data, codec, level))


def _time_transform(chunk: bytes, dtype: str, method: str, warmup: int, repeats: int) -> float:
    for _ in range(max(0, warmup)):
        fs.transform(chunk, dtype, method)
    times = []
    for _ in range(max(1, repeats)):
        t0 = time.perf_counter_ns()
        fs.transform(chunk, dtype, method)
        times.append(time.perf_counter_ns() - t0)
    times.sort()
    return max(times[len(times) // 2], 1) / 1e9


def measure_transform(
    chunk: bytes,
    dtype: str,
    method: str,
    codec: str = "deflate",
    level=6,
    *,
    warmup: int = 1,
    repeats: int = 3,
) -> dict:
    n = fs.n_values(chunk, dtype)
    original = len(chunk)
    if original == 0:
        raise ValueError("empty chunk")

    alpha_raw = _csize(chunk, codec, level) / original

    transformed = fs.transform(chunk, dtype, method)
    concat_comp = _csize(transformed, codec, level)
    alpha_concat = concat_comp / original

    transform_s = _time_transform(chunk, dtype, method, warmup, repeats)
    transform_mbps = (original / 1e6) / transform_s

    # bit-exact: the transform must invert, and the deflate stream must roundtrip.
    bit_exact = fs.invert(transformed, dtype, method, n) == chunk
    bit_exact = bit_exact and m1_codecs.decompress(
        m1_codecs.compress(transformed, codec, level), codec, level
    ) == transformed

    perplane = None
    if method == "bitplane":
        planes = fs.split_planes(chunk, dtype)
        sign_c = _csize(planes["sign"], codec, level) if planes["sign"] else 0
        exp_c = _csize(planes["exp"], codec, level) if planes["exp"] else 0
        mant_raw = len(planes["mantissa"])
        mant_c = _csize(planes["mantissa"], codec, level) if planes["mantissa"] else 0
        # Per the technique ("don't compress the mantissa"): store mantissa RAW.
        perplane_comp = sign_c + exp_c + mant_raw
        perplane = {
            "alpha": perplane_comp / original,
            "alpha_sign": (sign_c / len(planes["sign"])) if planes["sign"] else None,
            "alpha_exp": (exp_c / len(planes["exp"])) if planes["exp"] else None,
            "alpha_mant": (mant_c / len(planes["mantissa"])) if planes["mantissa"] else None,
            "mantissa_stored_raw": True,
            "plane_bytes": {
                "sign": len(planes["sign"]),
                "exp": len(planes["exp"]),
                "mantissa": len(planes["mantissa"]),
            },
        }

    return {
        "dtype": dtype,
        "method": method,
        "codec": codec,
        "level": level,
        "original_size": original,
        "n_values": n,
        "alpha_raw": alpha_raw,
        "alpha_concat": alpha_concat,
        "transform_throughput_mbps": transform_mbps,
        "bit_exact": bit_exact,
        "perplane": perplane,
    }
