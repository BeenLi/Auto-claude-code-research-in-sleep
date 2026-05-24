#!/usr/bin/env python3
"""
verify_papers.py - Pre-search paper-existence verification helper.

Verifies that candidate papers found by literature-search skills actually exist
via 3-layer fallback (arXiv API -> CrossRef DOI lookup -> Semantic Scholar fuzzy
title match). Designed to catch LLM hallucination at search time, before
fabricated references propagate through downstream skills.

Used by `/research-lit` (Step 2.5, mandatory), `/idea-creator`, `/novelty-check`.

Helper resolution chain: `.aris/tools/verify_papers.py` ->
`tools/verify_papers.py` -> `$ARIS_REPO/tools/verify_papers.py`. See
`skills/shared-references/wiki-helper-resolution.md` for the canonical pattern.

CLI:

  python3 verify_papers.py --input papers.json --output verified.json
      [--arxiv-batch-size 40]
      [--s2-fuzzy-threshold 0.6]
      [--cache-scope project|user]
      [--cache-dir PATH]
      [--cache-ttl-days 30]
      [--no-cache]
      [--hallucination-warn-threshold 0.2]

Convenience entries (normalized to the same input schema internally):

  python3 verify_papers.py --arxiv-ids 2307.03172,2401.12345
  python3 verify_papers.py --titles-file titles.txt

Stdin/stdout supported via `-`:

  cat papers.json | python3 verify_papers.py --input - --output -

Input schema (papers.json):

  [
    {"id": "p1", "arxiv_id": "2307.03172", "doi": null, "title": "Lost in the Middle"},
    {"id": "p2", "arxiv_id": null, "doi": "10.1016/...", "title": "AgentAI"},
    {"id": "p3", "arxiv_id": null, "doi": null, "title": "Some Paper"}
  ]

Output schema (verified.json):

  {
    "verdict": "PASS | WARN | BLOCKED | ERROR",
    "hallucination_rate": 0.33,
    "pending_rate": 0.0,
    "warnings": ["high_hallucination_rate"],
    "papers": [
      {"id": "p1", "status": "verified",       "method": "arxiv",    "confidence": "high"},
      {"id": "p2", "status": "verified",       "method": "crossref", "confidence": "high"},
      {"id": "p3", "status": "unverified",     "method": null,       "reason": "no_arxiv_no_doi_no_s2_match"},
      {"id": "p4", "status": "verify_pending", "method": null,       "reason": "transient_api_failure"}
    ]
  }

Status semantics:

  verified        - at least one layer confirmed existence
  unverified      - all applicable layers ran cleanly and found no match
  verify_pending  - any layer hit transient failure (5xx, timeout, rate-limit) and
                    no earlier layer verified; do NOT count against hallucination rate
  error           - input malformed for this entry; rare

Top-level verdict:

  PASS    - hallucination_rate <= threshold AND no pending AND no pre-warnings
  WARN    - hallucination_rate >  threshold OR any pending OR pre-warnings
            (e.g. CrossRef polite-pool email unset, cache write failed)
  BLOCKED - input could not be read or parsed (no usable rows at all)
  ERROR   - verifier crashed mid-run, OR output JSON could not be written
            to the requested --output path. In every case the tool prints
            a verdict-envelope JSON to stdout so downstream callers can
            always `cat verified_papers.json` for a verdict.

Cache key priority: arxiv > doi > title-hash. Cache value retains all identifiers.

Email for CrossRef User-Agent: reads `ARIS_VERIFY_EMAIL` env. When set, the
mailto: parameter is included (CrossRef's "polite pool"). When unset, the
User-Agent is `ARIS-verify-papers/1.0` with no mailto, and the output carries a
`crossref_polite_pool_email_unset` warning (request may be rate-limited
harder). Set the env to opt in to the polite pool:

  export ARIS_VERIFY_EMAIL="you@institution.edu"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

ARXIV_API = "https://export.arxiv.org/api/query"
CROSSREF_API = "https://api.crossref.org/works"
S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"

DEFAULT_BATCH_SIZE = 40
DEFAULT_FUZZY_THRESHOLD = 0.6
DEFAULT_CACHE_TTL_DAYS = 30
DEFAULT_HALLUCINATION_WARN_THRESHOLD = 0.2

ARXIV_VERSION_RE = re.compile(r"v\d+$")
TITLE_NORMALIZE_RE = re.compile(r"[^\w\s]", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")


# --------------------------------------------------------------------------
# Data shapes
# --------------------------------------------------------------------------

@dataclass
class PaperInput:
    id: str
    arxiv_id: str | None = None
    doi: str | None = None
    title: str | None = None


@dataclass
class PaperResult:
    id: str
    status: str  # verified | unverified | verify_pending | error
    method: str | None = None  # arxiv | crossref | s2 | None
    confidence: str | None = None  # high | medium | low
    reason: str | None = None
    identifiers: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Normalization & cache keys
# --------------------------------------------------------------------------

def normalize_arxiv_id(raw: str) -> tuple[str, str | None]:
    """Return (id_without_version, original_version_or_none)."""
    raw = raw.strip()
    m = ARXIV_VERSION_RE.search(raw)
    if m:
        return raw[: m.start()], m.group(0)
    return raw, None


_DOI_URL_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi.org/",
    "dx.doi.org/",
)


def normalize_doi(raw: str) -> str:
    s = raw.strip().lower()
    for prefix in _DOI_URL_PREFIXES:
        if s.startswith(prefix):
            return s[len(prefix):]
    return s


def normalize_title(raw: str) -> str:
    """Lowercase + Unicode NFKD + strip punctuation + collapse whitespace."""
    t = unicodedata.normalize("NFKD", raw).lower()
    t = TITLE_NORMALIZE_RE.sub(" ", t)
    t = WHITESPACE_RE.sub(" ", t).strip()
    return t


def title_hash(normalized: str) -> str:
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def cache_key_for(paper: PaperInput) -> str | None:
    """Priority: arxiv > doi > title hash. None if no identifier."""
    if paper.arxiv_id:
        base, _ = normalize_arxiv_id(paper.arxiv_id)
        return f"arxiv:{base}"
    if paper.doi:
        return f"doi:{normalize_doi(paper.doi)}"
    if paper.title:
        return f"title:{title_hash(normalize_title(paper.title))}"
    return None


# --------------------------------------------------------------------------
# Cache I/O
# --------------------------------------------------------------------------

def resolve_cache_path(scope: str, cache_dir: str | None) -> Path | None:
    """Return cache file path, or None if caching disabled."""
    if cache_dir:
        return Path(cache_dir) / "verify_papers.json"
    if scope == "user":
        return Path.home() / ".aris-cache" / "verify_papers.json"
    if scope == "project":
        return Path(".aris/cache/verify_papers.json")
    return None


def load_cache(path: Path, ttl_days: int) -> dict[str, dict[str, Any]]:
    if not path or not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    now = time.time()
    cutoff = now - ttl_days * 86400
    return {k: v for k, v in raw.items() if v.get("ts", 0) >= cutoff}


def save_cache(path: Path, cache: dict[str, dict[str, Any]]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------
# Retry helpers
# --------------------------------------------------------------------------

def http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> tuple[int, str | None]:
    """Return (status_code, body) or (status_code, None) on error. Status -1 = network error."""
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return -1, None


def is_transient(status: int) -> bool:
    return status == -1 or status == 429 or 500 <= status < 600


def backoff(attempt: int) -> float:
    return min(2 ** attempt + random.uniform(0, 1), 30)


# --------------------------------------------------------------------------
# Layer 1: arXiv batch verification
# --------------------------------------------------------------------------

def verify_arxiv_batch(ids: list[str], batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, str]:
    """Return {arxiv_id: status} where status in {verified, unverified, verify_pending}."""
    if not ids:
        return {}
    result: dict[str, str] = {}
    for i in range(0, len(ids), batch_size):
        batch = ids[i : i + batch_size]
        result.update(_verify_arxiv_batch_with_retry(batch))
    return result


def _verify_arxiv_batch_with_retry(batch: list[str]) -> dict[str, str]:
    """3 retries with exponential backoff. On persistent failure split batch in half."""
    base_ids = [normalize_arxiv_id(x)[0] for x in batch]
    url = f"{ARXIV_API}?id_list={','.join(base_ids)}&max_results={len(base_ids)}"
    for attempt in range(3):
        status, body = http_get(url, timeout=30)
        if status == 200 and body is not None:
            found = set()
            for bid in base_ids:
                if f"<id>http://arxiv.org/abs/{bid}" in body:
                    found.add(bid)
            return {
                orig: "verified" if normalize_arxiv_id(orig)[0] in found else "unverified"
                for orig in batch
            }
        if not is_transient(status):
            # 4xx (non-transient) - likely malformed query; mark whole batch unverified
            return {orig: "unverified" for orig in batch}
        time.sleep(backoff(attempt))
    # Persistent failure - split & retry
    if len(batch) > 1:
        mid = len(batch) // 2
        left = _verify_arxiv_batch_with_retry(batch[:mid])
        right = _verify_arxiv_batch_with_retry(batch[mid:])
        return {**left, **right}
    return {batch[0]: "verify_pending"}


# --------------------------------------------------------------------------
# Layer 2: CrossRef DOI verification
# --------------------------------------------------------------------------

def verify_doi(doi: str, user_email: str | None) -> str:
    """Return verified | unverified | verify_pending."""
    encoded = urllib.parse.quote(normalize_doi(doi), safe="/")
    url = f"{CROSSREF_API}/{encoded}"
    ua = "ARIS-verify-papers/1.0"
    if user_email:
        ua = f"{ua} (mailto:{user_email})"
    headers = {"User-Agent": ua}
    for attempt in range(2):
        status, _ = http_get(url, headers=headers, timeout=15)
        if status == 200:
            return "verified"
        if status == 404:
            return "unverified"
        if not is_transient(status):
            return "unverified"
        time.sleep(backoff(attempt))
    return "verify_pending"


# --------------------------------------------------------------------------
# Layer 3: Semantic Scholar fuzzy title match
# --------------------------------------------------------------------------

def verify_title_s2(title: str, fuzzy_threshold: float) -> tuple[str, dict[str, str] | None]:
    """Return (status, identifiers_dict_or_None)."""
    normalized = normalize_title(title)
    if not normalized:
        return "unverified", None
    q = urllib.parse.quote(normalized[:200])
    url = f"{S2_API}?query={q}&limit=3&fields=title,year,externalIds"
    for attempt in range(2):
        status, body = http_get(url, timeout=15)
        if status == 200 and body is not None:
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return "verify_pending", None
            user_words = set(normalized.split())
            if not user_words:
                return "unverified", None
            for p in data.get("data", []):
                p_norm = normalize_title(p.get("title", ""))
                p_words = set(p_norm.split())
                if not p_words:
                    continue
                overlap = len(user_words & p_words) / max(len(user_words), len(p_words))
                if overlap >= fuzzy_threshold:
                    ext = p.get("externalIds", {}) or {}
                    identifiers = {
                        "s2_title": p.get("title", "") or "",
                        "arxiv_id": ext.get("ArXiv", "") or "",
                        "doi": ext.get("DOI", "") or "",
                    }
                    return "verified", {k: v for k, v in identifiers.items() if v}
            return "unverified", None
        if status == 429:
            return "verify_pending", None
        if not is_transient(status):
            return "unverified", None
        time.sleep(backoff(attempt))
    return "verify_pending", None


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def verify_papers(
    papers: list[PaperInput],
    *,
    arxiv_batch_size: int,
    fuzzy_threshold: float,
    user_email: str | None,
    cache: dict[str, dict[str, Any]] | None,
) -> list[PaperResult]:
    """Run 3-layer verification. Mutates cache if provided."""
    now = time.time()

    # Cache lookup - short-circuit
    results: dict[str, PaperResult] = {}
    to_verify_arxiv: dict[str, list[str]] = {}  # arxiv_id -> [paper_ids]
    to_verify_doi: list[PaperInput] = []
    to_verify_title: list[PaperInput] = []

    for p in papers:
        key = cache_key_for(p)
        if cache is not None and key and key in cache:
            cached = cache[key]
            results[p.id] = PaperResult(
                id=p.id,
                status=cached["status"],
                method=cached.get("method"),
                confidence=cached.get("confidence"),
                reason=cached.get("reason"),
                identifiers=cached.get("identifiers", {}),
            )
            continue
        if p.arxiv_id:
            base, _ = normalize_arxiv_id(p.arxiv_id)
            to_verify_arxiv.setdefault(base, []).append(p.id)
        elif p.doi:
            to_verify_doi.append(p)
        elif p.title:
            to_verify_title.append(p)
        else:
            results[p.id] = PaperResult(
                id=p.id, status="error", reason="no_identifier_no_title"
            )

    # Layer 1: arXiv batch
    if to_verify_arxiv:
        arxiv_results = verify_arxiv_batch(list(to_verify_arxiv.keys()), arxiv_batch_size)
        for base_id, paper_ids in to_verify_arxiv.items():
            status = arxiv_results.get(base_id, "verify_pending")
            for pid in paper_ids:
                results[pid] = PaperResult(
                    id=pid,
                    status=status,
                    method="arxiv" if status == "verified" else None,
                    confidence="high" if status == "verified" else None,
                    reason=None if status == "verified" else f"arxiv_{status}",
                    identifiers={"arxiv_id": base_id},
                )
                if cache is not None:
                    cache[f"arxiv:{base_id}"] = {
                        "status": status,
                        "method": "arxiv" if status == "verified" else None,
                        "confidence": "high" if status == "verified" else None,
                        "reason": None if status == "verified" else f"arxiv_{status}",
                        "identifiers": {"arxiv_id": base_id},
                        "ts": now,
                    }

    # Layer 2: CrossRef
    for p in to_verify_doi:
        status = verify_doi(p.doi or "", user_email)
        result = PaperResult(
            id=p.id,
            status=status,
            method="crossref" if status == "verified" else None,
            confidence="high" if status == "verified" else None,
            reason=None if status == "verified" else f"crossref_{status}",
            identifiers={"doi": normalize_doi(p.doi or "")},
        )
        # If unverified by CrossRef and we have a title, fall through to S2
        if status == "unverified" and p.title:
            s2_status, s2_ids = verify_title_s2(p.title, fuzzy_threshold)
            if s2_status == "verified":
                result = PaperResult(
                    id=p.id,
                    status="verified",
                    method="s2_fallback_from_doi",
                    confidence="medium",
                    identifiers={"doi": normalize_doi(p.doi or ""), **(s2_ids or {})},
                )
            elif s2_status == "verify_pending":
                result.status = "verify_pending"
                result.reason = "crossref_unverified_s2_pending"
        results[p.id] = result
        if cache is not None:
            cache[f"doi:{normalize_doi(p.doi or '')}"] = {
                "status": result.status,
                "method": result.method,
                "confidence": result.confidence,
                "reason": result.reason,
                "identifiers": result.identifiers,
                "ts": now,
            }

    # Layer 3: S2 title only
    for p in to_verify_title:
        s2_status, s2_ids = verify_title_s2(p.title or "", fuzzy_threshold)
        result = PaperResult(
            id=p.id,
            status=s2_status,
            method="s2" if s2_status == "verified" else None,
            confidence="medium" if s2_status == "verified" else None,
            reason=None if s2_status == "verified" else f"s2_{s2_status}",
            identifiers=s2_ids or {},
        )
        results[p.id] = result
        if cache is not None:
            cache[f"title:{title_hash(normalize_title(p.title or ''))}"] = {
                "status": result.status,
                "method": result.method,
                "confidence": result.confidence,
                "reason": result.reason,
                "identifiers": result.identifiers,
                "ts": now,
            }

    return [results[p.id] for p in papers]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

_PAPER_INPUT_KEYS = ("id", "arxiv_id", "doi", "title")


def _coerce_paper_input(d: Any, row_index: int) -> PaperInput:
    if not isinstance(d, dict):
        raise ValueError(f"row {row_index}: expected object, got {type(d).__name__}")
    pid = d.get("id")
    if not isinstance(pid, str) or not pid.strip():
        raise ValueError(f"row {row_index}: missing or empty 'id' field")
    fields = {k: d.get(k) for k in _PAPER_INPUT_KEYS}
    return PaperInput(**fields)


def parse_input(args: argparse.Namespace) -> list[PaperInput]:
    if args.input:
        if args.input == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(args.input).read_text()
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("input must be a JSON array of paper objects")
        return [_coerce_paper_input(d, i) for i, d in enumerate(data)]
    if args.arxiv_ids:
        ids = [x.strip() for x in args.arxiv_ids.split(",") if x.strip()]
        return [PaperInput(id=f"arxiv-{i}", arxiv_id=x) for i, x in enumerate(ids)]
    if args.titles_file:
        path = sys.stdin if args.titles_file == "-" else open(args.titles_file)
        try:
            titles = [line.strip() for line in path if line.strip()]
        finally:
            if path is not sys.stdin:
                path.close()
        return [PaperInput(id=f"title-{i}", title=t) for i, t in enumerate(titles)]
    raise SystemExit("error: provide --input, --arxiv-ids, or --titles-file")


def compute_verdict(
    results: list[PaperResult],
    threshold: float,
    extra_warnings: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    terminal = [r for r in results if r.status in ("verified", "unverified")]
    pending = [r for r in results if r.status == "verify_pending"]
    errors = [r for r in results if r.status == "error"]
    unverified = [r for r in results if r.status == "unverified"]

    h_rate = (len(unverified) / len(terminal)) if terminal else 0.0
    p_rate = (len(pending) / len(results)) if results else 0.0

    warnings: list[str] = list(extra_warnings or [])
    if h_rate > threshold:
        warnings.append("high_hallucination_rate")
    if pending:
        warnings.append("transient_failures_present")
    if errors:
        warnings.append("malformed_inputs_present")

    if not results:
        verdict = "BLOCKED"
    elif errors and not terminal and not pending:
        verdict = "ERROR"
    elif warnings:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return verdict, {
        "hallucination_rate": round(h_rate, 4),
        "pending_rate": round(p_rate, 4),
        "warnings": warnings,
    }


def _emit_error_payload(
    verdict: str,
    warning: str,
    detail: str,
    output_path: str | None,
) -> int:
    """Write a verdict JSON envelope describing a fatal pre-result failure."""
    payload = json.dumps(
        {
            "verdict": verdict,
            "hallucination_rate": 0.0,
            "pending_rate": 0.0,
            "warnings": [warning],
            "papers": [],
            "error": detail,
        },
        indent=2,
        ensure_ascii=False,
    )
    if output_path and output_path != "-":
        try:
            Path(output_path).write_text(payload)
        except OSError:
            # Last resort: still surface payload on stdout so callers can read it.
            print(payload)
            return 3
    else:
        print(payload)
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--input", help="Path to papers.json, or - for stdin")
    ap.add_argument("--output", help="Path to verified.json, or - for stdout (default)")
    ap.add_argument("--arxiv-ids", help="Convenience: comma-separated arXiv IDs")
    ap.add_argument("--titles-file", help="Convenience: file with one title per line, or -")
    ap.add_argument("--arxiv-batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    ap.add_argument("--s2-fuzzy-threshold", type=float, default=DEFAULT_FUZZY_THRESHOLD)
    ap.add_argument("--cache-scope", choices=["project", "user", "none"], default="project")
    ap.add_argument("--cache-dir", help="Explicit cache directory (overrides --cache-scope)")
    ap.add_argument("--cache-ttl-days", type=int, default=DEFAULT_CACHE_TTL_DAYS)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument(
        "--hallucination-warn-threshold",
        type=float,
        default=DEFAULT_HALLUCINATION_WARN_THRESHOLD,
    )
    args = ap.parse_args()

    try:
        papers = parse_input(args)
    except Exception as e:
        return _emit_error_payload("BLOCKED", "input_unreadable", str(e), args.output)

    raw_email = os.environ.get("ARIS_VERIFY_EMAIL", "").strip()
    user_email: str | None = raw_email or None
    pre_warnings: list[str] = []
    if not user_email:
        pre_warnings.append("crossref_polite_pool_email_unset")

    cache: dict[str, dict[str, Any]] | None = None
    cache_path: Path | None = None
    if not args.no_cache and args.cache_scope != "none":
        cache_path = resolve_cache_path(args.cache_scope, args.cache_dir)
        if cache_path:
            cache = load_cache(cache_path, args.cache_ttl_days)

    try:
        results = verify_papers(
            papers,
            arxiv_batch_size=args.arxiv_batch_size,
            fuzzy_threshold=args.s2_fuzzy_threshold,
            user_email=user_email,
            cache=cache,
        )
    except Exception as e:
        return _emit_error_payload("ERROR", "verifier_crashed", str(e), args.output)

    if cache is not None and cache_path:
        try:
            save_cache(cache_path, cache)
        except OSError:
            pre_warnings.append("cache_write_failed")

    verdict, metrics = compute_verdict(
        results,
        args.hallucination_warn_threshold,
        extra_warnings=pre_warnings,
    )
    output = {
        "verdict": verdict,
        **metrics,
        "papers": [asdict(r) for r in results],
    }

    payload = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output and args.output != "-":
        try:
            Path(args.output).write_text(payload)
        except OSError as e:
            return _emit_error_payload(
                "ERROR", "output_write_failed", f"{args.output}: {e}", None
            )
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
