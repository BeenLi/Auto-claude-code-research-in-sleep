# Experiment Plan

## Core Claims
1. Shared DPU compression interference is structured, not random.
2. A compact interference map predicts harmful co-runs better than naive load signals.
3. A QoS-aware scheduler that consults the map improves end-to-end multi-tenant utility.
4. The system is practical: low control overhead, limited reprofiling, stable gains.

## 1. Main Anchor Result: End-to-End Evaluation
- **Testbed**: 1-2 BlueField DPU shared compression engine pools. 3 tenant classes (Latency-critical, Elastic, Best-effort).
- **Baselines**: FIFO shared queue, Weighted fair sharing, Static partitioning, Reactive QoS controller.
- **Metrics**: SLO-goodput, p50/p95/p99 latency, QoS violation rate, total throughput, fairness.
- **Sweeps**: Offered load (0.4x to 1.3x saturation), Mix skew, Burstiness.
- **Success Criteria**: >=15-20% higher SLO-goodput or >=30% lower QoS violations vs. strongest non-oracle baseline, with <2% scheduler overhead.

## 2. Novelty Isolation
- **Interference Cartography Quality (C1, C2)**: Pairwise interference heatmaps vs. utilization/queue-depth/workload-label predictors.
- **Scheduler Ablations (C3)**: Full system vs. scheduler without map vs. QoS objective without map vs. stale map.
- **Overhead and Stability (C4)**: Decision latency, CPU/DPU memory footprint, map drift and rebuild cost.

## 3. Run Order, Budget, Decision Gates
Total Budget: ~350-450 DPU-hours

**1. Platform bring-up and single-tenant calibration (15-20h)**
- *Gate*: Single-tenant throughput within 10% of hardware baseline.

**2. Interference cartography (100-130h)**
- *Gate*: Harmful vs benign co-runs differ by >=15-20% slowdown. Map predicts unseen states with Spearman rho >= 0.8.

**3. Offline scheduler replay and ablations (10-20h)**
- *Gate*: Full scheduler beats best baseline by >=10-15% SLO-goodput in replay.

**4. Online end-to-end anchor (50-70h)**
- *Gate*: One clear headline win on SLO-goodput/QoS violations across sweeps.

**5. Robustness and practicality (30-50h)**
- *Gate*: Overhead <2%, map remains useful with modest drift.
