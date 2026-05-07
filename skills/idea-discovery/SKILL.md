---
name: idea-discovery
description: "Workflow 1: Full idea discovery pipeline. Orchestrates research-lit → idea-creator → novelty-check → research-review to go from a broad research direction to validated ideas with evaluation handoff plans. Use when user says \"找idea全流程\", \"idea discovery pipeline\", \"从零开始找方向\", or wants the complete idea exploration workflow."
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill, mcp__codex__codex, mcp__codex__codex-reply
---

# Workflow 1: Idea Discovery Pipeline

Orchestrate a complete idea discovery workflow for: **$ARGUMENTS**

## Overview

This skill chains sub-skills into a single automated pipeline for **AI infrastructure for LLM** research:

```
/research-lit → /idea-creator → /novelty-check → /research-review → /research-refine-pipeline
  (survey)      (brainstorm)    (verify novel)    (critical feedback)  (refine method + plan experiments)
```

Each phase builds on the previous one's output. The final deliverables are a validated `idea-stage/IDEA_REPORT.md` with ranked ideas, plus a refined proposal (`refine-logs/FINAL_PROPOSAL.md`) and experiment plan (`refine-logs/EXPERIMENT_PLAN.md`) for the top idea. The default scope covers compute/accelerator, memory/storage/data movement, interconnect/network, and runtime/system when runtime has a concrete hardware bottleneck.

## Constants

- **MAX_HANDOFF_IDEAS = 6** — Write evaluation handoff plans for at most 6 strong ideas. Workflow 1 does not run pilots.
- **MAX_READY_FOR_WORKFLOW_1_5 = 3** — Mark at most 3 ideas as immediate Workflow 1.5 candidates.
- **AUTO_PROCEED = true** — After each phase summary, automatically proceed with the best option if the user does not respond. Set to `false` to wait for explicit user confirmation at phase decision points.
- **REVIEWER_MODEL = `gpt-5.5`** — Model used via Codex MCP. Must be an OpenAI model (e.g., `gpt-5.5`, `o3`, `gpt-4o`). Passed to sub-skills.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.
- **ARXIV_DOWNLOAD = false** — When `true`, `/research-lit` downloads the top relevant arXiv PDFs during Phase 1. When `false` (default), only fetches metadata. Passed through to `/research-lit`.
- **COMPACT = false** — When `true`, generate compact summary files for short-context models and session recovery. Writes `idea-stage/IDEA_CANDIDATES.md` (top 3-5 ideas only) at the end of this workflow. Downstream skills read this instead of the full `idea-stage/IDEA_REPORT.md`.
- **REF_PAPER = false** — Reference paper to base ideas on. Accepts: local PDF path, arXiv URL, or any paper URL. When set, the paper is summarized first (`idea-stage/REF_PAPER_SUMMARY.md`), then idea generation uses it as context. Combine with `base repo` for "improve this paper with this codebase" workflows.

> 💡 These are defaults. Override by telling the skill, e.g., `/idea-discovery "topic" — auto proceed: false`, `/idea-discovery "topic" — ref paper: https://arxiv.org/abs/2406.04329`, or `/idea-discovery "topic" — compact: true`.

## Pipeline

### Phase 0: Load Research Brief (if available)

Before starting any other phase, check for a detailed research brief in the project:

1. Look for `RESEARCH_BRIEF.md` in the project root (or path passed as `$ARGUMENTS`)
2. If found, read it and extract:
   - Problem statement and context
   - Constraints (compute, data, timeline, venue)
   - What the user already tried / what didn't work
   - Domain knowledge and non-goals
   - Existing results (if any)
3. Use this as the primary context for all subsequent phases — it replaces the one-line prompt
4. If both `RESEARCH_BRIEF.md` and a one-line `$ARGUMENTS` exist, merge them (brief takes priority for details, argument sets the direction)

If no brief exists, proceed normally with `$ARGUMENTS` as the research direction.

> 💡 Create a brief from the template: `cp templates/RESEARCH_BRIEF_TEMPLATE.md RESEARCH_BRIEF.md`

### Phase 0.5: Reference Paper Summary (when REF_PAPER is set)

**Skip entirely if `REF_PAPER` is `false`.**

Summarize the reference paper before searching the literature:

1. **If arXiv URL** (e.g., `https://arxiv.org/abs/2406.04329`):
   - Invoke `/arxiv "ARXIV_ID" — download` to fetch the PDF
   - Read the first 5 pages (title, abstract, intro, method overview)

2. **If local PDF path** (e.g., `papers/reference.pdf`):
   - Read the PDF directly (first 5 pages)

3. **If other URL**:
   - Fetch and extract content via WebFetch

4. **Generate `idea-stage/REF_PAPER_SUMMARY.md`**:

```markdown
# Reference Paper Summary

**Title**: [paper title]
**Authors**: [authors]
**Venue**: [venue, year]

## What They Did
[2-3 sentences: core method and contribution]

## Key Results
[Main quantitative findings]

## Limitations & Open Questions
[What the paper didn't solve, acknowledged weaknesses, future work suggestions]

## Potential Improvement Directions
[Based on the limitations, what could be improved or extended?]

## Codebase
[If `base repo` is also set: link to the repo and note which parts correspond to the paper]
```

**🚦 Checkpoint:** Present the summary to the user:

```
📄 Reference paper summarized:
- Title: [title]
- Key limitation: [main gap]
- Improvement directions: [2-3 bullets]

Proceeding to literature survey with this as context.
```

Phase 1 and Phase 2 will use `idea-stage/REF_PAPER_SUMMARY.md` as additional context — `/research-lit` searches for related and competing work, `/idea-creator` generates ideas that build on or improve the reference paper.

### Phase 1: Literature Survey

Invoke `/research-lit` to map the research landscape:

```
/research-lit "$ARGUMENTS"
```

**What this does:**
- Search local/Zotero/Obsidian/web/arXiv sources for recent papers and preprints
- Infer the AI infrastructure layer and expand the topic within the same layer
- Build a landscape map: sub-directions, approaches, open problems
- Identify structural gaps, bottleneck evidence, and `Gap Seeds`
- Output a structured `Landscape Pack` for downstream idea generation, including `Evaluation Canon` and `Core Baseline Candidates`
- Output a literature summary (saved to working notes)

**Literature scope summary:** Present the landscape summary to the user. Ask:

```
📚 Literature survey complete. Here's what I found:
- Inferred AI infra layer: [layer]
- Key bottlenecks: [2-3 bullets]
- Evaluation Canon: platforms=[EC-P* summary], workloads=[EC-W* summary]
- Core Baseline Candidates: [CB* summary]
- Gap Seeds: [top 3]

Does this match your understanding? Should I adjust the scope before generating ideas?
(If no response, I'll proceed with the top-ranked direction.)
```

- **User approves** (or `AUTO_PROCEED=true` behavior) → proceed to Phase 2 with best direction.
- **User requests changes** (e.g., "focus more on X", "ignore Y", "too broad") → refine the search with updated queries, re-run `/research-lit` with adjusted scope, and present again. Repeat until the user is satisfied.

### Phase 2: Idea Generation + Filtering + Evaluation Handoff

Invoke `/idea-creator` with the landscape context (and `idea-stage/REF_PAPER_SUMMARY.md` if available):

```
/idea-creator "$ARGUMENTS"
```

**What this does:**
- If `idea-stage/REF_PAPER_SUMMARY.md` exists, include it as context — ideas should build on, improve, or extend the reference paper
- Brainstorm 8-12 concrete idea candidates from `Landscape Pack` / `Gap Seeds`
- Filter by the `idea-creator` scoring rubric: topic fit and concrete architecture/systems/measurement/benchmark question
- Run quick novelty checks, overall merit scoring, and evaluation target feasibility assessment
- Write evaluation handoff plans for the top 4-6 ideas
- Rank by overall merit and evaluation target feasibility
- Output `idea-stage/IDEA_REPORT.md`

**Idea selection summary:** Present `idea-stage/IDEA_REPORT.md` ranked ideas to the user. Ask:

```
💡 Generated X ideas, filtered to Y, wrote Z evaluation handoff plans. Top results:

1. [Idea 1] — merit: [1-4], feasibility: [high/medium/low/unknown], core_baseline: [CB*], canon_mapping: platform=[EC-P*], workload=[EC-W*], target_validation_style: [style], clarity: [clear], handoff: ready
2. [Idea 2] — merit: [1-4], feasibility: [high/medium/low/unknown], core_baseline: [CB* or new_baseline_with_rationale], canon_mapping: [mapping], target_validation_style: [style], clarity: [partial], handoff: needs_canon_clarification
3. [Idea 3] — merit: [1-4], feasibility: [low], handoff: designed_not_run, blocker: [main_blocker]

Which ideas should I validate further? Or should I regenerate with different constraints?
(If no response, I'll proceed with the top-ranked ideas.)
```

- **User picks ideas** (or `AUTO_PROCEED=true` behavior) → proceed to Phase 3 with top-ranked ideas.
- **User unhappy with all ideas** → collect feedback ("what's missing?", "what direction do you prefer?"), update the prompt with user's constraints, and re-run Phase 2 (idea generation). Repeat until the user selects at least 1 idea.
- **User wants to adjust scope** → go back to Phase 1 with refined direction.

### Phase 3: Deep Novelty Verification

For each selected top idea with strong overall merit and a credible evaluation handoff, run a thorough novelty check:

```
/novelty-check "[top idea 1 description]"
/novelty-check "[top idea 2 description]"
```

**What this does:**
- Multi-source literature search (arXiv, Scholar, Semantic Scholar)
- Cross-verify with GPT-5.5 xhigh
- Check for concurrent work (last 3-6 months)
- Identify closest existing work and differentiation points

**Update `idea-stage/IDEA_REPORT.md`** with deep novelty results. Eliminate any idea that turns out to be already published.

### Phase 4: External Critical Review

For the surviving top idea(s), get brutal feedback:

```
/research-review "[top idea with idea_shape + overall_merit_score + evaluation_target_feasibility + core_baseline + canon_mapping + metrics + evaluation handoff plan]"
```

**What this does:**
- GPT-5.5 xhigh acts as a senior computer architecture / systems reviewer (MICRO/ISCA/HPCA/ASPLOS/NSDI/SIGCOMM level)
- Scores the idea, identifies weaknesses, suggests minimum viable improvements
- Provides concrete feedback on experimental design

**Update `idea-stage/IDEA_REPORT.md`** with reviewer feedback and revised plan.

### Phase 4.5: Method Refinement + Experiment Planning

After review, refine the top idea into a concrete proposal and plan experiments. Present a pre-refine summary with the selected idea, novelty result, review summary, evaluation handoff summary, and known blockers before invoking the refinement pipeline:

```
/research-refine-pipeline "[top idea description + evaluation handoff plan + reviewer feedback]"
```

**What this does:**
- Freeze a **Problem Anchor** to prevent scope drift
- Iteratively refine the method via GPT-5.5 review (up to 5 rounds, until score ≥ 9)
- Generate a claim-driven experiment roadmap with ablations, budgets, and run order
- Output: `refine-logs/FINAL_PROPOSAL.md`, `refine-logs/EXPERIMENT_PLAN.md`, `refine-logs/EXPERIMENT_TRACKER.md`

#### Research Contract Postcondition

After the selected idea has proposal and plan outputs, apply `shared-references/research-contract-maintenance.md` to create or refresh `idea-stage/docs/research_contract.md`.
This is only a workflow-exit gate; experiment-plan is the semantic owner of `refine-logs/EXPERIMENT_PLAN.md`.

#### Checkpoint: Present the refined proposal summary

```
🔬 Method refined and experiment plan ready:
- Problem anchor: [anchored problem]
- Method thesis: [one sentence]
- Dominant contribution: [what's new]
- Must-run experiments: [N blocks]
- First 3 runs to launch: [list]

Proceed to implementation? Or adjust the proposal?
```

- **User approves** (or `AUTO_PROCEED=true` behavior) → proceed to Final Report.
- **User requests changes** → pass feedback to `/research-refine` for another round.
- **Lite mode:** If reviewer score < 6 or the evaluation handoff is unclear, run `/research-refine` only (skip `/experiment-plan`) and note remaining risks in the report.

### Phase 5: Final Report

Present the final report summary before writing the latest copy. Then finalize `idea-stage/IDEA_REPORT.md` with all accumulated information:

```markdown
# Idea Discovery Report

**Direction**: $ARGUMENTS
**Date**: [today]
**Pipeline**: research-lit → idea-creator → novelty-check → research-review → research-refine-pipeline

## Executive Summary
[2-3 sentences: best idea, key evidence, recommended next step]

## Literature Landscape
[from Phase 1]

## Ranked Ideas
[from Phase 2, updated with Phase 3-4 results]

### 🏆 Idea 1: [title] — RECOMMENDED
- Idea shape: [compact summary of the idea, target gap, proposed mechanism/study, and why the answer matters]
- Overall merit: [1-4] — [rationale]
- evaluation_target_feasibility: high | medium | low | unknown
- baseline_reproducibility: official_artifact | open_source_system | config_reproducible | paper_only | proprietary_or_unavailable | unknown
- evaluation_environment_access: ready | small_adapter_needed | major_bringup_needed | unavailable | unknown
- idea_adapter_cost: parameter_or_config_only | small_local_patch | moderate_adapter | major_system_change | new_platform_or_prototype
- pilot_runtime_cost: minutes_to_hours | one_to_two_days | multi_day_to_two_weeks | long_running_or_large_scale | unknown
- core_baseline: [CB* candidate or new baseline with rationale]
- canon_mapping: platform=[EC-P*]; workload=[EC-W*]
- metrics: [decisive metric first, secondary metrics if needed]
- target_validation_style: analytical_model | simulator_evaluation | prototype_measurement
- evaluation_target_clarity: clear | partial | missing
- handoff_to_workflow_1_5: ready | needs_canon_clarification | designed_not_run
- Novelty check: CONFIRMED (closest: [paper], differentiation: [what's different]; use this to update overall merit)
- Reviewer score: X/10
- Next step: /experiment-bridge → implement full experiment → /auto-review-loop

### Idea 2: [title] — BACKUP
...

## Eliminated Ideas
[ideas killed at each phase, with reasons]

## Refined Proposal
- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Tracker: `refine-logs/EXPERIMENT_TRACKER.md`

## Next Steps
- [ ] /experiment-bridge to create `refine-logs/EVALUATION_CONTRACT.md`
- [ ] /run-experiment to deploy experiments selected by Workflow 1.5
- [ ] /auto-review-loop to iterate until submission-ready
- [ ] Or invoke /research-pipeline for the complete end-to-end flow
```

### Phase 5.5: Write Compact Files (when COMPACT = true)

**Skip entirely if `COMPACT` is `false`.**

Write `idea-stage/IDEA_CANDIDATES.md` — a lean summary of the top 3-5 surviving ideas:

```markdown
# Idea Candidates

| # | Idea | Overall Merit | Feasibility | Core Baseline | Handoff | Reviewer Score | Status |
|---|------|---------------|-------------|---------------|---------|----------------|--------|
| 1 | [title] | 1 | high | CB1 | ready | X/10 | RECOMMENDED |
| 2 | [title] | 2 | medium | CB2 | needs_canon_clarification | X/10 | BACKUP |
| 3 | [title] | 1 | low | new_baseline_with_rationale | designed_not_run | — | DEFERRED |

## Active Idea: #1 — [title]
- Idea shape:
- core_baseline:
- canon_mapping:
- metrics:
- target_validation_style:
- evaluation_target_clarity:
- evaluation_target_feasibility:
- baseline_reproducibility:
- evaluation_environment_access:
- idea_adapter_cost:
- pilot_runtime_cost:
- Next step: /experiment-bridge or /research-refine
```

This file is intentionally small (~30 lines) so downstream skills and session recovery can read it without loading the full `idea-stage/IDEA_REPORT.md` (~200+ lines).

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.

- **Don't skip phases.** Each phase filters and validates — skipping leads to wasted effort later.
- **Summarize between phases.** Briefly state what was found before moving on.
- **Kill ideas early.** It's better to kill 10 bad ideas in Phase 3 than to implement one and fail.
- **Evaluation clarity beats vibes.** A publishable idea needs a credible baseline, workload, metrics, and handoff path, even if Workflow 1 does not run the experiment yet.
- **Document everything.** Dead ends are just as valuable as successes for future reference.
- **Be honest with the reviewer.** Include unclear canon mapping, unclear comparison targets, feasibility limits, and deferred platform blockers in the review prompt.
- **Feishu notifications are optional.** If `~/.claude/feishu.json` exists, send `checkpoint` at each phase transition and `pipeline_done` at final report. If absent/off, skip silently.

## Composing with Workflow 2

After this pipeline produces a validated top idea:

```
/idea-discovery "direction"         ← you are here (Workflow 1, includes method refinement + experiment planning)
/experiment-bridge                  ← create EVALUATION_CONTRACT.md and baseline-first execution path
/run-experiment                     ← deploy experiments selected by Workflow 1.5
/auto-review-loop "top idea"        ← Workflow 2: iterate until submission-ready

Or use /research-pipeline for the full end-to-end flow.
```
