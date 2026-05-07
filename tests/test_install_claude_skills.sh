#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/tools/install_claude_skills.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/aris-claude-skills-test.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

assert_symlink_target() {
    local path="$1" expected="$2"
    [[ -L "$path" ]] || fail "expected symlink: $path"
    local actual
    actual="$(readlink "$path")"
    [[ "$actual" == "$expected" ]] || fail "target mismatch for $path: $actual != $expected"
}

project_install="$TMP_ROOT/install-project"
mkdir -p "$project_install"
bash "$SCRIPT" --project "$project_install" >"$TMP_ROOT/install.out" 2>"$TMP_ROOT/install.err" || {
    cat "$TMP_ROOT/install.err" >&2
    fail "installer failed"
}

assert_symlink_target \
    "$project_install/.claude/skills/idea-discovery" \
    "$REPO_ROOT/skills/idea-discovery"
assert_symlink_target \
    "$project_install/.claude/skills/shared-references" \
    "$REPO_ROOT/skills/shared-references"

[[ ! -e "$project_install/.claude/skills/skills-codex" ]] \
    || fail "must not install Codex skill package as a Claude skill"

manifest="$project_install/.aris/claude-installed-skills.txt"
[[ -f "$manifest" ]] || fail "missing manifest: $manifest"
grep -F $'version\t1' "$manifest" >/dev/null || fail "manifest missing version"
grep -F "skill"$'\t'"idea-discovery"$'\t'"$REPO_ROOT/skills/idea-discovery"$'\t'"symlink" "$manifest" >/dev/null \
    || fail "manifest missing idea-discovery"
grep -F "support"$'\t'"shared-references"$'\t'"$REPO_ROOT/skills/shared-references"$'\t'"symlink" "$manifest" >/dev/null \
    || fail "manifest missing shared-references"

project_dry="$TMP_ROOT/dry-run-project"
mkdir -p "$project_dry"
bash "$SCRIPT" --project "$project_dry" --dry-run >"$TMP_ROOT/dry.out" 2>"$TMP_ROOT/dry.err" || {
    cat "$TMP_ROOT/dry.err" >&2
    fail "dry-run failed"
}
[[ ! -e "$project_dry/.claude" ]] || fail "dry-run created .claude"
[[ ! -e "$project_dry/.aris" ]] || fail "dry-run created .aris"

project_conflict="$TMP_ROOT/conflict-project"
mkdir -p "$project_conflict/.claude/skills/idea-discovery"
printf 'user skill\n' > "$project_conflict/.claude/skills/idea-discovery/SKILL.md"
if bash "$SCRIPT" --project "$project_conflict" >"$TMP_ROOT/conflict.out" 2>"$TMP_ROOT/conflict.err"; then
    fail "installer should refuse user-owned skill directory"
fi
grep -F "refusing to overwrite non-symlink" "$TMP_ROOT/conflict.err" >/dev/null \
    || fail "conflict error did not explain non-symlink refusal"

echo "install_claude_skills tests passed"
