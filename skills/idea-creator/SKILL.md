---
name: idea-creator
description: Generate and rank research ideas given a broad direction. Use when user says "找idea", "brainstorm ideas", "generate research ideas", "what can we work on", or wants to explore a research area for publishable directions.
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Grep, Glob, WebSearch, WebFetch, Agent, mcp__codex__codex, mcp__codex__codex-reply
---

# Research Idea Creator

Generate publishable research ideas for: $ARGUMENTS

## Overview

Given a broad research direction from the user, systematically generate, validate, and rank concrete research ideas. This skill composes with `/research-lit`, `/novelty-check`, and `/research-review` to form a complete idea discovery pipeline.

For this repository, the default domain is **AI infrastructure for LLM** with a computer architecture / systems bias. Valid ideas may sit in compute, memory, data movement, network, storage, runtime, or their boundaries. Do not impose protocol-, platform-, or mechanism-specific constraints globally; derive the right evaluation platforms, benchmarks, baselines, and metrics from the literature for the current topic.

## Constants

- **MAX_HANDOFF_IDEAS = 6** — Write evaluation handoff plans for at most 6 strong ideas. Workflow 1 does not execute pilots.
- **MAX_READY_FOR_WORKFLOW_1_5 = 3** — Mark at most 3 ideas as immediate Workflow 1.5 candidates.
- **REVIEWER_MODEL = `gpt-5.5`** — Model used via Codex MCP for brainstorming and review. Must be an OpenAI model (e.g., `gpt-5.5`, `o3`, `gpt-4o`).
- **REVIEWER_BACKEND = `codex`** — Default: Codex MCP (xhigh). Override with `— reviewer: oracle-pro` for GPT-5.5 Pro via Oracle MCP. See `shared-references/reviewer-routing.md`.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.


> Override via argument, e.g., `/idea-creator "topic" — handoff: analytical_model only`.

## AI Infrastructure Layer Taxonomy

Use this taxonomy to organize ideas and keep the brainstorm diverse. It is not a requirement that every run cover every layer, and ideas may be single-layer or multi-layer.

| Layer | Examples | Likely validation styles | Key metrics |
|-------|----------|--------------------------|-------------|
| `compute/accelerator` | attention/KV kernels, sparsity datapaths, inference accelerators, near-data compute | analytical_model, simulator_evaluation, prototype_measurement | TOPS/W, utilization, latency, SRAM pressure, area/power |
| `memory/storage/data movement` | KV cache hierarchy, CXL memory, HBM pressure, compression, prefetch | analytical_model, simulator_evaluation, prototype_measurement | GB/s, tail latency, cache miss rate, write amplification |
| `interconnect/network` | collectives, congestion, packet/flow scheduling, transport offload, programmable datapaths | analytical_model, simulator_evaluation, prototype_measurement | goodput, FCT, tail latency, retransmitted bytes, bandwidth utilization |
| `storage/checkpointing/data pipeline` | checkpoint bursts, object store, SSD pipeline, data loading | analytical_model, simulator_evaluation, prototype_measurement | checkpoint time, recovery time, IOPS, bandwidth, endurance |
| `runtime/system` | batching, admission, prefill/decode split, KV placement | analytical_model or simulator_evaluation, only when tied to a hardware/system bottleneck | HBM capacity, accelerator utilization, PCIe/network/storage traffic, tail latency |

## Scoring and Filtering Rubric

Use this rubric in Phase 3. Phase 2 only generates candidate ideas and hints.

Hard gates:
1. The problem must be an LLM / AI infrastructure problem in the selected topic scope.
2. The idea must name a concrete architecture, systems, measurement, benchmark, trace/workload, or mechanism question.

Default weighted score after hard gates:
- Overall merit: 60%
- Evaluation target feasibility: 40%

`overall_merit_score` follows a MICRO/HPCA-style reviewer scale where 1 is best and 4 is worst:
- `1`: Surprisingly new contribution, or likely to have major impact on future research/products; may inspire new research or start a new line.
- `2`: New contribution, or likely to impact future research/products.
- `3`: Incremental improvement, or likely to have minor impact.
- `4`: No novelty, or unlikely to have meaningful impact.

For weighted ranking, convert it with `overall_merit_points = 5 - overall_merit_score`.

`evaluation_target_feasibility` estimates the distance to a credible first-signal pilot:
- It is an aggregate score from `baseline_reproducibility`, `evaluation_environment_access`, `idea_adapter_cost`, and `pilot_runtime_cost`.
- `high`: baseline is `official_artifact`, `open_source_system`, or `config_reproducible`; environment is `ready` or `small_adapter_needed`; idea adapter cost is `parameter_or_config_only`, `small_local_patch`, or `moderate_adapter`; `pilot_runtime_cost` is exactly `minutes_to_hours`; no subfactor is unknown and there is no unavailable/proprietary artifact, unavailable environment, or major platform bring-up.
- `medium`: comparison target and evaluation environment are credible, but first-signal feedback takes `one_to_two_days` or `multi_day_to_two_weeks`, or the idea needs `major_system_change` while baseline/platform/workload remain available; no hard blocker is present.
- `low`: baseline is paper-only/proprietary, platform/workload needs major bring-up, idea needs a new platform/prototype, workload is unavailable, or first-signal pilot is long-running/large-scale. Keep high-merit ideas as deferred rather than eliminated.
- `unknown`: key artifact, platform, workload, baseline, or runtime information is missing; return to artifact/canon clarification rather than treating it as scientific rejection.

For weighted ranking, map feasibility as `high=4`, `medium=3`, `low=2`, `unknown=1`.

## Evaluation Canon Extraction

Before brainstorming, extract the current topic's evaluation canon from `idea-stage/LITERATURE_REVIEW.md`. This canon anchors idea quality without hard-coding any previous topic's assumptions.

From the literature review, identify:
- **Evaluation Canon**: item-level `evaluation_platform` and `benchmark_workload` rows with stable `EC-P*` / `EC-W*` IDs, supporting evidence, access status, and limitations.
- **Core Baseline Candidates**: baseline candidates with stable `CB*` IDs, original evaluation platform/workload/metrics, artifact status, and notes.

Use the canon in filtering and reviewer prompts as provenance for platform/workload choices. `canon_mapping` must only contain `platform=[EC-P*]; workload=[EC-W*]`. Baseline, metrics, and target validation style are idea-specific decisions: choose them from Core Baseline Candidates and the idea's hypothesis, not from a fixed canon menu. If the platform/workload canon is missing, mark `handoff_to_workflow_1_5: needs_canon_clarification` or `main_blocker: unclear_canon_mapping`; do not invent a platform requirement from a different topic.

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
- **Section 3** (structural gaps) → the 5-lens gap analysis — **this is the primary input for Phase 2 brainstorming**
- **Section 4** (competitive landscape) → top competing papers and positioning
- **Section 5** (Landscape Pack) → topic scope, bottleneck evidence, Evaluation Canon, Core Baseline Candidates, simulator/prototype readiness, and `Gap Seeds`
- **Evaluation Canon** → platform/workload rows commonly used by papers in this topic
- **Core Baseline Candidates** → baseline candidates and their original platform/workload/metrics/artifact status

Announce: _"Loaded research-lit from `idea-stage/LITERATURE_REVIEW.md`: {N} papers, {M} structural gaps, {K} Gap Seeds, {P} Evaluation Canon items, and {B} Core Baseline Candidates for {topic} identified."_

**If not found**: Warn the user:
> ⚠️ No `idea-stage/LITERATURE_REVIEW.md` found. It is strongly recommended to run `/research-lit "{topic}"` first — it produces the landscape map and structural gaps that drive idea quality. Proceeding with a minimal web-only landscape survey (results will be shallower).

Then run a condensed version: WebSearch across MICRO/ISCA/HPCA/NSDI/SIGCOMM for top 10 papers, build a basic landscape map, and identify gaps as best as possible.

> **All literature search and landscape work (including incremental web search) is done by `/research-lit`.** If the loaded output is stale or incomplete, re-run `/research-lit` first rather than searching here. idea-creator does not search for papers. Use `Gap Seeds` from the Landscape Pack as the main idea-generation substrate.

### Phase 2: Idea Generation (brainstorm with external LLM)

Use the external LLM via Codex MCP for divergent thinking:

```
mcp__codex__codex:
  model: REVIEWER_MODEL
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    You are a senior computer architecture / systems researcher (MICRO/ISCA/HPCA/ASPLOS/NSDI/SIGCOMM level) brainstorming research ideas.

    Research direction: [user's direction]
    Domain context: AI infrastructure for LLM. Valid layers include compute/accelerator, memory/storage/data movement, interconnect/network, storage/checkpointing/data pipeline, runtime/system, and multi-layer topics. Runtime/serving ideas are only valid if they expose or control a concrete hardware or system bottleneck.

    Here is the current landscape (from /research-lit Section 2):
    [paste landscape map — sub-direction clusters]

    Structural gaps identified (from /research-lit Section 3):
    [paste the 5-lens gap analysis: cross-domain / contradictions / untested assumptions / unexplored regimes / unasked questions]

    Top competing papers (from /research-lit Section 4):
    [paste competitive landscape — top 3 papers and what they leave open]

    Landscape Pack (from /research-lit Section 5):
    [paste Topic Scope, Bottleneck Evidence, Evaluation Canon, Core Baseline Candidates, Simulator / Prototype Readiness, and Gap Seeds]

    Evaluation canon extracted from the literature:
    [paste item-level Evaluation Canon rows: evaluation_platform and benchmark_workload only, with EC-P*/EC-W* IDs, access status, and limitations]

    Core baseline candidates extracted from the literature:
    [paste Core Baseline Candidates rows with CB* IDs, original platform/workload/metrics, and artifact status]

    Generate 8-12 concrete research ideas. Phase 2 is divergent: do not assign final ranking, feasibility, handoff, or Workflow 1.5 contract fields yet. For each idea:
    1. idea_id: stable short ID
    2. title
    3. idea_shape: one compact paragraph describing the idea, the gap it targets, the proposed mechanism/study, and why the answer may matter
    4. canon_platform_candidates: EC-P* candidates or missing
    5. canon_workload_candidates: EC-W* candidates or missing
    6. baseline_candidate_hint: CB* candidate or new_baseline_hint
    7. validation_route_hint: analytical_model | simulator_evaluation | prototype_measurement | unknown
    8. early_risk_notes
    9. estimated_effort: hours | days | weeks | platform_bringup

    Prioritize ideas that are:
    - Grounded in the topic's literature-derived platform/workload canon candidates
    - Clear enough for Phase 3 to define the comparison target, decisive metrics, and target validation style
    - Diverse across AI infrastructure layers and research shapes, without requiring cross-layer mechanisms
    - Not "integrate X with Y" unless the integration reveals surprising performance/design insights
    - Differentiated from the 10-15 papers above
    - Targeting MICRO/ISCA/HPCA/ASPLOS/NSDI/SIGCOMM/OSDI/USENIX ATC/EuroSys/FCCM/DAC bar

    Be creative but grounded. A great architecture idea is one whose answer — positive or negative — changes how people design AI infrastructure hardware or hardware/software boundaries.
```

Save the threadId for follow-up.

### Phase 3: First-Pass Filtering

For each generated idea, convert the Phase 2 hints into authoritative ranking and handoff fields. Use the `Scoring and Filtering Rubric` above; do not redefine another scoring scheme here.

1. **Apply hard gates from the rubric**:
   - Reject ideas outside the selected AI infrastructure topic.
   - Reject ideas without a concrete architecture, systems, measurement, benchmark, trace/workload, or mechanism question.

2. **Overall merit estimation**:
   - Run a quick novelty check with 2-3 targeted searches for closest work; full `/novelty-check` comes later for survivors.
   - Assign `overall_merit_score: 1 | 2 | 3 | 4` using the reviewer-style scale above.
   - Write `overall_merit_rationale`: closest known work, differentiation, likely impact, and whether positive or negative results would matter.
   - Use quick closest-work checks only to calibrate `overall_merit_score`: already-covered ideas should usually become `already_done` or score 4; differentiated and impactful ideas may score 1 or 2.

3. **Evaluation target definition**:
   - Assign `canon_mapping`: `platform=[EC-P*]; workload=[EC-W*]`. Do not place baseline or metrics inside `canon_mapping`.
   - Select `core_baseline` from Core Baseline Candidates, or use `new_baseline_with_rationale` when the comparison target is new.
   - Assign `metrics`: decisive metric first, secondary metrics only when needed.
   - Assign `target_validation_style`: `analytical_model`, `simulator_evaluation`, or `prototype_measurement`.
   - Assign `evaluation_target_clarity`: `clear`, `partial`, or `missing`.

4. **Evaluation target feasibility assessment**:
   - Assign `baseline_reproducibility`: `official_artifact`, `open_source_system`, `config_reproducible`, `paper_only`, `proprietary_or_unavailable`, or `unknown`.
   - Assign `evaluation_environment_access`: `ready`, `small_adapter_needed`, `major_bringup_needed`, `unavailable`, or `unknown`.
   - Assign `idea_adapter_cost`: `parameter_or_config_only`, `small_local_patch`, `moderate_adapter`, `major_system_change`, or `new_platform_or_prototype`.
   - Assign `pilot_runtime_cost`: `minutes_to_hours`, `one_to_two_days`, `multi_day_to_two_weeks`, `long_running_or_large_scale`, or `unknown`.
   - Assign aggregate `evaluation_target_feasibility`: `high`, `medium`, `low`, or `unknown`, using the rubric. Explain the dominant cost or blocker.

5. **Defer, eliminate, and rank**:
   - Eliminate `overall_merit_score: 4` ideas by default. Negative-result, benchmark, or measurement ideas should only survive if the likely finding itself justifies `overall_merit_score: 1-3`.
   - Mark high-merit but low-feasibility ideas as `handoff_to_workflow_1_5: designed_not_run`, not eliminated.
   - Mark missing EC-P/EC-W evidence as `needs_canon_clarification` or `main_blocker: unclear_canon_mapping`.
   - Mark unclear comparison targets as `main_blocker: unclear_comparison_target`.
   - Mark ideas with no credible analytical, simulation, artifact, benchmark, trace/workload, or prototype route as `main_blocker: no_credible_evaluation_path` and eliminate or defer based on merit.
   - Rank surviving ideas with `overall_merit` 60% and `evaluation_target_feasibility` 40%. Typically 8-12 ideas reduce to 4-6.

### Phase 4: Deep Validation (for top ideas)

For each surviving idea, run a deeper evaluation:

1. **Novelty check**: Use the `/novelty-check` workflow (multi-source search + GPT-5.5 cross-verification) for each idea

2. **Critical review**: Use GPT-5.5 via `mcp__codex__codex-reply` (same thread):
   ```
   Here are our top ideas after filtering:
   [paste surviving ideas with idea_shape, quick novelty results, overall_merit_score, overall_merit_rationale, canon_mapping, core_baseline, metrics, target_validation_style, evaluation_target_clarity, evaluation_target_feasibility, feasibility subfields, handoff_to_workflow_1_5, and main_blocker]

   For each, play devil's advocate:
   - What's the strongest objection a MICRO/ISCA/HPCA/ASPLOS/NSDI reviewer would raise?
   - What's the most likely failure mode (e.g., bottleneck too small, simulator abstraction too weak, area/power overhead dominates, workload not representative)?
   - What overall merit score would you assign, and why?
   - Does the proposed platform/workload mapping cite the right EC-P*/EC-W* items?
   - Is the selected core baseline credible for this idea, and are the chosen metrics decisive?
   - Is the novelty credible after considering the closest papers?
   - Which ideas have a positive-or-negative answer that would change design judgment?
   - Is the evaluation target feasible enough for a credible first-signal pilot, or should it be deferred?
   - How would you rank these for a top venue submission?
   - Which 2-3 are ready for Workflow 1.5, and which high-upside ideas should be deferred or sent back for canon/comparison-target clarification?

   For runtime/system ideas:
   - Is the hardware bottleneck real and central, or is this a pure software scheduler?
   ```

3. **Combine rankings**: Merge your assessment with GPT-5.5's ranking. Select top 4-6 ideas for evaluation handoff plans and top 2-3 ideas as immediate Workflow 1.5 candidates when their comparison target, platform/workload mapping, and feasibility are clear enough.

### Phase 5: Evaluation Handoff Planning (top 4-6 ideas)

Workflow 1 does **not** run pilots or baseline reproduction. It only prepares enough evaluation context for Workflow 1.5 (`/experiment-bridge`) to lock an `EVALUATION_CONTRACT.md` and run baseline-first pilots after the idea and evaluation platform are selected.

For each top 4-6 idea, write an `evaluation_handoff_plan`:

```markdown
### Evaluation Handoff Plan

- **core_baseline**: [CB* candidate, or new baseline with rationale]
- **canon_mapping**: platform=[EC-P*]; workload=[EC-W*]
- **metrics**: [decisive metric first, secondary metrics if needed]
- **target_validation_style**: analytical_model | simulator_evaluation | prototype_measurement
- **evaluation_target_clarity**: clear | partial | missing
- **evaluation_target_feasibility**: high | medium | low | unknown
- **baseline_reproducibility**: official_artifact | open_source_system | config_reproducible | paper_only | proprietary_or_unavailable | unknown
- **evaluation_environment_access**: ready | small_adapter_needed | major_bringup_needed | unavailable | unknown
- **idea_adapter_cost**: parameter_or_config_only | small_local_patch | moderate_adapter | major_system_change | new_platform_or_prototype
- **pilot_runtime_cost**: minutes_to_hours | one_to_two_days | multi_day_to_two_weeks | long_running_or_large_scale | unknown
- **platform_access_path**: [repo/artifact/simulator/benchmark path, or adapter needed]
- **main_blocker**: none | missing_artifact | trace_unavailable | backend_adapter | platform_bringup | unclear_canon_mapping | unclear_comparison_target | no_credible_evaluation_path | other
- **handoff_to_workflow_1_5**: ready | needs_canon_clarification | designed_not_run
```

Handoff rules:
- `ready`: core baseline, workload, metrics, and platform access are clear enough to enter the Workflow 1.5 handoff gate; this is not unconditional permission to execute.
- `needs_canon_clarification`: the idea is promising, but `canon_mapping` lacks clear EC-P*/EC-W* support or platform/workload evidence must be clarified before Workflow 1.5.
- `designed_not_run`: the idea is high-upside but currently blocked by unavailable platform, trace, artifact, or major adapter work. Treat it as deferred, not eliminated.

### Phase 6: Output — Ranked Idea Report

Write a structured report to `idea-stage/IDEA_REPORT.md`:

```markdown
# Research Idea Report

**Direction**: [user's research direction]
**Generated**: [UTC ISO-8601 timestamp ending in Z, e.g. 2026-04-26T02:26:45Z]
**Ideas evaluated**: X generated → Y survived filtering → Z received evaluation handoff plans → W recommended

## Landscape Summary
[3-5 paragraphs on the current state of the field]

## Recommended Ideas (ranked)

### Idea 1: [title]
- **Idea shape**: [compact summary of the idea, target gap, proposed mechanism/study, and why the answer matters]
- **Overall merit**: [1-4] — [overall_merit_rationale]
- **core_baseline**: [CB* candidate or new baseline with rationale]
- **canon_mapping**: platform=[EC-P*]; workload=[EC-W*]
- **metrics**: [decisive metric first, secondary metrics if needed]
- **target_validation_style**: analytical_model | simulator_evaluation | prototype_measurement
- **evaluation_target_clarity**: clear | partial | missing
- **evaluation_target_feasibility**: high | medium | low | unknown
- **baseline_reproducibility**: official_artifact | open_source_system | config_reproducible | paper_only | proprietary_or_unavailable | unknown
- **evaluation_environment_access**: ready | small_adapter_needed | major_bringup_needed | unavailable | unknown
- **idea_adapter_cost**: parameter_or_config_only | small_local_patch | moderate_adapter | major_system_change | new_platform_or_prototype
- **pilot_runtime_cost**: minutes_to_hours | one_to_two_days | multi_day_to_two_weeks | long_running_or_large_scale | unknown
- **Expected outcome**: [what success/failure looks like]
- **Feasibility**: [platform access path, data/trace availability, implementation estimates]
- **Estimated effort**: hours | days | weeks | platform bring-up
- **Risk**: LOW/MEDIUM/HIGH
- **handoff_to_workflow_1_5**: ready | needs_canon_clarification | designed_not_run
- **platform_access_path**: [repo/artifact/simulator/benchmark path, or adapter needed]
- **main_blocker**: none | missing_artifact | trace_unavailable | backend_adapter | platform_bringup | unclear_canon_mapping | unclear_comparison_target | no_credible_evaluation_path | other
- **Reviewer's likely objection**: [strongest counterargument]
- **Why we should do this**: [1-2 sentences]

### Idea 2: [title]
...

## Eliminated Ideas (for reference)
| Idea | Category | Reason | Revisit condition |
|------|----------|--------|-------------------|
| ... | already_done | Closest paper already covers the core mechanism/result | Revisit only if new workload/platform changes the conclusion |
| ... | not_ai_infrastructure | Idea falls outside the selected AI infrastructure topic | Revisit only if the project scope changes |
| ... | low_overall_merit | Contribution is incremental or unlikely to have impact | Revisit if a sharper contribution or stronger impact path appears |
| ... | unclear_canon_mapping | No credible EC-P*/EC-W* platform/workload path found in the topic literature | Revisit after better traces, benchmarks, or methodology are available |
| ... | missing_concrete_question | Pure software or ML idea without a concrete architecture, systems, measurement, benchmark, trace/workload, or mechanism question | Revisit if tied to a concrete infrastructure question |
| ... | no_credible_evaluation_path | No plausible platform/workload/baseline path found | Revisit after literature or artifact landscape changes |

## Deferred / Designed-Not-Run Ideas
| Idea | Reason deferred | Required clarification or platform path |
|------|-----------------|-----------------------------------------|
| ... | missing_artifact / trace_unavailable / backend_adapter / platform_bringup / unclear_canon_mapping / unclear_comparison_target / no_credible_evaluation_path / other | [what must become available before Workflow 1.5] |

## Evaluation Handoff Summary
| Idea | overall_merit_score | evaluation_target_feasibility | baseline_reproducibility | evaluation_environment_access | idea_adapter_cost | pilot_runtime_cost | core_baseline | canon_mapping | metrics | target_validation_style | evaluation_target_clarity | handoff_to_workflow_1_5 | main_blocker |
|------|---------------------|-------------------------------|--------------------------|-------------------------------|-------------------|--------------------|---------------|---------------|---------|-------------------------|---------------------------|-------------------------|--------------|
| Idea 1 | 1 | high | open_source_system | ready | small_local_patch | minutes_to_hours | CB1 | platform=[EC-P1]; workload=[EC-W1] | p99 latency, bandwidth utilization | simulator_evaluation | clear | ready | none |
| Idea 2 | 2 | medium | config_reproducible | small_adapter_needed | moderate_adapter | one_to_two_days | CB2 | platform=[EC-P2]; workload=[EC-W3] | FCT, utilization, tail latency | simulator_evaluation | partial | needs_canon_clarification | backend_adapter |

## Suggested Execution Order
1. Start with Idea 1 (highest overall merit and feasible first-signal path)
2. Keep Idea 2 as backup (good merit, needs canon or adapter clarification)
3. Archive eliminated ideas unless a stronger benchmark/baseline path appears

## Next Steps
- [ ] Move the selected idea to `/research-refine-pipeline`
- [ ] Let Workflow 1.5 run the handoff gate, create `refine-logs/EVALUATION_CONTRACT.md`, reproduce the core baseline, and run baseline-first evaluation pilots
- [ ] If confirmed, invoke /auto-review-loop for full iteration
```

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
- Always estimate implementation and validation cost. An idea that needs a new simulator, a private trace corpus, or a long platform bring-up should get low `evaluation_target_feasibility` or a `designed_not_run` handoff; that is not the same as scientific rejection.
- "Apply X to Y" is the lowest form of research idea. Push for deeper questions.
- Include eliminated ideas in the report — they save future time by documenting dead ends.
- **If the user's direction is too broad (e.g., "AI infrastructure" with no bottleneck, workload, or layer), STOP and ask them to narrow it.** A good direction is 1-2 sentences specifying the LLM infrastructure problem, hardware/system bottleneck, and validation constraint — e.g., "KV cache placement under CXL memory bandwidth limits" or "LLM checkpoint recovery under storage bandwidth and metadata pressure".

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

After each `mcp__codex__codex` or `mcp__codex__codex-reply` reviewer call, save the trace following `shared-references/review-tracing.md`. Use `tools/save_trace.sh` or write files directly to `.aris/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
