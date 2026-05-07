#!/usr/bin/env bash
# Backward-compatible wrapper for the ARIS Codex project-local installer.
#
# New scripts should call tools/install_aris_codex.sh directly. This wrapper
# keeps the old --reviewer entry point alive and maps reviewer modes to the
# Codex mirror plus optional reviewer overlays.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SCRIPT="$SCRIPT_DIR/install_aris_codex.sh"

PROJECT_PATH="$PWD"
REVIEWER="codex"
DRY_RUN=false
QUIET=false
NO_DOC=false
WITH_DOC=false
RECONCILE=false
UNINSTALL=false
ARIS_REPO=""
PASSTHROUGH=()

usage() {
    cat <<'EOF'
install_codex_skills.sh - compatibility wrapper for install_aris_codex.sh

Usage:
  bash tools/install_codex_skills.sh [--project PATH] [--reviewer codex|claude|gemini] [options]

Options:
  --project PATH       Project root to install into. Default: current directory.
  --reviewer NAME      codex, claude, or gemini. Default: codex.
  --reconcile          Reconcile an existing install.
  --uninstall          Remove only manifest-managed entries.
  --aris-repo PATH     Override ARIS repo discovery.
  --dry-run            Show planned changes without writing.
  --quiet              Reduce output.
  --with-doc           Opt in to AGENTS.md managed block update.
  --no-doc             Legacy compatibility; docs are skipped by default.
  --no-mcp             Accepted for legacy callers; no-op.
  -h, --help           Show this help.

Reviewer mapping:
  codex   -> install_aris_codex.sh
  claude  -> install_aris_codex.sh --with-claude-review-overlay
  gemini  -> install_aris_codex.sh --with-gemini-review-overlay
EOF
}

die() {
    echo "error: $*" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project)
            PROJECT_PATH="${2:?--project requires PATH}"
            shift 2
            ;;
        --reviewer)
            REVIEWER="${2:?--reviewer requires codex, claude, or gemini}"
            shift 2
            ;;
        --reconcile)
            RECONCILE=true
            shift
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --aris-repo)
            ARIS_REPO="${2:?--aris-repo requires PATH}"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --with-doc)
            WITH_DOC=true
            shift
            ;;
        --no-doc)
            NO_DOC=true
            shift
            ;;
        --no-mcp)
            # Legacy flag. install_aris_codex.sh does not register MCP servers.
            shift
            ;;
        --replace-link|--clear-stale-lock)
            PASSTHROUGH+=("$1")
            if [[ "$1" == "--replace-link" ]]; then
                PASSTHROUGH+=("${2:?--replace-link requires NAME}")
                shift 2
            else
                shift
            fi
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --*)
            die "unknown option: $1"
            ;;
        *)
            die "unexpected positional argument: $1"
            ;;
    esac
done

[[ -x "$INSTALL_SCRIPT" || -f "$INSTALL_SCRIPT" ]] || die "missing installer: $INSTALL_SCRIPT"

cmd=("bash" "$INSTALL_SCRIPT" "$PROJECT_PATH")

case "$REVIEWER" in
    codex) ;;
    claude) cmd+=("--with-claude-review-overlay") ;;
    gemini) cmd+=("--with-gemini-review-overlay") ;;
    *) die "--reviewer must be one of: codex, claude, gemini" ;;
esac

$RECONCILE && cmd+=("--reconcile")
$UNINSTALL && cmd+=("--uninstall")
[[ -n "$ARIS_REPO" ]] && cmd+=("--aris-repo" "$ARIS_REPO")
$DRY_RUN && cmd+=("--dry-run")
$QUIET && cmd+=("--quiet")
$WITH_DOC && cmd+=("--with-doc")
$NO_DOC && cmd+=("--no-doc")
cmd+=("${PASSTHROUGH[@]}")

exec "${cmd[@]}"
