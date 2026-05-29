# Research Idea Report

**Direction**: In-RNIC lossless compression engine for LLM cross-machine communication  
**Generated**: 2026-05-28T17:11:30Z  
**Pipeline**: research-lit -> idea-creator -> novelty-check -> research-review -> research-refine-pipeline

## Executive Summary

The selected idea is **WR-ZipGuard**: a BF3/RDMA work-request-granular compression gate that uses a measured break-even frontier, tensor-aware sampling, persistent DOCA contexts, pre-registered buffers, and bypass-on-risk semantics. This is the strongest direction because it avoids the crowded "new KV codec" lane and directly addresses the negative evidence from BlueField characterization: compression hardware is only useful when the system can amortize and avoid its fixed overheads.

The idea is ready for Workflow 1.5 with `refine_verdict=READY`, `refine_overall_score=9.0`, `drift_status=preserved`, and `handoff_refresh_status=passed`.

## Literature Landscape

The literature review found five stable constraints:

- PEDAL is the closest DPU system prior art, but it solves MPI message-boundary compression rather than RDMA work-request or GPUDirect transfer semantics.
- NetZIP is the closest training-side in-network compression prior art, but it assumes custom hardware rather than commodity BF3.
- SplitZip, KVCodec, and KVServe make KV compression a crowded 2026 topic; the DPU/RDMA angle must not be framed as "another KV codec."
- BlueField characterization shows C-engine speed is not enough: initialization, buffer staging, and data movement dominate naive use.
- Current DOCA/BF3 algorithm support must be capability-queried; LZ4/zlib compression acceleration cannot be assumed.

See `idea-stage/LITERATURE_REVIEW.md` for the full Landscape Pack.

## Recommended Ideas

### Idea 1: WR-ZipGuard -- RECOMMENDED

- **Idea shape**: Build a commodity BF3 RDMA work-request or transfer-chunk compression gate. First measure a BF3 break-even frontier for LLM tensor chunks, then integrate a sender-side gate that samples compressibility, checks DPU/link state, and chooses raw or compressed transfer with receiver-side bit-exact restore. The system preserves ordering and correctness through per-chunk metadata, sequencing, and bypass-on-risk.
- **negative_evidence_response**: addresses: NE-1 (persistent contexts and pre-registered buffers reduce fixed overhead); addresses: NE-2 (sampled profitability gate rejects raw tensors that generic codecs cannot compress); addresses: NE-3 (runtime bandwidth and queue-state aware gating avoids static-profile harm)
- **Status**: selected
- **overall_merit_score**: 4 -- clear novelty over PEDAL if work-request granularity, calibrated gating, and tensor-aware sampling all survive ablation; practical relevance is high.
- **evaluation_feasibility_score**: 4
- **Feasibility Breakdown**:
  - *platform_workload_access*: ready -- BF3 and A100 RDMA cluster are listed resources.
  - *baseline_artifact_readiness*: score=1; status=paper_only; verification=verified; evidence=PEDAL plus raw RDMA/NCCL tools; adapter=reimplement static-compress behavior if PEDAL artifact is unavailable.
  - *evaluation_adapter_cost*: moderate -- DOCA harness, verbs/UCX proxy, receiver restore path.
  - *first_signal_runtime*: 1-2_days -- first frontier and RDMA smoke tests after setup.
- **Evaluation handoff**: ready; details in the handoff table.
- **Novelty check**: proceed. Closest prior work is PEDAL, NetZIP, SplitZip, KVServe, and ShadowServe; no verified work was found that combines BF3 work-request-granular compression gating, tensor-aware sampling, and RDMA-safe bypass semantics.
- **Reviewer score**: merit=4/5, feasibility=4/5; external review ranked it first.
- **Next step**: `/experiment-bridge`

### Idea 2: BF3 Tensor Compression Atlas -- BACKUP

- **Idea shape**: Produce a measurement-first BF3 break-even frontier for BF16/FP8 KV, gradients, activations, and optimizer-state chunks across C-engine, SoC software, host software, message sizes, link rates, and buffer locations.
- **negative_evidence_response**: addresses: NE-1 (measures exposed overhead); addresses: NE-2 (tests tensor-specific compressibility rather than assuming it)
- **Status**: backup folded into selected idea Phase 0
- **overall_merit_score**: 3 -- useful and highly feasible, but weak as a standalone top-venue paper without a system mechanism.
- **evaluation_feasibility_score**: 5
- **Feasibility Breakdown**:
  - *platform_workload_access*: ready.
  - *baseline_artifact_readiness*: score=2; status=config_reproducible; verification=verified; evidence=DOCA and raw transfer tools.
  - *evaluation_adapter_cost*: small.
  - *first_signal_runtime*: hours.
- **Evaluation handoff**: designed_not_run as standalone; absorbed into WR-ZipGuard.
- **Main blocker**: insufficient standalone contribution.

### Idea 3: Hybrid GPU/DPU KV Compression Selector -- BACKUP

- **Idea shape**: Build an online selector that chooses raw transfer, GPU SplitZip/KVCodec, BF3 DPU compression, or bypass based on SLO, bandwidth, GPU contention, DPU queue state, and KV tensor shape.
- **negative_evidence_response**: addresses: NE-3 (dynamic policy); evades: NE-1 (uses BF3 only when frontier says it is profitable)
- **Status**: backup
- **overall_merit_score**: 4 -- strong systems problem and timely, but too broad until WR-ZipGuard establishes the BF3 leg.
- **evaluation_feasibility_score**: 2
- **Feasibility Breakdown**:
  - *platform_workload_access*: nontrivial -- needs reproducible GPU codec baselines and DPU path.
  - *baseline_artifact_readiness*: score=0; status=unknown; verification=verified papers but artifacts uncertain.
  - *evaluation_adapter_cost*: major.
  - *first_signal_runtime*: weeks.
- **Evaluation handoff**: designed_not_run.
- **Main blocker**: baseline_artifact_readiness and scope explosion.

### Idea 4: Activation-First DPU Compression for Pipeline Parallelism -- BACKUP

- **Idea shape**: Focus on point-to-point pipeline activation messages instead of KV transfer or all-reduce. Use pipeline stage boundaries as easier compression units and evaluate on SimAI plus a small real cluster.
- **negative_evidence_response**: conflicts: NE-2 (would retest whether activation regimes exist that escape raw-codec failure)
- **Status**: backup
- **overall_merit_score**: 3 -- cleaner semantics than collectives, but likely weaker impact and high risk of poor lossless compressibility.
- **evaluation_feasibility_score**: 3
- **Feasibility Breakdown**:
  - *platform_workload_access*: near_ready.
  - *baseline_artifact_readiness*: score=1; status=paper_only; verification=verified.
  - *evaluation_adapter_cost*: major -- PP harness integration is nontrivial.
  - *first_signal_runtime*: multi_day.
- **Evaluation handoff**: needs_canon_clarification.
- **Main blocker**: uncertain activation compressibility and workload integration.

## Deferred Ideas

| Idea | Reason deferred | Required clarification or platform path |
|---|---|---|
| GPU/DPU KV router | Too many strong 2026 KV baselines to reproduce in 3 months | First establish BF3 path with WR-ZipGuard, then compare against SplitZip/KVServe |
| Activation-first PP compression | May be negative if BF16 activations do not compress losslessly | Use WR-ZipGuard frontier to find a profitable activation regime first |
| FPGA/ASIC tensor codec | NetZIP/SplitZip already cover much of the custom codec story | Only revisit if BF3-supported paths are conclusively insufficient and FPGA resources are available |
| DPU prefix-cache fetch system | ShadowServe already occupies SmartNIC prefix-cache offload | Needs a clear BF3 compression-specific advantage over ShadowServe and KVCodec |

## Eliminated Ideas

| Idea | Category | Reason | Revisit condition |
|---|---|---|---|
| SHARP-compatible lossless compressed collectives | no_credible_evaluation_path | SHARP firmware is closed and compressed-domain reductions are semantically hard for exact arithmetic | NVIDIA collaboration plus a concrete compressed-domain reduce primitive |
| Generic "compress every RDMA tensor on BF3" | refuted_by_negative_evidence | NE-1 and NE-2 show naive offload and raw generic codecs often lose | Only revisit through a measured gate such as WR-ZipGuard |
| Lossy KV or gradient compression on DPU | outside_scope | Explicit non-goal; strong existing lossy literature | User changes correctness requirement |

## Evaluation Handoff Summary

| Idea | overall_merit_score | evaluation_feasibility_score | evaluation_feasibility_breakdown | baseline_artifact_readiness | core_baseline | canon_mapping | metrics | target_validation_style | evaluation_target_clarity | baseline_verification_delta | negative_evidence_response | refine_overall_score | refine_verdict | drift_status | handoff_refresh_status | handoff_to_workflow_1_5 | main_blocker |
|---|---:|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|---|---|
| WR-ZipGuard | 4 | 4 -- ready platform, moderate adapter, 1-2 day first signal | platform_workload_access=ready; evaluation_adapter_cost=moderate; first_signal_runtime=1-2_days | score=1; status=paper_only; verification=verified; evidence=PEDAL DOI plus raw RDMA/NCCL tools; adapter=static-compress reimplementation if needed | IB1: PEDAL-style static DPU compression plus raw RDMA/NCCL transfer | platform=[EC-P1,EC-P2]; workload=[EC-W4,EC-W5,EC-W3] | exposed transfer latency, p99 latency, bytes-on-wire, compression ratio, false-positive compression rate, bitwise correctness, TTFT or step-time impact | prototype_measurement | clear | verified_by_research_lit | addresses: NE-1 persistent contexts and pre-registered buffers; addresses: NE-2 sampled gate rejects uncompressible tensors; addresses: NE-3 runtime-aware gate avoids static harm | 9.0 | READY | preserved | passed | ready | none |
| BF3 Tensor Compression Atlas | 3 | 5 -- ready measurement path | platform_workload_access=ready; evaluation_adapter_cost=small; first_signal_runtime=hours | score=2; status=config_reproducible; verification=verified; evidence=DOCA and raw tools; adapter=minor | IB2: raw BF3/DOCA microbench | platform=[EC-P1]; workload=[EC-W4] | break-even frontier, exposed latency, compression ratio | prototype_measurement | clear | verified_by_research_lit | addresses: NE-1 measures overhead; addresses: NE-2 measures tensor compressibility | 0 | REVISE | preserved | not_run | designed_not_run | other |
| Hybrid GPU/DPU KV Selector | 4 | 2 -- baselines and adapters too broad | platform_workload_access=nontrivial; evaluation_adapter_cost=major; first_signal_runtime=weeks | score=0; status=unknown; verification=verified; evidence=SplitZip KVCodec KVServe papers; adapter=artifacts uncertain | IB3: SplitZip/KVServe/KVCodec plus raw KV transfer | platform=[EC-P2,EC-P3]; workload=[EC-W3] | TTFT, TPOT, JCT, GPU contention, DPU queue state | prototype_measurement | partial | verified_by_research_lit | addresses: NE-3 dynamic policy; evades: NE-1 BF3 only when profitable | 0 | REVISE | preserved | not_run | designed_not_run | missing_artifact |
| Activation-First DPU Compression | 3 | 3 -- feasible but nontrivial PP harness | platform_workload_access=near_ready; evaluation_adapter_cost=major; first_signal_runtime=multi_day | score=1; status=paper_only; verification=verified; evidence=NetZIP and PP compression papers; adapter=PP harness needed | IB4: raw pipeline activation transfer plus NetZIP-style projection | platform=[EC-P2,EC-P4]; workload=[EC-W2] | activation transfer time, stage bubble, bytes-on-wire | prototype_measurement | partial | verified_by_research_lit | conflicts: NE-2 retest activation-specific regime | 0 | REVISE | preserved | not_run | needs_canon_clarification | unclear_canon_mapping |

## Refined Proposal

- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Research contract: `idea-stage/docs/research_contract.md`
- Handoff schema: `skills/shared-references/idea-handoff-schema.md`

## Next Steps

- [x] Run `tools/workflow1_exit_gate.sh`
- [ ] Enter Workflow 1.5 with `/experiment-bridge`
