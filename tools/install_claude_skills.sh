#!/usr/bin/env bash
# install_claude_skills.sh - Project-local ARIS Claude skill installer.
#
# Purpose:
#   Install the Claude-native ARIS skill set into a project as flat symlinks:
#   <project>/.claude/skills/<skill-name> -> <aris-repo>/skills/<skill-name>
#
# Sync model:
#   Skill content stays live through symlinks. After updating the ARIS repo with
#   `git pull`, existing symlinks immediately see content changes. Re-run this
#   installer when upstream adds/removes skills.
#
# Safety model:
#   The installer writes `.aris/claude-installed-skills.txt` and only removes
#   symlinks listed in that manifest. It refuses to overwrite real files or
#   unmanaged symlinks.
#
# Usage:
#   bash tools/install_claude_skills.sh [--project PATH] [options]
#
# Options:
#   --project PATH       Project root to install into. Default: current directory.
#   --dry-run            Print planned changes without writing files.
#   -h, --help           Show this help text.
#
# Examples:
#   bash tools/install_claude_skills.sh
#   bash tools/install_claude_skills.sh --project /path/to/project
#   bash tools/install_claude_skills.sh --dry-run
#
# Sync Notes:
#   - Run `git pull` in the ARIS repo to update existing symlinked skill content.
#   - Re-run this script to reconcile newly added/removed skills.
#   - The installer writes `.aris/claude-installed-skills.txt` and only removes
#     symlinks listed in that manifest.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIS_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_ROOT="$ARIS_REPO/skills"

PROJECT_PATH="$PWD"
DRY_RUN=false
DESIRED_FILE=""
SAFE_NAME_REGEX='^[A-Za-z0-9][A-Za-z0-9._-]*$'

usage() {
    sed -n '2,35p' "$0" | sed 's/^# \?//'
}

log() { echo "$@"; }
die() { echo "error: $*" >&2; exit 1; }

abs_path() {
    (cd "$1" 2>/dev/null && pwd) || return 1
}

is_safe_name() {
    [[ "$1" =~ $SAFE_NAME_REGEX ]]
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project)
            PROJECT_PATH="${2:?--project requires PATH}"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
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

[[ -d "$SKILLS_ROOT" ]] || die "missing local Claude skills: $SKILLS_ROOT"
PROJECT_PATH="$(abs_path "$PROJECT_PATH")" || die "project path not found: $PROJECT_PATH"
CLAUDE_SKILLS_DIR="$PROJECT_PATH/.claude/skills"
ARIS_DIR="$PROJECT_PATH/.aris"
MANIFEST="$ARIS_DIR/claude-installed-skills.txt"

is_installable_entry() {
    local path="$1" name="$2"
    case "$name" in
        skills-codex|skills-codex-*|skills-codex.bak)
            return 1
            ;;
    esac
    [[ -f "$path/SKILL.md" || "$name" == "shared-references" ]]
}

build_desired() {
    local path name kind
    for path in "$SKILLS_ROOT"/*; do
        [[ -d "$path" ]] || continue
        name="$(basename "$path")"
        if ! is_safe_name "$name"; then
            log "  skip unsafe name: $name" >&2
            continue
        fi
        is_installable_entry "$path" "$name" || continue
        kind="skill"
        [[ "$name" == "shared-references" ]] && kind="support"
        printf "%s\t%s\t%s\n" "$name" "$path" "$kind"
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
    local name="$1" source="$2" target_path="$CLAUDE_SKILLS_DIR/$name" previous current
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
            skill|support) ;;
            *) continue ;;
        esac
        if desired_has_name "$desired_file" "$name"; then
            continue
        fi
        target_path="$CLAUDE_SKILLS_DIR/$name"
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
        printf "kind\tname\ttarget\tmode\n"
        while IFS=$'\t' read -r name source kind; do
            printf "%s\t%s\t%s\tsymlink\n" "$kind" "$name" "$source"
        done < "$desired_file"
    } > "$tmp"
    mv -f "$tmp" "$MANIFEST"
}

main() {
    local name source kind count
    DESIRED_FILE="$(mktemp "${TMPDIR:-/tmp}/claude-skills-desired.XXXXXX")"
    trap 'rm -f "${DESIRED_FILE:-}"' EXIT

    build_desired > "$DESIRED_FILE"
    count="$(wc -l < "$DESIRED_FILE" | tr -d ' ')"
    [[ "$count" != "0" ]] || die "no installable Claude skills found in $SKILLS_ROOT"

    log "Installing ARIS Claude skills"
    log "  project: $PROJECT_PATH"
    log "  source:  $SKILLS_ROOT"
    log "  entries: $count"

    if $DRY_RUN; then
        log "Dry-run: no files will be changed."
    else
        mkdir -p "$CLAUDE_SKILLS_DIR" "$ARIS_DIR"
    fi

    while IFS=$'\t' read -r name source kind; do
        apply_link "$name" "$source"
    done < "$DESIRED_FILE"

    remove_stale_links "$DESIRED_FILE"
    write_manifest "$DESIRED_FILE"

    if $DRY_RUN; then
        log "Dry-run complete."
    else
        log "Installed manifest: $MANIFEST"
    fi
}

main
