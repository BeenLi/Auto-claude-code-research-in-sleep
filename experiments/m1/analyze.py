"""Aggregate the M1 corpus and emit the GREEN/YELLOW/RED go/no-go.

Decision rule (M1_CHECKLIST §3.4, mirrored in EVALUATION_CONTRACT):
- GREEN  : a BF3 codec (deflate/lz4) reaches p50 ratio <= 0.75 at a chunk < 16MB.
- YELLOW : that target is met only at large chunks (>=16MB) or only via a non-BF3
           codec (zstd), or some configs sit in the marginal (0.75, 0.85] band.
- RED    : every phase x codec p50 ratio > 0.85 -> pivot to the negative-result paper.

`decide` is pure and unit-tested; loading/grouping/reporting is glue.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

_BF3_CODECS = {"deflate", "lz4"}
_16MB = 16 * (1 << 20)
_GREEN_RATIO = 0.75
_RED_RATIO = 0.85


def is_bf3_codec(codec: str) -> bool:
    return codec in _BF3_CODECS


def decide(records):
    """records: list of {codec, is_bf3, chunk_size_bytes, ratio_p50}. Returns (verdict, reason)."""
    if not records:
        raise ValueError("no records to decide on")

    green = [r for r in records if r["is_bf3"] and r["ratio_p50"] <= _GREEN_RATIO and r["chunk_size_bytes"] < _16MB]
    if green:
        g = min(green, key=lambda r: r["ratio_p50"])
        return "GREEN", f"BF3 codec {g['codec']} reaches p50={g['ratio_p50']:.3f} at chunk<16MB"

    yellow = [
        r
        for r in records
        if r["ratio_p50"] <= _GREEN_RATIO
        and ((r["is_bf3"] and r["chunk_size_bytes"] >= _16MB) or not r["is_bf3"])
    ]
    if yellow:
        return "YELLOW", "profitable ratio met only at large chunks (>=16MB) or via a non-BF3 codec"

    if all(r["ratio_p50"] > _RED_RATIO for r in records):
        return "RED", "all phase x codec p50 ratios > 0.85 — pivot to negative-result paper"

    return "YELLOW", "marginal: some p50 ratios in (0.75, 0.85]"


def load_rows(path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def aggregate(rows):
    """Collapse rows into per (phase, dtype, codec, chunk_size) p50-ratio records."""
    groups = defaultdict(list)
    for r in rows:
        if r["codec"] == "none":
            continue  # raw reference, ratio == 1.0 by construction
        key = (r["phase"], r["dtype"], r["codec"], r["chunk_size_bytes"])
        groups[key].append(r["ratio"])
    records = []
    for (phase, dtype, codec, chunk), ratios in groups.items():
        records.append(
            {
                "phase": phase,
                "dtype": dtype,
                "codec": codec,
                "is_bf3": is_bf3_codec(codec),
                "chunk_size_bytes": chunk,
                "ratio_p50": statistics.median(ratios),
                "n": len(ratios),
            }
        )
    return records


def analyze_file(corpus_path, out_path):
    rows = load_rows(corpus_path)
    records = aggregate(rows)
    verdict, reason = decide(records)
    result = {
        "verdict": verdict,
        "reason": reason,
        "n_rows": len(rows),
        "n_configs": len(records),
        "records": sorted(records, key=lambda r: r["ratio_p50"]),
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description="M1 corpus analysis + go/no-go")
    ap.add_argument("--corpus", default="m1_outputs/compressibility_corpus.jsonl")
    ap.add_argument("--out", default="m1_outputs/threshold_analysis.json")
    args = ap.parse_args(argv)
    result = analyze_file(args.corpus, args.out)
    print(f"VERDICT: {result['verdict']} — {result['reason']}")
    print(f"  rows={result['n_rows']} configs={result['n_configs']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
