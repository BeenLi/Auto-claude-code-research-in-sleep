# AGENT.md

This file provides guidance to AI agents when working in this repository.

## Research Domain

This ARIS instance is configured for **Computer Architecture / AI Infrastructure for LLM** research with a hardware-leaning systems focus. The current active idea is shared DPU/NIC-side lossless communication compression service fairness for LLM infrastructure, but Workflow 1 should search across the full AI infrastructure stack rather than defaulting to network-only topics.

### Domain Profile

- **Field**: Computer Architecture / Systems / Networking / AI Infrastructure for LLM
- **Target venues**: MICRO, ISCA, HPCA, ASPLOS, NSDI, OSDI, SIGCOMM, DAC, EuroSys, FCCM, IEEE TPDS, IEEE TC, IEEE TON, IEEE TVLSI, IEEE TCAD, ACM TACO
- **AI infrastructure layers**: compute/accelerator, memory/storage/data movement, interconnect/network, runtime/system
- **Evidence and validation**: Workflow 1 uses lightweight evidence for idea ranking: analytical models, small simulator runs, trace replay, microbenchmarks, RTL/HLS sketches, and gem5/htsim smoke runs. Full experiment execution is handled by Workflow 1.5.
- **Current simulator-first anchor**: gem5 + Broadcom/csg-htsim + `cosim_gem5_htsim`, with window-level co-simulation for Rx decompression expansion pressure.
- **Key metrics**: serving/system (tokens/s, requests/s, TTFT, TPOT, tail latency, completion time); data movement (HBM/CXL/PCIe/NIC/storage bandwidth, memory copy amplification, queue/buffer occupancy); network/RDMA (goodput, FCT, retransmitted bytes, drop/stall/congestion signals); compression (compression ratio, decompression expansion ratio, accepted/dropped compressed bytes); hardware cost (area, LUT/BRAM/DSP/SRAM footprint, timing/frequency, power/energy).
- **Platform primitives**: accelerators, HBM/CXL memory systems, SmartNIC/DPU/RNIC datapaths, FPGA/ASIC prototypes, P4 programmable switches, storage datapaths, gem5, Broadcom/csg-htsim, ns-3, SystemC, RTL/HLS.
- **Reviewer persona**: senior MICRO/ISCA/HPCA/ASPLOS program committee member; cares about microarchitecture detail, concrete bottleneck models, validation credibility, hardware cost, and generality across LLM infrastructure workloads.

## Workflows

**Workflow 1 -- Idea Discovery** (`/idea-discovery "topic"`):
`research-lit` -> `idea-creator` -> `novelty-check` -> `research-review` -> `research-refine` -> `experiment-plan`

**Workflow 1.5 -- Experiment Bridge** (`/experiment-bridge`):
Reads `refine-logs/EXPERIMENT_PLAN.md` -> implements code -> deploys experiments -> collects initial results in `EXPERIMENT_LOG.md`

**Workflow 2 -- Auto Review Loop** (`/auto-review-loop "scope"`):
Up to 4 rounds: external LLM review -> identify weaknesses -> agent implements fixes -> re-review until score >= 6/10

**Workflow 3 -- Paper Writing** (`/paper-writing "NARRATIVE_REPORT.md"`):
`paper-plan` -> `paper-figure` -> `paper-write` -> `paper-compile` -> `auto-paper-improvement-loop`

**Workflow 4 -- Rebuttal** (`/rebuttal "paper/ + reviews"`):
Parses external reviews -> enforces coverage and grounding -> drafts text-only rebuttal

**Full pipeline**: `/research-pipeline "topic"` runs Workflow 1 -> 1.5 -> 2 -> 3

## Pipeline Status

```yaml
stage: implementation
idea: "C-Share: Multi-Resource Fairness for Shared Lossless Communication Compression on DPUs/NICs"
contract: idea-stage/docs/research_contract.md
current_branch: codex/computer-architecture
baseline: "Uncompressed communication, FIFO DPU compression service, wire-byte fair sharing, ratio-greedy compression, current Rx output-only budgeter, generic DPU QoS without compression hints, oracle scheduler"
validation_status: "Workflow 1 idea discovery complete on 2026-05-07; external gpt-5.5 reviewer selected C-Share, score 5/6, confidence high; no C-Share experiments executed yet"
active_tasks: []
language: zh
last_updated: "2026-05-07"
next: "Proceed only with /experiment-bridge for C-Share P0 model plumbing: multi-resource compression-service simulator, naive scheduler failure matrix, resource ablations, and literature-profile calibration. Do not claim real LLM payload compressibility, DPU deployment benefit, or line-rate hardware feasibility until P2/P3 evidence exists."
```

## State Persistence Rules

Pipeline Status update triggers:
- Stage transitions, idea selection, baseline confirmed, validation start/stop
- User says "save" / "record" / "new session" / "wrap up"
- Before any long pause or handoff

Research Contract update triggers:
- Idea selected or changed; if the idea fails, select the next candidate from `idea-stage/IDEA_CANDIDATES.md` and overwrite the contract
- `refine-logs/FINAL_PROPOSAL.md` or `refine-logs/EXPERIMENT_PLAN.md` generated/updated
- Baseline reproduced, major result obtained, Mx Go/No-Go completed, or `/result-to-claim` resolves claim support

On new session or post-compaction recovery:
1. Read ## Pipeline Status
2. Read idea-stage/docs/research_contract.md (the active idea's focused context)
3. Read project notes if any (e.g., experiment logs, decision rationale)
4. If active_tasks is non-empty -> check remote status, rebuild monitoring
5. Resume work without asking the user

## Skill Invocation

```bash
/research-lit "AI infrastructure for LLM" -- sources: local, zotero, web -- extended topics: "KV cache CXL", "NIC compression", "LLM checkpointing"
/idea-discovery "AI infrastructure for LLM -- hardware bottlenecks"
/research-pipeline "NIC/DPU compression for LLM serving" -- AUTO_PROCEED: false
```

Key overridable parameters: `AUTO_PROCEED` (true), `human_checkpoint` (false), `sources` (all), `code_review` (true), `illustration` (gemini/mermaid/false).

## MCP Servers

Register reviewer MCP servers in the active agent runtime using that runtime's MCP configuration command.

```bash
# Codex CLI reviewer server command
npm install -g @openai/codex && codex setup
codex mcp-server

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
