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

For this repository, the default domain is **AI infrastructure for LLM** with a computer architecture / systems bias. Network/RDMA/NIC/DPU ideas are first-class, but they are one layer of the stack rather than the only valid target. Runtime/serving ideas are allowed only when they expose, control, or exploit a concrete hardware bottleneck.

## Constants

- **MAX_PILOT_IDEAS = 3** — Pilot at most 3 ideas. Additional ideas are validated analytically only.
- **PILOT_MAX_HOURS = 2** — Keep each lightweight architecture pilot within two wall-clock hours. If a pilot needs platform bring-up, record `pilot_status: designed_not_run` and the blocker instead of stalling Workflow 1.
- **REVIEWER_MODEL = `gpt-5.5`** — Model used via Codex MCP for brainstorming and review. Must be an OpenAI model (e.g., `gpt-5.5`, `o3`, `gpt-4o`).
- **REVIEWER_BACKEND = `codex`** — Default: Codex MCP (xhigh). Override with `— reviewer: oracle-pro` for GPT-5.5 Pro via Oracle MCP. See `shared-references/reviewer-routing.md`.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.
- **RANKING_PROFILE = `fast-iteration`** — Apply hard gates first, then rank by simulation readiness, implementation risk, LLM bottleneck importance, hardware insight, and novelty.

> 💡 **Domain context**: This skill is configured for **AI infrastructure for LLM** research across compute/accelerator, memory/storage/data movement, interconnect/network, and runtime/system. Hardware bottlenecks and simulator/prototype readiness are mandatory; pure ML algorithm ideas and pure software schedulers without a hardware bottleneck are out of scope.

> Override via argument, e.g., `/idea-creator "topic" — pilot: analytical only`.

## AI Infrastructure Layer Taxonomy

Classify every idea before ranking it:

| Layer | Examples | Typical validation backends | Key metrics |
|-------|----------|-----------------------------|-------------|
| `compute/accelerator` | attention/KV kernels, sparsity datapaths, inference accelerators, near-data compute | analytical model, gem5, GPGPU-Sim/Accel-Sim, RTL/HLS | TOPS/W, utilization, latency, SRAM pressure, area/power |
| `memory/storage/data movement` | KV cache hierarchy, CXL memory, HBM pressure, compression, prefetch | analytical model, gem5, trace replay, microbench | GB/s, tail latency, cache miss rate, write amplification |
| `interconnect/network` | RDMA, NIC/DPU compression, collectives, congestion, packet/flow scheduling | htsim, gem5+htsim, ns-3, DPU/FPGA microbench | goodput, FCT, retransmitted bytes, PCIe utilization, Rx pressure |
| `memory/storage/data movement` | checkpoint bursts, object store, SSD pipeline, data loading | analytical model, trace replay, storage microbench | checkpoint time, recovery time, IOPS, bandwidth, endurance |
| `runtime/system` | batching, admission, prefill/decode split, KV placement | only when tied to hardware model; analytical/gem5/trace replay | HBM capacity, accelerator utilization, PCIe/NIC traffic, tail latency |

Hard gates:
1. The problem must be an LLM infrastructure problem.
2. The idea must name a concrete hardware bottleneck.
3. The idea must have a minimum validation path: analytical model, gem5, htsim, gem5+htsim, trace replay, RTL/HLS, FPGA/DPU microbenchmark, or a clearly available existing backend.

Default weighted score after hard gates:
- Simulation readiness: 40%
- Implementation risk / iteration speed: 20%
- LLM bottleneck importance: 15%
- Hardware insight: 15% (minimum 2/5)
- Novelty: 10% (minimum 2/5)

Backend readiness tiers:
- **Ready**: analytical model, gem5, Broadcom/csg-htsim, `cosim_gem5_htsim`, trace replay using existing logs.
- **Partial**: GPGPU-Sim/Accel-Sim, SimAI, RTL/HLS, FPGA/DPU microbench when setup already exists.
- **Future**: new hardware platform bring-up, large real cluster, proprietary traces.

## Architecture Contribution Scope Level

Use this 4-level scale to classify how deep the architecture contribution is. For RDMA/NIC compression ideas, the examples below map directly to the network stack. For other AI infrastructure layers, reinterpret the levels as block, subsystem, protocol/control interaction, and application/system behavior.

| Level | Contribution scope | What the paper claims | Required testbed | Baseline |
|-------|-------------------|-----------------------|-----------------|---------|
| **L1** | **Compression engine** | Throughput / latency / compression ratio of the hardware compression block itself, independent of RDMA semantics | Single FPGA board (Corundum or custom RTL); standard benchmarks/real-world workloads (network traffic, video streaming, LLM training and inference) | LZ4 hardware, BlueField C-engine, CAST IP core |
| **L2** | **NIC pipeline integration** | How the compression engine fits into the NIC Tx/Rx pipeline: DMA descriptor changes, scatter-gather, zero-copy path, end-to-end single-node RDMA throughput/latency | 1–2 FPGA NICs (Corundum) + loopback or direct-connect RoCE | Uncompressed RDMA baseline on same hardware |
| **L3** | **RDMA protocol interaction** | How compression changes RoCE semantics: variable-size payloads vs fixed MTU, credit/flow-control accounting, retransmission of compressed frames, ATOMIC/SEND operation constraints | **2+ FPGA NICs + real switch** with RoCE traffic (the primary real-hardware testbed) | Standard RoCE on same FPGA NIC without compression |
| **L4** | **Network / application level** | Collective communication (AllReduce), congestion behavior under variable compression ratio (PFC/ECN interaction), end-to-end distributed workload speedup | **Multi-node FPGA NIC cluster + switch** for real-hardware validation; ns-3 RDMA simulation for scale-out sensitivity study | Commercial RDMA NICs (BlueField-2/3, CX7) or published NetZIP numbers |

**Key rules**:
- The baseline is always **real RDMA** at the appropriate level — never use Soft-RoCE as a substitute for RDMA comparison.
- ns-3 RDMA simulation is a **supplement** for scale-out analysis (e.g., 100-node sensitivity), not a replacement for the real multi-FPGA + switch testbed.
- An L4 paper still needs real L3 measurement data — you can't claim collective communication gains without showing the underlying per-NIC RDMA behavior.
- An L1/L2 paper is publishable standalone (e.g., FCCM, DAC) if the hardware contribution is strong. L3/L4 papers target MICRO/ISCA/NSDI/SIGCOMM.

## RDMA Plane Interaction (Second Dimension)

This is **orthogonal** to Contribution Scope Level. It asks: does this idea require modifying the RDMA **data plane**, **control plane**, or both?

Use this to assess novelty potential — **not** feasibility. An idea that necessarily requires co-innovating both planes is harder to implement and has no prior art by definition, which is exactly why it may be the most valuable.

### RDMA Plane Definitions

**Data plane** (fast path, per-packet, line-rate):
- Payload processing: compression/decompression of packet content
- MTU segmentation: compressed payload has variable size — breaks fixed-MTU assumption
- Scatter-gather list: original sg-list sizes ≠ compressed output sizes
- Checksum placement: must decide whether checksum covers pre- or post-compression data
- ATOMIC / RDMA READ semantics: these operations cannot be transparently compressed (byte-addressable)
- Inline data path: SEND/WRITE operations with inline payload compression
- **Rx-side decompression bandwidth amplification** (a structurally distinct sub-problem):
  - Wire bandwidth ≠ memory-side bandwidth after decompression. A 400Gbps NIC receiving flows with average 2× compression ratio must write 800Gbps of decompressed data to host memory — which may exceed PCIe 5.0 x16 bandwidth (~512Gbps bidirectional) or DRAM write bandwidth.
  - Multi-flow concurrency: many parallel flows arrive simultaneously, each with a **different and unpredictable compression ratio** (incompressible binary data ≈ 1.0×; text/log/gradient data ≈ 2–5×). The aggregate decompression output rate fluctuates at sub-microsecond timescales.
  - Decompression engine resource allocation: how many parallel decompression engines to provision? How to assign flows to engines when per-flow output rate is variable?
  - Output buffer pressure: when the sum of all decompressed streams transiently exceeds PCIe/memory throughput, where does the overflow go? In-NIC SRAM buffer? Drop? Back-pressure to Rx queues?
  - Back-pressure propagation path: if the NIC stalls decompression to protect host memory, the upstream sender is not notified — creating a hidden latency bubble invisible to DCQCN/ECN. This is a D+C boundary: the Rx data plane stall needs a control-plane signal to prevent sender-side credit build-up.
  - Note: this problem is **asymmetric** — the sender compresses at a predictable rate determined by the algorithm, but the receiver decompresses at a rate determined by the *incoming compressed data*, which it cannot control.

**Control plane** (slow path, per-connection or per-flow):
- Credit-based flow control: IB credits and PFC assume fixed payload sizes; variable compression ratio breaks credit accounting
- Connection MTU negotiation: QP creation path MTU must be re-thought when compression is active
- Congestion control (DCQCN/ECN): ECN marking thresholds and CWND adaptation assume uniform payload sizes; compression changes effective byte load per packet
- Retransmission semantics: should the NIC retransmit the compressed frame or recompress the original data?
- load-balancing mechanism (multi-path): if some flows compress better than others, how does that affect path selection(sPort) of the flow?
- QoS / priority scheduling: compressed flows have different BW profile than raw flows

### Classification

| Tag | Meaning | Novelty signal | Typical venue |
|-----|---------|---------------|--------------|
| **D** | Data plane only | Clean hardware contribution; prior art exists for pure data-path compression | FCCM / DAC / MICRO |
| **C** | Control plane only | Unusual angle; often a systems paper rather than architecture | NSDI / SIGCOMM / OSDI |
| **D+C** | Both planes, necessarily co-innovated | **Highest novelty signal**: the interaction between variable-size compressed payloads and RDMA's flow/congestion control is an open problem. Complex, nobody has done it end-to-end. | MICRO / ISCA / NSDI |
| **N** | Neither (RDMA-agnostic) | Pure algorithm or compression engine paper; RDMA is just the deployment context | FCCM / DAC / arXiv |

### Co-innovation Test

Ask for each idea **two questions**:

**Tx-side test**: *"If I add compression to the data path, does the RDMA control plane break or degrade — and does fixing that require a new mechanism?"*

**Rx-side test**: *"Under peak wire load with variable per-flow compression ratios, can the Rx NIC sustain full decompression throughput without exceeding host memory bandwidth — and if not, does handling the overflow require a new mechanism (buffer management, back-pressure signaling, flow scheduling)?"*

- If YES → the idea is **D+C**. The complexity is the contribution. Do not simplify away the control-plane interaction to make implementation easier — that would kill the novelty.
- If NO → the idea is **D** or **N**. Cleaner to implement, narrower claim.

D+C ideas should **not** be penalized for complexity in the feasibility filter. Flag them as high-effort but **high-value**, and plan for a staged implementation: prototype the D component first, then tackle C.

**Platform inventory** (what's available to build each level):

| Platform | Covers | Key strength for compression research | Notes |
|----------|--------|--------------------------------------|-------|
| [Corundum](https://github.com/corundum/corundum) | L1/L2: open FPGA NIC with full Tx/Rx pipeline | Best for inserting a compression block into the data path; clean AXI-Stream pipeline interfaces | Needs Xilinx UltraScale+ FPGA; no native RDMA transport (add RoCE on top) |
| [fpga-network-stack / BALBOA](https://github.com/fpgasystems/fpga-network-stack) | L2/L3: HLS-based RoCEv2 stack (WRITE/READ/SEND), fully interoperable with commercial NICs | RoCEv2 transport is exposed as modifiable HLS modules — can change flow-control, retransmission, and credit logic directly; configurable QP count (`FNS_ROCE_STACK_MAX_QPS`); runs at 100Gbps | Targets Xilinx VC709 / VCU118 / Alpha Data ADM-PCIE-7V3; surrounding DMA/memory infrastructure must be added by user |
| [Jingzhao (ETH-PLUS)](https://github.com/ETH-PLUS/Jingzhao) | L2/L3: first open-source RDMA NIC **fully compatible with standard OFED** (rdma-core / ibverbs) | Directly usable with unmodified RDMA applications; taped-out in TSMC 28nm (validates RTL for ASIC path); modular NIC prototyping framework for rapid integration of new network functions | [Paper: arXiv 2410.08476](https://arxiv.org/abs/2410.08476); OFED compatibility means existing RDMA benchmarks (ib_send_bw, perftest) run without modification |
| FPGA NICs + ToR switch | L3: 2-node RoCE experiments | Primary testbed for protocol interaction claims with real switch PFC/ECN | Use fpga-network-stack or Jingzhao as the NIC |
| Multi-FPGA cluster + switch | L4: end-to-end distributed workload | Final validation for application-level claims | Combine any above NIC platform at scale |
| [ns-3 + RDMA module](https://github.com/alibaba/High-Performance-RDMA-in-ns-3) | L4 supplement: scale-out PFC/ECN/DCQCN sensitivity | Explore 100-node configurations impossible on physical testbed | Use only to complement, not replace, real-hardware L3/L4 numbers |
| [RDMA-core](https://github.com/linux-rdma/rdma-core) | L2/L3: host-side driver and verbs | Needed for descriptor/WQE/CQE format changes on the host side | Always available; works with Jingzhao (OFED-compatible) |

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

**If found**: Extract all five sections:
- **Section 1** (paper table) → known-papers set for deduplication
- **Section 2** (landscape map) → sub-direction clusters, what's been tried
- **Section 3** (structural gaps) → the 5-lens gap analysis — **this is the primary input for Phase 2 brainstorming**
- **Section 4** (competitive landscape) → top competing papers and positioning
- **Section 5** (Landscape Pack) → topic scope, bottleneck evidence, simulator/prototype readiness, and `Gap Seeds`

Announce: _"Loaded research-lit from `idea-stage/LITERATURE_REVIEW.md`: {N} papers, {M} structural gaps, {K} Gap Seeds identified."_

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
    Domain context: AI infrastructure for LLM. Valid layers are compute/accelerator, memory/storage/data movement, interconnect/network, and runtime/system. Runtime/serving ideas are only valid if they expose or control a concrete hardware bottleneck.

    Here is the current landscape (from /research-lit Section 2):
    [paste landscape map — sub-direction clusters]

    Structural gaps identified (from /research-lit Section 3):
    [paste the 5-lens gap analysis: cross-domain / contradictions / untested assumptions / unexplored regimes / unasked questions]

    Top competing papers (from /research-lit Section 4):
    [paste competitive landscape — top 3 papers and what they leave open]

    Landscape Pack (from /research-lit Section 5):
    [paste Topic Scope, Bottleneck Evidence, Simulator / Prototype Readiness, and Gap Seeds]

    Generate 8-12 concrete research ideas. For each idea:
    1. One-sentence summary
    2. Core hypothesis (what you expect to find and why)
    3. ai_infra_layer: one of compute/accelerator, memory/storage/data movement, interconnect/network, runtime/system, or multi-layer
    4. hardware_bottleneck: the concrete resource pressure or timing path
    5. Minimum viable experiment (cheapest validation: analytical model / gem5 / htsim / gem5+htsim / trace replay / RTL simulation / FPGA or DPU micro-benchmark)
    6. Expected contribution type: hardware mechanism / microarchitecture / memory hierarchy / NIC or DPU pipeline integration / protocol co-design / storage datapath / hardware-aware runtime
    7. validation_backend and readiness tier: ready / partial / future
    8. Risk level: LOW / MEDIUM / HIGH
    9. Estimated effort: hours / days / weeks / platform bring-up
    10. Key metric that would constitute a win (throughput Gbps, latency ns/us, compression ratio, goodput, retransmitted bytes, host_memory_write_gbps, PCIe utilization, area/power)

    Prioritize ideas that are:
    - Validatable with an analytical model, gem5, Broadcom/csg-htsim, cosim_gem5_htsim, trace replay, RTL simulation, or a small micro-benchmark on available hardware
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
   - Minimal validation path: reject ideas with no analytical, simulation, trace, RTL/HLS, FPGA, DPU, or existing benchmark route.

2. **Fast-iteration feasibility check**:
   - Classify `ai_infra_layer` and contribution scope.
   - Assign `validation_backend`: analytical model, gem5, Broadcom/csg-htsim, cosim_gem5_htsim, trace replay, RTL/HLS, FPGA/DPU microbench, or future platform bring-up.
   - Mark readiness as `ready`, `partial`, or `future`.
   - For RDMA/NIC ideas, keep the real-RDMA baseline rule: do not substitute Soft-RoCE for claims about real RDMA behavior.
   - For runtime/system ideas, keep only those tied to a measurable hardware bottleneck such as HBM capacity, PCIe/NIC traffic, accelerator utilization, or host memory copy pressure.

3. **Workload availability**:
   - Prefer public traces, synthetic LLM serving/training traffic, standard compression corpora, microbenchmarks, or simulator-generated workloads.
   - Skip or downgrade ideas that require proprietary traces with no synthetic substitute.

4. **Novelty quick-check**: For each idea, do 2-3 targeted searches to see if it's already been done. Full `/novelty-check` comes later for survivors.

5. **Impact estimation**: Would a reviewer care about the result?
   - "So what?" test: if the experiment succeeds, does it change how people design AI infrastructure hardware or hardware/software boundaries?
   - Is the finding actionable or just interesting?
   - For RDMA/NIC compression, preserve D+C co-innovation as a high-novelty signal when variable compressed bytes force a protocol/control-plane response.

Apply the `fast-iteration` ranking profile after the gates: simulation readiness 40%, implementation risk / iteration speed 20%, LLM bottleneck importance 15%, hardware insight 15%, novelty 10%. Typically 8-12 ideas reduce to 4-6.

### Phase 4: Deep Validation (for top ideas)

For each surviving idea, run a deeper evaluation:

1. **Novelty check**: Use the `/novelty-check` workflow (multi-source search + GPT-5.5 cross-verification) for each idea

2. **Critical review**: Use GPT-5.5 via `send_input` (same thread):
   ```
   Here are our top ideas after filtering:
   [paste surviving ideas with novelty check results, ai_infra_layer, hardware_bottleneck, validation_backend, and pilot status]

   For each, play devil's advocate:
   - What's the strongest objection a MICRO/ISCA/HPCA/ASPLOS/NSDI reviewer would raise?
   - What's the most likely failure mode (e.g., bottleneck too small, simulator abstraction too weak, area/power overhead dominates, workload not representative)?
   - How would you rank these for a top venue submission?
   - Which 2-3 would you actually work on?

   For runtime/system ideas:
   - Is the hardware bottleneck real and central, or is this a pure software scheduler?

   For RDMA/NIC compression ideas:
   - Is the data/control-plane interaction genuinely necessary?
   - Does Rx decompression expansion pressure create PCIe, host-memory, Rx buffer, stall, drop, or retransmission effects that the proposal must preserve?
   ```

3. **Combine rankings**: Merge your assessment with GPT-5.5's ranking. Select top 2-3 ideas for pilot experiments.

### Phase 5: Pilot Validation (for top 2-3 ideas)

Before committing to a full research effort, run or design cheap pilots to get early signal. For AI infrastructure architecture research, pilots are **analytical models, small simulator runs, trace replays, micro-benchmarks, or RTL/HLS sketches**. They are not full paper experiments.

1. **Design pilots**: For each top idea, classify `ai_infra_layer`, `hardware_bottleneck`, and validation backend first. The pilot just needs to answer: **does the mechanism give meaningful signal before full implementation investment?**

   | Layer / backend | Pilot approach | What to run | Success signal |
   |-----------------|---------------|-------------|---------------|
   | Any / analytical model | Queue, bandwidth, latency, or resource model | First-order script with published baselines and sensitivity sweep | Model shows a decisive bottleneck and plausible gain |
   | compute/accelerator | Kernel or pipeline model | Small simulator run, HLS/RTL sketch, or accelerator utilization trace | Utilization/latency/TOPS/W improves enough to justify mechanism |
   | memory/storage/data movement | gem5 or trace replay | KV/cache/CXL/HBM traffic model, bandwidth amplification, prefetch or placement sensitivity | Tail latency, bandwidth, miss rate, or capacity pressure changes materially |
   | interconnect/network | htsim or gem5+htsim | 100-1000 flow smoke, 100us window summaries, lossy RDMA/RTO sensitivity if relevant | goodput/FCT/retransmitted bytes/Rx pressure changes in expected direction |
   | memory/storage/data movement | trace replay or storage microbench | checkpoint burst, compression, object-store, or SSD bandwidth replay | checkpoint/recovery time or I/O amplification improves |
   | runtime/system | hardware-aware trace analysis | batching/admission/KV placement trace with hardware resource accounting | tail latency or throughput improves because a named hardware bottleneck is controlled |
   | RTL/HLS/FPGA/DPU | microarchitecture sketch | Minimal datapath or existing IP configuration, no full platform build required | line-rate feasibility, area/power estimate, or platform blocker identified |

   - Default budget: `pilot_budget: <=2h mini-run`.
   - If the backend is unavailable, set `pilot_status: designed_not_run`, write `pilot_command_or_plan`, and record `readiness_blocker`.
   - For RDMA/NIC compression, preserve **Rx decompression expansion pressure** in the pilot plan when relevant: model compressed wire bytes separately from decompressed PCIe/host-memory writes, Rx buffer occupancy, drops, stalls, sender-side RTO retransmission, goodput, and tail latency.
   - Clear success metric defined upfront per row above.

2. **Run pilots when ready**: Use Bash to run analytical scripts, trace replays, small simulator invocations, or existing micro-benchmarks. Do not perform platform bring-up inside Workflow 1.

3. **Collect results**: Once pilots complete, compare:
   - Which ideas showed positive signal (model predicts improvement)?
   - Which showed null/negative signal? (eliminate or deprioritize)
   - Any surprising findings that suggest a pivot?

4. **Re-rank based on pilot evidence**: An idea with strong analytical/simulation signal jumps ahead of a theoretically appealing but unvalidated idea, unless novelty or hardware insight is below the minimum bar.

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
- **ai_infra_layer**: compute/accelerator | memory/storage/data movement | interconnect/network | memory/storage/data movement | runtime/system | multi-layer
- **hardware_bottleneck**: [concrete resource pressure or timing path]
- **validation_backend**: analytical_model | gem5 | Broadcom/csg-htsim | cosim_gem5_htsim | trace_replay | RTL/HLS | FPGA/DPU_microbench | future_platform
- **Minimum experiment**: [concrete description]
- **Expected outcome**: [what success/failure looks like]
- **Novelty**: X/10 — closest work: [paper]
- **Feasibility**: [simulator/prototype readiness, data/trace availability, implementation estimates]
- **Risk**: LOW/MEDIUM/HIGH
- **Contribution type**: hardware mechanism / microarchitecture / memory hierarchy / protocol co-design / diagnostic / hardware-aware runtime
- **Contribution scope**: L1 / L2 / L3 / L4 — [block, subsystem, protocol/control interaction, or application/system behavior]
- **RDMA plane interaction**: D / C / D+C / N — [only for RDMA/NIC ideas; otherwise N/A]
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
| Idea | Reason eliminated |
|------|-------------------|
| ... | Already done by [paper] |
| ... | Requires unavailable simulator/platform bring-up |
| ... | Result wouldn't be interesting either way |

## Pilot Validation Results
| Idea | ai_infra_layer | validation_backend | pilot_status | pilot_budget | pilot_command_or_plan | key_metric | signal | readiness_blocker |
|------|----------------|--------------------|--------------|--------------|-----------------------|------------|--------|-------------------|
| Idea 1 | interconnect/network | cosim_gem5_htsim | completed | <=2h mini-run | `python3 run_rx_pressure_smoke.py --flows 100 --window-us 100` | host_memory_write_gbps, retransmitted_bytes | POSITIVE | none |
| Idea 2 | memory/storage/data movement | gem5 | designed_not_run | <=2h mini-run | cache/KV trace replay with CXL bandwidth sweep | tail latency, bandwidth amplification | NOT_RUN | missing trace |
| Idea 3 | runtime/system | trace_replay | killed | <=2h mini-run | N/A | N/A | NEGATIVE | no hardware bottleneck claim |

## Suggested Execution Order
1. Start with Idea 1 (positive pilot signal, lowest risk)
2. Idea 3 as backup (weak signal, may need larger scale to confirm)
3. Idea 2 eliminated by pilot — negative result documented

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
- Always estimate implementation and validation cost. An idea that needs a new simulator, a private trace corpus, or a long platform bring-up is not fast-iteration actionable.
- "Apply X to Y" is the lowest form of research idea. Push for deeper questions.
- Include eliminated ideas in the report — they save future time by documenting dead ends.
- **If the user's direction is too broad (e.g., "AI infrastructure" with no bottleneck, workload, or layer), STOP and ask them to narrow it.** A good direction is 1-2 sentences specifying the LLM infrastructure problem, hardware bottleneck, and validation constraint — e.g., "KV cache placement under CXL memory bandwidth limits" or "Rx decompression expansion pressure for compressed RDMA traffic".

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
