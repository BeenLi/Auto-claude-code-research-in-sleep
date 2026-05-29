# Research Proposal: WR-ZipGuard

**Generated**: 2026-05-28T17:11:30Z  
**refine_verdict**: READY  
**refine_overall_score**: 9.0  
**drift_status**: preserved  
**handoff_refresh_status**: passed

## Problem Anchor

- **Bottom-line problem**: Commodity BF3/DPU compression is attractive for LLM cross-machine tensor traffic, but naive offload loses because DOCA setup, buffer staging, unsupported algorithms, and RDMA semantic constraints can exceed the wire-time saved by compression.
- **Must-solve bottleneck**: Make lossless compression useful only where it is profitable, at RDMA work-request or chunk granularity, while preserving ordering, completion, and bit-exact tensor delivery.
- **Non-goals**: lossy compression; NCCL/RDMA driver modification as the primary route; SHARP firmware changes; ASIC tape-out; claiming full raw one-sided GPUDirect transparency before it is measured.
- **Constraints**: 3-month timeline; A100 multi-node RDMA cluster; BF3 DPU servers; DOCA Compress support must be queried per device; SimAI and LLMServingSim are projection tools, not primary proof.
- **Success condition**: A measured BF3/RDMA prototype that reduces exposed transfer latency or wire occupancy for profitable LLM tensor messages, avoids regressions on unprofitable messages through bypass, and produces a calibrated break-even frontier that explains when BF3 compression should not be used.

## Technical Gap

PEDAL shows how to amortize BlueField compression overhead in MPICH, but it relies on MPI message boundaries. NetZIP shows tensor-aware in-network lossless compression can help training, but it assumes custom hardware. SplitZip, KVCodec, and KVServe show that KV compression is valuable, but they operate above the RNIC on GPU/runtime hooks.

The missing system is a commodity BF3 path that turns compression into a **per-message decision** rather than a blanket offload. The research question is not "can BF3 compress a buffer?" The question is:

> Can a BF3 DPU safely decide, at RDMA work-request or transfer-chunk granularity, whether bit-exact compression will save more wire time than it exposes in sampling, staging, compression, metadata, decompression, and copy-out cost?

## Method Thesis

WR-ZipGuard is a BF3/RDMA compression gate that combines a measured break-even frontier, cheap tensor-aware sampling, persistent DOCA contexts, pre-registered staging buffers, and bypass-on-risk semantics to compress only profitable LLM tensor chunks while preserving per-QP ordering and bit-exact delivery.

## Contribution Focus

- **Dominant contribution**: A work-request-granular profitability gate for commodity BF3 compression on LLM tensor traffic, including the measured cost model and a prototype RDMA transfer path.
- **Supporting contribution**: A BF3 LLM tensor compression atlas that maps break-even regions across dtype, tensor phase, chunk size, link rate, buffer location, and codec path.
- **Explicit non-contributions**: a new compression algorithm; lossy KV quantization; SHARP compressed-domain collectives; a production NCCL plugin; an ASIC design.

## Proposed Method

### Complexity Budget

- **Frozen / reused substrate**: BF3 DOCA Compress, verbs/UCX-style RDMA microbenchmarks, existing LLM tensor traces, SimAI, LLMServingSim, raw RDMA/NCCL baselines.
- **New mechanisms**: the break-even frontier builder and the WR-ZipGuard gate.
- **Tempting additions intentionally rejected**: custom FPGA codec in the main path, GPU/DPU multi-codec router, SHARP integration, lossy quantization.

### System Overview

1. **Frontier builder** measures raw transfer, DOCA/C-engine paths, SoC software paths, and fallback paths over LLM tensor chunks.
2. **Sender gate** samples a chunk, queries the frontier, estimates effective link bandwidth and DPU queue state, and chooses `raw` or `compressed`.
3. **Metadata envelope** records chunk id, sequence, codec, raw length, compressed length, checksum, destination offset, and fallback status.
4. **Receiver restore path** uses a staging buffer for compressed chunks, decompresses bit-exactly, and writes the restored tensor bytes to the target registered region.
5. **Bypass-on-risk** sends raw bytes when the lower-confidence expected gain is not positive.

The first implementation targets user-level RDMA send/receive, UCX-style transfer hooks, and vLLM/Mooncake-like KV-transfer boundaries. Raw one-sided GPUDirect writes are measured as a harder semantic case; the proposal does not assume they are already solved.

### Core Mechanism

The gate estimates:

```text
gain = raw_bytes / effective_bw
       - (compressed_bytes / effective_bw
          + T_sample
          + T_stage
          + T_compress
          + T_metadata
          + T_decompress
          + T_copyout)
```

Compression is allowed only when a conservative lower bound on `gain` exceeds a safety margin. The predictor uses:

- chunk size and alignment;
- dtype and tensor phase (`KV`, `activation`, `gradient`, `optimizer`);
- cheap sample compressibility or entropy proxy;
- measured DOCA path state: cold/warm context, pre-registered buffer availability, queue depth;
- effective link bandwidth and contention level;
- codec capability matrix from BF3 runtime queries.

If compression expands data, fails, or cannot meet the frontier threshold, the chunk is sent raw. Per-QP sequence numbers preserve in-order delivery. Checksums and bitwise comparisons verify correctness during development.

### Why This Is Small Enough

The proposal reuses BF3 hardware and existing codecs. It does not build a new codec. Its novelty is the measured decision boundary and RDMA-safe execution path. That keeps the paper focused: **when can commodity BF3 compression be used safely for LLM tensor communication, and how do we avoid the negative cases that prior characterization warns about?**

## Handoff Fields

- **core_baseline**: `IB1`: PEDAL-style static DPU compression plus raw RDMA/NCCL transfer; verified by literature review.
- **baseline_artifact_readiness**: `score=1; status=paper_only; verification=verified; evidence=PEDAL DOI and raw RDMA/NCCL tools; adapter_notes=PEDAL behavior reimplemented as static-compress baseline if no artifact is available`.
- **canon_mapping**: `platform=[EC-P1,EC-P2]; workload=[EC-W4,EC-W5,EC-W3]`.
- **metrics**: exposed transfer latency, p99 latency, bytes-on-wire, compression ratio, false-positive compression rate, DPU CPU utilization, bitwise correctness, TTFT/step-time impact.
- **target_validation_style**: prototype_measurement.
- **evaluation_target_clarity**: clear.
- **evaluation_feasibility_score**: 4.
- **evaluation_feasibility_breakdown**: `platform_workload_access=ready; baseline_artifact_readiness=score=1; evaluation_adapter_cost=moderate; first_signal_runtime=1-2_days`.
- **negative_evidence_response**: `addresses: NE-1 (persistent contexts and pre-registered buffers reduce fixed overhead); addresses: NE-2 (sampled profitability gate rejects raw tensors that generic codecs cannot compress); addresses: NE-3 (runtime bandwidth and queue-state aware gating avoids static-profile harm)`.
- **handoff_to_workflow_1_5**: ready.

## Must-Run Validation

1. BF3 compression frontier on LLM tensor chunks.
2. RDMA WR/chunk microbench with raw, always-compress, static-threshold, and WR-ZipGuard policies.
3. KV-transfer or activation-transfer end-to-end harness anchored to measured microbench points.
4. Ablations proving persistent context, pre-registered buffers, sampling, and bypass each matter.

## Main Risks

- **PEDAL delta unclear**: must show WR/chunk granularity, tensor-aware sampling, and risk-calibrated gating each add value beyond static MPI-style compression.
- **Algorithm support narrower than expected**: capability queries become part of the contribution; unsupported LZ4/zlib compression paths are treated as SoC/software or excluded.
- **GPUDirect one-sided path too hard**: keep the first prototype at transfer-library/proxy boundaries and report one-sided GPUDirect as a separate measured limitation.
- **No tensor phase wins**: if no BF3-supported path is profitable, pivot to a strong negative-result atlas with clear design guidance, but do not claim a ready system speedup.
