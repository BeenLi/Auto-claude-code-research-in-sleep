"""M3 frontier refresh for new claimable alphas (M1.5 byte-transpose bf16, M1.6 layout).

Thin CLI glue over the unit-tested ``analyze_m3.verdict`` — no new math. For each named
(dtype, alpha) scenario it reports B_crit across the FPGA compress band plus the
free-compressor ceiling B < (1 - alpha) * D_egress, so the band shift vs the original
FP8_E5M2-only envelope is quantified in one table.

Caveat carried from M1.5/M1.6 contracts: T_xform (sender reorder/transpose) and the
receive-side inverse are NOT in this model yet; alphas here assume the transform is free,
so bf16 rows are slightly optimistic bounds.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import analyze_m3

_INPUTS = analyze_m3._INPUTS


def scenario(name: str, alpha: float) -> dict:
    fpga = _INPUTS["compress_band"]["fpga"]["band_gbps"]
    chunk = _INPUTS["decompress"]["max_tested_chunk_bytes"]
    t_fixed = _INPUTS["decompress"]["t_fixed_s"]
    d_egress = _INPUTS["decompress"]["d_egress_gbps_by_chunk_bytes"][str(chunk)]
    v = analyze_m3.verdict(alpha=alpha, C_band_gbps=fpga, chunk_bytes=chunk, T_fixed_s=t_fixed)
    v["scenario"] = name
    v["wire_saving_pct"] = round((1.0 - alpha) * 100.0, 1)
    v["free_compressor_ceiling_gbps"] = round((1.0 - alpha) * d_egress, 1)
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="M3 frontier refresh across dtype/alpha scenarios")
    ap.add_argument(
        "--scenario", action="append", default=[],
        help="name=alpha, e.g. bf16_m15_byte_transpose=0.705 (repeatable)",
    )
    ap.add_argument("--out", default="m3_outputs/alpha_refresh.json")
    args = ap.parse_args(argv)

    scenarios = [("fp8_e5m2_m1_raw(baseline)", _INPUTS["compression"]["alpha"]["typical"])]
    for s in args.scenario:
        name, _, a = s.partition("=")
        scenarios.append((name, float(a)))

    results = [scenario(n, a) for n, a in scenarios]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")

    hdr = f"{'scenario':36} {'alpha':>6} {'save%':>6} {'ceiling':>8} " + " ".join(
        f"B_crit@{int(c)}G" for c in _INPUTS["compress_band"]["fpga"]["band_gbps"]
    )
    print(hdr)
    for r in results:
        bcs = " ".join(f"{r['b_crit_by_compress_gbps'][c]:9.1f}" for c in sorted(r["b_crit_by_compress_gbps"]))
        print(f"{r['scenario']:36} {r['alpha']:6.3f} {r['wire_saving_pct']:6.1f} "
              f"{r['free_compressor_ceiling_gbps']:8.1f} {bcs}   [{r['verdict']}]")
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
