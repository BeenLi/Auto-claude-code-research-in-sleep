#!/usr/bin/env python3
"""build_manifest.py — Convert grid specs into queue_manager manifest.json.

Usage:
    python3 build_manifest.py \\
        --config grid_spec.yaml \\
        --output manifest.json

Grid spec YAML format:

project: rx_pressure
backend: cosim_gem5_htsim
cwd: /home/user/rx-pressure
env:
  setup: source env.sh
resources:
  slots:
    - {id: sim0, type: cpu_sim}
    - {id: sim1, type: cpu_sim}
cosim:
  coordinator: external
  window_us: 100
  worker_lifecycle: persistent_file_handshake
  htsim_variant: broadcom_csg_htsim
  ground_truth: rx_decompression_expansion_pressure
phases:
  - name: sanity
    grid:
      ratio: [1.5, 2.0]
    template:
      id: "rx_ratio_${ratio}"
      adapter: cosim_gem5_htsim
      cmd: "python3 run_cosim.py --ratio ${ratio}"
      resources: {slot_type: cpu_sim, cpu_cores: 4, memory_gb: 16}
      outputs:
        required:
          - "results/rx_ratio_${ratio}.json"
"""

import argparse
import itertools
import json
import re
from pathlib import Path


def substitute(template, values):
    """Substitute ${var} placeholders in a string or nested dict."""
    if isinstance(template, str):
        def replace(match):
            key = match.group(1)
            return str(values[key]) if key in values else match.group(0)
        return re.sub(r'\$\{([^}]+)\}', replace, template)
    elif isinstance(template, dict):
        return {k: substitute(v, values) for k, v in template.items()}
    elif isinstance(template, list):
        return [substitute(v, values) for v in template]
    return template


def expand_grid(grid):
    """Cartesian product over grid dict values."""
    keys = list(grid.keys())
    vals = [grid[k] for k in keys]
    for combo in itertools.product(*vals):
        yield dict(zip(keys, combo))


def build(config):
    out = {
        "project": config.get("project", "unknown"),
        "backend": config.get("backend", config.get("adapter", "generic_shell")),
        "cwd": config.get("cwd", "."),
        "max_parallel": config.get("max_parallel", 8),
        "phases": [],
    }
    for key in (
        "adapter",
        "env",
        "resources",
        "cosim",
        "outputs",
        "metrics",
        "success",
        "retry",
        "timeout",
        "conda",
        "conda_hook",
        "gpus",
        "gpu_free_threshold_mib",
        "oom_retry",
    ):
        if key in config:
            out[key] = config[key]
    if "resources" not in out and "gpus" in out:
        out["resources"] = {
            "slots": [
                {"id": f"gpu{gpu}", "type": "gpu", "gpu": gpu}
                for gpu in out["gpus"]
            ]
        }
    for phase in config.get("phases", []):
        phase_out = {
            "name": phase["name"],
            "depends_on": phase.get("depends_on", []),
            "jobs": [],
        }
        grid = phase.get("grid", {})
        template = phase.get("template", {})
        if not grid:
            # Single job in this phase
            job = {
                "id": template.get("id", phase["name"]),
                "cmd": template["cmd"],
            }
            for key, value in template.items():
                if key not in job:
                    job[key] = substitute(value, {})
            if "outputs" in job and "expected_output" not in job:
                required = job["outputs"].get("required", [])
                if required:
                    job["expected_output"] = required[0]
            phase_out["jobs"].append(job)
        else:
            for values in expand_grid(grid):
                job = {
                    "id": substitute(template["id"], values),
                    "cmd": substitute(template["cmd"], values),
                }
                for key, value in template.items():
                    if key not in job:
                        job[key] = substitute(value, values)
                if "expected_output" in template:
                    job["expected_output"] = substitute(template["expected_output"], values)
                elif "outputs" in job:
                    required = job["outputs"].get("required", [])
                    if required:
                        job["expected_output"] = required[0]
                phase_out["jobs"].append(job)
        out["phases"].append(phase_out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True,
                    help="Grid-spec YAML or JSON file")
    ap.add_argument("--output", required=True,
                    help="Output manifest.json path")
    args = ap.parse_args()

    p = Path(args.config)
    if p.suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            print("PyYAML not available; install with: pip install pyyaml")
            raise SystemExit(1)
        config = yaml.safe_load(p.read_text())
    else:
        config = json.loads(p.read_text())

    manifest = build(config)
    Path(args.output).write_text(json.dumps(manifest, indent=2))

    total_jobs = sum(len(ph["jobs"]) for ph in manifest["phases"])
    print(f"Built manifest with {len(manifest['phases'])} phases, "
          f"{total_jobs} total jobs")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
