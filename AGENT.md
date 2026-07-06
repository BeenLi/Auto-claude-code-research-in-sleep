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
stage: workflow_1_5_in_progress  # M1 GREEN (narrow), M1.5 GREEN (bf16 rehabilitated via byte-transpose), M2 GREEN, M3 YELLOW (analytical frontier + sim cross-check done); M4a next
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
  m1_5_code: experiments/m1_5/  # 49 unit tests, float-split transforms; m15_results.json + M1_5_REPORT.md
  m1_5_contract: refine-logs/EVALUATION_CONTRACT_M1.5.md
  m1_6_code: experiments/m1_6/  # 69 unit tests, channel-major layout transforms; m16_results.json + M1_6_REPORT.md + commodity_decode_cost.json
  m1_6_contract: refine-logs/EVALUATION_CONTRACT_M1.6.md
workflow_1_exit_gate: passed
m1_status: GREEN_fp8e5m2_RAW_plus_bf16_via_transform  # RAW-byte deflate: ONLY FP8_E5M2 clears 0.75 (BF16/FP8_E4M3 raw entropy floors >0.75). NOTE M1.5 REVISION: M1's "BF16 provably can't" was RAW-byte-specific; a cheap byte-transpose BEFORE deflate rehabilitates BF16 to ~0.70 (clears 0.75) on real gpt2+Qwen2.5-7B KV. See m1_5_status. Generator validated synthetic+gpt2+Qwen2.5-7B
m1_5_status: GREEN  # experiments/m1_5/ (49 unit tests). Float-split/bit-plane preprocessing before deflate (DietGPU/UCCL-Zip/NetZIP/ZipNN mechanism), under BF3 single-standard-deflate-stream constraint. byte_transpose (SoA 2-byte de-interleave, pure permutation, no-op for 1-byte fp8, off-GPU inverse) is THE deployment candidate; bitplane (field split) is diagnostic. Claimable α = concat (one deflate stream BF3 decompresses, M2-proven bit-exact); per-plane (mantissa raw) = DietGPU ceiling, NOT BF3-claimable. RESULT (medians, gate 0.75, decided on captured KV): BF16 RAW 0.79-0.80 -> byte_transpose ~0.70-0.71 REHABILITATED on real KV (gpt2 0.705, Qwen2.5-7B 0.708, synth 0.702) — win entirely the exponent plane (high byte ~0.40; low byte+mantissa ~1.0). fp8 NOT helped: byte_transpose no-op (1 byte), bit-split WORSE (e5m2 0.73->0.83-0.86, e4m3 0.82->0.85); fp8_e5m2 keeps RAW path. byte_transpose ~2500-2750 MB/s sw (vs bitplane ~40-65 for +0.002-0.006). Independently cross-checked fresh-impl (bf16 0.792->0.704 bit-exact, single-stream roundtrip True). IMPLICATION: widens the DTYPE set to BF16 (the DEFAULT dtype -> high applicability), NOT the M3 bandwidth region (bf16 ~30% wire saving ≈ fp8_e5m2 ~27% -> B_crit barely moves; still narrow bandwidth-limited regime). C2 survives (single deflate stream); receive-side un-transpose MUST stay off-GPU (host/DPU-ARM). OPEN: T_xform cost + inverse placement/throughput on real target unmeasured (couples to M2 DPU-ARM block); fp8 captures naive astype (saturation unreported); literature ANS ratios (bf16 ~0.64) need non-deflate codec BF3 can't decode. Report: experiments/m1_5/M1_5_REPORT.md; contract: refine-logs/EVALUATION_CONTRACT_M1.5.md
m2_status: GREEN  # bf3_server (10.154.163.113, root) real BF3 + DOCA 2.9. Capability: compress=unsupported, decompress deflate/lz4=supported. C2 correctness PROVEN bit-exact on HW (stock zlib + raw deflate of FP8_E5M2 KV). Throughput (doca_bench): engine ceiling ~170-175 Gib/s (~188 Gbps), pipelining-required (8x over single-shot), chunk-gated (256KB->141Gbps, 1MB->180, 2MB->188; 4KB hopeless). Red lines 1+2+3 CLEAR for >=256KB chunks at <=100Gbps. Design constraint: gate must aggregate KV to >=256KB. Ceiling: ~188Gbps egress does NOT scale w/ parallel contexts (4ctx=4x42.6=170Gib/s=1ctx) BUT likely a PCIe-x8 artifact NOT the engine: lspci shows BF3 link Gen5 x8 (downgraded from x16), egress 23.5GB/s ~87% of practical x8/dir -> host PCIe write-back ~saturated. CORRECTED over-claim: it's a system ceiling under host-mem+x8-slot, not proven silicon; on x16 or DPU-local mem could be ~2x (~376Gbps). RESOLVE via host-vs-DPU-memory test (skipped; needs DPU ARM access — rshim present, tmfifo/SSH unconfigured). Scope holds for THIS setup: compression pays when path-bottleneck-BW < ~188Gbps; profitable region FP8_E5M2 x BW<~188Gbps(maybe x8-limited) x chunk>=256KB. Peer bf3_client=10.154.163.112 for M4 RDMA.
m3_status: YELLOW  # experiments/m3/ (46 unit tests, pure-stdlib analytical core). Two-layer (user-approved): analytical frontier + LLMServingSim cross-check. LAYER 1 (go/no-go): reuses M1 profitability.py, decompress chunk-coupled D=alpha*D_egress(S) (egress->input units reconciliation). For measured envelope (FP8_E5M2 alpha=0.732, 2MB chunk) profitable iff B < B_crit: 25Gbps band->5.9, 50->10.5, 100Gbps FPGA->17.2 Gbps. HARD CEILING: even free/infinite compress caps region at B<(1-alpha)*D_egress~=0.27*188~=50Gbps -> realistic-KV compression STRUCTURALLY cannot pay at mainstream 100-400Gbps (alpha~0.73 => only 27% wire saving). Software compress (17MB/s) never pays -> asymmetric FPGA mandatory. VERDICT YELLOW: real but narrow bandwidth-limited region (cross-AZ/oversubscribed/WAN-ish). LAYER 2 (cross-check, PASS): deployed LLMServingSim v1.1.0 (myDevbox ~/autoResearch/LLMServingSim, PD disaggregation, ASTRA-Sim analytical). Llama-3.1-8B bf16, 2048-tok prompt, single_node_pd, --no-enable-prefix-caching (PD+prefix-cache crashes this branch). TTFT(link_bw): bw<=8GB/s clean 1/bw law R2=1.0 -> PD KV transfer is bandwidth-limited (~bytes/link_bw), validates frontier physics; bw>=16 floors at compute ~83ms; TPOT invariant. Implied payload 750MB=2.79x minimal KV (sim moves activations alongside KV; scaling law unaffected). Caveats: bf16 only (no FP8 sim profile) validates transfer MODEL not FP8 TTFT; M2 ~188Gbps ceiling maybe x8-limited so window could be ~2x wider; full raw/always/static/gate TTFT injection deferred (needs Chakra/ASTRA instrumentation + FP8 profile + long-ctx workloads). C3=YELLOW (narrowed regime). Report: experiments/m3/M3_REPORT.md; contract: refine-logs/EVALUATION_CONTRACT_M3.md.
m6_status: PLANNED_BLOCKED  # supplementary GPU-cost baseline (EXPERIMENT_PLAN Block 7, tracker R013). Measures the GPU tax of GPU-side KV compression (UCCL p2p + DietGPU ANS; opt nvCOMP) to quantify the "GPU-side codecs compete for GPU resources" differentiator. Metrics: SM%/HBM-BW% of compress kernels + TTFT/TPOT interference of co-located vLLM. DietGPU=fp16/bf16/fp32 only (NO FP8 -> can't target WR-ZipGuard's profitable dtype; bf16 KV ~0.79 ratio). BLOCKED on GPU access (myDevbox no GPU, A100 unavail); single-GPU loopback fallback. Off critical path. Full plan in Obsidian 007-ideas/WR-ZipGuard/Experiment Plan — GPU Cost...(M6).md.
m4a_pre_status: YELLOW_HOST_CPU_LEG_DONE_ARM_BLOCKED  # experiments/m4a_pre/ (2026-07-06, tracker R016, contract EVALUATION_CONTRACT_T_INVERSE.md pre-registered first). HW NOTE: bf3_client DOWN (user) AND BF3 card ABSENT from bf3_server PCIe bus since 2026-07-01 reboot (zero 15b3 devices, rescan ineffective, rshim has no backend) -> "boot into DPU mode" impossible until card re-enumerates (host reboot / BMC power-cycle / DC-ops; user decision). Host-CPU leg (no card needed, 192-core x86): C tinv_bench (fresh impl, bit-exact vs 6 Python golden pairs on mac+server): bf16 chan_bt^-1 2.04 GB/s 1T @2MiB (2T->R_f 3.75, 12T->R_e 23.5, linear to 16T=32.3), fp8 chan^-1 1.39 GB/s 1T (3T->R_f; 16T=22.2). T_xform FOLDED into m1/profitability.py (*_with_transform, +8 TDD tests, 120 pass). B_crit scenarios (tinv_frontier.json): fp8 raw 16.2 Gbps vs chan+8T-inverse 10.7 / 16T 13.4 -> CHAN DOES NOT PAY vs raw fp8 on host-CPU inverse (alpha win < inverse tax; pays only if inverse ~free: ARM/engine/FPGA = measured M4a/M4b design requirement). bf16 (no raw fallback): FPGA-sender+8T 12.2 Gbps (-30% vs 17.9 free); SW sender collapses all (<=3.9). Gate must price T_inv per-WR (closed forms + measured X_inv now exist)
lit_refresh_2026_07: DONE  # 2026-07-06, three parallel web sweeps + primary-source verification; full table LITERATURE_REVIEW.md Section 1c; positioning folded into research_contract.md (Current Evidence Status + Key Decisions). HEADLINES: (1) TRACE (2509.03377, IEEE TC): LOSSLESS bf16 KV alpha~0.53 via channel-major bit-plane layout in CUSTOM CXL-controller silicon -> top threat/opportunity; its transform is a pure permutation so it may port to our single-standard-deflate-stream/BF3 constraint -> M1.6 tests this. (2) Custom-decoder ceilings: UCCL-Zip v2 ANS bf16 0.64/e5m2 0.70/e4m3 0.77 (we pay +0.06/+0.03/+0.05 for commodity decode); SplitZip v3 bf16 alpha~0.755 + e5m2 0.877 = WORSE than our 0.70/0.73 (positioning gift). (3) ECF8 (2510.02676) provides THEORY (alpha-stable SGD -> low exponent entropy) for our exponent-plane floors. (4) Gate still unclaimed: NetSenseML = congestion-reactive lossy training gradients; CIDR'26 Waiting-to-Decompress = LLM-as-codec storage economics; neither is per-transfer bit-exact measured-frontier gating. (5) BF4 still NO hw compress engine (recheck at DOCA 3.x GA); no production lossless KV compression in vLLM/SGLang/Mooncake/NIXL/LMCache as of 2026-07 — PRECISE FORM (2nd verification pass same day, prompted by "haven't GPU-codec papers been merged?"): merged = lossy only (LMCache's sole codec is CacheGen quant+entropy coding; vLLM native = FP8 KV quant; SGLang HiCache = tiering, no codec; KVTC->Dynamo KVBM announced 2026-03 not shipped, lossy overall); lossless GPU codecs (DietGPU/UCCL-Zip/SplitZip/ZipNN/TRACE) all unmerged research. Claim phrasing: "what ships is lossy; lossless remains unshipped". Watch item: KVTC/nvCOMP-deflate landing in Dynamo KVBM would legitimize deflate-on-KV (helps narrative, storage-side lossy, doesn't touch our transfer-side bit-exact gate) — re-check before submission. (6) New must-cites: SpectrumKV (lossy PD-transfer), VeriCache (draft+verify lossless-output), KVTC, DFloat11, Unweight, SAC/CXL-SpecKV (CXL substrate).
m1_6_status: RED_preregistered_E5M2_REREGISTERED_MODERN_ARCH_YELLOW  # experiments/m1_6/ (69 unit tests), 2026-07-06, tracker R015. TRACE-inspired channel-major reorder (chan, keyed by head_dim) +/- byte_transpose +/- mod-256 delta, ONE standard deflate stream (BF3-decodable). RED per pre-registered worst-captured-model rule: gpt2 bf16 chan_bt 0.697 (>0.695) / e5m2 chan 0.724 (>0.72) miss YELLOW by 0.002/0.004. BUT models disagree and that IS the finding: on Qwen2.5-7B bf16 0.708->0.671, e5m2 0.732->0.704 = FIRST fp8 transform win. THIRD-MODEL EXTENSION RESOLVED same day (Llama-3.1-8B via NousResearch ungated mirror; rule pre-registered BEFORE capture; 288 rows 0 failures; 4068 rows total): e5m2 chan 0.730->0.699 agrees with Qwen (+-0.005) -> gpt2 confirmed outlier -> RE-REGISTERED NARROW CLAIM: fp8_e5m2 YELLOW on modern-arch (GQA/RoPE) KV, alpha*=worst-of-modern=0.704, BF3-decodable, ANS-parity with UCCL-Zip 0.70. bf16 NOT re-registered: llama 0.690 clears YELLOW individually but 0.019 from qwen > 0.01 bound (gradient 0.697/0.690/0.671 = "gain grows with architecture modernity"); claimable bf16 stays M1.5 byte-transpose 0.705-0.709 (now three-model). Synthetic control zero-gain; delta coding HURTS; llama K<V alpha (reverse of gpt2). TRACE gap priced: portable share of 0.80->0.53 is 0.80->0.671; remaining ~0.14 alpha = their custom silicon. E3: B_crit@100G-FPGA 17.2->19.4/21.1 Gbps; ceiling 50->62; M3 STAYS YELLOW at every alpha (e5m2 0.704 scenario already in alpha_refresh.json: 6.5/11.6/19.0 Gbps). E2 table commodity_decode_cost.json. Report M1_6_REPORT.md; contract EVALUATION_CONTRACT_M1.6.md (third-model resolution section)
next_step: "BLOCKED ON HARDWARE for M4a proper: bf3_client down + bf3_server BF3 card absent from PCIe (user must decide: host reboot / BMC power-cycle / DC-ops). When card returns: (1) DPU-ARM leg of T-inverse (same protocol, experiments/m4a_pre/), (2) M2 host-vs-DPU-memory ceiling test, (3) M4a integrated RDMA prototype. DONE 2026-07-06: M1.6 third-model (e5m2 re-registered YELLOW modern-arch alpha*=0.704); T-inverse host-CPU leg YELLOW (R016); T_xform folded into profitability.py. Software-available meanwhile: gate logic can now price T_inv per-WR (integrate *_with_transform into gate design docs); fp8 saturation fraction; optional 4th model for bf16 gradient. Standing: M4b FPGA compress (software=17MB/s never pays; now ALSO needs the forward transform folded into FPGA — SW sender collapses B_crit to <=3.9Gbps)."
execution_platform: myDevbox  # Debian, py3.13, 64-core, 251GB RAM, no GPU; HF via hf-mirror.com. LLMServingSim deployed at ~/autoResearch/LLMServingSim (venv env/; matplotlib unavailable offline -> M3 figure PNGs deferred, figure-data JSON committed)
active_tasks: []  # no long-running remote jobs; M1/M3 runs are on-demand
last_updated_utc: 2026-07-06T00:00:00Z
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
