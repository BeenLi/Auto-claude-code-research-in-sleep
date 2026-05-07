# Review Summary

**Generated**: 2026-05-07T06:07:21Z  
**Reviewer backend**: Oracle API, model `gpt-5.5`  
**Trace session**: `lossless-comm-compressio-review-top`  
**Scope**: Candidate review for Lossless Communication Compression.

---

## Reviewed Candidates

| Candidate | Score | Confidence | Reviewer verdict |
|---|---:|---|---|
| C-Share / Compression-Service Fairness | 5/6 | High | Top pick; ready for Workflow 1.5 if trace replay + analytical model + minimal hardware sanity are planned. |
| Checkpoint/Model-Load Compression Placement | 3/6 | Medium | Too incremental as standalone; useful as supporting workload/ablation. |
| Compressibility-Aware Expert-Parallel Token Exchange | 4/6 | Medium to medium-high | Interesting but risky; could be incremental vs DeepEP/UCCL-EP/UCCL-Zip. |

---

## Key Reviewer Criticism

For C-Share, the strongest objection is that it may look like generic multi-resource scheduling applied to compression. The proposal must make the compression-specific resource coupling explicit:

- compressed input bytes can be low while output bytes are high;
- engine cycles are not proportional to wire bytes;
- DMA/host-memory traffic can dominate DPU offload;
- high-ratio or bursty tenants can be throughput-friendly but SLO-hostile.

The reviewer also warned that hardware feasibility cannot be hand-waved. A first analytical/trace result is acceptable for Workflow 1.5, but any submission-grade claim needs at least hardware-calibrated engine timing or a DPU/FPGA microbenchmark.

---

## Accepted Changes to Proposal

- Reframed the dominant contribution from “better compression scheduling” to “multi-resource fair shared compression service”.
- Made C-Share compare against current Rx expansion budgeting to prove the new dimension is engine-time and tenant fairness.
- Demoted checkpoint/model-load placement to workload/ablation instead of standalone idea.
- Deferred EP token exchange as backup until baselines and traces are clearer.

---

## Minimum Experiment Package

1. Analytical multi-resource simulator with FIFO, wire-byte fair, ratio-greedy, Rx-output-only, and C-Share.
2. Mixed traffic trace generator/replay with collectives, KV transfer, checkpoint burst, and latency-sensitive serving traffic.
3. Parameter sweeps over compression ratio, codec service time, expansion ratio, DPU DMA budget, tenant weight, and burstiness.
4. Optional DPU/engine microbenchmark to calibrate service-time and DMA constants.

---

## Reviewer-Gated Claim Boundary

Allowed after P0/P1:

- “Under modeled mixed-workload assumptions, compression-service scheduling policy changes fairness and p99 outcomes.”
- “C-Share is a plausible first-signal mechanism for multi-resource compression-service fairness.”

Not allowed until P2/P3:

- real LLM payload compressibility claims,
- real DPU/BlueField deployment claims,
- line-rate hardware timing claims,
- production multi-tenant SLO claims.

