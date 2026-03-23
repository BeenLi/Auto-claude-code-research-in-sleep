# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ARIS (Auto-claude-code-research-in-sleep) is a zero-dependency ML research automation system built on pure Markdown skills. It automates the full research pipeline: literature → idea → experiment → paper.

**Core design**: Skills are `.md` files readable by any LLM. No framework lock-in. No build system.

## Installing Skills

```bash
# Install to Claude Code
cp -r skills/* ~/.claude/skills/

# Install Codex variant
cp -r skills-codex/* ~/.codex/skills/
```

## MCP Server Setup (for cross-model review)

```bash
# Install Codex CLI (required for GPT-5.4 reviewer role)
npm install -g @openai/codex
codex setup  # set model to gpt-5.4

# Register Codex as MCP server in Claude Code
claude mcp add codex -s user -- codex mcp-server
```

### claude-review MCP (makes Claude review Codex's work)
```bash
mkdir -p ~/.codex/mcp-servers/claude-review
cp mcp-servers/claude-review/server.py ~/.codex/mcp-servers/claude-review/server.py
codex mcp add claude-review -- python3 ~/.codex/mcp-servers/claude-review/server.py
```

### llm-chat MCP (OpenAI-compatible API bridge)
```bash
pip install httpx
# Set env: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
```

## Architecture

### Four Core Workflows

**Workflow 1 — Idea Discovery** (`/idea-discovery "topic"`):
`research-lit` → `idea-creator` → `novelty-check` → `research-review` → `research-refine` → `experiment-plan`

**Workflow 1.5 — Experiment Bridge** (`/experiment-bridge`):
Experiment plan → code implementation → GPT-5.4 code review → deploy → collect results

**Workflow 2 — Auto Review Loop** (`/auto-review-loop "topic"`):
Up to 4 rounds: external LLM review → identify weaknesses → Claude implements fixes → re-review until score ≥ 6/10

**Workflow 3 — Paper Writing** (`/paper-writing "NARRATIVE_REPORT.md"`):
`paper-plan` → `paper-figure` → `paper-write` → `paper-compile` → `auto-paper-improvement-loop`

**Full pipeline**: `/research-pipeline "topic"` runs Workflow 1 → 1.5 → 2 → 3

### Dual-Model Architecture

```
Claude Code (executor) ←→ GPT-5.4 via Codex MCP (reviewer)
```
Adversarial review is more effective than self-review. Claude executes; GPT-5.4 critiques.

### Key Constants

| Constant | Default | Meaning |
|----------|---------|---------|
| `MAX_ROUNDS` | 4 | Max review rounds in Workflow 2 |
| `POSITIVE_THRESHOLD` | 6/10 | Review pass condition |
| `PILOT_MAX_HOURS` | 2 | Max GPU hours per pilot |
| `MAX_TOTAL_GPU_HOURS` | 8 | Total GPU budget (Workflow 1) |
| `REVIEWER_MODEL` | gpt-5.4 | External reviewer (via Codex MCP) |

### State Persistence Files

Auto-created during runs:
- `IDEA_REPORT.md` — ranked idea list (Workflow 1)
- `NARRATIVE_REPORT.md` — user-provided input for Workflow 3
- `AUTO_REVIEW.md` — cumulative review log (Workflow 2)
- `REVIEW_STATE.json` — checkpoint for context-compact recovery
- `refine-logs/` — full iteration history
- `paper/` — LaTeX source and compiled PDF

## User Project CLAUDE.md Configuration

When running ARIS in a research project, the project's own `CLAUDE.md` should include:

```markdown
## Remote Server
- SSH: `ssh my-gpu-server`
- GPU: 4x A100
- Conda env: `research` (Python 3.10 + PyTorch)
- Activate: `eval "$(/opt/conda/bin/conda shell.bash hook)" && conda activate research`
- Code directory: `/home/user/experiments/`
- Use `screen` for background jobs

## W&B Configuration (optional)
- wandb_project: my-research-project
- wandb_entity: my-username
```

## Skill Invocation

```bash
# Basic usage
/idea-discovery "transformer efficiency"

# Override defaults inline
/research-pipeline "topic" — AUTO_PROCEED: false, human_checkpoint: true
/paper-writing "NARRATIVE_REPORT.md" — illustration: mermaid
/experiment-bridge — code_sync: git, wandb: true
```

Key overridable parameters: `AUTO_PROCEED` (true), `human_checkpoint` (false), `sources` (all), `code_review` (true), `wandb` (false), `illustration` (gemini/mermaid/false).

## LaTeX Dependencies (Workflow 3)

```bash
# macOS
brew install mactex poppler

# Linux
apt install texlive-full poppler-utils
```

## Optional Integrations

- **Zotero**: `uv tool install zotero-mcp-server` (literature from personal library)
- **Obsidian**: configure obsidian-mcp (notes as literature source)
- **Feishu/Lark**: `feishu-bridge` MCP for mobile notifications on experiment completion
- **Alternative models**: `llm-chat` MCP supports any OpenAI-compatible API (DeepSeek, Kimi, GLM, MiniMax, ModelScope)

## Supported IDEs

| IDE | Notes |
|-----|-------|
| Claude Code | Native — all 37 skills |
| Codex CLI | `skills-codex/` subset (31 skills) |
| Cursor | `@skill-name` syntax — see `docs/CURSOR_ADAPTATION.md` |
| Trae (ByteDance) | `docs/TRAE_ARIS_RUNBOOK_EN.md` |
| Antigravity (Google) | `docs/ANTIGRAVITY_ADAPTATION.md` |
| OpenClaw (OpenHands) | `docs/OPENCLAW_ADAPTATION.md` |

## Contributing New Skills

A skill is a `SKILL.md` file with frontmatter:
```markdown
---
name: skill-name
description: "what it does"
argument-hint: [argument-description]
allowed-tools: Bash(*), Read, Write, WebSearch, ...
---
```

Place in `skills/skill-name/SKILL.md`. No build step required.
