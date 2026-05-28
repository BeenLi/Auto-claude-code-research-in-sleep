#!/usr/bin/env bash
set -euo pipefail

idea_report="idea-stage/IDEA_REPORT.md"
experiment_plan="refine-logs/EXPERIMENT_PLAN.md"
final_proposal="refine-logs/FINAL_PROPOSAL.md"
selected_idea=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --idea-report)
      idea_report="${2:?missing value for --idea-report}"
      shift 2
      ;;
    --experiment-plan)
      experiment_plan="${2:?missing value for --experiment-plan}"
      shift 2
      ;;
    --final-proposal)
      final_proposal="${2:?missing value for --final-proposal}"
      shift 2
      ;;
    --selected-idea)
      selected_idea="${2:?missing value for --selected-idea}"
      shift 2
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: workflow1_exit_gate.sh [--idea-report PATH] [--experiment-plan PATH]
                              [--final-proposal PATH] [--selected-idea TEXT]

Validates the selected Workflow 1 idea handoff before entering Workflow 1.5.

The gate enforces every required field listed in
`skills/shared-references/idea-handoff-schema.md` "Workflow 1 Exit Gate":
- IDEA_REPORT.md, FINAL_PROPOSAL.md, EXPERIMENT_PLAN.md all exist.
- The selected idea row has `handoff_to_workflow_1_5: ready`.
- `baseline_artifact_readiness.score` is 1 or 2 (0 cannot be ready).
- `evaluation_feasibility_score` is 4 or 5 (1-3 cannot be ready).
- `refine_verdict` is READY, `refine_overall_score` is at least 9,
  `drift_status` is preserved or corrected, and `handoff_refresh_status`
  is passed.
- `canon_mapping` references both `EC-P*` and `EC-W*`.
- core_baseline, metrics, target_validation_style,
  evaluation_target_clarity, evaluation_feasibility_score,
  evaluation_feasibility_breakdown, baseline_artifact_readiness,
  baseline_verification_delta, negative_evidence_response,
  refine_overall_score, refine_verdict, drift_status, and
  handoff_refresh_status are all present and non-empty.

Selected idea matching is case-insensitive exact match first; if that
misses, the gate falls back to "selected value is a prefix of the row's
idea label" and prints a warning on stderr. Substring matches in the
other direction (row name contained in the selected value) are not
accepted.

Exit codes:
  0  gate passed
  1  gate failed (missing artifact, missing field, invalid value, or
     selected idea not found / not ready)
  2  usage error (unknown argument, missing argument value)
USAGE
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

python3 - "$idea_report" "$experiment_plan" "$final_proposal" "$selected_idea" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path


idea_report = Path(sys.argv[1])
experiment_plan = Path(sys.argv[2])
final_proposal = Path(sys.argv[3])
selected_idea = sys.argv[4].strip()


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"WARN: {message}", file=sys.stderr)


if not idea_report.exists():
    fail(f"missing idea report: {idea_report}")
if not final_proposal.exists():
    fail(f"missing final proposal: {final_proposal}")
if not experiment_plan.exists():
    fail(f"missing experiment plan: {experiment_plan}")

text = idea_report.read_text()
rows: list[list[str]] = []
for line in text.splitlines():
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        continue
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if cells and not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
        rows.append(cells)

# Find only the first table that matches the handoff-summary header signature,
# then collect rows that belong to it. Tables ending earlier don't bleed into
# later ones.
header: list[str] | None = None
records: list[dict[str, str]] = []
for row in rows:
    lowered = [cell.lower() for cell in row]
    if header is None:
        if "handoff_to_workflow_1_5" in lowered and "canon_mapping" in lowered:
            header = lowered
        continue
    if len(row) != len(header):
        # Row width changed — the handoff table has ended.
        break
    records.append(dict(zip(header, row)))

if header is None or not records:
    fail("no Evaluation Handoff Summary row found")

record: dict[str, str] | None = None
if selected_idea:
    selected_lower = selected_idea.lower()
    for candidate in records:
        if candidate.get("idea", "").lower() == selected_lower:
            record = candidate
            break
    if record is None:
        prefix_matches = [
            candidate
            for candidate in records
            if candidate.get("idea", "").lower().startswith(selected_lower)
        ]
        if len(prefix_matches) == 1:
            record = prefix_matches[0]
            warn(
                f"selected idea matched by prefix, not exact label: "
                f"{record.get('idea', '')!r} (pass the full row label to silence this warning)"
            )
        elif len(prefix_matches) > 1:
            labels = ", ".join(repr(c.get("idea", "")) for c in prefix_matches)
            fail(
                f"selected idea {selected_idea!r} is ambiguous; "
                f"matches multiple rows by prefix: {labels}"
            )
    if record is None:
        fail(f"selected idea not found in handoff table: {selected_idea}")
else:
    for candidate in records:
        if candidate.get("handoff_to_workflow_1_5", "").lower() == "ready":
            record = candidate
            break
    if record is None:
        fail("no ready handoff row found")

required_nonempty = [
    "baseline_artifact_readiness",
    "core_baseline",
    "metrics",
    "target_validation_style",
    "evaluation_target_clarity",
    "evaluation_feasibility_score",
    "evaluation_feasibility_breakdown",
    "baseline_verification_delta",
    "negative_evidence_response",
    "refine_overall_score",
    "refine_verdict",
    "drift_status",
    "handoff_refresh_status",
]
for key in required_nonempty:
    if key not in record:
        fail(
            f"handoff table is missing required column: {key} "
            "(add it to the Evaluation Handoff Summary header)"
        )
    if not record.get(key, "").strip():
        fail(f"missing required handoff field: {key}")

handoff = record.get("handoff_to_workflow_1_5", "").lower()
baseline_readiness = record.get("baseline_artifact_readiness", "").strip()
baseline_match = re.search(r"(?:^|score\s*=\s*)([0-2])\b", baseline_readiness)
baseline_score = baseline_match.group(1) if baseline_match else ""
canon = record.get("canon_mapping", "")
clarity = record.get("evaluation_target_clarity", "").strip().lower()
feasibility_score = record.get("evaluation_feasibility_score", "").strip()
feasibility_match = re.match(r"([1-5])\b", feasibility_score)
feasibility_value = feasibility_match.group(1) if feasibility_match else ""
feasibility_breakdown = record.get("evaluation_feasibility_breakdown", "")
refine_score_text = record.get("refine_overall_score", "").strip()
try:
    refine_score = float(refine_score_text)
except ValueError:
    refine_score = -1.0
refine_verdict = record.get("refine_verdict", "").strip().upper()
drift_status = record.get("drift_status", "").strip().lower()
handoff_refresh_status = record.get("handoff_refresh_status", "").strip().lower()

if handoff != "ready":
    fail(f"selected idea is not ready for Workflow 1.5: handoff_to_workflow_1_5={handoff or 'missing'}")
if baseline_score == "0":
    fail("baseline_artifact_readiness.score: 0 cannot be marked handoff_to_workflow_1_5: ready")
if baseline_score not in {"1", "2"}:
    fail(
        "baseline_artifact_readiness.score must be 1 or 2 for ready handoff, "
        f"got: {baseline_readiness or 'missing'}"
    )
if not re.search(r"platform=\[?EC-P[0-9A-Za-z_-]*\]?", canon):
    fail("canon_mapping must reference platform=[EC-P*]")
if not re.search(r"workload=\[?EC-W[0-9A-Za-z_-]*\]?", canon):
    fail("canon_mapping must reference workload=[EC-W*]")
if clarity == "missing":
    fail("evaluation_target_clarity: missing blocks Workflow 1.5 (must be clear or partial)")
if feasibility_value not in {"4", "5"}:
    fail(
        "evaluation_feasibility_score must be 4 or 5 for ready handoff, "
        f"got: {feasibility_score or 'missing'}"
    )
for required_breakdown_key in (
    "platform_workload_access",
    "evaluation_adapter_cost",
    "first_signal_runtime",
):
    if required_breakdown_key not in feasibility_breakdown:
        fail(f"evaluation_feasibility_breakdown must include {required_breakdown_key}")
if refine_verdict != "READY":
    fail(f"refine_verdict must be READY for ready handoff, got: {refine_verdict or 'missing'}")
if refine_score < 9:
    fail(f"refine_overall_score must be >= 9 for ready handoff, got: {refine_score_text or 'missing'}")
if drift_status not in {"preserved", "corrected"}:
    fail(f"drift_status must be preserved or corrected for ready handoff, got: {drift_status or 'missing'}")
if handoff_refresh_status != "passed":
    fail(
        "handoff_refresh_status must be passed for ready handoff, "
        f"got: {handoff_refresh_status or 'missing'}"
    )

print(f"Workflow 1 exit gate passed: {record.get('idea', selected_idea or 'selected idea')}")
PY
