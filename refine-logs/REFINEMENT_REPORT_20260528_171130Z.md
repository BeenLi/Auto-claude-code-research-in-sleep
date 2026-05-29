# Refinement Report

**Generated**: 2026-05-28T17:11:30Z  
**Pipeline**: idea-discovery -> research-review -> research-refine-pipeline

## Round History

| Round | Proposal State | Main Criticism | Change Made | Score |
|---|---|---|---|---:|
| 0 | broad DPU/RNIC compression engine | too close to PEDAL, NetZIP, and 2026 KV codecs | narrowed to WR/chunk-granular profitability gate | 7.0 |
| 1 | WR-ZipGuard with atlas | risk of being only a heuristic | added measured frontier, lower-confidence gain rule, and ablation plan | 8.5 |
| 2 | final proposal | one-sided GPUDirect transparency overclaimed | scoped first implementation to transfer/proxy boundaries and made one-sided path a limitation | 9.0 |

## Preserved Problem Anchor

The selected problem remains commodity BF3/DPU lossless compression for LLM cross-machine tensor traffic, under RDMA/GPUDirect constraints. The refinement did not drift into lossy KV compression, new codec design, or SHARP collectives.

## Final Method Thesis

WR-ZipGuard uses a measured BF3 break-even frontier and work-request-granular bypass-on-risk gating to compress only profitable LLM tensor chunks while preserving bit-exact delivery and RDMA transfer semantics at the user-level transfer boundary.

## Handoff Refresh

- `core_baseline`: refreshed to raw RDMA/NCCL plus PEDAL-style static DPU compression.
- `canon_mapping`: refreshed to `platform=[EC-P1,EC-P2]; workload=[EC-W4,EC-W5,EC-W3]`.
- `baseline_artifact_readiness`: `score=1` because PEDAL is verified but artifact status is unknown/paper-only; raw RDMA tools are available.
- `evaluation_feasibility_score`: `4`, because hardware is available, adapter work is moderate, and first-signal microbenchmarks can run within 1-2 days after setup.
- `handoff_to_workflow_1_5`: ready.

## Complexity Intentionally Rejected

- No custom FPGA/ASIC codec in the main result.
- No SHARP firmware or compressed-domain reduction.
- No lossy compression or quality tradeoff.
- No claim that all NCCL one-sided GPUDirect paths are transparent before measurement.

## Remaining Risks

- BF3 C-engine support may be narrower than expected. This is handled by capability-query reporting and fallback paths.
- Compression wins may be sparse. This is handled by treating the frontier and negative regions as publishable design guidance.
- Transfer-library proxy semantics may be seen as weaker than full RNIC transparency. This is handled by measuring what each boundary supports and avoiding driver-level claims.
