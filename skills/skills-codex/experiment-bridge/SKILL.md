---
name: experiment-bridge
description: "Workflow 1.5 for Computer Architecture research: turn EXPERIMENT_PLAN.md into simulator manifests, scripts, sanity runs, and initial results for gem5, Broadcom/csg-htsim, co-simulation, RTL, synthesis, or micro-benchmark experiments."
argument-hint: [experiment-plan-path-or-topic]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, Skill, spawn_agent, send_input
---

# Workflow 1.5: Experiment Bridge

Bridge a claim-driven architecture experiment plan into executable simulator or hardware experiments.

## Inputs

Prefer:

1. `refine-logs/EXPERIMENT_PLAN.md`
2. `refine-logs/EXPERIMENT_TRACKER.md`
3. `refine-logs/FINAL_PROPOSAL.md`

Extract:

- claims and success criteria
- simulator/backend choice
- run order and milestones
- baselines and ablations
- required outputs and metrics
- resource needs: CPU, memory, walltime, license, board/testbed

## Default Execution Path

1. Parse the plan into a simulator manifest.
2. Generate or reuse scripts/configs for the selected backend.
3. Run the smallest sanity stage first.
4. Review code/configs before launching expensive runs.
5. Use `/run-experiment` for one-off runs or `/experiment-queue` for grids.
6. Collect result JSON/logs into `refine-logs/EXPERIMENT_LOG.md`.

## gem5 + Broadcom/csg-htsim Co-simulation

首版 co-simulation 默认服务 **Rx decompression expansion pressure**:

- gem5 models Rx NIC, decompression, PCIe, host memory pressure, buffers, and stalls.
- Broadcom/csg-htsim models lossy RDMA network behavior and sender-side RTO retransmission.
- An external coordinator advances fixed windows, default `100us`.
- Workers are persistent and use file-based JSON handshakes.
- Exchange is flow/QP summary level, not packet-event level.
- Coordinator validates outputs and records summaries, but does not implement transport retransmission.

The manifest must reserve these high-level metrics:

```yaml
metrics:
  - rx_pressure
  - rx_buffer_occupancy
  - decompression_expansion_ratio
  - accepted_compressed_bytes
  - dropped_compressed_bytes
  - drop_reason
  - sender_retransmission_policy
  - retransmitted_bytes
  - goodput_bytes
  - host_memory_write_gbps
  - pcie_utilization
  - rx_stall_ns
```

## Code/Config Review

Before expensive runs, review:

- Does the implementation match the claim?
- Are required outputs and metrics produced?
- Does the co-simulation preserve lossy RDMA with reliable completion?
- Are Rx overflow/drop and sender-side RTO retransmission represented as metrics?
- Are simulator versions, commands, and config files recorded?

## Output

Write or update:

- `refine-logs/EXPERIMENT_MANIFEST.yaml`
- `refine-logs/EXPERIMENT_TRACKER.md`
- `refine-logs/EXPERIMENT_LOG.md`

Initial results must separate:

- completed runs,
- failed/stuck runs,
- missing artifacts,
- claim impact,
- next runs to launch.
