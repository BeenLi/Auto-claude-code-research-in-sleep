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

- Build 3-8 query variants from the original topic, common aliases,
  representative systems/platforms, venue terms, and measurable outcomes found
  in the literature.
- Search direct DBLP/proceedings pages before keyword APIs. Cover current and
  previous year; extend to 5 years for architecture/systems topics.
- De-duplicate in this order: DOI -> arXiv ID -> normalized title. For non-paper
  web artifacts, use exact URL before title.
- Merge source labels into one canonical row. Use `references/search-sources.md`
  for source-specific field precedence.
- For papers without full text, mark `NO FULL TEXT`, limit analysis to
  title/abstract metadata, and keep them in the paper table with that evidence
  limitation exposed.
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

### 3. Analyze Papers

For every relevant paper, extract:

- Problem, method, key result, and relevance
- Source labels and whether it was already known or newly added
- Evaluation platform/backend, benchmark/workload/trace, baselines, metrics,
  artifact/code status, and evaluation limitations

### 4. Synthesize Landscape

Produce:

- Landscape map: 3-6 sub-direction clusters, what each achieved, and where it
  plateaus.
- Consensus and disagreements: field-level agreement, conflicting findings, and
  user-note insights when available.
- Structural gaps using five lenses: cross-domain transfer, contradictory
  findings, untested assumptions, unexplored regimes, and unasked diagnostic
  questions.
- Competitive landscape: top 3 directly competing papers and what they leave
  open.
- `Landscape Pack`: the fixed handoff schema below.

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
- `## Section 1 -- Paper Table` with `Paper | Venue | Year | Method | Key Result | Relevance | Source`.
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
| bottleneck_id | bottleneck | supporting_papers | decisive_metrics |
| --- | --- | --- | --- |

### Mechanism Clusters
| cluster | mechanism_family | representative_papers | plateau_or_missing_piece |
| --- | --- | --- | --- |

### Evaluation Canon
| canon_id | category | item | supporting_papers | adoption_strength | artifact_or_access | limitations | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |

### Core Baseline Candidates
| baseline_id | baseline_name | paper_or_system | scenario | evaluation_platform_used | workload_used | metrics_used | artifact_status | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

### Simulator / Prototype Readiness
| backend | readiness | what_it_can_validate | supporting_papers | blocker |
| --- | --- | --- | --- | --- |

### Gap Seeds
| gap_id | gap_type | bottleneck | supporting_papers | possible_mechanism_hint | minimum validation backend | decisive_metric | main_risk_or_kill_reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
```

Contract rules:

- `Evaluation Canon` is an environment map. It contains only
  `evaluation_platform` and `benchmark_workload` rows.
- Use stable IDs: `EC-P*` for platforms, `EC-W*` for workloads, `CB*` for
  baseline candidates, and `G*` for gap seeds.
- `Core Baseline Candidates` is a candidate pool. Include original platform,
  workload, metrics, and artifact status, but do not force future ideas to reuse
  the same metrics.
- `Gap Seeds` must be grounded in at least one source found during the search or
  explicit negative evidence from the search.
- When a canon item or baseline is weak or missing, write `none_found` or
  `weak_or_missing` and explain the gap in `limitations` or `notes`.

## Key Rules

- Always cite papers with title, authors when available, year, and venue/source.
- Do not claim to search ACM DL or IEEE Xplore directly unless a configured API
  actually succeeded.
- Do not fail because a source is unavailable; degrade gracefully and expose the
  skip in Source Audit.
- The final answer to the user should summarize findings, but the durable output
  is the saved literature review files.
