# Idea Candidates

| # | Idea | Overall Merit | Feasibility | Core Baseline | Handoff | Reviewer Score | Status |
|---|---|---:|---|---|---|---|---|
| 1 | C-Share: Multi-Resource Fairness for Shared Lossless Communication Compression on DPUs/NICs | 1 | high | CB3/CB4/CB5/CB6/CB7 | ready | 5/6 | RECOMMENDED |
| 2 | Compressibility-Aware Expert-Parallel Token Exchange | 2 | medium | CB1/CB5/DeepEP | needs_canon_clarification | 4/6 | BACKUP |
| 3 | DCA-Aware Compression Placement for SmartNIC DPU Offload | 2 | unknown | CB2/CB3/CB5 | designed_not_run | 4/6 inferred | DEFERRED |
| 4 | Checkpoint/Model-Load Compression Placement Controller | 3 | medium | CB2/CB8 | designed_not_run | 3/6 | DEFERRED |

## Active Idea: #1 — C-Share

- **Idea shape**: 把 DPU/NIC 上的 lossless compression engine 当作共享基础设施服务，设计多资源公平调度和准入控制。核心资源包括 compressed input bytes、original/output bytes、engine cycles、DMA/host-memory traffic。
- **core_baseline**: CB3 FIFO DPU compression service; CB4 ratio-greedy compression; CB5 per-flow compressed communication; CB6 current Rx expansion budgeter; CB7 DPU QoS without compression hints.
- **canon_mapping**: platform=[EC-P1, EC-P7, EC-P6 optional]; workload=[EC-W4, EC-W1, EC-W2, EC-W3].
- **metrics**: SLO-goodput, p99 latency, fairness index, engine occupancy, DMA/host-memory bytes, admitted/dropped original/output bytes.
- **target_validation_style**: analytical_model + simulator_evaluation; optional prototype_measurement.
- **evaluation_target_clarity**: clear.
- **evaluation_target_feasibility**: high first-signal / medium full.
- **baseline_reproducibility**: requires_reimplementation.
- **evaluation_environment_access**: ready for analytical/trace replay; optional hardware unknown.
- **idea_adapter_cost**: moderate_adapter.
- **pilot_runtime_cost**: minutes_to_hours.
- **Next step**: `/experiment-bridge` after reviewing `refine-logs/EXPERIMENT_PLAN.md`.

