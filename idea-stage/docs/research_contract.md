# Research Contract: C-Share

> Focused working document for the currently selected idea. This file is the recovery context for future sessions; detailed idea pool and experiment blocks live in `idea-stage/IDEA_REPORT.md` and `refine-logs/EXPERIMENT_PLAN.md`.

## Selected Idea

- **Description**: C-Share treats DPU/NIC-side lossless compression as a shared infrastructure service across tenants and LLM traffic classes. It designs a multi-resource scheduler/admission controller that accounts for compressed input bytes, original/output bytes, engine cycles, and DMA/host-memory traffic using original-byte credits, engine-time tokens, output-byte caps, and age-bucket fairness.
- **Source**: `idea-stage/IDEA_REPORT.md`, Idea #1.
- **Selection rationale**: Generic lossless communication compression is crowded by NetZIP, ZipCCL, UCCL-Zip, SplitZip, ZipServ, and Quad Length Codes. C-Share targets a remaining shared-service fairness gap and received external gpt-5.5 reviewer support at 5/6 confidence high.

## Core Claims

1. Mixed LLM communication workloads can make FIFO, wire-byte fair, or ratio-greedy compression services unfair because compressed bytes do not represent output bytes, engine time, or DMA/memory traffic.
2. C-Share can reduce p99/SLO unfairness using small multi-resource accounting mechanisms while preserving most compression throughput.
3. Hardware feasibility is plausible but unproven until service-time calibration and state-cost estimates are produced.

## Method Summary

C-Share models each compression request by compressed input size, original/output size, predicted engine cycles, DMA or memory bytes, tenant, traffic class, and age. The scheduler admits and orders requests with per-tenant original-byte credits, engine-time tokens, output-byte caps, and age-bucket fairness. It intentionally avoids optimizing solely for compression ratio or wire bytes.

The first implementation should be a standalone analytical/trace replay simulator, not a hardware prototype. It should compare against uncompressed communication, FIFO compression, wire-byte fair sharing, ratio-greedy compression, the existing Rx expansion budgeter, and generic DPU QoS without compression hints.

## Experiment Design Pointer

- **Plan**: `refine-logs/EXPERIMENT_PLAN.md`
- **Baselines**: uncompressed, FIFO compression, wire-byte fair, ratio-greedy, Rx-output-only budgeter, DPU QoS without compression hints, oracle scheduler.
- **Metrics**: SLO-goodput, p99 latency, fairness index, engine occupancy, output bytes, DMA/host-memory bytes.
- **Execution note**: Detailed run order lives in the experiment plan; do not copy full blocks here.

## Claim Boundary

Current evidence supports only idea selection and experiment planning. It does not yet support real LLM payload compressibility, real DPU/BlueField benefit, line-rate feasibility, or production multi-tenant SLO claims.

## Current Evidence Status

- Literature survey completed on 2026-05-07.
- External gpt-5.5 review selected C-Share as top idea, score 5/6, confidence high.
- No C-Share experiments have been executed yet.
- Largest gap: P0 simulator must show naive shared compression policies actually fail in meaningful regions.

## Key Decisions

- Selected shared compression-service fairness over generic collective/KV compression because direct prior work is crowded.
- Kept checkpoint/model-load as workload/ablation, not standalone contribution.
- Deferred hardware claims until DPU/engine timing or HLS/RTL sanity exists.
- Will compare against existing Rx expansion budgeting to separate output-byte admission from shared engine fairness.

## Immediate Research Gate

Implement P0 analytical/trace replay simulator and determine whether compression-service unfairness exists; do not claim real deployment or hardware benefit until P2/P3 evidence exists.

