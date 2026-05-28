---
name: research-pipeline
description: "Full research pipeline: Workflow 1 (idea discovery) → Workflow 1.5 (evaluation contract + implementation bridge) → Workflow 2 (auto review loop) → Workflow 3 (paper writing, optional). Goes from a broad research direction all the way to a polished PDF. Use when user says \"全流程\", \"full pipeline\", \"从找idea到投稿\", \"end-to-end research\", or wants the complete autonomous research lifecycle."
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill, spawn_agent, send_input
---

# Full Research Pipeline: Idea → Experiments → Submission

End-to-end autonomous research workflow for: **$ARGUMENTS**

## Constants

- **AUTO_PROCEED = true** — Controls the full pipeline's Gate 1 idea selection behavior. When `false`, wait for explicit user confirmation before continuing from the ranked ideas to Workflow 1.5.
- **ARXIV_DOWNLOAD = false** — When `true`, `/research-lit` downloads the top relevant arXiv PDFs during literature survey. When `false` (default), only fetches metadata via arXiv API. Passed through to `/idea-discovery` → `/research-lit`.
- **HUMAN_CHECKPOINT = false** — When `true`, the auto-review loops (Stage 4) pause after each round's review to let you see the score and provide custom modification instructions before fixes are implemented. When `false` (default), loops run fully autonomously. Passed through to `/auto-review-loop`.
- **REVIEWER_DIFFICULTY = medium** — How adversarial the reviewer is. `medium` (default): standard MCP review. `hard`: adds reviewer memory + debate protocol. `nightmare`: GPT reads repo directly via `codex exec` + memory + debate. Passed through to `/auto-review-loop`.
- **AUTO_WRITE = false** — When `true`, automatically invoke Workflow 3 (`/paper-writing`) after Stage 5. Requires `VENUE` to be set. When `false` (default), Stage 5 generates `NARRATIVE_REPORT.md` and stops — user invokes `/paper-writing` manually.
- **VENUE = ACM** — Target venue template family for paper writing (Stage 6). Only used when `AUTO_WRITE=true`. Options include `ACM`, `IEEE_CONF`, `IEEE_JOURNAL`, or any configured local venue template.

> 💡 Override via argument, e.g., `/research-pipeline "topic" — auto proceed: false, human checkpoint: true, difficulty: nightmare, auto_write: true, venue: ACM`.

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

## Pipeline

### Stage 1: Idea Discovery (Workflow 1)

To use a research brief, pass its `.md` path explicitly as `$ARGUMENTS`, e.g. `/research-pipeline "idea-stage/RESEARCH_BRIEF.md"`. A root `RESEARCH_BRIEF.md` is not auto-loaded. See `templates/RESEARCH_BRIEF_TEMPLATE.md`.

Invoke the idea discovery pipeline:

```
/idea-discovery "$ARGUMENTS"
```

This internally runs: `/research-lit` -> `/idea-creator` -> `/novelty-check` -> `/research-review` -> `/research-refine-pipeline`

**Output:** `idea-stage/IDEA_REPORT.md`, optional `idea-stage/IDEA_CANDIDATES.md`, `refine-logs/FINAL_PROPOSAL.md`, `refine-logs/EXPERIMENT_PLAN.md`, and `idea-stage/docs/research_contract.md`. Handoff fields must follow `../shared-references/idea-handoff-schema.md`.

**🚦 Gate 1 — Human Checkpoint:**

After Workflow 1 generates the report, proposal, and experiment plan, **pause and present the top ideas to the user** using the `Idea selection` checkpoint from `../shared-references/workflow1-checkpoints.md`:

```
📋 Idea Discovery complete. Top ideas:

1. [Idea 1 title] — merit: [1-5], evaluation_feasibility_score: [4|5], handoff: ready, schema: `idea-handoff-schema.md`
2. [Idea 2 title] — merit: [1-5], evaluation_feasibility_score: [1-5], handoff: needs_canon_clarification, schema: `idea-handoff-schema.md`
3. [Idea 3 title] — merit: [1-5], evaluation_feasibility_score: [1|2], handoff: designed_not_run, blocker: [main_blocker]

Recommended: Idea 1. Shall I proceed to Workflow 1.5 evaluation contract and implementation bridge?
```

**If `AUTO_PROCEED=false`:** Wait for user confirmation before continuing. The user may:
- **Approve an idea** → proceed to Stage 2.
- **Pick a different idea** → proceed with their choice.
- **Request changes** (e.g., "combine Idea 1 and 3", "focus more on X") → update the idea prompt with user feedback, re-run `/idea-discovery` with refined constraints, and present again.
- **Reject all ideas** → collect feedback on what's missing, re-run Stage 1 with adjusted research direction. Repeat until the user commits to an idea.
- **Stop here** → save current state to `idea-stage/IDEA_REPORT.md` for future reference.

**If `AUTO_PROCEED=true`:** Present the top ideas, wait briefly for user input if interactive, auto-select the #1 ranked idea with the strongest overall merit and evaluation feasibility score. If the highest-merit idea has `evaluation_feasibility_score <= 3`, keep it as deferred or clarification-needed and select the highest-ranked idea with `evaluation_feasibility_score` 4 or 5 for immediate Workflow 1.5. Log the actual selected label and title, for example: `"AUTO_PROCEED: selected [Idea N] — [title]"`.

### Stage 2: Evaluation Contract + Implementation Bridge (Workflow 1.5)

Once the user confirms which idea to pursue:

1. **Confirm Workflow 1 completed the selected idea package**:
   - `refine-logs/EXPERIMENT_PLAN.md` must exist before entering Workflow 1.5.
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
1. GPT-5.5 xhigh reviews the work (score, weaknesses, minimum fixes)
2. Claude Code implements fixes (code changes, new experiments, reframing)
3. Deploy fixes, collect new results
4. Re-review → repeat until score ≥ 6/10 or 4 rounds reached

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
/paper-writing "NARRATIVE_REPORT.md" — venue: ACM
```

**If `AUTO_WRITE=true`:**

🚦 **Gate 2 — Writing Checkpoint:**

```
📝 Research pipeline complete. Ready for Workflow 3.

- Venue: [VENUE]
- Input: NARRATIVE_REPORT.md
- Manual figures required: [list or none]
- Next step: /paper-writing "NARRATIVE_REPORT.md — venue: [VENUE]"

Proceeding with paper writing...
```

Checks before proceeding:
- If `VENUE` is missing → stop and ask. Do NOT silently use a default venue.
- If manual figures are required → pause and list them. Wait for user to add them.

Then invoke:

```
/paper-writing "NARRATIVE_REPORT.md" — venue: $VENUE
```

This delegates to Workflow 3 which handles its own phases:
`/paper-plan → /paper-figure → /paper-write → /paper-compile → /auto-paper-improvement-loop`

When Workflow 3 finishes, update the pipeline report with:
- Paper writing completion status
- Final PDF path (`paper/main.pdf`)
- Improvement scores (round 0 → round N)
- Remaining issues

**Output:** `paper/` directory with LaTeX source, compiled PDF, and `PAPER_IMPROVEMENT_LOG.md`.

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.

- **Stages 2-4 can run autonomously** once the user confirms the idea and Workflow 1.5 has written `EVALUATION_CONTRACT.md`. This is the "sleep and wake up to results" part.
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
