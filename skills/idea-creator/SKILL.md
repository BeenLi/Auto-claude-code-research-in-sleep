---
name: idea-creator
description: Generate and rank research ideas given a broad direction. Use when user says "找idea", "brainstorm ideas", "generate research ideas", "what can we work on", or wants to explore a research area for publishable directions.
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Grep, Glob, WebSearch, WebFetch, Agent, mcp__codex__codex, mcp__codex__codex-reply, mcp__manual_review__review, mcp__manual_review__review_reply
---

# Research Idea Creator

Generate publishable research ideas for: $ARGUMENTS

## Overview

Given a broad research direction from the user, systematically generate, validate, and rank concrete research ideas. This skill composes with `/research-lit`, `/novelty-check`, and `/research-review` to form a complete idea discovery pipeline.

The research domain is not hard-coded in this skill. Always derive the domain context from `idea-stage/LITERATURE_REVIEW.md`, especially the Section 4 `Topic Scope`, `Bottleneck Evidence`, `Evaluation Canon`, `Gap Seeds`, and `Competitive Landscape`. Do not inject a repository-wide domain default; derive the right venues, mechanisms, evaluation platforms, benchmarks, baselines, and metrics from the loaded literature for the current topic.

Shared references:
- Handoff fields and Workflow 1 exit gate: `../shared-references/idea-handoff-schema.md`
- Report template: `templates/IDEA_REPORT_TEMPLATE.md`
- Compact candidates template: `templates/IDEA_CANDIDATES_TEMPLATE.md`

## Constants

- **REVIEWER_MODEL = `gpt-5.5`** — Default model for the Codex backend. Must be an OpenAI model (e.g., `gpt-5.5`, `o3`, `gpt-4o`). Manual backend uses whatever model the user chooses.
- **REVIEWER_BACKEND = `codex`** — Default: Codex MCP (xhigh). Override with `— reviewer: oracle-pro` for Oracle MCP, or `— reviewer: manual` for Manual Review MCP. If manual-review MCP is unavailable, stop and print the install command; do not fall back to Codex. See `shared-references/reviewer-routing.md`.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.


> Override via argument, e.g., `/idea-creator "topic" — handoff: analytical_model only`.

## Scoring and Filtering Rubric

Use this rubric in Phase 3. Phase 2 only generates candidate ideas and hints.

Default weighted score:
- Overall merit: 60%
- Evaluation feasibility score: 40%

`overall_merit_score` follows a target-venue reviewer scale where 5 is best and 1 is worst:
- `5`: Surprisingly new contribution, or likely to have major impact on future research/products; may inspire new research or start a new line.
- `4`: Clear new contribution, or likely to impact future research/products.
- `3`: Incremental but valid improvement, with limited yet non-trivial impact.
- `2`: Weak novelty or marginal impact; generally not enough to justify acceptance.
- `1`: No clear novelty, or unlikely to have meaningful impact; should be rejected.

`evaluation_feasibility_score` provides a comprehensive assessment of the engineering effort, resource availability, and time required to achieve a credible first-signal pilot on a 1-5 high-is-better scale. It is a merged gate field determined by four primary factors:
1. **`platform_workload_access`**: Do we have access to the specific hardware, required cluster scale, or necessary production traces/data described by the selected EC-P*/EC-W* mapping?
2. **`baseline_artifact_readiness`**: A single structured baseline gate with `score`, `status`, `verification_status`, `evidence`, and `adapter_notes`. This replaces any separate baseline-code score.
3. **`evaluation_adapter_cost`**: What adapter or integration work is required before the first credible pilot?
4. **`first_signal_runtime`**: How long does it take to run the experiment that yields the *decisive metric*? This dictates the idea iteration speed (minutes/hours vs. weeks).

- **CRITICAL DISTINCTION in Systems Research**: "Baseline" (code) is separate from "Platform/Workload" (hardware/data). A perfectly open-source baseline still yields a low feasibility score if it requires inaccessible hardware or proprietary traces. Summarize the dominant rationale among these 4 factors in the score value or adjacent prose instead of adding separate handoff columns.

- `5`: ready evaluation path: `baseline_artifact_readiness.score` is `2`; platform/workload access is ready; adapter cost is small; first-signal runtime is minutes to hours.
- `4`: near-ready evaluation path: comparison target and platform/workload path are credible; implementation intrusiveness is minor to moderate; first signal should arrive within one to two days; no hard blocker is present.
- `3`: feasible but nontrivial: the path likely works, but needs major architectural changes, multi-day/multi-week bring-up, or reimplementing a closed-source baseline.
- `2`: weak feasibility: `baseline_artifact_readiness.score` is `0` or `1`, platform/workload needs major bring-up, the idea needs a new platform/prototype, workload is unavailable, or pilot cost is large-scale/long-running.
- `1`: no credible evaluation path: key artifact, platform, workload, baseline, comparison target, or runtime information is unavailable/unknown enough to block Workflow 1.5.

## Evaluation Canon And Baseline Extraction

Before brainstorming, extract the current topic's Evaluation Canon from
`idea-stage/LITERATURE_REVIEW.md`. In this workflow, Evaluation Canon means only
the literature-derived platform/workload reference set: `EC-P*` platform rows
and `EC-W*` workload rows. It anchors evaluation provenance without hard-coding
any previous topic's assumptions.

From the literature review, identify:
- **Bottleneck Evidence**: `Bottlenecks` rows with stable `B*` IDs and `Solution Attempts` rows with stable `S*` IDs. Use `Solution Attempts` as the mechanism source.
- **Evaluation Canon**: `Platforms` rows with stable `EC-P*` IDs and
  `Workloads` rows with stable `EC-W*` IDs. For platforms, extract
  `evaluation_platform`, `access_readiness`, `supported_workloads`,
  `validates_refs`, `artifact_access_path`, and `platform_limitations`.
  For workloads, extract `workload_characteristics` and
  `representativeness_limits`; EC-W rows describe workload shape and caveats,
  while decisive metrics remain idea-specific.
- **Verified paper/system evidence**: Section 1 paper rows with
  `Verification: verified`, Competitive Landscape competitors inside Section 4,
  and any explicit system or artifact notes tied to `B*` or `S*` evidence.

If the loaded Landscape Pack still contains the legacy global baseline pool or
legacy simulator/prototype readiness heading, stop and ask to re-run
`/research-lit`; do not try to parse the old schema.

Use the Evaluation Canon only as provenance for platform/workload choices.
`canon_mapping` must only contain
`platform=[EC-P*]; workload=[EC-W*]`. Baseline, metrics, and target validation
style are idea-specific decisions: build an idea-local baseline record for each
surviving idea, not a global baseline pool. If the required EC-P/EC-W evidence
is missing, mark `handoff_to_workflow_1_5: needs_canon_clarification` or
`main_blocker: unclear_canon_mapping`; do not invent a platform or workload
requirement from a different topic.

Each idea-local baseline record must follow
`../shared-references/idea-handoff-schema.md`.

Baseline source rules:
- Prefer a verified paper/system from Section 1 or a verified competitor from
  Section 4.
- Do not re-run `verify_papers.py` for Section 1 or Section 4 evidence already verified by `/research-lit`.
  Mark those baselines with `baseline_verification_delta: verified_by_research_lit`.
- Run `verify_papers.py` only when `idea-creator` adds a new baseline candidate
  from a narrow quick baseline lookup. Before doing this, announce the lookup to
  the user with the idea ID, the missing comparison target, and why the loaded
  literature evidence is insufficient.
- If a good idea needs a better comparison target, run a narrow quick baseline
  lookup, send only the new candidate through `verify_papers.py`, and record
  `baseline_verification_delta: new_baseline_lookup` with the lookup query,
  verifier output path, verification status, and whether the new evidence
  changed `handoff_to_workflow_1_5`.
- A baseline backed only by `unverified`, `verify_pending`, or `error` evidence
  may be discussed but cannot make the idea ready.

Resolve `verify_papers.py` with the canonical chain only for new
`idea-creator` baseline candidates (same pattern as `/research-lit` Step 2.5;
see also
`../shared-references/integration-contract.md` row "Candidate paper
verification"):

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
ARIS_REPO="${ARIS_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null)}"
VERIFY_SCRIPT=".aris/tools/verify_papers.py"
[ -f "$VERIFY_SCRIPT" ] || VERIFY_SCRIPT="tools/verify_papers.py"
[ -f "$VERIFY_SCRIPT" ] || { [ -n "${ARIS_REPO:-}" ] && VERIFY_SCRIPT="$ARIS_REPO/tools/verify_papers.py"; }
[ -f "$VERIFY_SCRIPT" ] || { echo "WARN: verify_papers.py unresolved; treat new baseline candidates as unverified." >&2; VERIFY_SCRIPT=""; }

# Then, only when idea-creator has new baseline candidates:
mkdir -p .aris/verify-papers
[ -n "$VERIFY_SCRIPT" ] && python3 "$VERIFY_SCRIPT" \
  --input .aris/verify-papers/idea-creator_baseline_candidates.json \
  --output .aris/verify-papers/idea-creator_verified_baselines.json
```

When `$VERIFY_SCRIPT` is empty, mark the new candidate as
`verification_status: unverified`, record
`baseline_verification_delta: verification_unresolved`, and treat the affected
idea as `designed_not_run` or set
`main_blocker: unclear_comparison_target` rather than `ready`.

Use the shared schema's `baseline_artifact_readiness.score` rule: `2` is verified
and official/open-source/config reproducible, `1` is verified but paper-only or
unknown reproducibility, and `0` is proprietary/unavailable/unverified-only.
Score `0` must not be marked
`handoff_to_workflow_1_5: ready`; downrank, defer, or set the blocker instead.

## Reviewer Calling Convention

When calling the reviewer for idea evaluation, branch on REVIEWER_BACKEND:

**If REVIEWER_BACKEND = `codex`:**
  Use `mcp__codex__codex` for new review threads.
  Use `mcp__codex__codex-reply` for follow-up rounds (reuse threadId).

**If REVIEWER_BACKEND = `manual`:**
  Use `mcp__manual_review__review` for new review threads with:
    prompt: [exact same prompt that would go to Codex]
    config: {"model_reasoning_effort": "xhigh"}
  Save the returned `threadId`.
  Use `mcp__manual_review__review_reply` for follow-up rounds with:
    threadId: [saved manual-review threadId]
    prompt: [follow-up prompt]
    config: {"model_reasoning_effort": "xhigh"}

Prompt fidelity: the manual prompt must be exactly the same text that Codex would receive.
Review tracing applies equally to both backends.

## Workflow

### Phase 0: Load Research Wiki (if active)

**Skip this phase entirely if `research-wiki/` does not exist.**

If `research-wiki/` exists, resolve the canonical helper using the
shared resolution chain (see `../research-wiki/SKILL.md` for the
contract):

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
ARIS_REPO="${ARIS_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null)}"
WIKI_SCRIPT=".aris/tools/research_wiki.py"
[ -f "$WIKI_SCRIPT" ] || WIKI_SCRIPT="tools/research_wiki.py"
[ -f "$WIKI_SCRIPT" ] || { [ -n "${ARIS_REPO:-}" ] && WIKI_SCRIPT="$ARIS_REPO/tools/research_wiki.py"; }
[ -f "$WIKI_SCRIPT" ] || {
  echo "WARN: research_wiki.py not found at .aris/tools/, tools/, or \$ARIS_REPO/tools/." >&2
  echo "      The idea-creation primary output (idea ranking) will still be produced." >&2
  echo "      Wiki integration (load query_pack, write idea pages, add edges, rebuild query_pack) will be skipped." >&2
  echo "      Fix: rerun 'bash tools/install_aris.sh', export ARIS_REPO, or 'cp <ARIS-repo>/tools/research_wiki.py tools/'." >&2
  WIKI_SCRIPT=""
}
```

```
if research-wiki/query_pack.md exists AND is less than 7 days old:
    Read query_pack.md and use it as initial landscape context:
    - Treat listed gaps as priority search seeds
    - Treat failed ideas as context; only `already_done` or `low_overall_merit` ideas are hard banlist entries
    - Treat top papers as known prior work (do not re-search them)
    Still run Phase 1 below for papers from the last 3-6 months (wiki may be stale)
else if research-wiki/ exists but query_pack.md is stale or missing:
    if [ -n "$WIKI_SCRIPT" ]: python3 "$WIKI_SCRIPT" rebuild_query_pack research-wiki/
    Then read query_pack.md as above
```

### Phase 1: Landscape Survey (5-10 min)

The landscape survey (paper collection, landscape map, structural gaps) is owned by `/research-lit`. This phase loads its output and optionally supplements it with fresh search.

#### Step 0: Load research-lit output (required)

Read the fixed latest literature review:

```
Read: idea-stage/LITERATURE_REVIEW.md
```

**If found**: Extract these sections:
- **Section 1** (paper table) → known-papers set for deduplication
- **Section 2** (landscape map) → sub-direction clusters, what's been tried
- **Section 2.5** (negative evidence) → `NE-*` table of refuted assumptions and
  multi-baseline failure modes; every surviving idea must declare a
  `negative_evidence_response` (see Phase 3 below)
- **Section 3** (structural gaps) → the 5-lens gap analysis — **this is the primary input for Phase 2 brainstorming**
- **Section 4** (Landscape Pack) → topic scope, bottleneck evidence (`Bottlenecks` and `Solution Attempts`), Evaluation Canon (`Platforms` and `Workloads`), `Gap Seeds`, and Competitive Landscape top competing papers / excluded competitors
- **Bottleneck Evidence** → `B*` bottlenecks plus `S*` solution attempts; use `Solution Attempts` as the mechanism source
- **Evaluation Canon** → `EC-P*` platform rows and `EC-W*` workload rows commonly used by papers in this topic
- **Verified evidence for baselines** → verified Section 1 papers/systems and Section 4 Competitive Landscape competitors that can seed idea-local baseline records

Announce: _"Loaded research-lit from `idea-stage/LITERATURE_REVIEW.md`: {N} papers, {V} verified papers, {NE} negative-evidence rows, {M} structural gaps, {K} Gap Seeds, {P} platforms, and {W} workloads for {topic} identified."_

**If not found**: Warn the user:
> ⚠️ No `idea-stage/LITERATURE_REVIEW.md` found. Please run `/research-lit "{topic}"` first to generate the landscape map and structural gaps.

Then terminate the entire workflow early.

### Phase 2: Idea Generation (brainstorm with external LLM)

Use the selected reviewer backend (see Reviewer Calling Convention) for divergent thinking.

*For `codex` backend:*

```
mcp__codex__codex:
  model: REVIEWER_MODEL
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    You are a senior researcher brainstorming publishable research ideas for the topic and venues implied by the supplied literature review.
```

*For `manual` backend:* use `mcp__manual_review__review` with the exact same prompt text and `config: {"model_reasoning_effort": "xhigh"}`. Save the returned `threadId` for Phase 4 follow-up.

The brainstorming prompt:

```
    You are a senior researcher brainstorming publishable research ideas for the topic and venues implied by the supplied literature review.

    Research direction: [user's direction]
    Domain context: [paste Topic Scope from /research-lit Section 4]

    Here is the current landscape (from /research-lit Section 2):
    [paste landscape map — sub-direction clusters]

    Negative evidence (from /research-lit Section 2.5) -- AUDIT INPUT:
    [paste the NE-* table verbatim, including claim, source, affected_methods, affected_assumption, confidence, linked_gaps]
    Avoid ideas whose hidden assumption matches any NE-*.affected_assumption
    unless the idea explicitly describes a mechanism that evades or addresses that
    assumption. For every idea you generate, populate a new field
    `negative_evidence_response`:
      - `n/a` if no NE-* affects this idea
      - `evades: NE-X (reason)` if the idea's mechanism sidesteps the refuted
        assumption
      - `addresses: NE-X (mechanism)` if the idea explicitly targets the
        refuted assumption with a corrective mechanism
      - `conflicts: NE-X (rationale)` only if the idea proposes to re-test the
        negative evidence itself (rare; must include why the original finding
        may not generalize)

    Structural gaps identified (from /research-lit Section 3):
    [paste the 5-lens gap analysis: cross-domain / contradictions / untested assumptions / unexplored regimes / unasked questions]

    Top competing papers (from /research-lit Section 4 Competitive Landscape):
    [paste competitive landscape — top 3 papers and what they leave open]

    Landscape Pack (from /research-lit Section 4):
    [paste Topic Scope, Bottleneck Evidence, Evaluation Canon, and Gap Seeds]
    `Bottleneck Evidence` contains `Bottlenecks` and `Solution Attempts`; use `Solution Attempts` as the mechanism source.
    `Evaluation Canon` contains `Platforms` and `Workloads`.

    Evaluation Canon platform/workload references extracted from the literature:
    [paste Evaluation Canon > Platforms rows with EC-P* IDs, evaluation_platform, access_readiness, supported_workloads, validates_refs, artifact_access_path, and platform_limitations; paste Evaluation Canon > Workloads rows with EC-W* IDs, workload_characteristics, representative papers, and representativeness_limits]

    Verified baseline evidence extracted from the literature:
    [paste verified paper/system and competitor rows that could become idea-local baseline records]

    Generate 8-12 concrete research ideas. Phase 2 is divergent: do not assign final ranking, feasibility, handoff, or Workflow 1.5 contract fields yet. For each idea:
    1. idea_id: stable short ID
    2. title
    3. idea_shape: one compact paragraph describing the idea, the gap it targets, the proposed mechanism/study, and why the answer may matter
    4. evaluation_platform_candidates: EC-P* candidates or missing
    5. evaluation_workload_candidates: EC-W* candidates or missing
    6. baseline_candidate_hint: verified paper/system candidate, quick_lookup_needed, or missing
    7. validation_route_hint: analytical_model | simulator_evaluation | prototype_measurement | unknown
    8. early_risk_notes
    9. estimated_effort: hours | days | weeks | platform_bringup
    10. negative_evidence_response: `n/a` | `evades: NE-X (reason)` | `addresses: NE-X (mechanism)` | `conflicts: NE-X (rationale)`

    Prioritize ideas that are:
    - Grounded in the topic's literature-derived EC-P*/EC-W* platform/workload candidates
    - Clear enough for Phase 3 to define the comparison target, decisive metrics, and target validation style
    - Diverse across the topic-derived mechanism families, bottlenecks, validation routes, and research shapes
    - Not "integrate X with Y" unless the integration reveals surprising performance/design insights
    - Differentiated from the 10-15 papers above
    - Targeting the venue bar implied by the topic scope and closest competing papers

    Be creative but grounded. A strong idea is one whose answer — positive or negative — changes design judgment in the loaded topic.
```

Save the threadId for follow-up.

### Phase 3: First-Pass Filtering

For each generated idea, convert the Phase 2 hints into authoritative ranking and handoff fields. Use the `Scoring and Filtering Rubric` above; do not redefine another scoring scheme here.

1. **Audit negative evidence**:
   - **Negative-evidence audit** (when Section 2.5 has any `NE-*` rows):
     - Reject ideas with `negative_evidence_response = n/a` whose hidden
       assumption (extracted from `idea_shape` mechanism) matches any
       `NE-*.affected_assumption`. Re-classify as `eliminated` with reason
       `refuted_by_NE-X`; do not just downrank.
     - Accept `evades: NE-X (reason)` only if the reason names a concrete
       mechanism that does not rely on the refuted assumption. Vague evasions
       (e.g., "we focus on a different metric") become `needs_canon_clarification`
       with `main_blocker: unclear_negative_evidence_response`.
     - Accept `addresses: NE-X (mechanism)` only if the mechanism is a concrete
       mechanism / measurement intervention, not a restatement of the gap.
       Add `decisive_metric_must_include: NE-X failure mode` to the
       evaluation_handoff_plan.
     - Accept `conflicts: NE-X (rationale)` only when the idea is itself a
     diagnostic re-test of the negative evidence; downrank `overall_merit`
     by one step (5->4, 4->3, 3->2) unless the rationale identifies a concrete
     scope where the original NE-* finding may not generalize.
     - When Section 2.5 is `none_identified` or absent, this gate is inactive;
       record `idea_health.negative_evidence_gate: inactive` in the final
       report rather than skipping silently.

2. **Overall merit estimation**:
   - Run a quick novelty check with 2-3 targeted searches for closest work; full `/novelty-check` comes later for survivors.
   - Assign `overall_merit_score: 1 | 2 | 3 | 4 | 5` using the reviewer-style scale above.
   - Write `overall_merit_rationale`: closest known work, differentiation, likely impact, and whether positive or negative results would matter.
   - Use quick closest-work checks only to calibrate `overall_merit_score`: already-covered ideas should usually become `already_done` or score 1; differentiated and impactful ideas may score 4 or 5.

3. **Evaluation target definition**:
   - Populate the handoff fields from `../shared-references/idea-handoff-schema.md`.
   - Do not place baseline or metrics inside `canon_mapping`; it only records `platform=[EC-P*]; workload=[EC-W*]`.
   - Prefer a verified Section 1 paper/system or Section 4 competitor; if the best comparison target is absent, run narrow quick baseline lookup, announce the lookup to the user, verify only the new candidate with `verify_papers.py`, and record `baseline_verification_delta` before treating it as ready.

4. **Evaluation target feasibility assessment**:
   - For every idea, you MUST explicitly output both the `overall_merit_score` (1-5) and the `evaluation_feasibility_score` (1-5).
   - For the `evaluation_feasibility_score`, you MUST provide `evaluation_feasibility_breakdown` with four sub-factors:
     1) **`platform_workload_access`**: access to required platform/hardware and workload/data
     2) **`baseline_artifact_readiness`**: `score`, `status`, `verification_status`, `evidence`, and `adapter_notes`
     3) **`evaluation_adapter_cost`**: adapter/integration work required before the first pilot
     4) **`first_signal_runtime`**: time required to run the decisive metric experiment
   - Summarize how these four sub-factors yield the final merged `evaluation_feasibility_score`.

5. **Defer, eliminate, and rank**:
   - Eliminate `overall_merit_score: 1` ideas by default. Negative-result, benchmark, or measurement ideas should only survive if the likely finding itself justifies `overall_merit_score: 3-5`.
   - Mark high-merit but `evaluation_feasibility_score <= 3` ideas as not immediate: use `needs_canon_clarification` when clarification could raise readiness, or `designed_not_run` for long-horizon platform/prototype work.
   - Mark missing EC-P/EC-W evidence as `needs_canon_clarification` or `main_blocker: unclear_canon_mapping`.
   - Mark unclear comparison targets as `main_blocker: unclear_comparison_target`.
   - Mark `baseline_artifact_readiness.score: 0` ideas as `designed_not_run`, `needs_canon_clarification`, or blocked by `main_blocker`; they must not be marked `handoff_to_workflow_1_5: ready`.
   - Mark `handoff_to_workflow_1_5: ready` only when `evaluation_feasibility_score` is `4` or `5`.
   - Mark ideas with no credible analytical, simulation, artifact, benchmark, trace/workload, or prototype route as `main_blocker: no_credible_evaluation_path` and eliminate or defer based on merit.
   - Rank surviving ideas with `overall_merit_score` 60% and `evaluation_feasibility_score` 40%. Keep all viable ideas in priority order; handoff planning will attempt them one at a time.

### Phase 4: Deep Validation (for priority-ordered survivors)

For each surviving idea in priority order, run a deeper evaluation:

1. **Novelty check**: Use the `/novelty-check` workflow (multi-source search + cross-model verification) for each idea

2. **Critical review**: Use the selected reviewer backend (see Reviewer Calling Convention). For `codex`, use `mcp__codex__codex-reply` (same thread). For `manual`, use `mcp__manual_review__review_reply` with the saved threadId:
   ```
   Here are our top ideas after filtering:
   [paste surviving ideas with idea_shape, quick novelty results, overall_merit_score, overall_merit_rationale, canon_mapping, core_baseline, baseline_artifact_readiness, baseline_verification_delta, metrics, target_validation_style, evaluation_target_clarity, evaluation_feasibility_score, evaluation_feasibility_breakdown, handoff_to_workflow_1_5, and main_blocker]

   For each, play devil's advocate:
   - What's the strongest objection a target-venue reviewer would raise?
   - What's the most likely failure mode (e.g., bottleneck too small, model abstraction too weak, overhead dominates, workload not representative)?
   - **Negative-evidence audit**: does this idea silently rely on any
     assumption that Section 2.5's `NE-*` rows have refuted? Is the stated
     `negative_evidence_response` concrete enough, or is it cosmetic? If
     `addresses: NE-X`, does the proposed `decisive_metric` actually surface
     the NE-X failure mode and not just hide it behind aggregate scores?
   - Evaluate and provide the `overall_merit_score` (1-5), and explain why.
   - Evaluate and provide the `evaluation_feasibility_score` (1-5). You MUST explicitly break down this score into the 4 sub-factors: 1) `platform_workload_access`, 2) `baseline_artifact_readiness`, 3) `evaluation_adapter_cost`, and 4) `first_signal_runtime`. Is the evaluation target feasible enough for a credible first-signal pilot, or should it be deferred?
   - Does the proposed platform/workload mapping cite the right EC-P*/EC-W* items?
   - Is the selected core baseline credible for this idea, and are the chosen metrics decisive?
   - Is the novelty credible after considering the closest papers?
   - Which ideas have a positive-or-negative answer that would change design judgment?
   - How would you rank these for a top venue submission?
   - Which highest-priority idea is ready for Workflow 1.5 now, and which high-upside backups should be deferred or sent back for EC-P*/EC-W* or comparison-target clarification?

   For systems or architecture ideas:
   - Is the named bottleneck real and central, or is the idea mostly an implementation detail without a decisive research question?
   ```

3. **Combine rankings**: Merge your assessment with the reviewer's ranking. Produce a single priority-ordered survivor list. The first idea with a clear comparison target, platform/workload mapping, decisive metrics, and feasible baseline path becomes the immediate Workflow 1.5 candidate; later viable ideas remain backups or deferred options.

### Phase 5: Evaluation Handoff Planning (priority-ordered ideas)

Workflow 1 does **not** run pilots or baseline reproduction. It only prepares enough evaluation context for Workflow 1.5 (`/experiment-bridge`) to lock an `EVALUATION_CONTRACT.md` and run baseline-first pilots after the idea and evaluation platform are selected.

Start with the highest-ranked surviving idea. Write an `evaluation_handoff_plan`
that follows `../shared-references/idea-handoff-schema.md`; use the shared
ready, clarification, and designed-not-run rules without copying the schema
inline.

If the highest-ranked idea cannot reach a reproducible baseline path, stop
trying to force it into `ready`: warn the user, record the failed handoff attempt
in `baseline_verification_delta`, `main_blocker`, and the report's deferred
ideas section, then try the next ranked surviving idea. Continue in priority
order until one idea reaches `handoff_to_workflow_1_5: ready` or every survivor
has a recorded blocker.

### Phase 6: Output — Ranked Idea Report

Write `idea-stage/IDEA_REPORT.md` from
`templates/IDEA_REPORT_TEMPLATE.md`. The report must include all
selected, backup, deferred, and eliminated ideas, but only the selected top idea
should be marked for `/research-refine-pipeline`.

If `COMPACT=true`, also write `idea-stage/IDEA_CANDIDATES.md` from
`templates/IDEA_CANDIDATES_TEMPLATE.md`.

## Phase 7: Write Ideas to Research Wiki (if active)

**Skip this phase entirely if `research-wiki/` does not exist.**

This is critical for spiral learning — without it, `ideas/` stays empty and re-ideation has no memory.

`$WIKI_SCRIPT` was resolved in Phase 0 above. If Phase 0 did not run
(no `research-wiki/`), this phase is skipped. If Phase 0 ran but the
resolution chain failed to find the helper (`$WIKI_SCRIPT` is empty),
the page-write step still runs (idea pages are plain markdown the
agent writes directly), but the edge / query-pack / log steps that
require the helper are skipped with a single warning.

```
if research-wiki/ exists:
    for each idea in recommended_ideas + eliminated_ideas:
        1. Create page: research-wiki/ideas/<idea_id>.md
           - node_id: idea:<id>
           - stage: proposed (or: handed_off, deferred, archived)
           - outcome: unknown (or: negative, mixed, positive)
           - based_on: [paper:<slug>, ...]
           - target_gaps: [gap:<id>, ...]
           - Include: hypothesis, proposed method, expected outcome
           - If Workflow 1.5 later ran: actual outcome, failure notes, reusable components

        2. Add edges (only if $WIKI_SCRIPT resolved):
           [ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" add_edge research-wiki/ --from "idea:<id>" --to "paper:<slug>" --type inspired_by --evidence "..."
           [ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" add_edge research-wiki/ --from "idea:<id>" --to "gap:<id>" --type addresses_gap --evidence "..."

    Rebuild query pack (only if $WIKI_SCRIPT resolved):
        [ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" rebuild_query_pack research-wiki/
    Log (only if $WIKI_SCRIPT resolved):
        [ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" log research-wiki/ "idea-creator wrote N ideas (M recommended, K eliminated)"

    if [ -z "$WIKI_SCRIPT" ]:
        echo "WARN: idea pages were written but edges / query_pack / log were skipped because research_wiki.py is unreachable (see Phase 0 warning above)." >&2
```

## Output Protocols

> Follow these shared protocols for all output files:
> - **[Output Versioning Protocol](../shared-references/output-versioning.md)** — write timestamped file first, then copy to fixed name
> - **[Output Manifest Protocol](../shared-references/output-manifest.md)** — log every output to MANIFEST.md
> - **[Output Language Protocol](../shared-references/output-language.md)** — respect the project's language setting

## Key Rules

- **Large file handling**: If the Write tool fails due to file size, immediately retry using Bash (`cat << 'EOF' > file`) to write in chunks. Do NOT ask the user for permission — just do it silently.

- The user provides a DIRECTION, not an idea. Your job is to generate the ideas.
- Quantity first, quality second: brainstorm broadly, then filter ruthlessly.
- A good negative result is just as publishable as a positive one. Prioritize ideas where the answer matters regardless of direction.
- Don't fall in love with any idea before validating it. Be willing to kill ideas.
- Always estimate implementation and validation cost. An idea that needs a new simulator, a private trace corpus, or a long platform bring-up should get `evaluation_feasibility_score <= 2` or a `designed_not_run` handoff; that is not the same as scientific rejection.
- "Apply X to Y" is the lowest form of research idea. Push for deeper questions.
- Include eliminated ideas in the report — they save future time by documenting dead ends.
- **If the user's direction is too broad (e.g., only a field name with no workload, mechanism, object of study, or validation target), STOP and ask them to narrow it.** A good direction is 1-2 sentences specifying the problem, workload or mechanism focus, and validation constraint, using terms that match the loaded literature scope.

## Composing with Other Skills

After this skill produces the ranked report:
```
/idea-creator "direction"     → ranked ideas
/novelty-check "top idea"     → deep novelty verification (already done in Phase 4, but user can re-run)
/research-review "top idea"   → external critical feedback
/experiment-bridge            → lock EVALUATION_CONTRACT.md and prepare baseline-first execution
/run-experiment               → execute the experiment command selected by Workflow 1.5
/auto-review-loop             → iterate until submission-ready
```

## Review Tracing

After each reviewer call (`mcp__codex__codex`, `mcp__codex__codex-reply`, `mcp__manual_review__review`, or `mcp__manual_review__review_reply`), save the trace following `shared-references/review-tracing.md` (Policy C — forensic; never silently skip). Use `save_trace.sh` (resolved per the chain in `shared-references/integration-contract.md` §2) or write files directly to `.aris/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
