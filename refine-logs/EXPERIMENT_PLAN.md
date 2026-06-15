# Experiment Plan — WR-ZipGuard (v2, asymmetric + simulate-first)

**Problem**: BF3 is hardware-decompress-only, so sender-side commodity-hardware compression does not
exist; and naive compression of LLM KV traffic loses because staging, init, and uncompressible
tensors can dominate saved wire time.
**Method Thesis**: WR-ZipGuard uses a per-work-request profitability gate plus asymmetric execution
(standard-format compress on the sender, **commodity BF3 hardware decompress** on the receiver),
validated simulate-first under measured parameters before any FPGA build.
**Date**: 2026-05-29

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|---|---|---|---|
| C1: Per-WR gate captures profitable KV compression while never regressing unprofitable chunks | Prior work shows naive compression loses; a useful system rejects bad cases | Gate beats both always-raw and always-compress on held-out KV chunks, with no p99 regression on unprofitable chunks, bit-exact | B4, B5, B6 |
| C2: A standard-format compressor is decompressed correctly + usefully by commodity BF3 hardware | This commodity-decompress path is the structural novelty over NetZIP | BF3 hardware decompresses software- and FPGA-produced deflate/LZ4 streams bit-exactly at measured throughput sufficient to not bottleneck KV transfer | B2, B4, B5 |
| C3: A realistic-parameter simulation identifies the profitable KV-transfer region, matched by real hardware | Prevents assumed-gain simulator-only claims | LLMServingSim sweep under measured ratios + measured BF3 decompress shows a bandwidth-limited profitable region; M4b prototype within 15% of projection | B1, B3, B5 |

## Paper Storyline

- **Main paper must prove**: commodity-DPU-decompressible KV compression is a *conditional* primitive,
  and WR-ZipGuard's gate + asymmetric execution makes the condition explicit and safe to use.
- **Appendix can support**: extra tensor phases, training workload (SimAI), additional codecs,
  larger LLMServingSim sweeps.
- **Experiments intentionally cut**: sender-side BF3 hardware compression (does not exist), SHARP
  integration, full NCCL plugin, lossy KV methods, ASIC tape-out.

## Evaluation Inputs

- **core_baseline**: raw RDMA/NCCL KV transfer; static always-compress; static size threshold;
  SplitZip/KVServe/KVCodec as contextual baselines when reproducible.
- **baseline_artifact_readiness**: `score=1; status=paper_only; verification=verified; evidence=SplitZip/KVServe/KVCodec arXiv + raw RDMA/NCCL tools; adapter_notes=reimplement static-compress and size-threshold baselines directly`.
- **canon_mapping**: `platform=[EC-P1,EC-P2,EC-P3]; workload=[EC-W3,EC-W4,EC-W5] primary; EC-W1,EC-W2 supplementary`.
- **metrics**: TTFT, TPOT, exposed transfer latency, p99 latency, bytes-on-wire, compression ratio,
  false-positive compression rate, BF3 decompress throughput, bitwise correctness.
- **negative_evidence_response**: `addresses NE-1 (persistent contexts + pre-registered buffers cut fixed overhead); addresses NE-2 (sampled gate rejects uncompressible KV tensors); addresses NE-3 (runtime bandwidth/queue-aware gate avoids static-profile harm)`.
- **target_validation_style**: simulation_gate_then_prototype_measurement.
- **evaluation_target_clarity**: clear.
- **evaluation_feasibility_score**: 3 (downgraded from v1's 4 — sender-side hardware compress must be
  custom-built; first speedup requires FPGA in M4b).
- **evaluation_feasibility_breakdown**:
  - **platform_workload_access**: BF3 SmartNIC ready (decompress); FPGA SmartNIC available for M4b;
    A100 RDMA cluster listed.
  - **baseline_artifact_readiness**: score=1; KV baselines paper-only; raw RDMA/NCCL reproducible.
  - **evaluation_adapter_cost**: moderate for M1–M4a; high for M4b (FPGA RTL).
  - **first_signal_runtime**: hours for M1; 1–2 days for M2; days for M3.
- **simulator_caveat**: SimAI/LLMServingSim do not model a compression engine natively; a
  latency+byte-reduction model is injected on the transfer path. Simulation states *potential*
  benefit; M4b states *realized* benefit.

## Experiment Blocks

### Block 1: Real Tensor Compressibility Corpus  (M1)

- **Claim tested**: C3 (input + go/no-go).
- **Why this block exists**: The cheapest kill/green-light signal — if real KV/FP8 tensors do not
  compress, no hardware can save the idea.
- **Workload / configuration**: captured or generated BF16/FP8 KV blocks (primary), plus
  gradient/activation/optimizer chunks (supplementary); sizes 4KB–64MB; per-phase and per-dtype.
- **Compared systems**: deflate, LZ4, zstd at representative levels (software, no hardware needed).
- **Metrics and why decisive**: compression-ratio distribution per phase/dtype decides whether a
  profitable region is even possible.
- **Success criterion**: at least one phase exceeds a profitability-relevant ratio threshold (set
  from the break-even math in Block 3); otherwise stop or pivot to negative-result paper.
- **Table / figure target**: Figure 1 ratio distributions; Table 1 per-phase ratios.
- **Priority**: MUST-RUN (FIRST — this is "Step 1").

### Block 2: BF3 Hardware Decompress Microbenchmark  (M2)

- **Claim tested**: C2.
- **Why this block exists**: The asymmetric design rests on BF3 decompress being correct and fast
  enough not to bottleneck KV transfer.
- **Workload / configuration**: deflate and LZ4 block/stream decompress on BF3; host vs DPU memory;
  cold vs warm DOCA context; pre-registered vs on-demand buffers; chunk-size sweep.
- **Compared systems**: BF3 hardware decompress vs host software decompress.
- **Metrics and why decisive**: decompress throughput, exposed latency, staging cost, correctness.
- **Setup details**: query device capabilities first (`doca_compress_cap_task_decompress_*`); record
  firmware, DOCA version, queue depth, buffer location.
- **Success criterion**: BF3 decompress sustains throughput that does not bottleneck target KV
  transfer rates; bit-exact on software-produced standard streams.
- **Go/No-Go rules** (added 2026-06-12 after the Codex "staging shim" attack; rationale in the
  novelty trace and research_contract Key Decisions). Definitions: `D_eff` = warm-path effective
  decompress throughput, output-side bytes, **including staging + copy-out**, at max queue
  depth/engine parallelism; `B_t` = target link bandwidth tier; `T_fixed` = warm per-task fixed
  overhead (persistent DOCA context + pre-registered buffer pool). Steady-state delivery of the
  compressed path is `min(B_t/α, D_eff)` vs `B_t` raw, hence three red lines:
  - **Red line 1 (throughput, ratio-independent)**: `D_eff <= B_t` at every bandwidth tier where
    M1 ratios are profitable → no steady-state gain at any compression ratio.
  - **Red line 2 (non-amortizable fixed cost)**: warm `T_fixed` such that `B_t * T_fixed / S`
    exhausts the alpha budget for all realistic KV chunks `S <= 16MB` (guide: at `B_t = 12.5 GB/s`,
    `S = 1MB`, `T_fixed = 50us` burns 0.6 of the alpha ceiling — dead; `20us` burns 0.25 — viable),
    with copy-out not eliminable (DOCA cannot decompress directly into the registered region).
  - **Red line 3 (no pipelining)**: decompress of chunk N cannot overlap arrival of chunk N+1
    (e.g., task submission serializes per QP), so exposed latency breaks p99/TTFT even when
    throughput suffices.
  - **GREEN**: `D_eff >= 2*B_t` at a tier where M1 shows profitable ratios, warm `T_fixed <= ~20us`,
    overlap works, bit-exact → proceed to M3 with the asymmetric positioning intact.
  - **YELLOW**: `B_t < D_eff < 2*B_t`, or amortization only at chunks >= 16MB, or partial overlap →
    proceed to M3 but narrow the claimed bandwidth regime (e.g., 25–50 Gbps cross-AZ/oversubscribed
    fabrics) and flag the narrow profitability window.
  - **RED**: any red line still holds after engineering mitigations (persistent context, buffer
    pool, multi-engine parallelism, pipelining) → do **not** pivot to NetZIP-style dual-end inline
    hardware (incremental novelty, contradicts the simulate-first cost structure); pivot to the
    profitability-atlas / negative-result + hardware-implications paper ("what a commodity DPU must
    provide for KV compression to pay"), reusing M1/M2 data on the same narrative line.
- **Table / figure target**: Figure 2 decompress throughput vs chunk size.
- **Priority**: MUST-RUN.

### Block 3: LLMServingSim Profitability Sweep  (M3 — project-wide gate)

- **Claim tested**: C3.
- **Why this block exists**: Proves a bandwidth-limited profitable region exists *before* committing
  to FPGA RTL.
- **Workload / configuration**: vLLM/Mooncake-like prefill→decode KV transfer; long-context
  32K–128K traces; link-rate sweep (bandwidth-limited to bandwidth-rich); SimAI training collectives
  as supplementary axis.
- **Injected envelope (all from real sources)**: compression ratio from B1, BF3 decompress
  throughput from B2, compress-throughput band from NetZIP + FPGA deflate IP datasheets.
- **Compared systems**: raw, always-compress, static size threshold, WR-ZipGuard gate policy.
- **Metrics and why decisive**: projected TTFT/TPOT, bytes-on-wire, sensitivity to link rate;
  identifies the profitable region and the bypass region.
- **Success criterion**: a bandwidth-limited regime where the gate policy improves end-to-end metric
  and rejects the no-gain regime; otherwise pivot to negative-result design-space paper.
- **Failure interpretation**: no profitable region under realistic parameters → the publishable
  result is "commodity-DPU-decompressible KV compression is not viable under these parameters."
- **Table / figure target**: Figure 3 profitability frontier heatmap; Figure 4 policy comparison.
- **Priority**: MUST-RUN.

### Block 4: Software-Compress + BF3-Decompress Prototype  (M4a)

- **Claim tested**: C1, C2 (correctness).
- **Why this block exists**: Proves the mechanism and the commodity-decompress path on real machines
  in weeks, without gating on FPGA RTL.
- **Workload / configuration**: 2–4 node KV transfer; software deflate/LZ4 compress on sender; BF3
  hardware decompress on receiver; per-chunk metadata envelope; QP/message-size sweep.
- **Compared systems**: raw RDMA, always-compress, static threshold, WR-ZipGuard gate.
- **Metrics and why decisive**: bit-exact correctness, in-situ BF3 decompress throughput, gate
  decision overhead, receiver staging/writeback cost, p99 on rejected chunks.
- **Expected outcome (honest)**: software compress cannot saturate line rate, so the gate correctly
  bypasses most chunks — this block yields a *correctness/safety* result, not a speedup result.
- **Success criterion**: end-to-end pipeline is bit-exact and order-preserving; BF3 decompresses the
  standard stream correctly; gate never regresses p99 vs raw on bypassed chunks.
- **Table / figure target**: Figure 5 correctness + decompress-path latency.
- **Priority**: MUST-RUN.

### Block 5: FPGA-Compressor End-to-End Speedup  (M4b — headline; absorbs old M5 realizability)

- **Claim tested**: C1, C3 (headline).
- **Why this block exists**: Provides the measured end-to-end KV speedup the paper headlines on, and
  demonstrates FPGA-compressor realizability directly.
- **Workload / configuration**: same pipeline as B4 with the FPGA compressor swapped in on the sender
  SmartNIC; bandwidth-limited KV regimes from B3.
- **Compared systems**: raw, static compression, WR-ZipGuard; report FPGA throughput/area/timing.
- **Metrics and why decisive**: measured TTFT/transfer-time improvement in profitable regimes;
  projection error vs B3; FPGA throughput/area/timing.
- **Success criterion**: real speedup in at least one bandwidth-limited regime; lands within 15% of
  the B3 projection; FPGA sustains compress throughput in the assumed band.
- **Failure interpretation**: if FPGA cannot hit line rate or speedup is absent, fall back to the
  B3+B4 result (simulated benefit + real correctness) and design guidance.
- **Table / figure target**: Figure 6 measured end-to-end speedup; Table 2 FPGA cost.
- **Priority**: MUST-RUN (contingent on B3 green).

### Block 6: Novelty Isolation Ablations  (M5)

- **Claim tested**: C1, C2.
- **Why this block exists**: Separates the contribution from static thresholds and from "just use a
  fast codec."
- **Workload / configuration**: held-out KV chunks and microbench settings from B1–B5.
- **Compared systems**: full WR-ZipGuard, no sampling, no persistent DOCA context, no pre-registered
  buffers, no bypass, static size threshold.
- **Metrics and why decisive**: false-positive/negative rate, p99 latency, throughput.
- **Success criterion**: removing bypass or sampling causes clear regressions; a plain threshold does
  not match the gate.
- **Failure interpretation**: if a simple threshold matches WR-ZipGuard, simplify/reframe the method.
- **Table / figure target**: Table 3 ablations.
- **Priority**: MUST-RUN.

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|---|---|---|---|---|---|
| M1 | Real tensor compressibility | Block 1 | some phase exceeds ratio threshold | hours–1 day | KV/FP8 incompressible |
| M2 | BF3 decompress microbench | Block 2 | decompress not a bottleneck, bit-exact | 1–2 days | DOCA setup drift |
| M3 | Profitability sweep | Block 3 | bandwidth-limited profitable region exists | 3–5 days | no profitable region |
| M4a | Software prototype | Block 4 | mechanism correct + commodity decompress works | 1–2 weeks | staging/metadata overhead |
| M4b | FPGA prototype | Block 5 | measured speedup within 15% of projection | 4–12 weeks | FPGA RTL / line-rate |
| M5 | Ablations | Block 6 | every component matters | 3–5 days | weak component |

## Validation Budget

- **First credible result (M1–M3 + M4a)**: 3–5 weeks.
- **Paper-ready package (through M4b + M5)**: add 4–12 weeks depending on FPGA RTL.
- **Trace / workload prep**: KV tensor generator/capture from vLLM/Mooncake-like path; optional
  training tensors for the supplementary axis.
- **Platform setup**: BF3 DOCA SDK (decompress), RDMA verbs/UCX tools, FPGA SmartNIC toolchain for
  M4b, A100 GPUDirect checks, link-rate shaping if possible.
- **Biggest bottleneck**: FPGA compressor RTL (M4b) — kept off the critical path via M4a + M3.

## Risks and Mitigations

- **Risk**: KV/FP8 tensors do not compress losslessly.
  **Mitigation**: B1 measures this first; negative result becomes a design-space paper.
- **Risk**: no profitable region in simulation.
  **Mitigation**: B3 is the go/no-go; pivot to negative-result frontier before any FPGA spend.
- **Risk**: software compress too slow to show speedup.
  **Mitigation**: expected — M4a claims correctness only; speedup comes from M4b (FPGA).
- **Risk**: FPGA compressor cannot hit line rate.
  **Mitigation**: B3 envelope uses conservative FPGA throughput; fall back to B3+B4 result.
- **Risk**: reviewers see only a heuristic.
  **Mitigation**: calibrated frontier, conservative gain rule, held-out prediction error, ablations.

## Final Checklist

- [ ] Main paper tables are covered
- [ ] Novelty is isolated (gate + asymmetric execution, not a new codec)
- [ ] Simplicity is defended
- [ ] Simulation parameters are all traced to measured sources (no assumed gains)
- [ ] Every experiment block references the Evaluation Inputs it depends on
- [ ] Metrics are inherited from the core baseline or justified as idea-specific
- [ ] M4b (FPGA) is gated on M3 green, never on the critical path to a publishable floor
