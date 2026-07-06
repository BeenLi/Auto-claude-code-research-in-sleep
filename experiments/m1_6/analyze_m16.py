"""Aggregate the M1.6 layout corpus and emit the pre-registered go/no-go.

Question: how much of TRACE's channel-major layout gain survives the commodity-BF3
single-deflate-stream constraint? Verdict decided on CAPTURED KV only, per model, using
the WORST captured model (conservative), per refine-logs/EVALUATION_CONTRACT_M1.6.md:

- GREEN  : captured bf16 alpha* <= 0.65 or captured fp8_e5m2 alpha* <= 0.70
- YELLOW : captured bf16 alpha* <= 0.695 or captured fp8_e5m2 alpha* <= 0.72
- RED    : otherwise — no method beats the M1.5 baselines (bf16 0.705 / e5m2 0.73) by > 0.01
Disqualifiers: any bit-exact failure => RED; synthetic rows never drive the verdict
(the standard-normal generator has no per-channel scale structure, so it cannot witness
the mechanism); cross-model spread > 0.01 is flagged in the reason.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

GREEN_BF16 = 0.65
YELLOW_BF16 = 0.695
GREEN_E5M2 = 0.70
YELLOW_E5M2 = 0.72
AGREEMENT_SPREAD = 0.01


def aggregate(rows):
    """Collapse rows into per (generation_method, model_size, dtype) best-method records."""
    by_method = defaultdict(lambda: {"concat": [], "raw": [], "bit_exact": True})
    for r in rows:
        key = (r["generation_method"], r["model_size"], r["dtype"], r["method"])
        by_method[key]["concat"].append(r["alpha_concat"])
        by_method[key]["raw"].append(r["alpha_raw"])
        if not r["bit_exact"]:
            by_method[key]["bit_exact"] = False

    by_src = defaultdict(list)
    for (gen, model, dtype, method), v in by_method.items():
        by_src[(gen, model, dtype)].append(
            (method, statistics.median(v["concat"]), statistics.median(v["raw"]), v["bit_exact"])
        )

    out = []
    for (gen, model, dtype), lst in by_src.items():
        best_method, best_alpha = min(((m[0], m[1]) for m in lst), key=lambda x: x[1])
        per_method = {m[0]: m[1] for m in lst}
        out.append(
            {
                "generation_method": gen,
                "model_size": model,
                "dtype": dtype,
                "raw_alpha": statistics.median([m[2] for m in lst]),
                "best_alpha": best_alpha,
                "best_method": best_method,
                "per_method_alpha": per_method,
                "bit_exact": all(m[3] for m in lst),
            }
        )
    return out


def decide(records):
    """records: aggregate() output. Returns (verdict, reason)."""
    if not records:
        raise ValueError("no records to decide on")

    if not all(r["bit_exact"] for r in records):
        bad = sorted({(r["model_size"], r["dtype"]) for r in records if not r["bit_exact"]})
        return "RED", f"bit-exact failure(s) in {bad} — disqualifying regardless of alpha"

    captured = [r for r in records if r["generation_method"] == "captured"]
    if not captured:
        return "RED", "no captured rows — synthetic cannot witness the channel-major mechanism"

    # Worst (max) best_alpha across captured models, per dtype; spread for the agreement flag.
    per_dtype = defaultdict(dict)
    for r in captured:
        per_dtype[r["dtype"]][r["model_size"]] = r["best_alpha"]

    def worst(dtype):
        vals = per_dtype.get(dtype, {})
        return max(vals.values()) if vals else None

    def spread(dtype):
        vals = list(per_dtype.get(dtype, {}).values())
        return (max(vals) - min(vals)) if len(vals) > 1 else 0.0

    bf16, e5m2 = worst("bf16"), worst("fp8_e5m2")
    flags = [
        f"{d} cross-model spread {spread(d):.3f} > {AGREEMENT_SPREAD}"
        for d in ("bf16", "fp8_e5m2")
        if per_dtype.get(d) and spread(d) > AGREEMENT_SPREAD
    ]
    flag_s = f" [models disagree: {'; '.join(flags)}]" if flags else ""

    if (bf16 is not None and bf16 <= GREEN_BF16) or (e5m2 is not None and e5m2 <= GREEN_E5M2):
        hits = []
        if bf16 is not None and bf16 <= GREEN_BF16:
            hits.append(f"bf16 alpha*={bf16:.3f} <= {GREEN_BF16}")
        if e5m2 is not None and e5m2 <= GREEN_E5M2:
            hits.append(f"fp8_e5m2 alpha*={e5m2:.3f} <= {GREEN_E5M2}")
        return "GREEN", f"channel-major layout clears the pre-registered gate on captured KV: {'; '.join(hits)}{flag_s}"

    if (bf16 is not None and bf16 <= YELLOW_BF16) or (e5m2 is not None and e5m2 <= YELLOW_E5M2):
        parts = []
        if bf16 is not None:
            parts.append(f"bf16 alpha*={bf16:.3f}")
        if e5m2 is not None:
            parts.append(f"fp8_e5m2 alpha*={e5m2:.3f}")
        return "YELLOW", (
            f"real but partial gain on captured KV ({', '.join(parts)}): TRACE's mechanism survives "
            f"commodity decode only partially{flag_s}"
        )

    parts = [f"{d} alpha*={worst(d):.3f}" for d in ("bf16", "fp8_e5m2") if worst(d) is not None]
    return "RED", (
        f"no layout method beats the M1.5 baselines by > 0.01 on captured KV ({', '.join(parts)}): "
        f"channel-major structure is unreachable through a single deflate stream{flag_s}"
    )


def load_rows(path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def analyze_files(corpus_paths, out_path):
    rows = []
    for p in corpus_paths:
        rows.extend(load_rows(p))
    agg = aggregate(rows)
    verdict, reason = decide(agg)
    result = {
        "verdict": verdict,
        "reason": reason,
        "criteria": {
            "green": {"bf16": GREEN_BF16, "fp8_e5m2": GREEN_E5M2},
            "yellow": {"bf16": YELLOW_BF16, "fp8_e5m2": YELLOW_E5M2},
        },
        "n_rows": len(rows),
        "records": sorted(agg, key=lambda r: (r["generation_method"], r["model_size"], r["dtype"])),
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _print_table(result):
    print(f"VERDICT: {result['verdict']} — {result['reason']}")
    print(f"  rows={result['n_rows']}")
    print(f"  {'gen':9} {'model':12} {'dtype':10} {'raw':>6} {'best':>6} {'method':16} methods")
    for r in result["records"]:
        pm = " ".join(f"{m}={a:.3f}" for m, a in sorted(r["per_method_alpha"].items()))
        print(
            f"  {r['generation_method']:9} {r['model_size']:12} {r['dtype']:10} "
            f"{r['raw_alpha']:.3f} {r['best_alpha']:.3f} {r['best_method']:16} {pm}"
        )


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description="M1.6 layout analysis + go/no-go")
    ap.add_argument("--corpus", nargs="+", default=["m16_outputs/layout_corpus.jsonl"])
    ap.add_argument("--out", default="m16_outputs/layout_analysis.json")
    args = ap.parse_args(argv)
    result = analyze_files(args.corpus, args.out)
    _print_table(result)
    print(f"  -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
