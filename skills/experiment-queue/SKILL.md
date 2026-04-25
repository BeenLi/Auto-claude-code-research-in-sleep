---
name: experiment-queue
description: Generic simulator/job queue for Computer Architecture experiments, including gem5, Broadcom/csg-htsim, window-level co-simulation, RTL/synthesis jobs, and micro-benchmark sweeps. Use for batch experiments, simulator grids, multi-phase runs, or when /run-experiment is insufficient.
argument-hint: [manifest-or-grid-spec]
allowed-tools: Bash(*), Read, Grep, Glob, Edit, Write, Agent, Skill(run-experiment), Skill(monitor-experiment)
---

# Experiment Queue

Orchestrate batches of Computer Architecture experiments across generic resource slots.

## Default Backends

- `gem5`
- `htsim` for `Broadcom/csg-htsim`
- `cosim_gem5_htsim`
- `generic_shell`

The queue is simulator-first. Do not assume CUDA, GPU memory, W&B, or ML training loops unless the manifest explicitly requests them through `generic_shell`.

## Resource Model

Prefer `resources.slots` over GPU lists:

```yaml
resources:
  slots:
    - {id: sim0, type: cpu_sim}
    - {id: sim1, type: cpu_sim}
    - {id: vcs0, type: license_vcs}
max_parallel: 2
```

Jobs request slot types:

```yaml
resources: {slot_type: cpu_sim, cpu_cores: 4, memory_gb: 16, walltime: 2h}
```

Supported resource concepts:
- CPU simulation slots
- memory budget
- walltime/timeout
- EDA license tokens
- exclusive FPGA/DPU/testbed devices
- legacy GPU slots only for compatibility

## Manifest Shape

```yaml
project: rx_pressure
backend: cosim_gem5_htsim
cwd: /home/user/rx-pressure
env:
  setup: source env.sh
resources:
  slots:
    - {id: sim0, type: cpu_sim}
    - {id: sim1, type: cpu_sim}
cosim:
  coordinator: external
  window_us: 100
  worker_lifecycle: persistent_file_handshake
  htsim_variant: broadcom_csg_htsim
  ground_truth: rx_decompression_expansion_pressure
phases:
  - name: sanity
    grid:
      ratio: [1.5, 2.0]
    template:
      id: rx_ratio_${ratio}
      adapter: cosim_gem5_htsim
      cmd: python3 run_cosim.py --ratio ${ratio}
      resources: {slot_type: cpu_sim, cpu_cores: 4, memory_gb: 16}
      outputs:
        required:
          - results/rx_ratio_${ratio}.json
          - exchange/cosim_trace.jsonl
      metrics:
        - rx_pressure
        - decompression_expansion_ratio
        - accepted_compressed_bytes
        - dropped_compressed_bytes
        - sender_retransmission_policy
```

## gem5 + Broadcom/csg-htsim Co-simulation

首版协同仿真锚点是 **Rx decompression expansion pressure**:

- compressed wire bytes can expand into larger host-memory writes after Rx decompression,
- bursty multi-flow arrivals can exceed PCIe, host memory, Rx buffer, or decompression-engine capacity,
- the network is lossy, but RDMA flow completion is reliable,
- drops are performance events recovered by sender-side RTO retransmission,
- coordinator advances windows and records summaries, but retransmission is htsim sender-side transport behavior.

Use persistent workers plus file-based JSON handshakes. Exchange flow/QP summaries at window boundaries; do not exchange packet-level events in JSON.

## Workflow

1. Parse YAML/JSON grid spec.
2. Build an explicit manifest with `tools/experiment_queue/build_manifest.py`.
3. Launch `tools/experiment_queue/queue_manager.py`.
4. Monitor `queue_state.json`.
5. Parse required result JSON and simulator logs.
6. Hand completed metrics to `/analyze-results`, `/result-to-claim`, or paper figures.

## Failure Handling

Retry transient failures such as timeouts and license checkout failures. Mark missing required outputs as failed/stuck. For lossy RDMA experiments, packet/drop behavior belongs in the simulator output and result JSON, not in the queue state machine.

## Invariants

- Expected outputs are the source of completion truth.
- Queue state is written atomically.
- Scheduler does not inject retransmissions for co-simulation.
- New architecture manifests should not rely on `nvidia-smi` or `CUDA_VISIBLE_DEVICES`.
