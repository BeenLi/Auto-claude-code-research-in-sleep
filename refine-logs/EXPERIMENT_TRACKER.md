# Experiment Tracker: C-Share

**Generated**: 2026-05-07T06:07:21Z  
**Status**: planned, not executed.

| ID | Experiment | Status | Gate | Expected output |
|---|---|---|---|---|
| P0-M1 | Multi-resource service simulator scaffold | pending | model compiles and tests pass | simulator module + tests |
| P0-M2 | Naive scheduler failure matrix | pending | identify or falsify unfairness regions | CSV/JSON + Go/No-Go report |
| P0-M3 | Resource ablation pack | pending | show which resource dimensions matter | ablation table |
| P1-T1 | Mixed LLM traffic trace generator | pending | generate collectives/KV/checkpoint/service mixes | trace profiles |
| P1-T2 | Literature profile calibration | pending | map NetZIP/ZipCCL/UCCL-Zip/SplitZip-like profiles | profile library |
| P2-R1 | Public workload ingestion | deferred | find public traces or tensor profiles | reproducible trace adapter |
| P3-H1 | DPU/engine timing microbenchmark | deferred | hardware available or HLS surrogate accepted | service-time calibration |
| P3-H2 | Scheduler state-cost estimate | deferred | counter/SRAM/logic estimate | hardware-cost report |

## Current Gate

Start with P0-M1/P0-M2 only. The next decision is whether naive shared compression-service policies fail strongly enough to justify implementation.

