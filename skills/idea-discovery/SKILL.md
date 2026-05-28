---
name: idea-discovery
description: 'Workflow 1: Full idea discovery pipeline. Orchestrates research-lit → idea-creator → novelty-check → research-review to go from a broad research direction to validated ideas with evaluation handoff plans. Use when user says "找idea全流程", "idea discovery pipeline", "从零开始找方向", or wants the complete idea exploration workflow.'
argument-hint: \[research-direction | path/to/RESEARCH_BRIEF.md | paper-ref]
allowed-tools: Bash(\*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill, mcp\_\_codex\_\_codex, mcp\_\_codex\_\_codex-reply
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

Shared references:
- Handoff fields and Workflow 1 exit gate: `../shared-references/idea-handoff-schema.md`
- Phase checkpoint summaries: `../shared-references/workflow1-checkpoints.md`
- Report shape: `templates/IDEA_REPORT_TEMPLATE.md`
- Compact candidate shape: `templates/IDEA_CANDIDATES_TEMPLATE.md`

## Constants

- **Handoff planning is priority-ordered** — Attempt the highest-ranked survivor first; if it records a concrete blocker, move to the next survivor. Only one selected ready idea crosses into Workflow 1.5.
- **AUTO\_PROCEED = true** — After each phase summary, automatically proceed with the best option if the user does not respond. Set to `false` to wait for explicit user confirmation at phase decision points.
- **REVIEWER\_MODEL =** **`gpt-5.5`** — Model used via Codex MCP. Must be an OpenAI model (e.g., `gpt-5.5`, `o3`, `gpt-4o`). Passed to sub-skills.
- **OUTPUT\_DIR =** **`idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.
- **ARXIV\_DOWNLOAD = false** — When `true`, `/research-lit` downloads the top relevant arXiv PDFs during Phase 1. When `false` (default), only fetches metadata. Passed through to `/research-lit`.
- **COMPACT = false** — When `true`, generate compact summary files for short-context models and session recovery. Writes `idea-stage/IDEA_CANDIDATES.md` (top 3-5 ideas only) at the end of this workflow. Downstream skills read this instead of the full `idea-stage/IDEA_REPORT.md`.
- **REF\_PAPER** — Pass the paper reference directly as `$ARGUMENTS` (arXiv URL/ID, DOI, or local `.pdf` path); `/research-lit` detects mode 3 automatically, reads the complete paper, and writes `idea-stage/REF_PAPER_SUMMARY.md` before the literature search. Combine with `base repo` for "improve this paper with this codebase" workflows.

> 💡 These are defaults. Override by telling the skill, e.g., `/idea-discovery "topic" — auto proceed: false`, `/idea-discovery "https://arxiv.org/abs/2406.04329"` (reference paper as SOTA baseline; mutually exclusive with topic), or `/idea-discovery "topic" — compact: true`.

## Pipeline

> 💡 `$ARGUMENTS` accepts a plain research direction, a `.md` path (e.g., `idea-stage/RESEARCH_BRIEF.md`), or a paper reference (arXiv URL/ID, DOI, or local `.pdf` path). Modes are mutually exclusive — do not combine a topic string with a paper reference. For modes 2 and 3, `/research-lit` handles all extraction in Phase 1. Create a brief from the template: `cp templates/RESEARCH_BRIEF_TEMPLATE.md idea-stage/RESEARCH_BRIEF.md`

### Phase 1: Literature Survey

Invoke `/research-lit` to map the research landscape. Idea discovery is exactly the place where Gemini's AI-driven broad coverage adds value, so include `gemini` as a source by default unless the user already specified an explicit `— sources:` directive in their idea-discovery invocation.

```
NORMALIZED_ARGS="$(tools/inject_default_sources.sh "$ARGUMENTS")"
/research-lit "$NORMALIZED_ARGS"
```

If `gemini-cli` is not installed, `/research-lit` skips the Gemini source gracefully with a warning — no break to the pipeline. Users who want to force-disable Gemini in idea-discovery can pass `/idea-discovery "topic" — sources: all` explicitly (which becomes the literal source list, no auto-injection).

**What this does:**

- Search local/Zotero/Obsidian/web/arXiv sources for recent papers and preprints
- Infer the AI infrastructure layer and expand the topic within the same layer
- Plus Gemini-driven broad discovery (sub-problem decomposition, naming variants, alias coverage) when `gemini-cli` is available
- Build a landscape map: sub-directions, approaches, open problems
- Identify structural gaps, `B*` bottlenecks, `S*` solution attempts, and `G*` residual-gap seeds
- Output a structured `Landscape Pack` for downstream idea generation, including `Evaluation Canon`, verified paper status, and `Gap Seeds`
- For paper-reference mode, write `idea-stage/REF_PAPER_SUMMARY.md`; Phase 2 uses it as additional context so ideas build on or improve the reference paper
- In `Evaluation Canon`, expect platform rows to carry `evaluation_platform`,
  `access_readiness`, `validates_refs`, and `platform_limitations`; expect
  workload rows to carry `workload_characteristics` and
  `representativeness_limits`. Treat metrics as idea-specific, not part of the
  workload row.
- Output a literature summary (saved to working notes)

**Literature scope summary:** Present the `Literature scope` checkpoint from `../shared-references/workflow1-checkpoints.md`. Ask:

```
📚 Literature survey complete. Here's what I found:
- Inferred AI infra layer: [layer]
- Key bottlenecks: [2-3 bullets]
- Bottleneck Evidence: B* bottlenecks and S* solution attempts
- Evaluation Canon: platforms=[EC-P* evaluation_platform/access_readiness summary], workloads=[EC-W* workload_characteristics summary]
- Idea-local baselines: derived per idea from verified papers/systems or verified quick lookup
- Gap Seeds: [top G* residual-gap seeds]

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
- Filter by the `idea-creator` scoring rubric: literature-derived topic scope, concrete research question, overall merit, and evaluation feasibility score
- Run quick novelty checks, overall merit scoring, and `evaluation_feasibility_score` assessment
- Write evaluation handoff plans in priority-ordered sequence until one idea reaches `handoff_to_workflow_1_5: ready` or all survivors have recorded blockers
- Rank by `overall_merit_score` and `evaluation_feasibility_score`
- Output `idea-stage/IDEA_REPORT.md` using `templates/IDEA_REPORT_TEMPLATE.md`
- Optionally output `idea-stage/IDEA_CANDIDATES.md` using `templates/IDEA_CANDIDATES_TEMPLATE.md`

**Idea selection summary:** Present the `Idea selection` checkpoint from `../shared-references/workflow1-checkpoints.md`. Use field names and domains from `../shared-references/idea-handoff-schema.md`. Ask:

```
💡 Generated X ideas, filtered to Y, wrote Z evaluation handoff plans. Top results:

1. [Idea 1] — merit: [1-5], evaluation_feasibility_score: [4|5], evaluation_feasibility_breakdown: platform_workload_access=[...], evaluation_adapter_cost=[...], first_signal_runtime=[...], core_baseline: [idea-local baseline record], baseline_artifact_readiness: score=[2|1], status=[...], verification=[...], canon_mapping: platform=[EC-P*], workload=[EC-W*], target_validation_style: [style], clarity: [clear], handoff: ready
2. [Idea 2] — merit: [1-5], evaluation_feasibility_score: [1-5], evaluation_feasibility_breakdown: [main weak factor], core_baseline: [idea-local baseline record or new baseline with rationale], baseline_artifact_readiness: score=[2|1|0], status=[...], verification=[...], canon_mapping: [mapping], target_validation_style: [style], clarity: [partial], handoff: needs_canon_clarification
3. [Idea 3] — merit: [1-5], evaluation_feasibility_score: [1|2], handoff: designed_not_run, blocker: [main_blocker]

Which ideas should I validate further? Or should I regenerate with different constraints?
(If no response, I'll proceed with the top-ranked ideas.)
```

- **User picks an idea** (or `AUTO_PROCEED=true` behavior) → proceed to Phase 3 with the selected top idea; keep other ready ideas as backups in `IDEA_REPORT.md`.
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

**Update** **`idea-stage/IDEA_REPORT.md`** with deep novelty results. Eliminate any idea that turns out to be already published.

### Phase 4: External Critical Review

For the surviving top idea(s), get brutal feedback:

```
/research-review "[top idea with idea_shape + overall_merit_score + evaluation_feasibility_score + core_baseline + canon_mapping + metrics + evaluation handoff plan]"
```

**What this does:**

- GPT-5.5 xhigh acts as a senior computer architecture / systems reviewer (MICRO/ISCA/HPCA/ASPLOS/NSDI/SIGCOMM level)
- Scores the idea, identifies weaknesses, suggests minimum viable improvements
- Provides concrete feedback on experimental design

**Update** **`idea-stage/IDEA_REPORT.md`** with reviewer feedback and revised plan.

### Phase 4.5: Method Refinement + Experiment Planning

After review, refine only the selected top idea into a concrete proposal and plan experiments. Present a pre-refine summary with the selected idea, novelty result, review summary, evaluation handoff summary, and known blockers before invoking the refinement pipeline:

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

Use the `Refined proposal ready` checkpoint from `../shared-references/workflow1-checkpoints.md`.

```
🔬 Method refined and experiment plan ready:
- Problem anchor: [anchored problem]
- Method thesis: [one sentence]
- Dominant contribution: [what's new]
- Must-run experiments: [N blocks]
- First 3 runs to launch: [list]

Proceed to implementation? Or adjust the proposal?
```

- **User approves** (or `AUTO_PROCEED=true` behavior) → proceed to Final Report only if `refine_verdict=READY`, `refine_overall_score >= 9`, `drift_status` is `preserved` or `corrected`, and `handoff_refresh_status=passed`.
- **User requests changes** → pass feedback to `/research-refine` for another round.
- **Refine does not converge:** If `refine_verdict != READY`, `refine_overall_score < 9/10`, `drift_status=drifted`, or `handoff_refresh_status != passed`, automatically try the next priority idea from `IDEA_REPORT.md`; if no ready backup remains, mark `main_blocker: refine_did_not_converge`.
- **Lite mode:** If `refine_overall_score < 6/10` or the evaluation handoff is unclear, run `/research-refine` only (skip `/experiment-plan`) and note remaining risks in the report.

### Phase 5: Final Report

Present the final report summary before writing the latest copy. Then finalize `idea-stage/IDEA_REPORT.md` with all accumulated information using `templates/IDEA_REPORT_TEMPLATE.md`.

The report must make the selected idea explicit, keep backup/deferred ideas documented, and link:
- `refine-logs/FINAL_PROPOSAL.md`
- `refine-logs/EXPERIMENT_PLAN.md`
- `idea-stage/docs/research_contract.md`
- `../shared-references/idea-handoff-schema.md`

Do not restate a second handoff schema in this orchestrator.

### Phase 5.5: Write Compact Files (when COMPACT = true)

**Skip entirely if** **`COMPACT`** **is** **`false`.**

Write `idea-stage/IDEA_CANDIDATES.md` from `templates/IDEA_CANDIDATES_TEMPLATE.md` — a lean summary of the top 3-5 surviving ideas.

This file is intentionally small (\~30 lines) so downstream skills and session recovery can read it without loading the full `idea-stage/IDEA_REPORT.md` (\~200+ lines).

## Output Protocols

> Follow these shared protocols for all output files:
>
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

## Composing with Workflow 1.5 & 2

After this pipeline produces a validated top idea:

```
/idea-discovery "direction"         ← you are here (Workflow 1, includes method refinement + experiment planning)
/experiment-bridge                  ← create EVALUATION_CONTRACT.md and baseline-first execution path
/run-experiment                     ← deploy experiments selected by Workflow 1.5
/auto-review-loop "top idea"        ← Workflow 2: iterate until submission-ready

Or use /research-pipeline for the full end-to-end flow.
```
