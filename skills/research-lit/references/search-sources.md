# Research Lit Search And Sources Reference

Use this reference only when `/research-lit` needs concrete source commands,
conference URL patterns, alias derivation patterns, or adapter-specific
fallback details.

Execution order follows `skills/research-lit/SKILL.md`; this file is a
maintenance reference for URLs, CLI commands, and fallbacks. The default
`sources: all` behavior remains Zotero, Obsidian, local PDFs,
DBLP/proceedings, arXiv, and WebSearch. Semantic Scholar, DeepXiv, Exa, Gemini,
and OpenAlex are explicit-only sources.

## Query Alias Patterns

Derive 2-5 aliases per topic from these patterns on the fly. Do not maintain a
fixed lookup table; apply the patterns to whatever topic the user provides.

- Abbreviation <-> spelled-out form: `KV cache` <-> `key-value cache`,
  `PIM` <-> `processing-in-memory`, `MoE` <-> `mixture of experts`,
  `RDMA` <-> `remote direct memory access`.
- Close synonyms within the same scope: `offload` ~ `migration` ~ `swap` ~
  `tiering`; `cache` ~ `pooling` ~ `store`.
- Historical or community renames for the same concept: `attention cache` ->
  `KV cache` -> `context caching`.
- Stem variants when the search engine does not normalize: `compress` /
  `compression`, `quantize` / `quantization`.

Rules:

- Preserve the original topic scope. `KV cache` -> `cache` is too broad.
  `compression` -> `model compression` is fine only when the topic is already
  model-bound.
- Do not introduce hardware (`H100`, `CXL`), system (`vLLM`, `DistServe`), or
  metric (`throughput`, `tail latency`) names here. Those are handled by venue
  sweep and optional adapters, not by alias expansion.
- 2-5 aliases per topic is enough. More aliases without new semantic ground is
  wasted recall.

## Venue Search

Use venue pages before keyword APIs because keyword APIs can miss papers when
queries do not match titles exactly. For this ARIS instance, use this fallback
order for every recommended venue: DBLP first; official conference root or
program page second; targeted web query fallback third.

1. DBLP/proceedings pages.
2. Official conference root or program page.
3. Targeted web query.

For architecture/systems topics, fetch the current and previous year first, then
extend to five years when the topic is still underspecified or historical
context matters.

### Recommended Venue Coverage

Approved recommended venues for this domain are intentionally narrow for now.
Add more only when explicitly requested and after URL patterns are verified.

| Venue | DBLP pattern | Official URL guidance | Targeted fallback query | last_verified |
| --- | --- | --- | --- | --- |
| ASPLOS | `https://dblp.org/db/conf/asplos/asplos{YYYY}-{PART}.html` for split DBLP parts, usually `1` and `2` | `https://www.asplos-conference.org/asplos{YYYY}/` root; use its accepted-papers or program link if present | `"ASPLOS {YYYY} accepted papers program"` | 2026-05-21 |
| ISCA | `https://dblp.org/db/conf/isca/isca{YYYY}.html` | `https://iscaconf.org/isca{YYYY}/` root; use its accepted-papers or program link if present | `"ISCA {YYYY} accepted papers program"` | 2026-05-21 |
| MICRO | `https://dblp.org/db/conf/micro/micro{YYYY}.html` | Use edition-aware official roots from `https://microarch.org/`; for example MICRO 57 maps to 2024 and MICRO 58 maps to 2025 | `"MICRO {YYYY} accepted papers program"` | 2026-05-21 |
| HPCA | `https://dblp.org/db/conf/hpca/hpca{YYYY}.html` | `https://hpca-conf.org/{YYYY}/` root; use its accepted-papers or program link if present | `"HPCA {YYYY} accepted papers program"` | 2026-05-21 |
| SOSP | `https://dblp.org/db/conf/sosp/sosp{YYYY}.html` | `https://sigops.org/s/conferences/sosp/{YYYY}/` root when available; otherwise use the ACM SIGOPS conference page | `"SOSP {YYYY} accepted papers program"` | 2026-05-21 |
| OSDI | `https://dblp.org/db/conf/osdi/osdi{YYYY}.html` | `https://www.usenix.org/conference/osdi{YY}/technical-sessions` | `"OSDI {YYYY} technical sessions accepted papers"` | 2026-05-21 |
| NSDI | `https://dblp.org/db/conf/nsdi/nsdi{YYYY}.html` | `https://www.usenix.org/conference/nsdi{YY}/technical-sessions` | `"NSDI {YYYY} technical sessions accepted papers"` | 2026-05-21 |
| USENIX ATC | `https://dblp.org/db/conf/usenix/usenix{YYYY}.html` | `https://www.usenix.org/conference/atc{YY}/technical-sessions` | `"USENIX ATC {YYYY} technical sessions accepted papers"` | 2026-05-21 |
| SIGCOMM | `https://dblp.org/db/conf/sigcomm/sigcomm{YYYY}.html` | Start at `https://conferences.sigcomm.org/sigcomm/{YYYY}/`; follow the site-local program or accepted-papers link because subpaths vary by year | `"SIGCOMM {YYYY} accepted papers program"` | 2026-05-21 |
| EuroSys | `https://dblp.org/db/conf/eurosys/eurosys{YYYY}.html` | Start from `https://www.eurosys.org/` or the year-specific EuroSys site linked there; verify the current subpath before use | `"EuroSys {YYYY} accepted papers program"` | 2026-05-21 |
| MLSys | `https://dblp.org/db/conf/mlsys/mlsys{YYYY}.html` | `https://mlsys.org/virtual/{YYYY}/papers.html` when present; otherwise use the official `https://mlsys.org/` year page | `"MLSys {YYYY} accepted papers program"` | 2026-05-21 |

Avoid treating fragile subpaths as authoritative until verified for the specific
year. MICRO is especially edition-based rather than two-digit-year based, so map
year to edition before using official pages.

## User Sources

### Zotero

Traverse collections before keyword search:

1. Get the full collection tree.
2. Split topic and expanded terms into fragments such as `compression`, `nic`,
   `rdma`, `cxl`, `checkpoint`.
3. Match any collection name at any depth containing any fragment.
4. Retrieve items from matched collections, then run keyword search as fallback.
5. For relevant items, extract annotations, notes, tags, collection path, and
   BibTeX when available.

### Obsidian

Search notes, tags, frontmatter, and linked notes. Prefer user summaries and
insights over generic metadata when synthesizing consensus or gaps.

## Optional Adapters

Run optional adapters only when explicitly listed in `sources:`.

```bash
python3 tools/arxiv_fetch.py search "QUERY" --max 10
python3 tools/semantic_scholar_fetch.py search "QUERY" --max 10 --fields-of-study "Computer Science,Engineering" --publication-types "JournalArticle,Conference"
python3 tools/deepxiv_fetch.py search "QUERY" --max 10
python3 tools/deepxiv_fetch.py paper-brief ARXIV_ID
python3 tools/deepxiv_fetch.py paper-head ARXIV_ID
python3 tools/exa_search.py search "QUERY" --max 10 --category "research paper" --content highlights
python3 tools/exa_search.py search "QUERY" --max 10 --content highlights
python3 tools/openalex_fetch.py search "QUERY" --max 10 --year "2022-" --type article --sort relevance
```

Semantic Scholar 429: retry once, then skip. OpenAlex requires `requests`.
Gemini: prefer MCP; otherwise `gemini -p` with a 120s timeout. Ask Gemini for
exact title, authors, year, venue, arXiv ID, DOI, code URL, and one-sentence
contribution. Do not use Gemini-reported citation counts.

## Merge Rules

- De-duplicate: DOI -> arXiv ID -> normalized title; for non-paper web artifacts,
  exact URL before title.
- Prefer Semantic Scholar for venue/DOI/citation/TLDR, arXiv for PDF/abstract,
  OpenAlex for affiliation/funding, and DeepXiv for section notes.
- Keep source labels merged on one canonical row.
