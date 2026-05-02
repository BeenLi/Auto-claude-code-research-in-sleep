# experiment-queue Tools

Scheduler and manifest builder for simulator-first ARIS experiments.

## Files

- `build_manifest.py` — expands YAML/JSON grid specs into explicit job manifests.
- `queue_manager.py` — runs jobs across generic resource slots, tracks state, retries transient failures, and verifies required outputs.
- `cosim_protocol.py` — defines the window-level gem5 + Broadcom/csg-htsim exchange contract for Rx decompression expansion pressure.

## Install on Remote

The `/experiment-queue` skill installs helper scripts on the SSH host under `~/.aris_queue/` per invocation. It resolves local helpers with this fallback chain:

```text
.aris/tools/experiment_queue/ -> tools/experiment_queue/ -> $ARIS_REPO/tools/experiment_queue/
```

Manual install, when needed:

```bash
ssh <server> 'mkdir -p ~/.aris_queue'
scp "$ARIS_REPO/tools/experiment_queue/queue_manager.py" \
    "$ARIS_REPO/tools/experiment_queue/build_manifest.py" \
    <server>:.aris_queue/
```

## Resource Model

The queue no longer treats GPUs as the default resource. Simulator manifests should declare generic slots:

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
max_parallel: 2
cosim:
  coordinator: external
  window_us: 100
  worker_lifecycle: persistent_file_handshake
  htsim_variant: broadcom_csg_htsim
  ground_truth: rx_decompression_expansion_pressure
```

Jobs request a slot type:

```yaml
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

The first co-simulation target is Rx decompression expansion pressure:

- compressed wire bytes can expand into larger host-memory writes after Rx decompression,
- bursty multi-flow arrivals can overflow Rx decompression buffers or PCIe/memory capacity,
- the network is lossy, but RDMA completion is reliable,
- drops are performance events recovered by sender-side RTO retransmission,
- the coordinator records window summaries but does not simulate retransmission itself.

The protocol uses persistent workers plus file-based JSON handshakes at window boundaries. It exchanges flow/QP summaries, not packet-level events.

## Launch

Build a manifest:

```bash
python3 tools/experiment_queue/build_manifest.py \
  --config grid_spec.yaml \
  --output manifest.json
```

For local runs:

```bash
nohup python3 tools/experiment_queue/queue_manager.py \
  --manifest manifest.json \
  --state queue_state.json \
  --log-dir logs \
  > queue_mgr.log 2>&1 &
```

For remote runs, use a per-run directory under `~/.aris_queue/runs/` so concurrent queues do not collide and crash-resume is reproducible. Use remote-relative paths for `scp` destinations and `$HOME`-prefixed paths only inside `ssh` command strings:

```bash
RUN_TS=$(date -u +%Y%m%dT%H%M%SZ)
REMOTE_RUN_REL=".aris_queue/runs/$RUN_TS"
REMOTE_RUN_DIR="\$HOME/$REMOTE_RUN_REL"

ssh <server> "mkdir -p \"$REMOTE_RUN_DIR/logs\" \"\$HOME/.aris_queue\""
scp "$ARIS_REPO/tools/experiment_queue/queue_manager.py" \
    "$ARIS_REPO/tools/experiment_queue/build_manifest.py" \
    <server>:.aris_queue/
scp manifest.json <server>:"$REMOTE_RUN_REL/manifest.json"

ssh <server> "nohup python3 \"\$HOME/.aris_queue/queue_manager.py\" \\
    --manifest \"$REMOTE_RUN_DIR/manifest.json\" \\
    --state    \"$REMOTE_RUN_DIR/queue_state.json\" \\
    --log-dir  \"$REMOTE_RUN_DIR/logs\" \\
    > \"$REMOTE_RUN_DIR/queue_mgr.log\" 2>&1 &"
```

Use `--log-dir`, not `--log`; per-job logs in `--log-dir` drive failure detection.

Monitor:

```bash
jq '.jobs | group_by(.status) | map({(.[0].status): length}) | add' queue_state.json
ssh <server> "jq '.jobs | group_by(.status) | map({(.[0].status): length}) | add' \"$REMOTE_RUN_DIR/queue_state.json\""
```

## Legacy GPU Manifests

Old manifests with `gpus: [...]` still work through a compatibility path. New architecture experiments should use `resources.slots`.

## Dependencies

- Python 3.8+
- `screen`
- Optional: `pyyaml` for YAML grid specs
- Optional simulator toolchains: gem5, Broadcom/csg-htsim, VCS/Vivado, or project-specific wrappers
