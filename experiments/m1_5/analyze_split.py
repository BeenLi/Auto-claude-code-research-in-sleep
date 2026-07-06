"""Aggregate the M1.5 float-split corpus and emit the go/no-go.

Question: does an exponent-grouping transform move a dtype across the 0.75 profitability
gate that M1 measured on RAW bytes? Decided on CAPTURED (real) KV — the standard-normal
synthetic generator inflates the exponent plane (narrow magnitude spread), so synthetic
rehabilitation that does not survive on captured KV is only YELLOW.

- GREEN  : float-split rehabilitates >=1 dtype across 0.75 on CAPTURED KV (dtype gate widens).
- YELLOW : float-split improves >=1 dtype on captured KV but none newly cross 0.75, OR
           rehabilitation appears only on synthetic and is not confirmed on captured.
- RED    : no float-split improvement on captured KV -> M1's raw-byte conclusion stands.

`classify`, `aggregate`, and `decide` are pure and unit-tested; I/O is glue.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

GATE = 0.75
MARGIN = 0.01  # ratio points; below this a change is "neutral" (noise)


def classify(raw: float, split: float, gate: float = GATE, margin: float = MARGIN) -> str:
    if raw > gate and split <= gate:
        return "rehabilitated"
    if split < raw - margin:
        return "improved"
    if split > raw + margin:
        return "regressed"
    return "neutral"


def aggregate(rows):
    """Collapse rows into per (generation_method, dtype) best-split records."""
    by_method = defaultdict(lambda: {"concat": [], "perplane": [], "raw": []})
    for r in rows:
        key = (r["generation_method"], r["dtype"], r["method"])
        by_method[key]["concat"].append(r["alpha_concat"])
        by_method[key]["raw"].append(r["alpha_raw"])
        if r.get("alpha_perplane") is not None:
            by_method[key]["perplane"].append(r["alpha_perplane"])

    by_dt = defaultdict(list)
    for (gen, dtype, method), v in by_method.items():
        by_dt[(gen, dtype)].append(
            (
                method,
                statistics.median(v["concat"]),
                statistics.median(v["perplane"]) if v["perplane"] else None,
                statistics.median(v["raw"]),
            )
        )

    out = []
    for (gen, dtype), lst in by_dt.items():
        raw = statistics.median([m[3] for m in lst])
        best_method, best_concat = min(((m[0], m[1]) for m in lst), key=lambda x: x[1])
        perplanes = [m[2] for m in lst if m[2] is not None]
        out.append(
            {
                "generation_method": gen,
                "dtype": dtype,
                "raw_alpha": raw,
                "best_split_alpha": best_concat,
                "best_method": best_method,
                "best_perplane_alpha": min(perplanes) if perplanes else None,
                "classification": classify(raw, best_concat),
            }
        )
    return out


def decide(records):
    """records: per (generation_method, dtype) dicts with raw_alpha + best_split_alpha."""
    if not records:
        raise ValueError("no records to decide on")

    captured = [r for r in records if r["generation_method"] == "captured"]
    synthetic = [r for r in records if r["generation_method"] == "synthetic"]

    def cls(recs):
        return {r["dtype"]: classify(r["raw_alpha"], r["best_split_alpha"]) for r in recs}

    cap_c = cls(captured)
    syn_c = cls(synthetic)
    cap_rehab = sorted(d for d, c in cap_c.items() if c == "rehabilitated")
    cap_improved = sorted(d for d, c in cap_c.items() if c == "improved")
    syn_rehab = sorted(d for d, c in syn_c.items() if c == "rehabilitated")

    if cap_rehab:
        return "GREEN", f"float-split rehabilitates {cap_rehab} across the {GATE} gate on captured KV"
    if captured and cap_improved:
        return "YELLOW", f"float-split improves {cap_improved} on captured KV but none newly cross {GATE}"
    if syn_rehab:
        return "YELLOW", f"rehabilitation of {syn_rehab} seen only on synthetic KV; not confirmed on captured"
    if captured:
        return "RED", "no float-split improvement on captured KV; M1 raw-byte conclusion stands"
    # synthetic-only fallback
    syn_improved = sorted(d for d, c in syn_c.items() if c == "improved")
    if syn_improved:
        return "YELLOW", f"float-split improves {syn_improved} on synthetic KV (no captured data)"
    return "RED", "no float-split improvement (synthetic only)"


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
        "gate": GATE,
        "n_rows": len(rows),
        "records": sorted(agg, key=lambda r: (r["generation_method"], r["dtype"])),
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _print_table(result):
    print(f"VERDICT: {result['verdict']} — {result['reason']}")
    print(f"  rows={result['n_rows']} gate={result['gate']}")
    hdr = f"  {'gen':9} {'dtype':10} {'raw':>6} {'split':>6} {'method':14} {'perpl':>6} {'class':>14}"
    print(hdr)
    for r in result["records"]:
        pp = r["best_perplane_alpha"]
        pp_s = f"{pp:.3f}" if isinstance(pp, (int, float)) else "  -  "
        print(
            f"  {r['generation_method']:9} {r['dtype']:10} {r['raw_alpha']:.3f} "
            f"{r['best_split_alpha']:.3f} {r['best_method']:14} {pp_s:>6} {r['classification']:>14}"
        )


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description="M1.5 float-split analysis + go/no-go")
    ap.add_argument("--corpus", nargs="+", default=["m15_outputs/split_corpus.jsonl"])
    ap.add_argument("--out", default="m15_outputs/split_analysis.json")
    args = ap.parse_args(argv)
    result = analyze_files(args.corpus, args.out)
    _print_table(result)
    print(f"  -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
