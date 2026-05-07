# Final Proposal: C-Share

**Generated**: 2026-05-07T06:07:21Z  
**Direction**: Lossless Communication Compression  
**Selected idea**: C-Share: Multi-Resource Fairness for Shared Lossless Communication Compression on DPUs/NICs  
**Verdict**: READY for Workflow 1.5 first-signal planning; hardware claims deferred.

---

## Problem Anchor

LLM infrastructure is beginning to use lossless compression in communication paths: NIC-side training compression, GPU collective/P2P compression, KV-transfer compression, and DPU compression engines. Existing work evaluates compression as a per-flow or per-library accelerator. That framing breaks down when the compressor/decompressor becomes a shared DPU/NIC infrastructure service across tenants, checkpoints, KV transfers, collectives, and storage traffic.

The hidden problem is that “compressed bytes” are not the only resource. A shared lossless compression service consumes at least four coupled resources:

1. compressed input bytes on the wire or service ingress,
2. original/decompressed output bytes delivered to host/GPU/storage,
3. engine cycles and queue slots inside the compression accelerator,
4. DMA / PCIe / host-memory / DPU-memory traffic.

Schedulers that are fair by wire bytes, job count, or compression ratio can still be unfair by output bytes, engine time, or SLO impact.

---

## Method Thesis

**C-Share designs a hardware-feasible multi-resource scheduler and admission controller for DPU/NIC lossless communication compression services, using original-byte credits, engine-time tokens, output-byte caps, and age-bucket fairness to prevent compression-induced noisy-neighbor failures while preserving most compression throughput.**

---

## Dominant Contribution

The contribution is not a new codec. It is a compression-service resource model and a small scheduling mechanism that exposes why existing per-flow compression systems are unsafe or unfair when deployed as shared infrastructure.

---

## Method Summary

C-Share treats each compression request as a tuple:

- `compressed_in_bytes`
- `original_or_output_bytes`
- `predicted_engine_cycles`
- `dma_or_memory_bytes`
- `tenant_id`
- `traffic_class`
- `deadline_or_slo_class`
- `age`

The scheduler maintains lightweight per-tenant state:

- original-byte credit bucket,
- engine-time token bucket,
- output-byte cap over short windows,
- age bucket to prevent starvation,
- optional DMA/memory budget when modeling DPU or PCIe pressure.

At admission time, a request is admitted only if it does not violate the output/DMA/service envelope for its tenant and traffic class. At scheduling time, C-Share ranks eligible requests by age-adjusted normalized dominant-resource deficit, not by compressed bytes or compression ratio alone. This intentionally penalizes flows that look cheap on the wire but inflate output bytes or monopolize engine time.

---

## Explicitly Rejected Complexity

- No new entropy codec in the main contribution.
- No protocol-visible RDMA semantic change in the first proposal.
- No claim of real LLM payload compressibility until P2/P3 evidence exists.
- No full BlueField production stack dependency for the first gate.
- No universal optimal placement controller across GPU/CPU/DPU/storage; placement is an ablation, not the dominant story.

---

## Core Claims

1. **Failure claim**: In mixed LLM communication workloads, FIFO, wire-byte fair, and ratio-greedy compression schedulers can produce unfair p99 latency or SLO-goodput collapse because they ignore output bytes, engine cycles, and DMA/memory traffic.
2. **Mechanism claim**: A small multi-resource scheduler using original-byte credits, engine-time tokens, output-byte caps, and age buckets reduces tail unfairness with bounded throughput loss.
3. **Hardware feasibility claim**: The required state and arithmetic are small enough for DPU firmware, SmartNIC datapath assist, or FPGA shell implementation; full hardware timing is deferred until after P0/P1.

---

## Target Baselines

- Uncompressed communication.
- FIFO DPU compression service.
- Ratio-greedy compression service.
- Wire-byte fair sharing.
- Per-flow compressed communication approximating NetZIP/ZipCCL/UCCL-Zip behavior.
- Existing Rx expansion budgeter as receiver-output-only baseline.
- DPU QoS without compression-specific resource hints.

---

## Main Risks

- **Novelty risk**: reviewer may say this is generic multi-resource scheduling. Mitigation: show compression creates a distinct coupled resource vector and failure modes absent from ordinary NIC QoS.
- **Hardware realism risk**: without a DPU/FPGA sanity check, claims may look too analytical. Mitigation: make hardware claim scoped; add microbenchmark only after P0/P1.
- **Workload realism risk**: public traces may not reflect production tenant mixes. Mitigation: sweep compressibility, job size, burstiness, deadlines, and traffic classes; label evidence levels.
- **Overlap risk**: current local Rx expansion budgeting is close. Mitigation: explicitly compare and show C-Share handles shared engine time and tenant fairness, not only receiver output-byte admission.

---

## Final Verdict

Proceed to Workflow 1.5 only for **model plumbing and first-signal evaluation**. The first gate should establish whether compression-service unfairness exists under realistic parameter sweeps. Do not claim a real deployment benefit until trace replay and at least one hardware-calibrated service-time model are available.

