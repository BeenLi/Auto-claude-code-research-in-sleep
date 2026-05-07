# Experiment Plan: C-Share

**Generated**: 2026-05-07T06:07:21Z  
**Selected idea**: C-Share: Multi-Resource Fairness for Shared Lossless Communication Compression on DPUs/NICs  
**Stage**: Workflow 1 output; ready for `/experiment-bridge` handoff gate.

---

## Claim-Driven Roadmap

### Claim C1: Existing compression-service schedulers are unfair under mixed LLM traffic

**Hypothesis**: FIFO, wire-byte fair sharing, and ratio-greedy scheduling can improve average throughput while worsening tenant p99 latency or SLO-goodput because they ignore engine cycles, output bytes, and DMA/memory traffic.

**Experiments**:

- P0 analytical sweep over synthetic traffic classes:
  - latency-sensitive KV transfer,
  - bulk collectives,
  - checkpoint/model-load bursts,
  - background storage/network services.
- Compare schedulers:
  - uncompressed,
  - FIFO compression,
  - wire-byte fair,
  - ratio-greedy,
  - Rx-output-only budgeter,
  - C-Share.

**Metrics**:

- SLO-goodput,
- p50/p95/p99 service latency,
- Jain fairness index or weighted slowdown fairness,
- engine occupancy,
- output-byte admitted/dropped,
- DMA/host-memory bytes.

**Decision gate**:

- Go if at least one realistic parameter region shows >20% p99/SLO fairness degradation for naive schedulers and C-Share recovers most of it with <10% throughput loss.
- No-go if all schedulers behave similarly across broad sweeps.

### Claim C2: Multi-resource compression accounting is necessary beyond receiver output-byte budgeting

**Hypothesis**: output-byte-only admission catches receiver expansion pressure but misses engine-cycle and DMA contention; C-Share catches both.

**Experiments**:

- Reuse local Rx expansion model as baseline.
- Add service-time and DMA dimensions.
- Sweep codec families:
  - fast low-ratio,
  - slow high-ratio,
  - asymmetric compress/decompress,
  - fixed-format GPU-friendly codec,
  - DPU C-engine-like service.

**Metrics**:

- missed overload cases by baseline,
- false throttling cases,
- tenant slowdown,
- engine queue depth.

**Decision gate**:

- Go if C-Share identifies unsafe states that Rx-output-only and wire-byte policies miss.

### Claim C3: C-Share can be hardware-feasible with small state

**Hypothesis**: C-Share needs only per-tenant buckets and coarse service-time classes, not large dynamic optimization.

**Experiments**:

- Static resource/state accounting model:
  - number of tenants,
  - bucket width,
  - update frequency,
  - counter size,
  - SRAM estimate.
- Optional HLS/RTL sketch for scheduler selection logic.
- Optional BlueField/DPU compression microbenchmark if hardware exists:
  - service time by block size,
  - queueing under concurrency,
  - DMA bytes by placement.

**Metrics**:

- per-tenant state bytes,
- scheduler critical operations per packet/job,
- estimated SRAM,
- throughput envelope,
- measured/calibrated engine service time.

**Decision gate**:

- Go if state is small enough for DPU firmware/FPGA shell assumptions and scheduler does not require per-byte dynamic optimization.

---

## Run Order

1. **P0-Model**: implement standalone multi-resource service simulator and reproduce naive scheduler failure cases.
2. **P1-Trace**: add mixed workload trace generator/replay; calibrate synthetic classes from literature ratios and local profiles.
3. **P1-Ablation**: isolate each resource dimension: input bytes, output bytes, engine time, DMA/memory bytes.
4. **P2-Realistic Profiles**: ingest public or measured ZipCCL/UCCL-Zip/SplitZip/NetZIP-like ratios and service-time approximations.
5. **P3-Hardware Sanity**: optional BlueField/DPU or HLS/RTL microbenchmark to calibrate engine timing/state cost.

---

## Baselines

| Baseline | Purpose |
|---|---|
| Uncompressed | Shows whether compression service is worthwhile at all. |
| FIFO compression | Simplest shared service. |
| Wire-byte fair | Tests conventional network fairness. |
| Ratio-greedy | Tests throughput-maximizing compression. |
| Rx-output-only budgeter | Separates current local idea from new engine/DMA fairness. |
| DPU QoS without compression hints | Tests whether generic QoS is enough. |
| Oracle scheduler | Upper bound with full future resource demand. |

---

## Ablations

- Remove original-byte credits.
- Remove engine-time tokens.
- Remove output-byte caps.
- Remove DMA/memory budget.
- Remove age fairness.
- Vary tenant weights and deadlines.
- Vary compression-ratio predictability.
- Vary engine-time prediction error.
- Vary DPU/host memory bandwidth and DCA assumptions.

---

## Evidence Levels

- P0: analytical sensitivity only; no real payload claim.
- P1: trace replay with literature-derived profiles; limited workload claim.
- P2: public workload or measured tensor profiles; stronger LLM relevance.
- P3: hardware-calibrated or prototype measurement; architecture claim can begin.

---

## First 3 Runs to Launch

1. `p0_naive_failure_matrix`: sweep tenant mixes and scheduler policies to find failure regions.
2. `p0_resource_ablation`: turn each C-Share resource dimension on/off.
3. `p1_profile_calibration`: map ZipCCL/UCCL-Zip/SplitZip/NetZIP-like ratio/service profiles into workload classes.

---

## Do-Not-Claim Boundary

Do not claim:

- real compressed communication payload behavior,
- production DPU/NIC deployment benefits,
- line-rate feasibility,
- BlueField C-engine fairness,
- real LLM serving/training speedup,

until P2/P3 evidence exists.

