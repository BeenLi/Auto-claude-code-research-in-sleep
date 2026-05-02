# Research Contract: Rx Expansion Budgeting for Compressed RDMA

This is the active session-recovery contract and claim boundary for the current idea. Read it after the Pipeline Status in `AGENTS.md` or `CLAUDE.md`. The experiment execution blueprint remains `refine-logs/EXPERIMENT_PLAN.md`.

## Selected Idea

**Rx Expansion Budgeting for Compressed RDMA** adds an expansion-aware receiver-side budgeter for compressed RDMA traffic. The central observation is that NIC/DPU-side lossless compression reduces wire bytes, but the receiver must still materialize the original decompressed bytes into host memory, GPU memory, or staging buffers.

The selected mechanism, EARB, tracks compressed ingress bytes, decompressed output-byte pressure, expansion debt, Rx SRAM occupancy, decompression-engine service, and feedback to RDMA credit or congestion control.

Primary sources:

- `idea-stage/IDEA_REPORT.md`
- `refine-logs/FINAL_PROPOSAL.md`
- `refine-logs/EXPERIMENT_PLAN.md`
- `experiments/rx-expansion/results/M1_GO_NOGO_REPORT.md`

## Core Claims

1. Naive compressed RDMA can shift the bottleneck from link bytes to receiver decompressed-output service, creating avoidable Rx stalls, tail latency, drops, retransmissions, or completion delay.
2. Short-window expansion-ratio estimation can predict dangerous receiver pressure well enough to guide scheduling and feedback.
3. Expansion-aware Rx budgeting should improve p99/p999 FCT, completion latency, stall/drop bytes, and fairness versus naive compressed RDMA and wire-byte-only controls.
4. The mechanism must be practical for NIC/DPU implementation: bounded metadata, SRAM, scheduler latency, and control-path complexity.

## Method Summary

EARB is a NIC/RDMA control mechanism, not a new compression algorithm. Its required pieces are:

- Dual-byte accounting for compressed ingress bytes, decompressed output bytes, and buffered expansion debt.
- Receiver decompressed-byte token bucket as the strongest non-oracle baseline.
- Static per-QP decompressed-byte caps and static Rx output partitioning baselines.
- Exact-original-byte receiver credits when original length metadata is available.
- FIFO shared decompression queue and wire-byte weighted fair sharing baselines.
- Expansion-aware decompression scheduling by predicted output pressure.
- Feedback hook to sender-side rate, credit, or marking logic after the local receiver model is validated.
- Hardware-cost accounting for per-flow state, Rx SRAM, scheduler cycles, and optional output-credit scheduler sketch.

## Experiment Design Pointer

Workflow 1.5 must execute from `refine-logs/EXPERIMENT_PLAN.md`. The current experiment path is:

1. Keep the M0/M1 trace/payload split explicit: `schedule_trace` is communication structure only, while `compression_profile` and `ratio_trace` carry payload and provenance fields.
2. Use `experiments/rx-expansion/contracts/TRACE_PAYLOAD_CONTRACT.md` and `experiments/rx-expansion/contracts/CLAIM_BOUNDARY.md` as executable boundary documents.
3. Continue from the M1 analytical model into M2 model plumbing only.
4. M2 must include compressed/original byte accounting, finite Rx output buffer/SRAM, decompression input and output service, queueing/control signals, and baselines including receiver decompressed-byte token bucket.
5. Only after M2 is stable should htsim integration, gem5/htsim window co-simulation, and hardware-cost ablations be expanded.

Key metrics include p50/p95/p99/p999 FCT, completion latency, retransmitted bytes, ECN/PFC marks if modeled, Rx SRAM occupancy, expansion debt, decompressor utilization, stall/drop bytes, compression ratio, prediction error, accepted/dropped compressed bytes, and hardware cost.

## Claim Boundary

Current evidence does not prove real compressed communication payload behavior. Do not make that claim until P2/P3 payload evidence exists. P0 literature ratios support analytical sensitivity and Go/No-Go triage only.

Do not claim line-rate RoCE correctness, production DCQCN/PFC behavior, PCIe transaction-level behavior, timing closure, energy, or end-to-end LLM serving speedup from the current evidence.

## Current Evidence Status

The M1 P0-only analytical sensitivity pack is complete.

- Rows evaluated: 960.
- Output-unsafe rows: 384.
- Codec families: EBPC, Quad e4m3, and ZipServ-like.
- Output paths: CXL or PCIe 6 staging-like, GPU-direct PCIe 5 x16-like, host DRAM PCIe 4 x16-like, and host DRAM PCIe 5 x16-like.
- Offered-load modes: compressed-line-rate saturated and same-original-bytes.
- Decision: conditional Go for M2 model plumbing only.

Targeted M1 Go/No-Go review on 2026-05-01 with `gpt-5-5-pro` confirmed the same boundary: score 4/6, confidence high, conditional Go for M2 model plumbing only. The remaining blockers are P1/P2/P3 payload evidence, queueing/control realism, and hardware-cost detail.

## Key Decisions

- NetZIP makes generic "put lossless compression in the NIC" too incremental; the active contribution is receiver output-byte control under compression-induced expansion.
- Workflow 1 recovery uses this contract, `idea-stage/docs/research_contract.md`, not the experiment execution plan.
- Workflow 1.5 `/experiment-bridge` reads `refine-logs/EXPERIMENT_PLAN.md` as the canonical experiment execution blueprint.
- Topic-specific literature folders are legacy history only. Active Workflow 1 literature output is `idea-stage/LITERATURE_REVIEW.md` plus UTC timestamped history files.
- Chakra/ASTRA-sim schedule traces are schedule-only and never prove payload compressibility.
- Do not add P1/P2/P3 payload collection silently to the M1 pack; open a separate payload-evidence plan if needed.

## Immediate Research Gate

Proceed only with M2 model plumbing. Include receiver decompressed-byte token bucket, static per-QP decompressed-byte cap, exact-original-byte receiver credits, FIFO/static partitioning, queueing/control, Rx SRAM, decompressor/output-DMA service, and hardware-cost ablations. Do not claim real compressed communication payload behavior until P2/P3 evidence exists.
