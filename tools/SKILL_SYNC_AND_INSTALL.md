# ARIS Skill Sync and Project Install Guide

This document explains how ARIS skills are authored, mirrored for Codex, and installed into a target repository.

## Skill Trees

Author skills in the main tree:

```text
skills/<skill-name>/SKILL.md
skills/shared-references/*.md
```

Generated or adapted trees:

```text
skills/skills-codex/                 # Codex mirror generated from main skills
skills/skills-codex-claude-review/   # Codex overlay that swaps selected reviewers to Claude MCP
skills/skills-codex-gemini-review/   # Codex overlay that swaps selected reviewers to Gemini MCP
```

The main `skills/` tree is the source of truth. Do not hand-edit `skills/skills-codex/` for normal skill changes; regenerate it from the main tree.

## Sync Main Skills to Codex Mirror

Use `tools/sync_codex_skill_mirror.py`.

Dry-run first:

```bash
python3 tools/sync_codex_skill_mirror.py --dry-run
```

Apply the sync:

```bash
python3 tools/sync_codex_skill_mirror.py --apply
```

Confirm the mirror is clean:

```bash
python3 tools/sync_codex_skill_mirror.py --dry-run
```

Expected clean output includes:

```text
changes: 0
clean
```

The sync script:

- Enumerates main skills from `skills/*/SKILL.md`.
- Excludes `skills/skills-codex*` overlay packages.
- Copies each main skill into `skills/skills-codex/<skill-name>/`.
- Copies `skills/shared-references/` into `skills/skills-codex/shared-references/`.
- Removes stale Codex mirror skills no longer present in main `skills/`.
- Applies minimal Codex wording/tool conversion:
  - `mcp__codex__codex` -> `spawn_agent`
  - `mcp__codex__codex-reply` -> `send_input`
  - Codex MCP thread wording -> Codex subagent / agent id wording

The script does not rewrite `skills/skills-codex-claude-review/` or `skills/skills-codex-gemini-review/`.

## Install Codex Skills into a Repo

Preferred installer:

```bash
bash tools/install_aris_codex.sh /path/to/target/repo --dry-run
bash tools/install_aris_codex.sh /path/to/target/repo
```

This creates a project-local flat Codex skill install:

```text
/path/to/target/repo/.agents/skills/<skill-name> -> <aris-repo>/skills/skills-codex/<skill-name>
/path/to/target/repo/.aris/installed-skills-codex.txt
```

By default it does not write agent documentation files. Pass `--with-doc` if you want it to manage an `ARIS-CODEX` block in the target repo's `AGENTS.md`; `--no-doc` is retained as a compatibility no-op.

After ARIS changes or after `git pull`, reconcile the target repo:

```bash
bash tools/install_aris_codex.sh /path/to/target/repo --reconcile
```

Uninstall only manifest-managed Codex skill links:

```bash
bash tools/install_aris_codex.sh /path/to/target/repo --uninstall
```

Use reviewer overlays when the Codex project should route selected review-heavy skills through Claude or Gemini review MCP wrappers:

```bash
bash tools/install_aris_codex.sh /path/to/target/repo --with-claude-review-overlay
bash tools/install_aris_codex.sh /path/to/target/repo --with-gemini-review-overlay
```

To reconcile an existing overlay install:

```bash
bash tools/install_aris_codex.sh /path/to/target/repo --reconcile --with-claude-review-overlay
bash tools/install_aris_codex.sh /path/to/target/repo --reconcile --with-gemini-review-overlay
```

Compatibility wrapper:

```bash
bash tools/install_codex_skills.sh --project /path/to/target/repo --reviewer codex
bash tools/install_codex_skills.sh --project /path/to/target/repo --reviewer claude
bash tools/install_codex_skills.sh --project /path/to/target/repo --reviewer gemini
```

The wrapper maps:

```text
--reviewer codex  -> install_aris_codex.sh
--reviewer claude -> install_aris_codex.sh --with-claude-review-overlay
--reviewer gemini -> install_aris_codex.sh --with-gemini-review-overlay
```

## Install Claude Skills into a Repo

Use `tools/install_claude_skills.sh` when the target repo is used by Claude Code and should read skills from `.claude/skills`.

For the manifest-managed project installer, `tools/install_aris.sh` is the canonical path. It creates the same flat Claude skill links and also manages the project-local tools helper symlink described below:

```bash
bash tools/install_aris.sh /path/to/target/repo --dry-run --no-doc
bash tools/install_aris.sh /path/to/target/repo --no-doc
```

Dry-run first:

```bash
bash tools/install_claude_skills.sh --project /path/to/target/repo --dry-run
```

Install:

```bash
bash tools/install_claude_skills.sh --project /path/to/target/repo
```

This creates:

```text
/path/to/target/repo/.claude/skills/<skill-name> -> <aris-repo>/skills/<skill-name>
/path/to/target/repo/.aris/claude-installed-skills.txt
```

The Claude installer uses the main `skills/` tree directly. It excludes Codex mirror and overlay packages.

`tools/install_aris.sh` additionally creates:

```text
/path/to/target/repo/.aris/tools -> <aris-repo>/tools
```

This symlink is intentionally not recorded in `installed-skills.txt`. It is treated as managed only when its exact target is `<aris-repo>/tools`; an existing directory, file, or symlink to any other target is user-owned and must be preserved.

After ARIS changes or after `git pull`, re-run the same command to reconcile added or removed skills:

```bash
bash tools/install_claude_skills.sh --project /path/to/target/repo
bash tools/install_aris.sh /path/to/target/repo --reconcile --no-doc
```

Re-running `tools/install_aris.sh` refreshes both the flat skill symlinks and `.aris/tools`, which is required for helper-resolution chains such as `.aris/tools/research_wiki.py` and `.aris/tools/experiment_queue/queue_manager.py`.

Uninstall removes only manifest-managed skill links and removes `.aris/tools` only if it is exactly the managed symlink:

```bash
bash tools/install_aris.sh /path/to/target/repo --uninstall --no-doc
```

User-created `.aris/tools` directories or symlinks to other targets are left in place.

## Recommended Update Flow

When editing a skill:

```bash
# 1. Edit the source skill
$EDITOR skills/<skill-name>/SKILL.md

# 2. Sync the Codex mirror
python3 tools/sync_codex_skill_mirror.py --dry-run
python3 tools/sync_codex_skill_mirror.py --apply
python3 tools/sync_codex_skill_mirror.py --dry-run

# 3. Reconcile installed Codex skills in target repos
bash tools/install_aris_codex.sh /path/to/target/repo --reconcile

# 4. Reconcile installed Claude skills in target repos
bash tools/install_claude_skills.sh --project /path/to/target/repo
bash tools/install_aris.sh /path/to/target/repo --reconcile --no-doc
```

For Codex reviewer overlays, keep the overlay flag when reconciling:

```bash
bash tools/install_aris_codex.sh /path/to/target/repo --reconcile --with-claude-review-overlay
```

## Is `smart_update_codex.sh` Needed?

Short answer: keep it only if copied Codex installs are supported.

The preferred Codex install path is symlink-managed:

```text
install_aris_codex.sh -> .agents/skills/<skill-name> symlinks + manifest
```

For this path, `smart_update_codex.sh` is not needed. A normal update is:

```bash
git pull
python3 tools/sync_codex_skill_mirror.py --apply
bash tools/install_aris_codex.sh /path/to/target/repo --reconcile
```

`smart_update_codex.sh` exists for copied installs, where skills were physically copied into:

```text
~/.codex/skills
/path/to/repo/.agents/skills
```

Copied installs have no manifest telling us whether a diff is upstream-only or a local edit. The smart updater is conservative:

- Adds missing upstream skills.
- Adds missing shared references.
- Replaces only safe overlay updates.
- Marks changed local copies as `Needs merge` instead of overwriting them.
- Refuses to mutate symlink-managed ARIS installs and points users back to `install_aris_codex.sh --reconcile`.

Recommendation:

- Keep `smart_update_codex.sh` if you still need to support old or external copied Codex installs.
- Do not use it for repos installed with `install_aris_codex.sh`.
- It can be deleted if the project policy is "symlink-managed installs only"; if deleted, also remove `tests/test_codex_install_update.py` coverage for smart-update behavior and any documentation references to copied installs.

## Validation Commands

After changing the sync or install chain:

```bash
bash -n tools/install_aris_codex.sh tools/install_codex_skills.sh tools/install_claude_skills.sh tools/smart_update_codex.sh
python3 -c "import py_compile; py_compile.compile('tools/sync_codex_skill_mirror.py', doraise=True)"
python3 tools/sync_codex_skill_mirror.py --dry-run
git diff --check
```

If `pytest` is available:

```bash
pytest -q tests/test_codex_skill_mirror.py tests/test_codex_install_update.py
```
