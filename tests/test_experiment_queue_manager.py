"""Tests for tools/experiment_queue/queue_manager.py (the detached scheduler).

Regression coverage for the scheduler defects ported from upstream 6be7b60:
- screen_exists() grepped for a literal backslash-t instead of the TAB that
  `screen -ls` prints, so every healthy job was judged dead and killed;
- the "screen alive, process gone" branch had no return;
- output_exists() shell-quoted the whole path, which disabled glob expansion;
- a bare-string `depends_on` was iterated character by character, so the
  dependent phase never became ready (fresh-manifest and resume paths);
- a persisted `failed_other` had no exit, so the scheduler never finished.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "experiment_queue" / "queue_manager.py"

SCREEN_LS = (
    "There are screens on:\n"
    "\t40123.EQ_rx_ratio_2.0\t(Detached)\n"
    "\t40124.EQ_rx_ratio_1.5\t(10/15/2026 02:11:07 AM)\t(Detached)\n"
    "2 Sockets in /run/screen/S-user.\n"
)


def load_module():
    spec = importlib.util.spec_from_file_location("eq_queue_manager", MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


qm = load_module()


def make_run(screen_ls=SCREEN_LS, kill_rc=0, calls=None):
    """Fake run(): answers `screen -ls` and `kill -0`, fails everything else."""

    def fake_run(cmd, check=False, capture=True):
        if calls is not None:
            calls.append(cmd)
        if cmd == "screen -ls":
            return screen_ls, 0
        if cmd.startswith("kill -0 "):
            return "", kill_rc
        return "", 1

    return fake_run


# --- screen_exists -----------------------------------------------------------


def test_screen_exists_matches_real_tab_through_a_real_shell(tmp_path, monkeypatch):
    # Execute whatever command screen_exists builds through a real shell, with
    # `screen -ls` replaced by the captured output. The old grep pipeline
    # ('.<name>\t' with a literal backslash-t) finds nothing here.
    listing = tmp_path / "screen_ls.txt"
    listing.write_text(SCREEN_LS)
    assert "\t40123.EQ_rx_ratio_2.0\t" in listing.read_text()

    def shell_run(cmd, check=False, capture=True):
        cmd = cmd.replace("screen -ls", f"cat {listing}")
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return r.stdout, r.returncode

    monkeypatch.setattr(qm, "run", shell_run)
    assert qm.screen_exists("EQ_rx_ratio_2.0")
    assert qm.screen_exists("EQ_rx_ratio_1.5")


def test_screen_exists_requires_exact_session_name(monkeypatch):
    monkeypatch.setattr(qm, "run", make_run())
    assert not qm.screen_exists("EQ_rx_ratio_2")      # prefix of a live session
    assert not qm.screen_exists("rx_ratio_2.0")        # suffix of a live session
    assert not qm.screen_exists("EQ_missing")


def test_screen_exists_with_no_sessions(monkeypatch):
    monkeypatch.setattr(qm, "run", make_run(screen_ls="No Sockets found in /run/screen/S-user.\n"))
    assert not qm.screen_exists("EQ_rx_ratio_2.0")


# --- output_exists -----------------------------------------------------------


def test_output_exists_expands_glob(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "rx_ratio_2.0_seed42.json").write_text("{}")

    assert qm.output_exists("results/rx_ratio_2.0_seed42.json", str(tmp_path))
    assert qm.output_exists("results/rx_ratio_*_seed42.json", str(tmp_path))
    assert qm.output_exists(str(results / "rx_ratio_*.json"), "/unused")
    assert not qm.output_exists("results/rx_ratio_*_seed7.json", str(tmp_path))
    assert not qm.output_exists("", str(tmp_path))
    assert not qm.output_exists(None, str(tmp_path))


def test_required_outputs_exist_with_globs(tmp_path):
    (tmp_path / "results").mkdir()
    (tmp_path / "exchange").mkdir()
    (tmp_path / "results" / "rx_ratio_1.5.json").write_text("{}")
    outputs = {"required": ["results/rx_ratio_*.json", "exchange/cosim_trace*.jsonl"]}
    assert not qm.required_outputs_exist(outputs, str(tmp_path))
    (tmp_path / "exchange" / "cosim_trace.jsonl").write_text("")
    assert qm.required_outputs_exist(outputs, str(tmp_path))


# --- depends_on normalization ------------------------------------------------


def test_normalize_depends_on_shapes():
    assert qm._normalize_depends_on("sanity") == ["sanity"]
    assert qm._normalize_depends_on(["sanity", "baseline"]) == ["sanity", "baseline"]
    assert qm._normalize_depends_on(None) == []
    assert qm._normalize_depends_on([]) == []


def _two_phase_manifest(depends_on):
    sweep = {"name": "sweep", "jobs": [{"id": "rx_ratio_2.0", "cmd": "true"}]}
    if depends_on is not None:
        sweep["depends_on"] = depends_on
    return {
        "project": "rx_pressure",
        "resources": {"slots": [{"id": "sim0", "type": "cpu_sim"}]},
        "phases": [
            {"name": "sanity", "jobs": [{"id": "rx_ratio_1.5", "cmd": "true"}]},
            sweep,
        ],
    }


def test_load_state_fresh_manifest_normalizes_bare_string(tmp_path):
    manifest = _two_phase_manifest("sanity")
    state = qm.load_state(str(tmp_path / "queue_state.json"), manifest)
    deps = {p["name"]: p["depends_on"] for p in state["phases"]}
    assert deps == {"sanity": [], "sweep": ["sanity"]}

    qm.assign_jobs_to_phases(manifest, state)
    assert not qm.phase_ready("sweep", state)
    state["jobs"][0]["status"] = "completed"
    assert qm.phase_complete("sanity", state)
    state["phases"][0]["status"] = "completed"   # what step() section 4 records
    assert qm.phase_ready("sweep", state)
    pending = qm.pending_jobs_in_active_phases(state, manifest)
    assert [j["id"] for j in pending] == ["rx_ratio_2.0"]


def test_load_state_fresh_manifest_keeps_list_and_missing(tmp_path):
    for value, expected in ((["sanity"], ["sanity"]), (None, [])):
        state = qm.load_state(str(tmp_path / "absent.json"), _two_phase_manifest(value))
        assert state["phases"][1]["depends_on"] == expected


def test_load_state_resume_normalizes_bare_string(tmp_path):
    state_file = tmp_path / "queue_state.json"
    state_file.write_text(json.dumps({
        "meta": {"project": "rx_pressure"},
        "phases": [
            {"name": "sanity", "depends_on": None, "status": "completed"},
            {"name": "sweep", "depends_on": "sanity", "status": "pending"},
            {"name": "ablation", "depends_on": ["sanity", "sweep"], "status": "pending"},
        ],
        "jobs": [],
    }))
    state = qm.load_state(str(state_file), {"phases": []})
    deps = {p["name"]: p["depends_on"] for p in state["phases"]}
    assert deps == {"sanity": [], "sweep": ["sanity"], "ablation": ["sanity", "sweep"]}
    assert qm.phase_ready("sweep", state)
    assert not qm.phase_ready("ablation", state)


# --- job_status_check --------------------------------------------------------


def _running_job(pid=4242):
    return {
        "id": "rx_ratio_2.0",
        "phase": "sweep",
        "status": "running",
        "screen_name": "EQ_rx_ratio_2.0",
        "pid": pid,
        "expected_output": "results/rx_ratio_2.0.json",
        "outputs": {},
        "attempts": 1,
        "completed": None,
        "error": None,
    }


def test_job_status_check_stale_screen_is_failed_other(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(qm, "run", make_run(kill_rc=1, calls=calls))
    status, err = qm.job_status_check(_running_job(), str(tmp_path / "logs"), str(tmp_path))
    assert status == "failed_other"
    assert "stale screen" in err
    assert "kill -0 4242 2>/dev/null" in calls


def test_job_status_check_healthy_job_keeps_running(tmp_path, monkeypatch):
    monkeypatch.setattr(qm, "run", make_run(kill_rc=0))
    assert qm.job_status_check(_running_job(), str(tmp_path), str(tmp_path)) == ("running", None)
    # No pid recorded: a live screen is trusted.
    assert qm.job_status_check(_running_job(pid=None), str(tmp_path), str(tmp_path)) == ("running", None)


def test_job_status_check_screen_gone_is_failed_other(tmp_path, monkeypatch):
    monkeypatch.setattr(qm, "run", make_run(screen_ls="No Sockets found.\n"))
    status, err = qm.job_status_check(_running_job(), str(tmp_path), str(tmp_path))
    assert status == "failed_other"
    assert "Screen exited" in err


def test_job_status_check_output_wins_over_dead_screen(tmp_path, monkeypatch):
    monkeypatch.setattr(qm, "run", make_run(screen_ls="No Sockets found.\n"))
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "rx_ratio_2.0.json").write_text("{}")
    assert qm.job_status_check(_running_job(), str(tmp_path), str(tmp_path)) == ("completed", None)


# --- step(): failed_other is terminal ----------------------------------------


def _step_manifest(tmp_path):
    return {
        "cwd": str(tmp_path),
        "resources": {"slots": [{"id": "sim0", "type": "cpu_sim"}]},
        "phases": [{"name": "sweep", "jobs": []}],
    }


def test_step_parks_stale_screen_as_stuck_and_finishes(tmp_path, monkeypatch):
    killed = []
    monkeypatch.setattr(qm, "run", make_run(kill_rc=1))
    monkeypatch.setattr(qm, "kill_screen", killed.append)
    state = {"phases": [{"name": "sweep", "depends_on": [], "status": "running"}],
             "jobs": [_running_job()]}
    state_file = tmp_path / "queue_state.json"

    qm.step(_step_manifest(tmp_path), state, str(state_file), str(tmp_path))

    job = state["jobs"][0]
    assert job["status"] == "stuck"
    assert "stale screen" in job["error"]
    assert killed == ["EQ_rx_ratio_2.0"]
    assert qm.all_done(state)
    assert json.loads(state_file.read_text())["jobs"][0]["status"] == "stuck"


def test_step_parks_resumed_failed_other_as_stuck(tmp_path, monkeypatch):
    monkeypatch.setattr(qm, "run", make_run())
    job = _running_job()
    job.update(status="failed_other", error="Screen exited without expected output",
               completed="2026-10-01T00:00:00Z")
    state = {"phases": [{"name": "sweep", "depends_on": [], "status": "running"}],
             "jobs": [job]}
    assert not qm.all_done(state)

    qm.step(_step_manifest(tmp_path), state, str(tmp_path / "queue_state.json"), str(tmp_path))

    assert state["jobs"][0]["status"] == "stuck"
    assert state["jobs"][0]["attempts"] == 1          # parked, not relaunched
    assert qm.all_done(state)
