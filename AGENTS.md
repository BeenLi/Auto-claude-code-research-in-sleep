# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working in this repository.

## Research Domain

This ARIS instance is configured for **Computer Architecture / AI Infrastructure for LLM** research with a hardware-leaning systems focus. The current active idea is NIC/DPU-side compression for RDMA traffic in LLM infrastructure, but Workflow 1 should search across the full AI infrastructure stack rather than defaulting to network-only topics.

### Domain Profile

- **Field**: Computer Architecture / Systems / Networking / AI Infrastructure for LLM
- **Target venues**: MICRO, ISCA, HPCA, ASPLOS, NSDI, OSDI, SIGCOMM, DAC, EuroSys, FCCM, IEEE TPDS, IEEE TC, IEEE TON, IEEE TVLSI, IEEE TCAD, ACM TACO
- **AI infrastructure layers**: compute/accelerator, memory/data movement, interconnect/network, storage/checkpoint/data pipeline, runtime/serving
- **Evidence and validation**: Workflow 1 uses lightweight evidence for idea ranking: analytical models, small simulator runs, trace replay, microbenchmarks, RTL/HLS sketches, and gem5/htsim smoke runs. Full experiment execution is handled by Workflow 1.5.
- **Current simulator-first anchor**: gem5 + Broadcom/csg-htsim + `cosim_gem5_htsim`, with window-level co-simulation for Rx decompression expansion pressure.
- **Key metrics**: serving/system (tokens/s, requests/s, TTFT, TPOT, tail latency, completion time); data movement (HBM/CXL/PCIe/NIC/storage bandwidth, memory copy amplification, queue/buffer occupancy); network/RDMA (goodput, FCT, retransmitted bytes, drop/stall/congestion signals); compression (compression ratio, decompression expansion ratio, accepted/dropped compressed bytes); hardware cost (area, LUT/BRAM/DSP/SRAM footprint, timing/frequency, power/energy).
- **Platform primitives**: accelerators, HBM/CXL memory systems, SmartNIC/DPU/RNIC datapaths, FPGA/ASIC prototypes, P4 programmable switches, storage datapaths, gem5, Broadcom/csg-htsim, ns-3, SystemC, RTL/HLS.
- **Reviewer persona**: senior MICRO/ISCA/HPCA/ASPLOS program committee member; cares about microarchitecture detail, concrete bottleneck models, validation credibility, hardware cost, and generality across LLM infrastructure workloads.

## Workflows

**Workflow 1 — Idea Discovery** (`/idea-discovery "topic"`):
`research-lit` → `idea-creator` → `novelty-check` → `research-review` → `research-refine` → `experiment-plan`

**Workflow 1.5 — Experiment Bridge** (`/experiment-bridge`):
Reads `EXPERIMENT_PLAN.md` → implements code → deploys experiments → collects initial results in `EXPERIMENT_LOG.md`

**Workflow 2 — Auto Review Loop** (`/auto-review-loop "scope"`):
Up to 4 rounds: external LLM review → identify weaknesses → Codex implements fixes → re-review until score ≥ 6/10

**Workflow 3 — Paper Writing** (`/paper-writing "NARRATIVE_REPORT.md"`):
`paper-plan` → `paper-figure` → `paper-write` → `paper-compile` → `auto-paper-improvement-loop`

**Workflow 4 — Rebuttal** (`/rebuttal "paper/ + reviews"`):
Parses external reviews → enforces coverage and grounding → drafts text-only rebuttal

**Full pipeline**: `/research-pipeline "topic"` runs Workflow 1 → 1.5 → 2 → 3

## Pipeline Status

```yaml
stage: implementation
idea: "Rx Expansion Budgeting for Compressed RDMA: NIC/DPU-side lossless compression with decompressed output-byte admission, scheduling, and feedback"
contract: refine-logs/EXPERIMENT_PLAN.md
current_branch: codex/computer-architecture
baseline: "Uncompressed RDMA, naive compressed RDMA, receiver decompressed-byte token bucket, static Rx output partitioning, FIFO decompression queue, wire-byte weighted fair sharing, reactive QoS controller, oracle output-byte scheduler"
validation_status: M1 P0-only analytical sensitivity pack complete; 960 rows, 384 output-unsafe, conditional Go for M2 model plumbing only
active_tasks: []
language: zh
last_updated: "2026-04-26"
next: "Use experiments/rx-expansion/results/M1_GO_NOGO_REPORT.md for targeted Go/No-Go review or decide whether to implement M2 standalone simulator. P0-only results are analytical sensitivity only."
```

## State Persistence Rules

Pipeline Status update triggers:
- Stage transitions, idea selection, baseline confirmed, validation start/stop
- User says "save" / "record" / "new session" / "wrap up"
- Before any long pause or handoff

On new session or post-compaction recovery:
1. Read ## Pipeline Status
2. Read refine-logs/EXPERIMENT_PLAN.md (the active idea's focused context)
3. Read project notes if any (e.g., experiment logs, decision rationale)
4. If active_tasks is non-empty → check remote status, rebuild monitoring
5. Resume work without asking the user

## Skill Invocation

```bash
/research-lit "AI infrastructure for LLM" — sources: local, zotero, web — extended topics: "KV cache CXL", "NIC compression", "LLM checkpointing"
/idea-discovery "AI infrastructure for LLM — hardware bottlenecks"
/research-pipeline "NIC/DPU compression for LLM serving" — checkpoint mode: standard
```

Key overridable parameters: `CHECKPOINT_MODE` (standard), `CHECKPOINTS` (literature_scope, idea_selection), `AUTO_PROCEED` (compatibility), `human_checkpoint` (false), `sources` (all), `code_review` (true), `illustration` (gemini/mermaid/false).

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
