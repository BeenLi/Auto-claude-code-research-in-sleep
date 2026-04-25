---
name: run-experiment
description: Launch a single Computer Architecture experiment: simulator run, micro-benchmark, RTL simulation, synthesis job, gem5 run, Broadcom/csg-htsim run, or co-simulation sanity check.
argument-hint: [experiment-description-or-command]
allowed-tools: Bash(*), Read, Grep, Glob, Edit, Write, Agent
---

# Run Experiment

Launch one architecture experiment and verify that it produced the expected artifacts.

## Supported Experiment Types

- `gem5` microarchitecture or memory-system simulation
- `Broadcom/csg-htsim` network/RDMA simulation
- `cosim_gem5_htsim` window-level co-simulation sanity run
- RTL simulation through VCS/Verilator/Vivado xsim
- FPGA synthesis/implementation report generation
- DPU/SmartNIC/FPGA micro-benchmark
- Generic shell experiment

Do not assume ML training, CUDA, W&B, or GPU allocation unless the user explicitly asks for a GPU experiment.

## Pre-flight

Read project configuration from `AGENTS.md`, `CLAUDE.md`, or the experiment manifest if present. Identify:

- backend: `gem5`, `htsim`, `cosim_gem5_htsim`, `rtl`, `synthesis`, `microbench`, or `generic_shell`
- working directory
- environment setup command
- resource needs: CPU cores, memory, walltime, license tokens, exclusive devices
- required outputs
- metrics to parse

For simulator jobs, verify the executable exists before launch:

```bash
command -v gem5.opt
test -x path/to/htsim_roce
```

For RTL/synthesis jobs, check license/tool availability only through non-destructive commands.

## Launch Pattern

Prefer a reproducible command with logs:

```bash
mkdir -p logs results
<env-setup-if-needed>
<experiment-command> 2>&1 | tee logs/<run_id>.log
```

For long-running local or SSH jobs, use `screen` or `tmux` with a stable run id. Record:

- run id
- command
- working directory
- log path
- expected output path
- estimated walltime

## Co-simulation Sanity

For `cosim_gem5_htsim`, the first sanity run should preserve the Rx decompression expansion pressure ground truth:

- compressed wire bytes can expand into larger Rx memory-side writes,
- Rx overflow/drop must be representable,
- lossy RDMA still completes reliably through sender-side RTO retransmission,
- coordinator must not inject retransmissions itself.

Expected high-level metrics:

- `rx_pressure`
- `rx_buffer_occupancy`
- `decompression_expansion_ratio`
- `accepted_compressed_bytes`
- `dropped_compressed_bytes`
- `drop_reason`
- `sender_retransmission_policy`
- `retransmitted_bytes`
- `goodput_bytes`
- `host_memory_write_gbps`
- `pcie_utilization`
- `rx_stall_ns`

## Verification

After launch or completion, verify:

- process started or exited cleanly,
- log exists and has no immediate fatal error,
- all required outputs exist,
- result JSON contains the expected metrics,
- simulator-specific failure signatures are absent or explained.

If a run is part of a grid or has more than a few jobs, hand it to `/experiment-queue`.
