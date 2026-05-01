#!/usr/bin/env python3
"""queue_manager.py — ARIS experiment-queue scheduler.

Runs on the SSH remote host or locally.
Reads a manifest, launches jobs across generic resource slots via `screen`,
retries transient failures, cleans stale screens, and writes state continuously
to disk. Legacy GPU manifests are still understood, but simulator-first
manifests should declare `resources.slots` instead of `gpus`.

Usage (on remote):
    nohup python3 queue_manager.py \\
        --manifest manifest.json \\
        --state queue_state.json \\
        --log queue.log \\
        > queue_mgr.log 2>&1 &

The manifest.json is either produced manually or by `build_manifest.py`.

State file format (queue_state.json):
{
  "meta": {"project": "...", "started": "ISO8601", "host": "..."},
  "phases": [{"name": "...", "depends_on": [...], "status": "..."}],
  "jobs": [
    {
      "id": "s200_N64_n50K",
      "phase": "distill",
      "status": "running",  # pending|running|completed|failed_retryable|stuck
      "resource_slot": "sim0",
      "screen_name": "EQ_s200_N64_n50K",
      "pid": 12345,
      "attempts": 1,
      "started": "...",
      "completed": null,
      "expected_output": "figures/pcdistill_sw_N64_n50K_...json",
      "error": null
    }, ...
  ]
}
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


OOM_RE = re.compile(r"(CUDA out of memory|torch\.OutOfMemoryError)")
TRANSIENT_FAILURE_RE = re.compile(
    r"(CUDA out of memory|torch\.OutOfMemoryError|license unavailable|"
    r"license checkout failed|timed out|timeout)",
    re.IGNORECASE,
)
DEFAULT_GPU_FREE_THRESHOLD_MIB = 500
POLL_INTERVAL_SEC = 60


def resolve_conda_hook(manifest_hook=None):
    """Resolve conda hook command via (1) manifest, (2) env var, (3) auto-detect, (4) PATH.

    manifest_hook: value of `conda_hook` field in manifest (full hook command, e.g.
        `eval "$(/custom/path/conda shell.bash hook)"`), or a bare conda binary path
        which will be wrapped automatically.
    """
    def wrap(path_or_cmd):
        if path_or_cmd.startswith("eval"):
            return path_or_cmd
        return f'eval "$({path_or_cmd} shell.bash hook)"'

    # 1. Manifest override
    if manifest_hook:
        return wrap(manifest_hook)
    # 2. Env var override
    env_hook = os.environ.get("ARIS_CONDA_HOOK")
    if env_hook:
        return wrap(env_hook)
    # 3. Auto-detect common install paths
    for p in (
        os.path.expanduser("~/anaconda3/bin/conda"),
        os.path.expanduser("~/miniconda3/bin/conda"),
        os.path.expanduser("~/miniforge3/bin/conda"),
        "/opt/anaconda3/bin/conda",
        "/opt/miniconda3/bin/conda",
        "/opt/miniforge3/bin/conda",
        "/usr/local/anaconda3/bin/conda",
        "/opt/homebrew/anaconda3/bin/conda",
    ):
        if os.path.exists(p):
            return wrap(p)
    # 4. Fall back to PATH
    out, rc = run("command -v conda 2>/dev/null")
    if rc == 0 and out.strip():
        return wrap(out.strip())
    # 5. Last resort
    return 'eval "$(conda shell.bash hook)"'


def now_dt():
    return datetime.now(timezone.utc)


def now():
    return now_dt().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value):
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def run(cmd, check=False, capture=True):
    """Run shell command, return (stdout, returncode)."""
    r = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{r.stderr}")
    return r.stdout, r.returncode


def gpu_memory_used():
    """Return list of used MiB per GPU index."""
    out, rc = run("nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits")
    if rc != 0:
        return []
    return [int(x.strip()) for x in out.strip().split("\n") if x.strip()]


def free_gpus(allowed, threshold_mib=DEFAULT_GPU_FREE_THRESHOLD_MIB):
    """Return list of GPU indices with memory.used < threshold."""
    used = gpu_memory_used()
    return [i for i in allowed if i < len(used) and used[i] < threshold_mib]


def screen_exists(name):
    out, _ = run(f"screen -ls | grep -F '.{name}\\t'")
    return name in out


def kill_screen(name):
    run(f"screen -S {name} -X quit", check=False)


def detect_transient_failure_in_log(log_path):
    if not log_path or not Path(log_path).exists():
        return None
    try:
        out, _ = run(f"tail -c 10000 {shlex.quote(log_path)}")
        match = TRANSIENT_FAILURE_RE.search(out)
        return match.group(0) if match else None
    except Exception:
        return None


def detect_oom_in_log(log_path):
    marker = detect_transient_failure_in_log(log_path)
    return bool(marker and OOM_RE.search(marker))


def output_exists(path_pattern, cwd):
    """Check if output file exists (pattern supports shell glob)."""
    if not path_pattern:
        return False
    full = os.path.join(cwd, path_pattern) if not os.path.isabs(path_pattern) else path_pattern
    out, _ = run(f"ls {shlex.quote(full)} 2>/dev/null | wc -l")
    try:
        return int(out.strip()) > 0
    except ValueError:
        return False


def required_outputs_exist(outputs, cwd):
    required = []
    if isinstance(outputs, dict):
        required = outputs.get("required", [])
    elif isinstance(outputs, list):
        required = outputs
    if not required:
        return False
    return all(output_exists(path, cwd) for path in required)


def resource_slots(manifest):
    """Return configured generic resource slots, or [] for legacy GPU mode."""
    slots = manifest.get("resources", {}).get("slots", [])
    normalized = []
    for idx, slot in enumerate(slots):
        if isinstance(slot, str):
            normalized.append({"id": slot, "type": "generic"})
        else:
            item = dict(slot)
            item.setdefault("id", f"slot{idx}")
            item.setdefault("type", "generic")
            normalized.append(item)
    return normalized


def slot_matches(job, slot):
    requested = job.get("resources", {}).get("slot_type")
    return requested in (None, "any", slot.get("type"))


def available_resource_slots(manifest, state):
    slots = resource_slots(manifest)
    if not slots:
        return []
    taken = {
        job.get("resource_slot")
        for job in state.get("jobs", [])
        if job.get("status") == "running" and job.get("resource_slot")
    }
    return [slot for slot in slots if slot["id"] not in taken]


def load_state(state_file, manifest):
    """Load state from disk or initialize from manifest."""
    if Path(state_file).exists():
        with open(state_file) as f:
            return json.load(f)
    # Initialize from manifest
    state = {
        "meta": {
            "project": manifest.get("project", "unknown"),
            "started": now(),
            "manifest_path": str(manifest.get("_path", "")),
        },
        "phases": [
            {"name": p.get("name", f"phase_{i}"),
             "depends_on": p.get("depends_on", []),
             "status": "pending"}
            for i, p in enumerate(manifest.get("phases", []))
        ],
        "jobs": [],
    }
    return state


def save_state(state, state_file):
    tmp = state_file + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.rename(tmp, state_file)


def phase_ready(phase_name, state):
    """Check if all depends_on phases are completed."""
    for p in state["phases"]:
        if p["name"] == phase_name:
            if not p["depends_on"]:
                return True
            for dep in p["depends_on"]:
                dep_phase = next((x for x in state["phases"] if x["name"] == dep), None)
                if not dep_phase or dep_phase["status"] != "completed":
                    return False
            return True
    return False


def phase_complete(phase_name, state):
    phase_jobs = [j for j in state["jobs"] if j.get("phase") == phase_name]
    if not phase_jobs:
        return False
    return all(j["status"] in ("completed", "stuck") for j in phase_jobs)


def assign_jobs_to_phases(manifest, state):
    """Ensure state.jobs contains all manifest jobs; idempotent."""
    for phase in manifest.get("phases", []):
        phase_name = phase.get("name")
        for job in phase.get("jobs", []):
            existing = next((j for j in state["jobs"] if j["id"] == job["id"]), None)
            if not existing:
                state["jobs"].append({
                    "id": job["id"],
                    "phase": phase_name,
                    "adapter": job.get("adapter", manifest.get("backend", "generic_shell")),
                    "cmd": job["cmd"],
                    "expected_output": job.get("expected_output"),
                    "outputs": job.get("outputs", {}),
                    "metrics": job.get("metrics", []),
                    "resources": job.get("resources", {}),
                    "cosim": job.get("cosim", manifest.get("cosim", {})),
                    "status": "pending",
                    "gpu": None,
                    "resource_slot": None,
                    "screen_name": None,
                    "pid": None,
                    "attempts": 0,
                    "started": None,
                    "completed": None,
                    "error": None,
                })


def launch_job(job, resource_slot, conda_env, cwd, log_dir, conda_hook, env_setup=None):
    """Launch job in a detached screen, return (screen_name, pid)."""
    screen_name = f"EQ_{job['id']}"
    if screen_exists(screen_name):
        # Shouldn't happen; clean up
        kill_screen(screen_name)
        time.sleep(2)
    log_file = os.path.join(log_dir, f"{job['id']}.log")
    cmd = job["cmd"]
    slot = resource_slot if isinstance(resource_slot, dict) else {"id": str(resource_slot)}
    slot_id = str(slot.get("id"))
    cmd_with_slot = cmd.replace("${RESOURCE_SLOT}", slot_id)
    if "gpu" in slot:
        cmd_with_slot = cmd_with_slot.replace("${GPU}", str(slot["gpu"]))

    setup_parts = [f"cd {shlex.quote(cwd)}"]
    if env_setup:
        setup_parts.append(env_setup)
    if conda_env:
        setup_parts.extend([conda_hook, f"conda activate {shlex.quote(conda_env)}"])
    env_prefix = f"ARIS_RESOURCE_SLOT={shlex.quote(slot_id)}"
    if "gpu" in slot:
        env_prefix += f" CUDA_VISIBLE_DEVICES={slot['gpu']}"
    full = (
        " && ".join(setup_parts)
        + f" && {env_prefix} {cmd_with_slot} 2>&1 | tee {shlex.quote(log_file)}"
    )
    screen_cmd = f'screen -dmS {screen_name} bash -c {shlex.quote(full)}'
    run(screen_cmd)
    time.sleep(2)
    # Best-effort PID lookup. Completion is still output-driven.
    pid_out, _ = run(
        f"ps -ef | grep {shlex.quote(job['id'])} | grep -v grep | "
        f"awk '{{print $2}}' | head -1")
    pid = pid_out.strip()
    return screen_name, (int(pid) if pid.isdigit() else None)


def job_status_check(job, log_dir, cwd):
    """Return new status for a running job."""
    screen_name = job["screen_name"]
    log_file = os.path.join(log_dir, f"{job['id']}.log")

    # 1. Output exists → completed
    if job.get("outputs") and required_outputs_exist(job["outputs"], cwd):
        return "completed", None
    if job.get("expected_output") and output_exists(job["expected_output"], cwd):
        return "completed", None

    # 2. Retryable failures (legacy CUDA OOM, EDA license stalls, timeouts)
    transient = detect_transient_failure_in_log(log_file)
    if transient:
        return "failed_retryable", f"Retryable failure detected: {transient}"

    # 3. Screen alive + python alive → still running
    if screen_name and screen_exists(screen_name):
        if job.get("pid"):
            _, rc = run(f"kill -0 {job['pid']} 2>/dev/null")
            if rc == 0:
                return "running", None
            # Python died but screen alive → stale
        else:
            # No pid known; trust screen for now
            return "running", None

    # 4. Screen gone, no output → failed_other
    if not screen_name or not screen_exists(screen_name):
        return "failed_other", "Screen exited without expected output"

    # Default: running
    return "running", None


def pending_jobs_in_active_phases(state, manifest):
    active_phases = []
    for phase in manifest.get("phases", []):
        phase_name = phase.get("name")
        if phase_ready(phase_name, state) and not phase_complete(phase_name, state):
            active_phases.append(phase_name)
    return [
        j for j in state["jobs"]
        if j["status"] == "pending" and j["phase"] in active_phases
    ]


def step(manifest, state, state_file, log_dir):
    """Run one scheduler step: poll, launch, update state."""
    cwd = manifest.get("cwd", ".")
    conda_env = manifest.get("conda")
    conda_hook = resolve_conda_hook(manifest.get("conda_hook"))
    env_setup = manifest.get("env", {}).get("setup")
    allowed_gpus = manifest.get("gpus", list(range(8)))
    max_parallel = manifest.get("max_parallel", len(allowed_gpus))
    gpu_free_threshold = manifest.get("gpu_free_threshold_mib",
                                       DEFAULT_GPU_FREE_THRESHOLD_MIB)
    oom_delay = manifest.get("oom_retry", {}).get("delay", 120)
    max_oom_attempts = manifest.get("oom_retry", {}).get("max_attempts", 3)

    # 1. Check running jobs
    for job in state["jobs"]:
        if job["status"] != "running":
            continue
        new_status, err = job_status_check(job, log_dir, cwd)
        if new_status == "completed":
            job["status"] = "completed"
            job["completed"] = now()
            # Clean up screen
            if job["screen_name"]:
                kill_screen(job["screen_name"])
        elif new_status == "failed_retryable":
            job["status"] = "failed_retryable"
            job["error"] = err
            job["completed"] = now()
            if job["screen_name"]:
                kill_screen(job["screen_name"])
        elif new_status == "failed_other":
            job["status"] = "stuck"
            job["error"] = err
            job["completed"] = now()
            if job["screen_name"]:
                kill_screen(job["screen_name"])

    # 2. Retry transient failures that have waited long enough
    for job in state["jobs"]:
        if job["status"] not in ("failed_retryable", "failed_oom"):
            continue
        if job["attempts"] >= max_oom_attempts:
            job["status"] = "stuck"
            continue
        # Wait oom_delay after failure before retry
        if job["completed"]:
            last = parse_timestamp(job["completed"])
            elapsed = (now_dt() - last).total_seconds()
            if elapsed >= oom_delay:
                job["status"] = "pending"  # Requeue

    # 3. Launch new jobs up to max_parallel
    running = [j for j in state["jobs"] if j["status"] == "running"]
    pending = pending_jobs_in_active_phases(state, manifest)
    generic_slots = available_resource_slots(manifest, state)
    if generic_slots:
        launch_pairs = []
        for job in pending:
            match = next((slot for slot in generic_slots if slot_matches(job, slot)), None)
            if not match:
                continue
            launch_pairs.append((job, match))
            generic_slots.remove(match)
            if len(launch_pairs) >= max_parallel - len(running):
                break
    else:
        free = free_gpus(allowed_gpus, gpu_free_threshold)
        # Exclude GPUs already assigned to running jobs
        taken = {j["gpu"] for j in running if j.get("gpu") is not None}
        free = [g for g in free if g not in taken]
        launch_pairs = [
            (pending[i], {"id": f"gpu{free[i]}", "type": "gpu", "gpu": free[i]})
            for i in range(min(max_parallel - len(running), len(free), len(pending)))
        ]

    for job, slot in launch_pairs:
        screen_name, pid = launch_job(
            job, slot, conda_env, cwd, log_dir, conda_hook, env_setup)
        job["status"] = "running"
        job["gpu"] = slot.get("gpu")
        job["resource_slot"] = slot["id"]
        job["screen_name"] = screen_name
        job["pid"] = pid
        job["attempts"] += 1
        job["started"] = now()
        job["error"] = None

    # 4. Update phase status
    for phase in state["phases"]:
        if phase_complete(phase["name"], state):
            phase["status"] = "completed"
        elif any(j["status"] == "running"
                 for j in state["jobs"] if j.get("phase") == phase["name"]):
            phase["status"] = "running"

    save_state(state, state_file)


def all_done(state):
    return all(j["status"] in ("completed", "stuck") for j in state["jobs"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--log", default=None, help="Human-readable log file")
    ap.add_argument("--log-dir", default=None,
                    help="Per-job log directory (default: cwd)")
    ap.add_argument("--poll", type=int, default=POLL_INTERVAL_SEC)
    args = ap.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)
    manifest["_path"] = args.manifest

    log_dir = args.log_dir or manifest.get("cwd", ".")
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    state = load_state(args.state, manifest)
    assign_jobs_to_phases(manifest, state)
    save_state(state, args.state)

    print(f"[{now()}] Queue manager started with {len(state['jobs'])} jobs")
    sys.stdout.flush()

    while not all_done(state):
        try:
            step(manifest, state, args.state, log_dir)
        except Exception as e:
            print(f"[{now()}] Step error: {e}")
            sys.stdout.flush()
        time.sleep(args.poll)

    print(f"[{now()}] All jobs done")


if __name__ == "__main__":
    main()
