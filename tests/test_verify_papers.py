from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFY_TOOL = REPO_ROOT / "tools" / "verify_papers.py"


def load_verify_module():
    assert VERIFY_TOOL.exists()
    spec = importlib.util.spec_from_file_location("verify_papers_tool", VERIFY_TOOL)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_verify_papers_tool_exports_input_output_schema() -> None:
    module = load_verify_module()

    required = [
        "PaperInput",
        "PaperResult",
        "parse_input",
        "verify_papers",
        "compute_verdict",
        "normalize_arxiv_id",
        "normalize_doi",
        "normalize_title",
    ]
    for name in required:
        assert hasattr(module, name)

    assert module.normalize_arxiv_id("2307.03172v2") == ("2307.03172", "v2")
    assert module.normalize_doi("https://doi.org/10.1145/123") == "10.1145/123"
    assert module.normalize_title("A  Fast: Paper!") == "a fast paper"


def test_normalize_doi_handles_url_prefixes_and_strip_set_chars() -> None:
    """Regression: previously lstrip(prefix) ate matching leading characters."""
    module = load_verify_module()

    # URL variants
    assert module.normalize_doi("https://doi.org/10.1145/foo") == "10.1145/foo"
    assert module.normalize_doi("http://doi.org/10.1145/foo") == "10.1145/foo"
    assert module.normalize_doi("https://dx.doi.org/10.1145/foo") == "10.1145/foo"
    assert module.normalize_doi("http://dx.doi.org/10.1145/foo") == "10.1145/foo"
    assert module.normalize_doi("doi.org/10.1145/foo") == "10.1145/foo"
    assert module.normalize_doi("dx.doi.org/10.1145/foo") == "10.1145/foo"

    # DOIs whose bodies start with chars in the old lstrip set must survive intact.
    assert module.normalize_doi("https://doi.org/10.1145/sigarch.xxx") == "10.1145/sigarch.xxx"
    assert module.normalize_doi("10.1145/sigarch.xxx") == "10.1145/sigarch.xxx"
    assert module.normalize_doi("10.1109/iccd.foo") == "10.1109/iccd.foo"

    # Case + whitespace normalization
    assert module.normalize_doi("  HTTPS://DOI.ORG/10.1145/Foo  ") == "10.1145/foo"

    # No prefix: unchanged (apart from lower/strip)
    assert module.normalize_doi("not-a-doi") == "not-a-doi"


def test_verify_papers_runs_offline_with_mocked_layers(monkeypatch) -> None:
    module = load_verify_module()

    monkeypatch.setattr(
        module,
        "verify_arxiv_batch",
        lambda ids, batch_size: {ids[0]: "verified", ids[1]: "unverified"},
    )
    monkeypatch.setattr(module, "verify_doi", lambda doi, user_email: "verified")
    monkeypatch.setattr(
        module,
        "verify_title_s2",
        lambda title, threshold: ("unverified", None),
    )

    papers = [
        module.PaperInput(id="p1", arxiv_id="2307.03172"),
        module.PaperInput(id="p2", arxiv_id="9999.99999"),
        module.PaperInput(id="p3", doi="10.1145/123"),
        module.PaperInput(id="p4", title="Unmatched Candidate"),
    ]

    results = module.verify_papers(
        papers,
        arxiv_batch_size=40,
        fuzzy_threshold=0.6,
        user_email="test@example.com",
        cache=None,
    )

    assert [r.status for r in results] == [
        "verified",
        "unverified",
        "verified",
        "unverified",
    ]
    verdict, metrics = module.compute_verdict(results, threshold=0.2)
    assert verdict == "WARN"
    assert metrics["warnings"] == ["high_hallucination_rate"]


def test_zero_verified_papers_warns_instead_of_silent_success() -> None:
    module = load_verify_module()

    results = [
        module.PaperResult(id="p1", status="unverified", reason="s2_unverified"),
        module.PaperResult(id="p2", status="unverified", reason="crossref_unverified"),
    ]

    verdict, metrics = module.compute_verdict(results, threshold=0.2)

    assert verdict == "WARN"
    assert metrics["hallucination_rate"] == 1.0
    assert "high_hallucination_rate" in metrics["warnings"]


def test_parse_input_rejects_rows_without_id(tmp_path) -> None:
    """parse_input must surface which row lacks `id` instead of a bare TypeError."""
    module = load_verify_module()

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"id": "p1", "arxiv_id": "1234.5678"}, {"arxiv_id": "9999.99999"}]))

    args = type("Args", (), {"input": str(bad), "arxiv_ids": None, "titles_file": None})()
    try:
        module.parse_input(args)
    except ValueError as e:
        assert "row 1" in str(e)
        assert "id" in str(e)
    else:
        raise AssertionError("expected ValueError naming the offending row")


def test_parse_input_ignores_unknown_keys(tmp_path) -> None:
    """Typo'd extra keys (e.g. 'arxiv' for 'arxiv_id') must not raise TypeError."""
    module = load_verify_module()

    good = tmp_path / "good.json"
    good.write_text(json.dumps([{"id": "p1", "arxiv": "1234.5678", "arxiv_id": "2307.03172"}]))

    args = type("Args", (), {"input": str(good), "arxiv_ids": None, "titles_file": None})()
    papers = module.parse_input(args)
    assert len(papers) == 1
    assert papers[0].id == "p1"
    assert papers[0].arxiv_id == "2307.03172"


def _run_cli(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VERIFY_TOOL), *args],
        capture_output=True,
        text=True,
        timeout=20,
        **kwargs,
    )


def test_cli_main_emits_blocked_envelope_for_missing_input(tmp_path) -> None:
    """Contract: downstream skills can always `cat verified_papers.json` for a verdict.

    Even when --input points at a non-existent file, the tool must write a
    JSON envelope to --output (not crash before the file is created).
    """
    missing_input = tmp_path / "does-not-exist.json"
    output = tmp_path / "verified.json"

    proc = _run_cli([
        "--input", str(missing_input),
        "--output", str(output),
        "--no-cache",
    ])

    assert proc.returncode != 0
    assert output.exists(), f"output file must exist; stderr={proc.stderr}, stdout={proc.stdout}"
    payload = json.loads(output.read_text())
    assert payload["verdict"] == "BLOCKED"
    assert payload["warnings"] == ["input_unreadable"]
    assert payload["papers"] == []


def test_cli_main_emits_blocked_envelope_for_malformed_json(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not valid json {")
    output = tmp_path / "verified.json"

    proc = _run_cli([
        "--input", str(bad),
        "--output", str(output),
        "--no-cache",
    ])

    assert proc.returncode != 0
    assert output.exists()
    payload = json.loads(output.read_text())
    assert payload["verdict"] == "BLOCKED"
    assert payload["warnings"] == ["input_unreadable"]


def test_cli_main_emits_blocked_envelope_for_row_without_id(tmp_path) -> None:
    """Row-level validation error must produce a BLOCKED envelope, not a stack trace."""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"arxiv_id": "1234.5678"}]))
    output = tmp_path / "verified.json"

    proc = _run_cli([
        "--input", str(bad),
        "--output", str(output),
        "--no-cache",
    ])

    assert proc.returncode != 0
    payload = json.loads(output.read_text())
    assert payload["verdict"] == "BLOCKED"
    assert "row 0" in payload.get("error", "")
