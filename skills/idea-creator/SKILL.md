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

## Constants

- **MAX_PILOT_IDEAS = 3** — Pilot at most 3 ideas. Additional ideas are validated analytically only.
- **REVIEWER_MODEL = `gpt-5.5`** — Model used via Codex MCP for brainstorming and review. Must be an OpenAI model (e.g., `gpt-5.5`, `o3`, `gpt-4o`).
- **REVIEWER_BACKEND = `codex`** — Default: Codex MCP (xhigh). Override with `— reviewer: oracle-pro` for GPT-5.5 Pro via Oracle MCP. See `shared-references/reviewer-routing.md`.
- **OUTPUT_DIR = `idea-stage/`** — All idea-stage outputs go here. Create the directory if it doesn't exist.

> 💡 **Domain context**: This skill is configured for **NIC/DPU-side lossless compression and RDMA systems** research. For this domain, every idea is in principle implementable — the real pilot judgment is (1) how deeply it modifies the NIC pipeline, and (2) whether an open-source platform exists to validate it. See `## NIC Modification Depth` below and `## Research Domain` in CLAUDE.md.

> Override via argument, e.g., `/idea-creator "topic" — pilot: analytical only`.

## Contribution Scope Level

Use this 4-level scale to classify **where in the RDMA system an idea's contribution sits**. This determines the claim scope, the baseline (always real RDMA), and the required testbed scale. All levels are implementable — the question is what testbed you need to make credible claims.

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

Derive the topic slug from `$ARGUMENTS` (lowercase, hyphens). Then:

```
Glob: {project-root}/{topic-slug}/research-lit/*.md
```

**If found**: Read the most recent file. Extract all four sections:
- **Section 1** (paper table) → known-papers set for deduplication
- **Section 2** (landscape map) → sub-direction clusters, what's been tried
- **Section 3** (structural gaps) → the 5-lens gap analysis — **this is the primary input for Phase 2 brainstorming**
- **Section 4** (competitive landscape) → top competing papers and positioning

Announce: _"Loaded research-lit from {date}: {N} papers, {M} structural gaps identified."_

**If not found**: Warn the user:
> ⚠️ No research-lit output found for topic `{topic-slug}`. It is strongly recommended to run `/research-lit "{topic}"` first — it produces the landscape map and structural gaps that drive idea quality. Proceeding with a minimal web-only landscape survey (results will be shallower).

Then run a condensed version: WebSearch across MICRO/ISCA/HPCA/NSDI/SIGCOMM for top 10 papers, build a basic landscape map, and identify gaps as best as possible.

> **All literature search and landscape work (including incremental web search) is done by `/research-lit`.** If the loaded output is stale or incomplete, re-run `/research-lit` first rather than searching here. idea-creator does not search for papers.

### Phase 2: Idea Generation (brainstorm with external LLM)

Use the external LLM via Codex MCP for divergent thinking:

```
mcp__codex__codex:
  model: REVIEWER_MODEL
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    You are a senior computer architecture/networking researcher (MICRO/ISCA/HPCA/SIGCOMM/NSDI level) brainstorming research ideas.

    Research direction: [user's direction]
    Domain context: NIC/DPU-side systems research, RDMA networking, hardware acceleration.

    Here is the current landscape (from /research-lit Section 2):
    [paste landscape map — sub-direction clusters]

    Structural gaps identified (from /research-lit Section 3):
    [paste the 5-lens gap analysis: cross-domain / contradictions / untested assumptions / unexplored regimes / unasked questions]

    Top competing papers (from /research-lit Section 4):
    [paste competitive landscape — top 3 papers and what they leave open]

    Generate 8-12 concrete research ideas. For each idea:
    1. One-sentence summary
    2. Core hypothesis (what you expect to find and why)
    3. Minimum viable experiment (cheapest validation: analytical model / RTL simulation / FPGA micro-benchmark / 2-node RoCE testbed / multi-node cluster)
    4. Expected contribution type: hardware mechanism / NIC pipeline integration / RDMA protocol co-design / network/application-level system
    5. RDMA plane interaction — classify as one of:
       - D (data plane only): compression in the packet fast path, no protocol change needed
       - C (control plane only): protocol/flow-control change, no compression engine needed
       - D+C (both, necessarily co-innovated): adding compression to the data path FORCES a new mechanism in the control plane (credit accounting, congestion control, retransmission semantics) — flag these explicitly as high-novelty
       - N (RDMA-agnostic): compression improvement that doesn't depend on RDMA semantics
    6. Risk level: LOW / MEDIUM / HIGH
    7. Estimated effort: days / weeks / months
    8. Key metric that would constitute a win (throughput Gbps, latency ns, compression ratio, credit utilization, PFC pause rate)

    Prioritize ideas that are:
    - Validatable with an analytical model, RTL simulation, gem5 simulation, or micro-benchmark on available hardware (BlueField-2/3, 4/8 FPGA boards)
    - Not "integrate X with Y" unless the integration reveals surprising performance/design insights
    - Differentiated from the 10-15 papers above
    - Targeting MICRO/ISCA/HPCA/ASPLOS/NSDI/SIGCOMM/OSDI/USENIX ATC/EuroSys/FCCM/DAC bar

    Be creative but grounded. A great architecture idea is one whose answer — positive or negative — changes how people design NIC/DPU hardware.
```

Save the threadId for follow-up.

### Phase 3: First-Pass Filtering

For each generated idea, quickly evaluate:

1. **Feasibility check**: Two questions, not one "how long does it take?":

   **Q1 — Contribution scope level** (classify using L1–L4 in `## Contribution Scope Level`):
   - L1/L2: single FPGA board or 2-node loopback → HIGH feasibility, publishable at FCCM/DAC/MICRO
   - L3: 2-node FPGA NIC + switch testbed → MEDIUM feasibility, core claim requires real RoCE traffic
   - L4: multi-node cluster + switch → LOW setup friction if testbed exists; HIGH if not

   **Q2 — Testbed availability** (for the classified level):
   - Is the required testbed available? (FPGA board for L1/L2; FPGA NICs + switch for L3/L4)
   - For L4: is the multi-FPGA cluster + switch testbed ready, or does it need to be built?
   - If testbed is unavailable: flag as "needs hardware setup" — do NOT substitute Soft-RoCE for RDMA comparisons
   - ns-3 RDMA simulation can supplement L4 for scale-out sensitivity, but cannot replace real-hardware L3/L4 baseline numbers

   **Workload availability** (secondary check):
   - Are standard compression benchmarks usable? (Silesia corpus, enwik, real RDMA traces, synthetic gradient tensors)
   - Skip ideas that require exotic proprietary traces with no synthetic substitute

2. **Novelty quick-check**: For each idea, do 2-3 targeted searches to see if it's already been done. Full `/novelty-check` comes later for survivors.

3. **Impact estimation**: Would a reviewer care about the result?
   - "So what?" test: if the experiment succeeds, does it change how people design NIC/DPU hardware or RDMA protocols?
   - Is the finding actionable or just interesting?
   - **D+C co-innovation bonus**: if an idea is tagged D+C, do NOT eliminate it for complexity. The fact that it requires co-innovating both planes means it likely has no direct prior art. Flag it as "high-effort, high-novelty" and keep it in the list — plan a staged implementation.

Eliminate ideas that fail feasibility or impact. D+C ideas survive even if implementation is hard. Typically 8-12 ideas reduce to 4-6.

### Phase 4: Deep Validation (for top ideas)

For each surviving idea, run a deeper evaluation:

1. **Novelty check**: Use the `/novelty-check` workflow (multi-source search + GPT-5.5 cross-verification) for each idea

2. **Critical review**: Use GPT-5.5 via `mcp__codex__codex-reply` (same thread):
   ```
   Here are our top ideas after filtering:
   [paste surviving ideas with novelty check results and D/C/D+C/N classification]

   For each, play devil's advocate:
   - What's the strongest objection a MICRO/ISCA/NSDI reviewer would raise?
   - What's the most likely failure mode (e.g., compression ratio too low to matter, control-plane overhead dominates, incompatible with ATOMIC ops)?
   - How would you rank these for a top venue submission?
   - Which 2-3 would you actually work on?

   For ideas tagged D+C (data+control plane co-innovation):
   - Is the control-plane interaction genuinely necessary, or can the data-plane contribution stand alone?
   - If both are needed, what is the minimal control-plane change that enables the data-plane contribution?
   - Does this co-innovation represent an open problem in the RDMA community, or has it been partially solved?
   ```

3. **Combine rankings**: Merge your assessment with GPT-5.5's ranking. Select top 2-3 ideas for pilot experiments.

### Phase 5: Pilot Validation (for top 2-3 ideas)

Before committing to a full research effort, run cheap pilots to get early signal. For computer architecture/networking research, pilots are **analytical models, simulations, or micro-benchmarks** — not GPU training runs.

1. **Design pilots**: For each top idea, classify its NIC modification depth first, then choose the matching pilot type. All ideas are implementable — the pilot just needs to answer: **does the mechanism give meaningful signal before full RTL investment?**

   | Scope level | Pilot approach | What to run | Success signal |
   |-------------|---------------|-------------|---------------|
   | **L1** | Algorithm emulation + analytical model | Python/C prototype on Silesia / gradient tensor data; first-principles throughput/latency model | Compression ratio > target; model predicts throughput at line rate |
   | **L1/L2** | Corundum RTL sketch | 50–150 lines of Verilog/HLS for the core pipeline stage; simulate in Vivado/VCS | Pipeline depth ≤ N cycles, no throughput bubble, resource fits target FPGA |
   | **L2** | Corundum loopback RDMA | Integrate compression stub into Corundum Tx path; run ib_send_bw / ib_read_bw over loopback RoCE | End-to-end RDMA BW within X% of uncompressed baseline; latency overhead < Y ns |
   | **L3** | 2-node FPGA NIC + switch | Real RoCE traffic with variable-size compressed payloads; retransmit behavior under congestion ; retransmit rate < Z%; throughput improvement visible |
   | **L4** | Multi-node FPGA cluster + switch (or ns-3 for sensitivity) | End-to-end AllReduce / storage workload on real cluster; ns-3 for configurations beyond available node count | Application-level speedup > X% |
   | **Any** | Analytical model (first pass) | Queue-theory / pipeline model before any hardware work | Model consistent with published NetZIP / BlueField C-engine / CAST baselines |

   - **No Soft-RoCE substitution**: if L3/L4 testbed is not available, run only the analytical model + L1/L2 pilot and explicitly scope the paper claim down to L1/L2 until hardware is ready.
   - Clear success metric defined upfront per row above.

2. **Run pilots**: Use Bash to run analytical scripts or invoke available simulators. Do NOT launch GPU jobs — there are no ML models to train here.

3. **Collect results**: Once pilots complete, compare:
   - Which ideas showed positive signal (model predicts improvement)?
   - Which showed null/negative signal? (eliminate or deprioritize)
   - Any surprising findings that suggest a pivot?

4. **Re-rank based on pilot evidence**: An idea with strong analytical/simulation signal jumps ahead of a theoretically appealing but unvalidated idea.

Note: Skip this phase if no simulation environment or hardware is available. Flag skipped ideas as "needs pilot validation" in the report.

### Phase 6: Output — Ranked Idea Report

Write a structured report to `idea-stage/IDEA_REPORT.md`:

```markdown
# Research Idea Report

**Direction**: [user's research direction]
**Generated**: [date]
**Ideas evaluated**: X generated → Y survived filtering → Z piloted → W recommended

## Landscape Summary
[3-5 paragraphs on the current state of the field]

## Recommended Ideas (ranked)

### Idea 1: [title]
- **Hypothesis**: [one sentence]
- **Minimum experiment**: [concrete description]
- **Expected outcome**: [what success/failure looks like]
- **Novelty**: X/10 — closest work: [paper]
- **Feasibility**: [compute, data, implementation estimates]
- **Risk**: LOW/MEDIUM/HIGH
- **Contribution type**: empirical / method / theory / diagnostic
- **Contribution scope**: L1 / L2 / L3 / L4 — [what layer of the RDMA system this claims to improve]
- **RDMA plane interaction**: D / C / D+C / N — [one sentence: what exactly breaks or must change in each plane]
- **Required testbed**: [single FPGA / 2-node RoCE / multi-node cluster+switch / ns-3 supplement]
- **Pilot result**: [POSITIVE: X% gain shown / NEGATIVE: no signal / SCOPED DOWN: claim reduced to L1/L2 pending hardware / SKIPPED: testbed not available]
- **Reviewer's likely objection**: [strongest counterargument]
- **Why we should do this**: [1-2 sentences]

### Idea 2: [title]
...

## Eliminated Ideas (for reference)
| Idea | Reason eliminated |
|------|-------------------|
| ... | Already done by [paper] |
| ... | Requires > 1 week GPU time |
| ... | Result wouldn't be interesting either way |

## Pilot Validation Results
| Idea | Scope | Plane | Required testbed | Pilot run | Key metric | Signal |
|------|-------|-------|-----------------|-----------|------------|--------|
| Idea 1 | L1 | D | Single FPGA | Corundum RTL sketch, Vivado sim | pipeline depth 3 cycles, no stall | POSITIVE |
| Idea 2 | L3 | D+C ★ | 2-node FPGA + switch | Analytical model (testbed pending); credit window math shows underflow under variable ratio | 12% credit underflow predicted — control plane change necessary | HIGH-NOVELTY, SCOPED DOWN to L1/L2 pilot until testbed ready |
| Idea 3 | L2 | D | 2-node loopback RoCE | Corundum loopback + ib_send_bw | +22% effective BW vs uncompressed baseline | WEAK POSITIVE |

## Suggested Execution Order
1. Start with Idea 1 (positive pilot signal, lowest risk)
2. Idea 3 as backup (weak signal, may need larger scale to confirm)
3. Idea 2 eliminated by pilot — negative result documented

## Next Steps
- [ ] Scale up Idea 1 to full experiment (multi-seed, full dataset)
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
- Always estimate compute cost. An idea that needs 1000 GPU-hours is not actionable for most researchers.
- "Apply X to Y" is the lowest form of research idea. Push for deeper questions.
- Include eliminated ideas in the report — they save future time by documenting dead ends.
- **If the user's direction is too broad (e.g., "NLP", "computer vision", "reinforcement learning"), STOP and ask them to narrow it.** A good direction is 1-2 sentences specifying the problem, domain, and constraint — e.g., "factorized gap in discrete diffusion LMs" or "sample efficiency of offline RL with image observations". Without sufficient specificity, generated ideas will be too vague to run experiments on.

## Composing with Other Skills

After this skill produces the ranked report:
```
/idea-creator "direction"     → ranked ideas
/novelty-check "top idea"     → deep novelty verification (already done in Phase 4, but user can re-run)
/research-review "top idea"   → external critical feedback
implement                     → write code
/run-experiment               → deploy to GPU
/auto-review-loop             → iterate until submission-ready
```

## Review Tracing

After each `mcp__codex__codex` or `mcp__codex__codex-reply` reviewer call, save the trace following `shared-references/review-tracing.md`. Use `tools/save_trace.sh` or write files directly to `.aris/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
