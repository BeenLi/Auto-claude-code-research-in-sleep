---
name: idea-creator
description: Generate and rank research ideas given a broad direction. Use when user says "找idea", "brainstorm ideas", "generate research ideas", "what can we work on", or wants to explore a research area for publishable directions.
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Grep, Glob, WebSearch, WebFetch, Agent, spawn_agent, send_input
---

# Research Idea Creator

Generate publishable research ideas for: $ARGUMENTS

## Overview

Given a broad research direction from the user, systematically generate, validate, and rank concrete research ideas. This skill composes with `/research-lit`, `/novelty-check`, and `/research-review` to form a complete idea discovery pipeline.

For this repository, the default domain is **AI infrastructure for LLM** with a computer architecture / systems bias. Valid ideas may sit in compute, memory, data movement, network, storage, runtime, or their boundaries. Do not impose protocol-, platform-, or mechanism-specific constraints globally; derive the right evaluation platforms, benchmarks, baselines, and metrics from the literature for the current topic.

## Constants

- **MAX_PILOT_IDEAS = 3** — Run pilots for at most 3 ideas. Additional strong ideas receive lightweight pilot plans but are not run in Workflow 1.
- **MAX_PILOT_PLANS = 6** — Write lightweight pilot plans for at most 6 ideas.
- **PILOT_MAX_HOURS = 2** — Keep each lightweight architecture pilot within two wall-clock hours. If a pilot needs platform bring-up, record `pilot_status: designed_not_run` and the blocker instead of stalling Workflow 1.
- **REVIEWER_MODEL = `gpt-5.5`** — Model used via Codex MCP for brainstorming and review. Must be an OpenAI model (e.g., `gpt-5.5`, `o3`, `gpt-4o`).
- **REVIEWER_BACKEND = `codex`** — Default: Codex MCP (xhigh). Override with `— reviewer: oracle-pro` for GPT-5.5 Pro via Oracle MCP. See `shared-references/reviewer-routing.md`.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.
- **RANKING_PROFILE = `scientific-taste`** — Apply hard gates first, then rank by scientific taste, evaluation credibility, novelty, validation feasibility, and LLM infrastructure importance.

> 💡 **Domain context**: This skill is configured for **AI infrastructure for LLM** research across compute/accelerator, memory/storage/data movement, interconnect/network, storage/checkpointing, and runtime/system. A concrete hardware or system bottleneck is mandatory. Simulator, trace, prototype, or platform readiness is a `readiness_risk` signal, not a default elimination reason.

> Override via argument, e.g., `/idea-creator "topic" — pilot: analytical only`.

## AI Infrastructure Layer Taxonomy

Use this taxonomy to organize ideas and keep the brainstorm diverse. It is not a requirement that every run cover every layer, and ideas may be single-layer or multi-layer.

| Layer | Examples | Typical validation backends | Key metrics |
|-------|----------|-----------------------------|-------------|
| `compute/accelerator` | attention/KV kernels, sparsity datapaths, inference accelerators, near-data compute | analytical model, gem5, GPGPU-Sim/Accel-Sim, RTL/HLS | TOPS/W, utilization, latency, SRAM pressure, area/power |
| `memory/storage/data movement` | KV cache hierarchy, CXL memory, HBM pressure, compression, prefetch | analytical model, gem5, trace replay, microbench | GB/s, tail latency, cache miss rate, write amplification |
| `interconnect/network` | collectives, congestion, packet/flow scheduling, transport offload, programmable datapaths | network simulator, gem5+network model, ns-3, microbench, trace replay | goodput, FCT, tail latency, retransmitted bytes, bandwidth utilization |
| `storage/checkpointing/data pipeline` | checkpoint bursts, object store, SSD pipeline, data loading | analytical model, trace replay, storage microbench | checkpoint time, recovery time, IOPS, bandwidth, endurance |
| `runtime/system` | batching, admission, prefill/decode split, KV placement | only when tied to hardware model; analytical/gem5/trace replay | HBM capacity, accelerator utilization, PCIe/network/storage traffic, tail latency |

Hard gates:
1. The problem must be an LLM infrastructure problem.
2. The idea must name a concrete hardware or system bottleneck.
3. The idea must have a minimum validation path: analytical model, simulator, trace replay, RTL/HLS sketch, prototype, or another credible route used in the topic's literature.


Default weighted score after hard gates:
- Scientific taste: 30%
- Evaluation canon fit: 25%
- Novelty: 20% (minimum 2/5)
- Validation feasibility: 15%
- LLM bottleneck importance: 10%

Readiness tiers:
- **Ready**: can run now using existing analytical scripts, simulators, traces, public benchmarks, or local microbenchmarks.
- **Partial**: needs adapter work, trace conversion, small benchmark construction, or lightweight modeling before it can run.
- **Future**: needs new platform bring-up, large real cluster, proprietary traces, or unavailable hardware.

Treat readiness as `readiness_risk`. Do not eliminate a scientifically strong idea only because it is not immediately runnable; mark it as `designed_not_run` and describe the blocker unless there is no credible validation path at all.

## Evaluation Canon Extraction

Before brainstorming, extract the current topic's evaluation canon from `idea-stage/LITERATURE_REVIEW.md`. This canon anchors idea quality without hard-coding any previous topic's assumptions.

From the literature review, identify:
- **evaluation_platforms**: simulators, prototypes, real systems, analytical models, trace frameworks, or hardware platforms commonly used by papers in this topic.
- **benchmarks_workloads**: public benchmarks, traces, synthetic workloads, microbenchmarks, or application workloads used in the area.
- **baselines**: systems, algorithms, hardware mechanisms, policies, or published results that papers compare against.
- **metrics**: throughput, latency, tail behavior, bandwidth, utilization, energy, area, accuracy, reliability, recovery time, or other topic-standard metrics.
- **validation_style**: the level of evidence papers usually provide, such as analytical sensitivity, trace replay, cycle simulation, RTL/HLS synthesis, hardware measurement, or end-to-end system experiments.
- **known_limitations**: missing traces, simulator abstraction gaps, platform bring-up cost, scale limits, or unrealistic assumptions reported by the literature.

Use the canon in filtering and reviewer prompts. If the canon is weak or missing, mark `evaluation_canon_fit: weak` and explain what evidence would be needed; do not invent a platform requirement from a different topic.

## Workflow

### Phase 0: Load Research Wiki (if active)

**Skip this phase entirely if `research-wiki/` does not exist.**

```
if research-wiki/query_pack.md exists AND is less than 7 days old:
    Read query_pack.md and use it as initial landscape context:
    - Treat listed gaps as priority search seeds
    - Treat failed ideas as a banlist (do NOT regenerate similar ideas)
    - Treat top papers as known prior work (do not re-search them)
    Still run Phase 1 below for papers from the last 3-6 months (wiki may be stale)
else if research-wiki/ exists but query_pack.md is stale or missing:
    python3 tools/research_wiki.py rebuild_query_pack research-wiki/
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
- **Section 5** (Landscape Pack) → topic scope, bottleneck evidence, simulator/prototype readiness, and `Gap Seeds`
- **Evaluation canon** → platforms, benchmarks/workloads, baselines, metrics, validation style, and known limitations commonly used by papers in this topic

Announce: _"Loaded research-lit from `idea-stage/LITERATURE_REVIEW.md`: {N} papers, {M} structural gaps, {K} Gap Seeds, and evaluation canon for {topic} identified."_

**If not found**: Warn the user:
> ⚠️ No `idea-stage/LITERATURE_REVIEW.md` found. It is strongly recommended to run `/research-lit "{topic}"` first — it produces the landscape map and structural gaps that drive idea quality. Proceeding with a minimal web-only landscape survey (results will be shallower).

Then run a condensed version: WebSearch across MICRO/ISCA/HPCA/NSDI/SIGCOMM for top 10 papers, build a basic landscape map, and identify gaps as best as possible.

> **All literature search and landscape work (including incremental web search) is done by `/research-lit`.** If the loaded output is stale or incomplete, re-run `/research-lit` first rather than searching here. idea-creator does not search for papers. Use `Gap Seeds` from the Landscape Pack as the main idea-generation substrate.

### Phase 2: Idea Generation (brainstorm with external LLM)

Use the external LLM via Codex MCP for divergent thinking:

```
spawn_agent:
  reasoning_effort: xhigh
  model: REVIEWER_MODEL
  message: |
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
    [paste Topic Scope, Bottleneck Evidence, Simulator / Prototype Readiness, and Gap Seeds]

    Evaluation canon extracted from the literature:
    [paste evaluation_platforms, benchmarks_workloads, baselines, metrics, validation_style, and known_limitations]

    Generate 8-12 concrete research ideas. For each idea:
    1. One-sentence summary
    2. Core hypothesis (what you expect to find and why)
    3. ai_infra_layer: one of compute/accelerator, memory/storage/data movement, interconnect/network, storage/checkpointing/data pipeline, runtime/system, or multi-layer
    4. hardware_bottleneck: the concrete resource pressure or timing path
    5. evaluation_canon_fit: which platform, benchmark/workload, baseline, and metric from the canon would validate it
    6. Minimum viable experiment (cheapest credible validation path for this topic)
    7. Expected contribution type: hardware mechanism / microarchitecture / memory hierarchy / storage datapath / diagnostic / hardware-aware runtime / system design
    8. validation_backend and readiness_risk: ready / partial / future, with the blocker if not runnable now
    9. scientific_taste: why the result would be non-obvious and worth a reviewer caring about
    10. Risk level: LOW / MEDIUM / HIGH
    11. Estimated effort: hours / days / weeks / platform bring-up
    12. Key metric that would constitute a win, chosen from the topic's evaluation canon when possible

    Prioritize ideas that are:
    - Grounded in the topic's literature-derived evaluation canon
    - Diverse across AI infrastructure layers and research shapes, without requiring cross-layer mechanisms
    - Not "integrate X with Y" unless the integration reveals surprising performance/design insights
    - Differentiated from the 10-15 papers above
    - Targeting MICRO/ISCA/HPCA/ASPLOS/NSDI/SIGCOMM/OSDI/USENIX ATC/EuroSys/FCCM/DAC bar

    Be creative but grounded. A great architecture idea is one whose answer — positive or negative — changes how people design AI infrastructure hardware or hardware/software boundaries.
```

Save the threadId for follow-up.

### Phase 3: First-Pass Filtering

For each generated idea, quickly evaluate:

1. **Hard gates**:
   - LLM infrastructure problem: reject pure ML method ideas and unrelated architecture ideas.
   - Hardware bottleneck claim: reject pure software scheduling unless it names a resource bottleneck and hardware-facing metric.
   - Minimal validation path: reject ideas with no analytical, simulation, trace, RTL/HLS, prototype, or existing benchmark route.

2. **Evaluation canon and readiness check**:
   - Classify `ai_infra_layer` only for organization.
   - Assign `evaluation_canon_fit`: platform, benchmark/workload, baseline, metrics, and validation style from the current topic's literature.
   - Assign `validation_backend`: analytical model, simulator, trace replay, public benchmark, microbenchmark, RTL/HLS sketch, prototype, or future platform.
   - Mark `readiness_risk` as `ready`, `partial`, or `future`; do not eliminate solely because an idea is not runnable now.
   - For runtime/system ideas, keep only those tied to a measurable hardware or system bottleneck such as HBM capacity, PCIe/network traffic, accelerator utilization, memory-copy pressure, storage I/O, or tail latency.

3. **Workload availability**:
   - Prefer public traces, synthetic LLM serving/training traffic, topic-standard benchmarks, microbenchmarks, or simulator-generated workloads when they match the evaluation canon.
   - Mark ideas that require proprietary traces with no synthetic substitute as `readiness_risk: future` or `evaluation_canon_fit: weak`, rather than killing them by default.

4. **Novelty quick-check**: For each idea, do 2-3 targeted searches to see if it's already been done. Full `/novelty-check` comes later for survivors.

5. **Scientific taste and impact estimation**: Would a reviewer care about the result?
   - Non-obvious bottleneck: does the idea expose a resource pressure or timing path people are likely underestimating?
   - Mechanism insight: does it teach something deeper than "apply X to Y"?
   - Design judgment: would a positive or negative result change how people build AI infrastructure?
   - Evaluation credibility: does the proposed platform/benchmark/metric match what strong papers in this topic use?
   - "So what?" test: if the experiment succeeds, does it change how people design AI infrastructure hardware or hardware/software boundaries?
   - Is the finding actionable or just interesting?

Apply the `scientific-taste` ranking profile after the hard gates: scientific taste 30%, evaluation canon fit 25%, novelty 20%, validation feasibility 15%, LLM bottleneck importance 10%. Typically 8-12 ideas reduce to 4-6.

### Phase 4: Deep Validation (for top ideas)

For each surviving idea, run a deeper evaluation:

1. **Novelty check**: Use the `/novelty-check` workflow (multi-source search + GPT-5.5 cross-verification) for each idea

2. **Critical review**: Use GPT-5.5 via `send_input` (same thread):
   ```
   Here are our top ideas after filtering:
   [paste surviving ideas with novelty check results, ai_infra_layer, hardware_bottleneck, evaluation_canon_fit, validation_backend, readiness_risk, scientific_taste, and pilot status]

   For each, play devil's advocate:
   - What's the strongest objection a MICRO/ISCA/HPCA/ASPLOS/NSDI reviewer would raise?
   - What's the most likely failure mode (e.g., bottleneck too small, simulator abstraction too weak, area/power overhead dominates, workload not representative)?
   - Is the scientific taste strong, or is this just an engineering integration?
   - Does the proposed platform/benchmark/baseline/metric match the topic's literature?
   - Is the novelty credible after considering the closest papers?
   - Which ideas have a positive-or-negative answer that would change design judgment?
   - How would you rank these for a top venue submission?
   - Which 2-3 would you actually pilot first, and which additional ideas deserve a designed_not_run pilot plan?

   For runtime/system ideas:
   - Is the hardware bottleneck real and central, or is this a pure software scheduler?
   ```

3. **Combine rankings**: Merge your assessment with GPT-5.5's ranking. Select top 4-6 ideas for lightweight pilot plans and top 2-3 ideas for pilots to run immediately when ready.

### Phase 5: Pilot Validation (plans for top 4-6, runs for top 2-3)

Before committing to a full research effort, run or design cheap pilots to get early signal. For AI infrastructure architecture research, pilots are **analytical models, small simulator runs, trace replays, micro-benchmarks, or RTL/HLS sketches**. They are not full paper experiments.

1. **Design pilots**: For each of the top 4-6 ideas, record `ai_infra_layer`, `hardware_bottleneck`, `evaluation_canon_fit`, and validation backend first. The pilot just needs to answer: **does the mechanism give meaningful signal before full implementation investment?**

   | Layer / backend | Pilot approach | What to run | Success signal |
   |-----------------|---------------|-------------|---------------|
   | Any / analytical model | Queue, bandwidth, latency, or resource model | First-order script with published baselines and sensitivity sweep | Model shows a decisive bottleneck and plausible gain |
   | compute/accelerator | Kernel or pipeline model | Small simulator run, HLS/RTL sketch, or accelerator utilization trace | Utilization/latency/TOPS/W improves enough to justify mechanism |
   | memory/storage/data movement | gem5 or trace replay | KV/cache/CXL/HBM traffic model, bandwidth amplification, prefetch or placement sensitivity | Tail latency, bandwidth, miss rate, or capacity pressure changes materially |
   | interconnect/network | network simulation, trace replay, or microbench | Small flow/job smoke test, window summaries, congestion or tail-latency sensitivity when relevant | goodput, FCT, retransmitted bytes, queueing, utilization, or tail latency changes in expected direction |
   | memory/storage/data movement | trace replay or storage microbench | checkpoint burst, compression, object-store, or SSD bandwidth replay | checkpoint/recovery time or I/O amplification improves |
   | runtime/system | hardware-aware trace analysis | batching/admission/KV placement trace with hardware resource accounting | tail latency or throughput improves because a named hardware bottleneck is controlled |
   | RTL/HLS/prototype | microarchitecture sketch | Minimal datapath or existing IP configuration, no full platform build required | throughput feasibility, area/power estimate, or platform blocker identified |

   - Default budget: `pilot_budget: <=2h mini-run`.
   - If the backend is unavailable, set `pilot_status: designed_not_run`, write `pilot_command_or_plan`, and record `readiness_blocker`.
   - Clear success metric defined upfront per row above.

2. **Run pilots when ready**: Run at most `MAX_PILOT_IDEAS` pilots immediately. Use Bash to run analytical scripts, trace replays, small simulator invocations, or existing micro-benchmarks. Do not perform platform bring-up inside Workflow 1.

3. **Collect results**: Once pilots complete, compare:
   - Which ideas showed positive signal (model predicts improvement)?
   - Which showed null/negative signal? (eliminate or deprioritize)
   - Any surprising findings that suggest a pivot?

4. **Re-rank based on pilot evidence**: An idea with strong analytical/simulation signal jumps ahead of a theoretically appealing but unvalidated idea, unless novelty or scientific taste is below the minimum bar. Do not eliminate a strong idea solely because the pilot was only designed and not run.

Note: Skip this phase if no simulation environment or hardware is available. Flag skipped ideas as "needs pilot validation" in the report.

### Phase 6: Output — Ranked Idea Report

Write a structured report to `idea-stage/IDEA_REPORT.md`:

```markdown
# Research Idea Report

**Direction**: [user's research direction]
**Generated**: [UTC ISO-8601 timestamp ending in Z, e.g. 2026-04-26T02:26:45Z]
**Ideas evaluated**: X generated → Y survived filtering → Z piloted → W recommended

## Landscape Summary
[3-5 paragraphs on the current state of the field]

## Recommended Ideas (ranked)

### Idea 1: [title]
- **Hypothesis**: [one sentence]
- **ai_infra_layer**: compute/accelerator | memory/storage/data movement | interconnect/network | storage/checkpointing/data pipeline | runtime/system | multi-layer
- **hardware_bottleneck**: [concrete resource pressure or timing path]
- **evaluation_canon**: platforms=[...]; benchmarks_workloads=[...]; baselines=[...]; metrics=[...]; validation_style=[...]
- **evaluation_canon_fit**: strong | acceptable | weak — [why the proposed evaluation matches or diverges from the topic's literature]
- **validation_backend**: analytical_model | simulator | trace_replay | public_benchmark | microbenchmark | RTL/HLS | prototype | future_platform
- **readiness_risk**: ready | partial | future — [blocker if any]
- **Minimum experiment**: [concrete description]
- **Expected outcome**: [what success/failure looks like]
- **Novelty**: X/10 — closest work: [paper]
- **Feasibility**: [simulator/prototype readiness, data/trace availability, implementation estimates]
- **Scientific taste**: [why this is non-obvious, mechanism-rich, and useful even if the result is negative]
- **Risk**: LOW/MEDIUM/HIGH
- **Contribution type**: hardware mechanism / microarchitecture / memory hierarchy / protocol co-design / diagnostic / hardware-aware runtime
- **pilot_status**: runnable_now | completed | designed_not_run | skipped | killed
- **pilot_budget**: <=2h mini-run by default
- **pilot_command_or_plan**: [command if run; otherwise concrete plan]
- **key_metric**: [decisive metric]
- **signal**: POSITIVE / WEAK_POSITIVE / NEGATIVE / INCONCLUSIVE / NOT_RUN
- **readiness_blocker**: [none, missing simulator adapter, platform bring-up, traces unavailable, etc.]
- **Reviewer's likely objection**: [strongest counterargument]
- **Why we should do this**: [1-2 sentences]

### Idea 2: [title]
...

## Eliminated Ideas (for reference)
| Idea | Category | Reason | Revisit condition |
|------|----------|--------|-------------------|
| ... | already_done | Closest paper already covers the core mechanism/result | Revisit only if new workload/platform changes the conclusion |
| ... | scientifically_weak | Result would not change design judgment either way | Revisit if a sharper bottleneck hypothesis appears |
| ... | weak_evaluation_canon | No credible platform/benchmark/baseline/metric path found in the topic literature | Revisit after better traces, benchmarks, or methodology are available |
| ... | missing_hardware_bottleneck | Pure software or ML idea without a hardware/system resource claim | Revisit if tied to a concrete bottleneck |
| ... | not_currently_runnable | Scientifically interesting but blocked by platform, traces, or setup | Keep as designed_not_run backup, not a scientific rejection |

## Pilot Validation Results
| Idea | ai_infra_layer | evaluation_canon_fit | validation_backend | readiness_risk | pilot_status | pilot_budget | pilot_command_or_plan | key_metric | signal | readiness_blocker |
|------|----------------|----------------------|--------------------|----------------|--------------|--------------|-----------------------|------------|--------|-------------------|
| Idea 1 | memory/storage/data movement | strong | trace_replay | ready | completed | <=2h mini-run | `python3 run_kv_cache_trace_smoke.py --sweep cxl_bw` | p99 latency, bandwidth utilization | POSITIVE | none |
| Idea 2 | interconnect/network | acceptable | simulator | partial | designed_not_run | <=2h mini-run | small network simulation with topic-standard workload and baseline | FCT, utilization, tail latency | NOT_RUN | missing adapter |
| Idea 3 | runtime/system | weak | trace_replay | future | skipped | <=2h mini-run | N/A | N/A | INCONCLUSIVE | no credible benchmark/baseline yet |

## Suggested Execution Order
1. Start with Idea 1 (positive pilot signal, strong evaluation canon fit, credible novelty)
2. Keep Idea 2 as backup (good scientific taste, partial readiness)
3. Archive Idea 3 unless a stronger benchmark/baseline path appears

## Next Steps
- [ ] Move the selected idea to `/research-refine-pipeline`
- [ ] Let Workflow 1.5 expand the pilot into a full experiment plan and execution log
- [ ] If confirmed, invoke /auto-review-loop for full iteration
```

## Phase 7: Write Ideas to Research Wiki (if active)

**Skip this phase entirely if `research-wiki/` does not exist.**

This is critical for spiral learning — without it, `ideas/` stays empty and re-ideation has no memory.

```
if research-wiki/ exists:
    for each idea in recommended_ideas + eliminated_ideas:
        1. Create page: research-wiki/ideas/<idea_id>.md
           - node_id: idea:<id>
           - stage: proposed (or: piloted, archived)
           - outcome: unknown (or: negative, mixed, positive)
           - based_on: [paper:<slug>, ...]
           - target_gaps: [gap:<id>, ...]
           - Include: hypothesis, proposed method, expected outcome
           - If pilot was run: actual outcome, failure notes, reusable components

        2. Add edges:
           python3 tools/research_wiki.py add_edge research-wiki/ --from "idea:<id>" --to "paper:<slug>" --type inspired_by --evidence "..."
           python3 tools/research_wiki.py add_edge research-wiki/ --from "idea:<id>" --to "gap:<id>" --type addresses_gap --evidence "..."

    Rebuild query pack:
        python3 tools/research_wiki.py rebuild_query_pack research-wiki/
    Log:
        python3 tools/research_wiki.py log research-wiki/ "idea-creator wrote N ideas (M recommended, K eliminated)"
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
- Always estimate implementation and validation cost. An idea that needs a new simulator, a private trace corpus, or a long platform bring-up gets `readiness_risk: future`; that is not the same as scientific rejection.
- "Apply X to Y" is the lowest form of research idea. Push for deeper questions.
- Include eliminated ideas in the report — they save future time by documenting dead ends.
- **If the user's direction is too broad (e.g., "AI infrastructure" with no bottleneck, workload, or layer), STOP and ask them to narrow it.** A good direction is 1-2 sentences specifying the LLM infrastructure problem, hardware/system bottleneck, and validation constraint — e.g., "KV cache placement under CXL memory bandwidth limits" or "LLM checkpoint recovery under storage bandwidth and metadata pressure".

## Composing with Other Skills

After this skill produces the ranked report:
```
/idea-creator "direction"     → ranked ideas
/novelty-check "top idea"     → deep novelty verification (already done in Phase 4, but user can re-run)
/research-review "top idea"   → external critical feedback
implement                     → write code
/run-experiment               → execute simulator, microbenchmark, or other experiment command
/auto-review-loop             → iterate until submission-ready
```

## Review Tracing

After each `spawn_agent` or `send_input` reviewer call, save the trace following `shared-references/review-tracing.md`. Use `tools/save_trace.sh` or write files directly to `.aris/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
