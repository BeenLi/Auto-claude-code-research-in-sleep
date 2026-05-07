# skills-codex-claude-review

This package is a **thin override layer** for users who want:

- **Codex** as the main executor
- **Claude Code** as the reviewer
- the local `claude-review` MCP bridge instead of a second Codex reviewer

It is designed to sit on top of the upstream Codex-native package at `skills/skills-codex/`.

## What this package contains

- Only the review-heavy skill overrides that need a different reviewer backend
- No duplicate templates or resource directories
- No replacement for the base `skills/skills-codex/` installation

Current overrides:

- `research-review`
- `novelty-check`
- `research-refine`
- `auto-review-loop`
- `paper-plan`
- `paper-figure`
- `paper-write`
- `auto-paper-improvement-loop`

## Install

```bash
# Clone ARIS once, then run this from each Codex project.
git clone https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep.git ~/aris_repo
cd /path/to/your/project
bash ~/aris_repo/tools/install_aris.sh . --target codex --with-claude-review-overlay
```

The installer links base skills from `skills/skills-codex/`, points the
review-heavy overrides at this package, and writes `.aris/installed-skills-codex.txt`.
Register `claude-review` MCP separately when this overlay is used.

If your Claude setup depends on a shell helper such as `claude-aws`, use the wrapper instead:

```bash
codex mcp remove claude-review
codex mcp add claude-review -- ~/aris_repo/mcp-servers/claude-review/run_with_claude_aws.sh
```

## Why this exists

The upstream `skills/skills-codex/` path already supports Codex-native execution with a second Codex reviewer via `spawn_agent`.

This package adds a different split:

- executor: Codex
- reviewer: Claude Code CLI
- transport: `claude-review` MCP

For long paper and review prompts, the reviewer path uses:

- `review_start`
- `review_reply_start`
- `review_status`

This avoids the observed Codex-hosted timeout issue when Claude is invoked synchronously through a local bridge.
