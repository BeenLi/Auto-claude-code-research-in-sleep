---
name: research-lit
description: Search and analyze research papers, find related work, summarize key ideas. Use when user says "find papers", "related work", "literature review", "what does this paper say", or needs to understand academic papers.
argument-hint: [paper-topic-or-url]
allowed-tools: Bash(*), Read, Glob, Grep, WebSearch, WebFetch, Write, Agent, mcp__zotero__*, mcp__obsidian-vault__*
---

# Research Literature Review

Research topic: $ARGUMENTS  _(if $ARGUMENTS is a `.md` path, topic and context are extracted from the brief in Step 0)_

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

### 0. Detect Input Mode and Load Context

Detect the input mode from `$ARGUMENTS` before any other step. Modes are
mutually exclusive — do not combine a topic string with research brief or paper reference.
Log one line after detection: `Input mode: <1|2|3> — <topic | brief path | paper title/URL>`

| Mode | Detection rule | Search framing |
| --- | --- | --- |
| 1 — Topic | Plain string; does not match mode 2 or 3 rules | Broad exploration of the topic area |
| 2 — Research Brief | Ends with `.md` and the file exists | Scoped, constrained search driven by stated intent |
| 3 — Reference Paper | Matches `http(s)://`, bare arXiv ID (`\d{4}\.\d{4,5}`), DOI (`10\.\d{4,}/`), or ends with `.pdf` | "Can we improve this?" — treat paper as SOTA; search for competing/related work |

Canonical examples:

```text
/research-lit "KV cache CXL"                                    (mode 1 — topic)
/research-lit "idea-stage/RESEARCH_BRIEF.md"                    (mode 2 — brief)
/research-lit "https://arxiv.org/abs/2406.04329"                (mode 3 — arXiv URL)
/research-lit "2406.04329"                                      (mode 3 — bare arXiv ID)
/research-lit "papers/baseline.pdf"                             (mode 3 — local PDF)
/research-lit "10.1145/3725843.3756079"                         (mode 3 — DOI)
```

#### Mode 1 — Topic

If `$ARGUMENTS` is a plain string, use it as the research topic. Broad exploration of the topic area.

#### Mode 2 — Research Brief

If `$ARGUMENTS` ends with `.md` and the file exists, read it and extract the
following fields before any other step. These extracted values replace
`$ARGUMENTS` as the effective research context for all subsequent steps.

| Field | Source section in Brief | How it is used |
| --- | --- | --- |
| `topic` | Title line + `## Problem Statement` (first 2 sentences) | Replaces `$ARGUMENTS` as the search direction |
| `known_papers` | `## Background` → `Key papers I've read` bullet list | Must be included in Step 3 Analyze Papers — treat as mandatory coverage; discovered through normal search flow |
| `constraints` | `## Constraints` | Scope the search: honour venue/timeline focus, limit evaluation platforms to those listed |
| `non_goals` | `## Non-Goals` | Exclude these directions from gap analysis and Gap Seeds |
| `domain_knowledge` | `## Domain Knowledge` | Seed query variants and inform cluster framing in Section 2 |

Extraction rules:
- Parse with best effort; missing sections are silently skipped.
- `known_papers`: extract each bullet's paper title (bold or plain) and any URL present.
- `constraints.venue`: if listed, prefer papers and evaluation setups relevant to that venue's scope.
- After extraction, log: `Brief loaded: topic="<topic>", known=<N> papers, non-goals=<N>`.
- If the file does not exist or cannot be read, fall back to treating `$ARGUMENTS` as a plain topic string.

#### Mode 3 — Reference Paper

Fetch and read the **complete paper** — no page limit; this paper is the
primary research input and must be fully understood before searching.

- arXiv URL or bare ID: download PDF via the arxiv adapter or fetch full text via WebFetch.
- Local PDF path (ends with `.pdf`): read the complete PDF.
- DOI or other URL: fetch full content via WebFetch.

Extract from the full paper: `title`, `authors`, `venue`, `year`, `problem`
(primary problem the paper addresses), `method` (core technical approach),
`key_results` (main quantitative findings), `limitations` (acknowledged or
inferable weaknesses), `open_questions` (future work or unresolved issues).

Write `idea-stage/REF_PAPER_SUMMARY.md` before continuing:

```markdown
# Reference Paper Summary

**Title**: [paper title]
**Authors**: [authors]
**Venue**: [venue, year]

## What They Did
[2-3 sentences: core method and contribution]

## Key Results
[Main quantitative findings]

## Limitations & Open Questions
[What the paper did not solve, acknowledged weaknesses, future work suggestions]

## Potential Improvement Directions
[Directions implied by the limitations and open questions]
```

Derive `topic` from `problem`. Add this paper to `known_papers` as mandatory
coverage. Apply this framing to all subsequent steps:

> **SOTA baseline framing**: this paper is the current best-known solution.
> Search for competing and related work. Section 2 clusters ask "where does
> this paper plateau?" Gap Seeds ask "what does this paper leave unsolved,
> and how could it be improved or extended?"

Log: `Ref paper loaded: title="<title>", topic derived="<topic>", venue="<venue> <year>"`.

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

Follow `references/verify-candidate-papers.md` for the full operational flow:
prior-review reuse rules, candidate JSON schema, helper resolution, degraded
`BLOCKED` receipt creation, verifier invocation, status vocabulary, and
verdict handling.

Required artifacts:

- `.aris/verify-papers/candidate_papers.json`
- `.aris/verify-papers/verified_papers.json`

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

For every relevant paper, extract and write into Section 1:

- Problem, method, key result, limitations, and relevance.
- Source labels and whether it was already known or newly added.
- Verification status from `.aris/verify-papers/verified_papers.json`.
- Evaluation platform/substrate → `Eval Platform` column (e.g., `BF3 DPU`, `A100 cluster`, `LLMServingSim`); use `none/NA` when not reported.
- Benchmark/workload/trace → `Workload` column (e.g., `NCCL AllReduce`, `GPT-3 175B prefill`); use `none/NA` when not reported.
- Comparison systems → `Baseline` column (e.g., `raw RDMA`, `PEDAL`, `vLLM 0.4`); use `none/NA` when not reported.
- Metrics, artifact/code status, and evaluation limitations (these feed Section 4 Evaluation Canon `EC-P*`/`EC-W*` rows).

### 4. Synthesize Landscape

Mint `B*`/`S*`/`C*`/`EC-P*`/`EC-W*`/`G*` IDs while drafting Section 4 first, then
backfill those IDs into Sections 2-3 prose; if any Section 2-3 paragraph was drafted
before the ID existed, backfill the citation before saving.

#### Section 2 -- Problem-Anchored Clusters

Produce 3-6 clusters keyed by concrete unresolved problems or bottlenecks specific to
the current topic, not generic systems-domain headings. For a topic such as `KV cache
CXL`, prefer clusters like "page-granular CXL migration still causes tail-latency
spikes" over a broad resource label. For broad topics, still phrase each cluster as one
primary unresolved problem or bottleneck. For each cluster, state the unresolved
problem/bottleneck, solution attempts already tried, what those attempts achieved and
where they plateau, scenario/evaluation limitations including workload coverage,
hardware coverage, artifact maturity, and `EC-P*.platform_limitations` /
`EC-W*.representativeness_limits` references where applicable, the hardware generation
or `hardware-agnostic` status, and the workload/model-size class when evidence permits.
These problem clusters should directly ground Section 4 `B*` bottlenecks and `S*`
solution attempts.

For each cluster also summarize field-level agreement, conflicting findings,
quantifiable metrics when available, and user-note conflicts or qualifications from
Zotero/Obsidian when available.

#### Section 2.5 -- Negative Evidence

Identify 0-5 findings in the candidate set that either (a) refute a field-wide hidden
assumption shared by most `S*` solution attempts, (b) report a structural failure mode
shared by >=3 mainstream baselines on a benchmark (e.g., near-zero accuracy where the
field-standard metric would predict success), or (c) expose a failure mode that
aggregate benchmark scores in this topic hide. Incremental "we beat SOTA by X%" results
do NOT qualify. Each finding becomes a `NE-*` row in Section 2.5 with `claim`,
`source` paper(s), `affected_methods` (list of `S*` IDs or paper names),
`affected_assumption`, `confidence` (`high` = independently reproduced or multi-baseline
at multiple budgets; `medium` = single-paper multi-baseline; `low` = single-paper
single-baseline), and `linked_gaps` (G* IDs that build on this). If no qualifying
evidence is present, write `none_identified` as a single row with a one-line reason.

#### Section 3 -- Structural Gaps

Use five lenses: cross-domain transfer, contradictory findings, untested assumptions,
unexplored regimes, and unasked diagnostic questions. Produce 1-2 grounded gaps per
applicable lens and no more than 8 total unless the user explicitly requests a broader
survey. Every gap must be anchored to a `B*` bottleneck, an `S*` solution attempt, or a
`NE-*` negative evidence row from Section 2.5 (when Section 2.5 has `none_identified`,
gaps may still cite raw negative evidence from the search but cannot cite `NE-*` IDs).

#### Section 4 -- Landscape Pack

Section 4 is the machine-readable handoff for `/idea-creator`. Treat it as the
ID-backed projection of Sections 2-3, not as a parallel summary. Section 3 carries
lens-shaped narrative; `Gap Seeds` carries actionable `G*` rows derived from
`B*.residual_gap`, `S*.missing_piece`, or explicit negative evidence.

The `Competitive Landscape` sub-section of Section 4 contains the top 3 directly
competing papers (or fewer when the field is sparse, with a one-line reason). Treat
directly competing as sharing the same primary `B*` bottleneck, comparable workload
class, and comparable hardware/system tier when possible. Identify what each competitor
solves and where it leaves residual evaluation or mechanism gaps; do not mint global
baseline candidates here. Write the two fixed sub-tables (Competitors + Excluded
Competitors) defined in `## Landscape Pack Contract`. Hard rules:

- `selection_rule`: rank candidates by (1) workload-class overlap with the scope's
  `decisive_metrics`, then (2) `best_outcome` on those metrics, then (3) recency;
  break further ties by preferring papers with public artifact. Record the chosen rule
  in one line above the Competitors table when it deviates from this default.
- Scope is anchored to a single `primary_B*`. Cross-bottleneck competitors belong in
  the same Competitors table with their `B*_scope` cell written as
  `B<primary> (adj: B<secondary>, ...)`. Do not split the Competitive Landscape
  sub-section into multiple Competitors tables per bottleneck.
- NE-* coupling (hard gate): every paper appearing in the `source` column of a `NE-*`
  row in Section 2.5, when it shares the `primary_B*`, must appear either in the
  Competitors table or in the Excluded Competitors table. If excluded,
  `excluded_reason` must explain why the negative evidence does not warrant inclusion
  (e.g., different `eval_tier`).
- Excluded Competitors table is required (not optional) whenever any paper from a
  shared `B*` is dropped from the top-3. Use `none_excluded` as a single placeholder
  row when no qualifying paper was dropped.

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
- `## Section 1 -- Paper Table` with `| Paper | Venue | Year | Method | Key Result | Eval Platform | Workload | Baseline | Relevance | Source | Verification | Preprint | Full Text | Artifact |`. `Verification` is `verified|unverified|verify_pending|error` from `verified_papers.json`. `Preprint` is `yes|no` (peer-reviewed = `no`). `Full Text` is `yes|no` (use `no` for `NO FULL TEXT` rows). `Artifact` is `yes|partial|no|unknown` (code/data availability, prefer artifact-evaluation badges when present). `Eval Platform` is the hardware/system/simulator used (e.g., `BF3 DPU`, `A100 cluster`, `LLMServingSim`). `Workload` is the benchmark, trace, or task class (e.g., `NCCL AllReduce`, `GPT-3 prefill`). `Baseline` is the primary comparison system(s) (e.g., `raw RDMA`, `PEDAL`). All three use `none/NA` when not reported.
- `## Section 2 -- Problem-Anchored Clusters`.
- `## Section 2.5 -- Negative Evidence`. Fixed table with columns
  `| negative_id | claim | source | affected_methods | affected_assumption | confidence | linked_gaps |`.
  `negative_id` is `NE-1`, `NE-2`, ... `confidence` is `high|medium|low` (see
  Workflow Step 4 for the rule). `affected_methods` lists `S*` IDs or paper
  names of methods refuted by the finding; `linked_gaps` lists `G*` IDs from
  Section 4 Gap Seeds that build on this. If nothing in the candidate set
  qualifies, the table contains exactly one row: `NE-NONE | none_identified | n/a | n/a | n/a | n/a | n/a` and a one-line reason below.
  This section is a HARD GATE for `/idea-creator`: ideas whose hidden assumption
  is listed in `affected_assumption` must either be eliminated or explicitly
  declare how they evade or address that assumption.
- `## Section 3 -- Structural Gaps`.
- `## Section 4 -- Landscape Pack`. Contains sub-sections: `Topic Scope`,
  `Bottleneck Evidence`, `Evaluation Canon`, `Gap Seeds`, and
  `Competitive Landscape`. The `Competitive Landscape` sub-section holds two
  fixed tables (Competitors + Excluded Competitors); see `## Landscape Pack
  Contract` for the full schema and field rules.

Section 3 is for human reading. Section 2.5 is a small, structured table read by
`/idea-creator` as a hard gate. Section 4 is the primary machine-readable
handoff for `/idea-creator`.

## Landscape Pack Contract

Keep these headings and field names stable. In all `representative_papers` cells use
Markdown link format: `[Short Title](URL)` where URL is `https://doi.org/<DOI>` for
peer-reviewed papers or `https://arxiv.org/abs/<ID>` for preprints; fall back to a
plain title when no confirmed URL is available.

```markdown
## Section 4 -- Landscape Pack

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
| platform_id | evaluation_platform | access_readiness | supported_workloads | validates_refs | artifact_access_path | platform_limitations |
| --- | --- | --- | --- | --- | --- | --- |

#### Workloads
| workload_id | workload | bottlenecks | workload_characteristics | representative_papers | representativeness_limits |
| --- | --- | --- | --- | --- | --- |

### Competitive Landscape

selection_rule: <rule>  _(omit this line when the default rule was used)_

#### Competitors
| competitor_id | papers | B*_scope | eval_tier | what_it_solves | residual_gap | NE_link |
| --- | --- | --- | --- | --- | --- | --- |

#### Excluded Competitors
| excluded_paper | shared_B* | eval_tier | excluded_reason | revisit_condition |
| --- | --- | --- | --- | --- |

### Gap Seeds
| gap_id | bottleneck_id | source_gap_ref | mechanism_hint | validation_target | decisive_metric | kill_reason |
| --- | --- | --- | --- | --- | --- | --- |
```

### Topic Scope

- `original_topic`: verbatim topic string passed to the skill.

### Bottleneck Evidence

**Bottlenecks** (`B*` IDs) — one row per distinct unresolved problem or structural bottleneck:

- `bottleneck_id`: stable `B*` ID (e.g., `B1`).
- `bottleneck`: one-phrase label for the unresolved problem.
- `context`: one sentence situating the bottleneck in the topic's system or workload space.
- `decisive_metrics`: comma-separated metrics that would confirm or refute progress.
- `representative_papers`: 1-3 papers best evidencing this bottleneck; use `[Short Title](URL)`.
- `current_status`: one sentence on where the state of the art plateaus.
- `residual_gap`: the unresolved part of this bottleneck; seeds `Gap Seeds.source_gap_ref`.

**Solution Attempts** (`S*` IDs) — one row per distinct mechanism family addressing a bottleneck:

- `solution_id`: stable `S*` ID (e.g., `S1`).
- `bottleneck_ids`: comma-separated `B*` IDs this solution targets.
- `mechanism_family`: compact label for the approach class (e.g., `speculative decoding`, `KV offload`).
- `representative_papers`: 1-3 papers; use `[Short Title](URL)`.
- `best_outcome`: best reported result on `decisive_metrics`; include benchmark and hardware tier.
- `missing_piece`: what the mechanism leaves unsolved; seeds `Gap Seeds.source_gap_ref`.

### Evaluation Canon

**Platforms** (`EC-P*` IDs) — one row per concrete evaluation substrate available to test ideas:

- `platform_id`: stable `EC-P*` ID.
- `evaluation_platform`: simulator, trace harness, benchmark artifact, prototype, testbed, or open-source system.
- `access_readiness`: `ready | small_adapter_needed | major_bringup_needed | unavailable | unknown`.
- `supported_workloads`: comma-separated `EC-W*` IDs; concise workload family when no `EC-W*` row exists yet.
- `validates_refs`: comma-separated `B*` or `S*` IDs this platform can measure or reproduce.
- `artifact_access_path`: public URL, repo path, or `none_found`.
- `platform_limitations`: access, fidelity, scale, hardware, or license blockers; `none` when absent.

**Workloads** (`EC-W*` IDs) — one row per benchmark, trace family, or synthetic workload class:

- `workload_id`: stable `EC-W*` ID.
- `workload`: canonical name of the benchmark, trace, or workload class.
- `bottlenecks`: comma-separated `B*` IDs this workload stresses.
- `workload_characteristics`: workload shape — model family, trace type, request pattern, sequence length, topology, scale, or benchmark configuration. Record shape, not outcome.
- `representative_papers`: 1-3 papers using this workload; use `[Short Title](URL)`.
- `representativeness_limits`: caveats — synthetic traces, outdated benchmarks, small scale, missing multi-tenancy, no tail behavior, narrow model family, or unavailable real traces. Write `weak_or_missing` when no good representative exists.

### Competitive Landscape

The `Competitive Landscape` sub-section is the authoritative location for all competitive data.

**selection_rule** (optional line above Competitors table): default ranking is (1) workload-class overlap with `decisive_metrics`, then (2) `best_outcome` on those metrics, then (3) recency; ties broken by public artifact. Include only when deviating from the default.

**Competitors** (`C*` IDs) — top 3 rows, or fewer with a one-line reason; directly competing papers sharing the same primary `B*`:

- `competitor_id`: stable `C*` ID (e.g., `C1`); stable across re-runs when the same paper stays in scope.
- `papers`: `[Short Title](URL)` plus venue/year; one paper per row; group only when the same lab releases an explicit follow-up.
- `B*_scope`: `B<primary>` or `B<primary> (adj: B<secondary>, ...)` for cross-bottleneck competitors. Every `B*` ID, including `adj:` IDs, must resolve to a `B*`.
- `eval_tier`: `"<workload class> @ <hw/system tier>"` in one cell (e.g., `LongBench 32K @ commodity GPU`).
- `what_it_solves`: one sentence; do not restate the abstract.
- `residual_gap`: one sentence; end with `-> G<id>` when a Gap Seeds row exists, else `no_gap_seed_yet`.
- `NE_link`: `NE-*` IDs where this paper is a revealer or refuted method; `none` when absent.

**Excluded Competitors** — required table; one `none_excluded` placeholder row when no shared-`B*` paper was dropped:

- `excluded_paper`: paper handle; no `C*` ID needed.
- `shared_B*`: the primary bottleneck this paper shares with the scope.
- `eval_tier`: same format as Competitors.
- `excluded_reason`: concrete and audit-grade (e.g., `different substrate: CXL-PNM, not commodity GPU`).
- `revisit_condition`: trigger that would force re-inclusion.

NE-* coupling (hard gate): every paper in the `source` column of a `NE-*` row that shares the `primary_B*` must appear in Competitors or Excluded Competitors. If excluded, `excluded_reason` must address why the negative evidence does not warrant inclusion.

### Gap Seeds

**Gap Seeds** (`G*` IDs) — one row per actionable research seed; converts bottleneck residuals into testable ideas for `/idea-creator`:

- `gap_id`: stable `G*` ID for downstream references.
- `bottleneck_id`: primary `B*` this seed targets; must resolve to a `B*`.
- `source_gap_ref`: evidence pointer — `B*.residual_gap`, `S*.missing_piece`, or `NE-*` ID from Section 2.5 (raw text only when Section 2.5 is `none_identified`).
- `mechanism_hint`: compact hint for the possible mechanism, measurement, or study direction; not a complete proposed method.
- `validation_target`: `EC-P*`/`EC-W*` target, platform, workload, baseline, or prototype that would test the seed.
- `decisive_metric`: first metric that would decide whether the seed has value.
- `kill_reason`: concrete observation that would make the seed not worth pursuing.

Gap Seeds must be grounded in at least one source found during the search, a `NE-*` row from Section 2.5, or raw negative evidence. Structural gap categories belong in Section 3 prose, not in Gap Seeds.

Contract rules:

**General:**

- Preserve the top-level headings exactly: `Topic Scope`, `Bottleneck Evidence`, `Evaluation Canon`, `Competitive Landscape`, and `Gap Seeds`.
- No Landscape Pack table should exceed 7 columns.
- When a Bottlenecks or Evaluation Canon item is weak or missing, write `none_found` or `weak_or_missing` and explain in `residual_gap`, `platform_limitations`, or `representativeness_limits`.
- `Bottlenecks.residual_gap` records the unresolved problem; `Gap Seeds` converts one or more residuals into an actionable idea seed.
- `evaluation_platform` is the concrete evaluation substrate.
- `access_readiness` is one of `ready`, `small_adapter_needed`, `major_bringup_needed`, `unavailable`, `unknown`.
- `validates_refs` entries must resolve to `B*` or `S*`.
- `platform_limitations` records platform, access, or fidelity blockers.
- `workload_characteristics` records workload shape.
- `representativeness_limits` records workload-level caveats.

**ID resolution constraints:**

- `S*.bottleneck_ids` is a comma-separated list of `B*` IDs. Every entry must resolve to a `B*`.
- Every `EC-W*.bottlenecks` entry must resolve to `B*`.
- Every `G*.bottleneck_id` must resolve to `B*`.
- Every `G*.source_gap_ref` must point to `B*.residual_gap`, `S*.missing_piece`, or explicit negative evidence.
- `C*.B*_scope`: every `B*` ID in the cell (including `adj:` IDs) must resolve to a `B*`.
- `C*` IDs must be stable across re-runs when the same paper stays in scope.

## Key Rules

- Always cite papers with title, authors when available, year, and venue/source.
- Do not claim to search ACM DL or IEEE Xplore directly unless a configured API
  actually succeeded.
- Do not fail because a source is unavailable; degrade gracefully and expose the
  skip in Source Audit.
- The final answer to the user should summarize findings, but the durable output
  is the saved literature review files.
