# Verify Candidate Papers Reference

This reference is the operational contract for `/research-lit` Step 2.5.
Use it whenever candidate papers must be checked before analysis, citation,
Landscape Pack construction, or downstream baseline handoff.

## Activation

Run this gate after evidence collection and before paper analysis. Candidate
papers from all sources must pass through it, including:

- search results,
- LLM-suggested or adapter-suggested papers,
- user notes,
- stale prior reviews,
- papers loaded from `idea-stage/LITERATURE_REVIEW.md`.

For papers loaded from a prior `idea-stage/LITERATURE_REVIEW.md`, trust rows
whose `Verification` column is already `verified`; otherwise re-emit them as
candidate rows. Do not leave any Section 1 row without a `Verification` value.

## Candidate Artifact

Write candidate rows before verification:

```text
.aris/verify-papers/candidate_papers.json
```

Use a JSON list. Each object must have a stable `id` and the best-known
identifier fields:

```json
[
  {
    "id": "p1",
    "arxiv_id": "2307.03172",
    "doi": null,
    "title": "Example Paper Title"
  }
]
```

## Helper Resolution And Invocation

Resolve and invoke the helper. `python3` is a hard prerequisite. If it is
missing, stop the workflow with a `BLOCKED` outcome. If the helper itself is
missing on disk, write a degraded `BLOCKED` envelope so downstream skills always
have a JSON receipt to read, per the shared integration contract.

```bash
mkdir -p .aris/verify-papers
VERIFY_OUTPUT=".aris/verify-papers/verified_papers.json"

command -v python3 >/dev/null 2>&1 || {
  echo "BLOCKED: python3 is required for verify_papers.py" >&2
  python3 - <<'PY' >"$VERIFY_OUTPUT" 2>/dev/null || cat >"$VERIFY_OUTPUT" <<'JSON'
{
  "verdict": "BLOCKED",
  "hallucination_rate": 0.0,
  "pending_rate": 0.0,
  "warnings": ["python3_missing"],
  "papers": [],
  "error": "python3 not on PATH"
}
JSON
  exit 1
}

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
ARIS_REPO="${ARIS_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills.txt 2>/dev/null)}"
VERIFY_SCRIPT=".aris/tools/verify_papers.py"
[ -f "$VERIFY_SCRIPT" ] || VERIFY_SCRIPT="tools/verify_papers.py"
[ -f "$VERIFY_SCRIPT" ] || { [ -n "${ARIS_REPO:-}" ] && VERIFY_SCRIPT="$ARIS_REPO/tools/verify_papers.py"; }
if [ ! -f "$VERIFY_SCRIPT" ]; then
  echo "BLOCKED: verify_papers.py not found at .aris/tools/, tools/, or \$ARIS_REPO/tools/." >&2
  python3 - "$VERIFY_OUTPUT" .aris/verify-papers/candidate_papers.json <<'PY'
import json, sys
out_path, in_path = sys.argv[1], sys.argv[2]
try:
    candidates = json.loads(open(in_path).read())
except Exception:
    candidates = []
papers = [
    {
        "id": (c.get("id") or f"row-{i}") if isinstance(c, dict) else f"row-{i}",
        "status": "unverified",
        "method": None,
        "confidence": None,
        "reason": "verifier_missing",
        "identifiers": {},
    }
    for i, c in enumerate(candidates)
]
json.dump(
    {
        "verdict": "BLOCKED",
        "hallucination_rate": 0.0,
        "pending_rate": 0.0,
        "warnings": ["verifier_missing"],
        "papers": papers,
        "error": "verify_papers.py not resolvable; rerun bash tools/install_aris.sh or set ARIS_REPO",
    },
    open(out_path, "w"),
    indent=2,
    ensure_ascii=False,
)
PY
  exit 1
fi

python3 "$VERIFY_SCRIPT" \
  --input .aris/verify-papers/candidate_papers.json \
  --output "$VERIFY_OUTPUT"
```

## Result Artifact

The verifier writes:

```text
.aris/verify-papers/verified_papers.json
```

Paper-level status vocabulary is `verified`, `unverified`, `verify_pending`, and `error`.

- `verified`
- `unverified`
- `verify_pending`
- `error`

Top-level verdict vocabulary is `PASS`, `WARN`, `BLOCKED`, and `ERROR`.

- `PASS`
- `WARN`
- `BLOCKED`
- `ERROR`

## Verdict Handling

- `PASS`: proceed normally.
- `WARN` continues with degraded output. Explicitly mark all `unverified`,
  `verify_pending`, or `error` evidence in Section 1 and in prose that relies on
  it. A `WARN` review cannot produce ready handoff evidence.
- `BLOCKED` prevents saving the literature review. Fix helper
  resolution, malformed input/output paths, or unreadable candidate JSON first.
- `ERROR`: retry once. If it repeats, treat as `BLOCKED` unless the user
  explicitly accepts a diagnostic-only run.
- If there are zero verified papers, treat as `WARN`; produce a degraded scoping summary only
  if the user explicitly wants it, otherwise stop before saving durable outputs.
