#!/usr/bin/env bash
# install_codex_skills.sh - Project-local ARIS Codex skill installer.
#
# Purpose:
#   Install the Codex-native ARIS skill set into a project as flat symlinks:
#   <project>/.agents/skills/<skill-name> -> <aris-repo>/skills/skills-codex/<skill-name>
#
# Sync model:
#   Skill content stays live through symlinks. After updating the ARIS repo with
#   `git pull`, existing symlinks immediately see content changes. Re-run this
#   installer when upstream adds/removes skills, or when switching reviewer mode.
#
# Reviewer overlay model:
#   Base skills come from `skills/skills-codex`. In `claude` or `gemini` mode,
#   same-named reviewer-aware skills are linked to the corresponding overlay
#   directory instead. This avoids exposing duplicate skill names.
#
# Usage:
#   bash tools/install_codex_skills.sh [--project PATH] [--reviewer codex|claude|gemini] [options]
#
# Options:
#   --project PATH       Project root to install into. Default: current directory.
#   --reviewer NAME      Reviewer profile: codex, claude, or gemini. Default: codex.
#   --dry-run            Print planned changes without writing files or registering MCP.
#   --no-mcp             Install/switch skill symlinks but skip MCP registration.
#   -h, --help           Show this help text.
#
# Examples:
#   bash tools/install_codex_skills.sh
#   bash tools/install_codex_skills.sh --reviewer claude
#   bash tools/install_codex_skills.sh --reviewer gemini
#   bash tools/install_codex_skills.sh --project /path/to/project --reviewer gemini
#   bash tools/install_codex_skills.sh --dry-run
#
# Sync Notes:
#   - Run `git pull` in the ARIS repo to update existing symlinked skill content.
#   - Re-run this script to reconcile newly added/removed skills.
#   - Re-run with another `--reviewer` value to switch reviewer overlay targets.
#   - The installer writes `.aris/codex-installed-skills.txt` and only removes
#     symlinks listed in that manifest.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIS_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_ROOT="$ARIS_REPO/skills/skills-codex"
CLAUDE_ROOT="$ARIS_REPO/skills/skills-codex-claude-review"
GEMINI_ROOT="$ARIS_REPO/skills/skills-codex-gemini-review"

PROJECT_PATH="$PWD"
REVIEWER="codex"
DRY_RUN=false
NO_MCP=false
DESIRED_FILE=""

usage() {
    sed -n '2,40p' "$0" | sed 's/^# \?//'
}

log() { echo "$@"; }
die() { echo "error: $*" >&2; exit 1; }

abs_path() {
    (cd "$1" 2>/dev/null && pwd) || return 1
}

is_known_reviewer() {
    case "$1" in
        codex|claude|gemini) return 0 ;;
        *) return 1 ;;
    esac
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
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-mcp)
            NO_MCP=true
            shift
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

is_known_reviewer "$REVIEWER" || die "--reviewer must be one of: codex, claude, gemini"
[[ -d "$BASE_ROOT" ]] || die "missing base Codex skills: $BASE_ROOT"

PROJECT_PATH="$(abs_path "$PROJECT_PATH")" || die "project path not found: $PROJECT_PATH"
SKILLS_DIR="$PROJECT_PATH/.agents/skills"
ARIS_DIR="$PROJECT_PATH/.aris"
MANIFEST="$ARIS_DIR/codex-installed-skills.txt"

overlay_root() {
    case "$REVIEWER" in
        claude) echo "$CLAUDE_ROOT" ;;
        gemini) echo "$GEMINI_ROOT" ;;
        *) echo "" ;;
    esac
}

is_installable_base_entry() {
    local path="$1" name="$2"
    [[ -f "$path/SKILL.md" || "$name" == "shared-references" ]]
}

build_desired() {
    local overlay name base_path overlay_path target kind
    overlay="$(overlay_root)"
    for base_path in "$BASE_ROOT"/*; do
        [[ -d "$base_path" ]] || continue
        name="$(basename "$base_path")"
        is_installable_base_entry "$base_path" "$name" || continue
        target="$base_path"
        kind="skill"
        [[ "$name" == "shared-references" ]] && kind="support"
        if [[ -n "$overlay" ]]; then
            overlay_path="$overlay/$name"
            if [[ -f "$overlay_path/SKILL.md" ]]; then
                target="$overlay_path"
                kind="overlay"
            fi
        fi
        printf "%s\t%s\t%s\n" "$name" "$target" "$kind"
    done | sort
}

manifest_target_for() {
    local name="$1"
    [[ -f "$MANIFEST" ]] || return 0
    awk -F'\t' -v n="$name" 'NF==4 && $2==n {print $3; exit}' "$MANIFEST"
}

desired_has_name() {
    local desired_file="$1" name="$2"
    awk -F'\t' -v n="$name" '$1==n {found=1} END {exit(found ? 0 : 1)}' "$desired_file"
}

apply_link() {
    local name="$1" source="$2" target_path="$SKILLS_DIR/$name" previous current
    previous="$(manifest_target_for "$name")"

    if [[ -e "$target_path" || -L "$target_path" ]]; then
        if [[ ! -L "$target_path" ]]; then
            die "refusing to overwrite non-symlink: $target_path"
        fi
        current="$(readlink "$target_path")"
        if [[ "$current" == "$source" ]]; then
            log "  keep   $name -> $source"
            return
        fi
        if [[ -z "$previous" ]]; then
            die "refusing to replace unmanaged symlink: $target_path -> $current"
        fi
        if [[ "$current" != "$previous" ]]; then
            die "managed symlink target changed outside installer: $target_path -> $current"
        fi
        if $DRY_RUN; then
            log "  would update $name -> $source"
        else
            rm "$target_path"
            ln -s "$source" "$target_path"
            log "  update $name -> $source"
        fi
        return
    fi

    if $DRY_RUN; then
        log "  would create $name -> $source"
    else
        ln -s "$source" "$target_path"
        log "  create $name -> $source"
    fi
}

remove_stale_links() {
    local desired_file="$1" kind name source mode target_path current
    [[ -f "$MANIFEST" ]] || return 0
    while IFS=$'\t' read -r kind name source mode; do
        case "$kind" in
            skill|support|overlay) ;;
            *) continue ;;
        esac
        if desired_has_name "$desired_file" "$name"; then
            continue
        fi
        target_path="$SKILLS_DIR/$name"
        if [[ ! -e "$target_path" && ! -L "$target_path" ]]; then
            log "  stale missing $name"
            continue
        fi
        if [[ ! -L "$target_path" ]]; then
            die "refusing to remove non-symlink stale path: $target_path"
        fi
        current="$(readlink "$target_path")"
        if [[ "$current" != "$source" ]]; then
            die "stale managed symlink target changed outside installer: $target_path -> $current"
        fi
        if $DRY_RUN; then
            log "  would remove stale $name"
        else
            rm "$target_path"
            log "  remove stale $name"
        fi
    done < "$MANIFEST"
}

write_manifest() {
    local desired_file="$1" tmp name source kind
    $DRY_RUN && return 0
    tmp="$MANIFEST.tmp.$$"
    {
        printf "version\t1\n"
        printf "reviewer\t%s\n" "$REVIEWER"
        printf "kind\tname\ttarget\tmode\n"
        while IFS=$'\t' read -r name source kind; do
            printf "%s\t%s\t%s\tsymlink\n" "$kind" "$name" "$source"
        done < "$desired_file"
    } > "$tmp"
    mv -f "$tmp" "$MANIFEST"
}

register_mcp() {
    local server
    case "$REVIEWER" in
        codex)
            log "MCP: codex reviewer uses built-in Codex agent path; no MCP registration needed."
            ;;
        claude)
            server="$ARIS_REPO/mcp-servers/claude-review/server.py"
            [[ -f "$server" ]] || die "missing claude-review bridge: $server"
            if $DRY_RUN; then
                log "MCP: would register claude-review MCP -> python3 $server"
            elif $NO_MCP; then
                log "MCP: skipped claude-review registration (--no-mcp)"
            else
                command -v codex >/dev/null 2>&1 || die "codex CLI not found; install Codex or rerun with --no-mcp"
                codex mcp remove claude-review >/dev/null 2>&1 || true
                codex mcp add claude-review -- python3 "$server"
            fi
            ;;
        gemini)
            server="$ARIS_REPO/mcp-servers/gemini-review/server.py"
            [[ -f "$server" ]] || die "missing gemini-review bridge: $server"
            if $DRY_RUN; then
                log "MCP: would register gemini-review MCP -> GEMINI_REVIEW_BACKEND=api python3 $server"
            elif $NO_MCP; then
                log "MCP: skipped gemini-review registration (--no-mcp)"
            else
                command -v codex >/dev/null 2>&1 || die "codex CLI not found; install Codex or rerun with --no-mcp"
                codex mcp remove gemini-review >/dev/null 2>&1 || true
                codex mcp add gemini-review --env GEMINI_REVIEW_BACKEND=api -- python3 "$server"
            fi
            ;;
    esac
}

main() {
    local name source kind count
    DESIRED_FILE="$(mktemp "${TMPDIR:-/tmp}/codex-skills-desired.XXXXXX")"
    trap 'rm -f "${DESIRED_FILE:-}"' EXIT

    build_desired > "$DESIRED_FILE"
    count="$(wc -l < "$DESIRED_FILE" | tr -d ' ')"
    [[ "$count" != "0" ]] || die "no installable Codex skills found in $BASE_ROOT"

    log "Installing ARIS Codex skills"
    log "  project:  $PROJECT_PATH"
    log "  reviewer: $REVIEWER"
    log "  entries:  $count"

    if $DRY_RUN; then
        log "Dry-run: no files will be changed."
    else
        mkdir -p "$SKILLS_DIR" "$ARIS_DIR"
    fi

    while IFS=$'\t' read -r name source kind; do
        apply_link "$name" "$source"
    done < "$DESIRED_FILE"

    remove_stale_links "$DESIRED_FILE"
    write_manifest "$DESIRED_FILE"
    register_mcp

    if $DRY_RUN; then
        log "Dry-run complete."
    else
        log "Installed manifest: $MANIFEST"
    fi
}

main
