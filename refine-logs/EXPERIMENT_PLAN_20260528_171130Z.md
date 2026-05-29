# Experiment Plan

**Problem**: Commodity BF3/DPU compression is not automatically useful for LLM RDMA tensor traffic because staging, initialization, unsupported codecs, and semantic constraints can dominate saved wire time.  
**Method Thesis**: WR-ZipGuard uses a measured BF3 break-even frontier and work-request-granular bypass-on-risk gating to compress only profitable LLM tensor chunks.  
**Date**: 2026-05-28T17:11:30Z

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|---|---|---|---|
| C1: WR-ZipGuard avoids negative compression while capturing positive BF3/RDMA compression opportunities | Prior work shows naive BF3 compression can lose; a useful system must reject bad cases | WR-ZipGuard beats both always-raw and always-compress on held-out tensor chunks, with no p99 regression over raw on unprofitable chunks | B1, B2, B4 |
| C2: Work-request/chunk granularity and tensor-aware sampling are necessary beyond PEDAL-style static compression | Establishes novelty over PEDAL and generic thresholds | Ablations show removing sampling, persistent context, pre-registration, or bypass worsens latency/accuracy of decisions | B2, B4 |
| C3: Measured microbenchmarks can project end-to-end KV or activation transfer impact | Prevents simulator-only claims | End-to-end harness results align with measured RDMA microbench projections within 15% | B3, B5 |

## Paper Storyline

- **Main paper must prove**: BF3 compression is a conditional primitive, and WR-ZipGuard makes the condition explicit enough to use safely.
- **Appendix can support**: extra tensor phases, firmware revisions, additional codecs, and larger SimAI/LLMServingSim sweeps.
- **Experiments intentionally cut**: SHARP integration, full NCCL plugin, custom FPGA codec, lossy KV methods.

## Evaluation Inputs

- **core_baseline**: `IB1`: PEDAL-style static DPU compression plus raw RDMA/NCCL transfer; verified by literature review.
- **baseline_artifact_readiness**: `score=1; status=paper_only; verification=verified; evidence=PEDAL DOI and raw RDMA/NCCL tools; adapter_notes=PEDAL behavior reimplemented as static-compress baseline if no artifact is available`.
- **canon_mapping**: `platform=[EC-P1,EC-P2]; workload=[EC-W4,EC-W5,EC-W3]`.
- **metrics**: exposed transfer latency, p99 latency, bytes-on-wire, compression ratio, false-positive compression rate, DPU CPU utilization, bitwise correctness, TTFT/step-time impact.
- **negative_evidence_response**: `addresses: NE-1 (persistent contexts and pre-registered buffers reduce fixed overhead); addresses: NE-2 (sampled profitability gate rejects raw tensors that generic codecs cannot compress); addresses: NE-3 (runtime bandwidth and queue-state aware gating avoids static-profile harm)`.
- **target_validation_style**: prototype_measurement.
- **evaluation_target_clarity**: clear.
- **evaluation_feasibility_score**: 4.
- **evaluation_feasibility_breakdown**:
  - **platform_workload_access**: ready; BF3 and A100 RDMA cluster are listed resources.
  - **baseline_artifact_readiness**: score=1; PEDAL is verified but artifact status is paper-only/unknown; raw RDMA/NCCL baselines are reproducible.
  - **evaluation_adapter_cost**: moderate; verbs/UCX/KV-transfer proxy plus DOCA harness needed.
  - **first_signal_runtime**: 1-2_days after DOCA and RDMA smoke tests.
- **refine_overall_score**: 9.0.
- **refine_verdict**: READY.
- **drift_status**: preserved.
- **handoff_refresh_status**: passed.

## Experiment Blocks

### Block 1: BF3 Break-Even Frontier

- **Claim tested**: C1.
- **Why this block exists**: Establishes when BF3 compression is profitable and when it should be bypassed.
- **Evaluation Inputs referenced**: EC-P1, EC-W4, baseline readiness, metrics, NE-1, NE-2.
- **Workload / configuration**: captured or generated BF16/FP8 KV, gradients, activations, optimizer-state chunks; sizes 4KB to 64MB; host vs DPU memory; cold vs warm DOCA; pre-registered vs on-demand buffers.
- **Compared systems**: raw copy/transfer, DOCA-supported C-engine path, BF3 ARM software codecs where applicable, static always-compress, static size threshold.
- **Metrics and why decisive**: exposed latency and compression ratio decide break-even; false-positive compression rate shows safety.
- **Setup details**: query device capabilities first; record firmware, DOCA version, codec path, queue depth, and buffer location.
- **Success criterion**: identify at least one profitable region and predict break-even within 10% on held-out chunks, or document a clear negative frontier.
- **Failure interpretation**: if no profitable region exists, the publishable result becomes "commodity BF3 C-engine is not a viable LLM tensor compression primitive under these paths."
- **Table / figure target**: Figure 1 frontier heatmap; Table 1 capability matrix.
- **Priority**: MUST-RUN.

### Block 2: RDMA WR/Chunk Gate Microbenchmark

- **Claim tested**: C1, C2.
- **Why this block exists**: Shows the gate works on real transfer boundaries, not just local compression buffers.
- **Evaluation Inputs referenced**: EC-P1, EC-P2, EC-W5, core baseline, NE-1.
- **Workload / configuration**: verbs/UCX-like send/receive over 2 nodes; QP count sweep; message size sweep; host buffers first, then GPUDirect where feasible.
- **Compared systems**: raw RDMA, always-compress, PEDAL-style static compression, static size threshold, WR-ZipGuard.
- **Metrics and why decisive**: p50/p99 transfer latency, bytes-on-wire, CPU/DPU utilization, completion correctness.
- **Setup details**: per-chunk metadata envelope; receiver staging/decompress/writeback; bitwise compare restored payloads.
- **Success criterion**: WR-ZipGuard dominates always-compress on p99 and is within 1-2% of raw on rejected chunks while improving profitable chunks by at least 10%.
- **Failure interpretation**: if metadata/staging dominates, use Block 1 frontier to explain where BF3 fails and defer system claim.
- **Table / figure target**: Figure 2 latency CDF; Figure 3 policy ablations.
- **Priority**: MUST-RUN.

### Block 3: LLM KV or Activation Transfer Harness

- **Claim tested**: C3.
- **Why this block exists**: Anchors microbench results in an LLM-relevant transfer path.
- **Evaluation Inputs referenced**: EC-P2, EC-P3, EC-W3 or EC-W2, metrics, NE-3.
- **Workload / configuration**: vLLM/Mooncake-like prefill-to-decode KV transfer or pipeline activation transfer on 2-4 A100 nodes; long-context request traces preferred.
- **Compared systems**: raw transfer, static compression, WR-ZipGuard, and SplitZip/KVServe numbers as contextual baselines when reproducible.
- **Metrics and why decisive**: TTFT/TPOT for KV; stage bubble or transfer time for activations; p99 latency and bytes-on-wire.
- **Setup details**: first use generated tensor payloads matched to real shapes; then use captured tensors if available.
- **Success criterion**: end-to-end metric improves in at least one measured bandwidth-limited regime, and policy rejects high-bandwidth/no-gain regimes.
- **Failure interpretation**: if end-to-end impact is small despite microbench gains, paper claims should stay at transfer-layer design guidance.
- **Table / figure target**: Figure 4 end-to-end result.
- **Priority**: MUST-RUN.

### Block 4: Novelty Isolation Ablations

- **Claim tested**: C2.
- **Why this block exists**: Separates the contribution from PEDAL-style amortization or trivial size thresholds.
- **Evaluation Inputs referenced**: all selected handoff fields.
- **Workload / configuration**: held-out tensor chunks and RDMA microbench settings from Blocks 1-2.
- **Compared systems**: full WR-ZipGuard, no sampling, no persistent DOCA context, no pre-registered buffers, no bypass, static size threshold.
- **Metrics and why decisive**: false-positive rate, false-negative rate, p99 latency, throughput.
- **Success criterion**: every core component has a measurable role; removing bypass or sampling causes clear regressions.
- **Failure interpretation**: if a simple threshold matches WR-ZipGuard, novelty drops and the method must be simplified/reframed.
- **Table / figure target**: Table 2 ablations.
- **Priority**: MUST-RUN.

### Block 5: SimAI / LLMServingSim Projection

- **Claim tested**: C3.
- **Why this block exists**: Explores larger model/cluster regimes without overclaiming unmeasured scale.
- **Evaluation Inputs referenced**: EC-P3, EC-P4, EC-W1, EC-W3.
- **Workload / configuration**: SimAI collectives and LLMServingSim KV movement using measured latency/bandwidth frontier from Blocks 1-3.
- **Compared systems**: raw, static compression, WR-ZipGuard policy.
- **Metrics and why decisive**: projected step time, TTFT, throughput, and sensitivity to link rate.
- **Success criterion**: projection error against measured 2-4 node result is below 15% before reporting larger scale.
- **Failure interpretation**: if projection error is high, keep simulations as qualitative sensitivity only.
- **Table / figure target**: appendix or Figure 5 sensitivity.
- **Priority**: NICE-TO-HAVE.

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|---|---|---|---|---|---|
| M0 | BF3/DOCA/RDMA smoke | capability query, raw RDMA ping-pong, DOCA sample | device and codec paths identified | 0.5-1 day | DOCA setup drift |
| M1 | Tensor corpus | generate/capture KV, activations, gradients | chunk shapes match EC-W rows | 1 day | synthetic tensors not representative |
| M2 | Frontier | Block 1 sweeps | profitable region or strong negative frontier found | 2-4 days | no positive region |
| M3 | Gate microbench | Block 2 and Block 4 | WR-ZipGuard beats static policies in held-out cases | 4-7 days | staging overhead dominates |
| M4 | LLM harness | Block 3 | end-to-end metric improves in one regime | 1-2 weeks | integration dominates timeline |
| M5 | Projection | Block 5 | projection calibrated to measured results | 2-3 days | simulator mismatch |

## Validation Budget

- **Total estimated prototype time**: 3-6 weeks for first credible result, 8-10 weeks for paper-ready package.
- **Trace / workload preparation needs**: tensor generator plus optional capture from vLLM/Megatron/Mooncake-like transfer path.
- **Platform setup needs**: BF3 DOCA SDK, RDMA verbs/UCX tools, A100 GPUDirect checks, link-rate shaping if possible.
- **Biggest bottleneck**: transfer-boundary integration and receiver-side restore path.

## Risks and Mitigations

- **Risk**: BF3 C-engine lacks desired compression algorithm support.  
  **Mitigation**: capability matrix is part of Block 1; unsupported paths become SoC/software or excluded baselines.
- **Risk**: staging overhead kills all wins.  
  **Mitigation**: report negative frontier honestly; WR-ZipGuard's bypass should still avoid harm.
- **Risk**: one-sided GPUDirect cannot be transparently compressed.  
  **Mitigation**: first paper targets transfer/proxy boundaries and clearly scopes one-sided as a limitation.
- **Risk**: reviewers see only a heuristic.  
  **Mitigation**: use calibrated frontier, conservative gain rule, held-out prediction error, and component ablations.

## Final Checklist

- [ ] Main paper tables are covered
- [ ] Novelty is isolated
- [ ] Simplicity is defended
- [ ] Platform contribution is justified or explicitly not claimed
- [ ] Every experiment block references the Evaluation Inputs it depends on
- [ ] Metrics are either inherited from the core baseline or added for idea-specific reasons
- [ ] Nice-to-have runs are separated from must-run runs
