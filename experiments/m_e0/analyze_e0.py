"""E0 verdict per the pre-registered rule in refine-logs/EVALUATION_CONTRACT_E0.md.

Implements the contract verbatim:
- medians per (model, dtype, method, variant), captured rows only;
- claim statistic = worst-of-modern {non-gpt2} for chan/chan_bt (M1.6 re-registration
  scope), worst-of-all-models for raw/byte_transpose (M1/M1.5 scope);
- per-dtype best path selected under V3 (the HW-dyn proxy);
- GO gates: alpha_V3 <= 0.75 AND delta_V3 <= +0.03 (weak zone: delta <= +0.05);
- V0 must reproduce locked alphas within +-0.005 or no verdict may be read.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

ALPHA_GATE = 0.75
DELTA_STRICT = 0.03
DELTA_WEAK = 0.05
V0_TOLERANCE = 0.005
_EPS = 1e-12

MODERN_EXCLUDE = ("gpt2",)
CHAN_METHODS = {"chan", "chan_bt"}
PATH_CANDIDATES = {
    "bf16": (("bf16", "byte_transpose"), ("bf16", "chan_bt")),
    "fp8_e5m2": (("fp8_e5m2", "raw"), ("fp8_e5m2", "chan")),
}


def _medians(rows) -> dict:
    groups = defaultdict(list)
    for r in rows:
        for vid, a in r["alphas"].items():
            groups[(r["model_size"], r["dtype"], r["method"], vid)].append(a)
    return {k: median(v) for k, v in groups.items()}


def analyze(rows, *, reference=None) -> dict:
    bad = [r for r in rows if not r.get("bit_exact")]
    if bad:
        raise ValueError(f"{len(bad)} rows failed bit_exact — contract requires halting")

    captured = [r for r in rows if r.get("generation_method") == "captured"]
    synthetic = [r for r in rows if r.get("generation_method") == "synthetic"]
    med = _medians(captured)

    models = sorted({r["model_size"] for r in captured})
    modern = [m for m in models if not any(x in m for x in MODERN_EXCLUDE)]

    claim_stats = {}
    for dtype, method, vid in sorted({(d, m, v) for (_, d, m, v) in med}):
        scope = modern if method in CHAN_METHODS else models
        present = [m for m in scope if (m, dtype, method, vid) in med]
        if present:
            claim_stats[(dtype, method, vid)] = max(med[(m, dtype, method, vid)] for m in present)

    paths = {}
    for dtype, candidates in PATH_CANDIDATES.items():
        best = None
        for dt, method in candidates:
            v3 = claim_stats.get((dt, method, "V3"))
            v0 = claim_stats.get((dt, method, "V0"))
            if v3 is None or v0 is None:
                continue
            if best is None or v3 < best["alpha_v3"]:
                best = {"method": method, "alpha_v0": v0, "alpha_v3": v3, "delta_v3": v3 - v0}
        if best is not None:
            best["passes"] = best["alpha_v3"] <= ALPHA_GATE + _EPS and best["delta_v3"] <= DELTA_STRICT + _EPS
            best["passes_weak"] = best["alpha_v3"] <= ALPHA_GATE + _EPS and best["delta_v3"] <= DELTA_WEAK + _EPS
            paths[dtype] = best

    n_strict = sum(1 for p in paths.values() if p["passes"])
    n_weak = sum(1 for p in paths.values() if p["passes_weak"])
    if paths and n_strict == len(paths) and len(paths) >= 2:
        verdict = "STRONG_GO"
    elif n_strict >= 1:
        verdict = "GO_A"
    elif n_weak >= 1:
        verdict = "GO_A_WEAK"
    else:
        verdict = "NO_GO"

    v0_repro = {"ok": True, "failures": []}
    if reference:
        for (model, dtype, method), ref_alpha in reference.items():
            got = med.get((model, dtype, method, "V0"))
            if got is None:
                continue
            if abs(got - ref_alpha) > V0_TOLERANCE:
                v0_repro["failures"].append(
                    {"model": model, "dtype": dtype, "method": method,
                     "reference": ref_alpha, "measured_v0": got}
                )
        v0_repro["ok"] = not v0_repro["failures"]

    return {
        "medians": med,
        "synthetic_medians": _medians(synthetic),
        "claim_stats": claim_stats,
        "paths": paths,
        "verdict": verdict,
        "v0_reproduction": v0_repro,
        "gates": {"alpha": ALPHA_GATE, "delta_strict": DELTA_STRICT, "delta_weak": DELTA_WEAK},
    }


def _jsonable(result: dict) -> dict:
    out = dict(result)
    out["medians"] = {"|".join(map(str, k)): v for k, v in result["medians"].items()}
    out["synthetic_medians"] = {"|".join(map(str, k)): v for k, v in result["synthetic_medians"].items()}
    out["claim_stats"] = {"|".join(map(str, k)): v for k, v in result["claim_stats"].items()}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="E0 verdict per EVALUATION_CONTRACT_E0.md")
    ap.add_argument("--corpus", nargs="+", required=True, help="e0 jsonl row files")
    ap.add_argument("--reference", default=None,
                    help='locked-alpha json: {"model|dtype|method": alpha} (V0 reproduction gate)')
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    rows = []
    for path in args.corpus:
        with open(path, encoding="utf-8") as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())

    reference = None
    if args.reference:
        raw = json.loads(Path(args.reference).read_text(encoding="utf-8"))
        reference = {tuple(k.split("|")): v for k, v in raw.items()}

    result = analyze(rows, reference=reference)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_jsonable(result), indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"],
                      "paths": result["paths"],
                      "v0_reproduction_ok": result["v0_reproduction"]["ok"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
