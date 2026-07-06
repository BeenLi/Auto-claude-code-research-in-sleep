"""Golden vectors for the C T-inverse: Python forward transform (unit-tested layout.py)
-> C must invert back to the original bit-exactly.

Run:  PYTHONPATH=../m1:../m1_5:../m1_6 ../.m15venv/bin/python make_golden.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import layout

CASES = [
    # (dtype, method, head_dim, size_bytes)
    ("bf16", "chan_bt", 64, 262144),
    ("bf16", "chan_bt", 128, 262144),
    ("bf16", "chan_bt", 128, 1048576),
    ("fp8_e5m2", "chan", 64, 262144),
    ("fp8_e5m2", "chan", 128, 262144),
    ("fp8_e5m2", "chan", 128, 1048576),
]


def main() -> None:
    out_dir = Path(__file__).parent / "golden"
    out_dir.mkdir(exist_ok=True)
    rng = np.random.default_rng(20260706)
    manifest = []
    for dtype, method, head_dim, size in CASES:
        orig = rng.integers(0, 256, size=size, dtype=np.uint8).tobytes()
        trans = layout.transform(orig, dtype, method, head_dim=head_dim)
        assert len(trans) == size
        n = layout.invert(trans, dtype, method, size // layout.itemsize(dtype), head_dim=head_dim)
        assert n == orig, "python roundtrip broken — abort"
        tag = f"{dtype}_{method}_h{head_dim}_{size}"
        (out_dir / f"{tag}.orig").write_bytes(orig)
        (out_dir / f"{tag}.trans").write_bytes(trans)
        cdt = "bf16" if dtype == "bf16" else "fp8"
        manifest.append(
            {"tag": tag, "dtype_c": cdt, "method": method, "head_dim": head_dim, "bytes": size}
        )
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {len(manifest)} golden pairs -> {out_dir}")


if __name__ == "__main__":
    main()
