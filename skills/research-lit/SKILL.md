---
name: research-lit
description: Search and analyze research papers, find related work, summarize key ideas. Use when user says "find papers", "related work", "literature review", "what does this paper say", or needs to understand academic papers.
argument-hint: [paper-topic-or-url]
allowed-tools: Bash(*), Read, Glob, Grep, WebSearch, WebFetch, Write, Agent, mcp__zotero__*, mcp__obsidian-vault__*
---

# Research Literature Review

Research topic: $ARGUMENTS

## Constants

- **REVIEWER\_BACKEND =** **`codex`** — Default: Codex MCP (xhigh). Override with `— reviewer: oracle-pro` for GPT-5.5 Pro via Oracle MCP. See `shared-references/reviewer-routing.md`.
- **PAPER\_LIBRARY** — Local directory containing user's paper collection (PDFs). Check these paths in order:
  1. Inline override: `— paper library: /path/` in the skill invocation (highest priority)
  2. `papers/` in the current project directory
  3. `literature/` in the current project directory
- **MAX\_LOCAL\_PAPERS = 20** — Maximum number of local PDFs to scan (read first 3 pages each). If more are found, prioritize by filename relevance to the topic.
- **ARXIV\_DOWNLOAD = false** — When `true`, download top 3-5 most relevant arXiv PDFs to PAPER\_LIBRARY after search. When `false` (default), only fetch metadata (title, abstract, authors) via arXiv API — no files are downloaded.
- **ARXIV\_MAX\_DOWNLOAD = 5** — Maximum number of PDFs to download when `ARXIV_DOWNLOAD = true`.
- **EXTENDED\_TOPICS = \[]** — Optional list of related-but-broader topics to search in addition to the primary topic. Papers found via extended topics are tagged `[cross-domain]` and reported in a separate Section 1b table. They inform the "Cross-domain transfer" gap but do NOT affect the primary paper table.
- **AI\_INFRA\_LAYER =** **`auto`** — Inferred AI infrastructure for LLM layer unless overridden: `compute`, `memory`, `interconnect`, `storage`, `runtime`, or `multi`.
- **NEIGHBORHOOD =** **`same-layer`** — Expand the user's topic with same-layer aliases, platform names, and metrics. Use `explicit` to search only the original topic plus `EXTENDED_TOPICS`.
- **EVIDENCE\_POLICY =** **`arxiv-ok`** — Preprints may anchor frontier gaps, but every claim must carry an `evidence_level` (`peer-reviewed`, `preprint`, `local-note`, or `title-abstract-only`).

> 💡 Overrides:
>
> - `/research-lit "topic" — paper library: ~/my_papers/` — custom local PDF path
> - `/research-lit "topic" — sources: zotero, local` — only search Zotero + local PDFs
> - `/research-lit "topic" — sources: zotero` — only search Zotero
> - `/research-lit "topic" — sources: web` — only search the web (skip all local)
> - `/research-lit "topic" — sources: web, semantic-scholar` — also search Semantic Scholar for published venue papers (IEEE, ACM, etc.)
> - `/research-lit "topic" — sources: deepxiv` — only search via DeepXiv progressive retrieval
> - `/research-lit "topic" — sources: all, deepxiv` — use default sources plus DeepXiv
> - `/research-lit "topic" — arxiv download: true` — download top relevant arXiv PDFs
> - `/research-lit "topic" — arxiv download: true, max download: 10` — download up to 10 PDFs
> - `/research-lit "KV cache CXL" — ai-infra layer: memory, neighborhood: same-layer` — expand within the memory/storage/data movement layer
> - `/research-lit "nic-lossless-compression" — extended topics: "memory compression", "hardware compression accelerator"` — also search adjacent fields; results appear in Section 1b only

## AI Infrastructure Scope

This skill is the evidence entrypoint for **AI infrastructure for LLM** research with a computer architecture / systems bias. Do not assume the topic is machine learning method research or RDMA-only networking. Classify the topic into one or more of these layers:

| Layer                          | Typical topic terms                                                                                        | Same-layer expansion examples                                                                                                              | Hardware bottleneck signals                                                                  |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `compute/accelerator`          | NV/custom GPUs, FlashAttention, Triton kernels, tensor cores, sparsity                                     | kernel fusion, systolic array, quantization hardware, HLS/RTL accelerator, GPGPU-Sim                                                       | TOPS/W, utilization, pipeline stalls, on-chip SRAM pressure                                  |
| `memory/storage/data movement` | CFS storage, KV cache, HBM, CXL, SSD, checkpointing, dataset loading, memory compression                   | cache hierarchy, memory pool, memory share, disaggregated memory,  NUMA,  GPUDirect Storage, in-memory/storage computing，Near-data compute | GB/s, IOPS, tail latency, miss rate, write amplification, capacity pressure, checkpoint time |
| `interconnect/network`         | ScaleUP/HPN/DCN networks, intra-node interconnect, comm libraries, RDMA, NIC/DPU, collective communication | *NVLink/NVSwitch, NoC, Infiniband, collective fusion, SmartNIC，in-network computing*                                                       | goodput, FCT, retransmission, PCIe/NVLink utilization, congestion, Rx pressure               |
| `runtime/system`               | LLMServer/vLLM/Sglang, PD separation, SP/PP/EP parallel, scheduler, batching                               | admission control, pipeline bubble optimization, expert routing, memory tiering, accelerator partitioning                                  | only include when the idea exposes or controls a concrete hardware bottleneck                |

When `AI_INFRA_LAYER = auto`, infer the narrowest layer that matches the topic. If the topic is runtime/system and no concrete hardware bottleneck is visible, mark it as **software-only / out-of-scope for Workflow 1** unless the user explicitly asks for pure systems software.

### Topic Neighborhood Expansion

Use topic-neighborhood search, not a full five-layer scan by default:

1. Infer the primary AI infrastructure layer.
2. Add same-layer aliases, representative platforms, and decisive metrics to the query set.
3. Keep `EXTENDED_TOPICS` as the only automatic cross-layer broadening mechanism.
4. Record the final query set in the output so downstream skills can see what was and was not searched.

Examples:

- `KV cache CXL` -> `memory/storage/data movement`; expand with `HBM`, `CXL.mem`, `tiered memory`, `prefetch`, `paging`, `bandwidth`, `tail latency`.
- `RDMA NIC compression for LLM` -> `interconnect/network`; expand with `RoCE`, `SmartNIC`, `DPU`, `PFC`, `DCQCN`, `PCIe`, `Rx decompression expansion pressure`.
- `checkpointing for LLM training` -> `memory/storage/data movement`; expand with `burst buffer`, `SSD`, `GPUDirect Storage`, `checkpoint time`, `recovery time`.

## Data Sources

This skill checks multiple sources **in priority order**. All are optional — if a source is not configured or not requested, skip it silently.

### Source Selection

Parse `$ARGUMENTS` for a `— sources:` directive:

- **If** **`— sources:`** **is specified**: Only search the listed sources (comma-separated). Valid values: `zotero`, `obsidian`, `local`, `web`, `semantic-scholar`, `deepxiv`, `exa`, `all`.
- **If not specified**: Default to `all` — search every available source in priority order (`semantic-scholar`, `deepxiv`, and `exa` are **excluded** from `all`; they must be explicitly listed).

Examples:

```
/research-lit "diffusion models"                                    → all (default, no S2)
/research-lit "diffusion models" — sources: all                     → all (default, no S2)
/research-lit "diffusion models" — sources: zotero                  → Zotero only
/research-lit "diffusion models" — sources: zotero, web             → Zotero + web
/research-lit "diffusion models" — sources: local                   → local PDFs only
/research-lit "topic" — sources: obsidian, local, web               → skip Zotero
/research-lit "topic" — sources: web, semantic-scholar              → web + S2 API (IEEE/ACM venue papers)
/research-lit "topic" — sources: deepxiv                            → DeepXiv only
/research-lit "topic" — sources: all, deepxiv                       → default sources + DeepXiv
/research-lit "topic" — sources: all, semantic-scholar              → all + S2 API
/research-lit "topic" — sources: exa                               → Exa only (broad web + content extraction)
/research-lit "topic" — sources: all, exa                          → default sources + Exa web search
```

### Source Table

| Priority | Source                   | ID                 | How to detect                                                        | What it provides                                                                                                                                                                                                                                   |
| -------- | ------------------------ | ------------------ | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1        | **Zotero** (via MCP)     | `zotero`           | Try calling any `mcp__zotero__*` tool — if unavailable, skip         | Collections, tags, annotations, PDF highlights, BibTeX, semantic search                                                                                                                                                                            |
| 2        | **Obsidian** (via MCP)   | `obsidian`         | Try calling any `mcp__obsidian-vault__*` tool — if unavailable, skip | Research notes, paper summaries, tagged references, wikilinks                                                                                                                                                                                      |
| 3        | **Local PDFs**           | `local`            | `Glob: papers/**/*.pdf, literature/**/*.pdf`                         | Raw PDF content (first 3 pages)                                                                                                                                                                                                                    |
| 4        | **Web search**           | `web`              | Always available (WebSearch)                                         | arXiv, Semantic Scholar, Google Scholar                                                                                                                                                                                                            |
| 5        | **Semantic Scholar API** | `semantic-scholar` | `tools/semantic_scholar_fetch.py` exists                             | Published venue papers (IEEE, ACM, Springer) with structured metadata: citation counts, venue info, TLDR. **Only runs when explicitly requested** via `— sources: semantic-scholar` or `— sources: web, semantic-scholar`                          |
| 6        | **DeepXiv CLI**          | `deepxiv`          | `tools/deepxiv_fetch.py` and installed `deepxiv` CLI                 | Progressive paper retrieval: search, brief, head, section, trending, web search. **Only runs when explicitly requested** via `— sources: deepxiv` or `— sources: all, deepxiv`                                                                     |
| 7        | **Exa Search**           | `exa`              | `tools/exa_search.py` and installed `exa-py` SDK                     | AI-powered broad web search with content extraction (highlights, text, summaries). Covers blogs, docs, news, companies, and research papers beyond arXiv/S2. **Only runs when explicitly requested** via `— sources: exa` or `— sources: all, exa` |

> **Graceful degradation**: If no MCP servers are configured, the skill works exactly as before (local PDFs + web search). Zotero and Obsidian are pure additions.

## Workflow

### Step 0: Load Previous Review (if exists)

Before doing any search, check whether a prior literature review was already generated for this topic.

1. **Check the fixed latest copy**:
   ```
   Read: idea-stage/LITERATURE_REVIEW.md
   ```
2. **If the file exists**:
   - Extract the existing paper table and narrative summary
   - Use this as the **baseline** — treat all papers already listed as known
   - Announce to the user: _"Found prior literature review in `idea-stage/LITERATURE_REVIEW.md`, building on it."_
   - In subsequent steps, **only search for papers newer than the review date recorded in the file header**, or papers not already in the table
   - In Step 4 output, clearly mark newly added papers (e.g. `🆕`) vs papers carried over from the prior review
3. **If no prior review exists**: proceed normally from scratch.

> This ensures incremental refinement rather than redundant re-research. Each run adds new findings on top of existing ones.

### Step 0a: Search Zotero Library (if available)

**Skip this step entirely if Zotero MCP is not configured.**

Try calling `zotero_get_collections` first. If it succeeds, proceed with the steps below.

#### Phase A: Collection Discovery (path-aware)

Do NOT rely solely on keyword search — Zotero collections are organized as a user-curated hierarchy that must be traversed explicitly.

1. **Get full collection tree**: Call `zotero_get_collections` to retrieve all collections with their keys and nesting.
2. **Match by keyword fragments**: Decompose the original topic text and expanded search terms into meaningful keywords. For example, `"NIC-side lossless compression for RDMA"` → `["compression", "lossless", "nic", "rdma"]`. Match any collection whose name contains **any** of these keywords (case-insensitive). Collect all matching collections at any depth level.
   - Example: a topic mentioning NIC lossless compression matches a `compression` collection even if nested under `IOAcc → RDMA → compression`.
   - Do NOT require the full topic phrase to match — fragment matching is sufficient.
3. **Retrieve items from matched collections**: For each matched collection, call `zotero_get_collection_items(collection_key)`. De-duplicate across collections.
4. **Fallback text search**: Additionally run `zotero_search_items` with the original topic as query — this catches papers not yet filed into a matching collection.

#### Phase B: Cross-domain Broadening (only if EXTENDED\_TOPICS is set)

**Skip this phase entirely if the user did not provide** **`— extended topics:`** **in the invocation.**

If `EXTENDED_TOPICS` is non-empty, search each extended topic separately:

1. **Search Zotero for each extended topic**: Run `zotero_search_items` with each entry in EXTENDED\_TOPICS. Collect results NOT already found in Phase A.
2. **Also match Zotero collections**: For each extended topic keyword, re-run the collection fragment-matching from Phase A. Papers in matching collections are included.
3. **Filter by venue quality**: Keep only papers from top-tier venues (MICRO, ISCA, HPCA, ASPLOS, NSDI, SIGCOMM, OSDI, USENIX ATC, EuroSys, FCCM, DAC, IEEE TPDS, IEEE Micro, etc.). Discard workshop papers and preprints from unknown venues at this stage.
4. **Tag as cross-domain**: Mark these papers with `[cross-domain]` in your working set. They will be reported in Section 1b — NOT mixed into the primary paper table.

#### Phase C: Annotation and Metadata Extraction

For papers found in Phase A (primary) and Phase B (cross-domain):

1. **Extract annotations**: For highly relevant papers, call `zotero_get_annotations(item_key)` — these show what the user personally highlighted as important.
2. **Get notes**: Call `zotero_get_notes(item_key)` for any user-written notes attached to the paper.
3. **Compile each entry**:
   - Title, authors, year, venue
   - Collection path (e.g., `IOAcc → RDMA → compression`)
   - User's annotations/highlights (if any)
   - Tags the user assigned
   - `[cross-domain]` marker if applicable

> 📚 Phase A collection traversal ensures you find papers even when the collection name doesn't match the full topic text. Phase B cross-domain broadening ensures top-venue adjacent work is not silently dropped.

### Step 0b: Search Obsidian Vault (if available)

**Skip this step entirely if Obsidian MCP is not configured.**

Try calling an Obsidian MCP tool (e.g., search). If it succeeds:

1. **Search vault**: Search for notes related to the research topic
2. **Check tags**: Look for notes tagged with relevant topics (e.g., `#diffusion-models`, `#paper-review`)
3. **Read research notes**: For relevant notes, extract the user's own summaries and insights
4. **Follow links**: If notes link to other relevant notes (wikilinks), follow them for additional context
5. **Compile results**: For each relevant note:
   - Note title and path
   - User's summary/insights
   - Links to other notes (research graph)
   - Any frontmatter metadata (paper URL, status, rating)

> 📝 Obsidian notes represent the user's **processed understanding** — more valuable than raw paper content for understanding their perspective.

### Step 0c: Scan Local Paper Library

Before searching online, check if the user already has relevant papers locally:

1. **Locate library**: Resolve PAPER\_LIBRARY path in priority order:
   - Check for inline `— paper library:` override in the invocation arguments
   - Fall back to `papers/` or `literature/` in project directory
   ```
   Glob: {PAPER_LIBRARY}/**/*.pdf
   ```
2. **De-duplicate against Zotero**: If Step 0a found papers, skip any local PDFs already covered by Zotero results (match by filename or title).
3. **Filter by relevance**: Match filenames and first-page content against the research topic. Skip clearly unrelated papers.
4. **Summarize relevant papers**: For each relevant local PDF (up to MAX\_LOCAL\_PAPERS):
   - Read first 3 pages (title, abstract, intro)
   - Extract: title, authors, year, core contribution, relevance to topic
   - Flag papers that are directly related vs tangentially related
5. **Build local knowledge base**: Compile summaries into a "papers you already have" section. This becomes the starting point — external search fills the gaps.

> 📚 If no local papers are found, skip to Step 1. If the user has a comprehensive local collection, the external search can be more targeted (focus on what's missing).

### Step 1: Search (external)

- **De-duplicate**: Skip papers already found in Zotero, Obsidian, or local library
- Focus on papers from last 2 years unless studying foundational work; for architecture/systems topics, extend to last 5 years to capture influential prior work
- Search the following sources:

**Target venues** (for reference when evaluating results):

- Computer Architecture: MICRO, ISCA, HPCA, ASPLOS
- Systems & Networking: NSDI, SIGCOMM, OSDI, USENIX ATC, EuroSys
- Hardware design: FCCM, DAC, IEEE TCAD, IEEE TVLSI
- Journals: IEEE TPDS, IEEE TON, IEEE TC, ACM TOCS, ACM Transactions on Networking

> ⚠️ **ACM DL and IEEE Xplore cannot be accessed directly** (both return 403 / require login). Do NOT claim to "search ACM DL / IEEE Xplore" — use the alternative strategies below instead.

**Search strategy — use in priority order:**

> ⚠️ **Lessons from real runs**:
>
> - Semantic Scholar API (S3) hits **429 rate limits** frequently — do NOT rely on it as primary
> - DBLP keyword search API returns 0 results unless all terms match exactly — **do NOT use** `dblp.org/search/publ/api` for keyword queries
> - **DBLP direct proceedings pages** (`dblp.org/db/conf/{venue}/{venue}{year}.html`) are the most reliable way to get exhaustive conference coverage — use these first

**S1: DBLP direct proceedings pages** ✅ most reliable for conference coverage:

```
WebFetch https://dblp.org/db/conf/micro/micro2025.html   ← full paper list, no rate limits
WebFetch https://dblp.org/db/conf/asplos/asplos2026.html
```

- Returns the **complete paper list** for a conference+year — exhaustive, no keyword matching needed
- Scan the full list and filter by relevance to your topic
- Always fetch **current year AND previous year** for each target venue
- Known DBLP conference slugs: `micro`, `isca`, `hpca`, `asplos`, `sigcomm`, `nsdi`, `osdi`, `atc`, `eurosys`, `fccm`, `dac`
- For journals (by volume): `WebFetch https://dblp.org/db/journals/tpds/tpds36.html` — adjust volume number to match current year

**S2: Conference program pages** (for very recent conferences where DBLP not yet indexed):

- Use when the conference was held within the last **8 weeks** and DBLP page returns incomplete results
- **Derive the correct year** from `currentDate`. Always check current year AND previous year.
- Known URL patterns (substitute `{YY}` = 2-digit year, `{YYYY}` = 4-digit year):

| Venue      | URL pattern                                                     |
| ---------- | --------------------------------------------------------------- |
| ASPLOS     | `https://www.asplos-conference.org/asplos{YYYY}/program/`       |
| MICRO      | `https://microarch.org/micro{YY}/program.php`                   |
| ISCA       | `https://iscaconf.org/isca{YYYY}/program/`                      |
| HPCA       | `https://hpca-conf.org/{YYYY}/program/`                         |
| SIGCOMM    | `https://conferences.sigcomm.org/sigcomm/{YYYY}/program/`       |
| NSDI       | `https://www.usenix.org/conference/nsdi{YY}/technical-sessions` |
| OSDI       | `https://www.usenix.org/conference/osdi{YY}/technical-sessions` |
| USENIX ATC | `https://www.usenix.org/conference/atc{YY}/technical-sessions`  |
| EuroSys    | `https://{YYYY}.eurosys.org/program/`                           |
| FCCM       | `https://www.fccm.org/fccm-{YYYY}-program/`                     |

- If the URL pattern fails (404/redirect), fall back to WebSearch: `"{venue} {YYYY} program accepted papers"`

**S3: Semantic Scholar API** (keyword search, use when S1/S2 don't cover a topic):

```
WebFetch https://api.semanticscholar.org/graph/v1/paper/search?query=QUERY&fields=title,year,venue,abstract,authors,externalIds&limit=10
```

- ⚠️ **Rate limited (HTTP 429)** — if it fails, wait and retry once; if it fails again, skip and rely on S1/S2/S4
- Best use case: finding papers by keyword across all venues, especially for **extended topics** not covered by specific venue proceedings
- Covers IEEE/ACM journals (TPDS/TC/TON/IEEE Micro) which DBLP journal volumes require knowing the exact volume number

**S3b: IEEE Xplore API** (optional, requires free API key from developer.ieee.org):

```
WebFetch https://ieeexploreapi.ieee.org/api/v1/search/articles?querytext=QUERY&apikey=YOUR_KEY&max_records=10
```

- Useful for IEEE journals when Semantic Scholar is rate-limited
- Skip if no API key configured

**S4: WebSearch** (last resort, unreliable for venue-specific discovery):

- Use only to find arXiv preprints of papers identified by title: `"paper title" site:arxiv.org`
- Use to find a specific paper when you know part of its title: `"partial title" ASPLOS 2026`

**Search execution order**:

1. For each **target venue**: fetch DBLP proceedings page (S1) → scan full list → filter relevant titles
2. For **very recent conferences** (< 8 weeks): also fetch conference program page (S2)
3. For **keyword-based extended topics search**: try Semantic Scholar (S3), fall back to WebSearch (S4) if rate-limited
4. Always run arXiv API search (see below) in parallel for preprints not yet in proceedings

**Extended topics search** (only if `EXTENDED_TOPICS` is set):

After the primary search, run a second pass for each entry in EXTENDED\_TOPICS:

- Same venues and sources as the primary search
- Filter to top-tier venues only (same list as Step 0a Phase B)
- De-duplicate against all papers already found in the primary pass
- Tag all results as `[cross-domain]` — they go into Section 1b, not the primary paper table
- Cross-domain papers stay in Section 1b and do not change the fixed output path

**arXiv API search** (always runs, no download by default):

Locate the fetch script and search arXiv directly:

```bash
# Try to find arxiv_fetch.py
SCRIPT=$(find tools/ -name "arxiv_fetch.py" 2>/dev/null | head -1)
# If not found, check ARIS install
[ -z "$SCRIPT" ] && SCRIPT=$(find ~/.claude/skills/arxiv/ -name "arxiv_fetch.py" 2>/dev/null | head -1)

# Search arXiv API for structured results (title, abstract, authors, categories)
python3 "$SCRIPT" search "QUERY" --max 10
```

If `arxiv_fetch.py` is not found, fall back to WebSearch for arXiv (same as before).

The arXiv API returns structured metadata (title, abstract, full author list, categories, dates) — richer than WebSearch snippets. Merge these results with WebSearch findings and de-duplicate.

**Semantic Scholar API search** (only when `semantic-scholar` is in sources):

When the user explicitly requests `— sources: semantic-scholar` (or `— sources: web, semantic-scholar`), search for published venue papers beyond arXiv:

```bash
S2_SCRIPT=$(find tools/ -name "semantic_scholar_fetch.py" 2>/dev/null | head -1)
[ -z "$S2_SCRIPT" ] && S2_SCRIPT=$(find ~/.claude/skills/semantic-scholar/ -name "semantic_scholar_fetch.py" 2>/dev/null | head -1)

# Search for published CS/Engineering papers with quality filters
python3 "$S2_SCRIPT" search "QUERY" --max 10 \
  --fields-of-study "Computer Science,Engineering" \
  --publication-types "JournalArticle,Conference"
```

If `semantic_scholar_fetch.py` is not found, skip silently.

**Why use Semantic Scholar?** Many IEEE/ACM journal papers are NOT on arXiv. S2 fills the gap for published venue-only papers with citation counts and venue metadata.

**De-duplication between arXiv and S2**: Match by arXiv ID (S2 returns `externalIds.ArXiv`):

- If a paper appears in both: check S2's `venue`/`publicationVenue` — if it has been published in a journal/conference (e.g. IEEE TWC, JSAC), use S2's metadata (venue, citationCount, DOI) as the authoritative version, since the published version supersedes the preprint. Keep the arXiv PDF link for download.
- If the S2 match has no venue (still just a preprint indexed by S2): keep the arXiv version as-is.
- S2 results without `externalIds.ArXiv` are **venue-only papers** not on arXiv — these are the unique value of this source.

**DeepXiv search** (only when `deepxiv` is in sources):

When the user explicitly requests `— sources: deepxiv` (or includes `deepxiv` in a combined source list), use the DeepXiv adapter for progressive retrieval:

```bash
python3 tools/deepxiv_fetch.py search "QUERY" --max 10
```

Then deepen only for the most relevant papers:

```bash
python3 tools/deepxiv_fetch.py paper-brief ARXIV_ID
python3 tools/deepxiv_fetch.py paper-head ARXIV_ID
python3 tools/deepxiv_fetch.py paper-section ARXIV_ID "Experiments"
```

If `tools/deepxiv_fetch.py` or the `deepxiv` CLI is unavailable, skip this source gracefully and continue with the remaining requested sources.

**Why use DeepXiv?** It is useful when a broad search should be followed by staged reading rather than immediate full-paper loading. This reduces unnecessary context while still surfacing structure, TLDRs, and the most relevant sections.

**De-duplication against arXiv and S2**:

- Match by arXiv ID first, DOI second, normalized title third
- If DeepXiv and arXiv refer to the same preprint, keep one canonical paper row and record `deepxiv` as an additional source
- If DeepXiv overlaps with S2 on a published paper, prefer S2 venue/citation metadata in the final table, but keep DeepXiv-derived section notes when they add value

**Exa search** (only when `exa` is in sources):

When the user explicitly requests `— sources: exa` (or includes `exa` in a combined source list), use the Exa tool for broad AI-powered web search with content extraction:

```bash
EXA_SCRIPT=$(find tools/ -name "exa_search.py" 2>/dev/null | head -1)

# Search for research papers with highlights
python3 "$EXA_SCRIPT" search "QUERY" --max 10 --category "research paper" --content highlights

# Search for broader web content (blogs, docs, news)
python3 "$EXA_SCRIPT" search "QUERY" --max 10 --content highlights
```

If `tools/exa_search.py` or the `exa-py` SDK is unavailable, skip this source gracefully and continue with the remaining requested sources.

**Why use Exa?** Exa provides AI-powered search across the broader web (blogs, documentation, news, company pages) with built-in content extraction. It fills a gap between academic databases (arXiv, S2) and generic WebSearch by returning richer content with each result.

**De-duplication against arXiv, S2, and DeepXiv**:

- Match by URL first, then normalized title
- If Exa returns an arXiv paper already found by arXiv/S2, prefer the structured metadata from those sources
- Exa results from non-academic domains (blogs, docs, news) are unique value not covered by other sources

**Optional PDF download** (only when `ARXIV_DOWNLOAD = true`):

After all sources are searched and papers are ranked by relevance:

```bash
# Download top N most relevant arXiv papers
python3 "$SCRIPT" download ARXIV_ID --dir papers/
```

- Only download papers ranked in the top ARXIV\_MAX\_DOWNLOAD by relevance
- Skip papers already in the local library
- 1-second delay between downloads (rate limiting)
- Verify each PDF > 10 KB

### Step 1.5: Full-text Availability Check

Before analyzing, verify which papers actually have accessible full text.

**For every paper found in Step 1 (web search results only — local/Zotero/Obsidian papers already have full text):**

1. **Check local library first**: Match paper title/DOI against files already in PAPER\_LIBRARY. If found → mark `✅ local`.
2. **Build the unavailable list**: Collect all `⚠️ NO FULL TEXT` papers into a table:
   ```
   | Title | Year | Venue | DOI / URL |
   |-------|------|-------|-----------|
   ```
3. **Degraded Processing**:
   - Do NOT pause execution. The pipeline must remain fully autonomous.
   - For papers marked `⚠️ NO FULL TEXT`, include them in the final Paper Table with the ⚠️ marker.
   - Limit their analysis (in Step 2) strictly to the title and abstract (from the web search snippet or API metadata).
   - Add a note in the final output recommending the user to download these PDFs later for deeper analysis.

### Step 2: Analyze Each Paper

For each relevant paper (from all sources), extract:

- **Problem**: What gap does it address?
- **Method**: Core technical contribution (1-2 sentences)
- **Results**: Key numbers/claims
- **Relevance**: How does it relate to our work?
- **Source**: Where we found it (Zotero/Obsidian/local/web) — helps user know what they already have vs what's new
- **AI infrastructure layer**: compute/accelerator, memory/storage/data movement, interconnect/network, runtime/system, or multi-layer
- **Evidence level**: `peer-reviewed`, `preprint`, `local-note`, or `title-abstract-only`
- **Evaluation platform/backend**: simulator, artifact, benchmark harness, trace framework, prototype, or `not_reported`
- **Benchmark/workload/trace**: workload family, trace, benchmark scenario, synthetic setup, or `not_reported`
- **Compared baselines**: systems, policies, default configs, published results, or `not_reported`
- **Metrics used**: primary and secondary metrics, or `not_reported`
- **Artifact/code availability**: official artifact, open-source system, reproducible config, paper-only, unavailable, or `not_reported`
- **Evaluation limitations**: simulator gaps, trace realism, scale limits, unavailable artifacts, workload representativeness, or `not_reported`

### Step 3: Synthesize — Landscape Map + Structural Gaps

This step produces the analysis that both the user and downstream skills (e.g., `/idea-creator`) consume. Always produce the sections below, then end with the structured **Landscape Pack**.

#### 3a: Landscape Map (grouped by sub-direction)

Group all collected papers into 3–6 sub-directions or approach clusters. For each cluster:

- Cluster name and 1-sentence description
- Papers belonging to it (with year and venue)
- What the cluster has achieved and where it plateaus

#### 3b: Consensus and Disagreements

- Points of consensus: what does the field agree on? (e.g., "hardware LZ4 at 100Gbps is solved")
- Active disagreements or open debates: conflicting results between papers, or competing design philosophies
- If Obsidian notes exist, incorporate the user's own insights here

#### 3c: Structural Gaps (for research ideation)

Identify concrete, actionable gaps using these five lenses. Be specific — name the paper or assumption that creates each gap:

1. **Cross-domain transfer**: methods proven in domain A (e.g., memory compression) not yet applied in domain B (e.g., RDMA NIC data path)
2. **Contradictory findings**: papers that reach opposite conclusions — the discrepancy itself is a research opportunity
3. **Untested assumptions**: things every paper takes for granted but nobody has experimentally validated (e.g., "compression ratio is stable enough to not affect flow control")
4. **Unexplored regimes**: scales, workload types, hardware generations, or parameter ranges nobody has studied
5. **Unasked diagnostic questions**: measurement studies or characterizations that would change how the field thinks, but haven't been done

#### 3d: Competitive Landscape (for positioning)

For the top 3 most directly competing papers:

- What they claim to solve and what they leave open
- Whether they are peer-reviewed or preprints
- Whether they directly compete with or support a potential new contribution in this area

#### 3e: Landscape Pack (for `/idea-creator`)

The **Landscape Pack** is a fixed Markdown contract consumed by Workflow 1. It is still human-readable, but the headings and field names should remain stable.

```markdown
## Landscape Pack

### Topic Scope
- original_topic:
- inferred_ai_infra_layer:
- included_layers:
- excluded_layers:
- search_neighborhood:
- expanded_terms:

### Bottleneck Evidence
| bottleneck_id | layer | bottleneck | evidence_level | supporting_papers | decisive_metrics |
|---------------|-------|------------|----------------|-------------------|------------------|

### Mechanism Clusters
| cluster | layer | mechanism_family | representative_papers | plateau_or_missing_piece |
|---------|-------|------------------|-----------------------|--------------------------|

### Evaluation Canon
| canon_id | category | item | applies_to_layer_or_subtopic | supporting_papers | evidence_level | adoption_strength | artifact_or_access | limitations | notes |
|----------|----------|------|------------------------------|-------------------|----------------|-------------------|--------------------|-------------|-------|
| EC-P1 | evaluation_platform |  |  |  |  | common/occasional/single_paper/weak_or_missing | open_source/public_trace/public_benchmark/paper_only/requires_reimplementation/proprietary_or_unavailable/unknown |  |  |
| EC-W1 | benchmark_workload |  |  |  |  | common/occasional/single_paper/weak_or_missing | open_source/public_trace/public_benchmark/paper_only/requires_reimplementation/proprietary_or_unavailable/unknown |  |  |

### Core Baseline Candidates
| baseline_id | baseline_name | paper_or_system | scenario | evaluation_platform_used | workload_used | metrics_used | artifact_status | notes |
|-------------|---------------|-----------------|----------|--------------------------|---------------|--------------|-----------------|-------|
| CB1 |  |  |  |  |  |  | official_artifact/open_source_system/config_reproducible/requires_reimplementation/paper_only/proprietary_or_unavailable/unknown |  |

### Simulator / Prototype Readiness
| backend | readiness | fits_layers | what_it_can_validate | supporting_papers | blocker |
|---------|-----------|-------------|-----------------------|-------------------|---------|
|  | ready/partial/future |  |  |  |  |

### Gap Seeds
| gap_id | gap_type | layer | hardware_bottleneck | supporting_papers | evidence_level | possible_mechanism_hint | minimum validation backend | decisive_metric | main_risk_or_kill_reason |
|--------|----------|-------|---------------------|-------------------|----------------|-------------------------|----------------------------|-----------------|--------------------------|
```

Rules for **Gap Seeds**:

- Each seed must be grounded in at least one paper, preprint, local note, or explicit negative evidence from the search.
- `runtime/system` seeds are valid only when `hardware_bottleneck` names a concrete resource such as HBM capacity, PCIe bandwidth, NIC queue pressure, memory copy amplification, or accelerator utilization.
- Preprint-backed seeds are allowed under `EVIDENCE_POLICY = arxiv-ok`, but the `evidence_level` must expose that risk.
- Include **Rx decompression expansion pressure** as a valid interconnect/network seed when the topic involves NIC/DPU compression: compressed wire bytes can expand into larger PCIe/host-memory writes, creating Rx buffer overflow, stalls, drops, and sender-side retransmission pressure.

Rules for **Evaluation Canon**, **Core Baseline Candidates**, and **Simulator / Prototype Readiness**:

- Evaluation Canon is an environment map, not an idea-specific decision. It must contain only `evaluation_platform` and `benchmark_workload` rows.
- Use stable IDs: `EC-P*` for platforms and `EC-W*` for workloads. Downstream skills cite these IDs in `canon_mapping`.
- Put platform/workload caveats in the row-level `limitations` field, such as simulator abstraction gap, trace realism issue, scale limit, missing network/storage/compute model, artifact unavailable, workload not representative, or platform bring-up cost.
- Core Baseline Candidates is a baseline candidate pool. Include `metrics_used` because it records how that baseline was evaluated in its original paper/system; it does not force future ideas to use the same metrics.
- Do not carry over platforms, workloads, baselines, or metrics from a previous topic unless the current literature uses them.
- If a canon item or baseline candidate is weak or missing, write `none_found` or `weak_or_missing` and explain the evidence gap in `limitations` or `notes`.
- The readiness table should list both literature-standard backends and locally plausible backends, but `supporting_papers` must show which are common in the field.

### Step 4: Output

Present seven sections:

**Section 0 — Source Audit**
A table documenting the execution status of all attempted data sources during this run. This provides transparency on fallback behaviors.

```
| Source | Status | Action Taken / Notes |
|---|---|---|
| Zotero | Unavailable | localhost 502, fell back to local/web |
| arXiv API | Partial | Rate limited after 5 queries |
| Local PDFs | Available | Parsed 3 files |
```

**Section 1 — Paper Table (primary)**

```
| Paper | Venue | Year | Method | Key Result | Relevance | Source |
|-------|-------|------|--------|------------|-----------|--------|
```

- Mark new papers with 🆕 if building on a prior review.
- Mark papers from Zotero with 📚 and show their collection path (e.g., `IOAcc → RDMA → compression`).

**Section 1b — Cross-domain References**
Papers from adjacent fields (tagged `[cross-domain]` in Step 0a Phase B), kept separate to avoid polluting the primary landscape:

```
| Paper | Venue | Year | Domain | Transferable Insight | Source |
|-------|-------|------|--------|----------------------|--------|
```

These are inputs for the "Cross-domain transfer" lens in Section 3 (Structural Gaps).

**Section 2 — Landscape Map**
Narrative by sub-direction cluster (from Step 3a). 3–5 paragraphs covering the full field.

**Section 3 — Structural Gaps**
Bulleted list from Step 3c. These are the direct inputs for `/idea-creator` Phase 2. For the "Cross-domain transfer" gap, explicitly reference papers from Section 1b.

**Section 4 — Competitive Landscape**
Top 3 competing papers with positioning notes (from Step 3d).

**Section 5 — Landscape Pack**
The fixed `Landscape Pack` block from Step 3e. This is the primary machine-readable handoff for `/idea-creator`; include `Evaluation Canon`, `Core Baseline Candidates`, and `Gap Seeds` even if only 2-3 high-quality seeds exist.

If Zotero BibTeX was exported, append a `references.bib` snippet for direct use in paper writing.

### Step 5: Save Output

**Always save the output automatically** — do not wait for the user to request it.

#### Output files

```
idea-stage/LITERATURE_REVIEW_{YYYYMMDD_HHmmssZ}.md
idea-stage/LITERATURE_REVIEW.md
```

Rules:

- Use UTC timestamps for history files: `date -u +%Y%m%d_%H%M%SZ`.
- Write the timestamped history file first: `idea-stage/LITERATURE_REVIEW_{YYYYMMDD_HHmmssZ}.md`.
- Copy the same content to the fixed latest copy: `idea-stage/LITERATURE_REVIEW.md`.
- Downstream skills always read `idea-stage/LITERATURE_REVIEW.md`.
- Append both output rows to `MANIFEST.md` using stage `idea-discovery`.

Example: `idea-stage/LITERATURE_REVIEW_20260502_041530Z.md`

#### File content

The saved file must include:

1. A header with the generation date, skill name, and original topic query
2. **Section 0**: Source Audit — a table detailing the success, failure, or fallback state of each data source queried
3. **Section 1**: Full paper table (with 🆕 markers if incremental)
4. **Section 2**: Landscape map by sub-direction (3–5 paragraphs)
5. **Section 3**: Structural gaps — the 5-lens analysis (cross-domain / contradictions / untested assumptions / unexplored regimes / unasked questions)
6. **Section 4**: Competitive landscape — top 3 competing papers with positioning
7. **Section 5**: Landscape Pack — topic scope, bottleneck evidence, mechanism clusters, evaluation canon, core baseline candidates, simulator/prototype readiness, and Gap Seeds
8. All reference links

> Section 5 (Landscape Pack) is the primary input consumed by `/idea-creator`. Section 3 remains useful for human reading, but downstream idea generation should prioritize `Evaluation Canon`, `Core Baseline Candidates`, and `Gap Seeds`.

#### Additional saves (optional)

- If `ARXIV_DOWNLOAD = true`, save downloaded PDFs to the resolved `PAPER_LIBRARY`
- If Obsidian is available, optionally create a literature review note in the vault

### Step 6: Update Research Wiki

**Required when** **`research-wiki/`** **exists.** Skip entirely (no action, no
error) if the directory is absent. Per
[`shared-references/integration-contract.md`](../shared-references/integration-contract.md),
this step follows the canonical ingest contract — business logic lives
in `tools/research_wiki.py`, not in this prose.

```
📋 Research Wiki ingest (runs once, at end of research-lit):
   [ ] 1. Predicate: `research-wiki/` exists? If no, skip this step.
   [ ] 2. For each of the top 8–12 relevant papers (arxiv IDs collected above):
          python3 tools/research_wiki.py ingest_paper research-wiki/ \
              --arxiv-id <id> [--thesis "<one-line>"] [--tags <t1>,<t2>]
   [ ] 3. For each explicit relationship to an existing wiki entity,
          add an edge:
          python3 tools/research_wiki.py add_edge research-wiki/ \
              --from "paper:<slug>" --to "<target_node_id>" \
              --type <extends|contradicts|addresses_gap|inspired_by|...> \
              --evidence "<one-sentence quote or reasoning>"
   [ ] 4. Confirm papers/<slug>.md files were created (helper prints
          "Paper ingested: ..."); if any failed with a network error,
          retry or fall back to the --title/--authors/--year manual form.
```

`ingest_paper` handles slug generation, arXiv metadata fetch, dedup
(skips an existing paper by arXiv id), page rendering, `index.md`
rebuild, `query_pack.md` rebuild, and log append in a single call —
**do not manually write** **`papers/<slug>.md`**. If the helper is
unavailable (e.g., offline on a non-ARIS machine), log the gap and let
`/research-wiki sync --arxiv-ids …` backfill later.

For non-arXiv sources (Semantic Scholar only, IEEE/ACM journals without
arXiv mirrors, blog posts), pass manual metadata instead:

```
python3 tools/research_wiki.py ingest_paper research-wiki/ \
    --title "<full title>" --authors "A, B, C" --year <yyyy> \
    --venue "<venue>" [--external-id-doi "<doi>"] [--thesis "..."]
```

## Key Rules

- Always include paper citations (authors, year, venue)
- Distinguish between peer-reviewed and preprints
- Be honest about limitations of each paper
- Note if a paper directly competes with or supports our approach
- **Never fail because a MCP server is not configured** — always fall back gracefully to the next data source
- Zotero/Obsidian tools may have different names depending on how the user configured the MCP server (e.g., `mcp__zotero__search` or `mcp__zotero-mcp__search_items`). Try the most common patterns and adapt.
