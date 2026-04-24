# Pipeline Summary

**Problem**: Shared DPU compression engines are fast in isolation but poorly behaved under contention, creating head-of-line blocking and QoS violations.
**Final Method Thesis**: We propose to build an interference cartography of shared DPU compression engines and use it to drive a lightweight QoS-aware scheduler that predicts harmful co-schedules and steers requests to preserve tail latency and fairness.
**Final Verdict**: READY
**Date**: 2026-04-24

## Final Deliverables
- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`

## Contribution Snapshot
- **Dominant contribution**: A compact interference map characterizing compression workloads and a practical scheduler to mitigate DPU engine contention.
- **Optional supporting contribution**: An offline replay simulator for DPU compression scheduling.
- **Explicitly rejected complexity**: No hardware redesign, no cluster-wide orchestration, no heavy ML policies.

## Must-Prove Claims
- Interference on shared DPU compression engines is severe, asymmetric, and workload-dependent.
- A low-dimensional interference cartography can predict most harmful co-schedules accurately enough for online use.
- QoS-aware scheduling using this cartography substantially reduces p99 latency vs FIFO policies.

## First Runs to Launch
1. Platform bring-up and single-tenant calibration (establish saturation point).
2. Interference cartography data collection (pairwise matrix over load levels).
3. Offline scheduler replay and ablations.

## Main Risks
- **Risk**: The cartography becomes too hardware/firmware-specific and doesn't generalize well.
- **Mitigation**: Base features on fundamental properties (compressibility, chunk size, burstiness) and validate across different DPU models or firmware versions if possible.

## Next Action
- Proceed to `/run-experiment` (needs access to BlueField DPU).
