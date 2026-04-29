# `skills-codex`

Codex-native mirror of the base ARIS skill set.

## Scope

This package keeps the main `skills/` workflows available for OpenAI Codex CLI.

Recent core workflow follow-up skills mirrored here include:

- `training-check`
- `result-to-claim`
- `ablation-planner`

These skills cover the experiment follow-up chain:

1. monitor training quality early
2. judge what claims the results actually support
3. design reviewer-facing ablations before paper writing

## Install

> 💡 **Recommended: project-local symlink** (since v0.4.2). Project isolation keeps ARIS workflows separate from other community skill packs (Superpowers, etc.). See issue [#118](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/issues/118).

```bash
# 1. Clone ARIS once to a stable location
git clone https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep.git ~/aris_repo

# 2. Attach Codex skills to a project as flat symlinks:
cd ~/your-paper-project
bash ~/aris_repo/tools/install_codex_skills.sh
# -> creates .agents/skills/<skill> symlinks to ~/aris_repo/skills/skills-codex/<skill>
# -> writes .aris/codex-installed-skills.txt
# -> re-runnable: reconcile new/removed skills and switch reviewer overlays

# 3. Update existing skill content:
cd ~/aris_repo && git pull

```

Reviewer overlay modes:

```bash
# Codex executes, Claude Code reviews through claude-review MCP
bash ~/aris_repo/tools/install_codex_skills.sh --project ~/your-paper-project --reviewer claude

# Codex executes, Gemini reviews through gemini-review MCP
bash ~/aris_repo/tools/install_codex_skills.sh --project ~/your-paper-project --reviewer gemini

# Switch back to Codex-as-reviewer skills
bash ~/aris_repo/tools/install_codex_skills.sh --project ~/your-paper-project --reviewer codex
```

Use `bash ~/aris_repo/tools/install_codex_skills.sh --help` for all options, including `--dry-run` and `--no-mcp`.

<details>
<summary><b>Alternative: legacy global install (`~/.codex/skills/`)</b></summary>

```bash
cp -a ~/aris_repo/skills/skills-codex/* ~/.codex/skills/
```

Global install increases the risk of skill name collisions when other community skill packs are also installed globally. Use only if you understand the trade-off and don't mix ARIS with other packs.

</details>

<details>
<summary><b>Alternative: project-local copy (per-project customization)</b></summary>

```bash
mkdir -p ~/your-project/.agents/skills
cp -a ~/aris_repo/skills/skills-codex/* ~/your-project/.agents/skills/
# Overlay manually if needed:
# cp -a ~/aris_repo/skills/skills-codex-gemini-review/* ~/your-project/.agents/skills/
```

</details>

Optional companion dependency for the `deepxiv` skill:

```bash
pip install deepxiv-sdk
```

If you also use reviewer overlay packages, prefer `tools/install_codex_skills.sh`; it chooses the final symlink target for each overridden skill.
