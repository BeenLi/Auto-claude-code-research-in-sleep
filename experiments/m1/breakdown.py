"""Ad-hoc: p50 compression ratio as a (seq_len x chunk_size) matrix for one dtype/codec.

Answers "does dtype X under codec Y ever drop below the 0.75 ceiling as chunks/seqs grow?"
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict


def _hc(c: int) -> str:
    return f"{c // 1048576}M" if c >= 1048576 else f"{c // 1024}K"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--dtype", required=True)
    ap.add_argument("--codec", default="deflate")
    ap.add_argument("--ceiling", type=float, default=0.75)
    a = ap.parse_args(argv)

    rows = [json.loads(line) for line in open(a.corpus) if line.strip()]
    g = defaultdict(list)
    for r in rows:
        if r["dtype"] == a.dtype and r["codec"] == a.codec:
            g[(r["seq_len"], r["chunk_size_bytes"])].append(r["ratio"])
    if not g:
        print("no matching rows")
        return 0

    seqs = sorted({k[0] for k in g})
    chunks = sorted({k[1] for k in g})
    print(f"{a.dtype} {a.codec} p50 ratio  (rows=seq_len, cols=chunk_size):")
    print("  seq\\chunk" + "".join(f"{_hc(c):>9}" for c in chunks))
    for s in seqs:
        line = f"{s:>10} "
        for c in chunks:
            v = g.get((s, c))
            line += f"{st.median(v):>9.3f}" if v else f"{'-':>9}"
        print(line)
    mn = min(st.median(v) for v in g.values())
    verdict = "CLEARS 0.75 somewhere" if mn <= a.ceiling else f"all ABOVE {a.ceiling}"
    print(f"\nmin p50 over all (seq,chunk) = {mn:.3f}  ->  {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
