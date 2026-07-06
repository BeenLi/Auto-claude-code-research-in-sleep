# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | DOCA capability inventory | BF3 + DOCA Compress | local | supported tasks, max buffer, firmware, DOCA version | MUST | TODO | run before assuming codec support |
| R002 | M0 | raw RDMA baseline | ib_send_bw / custom verbs | 2-node | p50/p99 latency, bandwidth | MUST | TODO | host buffers first |
| R003 | M1 | tensor corpus generation | KV/activation/gradient chunks | synthetic + captured if possible | dtype, size, entropy sample | MUST | TODO | align with EC-W4 |
| R004 | M2 | cold vs warm frontier | DOCA path sweep | train/held-out chunks | compression ratio, exposed latency | MUST | TODO | captures NE-1; feeds red line 2 |
| R005 | M2 | pre-registered buffer sweep | DOCA + buffer pool | train/held-out chunks | staging time, latency | MUST | TODO | tests amortization; feeds red lines 1+2 (measure D_eff incl. copy-out) |
| R005b | M2 | decompress overlap/pipelining probe | DOCA multi-task queue, per-QP serialization check | held-out chunks | overlap ratio, exposed latency hidden % | MUST | TODO | feeds red line 3; tests chunk N decompress overlapping chunk N+1 arrival |
| R006 | M3 | WR gate smoke | WR-ZipGuard prototype | 2-node host buffers | correctness, latency | MUST | TODO | bitwise compare every chunk |
| R007 | M3 | policy comparison | raw/static/always/WR-ZipGuard | held-out chunks | p99, false positives, bytes | MUST | TODO | main method proof |
| R008 | M3 | ablation | no sampling/no bypass/no pool | held-out chunks | p99, false positives | MUST | TODO | novelty isolation |
| R009 | M4 | KV transfer harness | vLLM/Mooncake-like path | 2-4 nodes | TTFT, TPOT, bytes | MUST | TODO | bandwidth-limited regime |
| R010 | M4 | activation transfer harness | pipeline p2p transfer | 2-4 nodes | transfer time, stage bubble | SHOULD | TODO | run if KV path stalls |
| R011 | M5 | SimAI projection | measured frontier model | scale sweep | step time, sensitivity | NICE | TODO | report only if calibrated |
| R012 | M3 | LLMServingSim cross-check | measured frontier model | PD link_bw sweep | TTFT vs 1/link_bw | NICE | DONE | PASS R²=1.0 — sim PD transfer is bandwidth-limited (∝bytes/link_bw), validates frontier physics; bf16 (no FP8 profile), full policy injection deferred |
| R013 | M6 | GPU-cost baseline of GPU-side codec | UCCL p2p + DietGPU (ANS); opt. nvCOMP | bf16 KV ≥2MB + co-located vLLM | SM%/HBM-BW% of compress kernels; TTFT/TPOT interference; ratio | NICE | BLOCKED | needs GPU (myDevbox no GPU, A100 unavail); DietGPU has no FP8; quantifies "GPU-side competes for GPU resources"; single-GPU loopback fallback. Plan in Obsidian M6 note |
| R014 | M1.5 | Float-split / bit-plane preprocessing before deflate | byte_transpose + bitplane vs raw; deflate; BF3 single-stream | synthetic 7B + real gpt2 + Qwen2.5-7B KV | concat α vs raw α; per-plane/exp-plane α; xform throughput; bit-exact | SHOULD | DONE | **GREEN** — cheap byte-transpose rehabilitates **bf16** (default dtype) 0.79→~0.70 on real KV (crosses 0.75); fp8 unaffected (no-op) / hurt (bit-split). Widens dtype set, NOT M3 bandwidth region. 49 unit tests; off-GPU T-inverse + T_xform cost still unmeasured |
| R015 | M1.6 | TRACE-inspired channel-major layout before deflate (lit refresh 2026-07-06) | chan / chan_bt / (+delta) vs byte_transpose; single deflate stream | synthetic 7B control + real gpt2 + Qwen2.5-7B KV | concat α vs M1.5 baseline; per-model agreement; xform throughput; bit-exact | SHOULD | DONE | **RED** per pre-registered worst-model rule (gpt2 bf16 0.697/e5m2 0.724 miss YELLOW by 0.002/0.004) BUT architecture-dependent real gain on Qwen: bf16 0.708→**0.671**, e5m2 0.732→**0.704** (first fp8 transform win; ANS-parity w/ UCCL-Zip). Synthetic control zero-gain (no artifact). M3 stays YELLOW at all new α (B_crit 17.2→≤21.1 Gbps). 69 unit tests. **3rd-model extension RESOLVED same day (Llama-3.1-8B, rule pre-registered before capture): e5m2 0.699 agrees w/ Qwen (±0.005) → RE-REGISTERED fp8_e5m2 YELLOW (modern-arch scope) α\*=0.704; bf16 0.690 in-between (gradient 0.697/0.690/0.671) → no bf16 re-registration** |

## M2 Go/No-Go (decided from R004 + R005 + R005b; full rules in EXPERIMENT_PLAN.md Block 2)

Three red lines (`D_eff` = warm effective decompress throughput incl. staging + copy-out, output-side,
max parallelism; `B_t` = target bandwidth tier):

1. `D_eff <= B_t` at every tier where M1 ratios are profitable (ratio-independent kill).
2. Warm `T_fixed` non-amortizable for chunks <= 16MB and copy-out not eliminable.
3. Decompress cannot overlap next-chunk arrival (per-QP serialization).

- **GREEN** (`D_eff >= 2*B_t`, `T_fixed <= ~20us`, overlap works, bit-exact) → M3, positioning intact.
- **YELLOW** (`B_t < D_eff < 2*B_t` or only >=16MB chunks amortize) → M3 with narrowed bandwidth regime.
- **RED** (any red line after mitigations) → pivot to profitability-atlas / hardware-implications
  paper; do **not** build NetZIP-style dual-end inline hardware.
