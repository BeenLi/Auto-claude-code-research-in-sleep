---
name: research-pipeline
description: "Full research pipeline: Workflow 1 (idea discovery) → Workflow 1.5 (evaluation contract + implementation bridge) → Workflow 2 (auto review loop) → Workflow 3 (paper writing, optional). Goes from a broad research direction all the way to a polished PDF. Use when user says \"全流程\", \"full pipeline\", \"从找idea到投稿\", \"end-to-end research\", or wants the complete autonomous research lifecycle."
argument-hint: "[research-direction] [— resume <run_id>]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Skill, mcp__codex__codex, mcp__codex__codex-reply
---

# Full Research Pipeline: Idea → Experiments → Submission

> ⏱ **External cadence: non-judgmental heartbeat only.** An overnight `/loop` /
> `CronCreate` heartbeat may wake, detect a **stalled** phase (no progress, dead
> process, blocked on a freed resource) and **nudge** it forward — it may NEVER
> decide the work is good (paper good enough, proof holds, claim supported).
> Every such verdict stays on its own skill's internal cadence and terminates in
> the cross-model jury. A heartbeat may say "keep going," never "good enough."
> See
> [`shared-references/external-cadence.md`](../shared-references/external-cadence.md)
> (overnight-pipeline rule + stall detection & forced structural pivot). At heartbeat
> startup, touch the run state first each tick and register this run with the watchdog
> `loop` type (so a silent death surfaces as STALE); unregister on completion. The
> watchdog only detects — it never acquits. Each tick also record the new-finding count
> via the `iteration_log.py` helper (resolve through the canonical
> `.aris/tools → tools → $ARIS_REPO/tools → $ARIS_REPO/tools via ~/.aris/repo`
> chain, integration-contract §2; warn-and-skip if unresolved):
> `python3 "$ITER_LOG" note <root> <run_id> <phase> <n>`. On the returned
> `pivot=structural` (stale ≥ 2) the nudge must change a STRUCTURAL constraint and pick an
> untried direction; on `pivot=human` (stale ≥ 4) flag for attention. Counting only —
> never a quality verdict.

End-to-end autonomous research workflow for: **$ARGUMENTS**

## Optional formal proof route

Before creating an experimental run, route theorem-centered requests for Lean
to [`/lean-formalize`](../lean-formalize/SKILL.md) and report its actual proof
result. Run the experimental stages below when the task includes empirical
research. In a mixed project, use Lean for a user-requested formal proof or a
specific mathematical obligation whose formal verification would materially
help; return its checked scope and remaining obligations to the research summary
and applicable proof audit. Ordinary mathematics stays in the existing theory
skills. Difficulty alone does not make Lean mandatory, and a formal sublemma
does not establish an empirical claim.

## Constants

- **AUTO_PROCEED = true** — Controls the Gate 1 idea selection checkpoint and is passed to nested workflows. When `true`, every selection checkpoint is informational: report the choice and continue in the same turn. When `false`, ask for explicit user confirmation and end the turn at the checkpoint.
- **ARXIV_DOWNLOAD = false** — When `true`, `/research-lit` downloads the top relevant arXiv PDFs during literature survey. When `false` (default), only fetches metadata via arXiv API. Passed through to `/idea-discovery` → `/research-lit`.
- **HUMAN_CHECKPOINT = false** — When `true`, the auto-review loops (Stage 4) pause after each round's review to let you see the score and provide custom modification instructions before fixes are implemented. When `false` (default), loops run fully autonomously. Passed through to `/auto-review-loop`.
- **REVIEWER_DIFFICULTY = medium** — How adversarial the reviewer is. `medium` (default): standard MCP review. `hard`: adds reviewer memory + debate protocol. `nightmare`: GPT reads repo directly via `codex exec` + memory + debate. Passed through to `/auto-review-loop`.
- **AUTO_WRITE = false** — When `true`, automatically invoke Workflow 3 (`/paper-writing`) after Stage 5. `VENUE` is needed only when Stage 6 begins — a missing venue defers paper writing; it never blocks Stages 1-5. When `false` (default), Stage 5 generates `NARRATIVE_REPORT.md` and stops — user invokes `/paper-writing` manually.
- **VENUE = (unset)** — Target venue template family for paper writing; bound only when Stage 6 begins. Options include `ACM`, `IEEE_CONF`, `IEEE_JOURNAL`, or any configured local venue template. No default: a missing venue defers paper writing — it never blocks Stages 1-5 and is never guessed.
- **RENDER_HTML = true** — When `true` (default), auto-render `NARRATIVE_REPORT.md` to HTML at Stage 5 completion via `/render-html`. Uses `--no-review` (this is an internal handoff doc to `/paper-writing`, not a reviewer-facing final artifact — the Stage 4 auto-review loop already cross-model-reviewed the claims). Set `false` to skip, or pass `— render html: false`. **Non-blocking**: if `/render-html` fails or Codex MCP is unavailable, log the failure and continue — the HTML view is a nice-to-have, not a Stage 5 prerequisite.

- **RESUMABLE = true** — When `true` (default), the pipeline records per-stage state to `.aris/runs/<run_id>.json` so a crashed/interrupted run can resume via `/research-pipeline — resume <run_id>` instead of restarting. Stage status splits `done` (executor finished writing) from `accepted` (the stage's cross-model gate / deterministic verifier passed); resume re-validates any `done`-but-unaccepted stage. See `shared-references/resumable-runs.md`.

> 💡 Override via argument, e.g., `/research-pipeline "topic" — auto proceed: false, human checkpoint: true, difficulty: nightmare, auto_write: true, venue: ACM`.

## Checkpoint execution rule

Resolve `AUTO_PROCEED` once from `$ARGUMENTS` before Stage 1 and pass that
resolved value to nested workflows.

- **`AUTO_PROCEED=true` is non-blocking.** A checkpoint is a progress update,
  not a question. State the result and the automatically selected next action,
  then continue executing in the **same turn**. Do not ask for confirmation,
  request user input, sleep, wait for silence, or end the turn at a checkpoint.
- **`AUTO_PROCEED=false` is blocking.** Present the options, ask the user, and
  end the turn. Resume only after an explicit reply.

Never implement auto-proceed as “ask, then continue if there is no response.”
Once a turn ends, silence cannot resume the pipeline. The user can still
interrupt a non-blocking run at any time.

This rule governs only `AUTO_PROCEED`-controlled selection checkpoints. If the
user explicitly enables a Feishu **interactive** gate, that external approval
or reply is an intentional blocking exception; wait for that user-controlled
gate rather than treating it as a silence timeout. Feishu off/push-only modes
remain non-blocking under `AUTO_PROCEED=true`.

Non-blocking checkpoints never skip a gate: the Workflow 1 → 1.5 handoff gate
in Stage 2 still applies to an automatically selected idea.

## Overview

This skill chains the entire research lifecycle into a single pipeline:

```
/idea-discovery → /experiment-bridge → /run-experiment → /auto-review-loop → /paper-writing (optional)
├── Workflow 1 ──┤ ├── Workflow 1.5 ─┤ ├──────── Workflow 2 ───────┤ ├── Workflow 3 ──┤
```

It orchestrates up to three major workflows plus the implementation bridge between them. Workflow 3 (paper writing) is optional and controlled by `AUTO_WRITE`.

Shared references:
- Workflow 1 handoff fields and exit gate: `../shared-references/idea-handoff-schema.md`
- Workflow 1 checkpoint summaries: `../shared-references/workflow1-checkpoints.md`

## Resumable runs (`— resume <run_id>`)

This pipeline is long and can fail mid-run; it tracks per-stage state via
`run_state.py` so you can resume instead of restarting (see
[`shared-references/resumable-runs.md`](../shared-references/resumable-runs.md)).
Skip this whole section if `RESUMABLE = false`.

Resolve the helper via the canonical chain (integration-contract §2):
`.aris/tools/run_state.py` → `tools/run_state.py` → `$ARIS_REPO/tools/run_state.py`
→ `$ARIS_REPO/tools/run_state.py` via `~/.aris/repo`
(warn-and-skip if unresolved — never block the pipeline).

**Phases**, in order: `idea-discovery, experiment-bridge, auto-review-loop, summary, paper-writing`.

- **At start:** if `— resume <run_id>` was passed, run
  `run_state.py resume <root> <run_id>` — it prints the first non-`accepted`
  phase; **begin the pipeline at that stage** (re-run a `running`/`failed` stage;
  **re-audit** a `done`-but-unaccepted stage). Otherwise derive `<run_id>` from
  the direction slug + date and `run_state.py start <root> <run_id> --phases
  "idea-discovery,experiment-bridge,auto-review-loop,summary,paper-writing"`.
- **Per stage:** `set <run_id> <phase> running` on entry; `set <run_id> <phase>
  done --artifact <path>` once the stage's artifact is written.
- **Mark `accepted` ONLY after the stage's gate passes** — never on the executor's
  own say-so (`run_state.py accept` requires a recorded verdict id + reviewer):

  | phase | what sets `accepted` | record as reviewer |
  |-------|----------------------|--------------------|
  | `idea-discovery` | Gate 1 cross-model jury / novelty-check passed | `codex-gpt-6-astra` + thread id |
  | `experiment-bridge` | experiments actually ran (jobs completed) — deterministic | `deterministic:experiment-bridge` |
  | `auto-review-loop` | the loop hit its positive STOP (`score>=6 AND verdict∈{ready,almost}` — codex's verdict) | `codex-gpt-6-astra` + final review trace id |
  | `summary` | `NARRATIVE_REPORT.md` written (+ rendered if `RENDER_HTML`) — deterministic | `deterministic:summary` |
  | `paper-writing` | submission audits passed (`verify_paper_audits.sh` exit 0) — deterministic | `deterministic:verify_paper_audits.sh` |

**If `AUTO_WRITE = false`** (default), `paper-writing` is not part of this run:
after `summary` is accepted, `set <run_id> paper-writing skipped` so `resume`
reports COMPLETE instead of pointing forever at a pending stage. Record each
`accept` `verdict_id` as a **durable handle** — the codex thread/trace id, or the
path/sha of the deterministic verifier's report (e.g. the `verify_paper_audits.sh`
output JSON) — not just the reviewer label.

A stage left `done` (gate failed/ambiguous, or the run crashed before the gate)
is re-validated on the next resume — the acceptance obligation is never skipped.

## Overnight heartbeat: stall detection → forced structural pivot

Only when an unattended heartbeat is driving this run (overnight `/loop` /
`CronCreate`). Skip otherwise. Doctrine + rationale:
[`shared-references/external-cadence.md`](../shared-references/external-cadence.md)
→ "Stall detection & forced structural pivot". This is a Type-A signal — it counts
findings and changes *direction*, never *judges quality*.

Resolve the helper via the canonical chain (integration-contract §2), warn-and-skip
if unresolved (never block the run):
```bash
ITER_LOG=".aris/tools/iteration_log.py"
[ -f "$ITER_LOG" ] || ITER_LOG="tools/iteration_log.py"
[ -f "$ITER_LOG" ] || ITER_LOG="${ARIS_REPO:-}/tools/iteration_log.py"
[ -f "$ITER_LOG" ] || { [ -z "${ARIS_REPO:-}" ] && [ -f "$HOME/.aris/repo" ] && ARIS_REPO="$(cat "$HOME/.aris/repo" 2>/dev/null)"; } || true
[ -f "$ITER_LOG" ] || ITER_LOG="${ARIS_REPO:-}/tools/iteration_log.py"
[ -f "$ITER_LOG" ] || { echo "WARN: iteration_log.py not resolved; skipping stall detection" >&2; ITER_LOG=""; }
```
Then, **each heartbeat tick**, record how many concrete new findings the current
stage produced and read the returned `pivot`:
```bash
[ -n "$ITER_LOG" ] && python3 "$ITER_LOG" note "$ROOT" "$RUN_ID" "$STAGE" "$N_NEW_FINDINGS"
# → {"stale_count": N, "pivot": "none|structural|human"}
```
Act on `pivot`:
- `none` — keep going.
- `structural` (stale ≥ 2) — the next nudge must change a **structural constraint**
  (frame / objective / data / representation), not a tactical parameter, and pick a
  direction different from every one already tried. Record the chosen frame so future
  ticks can avoid it: `python3 "$ITER_LOG" note "$ROOT" "$RUN_ID" "$STAGE" 0 --direction "<the new frame>"`.
- `human` (stale ≥ 4) — stop nudging blindly; flag for human attention (escalate, do
  not silently abandon).

The heartbeat may say "keep going / change direction," never "good enough" — every
quality verdict still terminates in the cross-model jury (`acceptance-gate.md`).

## Pipeline

### Stage 1: Idea Discovery (Workflow 1)

To use a research brief, pass its `.md` path explicitly as `$ARGUMENTS`, e.g. `/research-pipeline "idea-stage/RESEARCH_BRIEF.md"`. A root `RESEARCH_BRIEF.md` is not auto-loaded. See `templates/RESEARCH_BRIEF_TEMPLATE.md`.

Invoke the idea discovery pipeline:

```
/idea-discovery "$ARGUMENTS" — AUTO_PROCEED: $AUTO_PROCEED
```

This internally runs: `/research-lit` -> `/idea-creator` -> `/novelty-check` -> `/research-review` -> `/research-refine-pipeline`

**Output:** `idea-stage/IDEA_REPORT.md`, optional `idea-stage/IDEA_CANDIDATES.md`, `refine-logs/FINAL_PROPOSAL.md`, `refine-logs/EXPERIMENT_PLAN.md`, and `idea-stage/docs/research_contract.md`. Handoff fields must follow `../shared-references/idea-handoff-schema.md`.

**🚦 Gate 1 — Idea Selection:**

After Workflow 1 generates the report, proposal, and experiment plan, present the top ideas using the `Idea selection` checkpoint from `../shared-references/workflow1-checkpoints.md`.

**If `AUTO_PROCEED=true` (non-blocking):** auto-select the #1 ranked idea with the strongest overall merit and evaluation feasibility score. If the highest-merit idea has `evaluation_feasibility_score <= 3`, keep it parked (clarification-needed or designed-not-run, with a `revisit_condition`) and select the highest-ranked idea with `evaluation_feasibility_score` 4 or 5 that is not parked for immediate Workflow 1.5. Report the selection and continue immediately in the same turn; do not phrase the update as a question. Log the actual selected label and title:

```
📋 Idea Discovery complete. Top ideas:

1. [Idea 1 title] — merit: [1-5], evaluation_feasibility_score: [4|5], handoff: ready, schema: `idea-handoff-schema.md`
2. [Idea 2 title] — merit: [1-5], evaluation_feasibility_score: [1-5], handoff: needs_canon_clarification, schema: `idea-handoff-schema.md`
3. [Idea 3 title] — merit: [1-5], evaluation_feasibility_score: [1|2], handoff: designed_not_run, blocker: [main_blocker], pool: parked

AUTO_PROCEED: selected [Idea N] — [title]. Continuing to Stage 2.
```

**If `AUTO_PROCEED=false` (blocking):** present the same ranking, ask
`Recommended: Idea 1. Shall I proceed to Workflow 1.5 evaluation contract and implementation bridge?`,
then end the turn. The user may:
- **Approve an idea** → proceed to Stage 2.
- **Pick a different idea** → proceed with their choice.
- **Request changes** (e.g., "combine Idea 1 and 3", "focus more on X") → update the idea prompt with user feedback, re-run `/idea-discovery` with refined constraints, and present again.
- **Reject all ideas** → collect feedback on what's missing, re-run Stage 1 with adjusted research direction. Repeat until the user commits to an idea.
- **Stop here** → save current state to `idea-stage/IDEA_REPORT.md` for future reference.

> ⚠️ **This gate waits for user confirmation only when `AUTO_PROCEED=false`.** When `true`, it reports the selection and continues. Stages 2-4 are expensive (platform bring-up, simulator/FPGA time, multiple review rounds), so set `AUTO_PROCEED=false` if you want a final review checkpoint before committing lab resources.

### Stage 2: Evaluation Contract + Implementation Bridge (Workflow 1.5)

Once the idea is selected (automatically or by the user):

1. **Confirm Workflow 1 completed the selected idea package**:
   - `refine-logs/EXPERIMENT_PLAN.md` must exist before entering Workflow 1.5.
   - When `RESUMABLE = true`, the Workflow 1 evidence gate (`gates.idea-discovery-evidence` in Workflow 1's own run record) must read `PASS`; a `BLOCKED` result means a stage or reviewer receipt is missing, so finish that stage in `/idea-discovery` first.
   - `refine-logs/FINAL_PROPOSAL.md` and `idea-stage/docs/research_contract.md` should exist for the selected idea.
   - If it is missing, Workflow 1 has not completed the refinement/planning path. Continue `/idea-discovery` or run `/research-refine-pipeline` for the selected idea before invoking `/experiment-bridge`.

2. **Run the Workflow 1 → 1.5 Handoff Gate**:
   - Run `tools/workflow1_exit_gate.sh --idea-report idea-stage/IDEA_REPORT.md --experiment-plan refine-logs/EXPERIMENT_PLAN.md --final-proposal refine-logs/FINAL_PROPOSAL.md --selected-idea "[title]"`.
   - The gate enforces `../shared-references/idea-handoff-schema.md`: `baseline_artifact_readiness.score: 0` cannot be ready, `canon_mapping` must cite `EC-P*` and `EC-W*`, `refine_verdict` must be `READY`, `refine_overall_score` must be at least `9`, `drift_status` must not be `drifted`, `handoff_refresh_status` must be `passed`, and required handoff fields must be present.
   - If any gate item fails, do not invoke `/experiment-bridge`; return to `/research-lit`, `/idea-discovery`, or `/research-refine-pipeline` as appropriate.

3. **Invoke `/experiment-bridge` before implementation**:
   ```
   /experiment-bridge "selected idea from idea-stage/IDEA_REPORT.md"
   ```

   This must generate `refine-logs/EVALUATION_CONTRACT.md` before any full implementation work.

4. **Verify the evaluation contract**:
   - baseline source, platform/workload, and metrics are explicit
   - handoff feasibility and access assumptions are explicit
   - `handoff_gate_status`, `baseline_go_no_go`, `baseline_smoke_required`, and `baseline_evidence_strength` are recorded
   - selected evaluation backend follows the baseline and platform/workload mapping
   - workload and metrics are decisive for the idea, not merely copied from prior work
   - baseline reproduction mode and idea execution readiness are honest

5. **Implement according to the contract**:
   - Build or adapt only the backend selected in `EVALUATION_CONTRACT.md`
   - Add proper evaluation metrics and logging
   - Write clean, reproducible experiment scripts
   - Follow existing codebase conventions

6. **Code review**: Before deploying, do a self-review:
   - Are all simulator/prototype parameters configurable via argparse or manifest?
   - Are random seeds or workload repetitions fixed and controllable when variance matters?
   - Are results saved to JSON/CSV for later analysis?
   - Is there proper logging for debugging?

### Stage 3: Deploy Experiments (Workflow 2 — Part 1)

Deploy the full-scale experiments. **Route by job count**:

**Small batch (≤5 jobs)** — direct deployment:
```
/run-experiment [experiment command]
```

**Large batch (≥10 jobs, sweeps, simulator grids, dependency chains)** — use the queue scheduler:
```
/experiment-queue [grid spec or manifest]
```

`experiment-bridge` (Workflow 1.5) writes the evaluation contract and auto-routes based on milestone job count. For pipeline runs with simulator grids from the start, you can override globally with `--- batch: queue` to force `/experiment-queue` for all milestones.

**What this does:**
- Check local or remote execution resources configured for the chosen backend
- Sync code to remote server
- Launch experiments in screen sessions or queue-managed jobs
- For `/experiment-queue`: also stale-session cleanup, phase dependencies, crash-safe state
- Verify experiments started successfully

**Monitor progress:**

```
/monitor-experiment [server]
```

Wait for experiments to complete. Collect results.

### Stage 4: Auto Review Loop (Workflow 2 — Part 2)

Once initial results are in, start the autonomous improvement loop:

```
/auto-review-loop "$ARGUMENTS — [chosen idea title], difficulty: $REVIEWER_DIFFICULTY"
```

**What this does (up to 4 rounds):**
1. GPT-6-Astra xhigh reviews the work (score, weaknesses, minimum fixes)
2. Claude Code implements fixes (code changes, new experiments, reframing)
3. Deploy fixes, collect new results
4. Re-review → repeat until (score ≥ 6/10 AND verdict ∈ {ready, almost}) or 4 rounds reached

**Output:** `review-stage/AUTO_REVIEW.md` with full review history and final assessment.

### Stage 5: Research Summary & Writing Handoff

After the auto-review loop completes, prepare the handoff for paper writing.

**Step 1:** Write a final research status report (same as before).

**Step 2:** Generate `NARRATIVE_REPORT.md` from:
- `IDEA_REPORT.md` (chosen idea, hypothesis, novelty justification)
- Implementation details from the repo
- Experiment configs and final results
- `AUTO_REVIEW.md` (review history, weaknesses fixed, remaining limitations)

The narrative report must contain:
- Problem statement and core claim
- Method summary
- Key quantitative results with evidence for each claim
- Figure/table inventory (which exist, which need manual creation)
- Limitations and remaining follow-up items

**Output:** `NARRATIVE_REPORT.md` + research pipeline report.

```markdown
# Research Pipeline Report

**Direction**: $ARGUMENTS
**Chosen Idea**: [title]
**Date**: [start] → [end]
**Pipeline**: idea-discovery → experiment-bridge → run-experiment → auto-review-loop

## Journey Summary
- Ideas generated: X → filtered to Y → wrote evaluation handoff plans for Z → chose 1
- Evaluation contract: `refine-logs/EVALUATION_CONTRACT.md` generated; backend=[selected_evaluation_backend]
- Implementation: [brief description of what was built]
- Experiments: [number of simulator/prototype experiments, total validation time]
- Review rounds: N/4, final score: X/10

## Writing Handoff
- NARRATIVE_REPORT.md: ✅ generated
- Venue: [VENUE or "not set — run /paper-writing manually"]
- Manual figures needed: [list or "none"]

## Remaining TODOs (if any)
- [items flagged by reviewer that weren't addressed]
```

### Stage 6: Paper Writing (Workflow 3 — Optional)

**Skip this stage if `AUTO_WRITE=false` (default).** Present the `/paper-writing` command for manual use:

```
📝 Research complete. To write the paper:
/paper-writing "NARRATIVE_REPORT.md" — venue: <VENUE>, AUTO_PROCEED: $AUTO_PROCEED
```

**If `AUTO_WRITE=true`:**

🚦 **Gate 2 — Writing Checkpoint:**

```
📝 Research pipeline complete. Ready for Workflow 3.

- Venue: [VENUE]
- Input: NARRATIVE_REPORT.md
- Manual figures required: [list or none]
- Next step: /paper-writing "NARRATIVE_REPORT.md" — venue: [VENUE], AUTO_PROCEED: $AUTO_PROCEED

Proceeding with paper writing...
```

Checks before proceeding (venue binds HERE — Stages 1-5 are venue-independent):
- If `VENUE` is missing: with `AUTO_PROCEED=false`, ask now. With
  `AUTO_PROCEED=true`, do not guess and do not wait — stamp
  "VENUE NOT SPECIFIED — paper writing deferred" in the report and checkpoint,
  leave the paper-writing phase pending, and finish the run cleanly for a later
  resume. Never silently pick a venue.
- If manual figures are required: with `AUTO_PROCEED=false`, pause and list
  them. With `AUTO_PROCEED=true`, record "paper writing deferred (manual
  figures: <list>)" and finish cleanly the same way.

Then invoke:

```
/paper-writing "NARRATIVE_REPORT.md" — venue: $VENUE, AUTO_PROCEED: $AUTO_PROCEED
```

Pass the resolved `AUTO_PROCEED` explicitly so Workflow 3 cannot silently
fall back to its own default mode.

This delegates to Workflow 3 which handles its own phases:
`/paper-plan → /paper-figure → /paper-write → /paper-compile → /auto-paper-improvement-loop`

When Workflow 3 finishes, update the pipeline report with:
- Paper writing completion status
- Final PDF path (`paper/main.pdf`)
- Improvement scores (round 0 → round N)
- Remaining issues

**Output:** `paper/` directory with LaTeX source, compiled PDF, and `PAPER_IMPROVEMENT_LOG.md`.

## Render HTML view (auto, when `RENDER_HTML = true`)

After Stage 5 finalizes `NARRATIVE_REPORT.md` (before paper writing branches), invoke `/render-html` on the narrative report:

```
/render-html "NARRATIVE_REPORT.md" --no-review
```

`--no-review` is intentional: this is an internal handoff doc, not reviewer-facing — the claims it summarizes were already cross-model-reviewed in Stage 4's `/auto-review-loop`. Output: `NARRATIVE_REPORT.html` next to the MD, with embedded source SHA256.

**Non-blocking**: if `/render-html` fails (helper missing, file write error, etc.), log the failure and continue Stage 5 — the HTML view is a convenience artifact, not a pipeline prerequisite.

Skip this step if `RENDER_HTML = false`.

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.

- **The Stage 1 checkpoint is controlled by AUTO_PROCEED.** When `false`, do not proceed without user confirmation. When `true`, report the top selection and continue in the same turn without asking or waiting.
- **Stages 2-4 can run autonomously** once the idea is selected and Workflow 1.5 has written `EVALUATION_CONTRACT.md`. This is the "sleep and wake up to results" part.
- **If Stage 4 ends at round 4 without positive assessment**, stop and report remaining issues. Do not loop forever.
- **Budget awareness**: Track simulator/prototype hours, platform setup time, and any hardware resource limits across the pipeline. Flag if approaching user-defined limits.
- **Documentation**: Every stage updates its own output file. The full history should be self-contained.
- **Fail gracefully**: If any stage fails (no good ideas, experiments crash, review loop stuck), report clearly and suggest alternatives rather than forcing forward.

## Typical Timeline

| Stage | Duration | Can sleep? |
|-------|----------|------------|
| 1. Idea Discovery | 30-60 min | Yes if AUTO_PROCEED=true |
| 2. Evaluation contract + implementation | 15-90 min | Yes after Gate 1 |
| 3. Deploy | 5 min + experiment time | Yes ✅ |
| 4. Auto Review | 1-4 hours (depends on experiments) | Yes ✅ |

**Sweet spot**: Run Stage 1-2 in the evening, launch Stage 3-4 before bed, wake up to a reviewed paper.
