# AGENT.md

This file provides guidance to AI agents when working in this repository.

## Research Domain

This ARIS instance is configured for **Computer Architecture / AI Infrastructure for LLM** research with a hardware-leaning systems focus. 

## Workflows

**Workflow 1 -- Idea Discovery** (`/idea-discovery "topic"`):
`research-lit` -> `idea-creator` -> `novelty-check` -> `research-review` -> `research-refine-pipeline`

Canonical chain: research-lit -> idea-creator -> novelty-check -> research-review -> research-refine-pipeline

`research-refine-pipeline` is the public Workflow 1 tail wrapper for
`research-refine` -> `experiment-plan`. Workflow 1 prepares the selected idea,
final proposal, and experiment plan; it does not execute pilots or baseline
reproduction.

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
stage: workflow_1_5_in_progress  # M1 GREEN (narrow), M2 GREEN, M3 YELLOW (analytical frontier + sim cross-check done); M4a next
active_idea: WR-ZipGuard
active_files:
  literature_review: idea-stage/LITERATURE_REVIEW.md
  idea_report: idea-stage/IDEA_REPORT.md
  final_proposal: refine-logs/FINAL_PROPOSAL.md
  experiment_plan: refine-logs/EXPERIMENT_PLAN.md
  evaluation_contract: refine-logs/EVALUATION_CONTRACT.md
  experiment_log: refine-logs/EXPERIMENT_LOG.md
  research_contract: idea-stage/docs/research_contract.md
  m1_code: experiments/m1/  # 66 unit tests, deployed to myDevbox:~/wr-zipguard/experiments/m1
  m3_code: experiments/m3/  # 46 unit tests, analytical frontier + sim cross-check; M3_REPORT.md
  m3_contract: refine-logs/EVALUATION_CONTRACT_M3.md
workflow_1_exit_gate: passed
m1_status: GREEN_fp8e5m2_only  # deflate-only; ONLY FP8_E5M2 clears 0.75 (BF16/FP8_E4M3 entropy floors >0.75, provably can't); generator validated synthetic+gpt2+Qwen2.5-7B
m2_status: GREEN  # bf3_server (10.154.163.113, root) real BF3 + DOCA 2.9. Capability: compress=unsupported, decompress deflate/lz4=supported. C2 correctness PROVEN bit-exact on HW (stock zlib + raw deflate of FP8_E5M2 KV). Throughput (doca_bench): engine ceiling ~170-175 Gib/s (~188 Gbps), pipelining-required (8x over single-shot), chunk-gated (256KB->141Gbps, 1MB->180, 2MB->188; 4KB hopeless). Red lines 1+2+3 CLEAR for >=256KB chunks at <=100Gbps. Design constraint: gate must aggregate KV to >=256KB. Ceiling: ~188Gbps egress does NOT scale w/ parallel contexts (4ctx=4x42.6=170Gib/s=1ctx) BUT likely a PCIe-x8 artifact NOT the engine: lspci shows BF3 link Gen5 x8 (downgraded from x16), egress 23.5GB/s ~87% of practical x8/dir -> host PCIe write-back ~saturated. CORRECTED over-claim: it's a system ceiling under host-mem+x8-slot, not proven silicon; on x16 or DPU-local mem could be ~2x (~376Gbps). RESOLVE via host-vs-DPU-memory test (skipped; needs DPU ARM access — rshim present, tmfifo/SSH unconfigured). Scope holds for THIS setup: compression pays when path-bottleneck-BW < ~188Gbps; profitable region FP8_E5M2 x BW<~188Gbps(maybe x8-limited) x chunk>=256KB. Peer bf3_client=10.154.163.112 for M4 RDMA.
m3_status: YELLOW  # experiments/m3/ (46 unit tests, pure-stdlib analytical core). Two-layer (user-approved): analytical frontier + LLMServingSim cross-check. LAYER 1 (go/no-go): reuses M1 profitability.py, decompress chunk-coupled D=alpha*D_egress(S) (egress->input units reconciliation). For measured envelope (FP8_E5M2 alpha=0.732, 2MB chunk) profitable iff B < B_crit: 25Gbps band->5.9, 50->10.5, 100Gbps FPGA->17.2 Gbps. HARD CEILING: even free/infinite compress caps region at B<(1-alpha)*D_egress~=0.27*188~=50Gbps -> realistic-KV compression STRUCTURALLY cannot pay at mainstream 100-400Gbps (alpha~0.73 => only 27% wire saving). Software compress (17MB/s) never pays -> asymmetric FPGA mandatory. VERDICT YELLOW: real but narrow bandwidth-limited region (cross-AZ/oversubscribed/WAN-ish). LAYER 2 (cross-check, PASS): deployed LLMServingSim v1.1.0 (myDevbox ~/autoResearch/LLMServingSim, PD disaggregation, ASTRA-Sim analytical). Llama-3.1-8B bf16, 2048-tok prompt, single_node_pd, --no-enable-prefix-caching (PD+prefix-cache crashes this branch). TTFT(link_bw): bw<=8GB/s clean 1/bw law R2=1.0 -> PD KV transfer is bandwidth-limited (~bytes/link_bw), validates frontier physics; bw>=16 floors at compute ~83ms; TPOT invariant. Implied payload 750MB=2.79x minimal KV (sim moves activations alongside KV; scaling law unaffected). Caveats: bf16 only (no FP8 sim profile) validates transfer MODEL not FP8 TTFT; M2 ~188Gbps ceiling maybe x8-limited so window could be ~2x wider; full raw/always/static/gate TTFT injection deferred (needs Chakra/ASTRA instrumentation + FP8 profile + long-ctx workloads). C3=YELLOW (narrowed regime). Report: experiments/m3/M3_REPORT.md; contract: refine-logs/EVALUATION_CONTRACT_M3.md.
m6_status: PLANNED_BLOCKED  # supplementary GPU-cost baseline (EXPERIMENT_PLAN Block 7, tracker R013). Measures the GPU tax of GPU-side KV compression (UCCL p2p + DietGPU ANS; opt nvCOMP) to quantify the "GPU-side codecs compete for GPU resources" differentiator. Metrics: SM%/HBM-BW% of compress kernels + TTFT/TPOT interference of co-located vLLM. DietGPU=fp16/bf16/fp32 only (NO FP8 -> can't target WR-ZipGuard's profitable dtype; bf16 KV ~0.79 ratio). BLOCKED on GPU access (myDevbox no GPU, A100 unavail); single-GPU loopback fallback. Off critical path. Full plan in Obsidian 007-ideas/WR-ZipGuard/Experiment Plan — GPU Cost...(M6).md.
next_step: M4a integrated RDMA prototype (bf3_server<->bf3_client) for in-pipeline D_eff + staging cost, with claimed regime narrowed to bandwidth-limited fabrics (<=~17Gbps realistic FPGA, <=~50Gbps ceiling, maybe ~100Gbps if M2 ceiling is x8-limited). Sender still needs M4b FPGA compress (software=17MB/s never pays). Optional: resolve M2 x8-vs-silicon ceiling (DPU ARM access) to widen the window; full LLMServingSim policy injection for real TTFT/TPOT if needed.
execution_platform: myDevbox  # Debian, py3.13, 64-core, 251GB RAM, no GPU; HF via hf-mirror.com. LLMServingSim deployed at ~/autoResearch/LLMServingSim (venv env/; matplotlib unavailable offline -> M3 figure PNGs deferred, figure-data JSON committed)
active_tasks: []  # no long-running remote jobs; M1/M3 runs are on-demand
last_updated_utc: 2026-06-16T00:00:00Z
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
