"""One-shot equivalence check: our numpy/ml_dtypes NetZIP port vs the artifact's torch code.

Usage (on the box, venv with torch):
    python check_netzip_equivalence.py /path/to/MICRO-2025-NetZIP/compression_ratio_calculation/compression_ratio_calculation.py

Verifies byte_group / bit_group / diff_min outputs are byte-identical on random bf16
buffers. Exit 0 = port certified; any mismatch prints the failing transform and exits 1.
"""

from __future__ import annotations

import importlib.util
import sys

import numpy as np


def main(artifact_py: str) -> int:
    import torch

    import netzip_kv

    # The artifact imports its full codec set at module top; only the three transform
    # functions are under test here, so stub any missing optional codec/UI deps.
    import types

    for optional in ("snappy", "lz4", "lz4.frame", "zstandard", "tqdm"):
        if importlib.util.find_spec(optional.split(".")[0]) is None and optional not in sys.modules:
            sys.modules[optional] = types.ModuleType(optional)

    spec = importlib.util.spec_from_file_location("netzip_artifact", artifact_py)
    art = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(art)

    rng = np.random.default_rng(11)
    failures = 0
    for n in (4096, 65536):
        import ml_dtypes

        buf = rng.standard_normal(n).astype(ml_dtypes.bfloat16).tobytes()
        t = torch.frombuffer(bytearray(buf), dtype=torch.int16)

        pairs = [
            ("byte_group", netzip_kv.byte_group(buf), art.byte_group_bfloat16(t)),
            ("bit_group", netzip_kv.bit_group(buf), art.bit_group_bfloat16(t)),
        ]
        base = netzip_kv.min_base(buf)
        ours_diff = netzip_kv.diff_min(buf)
        theirs_diff = art.difference_encode_bfloat16(t, base).numpy().tobytes()
        pairs.append(("diff_min", ours_diff, theirs_diff))

        for name, ours, theirs in pairs:
            ok = ours == theirs
            print(f"n={n} {name}: {'OK' if ok else 'MISMATCH'}")
            failures += not ok

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
