---
name: research-lit
description: Search and analyze research papers, find related work, summarize key ideas. Use when user says "find papers", "related work", "literature review", "what does this paper say", or needs to understand academic papers.
argument-hint: [paper-topic-or-url]
allowed-tools: Bash(*), Read, Glob, Grep, WebSearch, WebFetch, Write, Agent, mcp__zotero__*, mcp__obsidian-vault__*
---

# Research Literature Review

Research topic: $ARGUMENTS

## Role In The Workflow

`research-lit` is the evidence entrypoint for ARIS Workflow 1:

```text
/research-lit -> /idea-creator -> /novelty-check -> /research-review -> /research-refine-pipeline
```

Its job is to map the literature, identify structural gaps, and save a stable
`Landscape Pack` for downstream skills. Keep this file as the execution contract;
use `references/search-sources.md` only when concrete URL patterns or adapter
commands are needed.

## Defaults

| Setting | Default | Notes |
| --- | --- | --- |
| `sources` | `all` | Default sources only: Zotero, Obsidian, local PDFs, arXiv, DBLP/proceedings, WebSearch. Optional sources below require explicit opt-in. |
| `paper library` | `papers/`, then `literature/` | Inline `paper library: /path` wins. Scan at most 20 PDFs, prioritizing relevant filenames. |
| `arxiv download` | `false` | Metadata only unless enabled. Download only top ranked arXiv papers. |
| `max download` | `5` | Applies only when `arxiv download: true`. |
| `reviewer` | `codex` | Optional override: `reviewer: oracle-pro`; see `shared-references/reviewer-routing.md`. |

Supported source names: `zotero`, `obsidian`, `local`, `web`, `semantic-scholar`,
`deepxiv`, `exa`, `gemini`, `openalex`, `all`.

Canonical examples:

```text
/research-lit "KV cache CXL"
/research-lit "RDMA NIC compression" -- sources: all, gemini
/research-lit "topic" -- arxiv download: true, max download: 10
```

Treat `-- sources:`, `- sources:`, and em-dash `sources:` forms as the same
directive.

## Source Policy

### Selection

- If `sources:` is absent or exactly `all`, use default sources.
- If `sources:` lists names, search only those names; `all, gemini` means default
  sources plus Gemini.
- Optional sources `semantic-scholar`, `deepxiv`, `exa`, `gemini`, and
  `openalex` never run unless explicitly listed.
- Missing tools, MCP servers, scripts, dependencies, credentials, or rate limits
  must not stop the workflow. Record the skip in Section 0 Source Audit.

### Source Adapters

| Priority | Source | ID | Detect | Explicit-only? |
| --- | --- | --- | --- | --- |
| 1 | Zotero | `zotero` | Any Zotero MCP tool succeeds | No |
| 2 | Obsidian | `obsidian` | Any Obsidian MCP tool succeeds | No |
| 3 | Local PDFs | `local` | `papers/**/*.pdf` or `literature/**/*.pdf` | No |
| 4 | DBLP / proceedings | `web` | WebFetch/WebSearch | No |
| 5 | arXiv | `web` | `tools/arxiv_fetch.py` or WebSearch | No |
| 6 | WebSearch fallback | `web` | WebSearch | No |
| 7 | Semantic Scholar | `semantic-scholar` | `tools/semantic_scholar_fetch.py` | Yes |
| 8 | DeepXiv | `deepxiv` | `tools/deepxiv_fetch.py` and DeepXiv CLI | Yes |
| 9 | Exa | `exa` | `tools/exa_search.py` and SDK | Yes |
| 10 | Gemini | `gemini` | Gemini MCP or CLI | Yes |
| 11 | OpenAlex | `openalex` | `tools/openalex_fetch.py` and `requests` | Yes |

For exact commands, DBLP/program URL patterns, and adapter-specific fallback
details, use `references/search-sources.md`.

### Retrieval Rules

- Build 3-8 query variants from the original topic and its common aliases or
  synonyms only (see `references/search-sources.md` -> Query Alias Patterns
  for derivation guidance). Do not mix in system names, venue terms, or
  evaluation metrics at this stage; they tend to retrieve unrelated work.
- Search direct DBLP/proceedings pages before keyword APIs. Cover current and
  previous year; extend to 5 years for architecture/systems topics.
- De-duplicate in this order: DOI -> arXiv ID -> normalized title. For non-paper
  web artifacts, use exact URL before title.
- Merge source labels into one canonical row. Use `references/search-sources.md`
  for source-specific field precedence.
- For papers without full text, mark `NO FULL TEXT`, limit analysis to
  title/abstract metadata, and keep them in the paper table with that evidence
  limitation exposed.
- Treat arXiv and other preprints as important evidence for fast-moving AI
  infrastructure work, but expose evidence maturity instead of flattening them
  with peer-reviewed proceedings: preprint status, full-text availability, and
  artifact/code status must be exposed as dedicated columns in the Section 1
  Paper Table (see `## Required Output Shape`); evaluation limitations belong
  in the per-paper analysis. Source Audit is per-source (skips, rate limits,
  missing credentials), not per-paper maturity.
- If `arxiv download: true`, download only top ranked arXiv papers into the
  resolved paper library; verify each PDF is larger than 10 KB.

## Workflow

### 1. Load Prior Review

If `idea-stage/LITERATURE_REVIEW.md` exists, load it first. Treat existing
papers as known, preserve useful landscape context, and search only for new or
missing papers unless the user requests a full refresh. Mark new rows with `NEW`
in the output.

### 2. Collect Evidence

Search requested sources in the Source Policy order. For Zotero, traverse
fragment-matched collections at any depth before keyword search. Prefer
curated/user sources, then direct venue/arXiv coverage, then optional adapters,
then WebSearch fallback. Maintain a Source Audit row for every attempted source.

### 2.5. Verify Candidate Papers

Before analyzing or citing candidate papers, verify paper existence with the
canonical helper. This step is mandatory even when the candidate came from an
LLM, a user note, a stale prior review, or a search snippet.

Papers loaded from a prior `idea-stage/LITERATURE_REVIEW.md` (Step 1) must also
flow through this gate: if their `Verification` column is already `verified`,
trust it and skip re-verification; otherwise re-emit them as candidate rows.
Do not leave any Section 1 row without a `Verification` value.

Write candidate rows before verification:

```text
.aris/verify-papers/candidate_papers.json
```

Use a list of objects with stable `id`, and best-known `arxiv_id`, `doi`, and
`title` fields.

Then resolve and invoke the helper. `python3` is a hard prerequisite — if
missing, stop the workflow with a `BLOCKED` outcome. If the helper itself is
missing on disk, write a degraded `BLOCKED` envelope so downstream skills
always have a JSON receipt to read (per the [integration
contract](../shared-references/integration-contract.md)):

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
  # Treat as BLOCKED per the rules below.
  exit 1
fi

python3 "$VERIFY_SCRIPT" \
  --input .aris/verify-papers/candidate_papers.json \
  --output "$VERIFY_OUTPUT"
```

The paper-level status vocabulary is `verified`, `unverified`, `verify_pending`, and `error`.
The top-level verdict vocabulary is `PASS`, `WARN`, `BLOCKED`, and `ERROR`.

Handling rules:

- `PASS`: proceed normally.
- `WARN` continues with degraded output. All `unverified`, `verify_pending`,
  or `error` evidence must be explicitly marked in Section 1 and any prose that
  relies on it. A `WARN` review must not be treated as a ready handoff signal by
  downstream skills.
- `BLOCKED` prevents saving the literature review. Fix helper resolution,
  malformed input/output paths, or unreadable candidate JSON before continuing.
- `ERROR` means the verifier crashed or output could not be written; retry once,
  then treat it as `BLOCKED` unless the user explicitly accepts a diagnostic-only
  run.
- If there are zero verified papers, treat the verifier verdict as `WARN` and
  produce a degraded review only if the user explicitly wants a scoping summary;
  otherwise stop before saving durable literature outputs.

### 3. Analyze Papers

For every relevant paper, extract:

- Problem, method, key result, limitations, and relevance
- Source labels and whether it was already known or newly added
- Verification status from `.aris/verify-papers/verified_papers.json`.
- Evaluation platform/backend, benchmark/workload/trace, comparison systems,
  metrics, artifact/code status, and evaluation limitations.

### 4. Synthesize Landscape

Produce:

- Landscape map: 3-6 clusters keyed by concrete unresolved problems or
  bottlenecks specific to the current topic, not generic systems-domain
  headings. For a topic such as `KV cache CXL`, prefer clusters like
  "page-granular CXL migration still causes tail-latency spikes" over a broad
  resource label. For broad topics, still phrase each cluster as one primary
  unresolved problem or bottleneck. For each cluster, state the unresolved
  problem/bottleneck, solution attempts already tried, what those attempts
  achieved and where they plateau, scenario/evaluation limitations including
  workload coverage, hardware coverage, artifact maturity, and
  `EC-P*.limitations` / `EC-W*.limitations` references where applicable, the
  hardware generation or `hardware-agnostic` status, and the
  workload/model-size class when evidence permits. These problem clusters
  should directly ground Section 5 `B*` bottlenecks and `S*` solution attempts.
- Consensus and disagreements belong in Section 2: for each cluster, summarize
  field-level agreement, conflicting findings, quantifiable metrics when
  available, and user-note conflicts or qualifications from Zotero/Obsidian
  when available.
- Structural gaps use five lenses: cross-domain transfer, contradictory
  findings, untested assumptions, unexplored regimes, and unasked diagnostic
  questions. Produce 1-2 grounded gaps per applicable lens and no more than 8
  total unless the user explicitly requests a broader survey. Every gap must be
  anchored to a `B*` bottleneck, an `S*` solution attempt, or explicit negative
  evidence from the search.
- Competitive landscape: top 3 directly competing papers, or fewer when the
  field is sparse with a short reason. Treat directly competing as sharing the
  same `B*` bottleneck, comparable workload class, and comparable
  hardware/system tier when possible. Identify what each competitor solves and
  where it leaves residual evaluation or mechanism gaps; do not mint global
  baseline candidates here.
- `Landscape Pack`: the fixed handoff schema below. Treat Section 5 as the
  ID-backed projection of Sections 2-4, not as a parallel summary. Mint
  `B*`/`S*`/`EC-P*`/`EC-W*`/`G*` IDs while drafting the Landscape Pack schema
  first, then cite those same IDs in Sections 2-4 prose; if any Section 2-4
  paragraph was drafted before the ID existed, backfill the citation before
  saving. Section 3 carries lens-shaped narrative; `Gap Seeds` carries
  actionable `G*` rows derived from `B*.residual_gap`,
  `S*.missing_piece`, or explicit negative evidence.

### 5. Save Outputs

Always save both files:

```text
idea-stage/LITERATURE_REVIEW_{YYYYMMDD_HHmmssZ}.md
idea-stage/LITERATURE_REVIEW.md
```

Use UTC timestamps. Write the timestamped file first, copy the same content to
the fixed latest copy, and append both rows to `MANIFEST.md` with stage
`idea-discovery`. Downstream skills always read `idea-stage/LITERATURE_REVIEW.md`.

### 6. Update Research Wiki

If `research-wiki/` exists, run the ingest hook. If it does not exist, skip this
step silently.

Resolve the helper using the shared contract in
`shared-references/wiki-helper-resolution.md`: prefer `.aris/tools/research_wiki.py`,
then `tools/research_wiki.py`, then `$ARIS_REPO/tools/research_wiki.py`. If no
helper is found, warn and skip wiki ingest only; do not skip the literature
review output.

For the top 8-12 relevant arXiv papers:

```bash
python3 "$WIKI_SCRIPT" ingest_paper research-wiki/ --arxiv-id <id> --thesis "<one-line>"
```

For non-arXiv papers, call the same helper with manual title/authors/year/venue
metadata and DOI when available.

`ingest_paper` owns slugging, deduplication, page creation, index rebuild,
`query_pack.md` rebuild, and log append. Do not manually write paper pages.

## Required Output Shape

The saved review must contain:

- Header: generation UTC timestamp, skill name, and original topic.
- `## Section 0 -- Source Audit` with `Source | Status | Action Taken / Notes`.
- `## Section 1 -- Paper Table` with `| Paper | Venue | Year | Method | Key Result | Relevance | Source | Verification | Preprint | Full Text | Artifact |`. `Verification` is `verified|unverified|verify_pending|error` from `verified_papers.json`. `Preprint` is `yes|no` (peer-reviewed = `no`). `Full Text` is `yes|no` (use `no` for `NO FULL TEXT` rows). `Artifact` is `yes|partial|no|unknown` (code/data availability, prefer artifact-evaluation badges when present).
- `## Section 2 -- Landscape Map`.
- `## Section 3 -- Structural Gaps`.
- `## Section 4 -- Competitive Landscape`.
- `## Section 5 -- Landscape Pack`.

Section 3 is for human reading. Section 5 is the primary machine-readable handoff
for `/idea-creator`.

## Landscape Pack Contract

Keep these headings and field names stable.

```markdown
## Landscape Pack

### Topic Scope
- original_topic:

### Bottleneck Evidence

#### Bottlenecks
| bottleneck_id | bottleneck | context | decisive_metrics | representative_papers | current_status | residual_gap |
| --- | --- | --- | --- | --- | --- | --- |

#### Solution Attempts
| solution_id | bottleneck_ids | mechanism_family | representative_papers | best_outcome | missing_piece |
| --- | --- | --- | --- | --- | --- |

### Evaluation Canon

#### Platforms
| platform_id | platform_or_backend | backend_readiness | workloads | validates | artifact_access_path | blockers_or_limitations |
| --- | --- | --- | --- | --- | --- | --- |

#### Workloads
| workload_id | workload | bottlenecks | metrics | representative_papers | limitations |
| --- | --- | --- | --- | --- | --- |

### Gap Seeds
| gap_id | bottleneck_id | source_residual | mechanism_hint | validation_target | decisive_metric | kill_reason |
| --- | --- | --- | --- | --- | --- | --- |
```

Contract rules:

- Preserve the top-level headings exactly: `Topic Scope`, `Bottleneck Evidence`,
  `Evaluation Canon`, and `Gap Seeds`.
- `Bottleneck Evidence` contains `Bottlenecks` and `Solution Attempts`.
  Use stable `B*` IDs for bottlenecks and `S*` IDs for solution attempts.
- `Evaluation Canon` contains `Platforms` and `Workloads`, not mixed rows
  selected by a category column. Use stable `EC-P*` IDs for platforms and
  `EC-W*` IDs for workloads. `Evaluation Canon > Platforms` must absorb
  backend/prototype readiness, artifact/access path, and blocker information;
  do not create a separate readiness heading.
- `Gap Seeds` must be grounded in at least one source found during the search or
  explicit negative evidence from the search. Structural gap categories belong
  in Section 3 prose, not in the machine-readable `Gap Seeds` table.
- When a canon item is weak or missing, write `none_found` or `weak_or_missing`
  and explain the gap in `blockers_or_limitations`.
- `S*.bottleneck_ids` is a comma-separated list of `B*` IDs (one solution may
  address multiple bottlenecks). Every entry must resolve to a `B*`.
- Every `EC-P*.validates` entry must resolve to `B*` or `S*`.
- Every `EC-W*.bottlenecks` entry must resolve to `B*`.
- Every `G*.bottleneck_id` must resolve to `B*`.
- Every `G*.source_residual` must point to `B*.residual_gap`, `S*.missing_piece`, or explicit negative evidence.
- No Landscape Pack table should exceed 7 columns.

## Key Rules

- Always cite papers with title, authors when available, year, and venue/source.
- Do not claim to search ACM DL or IEEE Xplore directly unless a configured API
  actually succeeded.
- Do not fail because a source is unavailable; degrade gracefully and expose the
  skip in Source Audit.
- The final answer to the user should summarize findings, but the durable output
  is the saved literature review files.
