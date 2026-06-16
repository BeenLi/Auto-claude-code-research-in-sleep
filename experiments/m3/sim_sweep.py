"""Reproducible LLMServingSim link_bw sweep for the M3 cross-check (runs on myDevbox).

Generates one long-context PD request, sweeps the cluster ``link_bw``, runs the simulator, and
records TTFT(link_bw) -> JSON. The analysis (crosscheck.py) confirms the sim's PD KV transfer is
bandwidth-limited (TTFT ~ A + bytes/link_bw), validating the Layer-1 frontier physics.

Usage (on myDevbox, inside the LLMServingSim repo with the venv on PATH):
    PATH=$PWD/env/bin:$PATH python sim_sweep.py \
        --sim-root . --out m3_outputs/sim_sweep.json \
        --input-toks 2048 --link-bw 1 2 4 8 16 32 64
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

# The PD path crashes with prefix caching on this branch; disable it (baseline behaviour unaffected).
BASE_FLAGS = ["--dtype", "bfloat16", "--block-size", "16", "--no-enable-prefix-caching"]


def make_trace_record(*, input_toks: int, output_toks: int = 2) -> dict:
    """A single long-context request: large prompt (big KV), minimal decode, arrival at t=0."""
    return {
        "input_toks": input_toks,
        "output_toks": output_toks,
        "arrival_time_ns": 0,
        "input_tok_ids": list(range(1, input_toks + 1)),
        "output_tok_ids": list(range(1, output_toks + 1)),
    }


def parse_ttft_ns(csv_path: str) -> int:
    """Read TTFT (ns) of the (single) request from a serving output CSV."""
    with open(csv_path) as f:
        rows = [line for line in f.read().splitlines() if line.strip()]
    header, last = rows[0].split(","), rows[-1]
    ttft_idx = header.index("TTFT")
    # split only up to the ITL list (which contains commas); TTFT precedes it.
    fields = last.split(",")
    return int(fields[ttft_idx])


def run_sweep(
    *, sim_root: str, link_bw: list[float], input_toks: int, output_toks: int,
    base_cluster: str = "configs/cluster/single_node_pd_instance.json", workdir: str = "m3_work",
) -> dict:  # pragma: no cover - orchestration, exercised on myDevbox
    root = Path(sim_root)
    wd = root / workdir
    wd.mkdir(parents=True, exist_ok=True)

    trace = wd / f"ctx_{input_toks}.jsonl"
    trace.write_text(json.dumps(make_trace_record(input_toks=input_toks, output_toks=output_toks)) + "\n")

    base = json.loads((root / base_cluster).read_text())
    ttft_by_bw: dict[str, int] = {}
    for bw in link_bw:
        cfg = copy.deepcopy(base)
        cfg["link_bw"] = bw
        cfg_path = wd / f"pd_bw{bw}.json"
        cfg_path.write_text(json.dumps(cfg))
        out_csv = wd / f"ttft_bw{bw}.csv"
        cmd = [
            sys.executable, "-m", "serving", "--cluster-config", str(cfg_path),
            *BASE_FLAGS, "--dataset", str(trace), "--output", str(out_csv), "--num-reqs", "1",
        ]
        subprocess.run(cmd, cwd=str(root), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ttft_by_bw[str(bw)] = parse_ttft_ns(str(out_csv))

    return {
        "workload": {"input_toks": input_toks, "output_toks": output_toks, "model": "meta-llama/Llama-3.1-8B", "dtype": "bfloat16"},
        "link_bw_unit": "GB/s",
        "ttft_ns_by_link_bw": ttft_by_bw,
    }


def main() -> None:  # pragma: no cover
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sim-root", default=".")
    p.add_argument("--out", required=True)
    p.add_argument("--input-toks", type=int, default=2048)
    p.add_argument("--output-toks", type=int, default=2)
    p.add_argument("--link-bw", type=float, nargs="+", default=[1, 2, 4, 8, 16, 32, 64])
    args = p.parse_args()

    result = run_sweep(
        sim_root=args.sim_root, link_bw=args.link_bw, input_toks=args.input_toks, output_toks=args.output_toks
    )
    out = Path(args.sim_root) / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
