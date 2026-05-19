# Research Lit Search And Sources Reference

Use this reference only when `/research-lit` needs concrete source commands,
conference URL patterns, or adapter-specific fallback details.

## Venue Search

Prefer exhaustive venue pages before keyword APIs. Keyword APIs can miss papers
when queries do not match titles exactly; direct proceedings pages expose the
whole accepted-paper list for filtering.

### DBLP Direct Proceedings

Fetch current year and previous year:

```text
https://dblp.org/db/conf/micro/micro2025.html
https://dblp.org/db/conf/isca/isca2025.html
https://dblp.org/db/conf/hpca/hpca2025.html
https://dblp.org/db/conf/asplos/asplos2026.html
```

Common slugs: `micro`, `isca`, `hpca`, `asplos`, `sigcomm`, `nsdi`, `osdi`,
`atc`, `eurosys`, `fccm`, `dac`. For journals, use DBLP journal volume pages
when the year/volume mapping is known.

### Recent Conference Programs

Use official programs when DBLP is incomplete for a very recent conference.
Known patterns:

| Venue | Pattern |
| --- | --- |
| ASPLOS | `https://www.asplos-conference.org/asplos{YYYY}/program/` |
| MICRO | `https://microarch.org/micro{YY}/program.php` |
| ISCA | `https://iscaconf.org/isca{YYYY}/program/` |
| HPCA | `https://hpca-conf.org/{YYYY}/program/` |
| SIGCOMM | `https://conferences.sigcomm.org/sigcomm/{YYYY}/program/` |
| NSDI | `https://www.usenix.org/conference/nsdi{YY}/technical-sessions` |
| OSDI | `https://www.usenix.org/conference/osdi{YY}/technical-sessions` |
| USENIX ATC | `https://www.usenix.org/conference/atc{YY}/technical-sessions` |
| EuroSys | `https://{YYYY}.eurosys.org/program/` |
| FCCM | `https://www.fccm.org/fccm-{YYYY}-program/` |

If a pattern fails, search `"{venue} {YYYY} program accepted papers"`.

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
