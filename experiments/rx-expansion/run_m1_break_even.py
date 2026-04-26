#!/usr/bin/env python3
"""Generate the M1 P0-only analytical break-even evidence pack."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple

from rx_expansion import analytical_model
from rx_expansion import trace_payload


ROOT = Path(__file__).resolve().parent
RESULT_FIELDNAMES = [
    "schedule_source",
    "schedule_realism",
    "payload_source",
    "payload_realism",
    "evidence_level",
    "claim_scope",
    "source_pair",
    "codec_family",
    "offered_load_mode",
    "link_gbps",
    "output_path",
    "output_bw_gbps",
    "decompressor_input_gbps",
    "decompressor_output_gbps",
    "ratio",
    "ratio_threshold",
    "compressed_ingress_gbps",
    "decompressed_output_gbps",
    "effective_output_budget_gbps",
    "input_utilization",
    "output_utilization",
    "decompressor_output_utilization",
    "max_expansion_debt_bytes",
    "pressure_interpretation",
    "is_input_safe",
    "is_output_safe",
    "is_safe",
    "provenance",
]


def load_config(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_p0_profiles(config: Mapping[str, object], config_path: Path) -> List[Dict[str, object]]:
    profile_path = Path(str(config["profile_path"]))
    if not profile_path.is_absolute():
        profile_path = config_path.parent.parent / profile_path
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    profiles = payload["usable_ratio_profiles"]
    normalized = trace_payload.validate_compression_profiles(profiles)
    for profile in normalized:
        if profile["evidence_level"] != "P0_literature_ratio":
            raise trace_payload.ProvenanceError("M1 P0-only pack may only use P0 profiles")
    return normalized


def build_ratio_trace(
    config: Mapping[str, object],
    profiles: Iterable[Mapping[str, object]],
) -> List[Dict[str, object]]:
    return trace_payload.compose_ratio_trace(
        config["schedule_trace"],
        profiles,
        schedule_source=str(config["schedule_source"]),
    )


def build_results(
    config: Mapping[str, object],
    ratio_trace: Iterable[Mapping[str, object]],
) -> List[Dict[str, object]]:
    claim_scope = trace_payload.claim_scope_from_evidence(ratio_trace)
    if claim_scope["claim_scope"] != "analytical_sensitivity_only":
        raise trace_payload.ProvenanceError("M1 pack must remain P0-only analytical sensitivity")

    results: List[Dict[str, object]] = []
    for trace_row in ratio_trace:
        ratio = int(trace_row["original_bytes"]) / int(trace_row["compressed_bytes"])
        for offered_load_mode in config["offered_load_modes"]:
            for link_gbps in config["link_gbps"]:
                for output_path in config["output_paths"]:
                    model = analytical_model.evaluate_profile(
                        ratio=ratio,
                        link_gbps=float(link_gbps),
                        output_bw_gbps=float(output_path["output_bw_gbps"]),
                        decompressor_input_gbps=float(config["decompressor_input_gbps"]),
                        decompressor_output_gbps=float(config["decompressor_output_gbps"]),
                        offered_load_mode=str(offered_load_mode),
                        observation_window_us=float(config["observation_window_us"]),
                    )
                    row = {
                        "schedule_source": trace_row["schedule_source"],
                        "schedule_realism": trace_row["schedule_realism"],
                        "payload_source": trace_row["payload_source"],
                        "payload_realism": trace_row["payload_realism"],
                        "evidence_level": trace_row["evidence_level"],
                        "claim_scope": claim_scope["claim_scope"],
                        "source_pair": trace_row["source_pair"],
                        "codec_family": trace_row["codec_family"],
                        "offered_load_mode": offered_load_mode,
                        "link_gbps": float(link_gbps),
                        "output_path": output_path["name"],
                        "output_bw_gbps": float(output_path["output_bw_gbps"]),
                        "decompressor_input_gbps": float(config["decompressor_input_gbps"]),
                        "decompressor_output_gbps": float(config["decompressor_output_gbps"]),
                        "ratio": ratio,
                        "provenance": trace_row["provenance"],
                    }
                    row.update(model)
                    row["pressure_interpretation"] = pressure_interpretation(
                        offered_load_mode=str(offered_load_mode),
                        is_output_safe=bool(model["is_output_safe"]),
                    )
                    results.append(row)
    return results


def pressure_interpretation(
    *,
    offered_load_mode: str,
    is_output_safe: bool,
) -> str:
    if is_output_safe:
        return "safe"
    if offered_load_mode == "same_original_bytes":
        return "fixed_original_output_path_bottleneck"
    return "ratio_driven_output_pressure"


def write_json(path: Path, config: Mapping[str, object], results: List[Mapping[str, object]]) -> None:
    payload = {
        "title": "M1 P0-only analytical break-even evidence pack",
        "claim_scope": "analytical_sensitivity_only",
        "warning": (
            "This pack uses P0 literature-derived compression profiles only. "
            "It does not claim real communication payload compressibility."
        ),
        "config": config,
        "results": results,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, results: List[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        for row in results:
            writer.writerow({field: row[field] for field in RESULT_FIELDNAMES})


def _unsafe_summary(results: Iterable[Mapping[str, object]]) -> Tuple[int, Counter]:
    counter: Counter = Counter()
    total_unsafe = 0
    for row in results:
        if not bool(row["is_output_safe"]):
            total_unsafe += 1
            key = (
                str(row["codec_family"]),
                str(row["payload_source"]),
                str(row["offered_load_mode"]),
            )
            counter[key] += 1
    return total_unsafe, counter


def write_report(path: Path, results: List[Mapping[str, object]]) -> None:
    total = len(results)
    total_unsafe, unsafe_by_source = _unsafe_summary(results)
    codec_families = sorted({str(row["codec_family"]) for row in results})
    output_paths = sorted({str(row["output_path"]) for row in results})
    modes = sorted({str(row["offered_load_mode"]) for row in results})
    go_nogo = (
        "Conditional Go for M2 model plumbing only"
        if total_unsafe > 0
        else "No-Go until stronger ratios or payload evidence are available"
    )

    lines = [
        "# M1 Go/No-Go Report",
        "",
        "## Scope",
        "",
        "This is a P0-only analytical sensitivity pack. It combines schedule-only smoke traces with literature-derived codec ratios. It does not claim real communication payload compressibility.",
        "",
        "## Go/No-Go",
        "",
        f"- Decision: **{go_nogo}**.",
        f"- Rows evaluated: {total}.",
        f"- Output-unsafe rows: {total_unsafe}.",
        f"- Codec families: {', '.join(codec_families)}.",
        f"- Output paths: {', '.join(output_paths)}.",
        f"- Offered-load modes: {', '.join(modes)}.",
        "",
        "## Unsafe Rows by Codec / Payload / Mode",
        "",
        "| Codec | Payload source | Offered-load mode | Unsafe rows |",
        "| --- | --- | --- | ---: |",
    ]
    if unsafe_by_source:
        for (codec, payload_source, mode), count in sorted(unsafe_by_source.items()):
            lines.append(f"| {codec} | {payload_source} | {mode} | {count} |")
    else:
        lines.append("| none | none | none | 0 |")

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- compressed_line_rate_saturated unsafe rows indicate ratio-driven output pressure under the P0 assumptions.",
            "- same_original_bytes unsafe rows are fixed-output-path bottlenecks, not compression-created receiver pressure.",
            "",
            "## Claim Boundary",
            "",
            "- Claim scope: `analytical_sensitivity_only`.",
            "- P0-only results can justify sensitivity discussion and Go/No-Go triage.",
            "- P0-only results cannot justify a real communication payload claim.",
            "- P1/P2/P3 collection is intentionally out of scope for this M1 pack.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(*, config_path: Path, output_dir: Path) -> Dict[str, Path]:
    config_path = Path(config_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    profiles = load_p0_profiles(config, config_path)
    ratio_trace = build_ratio_trace(config, profiles)
    results = build_results(config, ratio_trace)

    json_path = output_dir / "m1_break_even.json"
    csv_path = output_dir / "m1_break_even.csv"
    report_path = output_dir / "M1_GO_NOGO_REPORT.md"
    write_json(json_path, config, results)
    write_csv(csv_path, results)
    write_report(report_path, results)
    return {
        "json": json_path,
        "csv": csv_path,
        "report": report_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "m1_break_even.json",
        help="Path to M1 break-even config JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results",
        help="Directory for m1_break_even.json/csv and M1_GO_NOGO_REPORT.md.",
    )
    args = parser.parse_args()
    outputs = run(config_path=args.config, output_dir=args.output_dir)
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
