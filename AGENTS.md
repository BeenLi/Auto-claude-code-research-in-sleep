# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working in this repository.

## Research Domain

This ARIS instance is configured for **Computer Architecture / AI Infrastructure for LLM** research with a hardware-leaning systems focus. The specific research project and active idea are defined in the **Pipeline Status** section below, which is branch-specific. Workflow 1 is centered around the user-provided **Topic**. While the search is anchored by this Topic, the agent must investigate the full AI infrastructure stack (compute, memory, interconnect, runtime) to identify cross-layer bottlenecks and co-design opportunities related to it.

### Domain Profile

- **Field**: Computer Architecture / Systems / Networking / AI Infrastructure for foundation-model workloads, with a hardware-leaning systems focus. The default emphasis is LLM inference and serving, but the agent must also track training, fine-tuning, checkpointing, multimodal/VLM, reasoning, RAG, and agentic multi-call workloads when they affect infrastructure bottlenecks.
- **Research mission**: Discover cross-layer bottlenecks and co-design opportunities across model behavior, runtime scheduling, memory hierarchy, accelerator/datapath design, interconnect/networking, storage/checkpointing, and cluster operations. Prefer ideas with a concrete bottleneck model, a plausible hardware/software mechanism, measurable system-level impact, and a credible path to artifact evaluation.
- **Primary target venues**: MICRO, ISCA, HPCA, ASPLOS, OSDI, SOSP, NSDI, SIGCOMM, MLSys, EuroSys.
- **Secondary / adjacent venues**: DAC, FCCM, SC, IEEE TPDS, IEEE TC, IEEE TON, IEEE TVLSI, IEEE TCAD, ACM TACO.
- **Current trend watchlist**:
  - Disaggregated inference: prefill/decode separation, KV transfer, phase-specific resource allocation, goodput under TTFT/TPOT SLOs.
  - KV-cache systems: paging, prefix reuse, compression, tiering, CXL/offload, migration, fragmentation, and long-context scaling.
  - Reasoning and agentic workloads: long traces, multi-call execution, tool/RAG pipelines, structured output, speculative decoding, and scheduler feedback loops.
  - Heterogeneous and rack-scale infrastructure: GPU/accelerator pods, scale-up interconnects, CXL fabrics, Ethernet/RDMA evolution, UEC/UALink-like standards, SmartNIC/DPU/RNIC offload.
  - Efficient inference: quantization, sparsity, MoE routing, speculative decoding, kernel fusion, memory-bandwidth reduction, and energy/TCO optimization.
  - Training and fine-tuning infrastructure: collective communication, checkpointing, pipeline/tensor/expert parallelism, failure recovery, and network contention.
- **Required baselines and comparators**:
  - For LLM serving/runtime ideas: compare against or explicitly rule out vLLM/PagedAttention, SGLang, TensorRT-LLM, continuous batching, prefix caching, chunked prefill, quantization, speculative decoding, and disaggregated serving baselines.
  - For network/collective ideas: compare against realistic RDMA/RoCE/InfiniBand/Ethernet congestion-control and collective-communication baselines, with topology and traffic assumptions stated.
  - For memory/KV ideas: compare against HBM-only, CPU/PCIe offload, CXL-tiering, paging, compression, and cache-reuse alternatives.
  - For hardware datapath ideas: include area/power/latency feasibility and identify whether the mechanism belongs in GPU, DPU/NIC, switch, CXL device, FPGA, ASIC, or software runtime.
- **Validation philosophy**: Use the cheapest credible evidence first, but never make claims beyond the achieved evidence tier. Every idea must state its highest evidence tier, missing evidence, and next validation step.
- **Evidence tiers**:
  - **T0 — Literature and novelty map**: recent papers, systems, standards, benchmarks, and products; identify closest prior work and why the idea is not already solved.
  - **T1 — Analytical bottleneck model**: equations or roofline-style model with explicit workload assumptions and sensitivity analysis.
  - **T2 — Component characterization**: microbenchmarks (e.g., isolating specific operator latency or hardware limits), statistical analysis of hardware/profiling traces (e.g., calculating read/write ratios or cache hit rates from memory access patterns), kernel/network/storage measurements, or post-mortem dissection of extracted profiles to isolate the bottleneck.
  - **T3 — Trace-driven or workload-driven simulation**: request traces, token traces, KV-cache traces, collective traces, or network traffic traces with stated replay limitations.
  - **T4 — Cross-layer simulation**: gem5, SystemC, htsim, ns-3, Astra-Sim, SimAI, or custom simulator, selected according to the hypothesis rather than fixed in advance.
  - **T5 — Hardware feasibility**: RTL/HLS/FPGA/ASIC model, synthesis, timing/area/power estimate, or single-node full-system prototype.
  - **T6 — End-to-end prototype or benchmark**: integration with serving/training stack and evaluation against modern baselines under realistic SLOs, load, topology, and cost constraints.
  
- **Default toolchain options**:
  - **Serving/runtime**: vLLM, SGLang, TensorRT-LLM, PyTorch, Triton, CUDA/HIP profiling, synthetic and real request traces.
  - **Architecture/memory**: gem5, SystemC, custom analytical models, cache/KV simulators, CXL/PCIe/NVMe models.
  - **Network/collectives**: htsim, ns-3, Astra-Sim, SimAI, NCCL/RCCL traces, topology-aware collective models.
  - **Hardware feasibility**: RTL, HLS, FPGA prototypes, synthesis reports, area/power models, P4 or programmable switch/NIC models.
  - **Benchmarking**: MLPerf-style serving/training scenarios, open LLM serving benchmarks, long-context workloads, reasoning/agent workloads, and project-specific traces.

- **Current simulator-first anchor**: No simulator is mandatory for all ideas. The agent should select the validation path based on the hypothesis. For collective communication or large-scale training ideas, prefer Astra-Sim/SimAI-style modeling.

- **Idea acceptance criteria**:
  - A clear bottleneck that is important for current or emerging foundation-model infrastructure.
  - A cross-layer mechanism that plausibly beats strong software/runtime baselines.
  - A minimal validation plan that can produce evidence within the current repository/tooling.
  - A path from preliminary evidence to publishable artifact.
  - A concise statement of why the idea fits at least one primary venue.

- **Early rejection criteria**:
  - Pure benchmark engineering without a new systems or architecture insight.
  - Pure software scheduling that is already covered by modern serving runtimes unless the idea exposes a new hardware/runtime interface.
  - Simulation-only claims without calibration, sensitivity analysis, or a path to real workload validation.
  - Novelty claims based only on LLM judgment without literature, artifact, and baseline checks.
- **Autonomous research-agent discipline**:
  - Maintain provenance for all claims: paper/system source, date checked, assumptions, and confidence.
  - Log why each idea was accepted, rejected, or deferred.
  - Preserve negative results and failed hypotheses; do not silently discard them.
  - Use external LLM review as critique, not as evidence.
  - Before expensive experiments, produce a compact contract: hypothesis, baseline, workload, metric, expected result, failure modes, and stop condition.
  - Bound every paper claim by the strongest completed evidence tier.
  - Prefer reproducible scripts, pinned versions, deterministic seeds where possible, and explicit simulator/runtime configuration.
  - Treat tool use, MCP integrations, remote execution, and generated code as potentially fallible; use guardrails, tracing, and sanity checks for agent actions.
- **Reviewer persona**: senior MICRO/ISCA/ASPLOS/OSDI/NSDI program committee member. The reviewer cares about concrete bottleneck models, architectural mechanism clarity, strong baselines, hardware feasibility, calibrated validation, reproducibility, scalability, deployment constraints, and whether the work would still matter under the next generation of LLM runtimes and accelerator fabrics.

## Workflows

**Workflow 1 — Idea Discovery** (`/idea-discovery "topic"`):
`research-lit` → `idea-creator` → `novelty-check` → `research-review` → `research-refine` → `experiment-plan`

**Workflow 1.5 — Experiment Bridge** (`/experiment-bridge`):
Reads `EXPERIMENT_PLAN.md` → anchors with Astra-Sim(<https://github.com/astra-sim/astra-sim)/SimAI(https://github.com/aliyun/SimAI>) for collective communication → abstracts gem5 compute to focus on Memory/PCIe/DMA modeling → enforces autoregressive feedback loops (not static trace replay) for accurate TTFT/TPOT → deploys experiments → collects initial results in `EXPERIMENT_LOG.md`

**Workflow 2 — Auto Review Loop** (`/auto-review-loop "scope"`):
Up to 4 rounds: external LLM review → identify weaknesses → Codex implements fixes → re-review until score ≥ 6/10

**Workflow 3 — Paper Writing** (`/paper-writing "NARRATIVE_REPORT.md"`):
`paper-plan` → `paper-figure` → `paper-write` → `paper-compile` → `auto-paper-improvement-loop`

**Workflow 4 — Rebuttal** (`/rebuttal "paper/ + reviews"`):
Parses external reviews → enforces coverage and grounding → drafts text-only rebuttal

**Full pipeline**: `/research-pipeline "topic"` runs Workflow 1 → 1.5 → 2 → 3

## Pipeline Status

```yaml
stage: idle
idea: ""
contract: ""
current_branch: main
baseline: ""
validation_status: ""
active_tasks: []
language: zh
last_updated: "2026-04-28"
next: "Ready to start Workflow 1 (Idea Discovery). Run `/research-pipeline \"topic\"` to begin."
```

## State Persistence Rules

Pipeline Status update triggers:

- Stage transitions, idea selection, baseline confirmed, validation start/stop
- User says "save" / "record" / "new session" / "wrap up"
- Before any long pause or handoff

On new session or post-compaction recovery:

1. Read ## Pipeline Status
2. Read refine-logs/EXPERIMENT\_PLAN.md (the active idea's focused context)
3. Read project notes if any (e.g., experiment logs, decision rationale)
4. If active\_tasks is non-empty → check remote status, rebuild monitoring
5. Resume work without asking the user

## Skill Invocation

```bash
/research-lit "AI infrastructure for LLM" — sources: local, zotero, web — extended topics: "KV cache CXL", "NIC compression", "LLM checkpointing"
/idea-discovery "AI infrastructure for LLM — hardware bottlenecks"
/research-pipeline "NIC/DPU compression for LLM serving" — checkpoint mode: standard
```

Key overridable parameters: `CHECKPOINT_MODE` (standard), `CHECKPOINTS` (literature\_scope, idea\_selection), `AUTO_PROCEED` (compatibility), `human_checkpoint` (false), `sources` (all), `code_review` (true), `illustration` (codex/mermaid/false).

## MCP Servers

```bash
# Codex CLI (GPT-5.5 reviewer)
npm install -g @openai/codex && codex setup
Codex mcp add codex -s user -- codex mcp-server

# llm-chat (OpenAI-compatible API bridge)
pip install httpx
# Set env: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
```

Active integrations: **Zotero** (literature), **Obsidian** (notes), **Feishu/Lark** (notifications).

## LaTeX Dependencies

```bash
# macOS
brew install mactex poppler
```

