---
name: monitor-experiment
description: Monitor Computer Architecture experiments, simulator queues, logs, required artifacts, and result JSON. Use when user asks to check progress, inspect results, or see whether simulator jobs are done.
argument-hint: [queue-state-or-run-id]
allowed-tools: Bash(ssh *), Bash(echo *), Read, Write, Edit
---

# Monitor Experiment Results

Monitor simulator, RTL, synthesis, micro-benchmark, or co-simulation runs.

## Workflow

### Step 1: Locate Run State

Prefer queue state when available:

```bash
jq '.jobs | group_by(.status) | map({(.[0].status): length}) | add' queue_state.json
```

For remote jobs:

```bash
ssh <server> "screen -ls"
ssh <server> "test -f queue_state.json && cat queue_state.json"
```

### Step 2: Inspect Logs

Read the latest log for running or stuck jobs:

```bash
tail -80 logs/<run_id>.log
```

Look for simulator-specific failures:

- gem5 panic/config exception/checkpoint missing
- htsim assertion/topology or traffic-matrix error
- VCS/Vivado license checkout failure
- timeout or killed process
- missing required output

### Step 3: Verify Required Artifacts

Check the outputs declared in the manifest:

```bash
test -f results/<run_id>.json
test -f exchange/cosim_trace.jsonl
```

For co-simulation, inspect window summaries and the final result JSON. The Rx pressure scenario should expose:

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

### Step 4: Summarize Raw Numbers First

Report raw metrics before interpretation:

```text
| Run | Backend | Status | Key Metric | Value |
|-----|---------|--------|------------|-------|
| rx_ratio_2.0 | cosim_gem5_htsim | done | dropped_compressed_bytes | ... |
```

### Step 5: Interpret Carefully

Tie interpretation back to the claim:

- Does Rx decompression expansion create PCIe/host-memory pressure?
- Did Rx overflow/drop appear?
- Did sender-side RTO retransmission reduce goodput or increase tail latency?
- Are failures simulator/setup problems or negative scientific results?

## Key Rules

- Never infer completion from a dead screen alone; required outputs must exist.
- Do not treat lossy RDMA drops as application-visible permanent loss unless the experiment explicitly says so.
- Do not claim retransmission was modeled unless the result JSON includes sender-side retransmission metrics.
- Always distinguish simulator walltime from simulated time.
