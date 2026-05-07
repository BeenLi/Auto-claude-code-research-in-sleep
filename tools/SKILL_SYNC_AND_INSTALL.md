# ARIS Skill Sync and Project Install Guide

This document explains how ARIS skills are authored, mirrored for Codex, and installed into a target repository.

## Skill Trees

The main `skills/` tree is the source of truth. Do not hand-edit `skills/skills-codex/` for normal skill changes; regenerate it from the main tree.

## Sync Main Skills to Codex Mirror

Use `tools/sync_codex_skill_mirror.py`.

```bash
python3 tools/sync_codex_skill_mirror.py --dry-run
python3 tools/sync_codex_skill_mirror.py --apply
python3 tools/sync_codex_skill_mirror.py --dry-run
```

Expected clean output includes:

```text
changes: 0
clean
```

The sync script copies main skills and `shared-references` into `skills/skills-codex/`, removes stale mirror skills, and applies the small Codex wording/tool-name adaptations. It does not rewrite the Claude or Gemini review overlay packages.

## Unified Project Install

Use one installer for all project-local symlink installs:

```bash
bash tools/install_aris.sh /path/to/target/repo --target claude --dry-run
bash tools/install_aris.sh /path/to/target/repo --target claude

bash tools/install_aris.sh /path/to/target/repo --target codex --dry-run
bash tools/install_aris.sh /path/to/target/repo --target codex

bash tools/install_aris.sh /path/to/target/repo --target gemini --dry-run
bash tools/install_aris.sh /path/to/target/repo --target gemini
```

`--target claude` is the default, so existing Claude installs can keep using:

```bash
bash tools/install_aris.sh /path/to/target/repo
```

Target layouts:

```text
claude -> .claude/skills/<skill-name>  -> <aris-repo>/skills/<skill-name>
codex  -> .agents/skills/<skill-name>  -> <aris-repo>/skills/skills-codex/<skill-name>
gemini -> .gemini/skills/<skill-name>  -> <aris-repo>/skills/<skill-name>
```

Target manifests:

```text
claude -> .aris/installed-skills.txt
codex  -> .aris/installed-skills-codex.txt
gemini -> .aris/installed-skills-gemini.txt
```

Each manifest is the installer-owned ledger for that target. Reconcile and uninstall only mutate symlinks recorded in the selected target manifest and preserve user-owned files, directories, and unmanaged symlinks.

## Codex Review Modes

By default, Codex skills use the base Codex package:

```bash
bash tools/install_aris.sh /path/to/target/repo --target codex
```

Use exactly one overlay when Codex should execute while another reviewer MCP handles review-heavy skills:

```bash
bash tools/install_aris.sh /path/to/target/repo --target codex --with-claude-review-overlay
bash tools/install_aris.sh /path/to/target/repo --target codex --with-gemini-review-overlay
```

Overlay rules:

```text
no overlay     -> skills/skills-codex/<skill-name>
Claude overlay -> skills/skills-codex-claude-review/<skill-name> when present, otherwise base
Gemini overlay -> skills/skills-codex-gemini-review/<skill-name> when present, otherwise base
```

`--with-claude-review-overlay` and `--with-gemini-review-overlay` are mutually exclusive.

## Shared Tools Link

Every successful install or reconcile ensures:

```text
<target-repo>/.aris/tools -> <aris-repo>/tools
```

This link is shared by all targets and is not written into any target manifest. It is removed only when uninstalling the last remaining ARIS target manifest, and only if it still points exactly to `<aris-repo>/tools`.

## Reconcile and Uninstall

After editing ARIS skills or running `git pull`:

```bash
python3 tools/sync_codex_skill_mirror.py --apply
bash tools/install_aris.sh /path/to/target/repo --target claude --reconcile
bash tools/install_aris.sh /path/to/target/repo --target codex --reconcile
bash tools/install_aris.sh /path/to/target/repo --target gemini --reconcile
```

Keep the Codex overlay flag when reconciling an overlay install:

```bash
bash tools/install_aris.sh /path/to/target/repo --target codex --with-claude-review-overlay --reconcile
```

Uninstall only one target at a time:

```bash
bash tools/install_aris.sh /path/to/target/repo --target claude --uninstall
bash tools/install_aris.sh /path/to/target/repo --target codex --uninstall
bash tools/install_aris.sh /path/to/target/repo --target gemini --uninstall
```

Copied installs are no longer managed by ARIS update scripts. To migrate a copied install, back up or remove the copied skills manually, then install project-local symlinks with `tools/install_aris.sh`.

## Validation Commands

After changing the sync or install chain:

```bash
bash -n tools/install_aris.sh
python3 -c "import py_compile; py_compile.compile('tools/sync_codex_skill_mirror.py', doraise=True)"
python3 tools/sync_codex_skill_mirror.py --dry-run
python3 -m pytest tests/test_codex_install_update.py tests/test_codex_skill_mirror.py tests/test_install_aris_tools_symlink.py -q
git diff --check
```

