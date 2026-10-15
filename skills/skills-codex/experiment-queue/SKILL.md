---
name: experiment-queue
description: Generic simulator/job queue for Computer Architecture experiments, including gem5, Broadcom/csg-htsim, window-level co-simulation, RTL/synthesis jobs, and micro-benchmark sweeps. Use for batch experiments, simulator grids, multi-phase runs, or when /run-experiment is insufficient.
argument-hint: "[manifest-or-grid-spec]"
allowed-tools: Bash(*), Read, Grep, Glob, Edit, Write, Skill(run-experiment), Skill(monitor-experiment)
---

# Experiment Queue

> ⏱ **External cadence: visibility only.** This skill already runs its own
> detached scheduler (60s poll, `depends_on` enforcement, slot assignment).
> Use its status output for overnight visibility (N done / N running / N
> pending); do **not** wrap it in a second `/loop` / `CronCreate` poll — that
> duplicates the scheduler on an uncoordinated clock and races its phase
> transitions. See
> [`shared-references/external-cadence.md`](../shared-references/external-cadence.md)
> ("does not duplicate an existing internal scheduler").

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

For this lab's slot types (`cpu_sim`, `cpu_rtl`, `license_vivado`, `fpga_vcu118`, `dpu_bf2`, `gpu_l40`), sweep-width rules, and the cross-run device lock, follow `../shared-references/hw-env-contract.md` §3. Build `resources.slots` from `../shared-references/lab-resources.yaml` instead of guessing counts.

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
  - name: sweep
    depends_on: [sanity]          # a LIST, even for a single dependency
    grid:
      ratio: [1.25, 1.75, 2.5, 3.0]
    template:
      id: rx_sweep_${ratio}
      adapter: cosim_gem5_htsim
      cmd: python3 run_cosim.py --ratio ${ratio}
      resources: {slot_type: cpu_sim, cpu_cores: 4, memory_gb: 16}
      outputs:
        required:
          - results/rx_sweep_${ratio}_*.json   # globs are expanded when checking outputs
```

Write `depends_on` as a list. The scheduler normalizes a bare string on load (fresh
manifest and resumed state file alike), but lists are the documented shape. A dependent
phase launches once every job in the phases it depends on is terminal — `completed`
**or** `stuck`. A stuck `sanity` job does not hold `sweep` back, so check
`queue_state.json` for `stuck` jobs before trusting a dependent phase's results.

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

Job states in `queue_state.json`:

```
pending → running → completed                      (required outputs exist)
                 ↘ failed_retryable → pending      (after oom_retry.delay) [retry up to oom_retry.max_attempts, then stuck]
                 ↘ failed_other → stuck            (screen exited without the required outputs)
stale screen (process gone, screen lingering) → failed_other → stuck
```

`failed_retryable` covers license checkout failures, timeouts, and legacy CUDA OOM.
`completed` and `stuck` are terminal; the scheduler exits when every job is one of them.

> **Operator note on `stuck` (the agent's move, not the queue's):** the queue
> deterministically parks `failed_other` jobs as `stuck` — that part is code and
> unchanged. Before handing a `stuck` batch to the human, the OPERATING AGENT
> should check: if the same failure repeats across jobs, try ONE clean
> reimplement of the **agent-generated wrapper/attempt script only** — never
> user/project source (simulator configs, RTL, or `run_*.py` you didn't write),
> the manifest, `queue_state.json`, the env-spec ledger, logs, or results (see
> `shared-references/external-cadence.md` § *Let a broken attempt restart, not just
> patch*). Reserve the human handoff for contract/environment doubts, not merely
> broken attempt code.

## Run Directory and Launch

Bind the run identifiers once so every later step (manifest save, scp, launch, monitor, resume) refers to the same paths. Set these as local shell variables before generating the manifest:

```bash
# REPLACE the placeholder path before running, or pre-export PROJECT_DIR:
PROJECT_DIR="${PROJECT_DIR:?set PROJECT_DIR to the local project root}"
RUN_TS=$(date -u +%Y%m%dT%H%M%SZ)             # one timestamp per run, reused everywhere
LOCAL_RUN_DIR="$PROJECT_DIR/experiment_queue/$RUN_TS"
mkdir -p "$LOCAL_RUN_DIR"
```

Save the built manifest to `$LOCAL_RUN_DIR/manifest.json` for reproducibility.

### Preflight

Before launch:

- Check SSH connection works if running on a remote host.
- Check `cwd` exists on the execution host.
- Check project-specific preconditions such as checkpoints, input traces, simulator binaries, licenses, and environment setup.
- Check required resource slots are available. Do not assume GPUs unless the manifest requests a legacy GPU slot.

If any precondition fails, show the user which jobs are blocked and why.

### Launch Scheduler

The scheduler implementation lives in `tools/experiment_queue/queue_manager.py`. Resolve helpers through the same project-local tools path used by installed ARIS skills:

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
if [ -z "${ARIS_REPO:-}" ] && [ -f .aris/installed-skills.txt ]; then
    ARIS_REPO=$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null) || true
fi
if [ -z "${ARIS_REPO:-}" ] && [ -f "$HOME/.aris/repo" ]; then
    ARIS_REPO=$(cat "$HOME/.aris/repo" 2>/dev/null) || true
fi
QUEUE_TOOLS=".aris/tools/experiment_queue"
[ -f "$QUEUE_TOOLS/queue_manager.py" ] || QUEUE_TOOLS="tools/experiment_queue"
[ -f "$QUEUE_TOOLS/queue_manager.py" ] || { [ -n "${ARIS_REPO:-}" ] && QUEUE_TOOLS="$ARIS_REPO/tools/experiment_queue"; }
[ -f "$QUEUE_TOOLS/queue_manager.py" ] || { echo "ERROR: experiment_queue helpers not found at .aris/tools/, tools/, or \$ARIS_REPO/tools/ (from the install manifest or ~/.aris/repo); rerun install_aris.sh or export ARIS_REPO" >&2; exit 1; }
```

This is the canonical chain from `../shared-references/integration-contract.md` §2. The `.aris/tools` symlink is set up by `install_aris.sh` (#174). Older installs without that symlink fall through to `tools/experiment_queue` when invoked inside the ARIS repo, then to `$ARIS_REPO/tools/experiment_queue`, where `ARIS_REPO` comes from the environment, the project's `.aris/installed-skills.txt`, or the one-line pointer file `~/.aris/repo`.

For remote runs, use both a remote-relative path for `scp` and a `$HOME`-prefixed path for `ssh` command strings. Modern `scp` uses SFTP mode and does not reliably expand `$HOME` in destination paths.

```bash
REMOTE_RUN_REL=".aris_queue/runs/$RUN_TS"
REMOTE_RUN_DIR="\$HOME/$REMOTE_RUN_REL"
```

Bootstrap the remote run directory and copy helpers plus manifest:

```bash
ssh <server> "mkdir -p \"$REMOTE_RUN_DIR/logs\" \"\$HOME/.aris_queue\""
scp "$QUEUE_TOOLS/queue_manager.py" "$QUEUE_TOOLS/build_manifest.py" <server>:.aris_queue/
scp "$LOCAL_RUN_DIR/manifest.json" <server>:"$REMOTE_RUN_REL/manifest.json"
```

Launch the detached scheduler:

```bash
ssh <server> "nohup python3 \"\$HOME/.aris_queue/queue_manager.py\" \\
  --manifest \"$REMOTE_RUN_DIR/manifest.json\" \\
  --state    \"$REMOTE_RUN_DIR/queue_state.json\" \\
  --log-dir  \"$REMOTE_RUN_DIR/logs\" \\
  > \"$REMOTE_RUN_DIR/queue_mgr.log\" 2>&1 &"
```

Use `--log-dir`, not `--log`. `queue_manager.py` reads per-job logs from `--log-dir` for failure detection; a single combined log breaks those checks.

Persist run metadata so monitoring and resume do not regenerate paths:

```bash
{
  printf 'PROJECT_DIR=%q\n'    "$PROJECT_DIR"
  printf 'RUN_TS=%q\n'         "$RUN_TS"
  printf 'LOCAL_RUN_DIR=%q\n'  "$LOCAL_RUN_DIR"
  printf 'REMOTE_RUN_REL=%q\n' "$REMOTE_RUN_REL"
  printf 'REMOTE_RUN_DIR=%q\n' "$REMOTE_RUN_DIR"
} > "$LOCAL_RUN_DIR/run_meta.txt"
```

To resume an existing queue, reload the recorded values and re-run only the launch command:

```bash
LOCAL_RUN_DIR="/abs/path/to/project/experiment_queue/<existing-run-ts>"
. "$LOCAL_RUN_DIR/run_meta.txt"
# Re-run the launch command. Do not re-run bootstrap if it would overwrite manifest.json or queue_state.json.
```

A `queue_state.json` written before the 2026-10 scheduler fix records healthy jobs the old code mis-judged as dead and parked as `stuck` (error `Screen exited without expected output`). Resuming keeps them `stuck` — they are not retried, so a state file whose jobs are all `stuck` finishes with nothing launched. Delete that state file and re-run from the bootstrap step, which also replaces the old `queue_manager.py` on the server.

### Monitoring

Check queue state using the recorded remote run directory:

```bash
ssh <server> "cat \"$REMOTE_RUN_DIR/queue_state.json\"" \
  | jq '.jobs | group_by(.status) | map({(.[0].status): length}) | add'
```

### Post-completion

When all jobs in `manifest.json` are `completed` or `stuck`:

- The remote scheduler exits cleanly with `All jobs done` in `$REMOTE_RUN_DIR/queue_mgr.log`.
- The local skill agent aggregates `$REMOTE_RUN_DIR/queue_state.json` into `$LOCAL_RUN_DIR/summary.md`.
- The local skill agent invokes `/analyze-results` if `analyze_on_complete: true`.

## Invariants

- Expected outputs are the source of completion truth.
- Dependencies are enforced at launch: a phase starts only after every job in the phases it depends on is terminal, and terminal includes `stuck`.
- Queue state is written atomically.
- Scheduler does not inject retransmissions for co-simulation.
- New architecture manifests should not rely on `nvidia-smi` or `CUDA_VISIBLE_DEVICES`.

## See Also

- `/run-experiment` — single experiment deployment
- `/monitor-experiment` — check experiment progress
- `/analyze-results` — post-hoc analysis
- `tools/experiment_queue/queue_manager.py` — scheduler implementation, resolved via the helper chain above
- `tools/experiment_queue/build_manifest.py` — manifest builder, resolved via the same helper chain
- `tools/experiment_queue/cosim_protocol.py` — window-level gem5 + Broadcom/csg-htsim exchange contract
