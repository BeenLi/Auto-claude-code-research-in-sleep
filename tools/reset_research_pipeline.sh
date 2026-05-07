#!/usr/bin/env bash
# reset_research_pipeline.sh - Remove project-local ARIS research pipeline artifacts.
#
# Default mode is dry-run. Pass --apply to delete the fixed allowlist of
# pipeline artifacts and reset AGENT.md's Pipeline Status YAML block to `{}`.

set -euo pipefail

APPLY=false
QUIET=false
PROJECT_PATH=""

DELETE_DIRS=(
    "idea-stage"
    "refine-logs"
    "review-stage"
    "experiments"
    "paper"
    "figures"
    "rebuttal"
    ".aris/traces"
)

DELETE_FILES=(
    "NARRATIVE_REPORT.md"
    "PAPER_PLAN.md"
    "CLAIMS_FROM_RESULTS.md"
    "findings.md"
    "MANIFEST.md"
    "ISSUE_BOARD.md"
    "STRATEGY_PLAN.md"
)

usage() {
    cat <<'EOF'
Usage:
  bash tools/reset_research_pipeline.sh [project_path] [--apply] [--quiet]

Options:
  --apply    Delete pipeline artifacts and reset AGENT.md. Without this, dry-run only.
  --quiet    Suppress non-error output.
  --help     Show this help.

Deletes only a fixed project-relative allowlist:
  idea-stage/ refine-logs/ review-stage/ experiments/ paper/ figures/ rebuttal/ .aris/traces/
  NARRATIVE_REPORT.md PAPER_PLAN.md CLAIMS_FROM_RESULTS.md findings.md MANIFEST.md
  ISSUE_BOARD.md STRATEGY_PLAN.md
EOF
}

log() {
    "$QUIET" && return 0
    echo "$@"
}

die() {
    echo "Error: $*" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --apply)
            APPLY=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --*)
            die "unknown option: $1"
            ;;
        *)
            if [[ -n "$PROJECT_PATH" ]]; then
                die "multiple project paths provided: $PROJECT_PATH and $1"
            fi
            PROJECT_PATH="$1"
            shift
            ;;
    esac
done

PROJECT_PATH="${PROJECT_PATH:-$(pwd)}"
[[ -d "$PROJECT_PATH" ]] || die "project path does not exist: $PROJECT_PATH"
PROJECT_PATH="$(cd "$PROJECT_PATH" && pwd -P)"
AGENT_FILE="$PROJECT_PATH/AGENT.md"
[[ -f "$AGENT_FILE" ]] || die "AGENT.md not found at $AGENT_FILE"

safe_path() {
    local rel="$1"
    case "$rel" in
        ""|/*|..|../*|*/..|*/../*)
            die "unsafe project-relative path in allowlist: $rel"
            ;;
    esac
    printf "%s/%s\n" "$PROJECT_PATH" "$rel"
}

validate_agent_status_block() {
    python3 - "$AGENT_FILE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
lines = path.read_text().splitlines(keepends=True)

try:
    header_idx = next(i for i, line in enumerate(lines) if line.strip() == "## Pipeline Status")
except StopIteration:
    sys.stderr.write(f"Error: Pipeline Status section not found in {path}\n")
    sys.exit(1)

try:
    fence_start = next(i for i in range(header_idx + 1, len(lines)) if lines[i].startswith("```"))
except StopIteration:
    sys.stderr.write(f"Error: Pipeline Status fenced code block not found in {path}\n")
    sys.exit(1)

try:
    next(i for i in range(fence_start + 1, len(lines)) if lines[i].startswith("```"))
except StopIteration:
    sys.stderr.write(f"Error: Pipeline Status fenced code block is not closed in {path}\n")
    sys.exit(1)
PY
}

reset_agent_status_block() {
    python3 - "$AGENT_FILE" <<'PY'
from pathlib import Path
import os
import sys

path = Path(sys.argv[1])
lines = path.read_text().splitlines(keepends=True)

header_idx = next(i for i, line in enumerate(lines) if line.strip() == "## Pipeline Status")
fence_start = next(i for i in range(header_idx + 1, len(lines)) if lines[i].startswith("```"))
fence_end = next(i for i in range(fence_start + 1, len(lines)) if lines[i].startswith("```"))

new_text = "".join(lines[: fence_start + 1]) + "{}\n" + "".join(lines[fence_end:])
tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
tmp.write_text(new_text)
os.replace(tmp, path)
PY
}

validate_agent_status_block

ACTION="dry-run"
"$APPLY" && ACTION="apply"

log ""
log "ARIS Research Pipeline Reset"
log "  Project:   $PROJECT_PATH"
log "  Action:    $ACTION"
log ""

print_plan_entry() {
    local kind="$1" rel="$2" path
    path="$(safe_path "$rel")"
    if [[ -e "$path" || -L "$path" ]]; then
        log "  REMOVE $kind  $rel"
    else
        log "  SKIP   $kind  $rel (missing)"
    fi
}

for rel in "${DELETE_DIRS[@]}"; do
    print_plan_entry "dir" "$rel"
done
for rel in "${DELETE_FILES[@]}"; do
    print_plan_entry "file" "$rel"
done
log "  RESET AGENT.md Pipeline Status -> {}"

if ! "$APPLY"; then
    log ""
    log "(dry-run) no changes made; rerun with --apply to reset"
    exit 0
fi

for rel in "${DELETE_DIRS[@]}"; do
    path="$(safe_path "$rel")"
    if [[ -e "$path" || -L "$path" ]]; then
        rm -rf "$path"
    fi
done

for rel in "${DELETE_FILES[@]}"; do
    path="$(safe_path "$rel")"
    if [[ -e "$path" || -L "$path" ]]; then
        rm -f "$path"
    fi
done

reset_agent_status_block

log ""
log "OK Research pipeline reset complete."
