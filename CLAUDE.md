# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Research Domain

This ARIS instance is configured for **computer architecture research**, specifically **NIC/DPU-side lossless compression in RDMA networks**. All skills should apply this domain context unless overridden inline.

### Domain Profile

- **Field**: Computer Architecture / Systems / Networking
- **Target venues**: MICRO, ISCA, HPCA, ASPLOS, NSDI, OSDI, SIGCOMM, DAC, EuroSys, FCCM, IEEE TPDS, IEEE TC, IEEE TON, IEEE TVLSI, IEEE TCAD, ACM TACO
- **Experimental paradigm**: FPGA prototype / RTL simulation / analytical model / gem5/systemC modeling / micro-benchmark on real hardware
- **Key metrics**: throughput (Gbps), latency (ns/μs), compression ratio, FPGA resource (LUT/BRAM/DSP), power (W), PCIe/RDMA bandwidth utilization
- **Platform primitives**: SmartNIC/DPU (NVIDIA BlueField, CX7), P4 programmable switches, FPGA-based RNIC prototype with compression hardware, ns-3 network simulator, htsim network simulator, gem5 simulator
- **Pilot experiments**: analytical throughput/latency model, gem5 modeling, RTL implementation and simulation in Vivado/VCS, or micro-benchmark on available hardware (e.g., BlueField-2)
- **Reviewer persona**: senior MICRO/ISCA/HPCA/ASPLOS program committee member — cares about: micro-architecture detail, real measurement vs simulation, hardware area/power overhead, generalizability across workloads

### Skill Behavior Overrides

When any skill references ML-specific concepts, apply the architecture equivalent:

| ML Concept (in skill) | Architecture Equivalent (apply this) |
|----------------------|--------------------------------------|
| NeurIPS / ICML / ICLR venues | MICRO / ISCA / HPCA / ASPLOS |
| GPU pilot experiment | RTL simulation / analytical model / FPGA micro-benchmark |
| `PILOT_MAX_HOURS` GPU budget | Implementation complexity (days of RTL work) |
| "Training recipe" / loss function | Hardware design flow: RTL → simulation → FPGA synthesis |
| "senior ML researcher" reviewer | "senior computer architecture researcher" reviewer |
| Semantic Scholar / arXiv cs.LG | DBLP proceedings / ACM DL / USENIX / IEEE Xplore |

## Paper Library

- default: ~/papers
- nic-lossless-compression: /Users/bytedance/Nutstore Files/顶刊论文/IOAcc/RDMA/compression

## Workflows

**Workflow 1 — Idea Discovery** (`/idea-discovery "topic"`):
`research-lit` → `idea-creator` → `novelty-check` → `research-review` → `research-refine` → `experiment-plan`

**Workflow 2 — Auto Review Loop** (`/auto-review-loop "topic"`):
Up to 4 rounds: external LLM review → identify weaknesses → Claude implements fixes → re-review until score ≥ 6/10

**Workflow 3 — Paper Writing** (`/paper-writing "NARRATIVE_REPORT.md"`):
`paper-plan` → `paper-figure` → `paper-write` → `paper-compile` → `auto-paper-improvement-loop`

**Full pipeline**: `/research-pipeline "topic"` runs Workflow 1 → 2 → 3

## Skill Invocation

```bash
/research-lit "nic-lossless-compression" — sources: local, zotero, web — extended topics: "memory compression", "compression accelerator", "in-network compression"
/idea-discovery "nic-lossless-compression"
/research-pipeline "nic-lossless-compression" — AUTO_PROCEED: false
```

Key overridable parameters: `AUTO_PROCEED` (true), `human_checkpoint` (false), `sources` (all), `code_review` (true), `illustration` (gemini/mermaid/false).

## MCP Servers

```bash
# Codex CLI (GPT-5.4 reviewer)
npm install -g @openai/codex && codex setup
claude mcp add codex -s user -- codex mcp-server

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
