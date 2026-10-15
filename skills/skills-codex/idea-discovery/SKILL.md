---
name: idea-discovery
description: 'Workflow 1: Full idea discovery pipeline. Orchestrates research-lit → idea-creator → novelty-check → research-review → research-refine-pipeline to go from a broad research direction to validated ideas with evaluation handoff plans. Use when user says "找idea全流程", "idea discovery pipeline", "从零开始找方向", or wants the complete idea exploration workflow.'
argument-hint: "[research-direction | path/to/RESEARCH_BRIEF.md | paper-ref]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Skill, spawn_agent, send_input
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
- Stage evidence ledger: `../shared-references/resumable-runs.md`
- Report shape: `templates/IDEA_REPORT_TEMPLATE.md`
- Compact candidate shape: `templates/IDEA_CANDIDATES_TEMPLATE.md`

## Constants

- **Handoff planning is priority-ordered** — Attempt the highest-ranked survivor first; if it records a concrete blocker, move to the next survivor. Only one selected ready idea crosses into Workflow 1.5.
- **AUTO_PROCEED = true** — When `true`, checkpoints are informational: report the selected option and continue in the same turn. Set to `false` to ask for explicit user confirmation and end the turn at each selection checkpoint.
- **REVIEWER_MODEL = `gpt-6-astra`** — Model used via Codex subagent. Must be an OpenAI model (e.g., `gpt-6-astra`, `o3`, `gpt-4o`). Passed to sub-skills.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.
- **ARXIV_DOWNLOAD = false** — When `true`, `/research-lit` downloads the top relevant arXiv PDFs during Phase 1. When `false` (default), only fetches metadata. Passed through to `/research-lit`.
- **COMPACT = false** — When `true`, generate compact summary files for short-context models and session recovery. Writes `idea-stage/IDEA_CANDIDATES.md` (top 3-5 ideas only) at the end of this workflow. Downstream skills read this instead of the full `idea-stage/IDEA_REPORT.md`.
- **RENDER_HTML = true** — When `true` (default), auto-render `idea-stage/IDEA_REPORT.md` to HTML at workflow end via `/render-html`. Uses `--no-review` (the source MD already went through novelty-check and cross-model review in Phases 3-4). Set `false` to skip, or pass `— render html: false`.
- **RESUMABLE = true** — Record stage evidence under `.aris/runs/<run_id>.json` and require a deterministic evidence gate before declaring the final report complete.
- **REF_PAPER** — Pass the paper reference directly as `$ARGUMENTS` (arXiv URL/ID, DOI, or local `.pdf` path); `/research-lit` detects mode 3 automatically, reads the complete paper, and writes `idea-stage/REF_PAPER_SUMMARY.md` before the literature search. Combine with `base repo` for "improve this paper with this codebase" workflows.

> 💡 These are defaults. Override by telling the skill, e.g., `/idea-discovery "topic" — auto proceed: false`, `/idea-discovery "https://arxiv.org/abs/2406.04329"` (reference paper as SOTA baseline; mutually exclusive with topic), or `/idea-discovery "topic" — compact: true`.

## Checkpoint execution rule

Resolve `AUTO_PROCEED` once from `$ARGUMENTS` before Phase 1 and keep that mode
for the entire workflow.

- **`AUTO_PROCEED=true` is non-blocking.** A checkpoint is a progress update,
  not a question. State the result and the automatically selected next action,
  then continue executing in the **same turn**. Do not ask for confirmation,
  request user input, sleep, wait for silence, or end the turn at a checkpoint.
- **`AUTO_PROCEED=false` is blocking.** Present the options, ask the user, and
  end the turn. Resume only after an explicit reply.

Never implement auto-proceed as “ask, then continue if there is no response.”
Once a turn ends, silence cannot resume the workflow. The user can still
interrupt a non-blocking run at any time.

This rule governs only `AUTO_PROCEED`-controlled selection checkpoints. If the
user explicitly enables a Feishu **interactive** gate, that external approval
or reply is an intentional blocking exception; wait for that user-controlled
gate rather than treating it as a silence timeout. Feishu off/push-only modes
remain non-blocking under `AUTO_PROCEED=true`.

The checkpoint contents come from `../shared-references/workflow1-checkpoints.md`.
Non-blocking checkpoints never relax a gate: automatic selection still follows
the candidate pool and handoff rules in `../shared-references/idea-handoff-schema.md`.

## Per-stage evidence gate (`RESUMABLE = true`)

Resolve `run_state.py` and `idea_discovery_gate.py` through the same canonical
helper chain used by `/research-pipeline` (integration-contract §2):
`.aris/tools/` → `tools/` → `$ARIS_REPO/tools/` → `$ARIS_REPO/tools/` via
`~/.aris/repo`. If either helper is unavailable, the final report is `BLOCKED`;
do not silently continue without a state record.

For a new run, derive `<run_id>` from the direction slug and UTC date, then start
this ordered state record with `--executor <actual-Claude-model>` (for example,
`claude-sonnet-4.5`):

```text
research-lit,idea-creator,novelty-check,research-review,research-refine-pipeline
```

When this workflow runs inside `/research-pipeline`, use its own run id (for
example `<pipeline_run_id>-w1`); the pipeline's record tracks Workflow 1 as the
single `idea-discovery` phase.

For each phase, mark `running` on entry and `done --artifact <path>` only after
its artifact is present. Use these artifact locators so the final gate checks
the stage outputs this workflow actually consumes:

| Phase | Artifact locator |
|---|---|
| `research-lit` | `idea-stage/LITERATURE_REVIEW.md` |
| `idea-creator` | `idea-stage/IDEA_REPORT.md#recommended-ideas` |
| `novelty-check` | `idea-stage/IDEA_REPORT.md#novelty-verification` |
| `research-review` | `idea-stage/IDEA_REPORT.md#external-critical-review` |
| `research-refine-pipeline` | `refine-logs/FINAL_PROPOSAL.md` |

`research-lit` is located by file because its Section 4 Landscape Pack is the
input `/idea-creator` reads. The gate treats a section whose first content line
is a sub-heading as empty, so open each anchored report section with a prose
line before any `###` sub-heading.

`novelty-check` and `research-review` are **reviewer-bearing phases**. A
`done` status or a heading alone is not review evidence. After each phase has
folded substantive findings into its anchored report section, first record it
`done`, then, only after the configured reviewer actually returns a positive,
identity-bearing verdict, record the cross-family receipt using the actual
returned model and durable thread/trace id:

```text
<resolved-python> <resolved-run_state.py> accept . <run_id> novelty-check --verdict-id "<thread-or-trace-id>" --reviewer "<actual-reviewer-model>"
<resolved-python> <resolved-run_state.py> accept . <run_id> research-review --verdict-id "<thread-or-trace-id>" --reviewer "<actual-reviewer-model>"
```

Never invent either value and never call `accept` without the positive verdict
required by the run-state contract. For `novelty-check`, **both PROCEED and
PROCEED WITH CAUTION are positive verdicts** — caution is guidance for
refinement and the Workflow 1.5 plan, not a rejection; only ABANDON is
negative. For `research-review`, positive means the review's bottom line does
not argue for abandoning the idea — a list of named risks is not a rejection.
If the review ends without a clear stance, ask the same reviewer thread for a
one-line verdict (proceed or abandon) and record on that answer; never infer
positivity from silence. A negative verdict does not grant a review receipt.
Leave the phase `done` and the final gate `BLOCKED`, record the reviewer's
reason, and keep the idea in the candidate pool as `backup` or `parked` (with
`park_reason` and `revisit_condition`); only an `already_done` citation or
`refuted_by_NE-*` evidence moves it to `eliminated`. Then select the next
priority-ordered idea and re-run that reviewer-bearing phase. Do the same if
the reviewer is unavailable, returns no valid identity/response, or its output
was not folded into the report.

**Executor-family route.** A receipt must say honestly who reviewed whom. When
this workflow runs on a Codex/OpenAI executor (the generated `skills-codex`
mirror) with the default OpenAI reviewer, the review is same-family and
`accept` refuses it. In that case start the run with
`--executor <actual-Codex-model> --provisional-advances` and record each
positive verdict as a provisional receipt instead:

```text
<resolved-python> <resolved-run_state.py> mark-provisional . <run_id> novelty-check --verdict-id "<agent-or-trace-id>" --reviewer "<actual-reviewer-model>"
<resolved-python> <resolved-run_state.py> mark-provisional . <run_id> research-review --verdict-id "<agent-or-trace-id>" --reviewer "<actual-reviewer-model>"
```

The same positive-verdict rules apply. If a reviewer overlay actually returns a
recognized different-family model, use `accept` with that model and trace id.
Never label a cross-family receipt provisional or a same-family receipt
accepted; the evidence gate validates either honest route from the recorded
families.

At the end of Phase 5, run:

```text
<resolved-python> <resolved-idea_discovery_gate.py> . <run_id> --report idea-stage/IDEA_REPORT.md
```

The gate writes its result to `gates.idea-discovery-evidence` in the run state.
On `PASS`, it has validated (but never created) the two review receipts, all
required artifacts, and non-empty anchored report sections. Per-phase
acceptance stays with each stage's own cross-model gate. On a non-zero exit, it
writes explicit `BLOCKED: <stage> evidence missing` lines to the report; do not
present the workflow as complete. On `— resume <run_id>`, start from the first
non-terminal phase and re-run the gate before finalizing.

This evidence gate and the Workflow 1 exit gate (`tools/workflow1_exit_gate.sh`,
see `../shared-references/idea-handoff-schema.md`) check different things, and
both must pass before Workflow 1.5: the evidence gate proves every stage ran and
left durable reviewer receipts; the exit gate proves the selected idea's
handoff fields are ready. Neither substitutes for the other, and neither marks
a phase accepted.

## Pipeline

> 💡 `$ARGUMENTS` accepts a plain research direction, a `.md` path (e.g., `idea-stage/RESEARCH_BRIEF.md`), or a paper reference (arXiv URL/ID, DOI, or local `.pdf` path). Modes are mutually exclusive — do not combine a topic string with a paper reference. For modes 2 and 3, `/research-lit` handles all extraction in Phase 1. Create a brief from the template: `cp templates/RESEARCH_BRIEF_TEMPLATE.md idea-stage/RESEARCH_BRIEF.md` — keep it to ~1-2 pages (4-8k chars); long material goes in separate files referenced by path.

### Phase 1: Literature Survey

Invoke `/research-lit` to map the research landscape. Idea discovery is exactly the place where Gemini's AI-driven broad coverage adds value, so include `gemini` as a source by default unless the user already specified an explicit `— sources:` directive in their idea-discovery invocation.

```
NORMALIZED_ARGS="$(tools/inject_default_sources.sh "$ARGUMENTS")"
/research-lit "$NORMALIZED_ARGS" — composed: idea-stage/IDEA_REPORT.md
```

If `gemini-cli` is not installed, `/research-lit` skips the Gemini source gracefully with a warning — no break to the pipeline. Users who want to force-disable Gemini in idea-discovery can pass `/idea-discovery "topic" — sources: all` explicitly (which becomes the literal source list, no auto-injection).

`— composed: idea-stage/IDEA_REPORT.md` puts `/research-lit` in composed mode: it still writes `idea-stage/LITERATURE_REVIEW.md` (the Landscape Pack that Phase 2 requires), skips its own `MANIFEST.md` rows, and returns a short landscape summary that this workflow folds into the report's `## Literature Landscape` section. The report does not exist yet at Phase 1 — the directive names the forthcoming canonical doc, and `/idea-creator` creates it in Phase 2.

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

**Literature scope checkpoint:** Present the `Literature scope` checkpoint from `../shared-references/workflow1-checkpoints.md`.

**When `AUTO_PROCEED=true` (non-blocking):** report the selected scope and
continue immediately in the same turn, without a question:

```
📚 Literature survey complete. Here's what I found:
- Inferred AI infra layer: [layer]
- Key bottlenecks: [2-3 bullets]
- Bottleneck Evidence: B* bottlenecks and S* solution attempts
- Evaluation Canon: platforms=[EC-P* evaluation_platform/access_readiness summary], workloads=[EC-W* workload_characteristics summary]
- Idea-local baselines: derived per idea from verified papers/systems or verified quick lookup
- Gap Seeds: [top G* residual-gap seeds]

AUTO_PROCEED: selected [top-ranked direction]. Continuing to Phase 2.
```

**When `AUTO_PROCEED=false` (blocking):** present the same summary, ask
`Does this match your understanding? Should I adjust the scope before generating ideas?`,
then end the turn.

- **User approves** → proceed to Phase 2 with the best direction.
- **User requests changes** (e.g., "focus more on X", "ignore Y", "too broad") → refine the search with updated queries, re-run `/research-lit` with adjusted scope, and present again. Repeat until the user is satisfied.

### Phase 2: Idea Generation + Filtering + Evaluation Handoff

Invoke `/idea-creator` with the landscape context (and `idea-stage/REF_PAPER_SUMMARY.md` if available):

```
/idea-creator "$ARGUMENTS" — composed: idea-stage/IDEA_REPORT.md
```

`/idea-creator` owns `idea-stage/IDEA_REPORT.md` as the canonical deliverable; the `— composed:` directive tells it to fold its findings into the report rather than emitting overlapping summary files alongside it.

**What this does:**

- If `idea-stage/REF_PAPER_SUMMARY.md` exists, include it as context — ideas should build on, improve, or extend the reference paper
- Brainstorm 8-12 concrete idea candidates from `Landscape Pack` / `Gap Seeds`
- Filter by the `idea-creator` scoring rubric: literature-derived topic scope, concrete research question, overall merit, and evaluation feasibility score
- Run quick novelty checks, overall merit scoring, and `evaluation_feasibility_score` assessment
- Write evaluation handoff plans in priority-ordered sequence until one idea reaches `handoff_to_workflow_1_5: ready` or all survivors have recorded blockers
- Rank by `overall_merit_score` and `evaluation_feasibility_score`. The ranking orders refinement and handoff attempts; it is not an elimination verdict. Ideas that are not selected stay in the pool as `backup` or `parked` (with `park_reason` and `revisit_condition`), per the Candidate Pool rules in `../shared-references/idea-handoff-schema.md`
- Output `idea-stage/IDEA_REPORT.md` using `templates/IDEA_REPORT_TEMPLATE.md`; open `## Recommended Ideas` with a one-line ranking summary (rank rule and pool counts) before the per-idea sub-sections
- Optionally output `idea-stage/IDEA_CANDIDATES.md` using `templates/IDEA_CANDIDATES_TEMPLATE.md`

**Idea selection checkpoint:** Present the `Idea selection` checkpoint from `../shared-references/workflow1-checkpoints.md`. Use field names and domains from `../shared-references/idea-handoff-schema.md`.

**When `AUTO_PROCEED=true` (non-blocking):** report the automatic selection and
continue immediately in the same turn, without a question. Select the
highest-ranked idea with `evaluation_feasibility_score` 4 or 5 that is not
parked; if the highest-merit idea scores `<= 3`, it stays parked with its
`revisit_condition` rather than being selected.

```
💡 Generated X ideas: Y active, P parked, K eliminated on evidence; wrote Z evaluation handoff plans. Top results:

1. [Idea 1] — merit: [1-5], evaluation_feasibility_score: [4|5], evaluation_feasibility_breakdown: platform_workload_access=[...], evaluation_adapter_cost=[...], first_signal_runtime=[...], core_baseline: [idea-local baseline record], baseline_artifact_readiness: score=[2|1], status=[...], verification=[...], canon_mapping: platform=[EC-P*], workload=[EC-W*], target_validation_style: [style], clarity: [clear], handoff: ready
2. [Idea 2] — merit: [1-5], evaluation_feasibility_score: [1-5], evaluation_feasibility_breakdown: [main weak factor], core_baseline: [idea-local baseline record or new baseline with rationale], baseline_artifact_readiness: score=[2|1|0], status=[...], verification=[...], canon_mapping: [mapping], target_validation_style: [style], clarity: [partial], handoff: needs_canon_clarification
3. [Idea 3] — merit: [1-5], evaluation_feasibility_score: [1|2], handoff: designed_not_run, blocker: [main_blocker], pool: parked, revisit: [revisit_condition]

AUTO_PROCEED: selected [Idea N] — [title] (highest-ranked idea that is not parked); backups and parked ideas stay in the pool. Continuing to Phase 3.
```

**When `AUTO_PROCEED=false` (blocking):** present the same ranking, ask
`Which ideas should I validate further? Or should I regenerate with different constraints?`,
then end the turn.

- **User picks an idea** → proceed to Phase 3 with the selected top idea; keep other ready ideas as backups in `IDEA_REPORT.md`.
- **User unhappy with all ideas** → collect feedback ("what's missing?", "what direction do you prefer?"), update the prompt with user's constraints, and re-run Phase 2 (idea generation). Before
  regenerating, read the already-tried directions (research-wiki Failed Ideas, parked and
  eliminated entries in `IDEA_REPORT.md`, and any `.aris/runs/<run_id>.iterations.jsonl`) and
  forbid a candidate too close to one already tried — enforced direction diversity; when an
  overnight heartbeat drives the run, record each chosen direction via
  `iteration_log.py note ... --direction "<frame>"` so later ticks can reject near-duplicates (see
  [`shared-references/external-cadence.md`](../shared-references/external-cadence.md) →
  Stall detection & forced structural pivot). Repeat until the user selects at least 1 idea.
- **User wants to adjust scope** → go back to Phase 1 with refined direction.

### Phase 3: Deep Novelty Verification

For each selected top idea with strong overall merit and a credible evaluation handoff, run a thorough novelty check:

```
/novelty-check "[top idea 1 description]"
/novelty-check "[top idea 2 description]"
```

**What this does:**

- Multi-source literature search (arXiv, Scholar, Semantic Scholar)
- Cross-verify with GPT-6-Astra xhigh
- Check for concurrent work (last 3-6 months)
- Identify closest existing work and differentiation points

**Update** **`idea-stage/IDEA_REPORT.md`** with deep novelty results under a `## Novelty Verification` section: per idea, the verdict (PROCEED / PROCEED WITH CAUTION / ABANDON), closest work, differentiation, and the reviewer trace path. Eliminate an idea only if its mechanism and claim are both already published (`already_done`, cite the paper). Close prior work lowers `overall_merit_score` and adds a differentiation note; the idea stays in the pool. Then record the phase `done` and its review receipt (see *Per-stage evidence gate*).

### Phase 4: External Critical Review

For the surviving top idea(s), get a sharp outside read — strongest case, named risks, and the cheapest discriminating next experiment; the core hypothesis is not up for rewriting:

```
/research-review "[top idea with idea_shape + overall_merit_score + evaluation_feasibility_score + core_baseline + canon_mapping + metrics + evaluation handoff plan]" — composed: idea-stage/IDEA_REPORT.md
```

In composed mode `/research-review` folds its conclusions into `idea-stage/IDEA_REPORT.md` and cites the `.aris/traces/…` path instead of writing a standalone review `.md` in the project root.

**What this does:**

- GPT-6-Astra xhigh acts as a senior computer architecture / systems reviewer (MICRO/ISCA/HPCA/ASPLOS/NSDI/SIGCOMM level)
- Scores the idea, identifies weaknesses, suggests minimum viable improvements
- Provides concrete feedback on experimental design

**Update** **`idea-stage/IDEA_REPORT.md`** with reviewer feedback and revised plan under an `## External Critical Review` section, including the review's bottom-line stance and trace path. Then record the phase `done` and its review receipt (see *Per-stage evidence gate*).

### Phase 4.5: Method Refinement + Experiment Planning

After review, refine only the selected top idea into a concrete proposal and plan experiments. Present a pre-refine summary with the selected idea, novelty result, review summary, evaluation handoff summary, and known blockers before invoking the refinement pipeline:

```
/research-refine-pipeline "[top idea description + evaluation handoff plan + reviewer feedback]"
```

**What this does:**

- Freeze a **Problem Anchor** to prevent scope drift
- Iteratively refine the method via GPT-6-Astra review (up to 5 rounds, until score ≥ 9) — reviewer risks choose the next tests, they do not add components; preserving the core hypothesis outranks pleasing the reviewer
- Generate a claim-driven experiment roadmap with ablations, budgets, and run order
- Output: `refine-logs/FINAL_PROPOSAL.md`, `refine-logs/EXPERIMENT_PLAN.md`, `refine-logs/EXPERIMENT_TRACKER.md`

#### Research Contract Postcondition

After the selected idea has proposal and plan outputs, apply `shared-references/research-contract-maintenance.md` to create or refresh `idea-stage/docs/research_contract.md`.
This is only a workflow-exit gate; experiment-plan is the semantic owner of `refine-logs/EXPERIMENT_PLAN.md`.
The postcondition is not gated on `COMPACT`; skip it only when the run selected no idea. The contract is the focused working context for the Workflow 1 → 1.5 handoff: `/experiment-bridge` implements against it, `/result-to-claim` and `/ablation-planner` read it as the claims boundary, and session recovery reloads the active idea from it instead of the full idea pool (`docs/SESSION_RECOVERY_GUIDE.md`).

#### Checkpoint: Present the refined proposal summary

Use the `Refined proposal ready` checkpoint from `../shared-references/workflow1-checkpoints.md`.

**When `AUTO_PROCEED=true` (non-blocking):** report the outcome and continue
immediately in the same turn, without a question:

```
🔬 Method refined and experiment plan ready:
- Problem anchor: [anchored problem]
- Method thesis: [one sentence]
- Dominant contribution: [what's new]
- Must-run experiments: [N blocks]
- First 3 runs to launch: [list]

AUTO_PROCEED: [accepted the refined proposal | refine did not converge, switching to backup Idea N]. Continuing to [Final Report | Phase 4.5 for the backup].
```

**When `AUTO_PROCEED=false` (blocking):** present the same summary, ask
`Proceed to implementation? Or adjust the proposal?`, then end the turn.

- **User approves** (or `AUTO_PROCEED=true` behavior) → proceed to Final Report only if `refine_verdict=READY`, `refine_overall_score >= 9`, `drift_status` is `preserved` or `corrected`, and `handoff_refresh_status=passed`.
- **User requests changes** → pass feedback to `/research-refine` for another round.
- **Refine does not converge:** If `refine_verdict != READY`, `refine_overall_score < 9/10`, `drift_status=drifted`, or `handoff_refresh_status != passed`, automatically try the next priority idea from `IDEA_REPORT.md`; if no ready backup remains, mark `main_blocker: refine_did_not_converge`. The non-converging idea stays in the pool with its scores; refinement results never eliminate it.
- **Lite mode:** If `refine_overall_score < 6/10` or the evaluation handoff is unclear, run `/research-refine` only (skip `/experiment-plan`) and note remaining risks in the report.

### Phase 5: Final Report

Present the final report summary before writing the latest copy. Then finalize `idea-stage/IDEA_REPORT.md` with all accumulated information using `templates/IDEA_REPORT_TEMPLATE.md`, keeping the `## Novelty Verification` and `## External Critical Review` sections from Phases 3-4.

The report must make the selected idea explicit, keep backup and parked ideas documented, and link:
- `refine-logs/FINAL_PROPOSAL.md`
- `refine-logs/EXPERIMENT_PLAN.md`
- `idea-stage/docs/research_contract.md`
- `../shared-references/idea-handoff-schema.md`

Do not restate a second handoff schema in this orchestrator.

Before presenting this report as complete, run the per-stage evidence gate and
the Workflow 1 exit gate (see *Per-stage evidence gate*). A `BLOCKED` gate
result is part of the report, not a warning to omit.

### Phase 5.5: Write Compact Files (when COMPACT = true)

**Skip entirely if** **`COMPACT`** **is** **`false`.**

Write `idea-stage/IDEA_CANDIDATES.md` from `templates/IDEA_CANDIDATES_TEMPLATE.md` — a lean summary of the top 3-5 surviving ideas.

This file is intentionally small (\~30 lines) so downstream skills and session recovery can read it without loading the full `idea-stage/IDEA_REPORT.md` (\~200+ lines).

## Output Protocols

> Follow these shared protocols for all output files:
>
> - **[Output Composition Protocol](../shared-references/output-composition.md)** — ONE canonical deliverable per pipeline; fold sub-skill findings in, don't scatter overlapping `.md` files
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — maintain `MANIFEST.md` only above the 15-artifact threshold (not "log every output")
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

### Output hygiene — one canonical report, no duplicate summaries (REQUIRED)

This workflow follows [`output-composition.md`](../shared-references/output-composition.md):
it owns a single canonical deliverable and folds each sub-skill's unique findings
into it instead of letting every sub-skill emit its own overlapping file.

1. **`idea-stage/IDEA_REPORT.md` is the canonical deliverable.** Novelty results and
   the external review are folded into it as the `## Novelty Verification` and
   `## External Critical Review` sections. If a sub-skill writes a scratch summary,
   inline its unique content into the report and delete the scratch when the phase closes.
2. **Pass `— composed: idea-stage/IDEA_REPORT.md` to every sub-skill that folds**
   (`/research-lit`, `/idea-creator`, `/research-review`). This is the explicit
   signal; a sub-skill without composed-mode support stays standalone by the
   protocol's fail-safe, and the orchestrator then does the folding itself.
3. **`idea-stage/LITERATURE_REVIEW.md` is a stage input, not a duplicate.**
   `/research-lit` writes it in composed mode too: its Section 4 Landscape Pack is
   the input `/idea-creator` reads, and `canon_mapping` cites its `EC-P*` /
   `EC-W*` rows. The report's `## Literature Landscape` summarizes and links it.
4. **Stage-scoped files stay with their owners** and are linked, not copied:
   `refine-logs/FINAL_PROPOSAL.md`, `refine-logs/EXPERIMENT_PLAN.md`,
   `refine-logs/EXPERIMENT_TRACKER.md`, and `idea-stage/docs/research_contract.md`.
5. **No `MANIFEST.md`** for a handful of files — only above the 15-artifact threshold in
   [`output-manifest.md`](../shared-references/output-manifest.md).
6. **Cross-model review traces belong in `.aris/traces/…`** (the audit trail); do not
   also keep a human-facing copy under `idea-stage/` — cite the trace path from the report.
7. **Before finishing,** the `idea-stage/` top level should hold roughly
   `IDEA_REPORT.md` (+ `.html`), `LITERATURE_REVIEW.md`, the optional
   `IDEA_CANDIDATES.md` and `REF_PAPER_SUMMARY.md`, `docs/research_contract.md`,
   and the timestamped copies from the Output Versioning Protocol. Nothing else
   unless it carries content not in the report.

## Render HTML view (auto, when `RENDER_HTML = true`)

After Phase 5 finalizes `idea-stage/IDEA_REPORT.md` (and the optional `IDEA_CANDIDATES.md`) and the evidence gate has written its section, invoke `/render-html` on the report so the user has a single-file HTML view for tablet / phone reading:

```
/render-html "idea-stage/IDEA_REPORT.md" --no-review
```

`--no-review` is intentional: the source MD already passed this skill's own novelty-check and cross-model review. HTML render is a structural conversion, not a new claim-audit gate. Output lands at `idea-stage/IDEA_REPORT.html` with embedded source SHA256 + render timestamp.

**Non-blocking**: if `/render-html` fails (helper missing, Codex subagent unavailable, file write error), log the failure and continue — the HTML view is a convenience artifact, not a Phase 5 prerequisite.

Skip this step if `RENDER_HTML = false`.

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.
- **Don't skip phases.** Each phase filters and validates — skipping leads to wasted effort later.
- **Checkpoint between phases.** Briefly summarize what was found. With `AUTO_PROCEED=true`, state the selected next action and keep executing in the same turn; with `false`, ask and end the turn.
- **Park ideas early, kill only on evidence.** It's better to park 10 weak ideas in Phase 3 than to implement one and fail. Parked ideas keep their scores and a `revisit_condition`, so a new lab resource or artifact can bring them back. A ranking, a reviewer's taste, or an anticipated objection never eliminates an idea; only an `already_done` citation or `refuted_by_NE-*` evidence does.
- **Evaluation clarity beats vibes.** A publishable idea needs a credible baseline, workload, metrics, and handoff path, even if Workflow 1 does not run the experiment yet.
- **Document everything — inside the one report, not in scattered files.** Dead ends, parked ideas, and eliminated ideas are valuable, so record them as sections of `idea-stage/IDEA_REPORT.md` (see *Output hygiene* above). Do not spawn a separate `.md` per phase.
- **Be honest with the reviewer.** Include unclear canon mapping, unclear comparison targets, feasibility limits, and parked ideas with their platform blockers in the review prompt.
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
