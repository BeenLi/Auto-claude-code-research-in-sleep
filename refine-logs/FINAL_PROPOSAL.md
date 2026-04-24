# Final Method Proposal

## 1. Problem Anchor
Shared DPU compression engines are fast in isolation but poorly behaved under contention. When flows with different compressibility, chunk sizes, and burst patterns share the same hardware engine, they interfere in highly asymmetric ways, creating head-of-line blocking, tail-latency inflation, and tenant-level QoS violations. Existing systems optimize for raw throughput but fail to provide predictable multi-tenant interference control.

## 2. Final Method Thesis
We propose to build an **interference cartography** of shared DPU compression engines and use it to drive a lightweight **QoS-aware scheduler** that predicts harmful co-schedules and steers requests to preserve tail latency and fairness with minimal throughput loss.

## 3. Dominant Contribution
Treating the DPU compression engine as a contention-sensitive shared accelerator and making its interference structure explicit, measurable, and schedulable.
- A compact interference map predicting how one workload degrades another.
- A practical scheduler that avoids destructive co-location and bounds unfair slowdowns without hardware changes.

## 4. Explicitly Rejected Complexity
- **No hardware redesign**: Focus is on software control of existing DPU engines.
- **No full-cluster scheduling**: This is a per-DPU engine scheduling problem.
- **No heavy ML/RL**: Simple predictive models or table-driven policies are used for fast online scheduling.
- **No perfect isolation**: Target is strong improvement in QoS predictability, not absolute strict isolation.

## 5. Key Claims and Must-Run Ablations
- **Claims**: Interference is structured/predictable; cartography accurately flags toxic co-runs; QoS scheduling reduces p99 latency significantly vs FIFO.
- **Ablations**: FIFO vs Map-aware Scheduler; Offline vs Online map; Feature ablations (compressibility vs size vs burstiness).
