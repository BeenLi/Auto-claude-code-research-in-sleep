# AGENT.md

This file provides guidance to AI agents when working in this repository.

## Research Domain

This ARIS instance is configured for **Computer Architecture / AI Infrastructure for LLM** research with a hardware-leaning systems focus. 

## Workflows

**Workflow 1 -- Idea Discovery** (`/idea-discovery "topic"`):
`research-lit` -> `idea-creator` -> `novelty-check` -> `research-review` -> `research-refine-pipeline`

Canonical chain: research-lit -> idea-creator -> novelty-check -> research-review -> research-refine-pipeline

`research-refine-pipeline` is the public Workflow 1 tail wrapper for
`research-refine` -> `experiment-plan`. Workflow 1 prepares the selected idea,
final proposal, and experiment plan; it does not execute pilots or baseline
reproduction.

**Workflow 1.5 -- Experiment Bridge** (`/experiment-bridge`):
Reads `refine-logs/EXPERIMENT_PLAN.md` -> implements code -> deploys experiments -> collects initial results in `EXPERIMENT_LOG.md`

**Workflow 2 -- Auto Review Loop** (`/auto-review-loop "scope"`):
Up to 4 rounds: external LLM review -> identify weaknesses -> agent implements fixes -> re-review until score >= 6/10

**Workflow 3 -- Paper Writing** (`/paper-writing "NARRATIVE_REPORT.md"`):
`paper-plan` -> `paper-figure` -> `paper-write` -> `paper-compile` -> `auto-paper-improvement-loop`

**Workflow 4 -- Rebuttal** (`/rebuttal "paper/ + reviews"`):
Parses external reviews -> enforces coverage and grounding -> drafts text-only rebuttal

**Full pipeline**: `/research-pipeline "topic"` runs Workflow 1 -> 1.5 -> 2 -> 3

## Pipeline Status

```yaml
stage: workflow_1_5_in_progress  # M1 deployed + first signal obtained
active_idea: WR-ZipGuard
active_files:
  literature_review: idea-stage/LITERATURE_REVIEW.md
  idea_report: idea-stage/IDEA_REPORT.md
  final_proposal: refine-logs/FINAL_PROPOSAL.md
  experiment_plan: refine-logs/EXPERIMENT_PLAN.md
  evaluation_contract: refine-logs/EVALUATION_CONTRACT.md
  experiment_log: refine-logs/EXPERIMENT_LOG.md
  research_contract: idea-stage/docs/research_contract.md
  m1_code: experiments/m1/  # 66 unit tests, deployed to myDevbox:~/wr-zipguard/experiments/m1
workflow_1_exit_gate: passed
m1_status: GREEN_fp8e5m2_only  # deflate-only; ONLY FP8_E5M2 clears 0.75 (BF16/FP8_E4M3 entropy floors >0.75, provably can't); generator validated synthetic+gpt2+Qwen2.5-7B
next_step: full M1 grid (10 seeds, +zstd ref) + M1_REPORT; then M2 (BF3 deflate decompress microbench)
execution_platform: myDevbox  # Debian, py3.13, 64-core, 251GB RAM, no GPU; HF via hf-mirror.com
active_tasks: []  # no long-running remote jobs; M1 runs are on-demand
last_updated_utc: 2026-06-15T00:00:00Z
```

## State Persistence Rules

Pipeline Status update triggers:
- Stage transitions, idea selection, baseline confirmed, validation start/stop
- User says "save" / "record" / "new session" / "wrap up"
- Before any long pause or handoff

Research Contract update triggers:
- Idea selected or changed; if the idea fails, select the next candidate from `idea-stage/IDEA_CANDIDATES.md` and overwrite the contract
- `refine-logs/FINAL_PROPOSAL.md` or `refine-logs/EXPERIMENT_PLAN.md` generated/updated
- Baseline reproduced, major result obtained, Mx Go/No-Go completed, or `/result-to-claim` resolves claim support

On new session or post-compaction recovery:
1. Read ## Pipeline Status
2. Read idea-stage/docs/research_contract.md (the active idea's focused context)
3. Read project notes if any (e.g., experiment logs, decision rationale)
4. If active_tasks is non-empty -> check remote status, rebuild monitoring
5. Resume work without asking the user

## Skill Invocation

```bash
/research-lit "AI infrastructure for LLM" -- sources: local, zotero, web -- extended topics: "KV cache CXL", "NIC compression", "LLM checkpointing"
/idea-discovery "AI infrastructure for LLM -- hardware bottlenecks"
/research-pipeline "NIC/DPU compression for LLM serving" -- AUTO_PROCEED: false
```

Key overridable parameters: `AUTO_PROCEED` (true), `human_checkpoint` (false), `sources` (all), `code_review` (true), `illustration` (gemini/mermaid/false).

## MCP Servers

Register reviewer MCP servers in the active agent runtime using that runtime's MCP configuration command.

```bash
# Codex CLI reviewer server command
npm install -g @openai/codex && codex setup
codex mcp-server

# llm-chat (OpenAI-compatible API bridge)
pip install httpx
# Set env: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
```

Active integrations: **Zotero** (literature), **Obsidian** (notes), **Feishu/Lark** (notifications).

## LaTeX Dependencies

```bash
# macOS
brew install mactex poppler
```
