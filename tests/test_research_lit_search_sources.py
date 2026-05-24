from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_LIT = REPO_ROOT / "skills" / "research-lit" / "SKILL.md"
SEARCH_SOURCES = REPO_ROOT / "skills" / "research-lit" / "references" / "search-sources.md"
VERIFY_TOOL = REPO_ROOT / "tools" / "verify_venue_urls.py"

APPROVED_VENUES = {
    "ASPLOS",
    "ISCA",
    "MICRO",
    "HPCA",
    "SOSP",
    "OSDI",
    "NSDI",
    "USENIX ATC",
    "SIGCOMM",
    "EuroSys",
    "MLSys",
}


def read(path: Path) -> str:
    return path.read_text()


def table_rows(text: str, heading: str) -> list[dict[str, str]]:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + 1)
    section = text[start:] if next_heading == -1 else text[start:next_heading]
    lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        if header is None:
            header = cells
            continue
        assert len(cells) == len(header), (header, cells)
        rows.append(dict(zip(header, cells)))
    return rows


def section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def test_research_lit_default_sources_and_explicit_adapters_are_stable() -> None:
    text = read(RESEARCH_LIT)

    assert (
        "Default sources only: Zotero, Obsidian, local PDFs, arXiv, DBLP/proceedings, WebSearch."
        in text
    )
    assert "Optional sources `semantic-scholar`, `deepxiv`, `exa`, `gemini`, and" in text
    assert "`openalex` never run unless explicitly listed." in text

    adapters = table_rows(text, "### Source Adapters")
    explicit_by_source = {row["Source"]: row["Explicit-only?"] for row in adapters}
    assert explicit_by_source["Semantic Scholar"] == "Yes"
    assert explicit_by_source["DeepXiv"] == "Yes"
    assert explicit_by_source["Exa"] == "Yes"
    assert explicit_by_source["Gemini"] == "Yes"
    assert explicit_by_source["OpenAlex"] == "Yes"


def test_research_lit_exposes_preprint_evidence_maturity() -> None:
    text = read(RESEARCH_LIT)

    required_fragments = [
        "preprint status",
        "full-text availability",
        "artifact/code status",
        "evaluation limitations",
    ]
    for fragment in required_fragments:
        assert fragment in text


def test_search_sources_venue_scope_and_url_metadata_are_curated() -> None:
    text = read(SEARCH_SOURCES)

    assert "Execution order follows `skills/research-lit/SKILL.md`" in text
    assert "DBLP first" in text
    assert re.search(r"official conference root or\s+program page second", text)
    assert re.search(r"targeted web query fallback third", text)

    venue_rows = table_rows(text, "### Recommended Venue Coverage")
    venues = {row["Venue"] for row in venue_rows}
    assert venues == APPROVED_VENUES
    assert all(row.get("last_verified") for row in venue_rows)

    unapproved_venues = {"FCCM", "DAC", "FAST", "SoCC"}
    assert venues.isdisjoint(unapproved_venues)


def test_search_sources_omits_stale_or_unverified_program_patterns() -> None:
    text = read(SEARCH_SOURCES)

    assert "micro{YY}" not in text
    assert "program.php" not in text
    assert "| SIGCOMM | `https://conferences.sigcomm.org/sigcomm/{YYYY}/program/`" not in text
    assert "| EuroSys | `https://{YYYY}.eurosys.org/program/`" not in text


def test_search_sources_dblp_patterns_use_year_tokens() -> None:
    text = read(SEARCH_SOURCES)
    venue_rows = table_rows(text, "### Recommended Venue Coverage")
    for row in venue_rows:
        dblp = row["DBLP pattern"]
        assert "{YYYY}" in dblp or "{YY}" in dblp, (row["Venue"], dblp)


def test_verify_venue_urls_tool_is_available_for_maintenance() -> None:
    assert VERIFY_TOOL.exists()
    text = read(VERIFY_TOOL)

    assert "VenuePattern" in text
    assert "current and previous year" in text
    assert "status_code" in text
    assert "redirect_target" in text
    assert "venue_relevant" in text


def test_synthesize_landscape_projects_prose_into_landscape_pack_ids() -> None:
    text = read(RESEARCH_LIT)
    synthesize = section(text, "### 4. Synthesize Landscape", "### 5. Save Outputs")

    assert "ID-backed projection" in synthesize
    assert "Sections 2-4" in synthesize
    for id_family in ("`B*`", "`S*`", "`EC-P*`", "`EC-W*`", "`G*`"):
        assert id_family in synthesize

    assert "Section 2" in synthesize
    assert "Consensus and disagreements" in synthesize
    assert "hardware-agnostic" in synthesize
    assert "workload/model-size class" in synthesize

    assert "same `B*` bottleneck" in synthesize
    assert "comparable workload class" in synthesize
    assert re.search(r"comparable\s+hardware/system tier", synthesize)

    assert re.search(r"no more than 8\s+total", synthesize)
    assert "`B*.residual_gap`" in synthesize
    assert "`S*.missing_piece`" in synthesize
    assert "explicit negative evidence" in synthesize


def test_synthesize_landscape_map_uses_topic_specific_unresolved_bottlenecks() -> None:
    text = read(RESEARCH_LIT)
    synthesize = section(text, "### 4. Synthesize Landscape", "### 5. Save Outputs")
    landscape = re.search(r"- Landscape map:.*?(?=\n- Consensus)", synthesize, flags=re.S)

    assert landscape is not None
    landscape_bullet = landscape.group(0)
    landscape_flat = re.sub(r"\s+", " ", landscape_bullet)

    assert "concrete unresolved problems or bottlenecks specific to the current topic" in landscape_flat
    assert "solution attempts already tried" in landscape_flat
    assert "EC-P*.limitations" in landscape_flat
    assert "EC-W*.limitations" in landscape_flat
    assert "KV cache CXL" in landscape_flat
    assert "Section 5 `B*` bottlenecks and `S*` solution attempts" in landscape_flat
    assert not re.search(
        r"such as compute,\s+memory/KV cache,\s+interconnect/network,\s+"
        r"storage/checkpointing,\s+scheduling/runtime,\s+or co-design",
        landscape_bullet,
    )
