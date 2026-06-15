"""Cross-validate synthetic vs HF-captured compression-ratio distributions.

This is M1's validity guard: at overlapping (phase, dtype, codec, size) configs,
the synthetic generator's ratio distribution must match the captured one, else the
full synthetic sweep cannot be trusted and the generator must be recalibrated.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def ratio_summary(ratios) -> dict:
    if len(ratios) == 0:
        raise ValueError("empty ratio list")
    arr = np.asarray(ratios, dtype=float)
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
    }


@dataclass
class ComparisonResult:
    status: str  # "match" | "divergent"
    syn_p50: float
    cap_p50: float
    abs_delta_p50: float
    ratio_tol: float


def compare_config(synthetic_ratios, captured_ratios, *, ratio_tol: float = 0.05) -> ComparisonResult:
    syn = ratio_summary(synthetic_ratios)
    cap = ratio_summary(captured_ratios)
    delta = abs(syn["p50"] - cap["p50"])
    return ComparisonResult(
        status="match" if delta <= ratio_tol else "divergent",
        syn_p50=syn["p50"],
        cap_p50=cap["p50"],
        abs_delta_p50=delta,
        ratio_tol=ratio_tol,
    )


_COMPARE_KEY = ("phase", "tensor_type", "dtype", "codec", "level", "chunk_size_bytes")


def _key(row):
    return tuple(row[k] for k in _COMPARE_KEY)


def compare_corpora(synthetic_rows, captured_rows, *, ratio_tol: float = 0.05):
    """Compare ratio distributions at every (phase,ttype,dtype,codec,level,size) present in both."""
    from collections import defaultdict

    syn, cap = defaultdict(list), defaultdict(list)
    for r in synthetic_rows:
        if r["codec"] != "none":
            syn[_key(r)].append(r["ratio"])
    for r in captured_rows:
        if r["codec"] != "none":
            cap[_key(r)].append(r["ratio"])
    shared = sorted(set(syn) & set(cap))
    return [(k, compare_config(syn[k], cap[k], ratio_tol=ratio_tol)) for k in shared]


def main(argv=None):
    import argparse
    import json
    from pathlib import Path

    ap = argparse.ArgumentParser(description="M1 synthetic-vs-captured validity guard")
    ap.add_argument("--synthetic", default="m1_outputs/compressibility_corpus.jsonl")
    ap.add_argument("--captured", default="m1_outputs/captured_corpus.jsonl")
    ap.add_argument("--ratio-tol", type=float, default=0.05)
    args = ap.parse_args(argv)

    def _load(p):
        with Path(p).open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    results = compare_corpora(_load(args.synthetic), _load(args.captured), ratio_tol=args.ratio_tol)
    if not results:
        print("NO OVERLAP: no shared (phase,dtype,codec,level,size) configs to compare")
        return 0
    n_match = sum(1 for _, r in results if r.status == "match")
    for key, r in results:
        print(f"[{r.status:9}] {key}  syn_p50={r.syn_p50:.3f} cap_p50={r.cap_p50:.3f} d={r.abs_delta_p50:.3f}")
    frac = n_match / len(results)
    verdict = "GENERATOR VALIDATED" if frac >= 0.8 else "RECALIBRATE GENERATOR"
    print(f"\n{verdict}: {n_match}/{len(results)} configs match (tol={args.ratio_tol})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
