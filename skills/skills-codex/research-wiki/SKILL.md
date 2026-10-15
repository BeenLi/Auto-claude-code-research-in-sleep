---
name: research-wiki
description: "Persistent research knowledge base that accumulates papers, ideas, experiments, claims, and their relationships across the entire research lifecycle. Inspired by Karpathy's LLM Wiki pattern. Use when user says \"知识库\", \"research wiki\", \"add paper\", \"wiki query\", \"查知识库\", or wants to build/query a persistent field map."
argument-hint: "[subcommand: init|ingest|sync|query|update|lint|stats]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, spawn_agent, send_input
---

# Research Wiki: Persistent Research Knowledge Base

Subcommand: **$ARGUMENTS**

## Overview

The research wiki is a persistent, per-project knowledge base that accumulates structured knowledge across the entire ARIS research lifecycle. Unlike one-off literature surveys that are used and forgotten, the wiki **compounds** — every paper read, idea tested, experiment run, and review received makes the wiki smarter.

Inspired by [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): compile knowledge once, keep it current, don't re-derive on every query.

## Core Concepts

### Four Entity Types

| Entity | Directory | Node ID format | What it represents |
|--------|-----------|---------------|--------------------|
| **Paper** | `papers/` | `paper:<slug>` | Agent-facing projection of a paper; full paper notes stay in Obsidian when synced |
| **Idea** | `ideas/` | `idea:<id>` | A research idea (proposed, handed off, parked, tested, or failed) — written via `upsert_idea` (see Hook 2) |
| **Experiment** | `experiments/` | `exp:<id>` | A concrete experiment run with its verdict — born via `add_experiment` (see Hook 3) |
| **Claim** | `claims/` | `claim:<id>` | A theorem/headline with an honest PROOF status — born via `/proof-checker` (see Hook 4) |

### Typed Relationships (`graph/edges.jsonl`)

| Edge type | From → To | Meaning |
|-----------|-----------|---------|
| `extends` | paper → paper | Builds on prior work |
| `contradicts` | paper → paper | Disagrees with results/claims |
| `addresses_gap` | paper\|idea → gap | Targets a known field gap |
| `inspired_by` | idea → paper | Idea sourced from this paper |
| `tested_by` | idea\|claim → exp | Tested in this experiment |
| `supports` | exp → claim\|idea | Experiment confirms claim |
| `invalidates` | exp → claim\|idea | Experiment disproves claim |
| `supersedes` | paper → paper | Newer work replaces older |
| `depends_on` | claim → claim | Proof-obligation dependency (written by `add_claim`) |
| `refutes` | claim → claim | A claim that falsifies another (written by `add_claim`) |
| `uses` | claim → paper | Claim imports a result or ingredient (written by `add_claim`) |

Edges are stored in `graph/edges.jsonl` only. The `## Connections` section on each page is **auto-generated** from the graph — never hand-edit it.

### Capture hygiene (anti-self-poisoning)

Before persisting an **idea / claim / experiment** note, screen it for
operational noise that would harden into a self-cited falsehood (see
[`shared-references/capture-antipatterns.md`](../shared-references/capture-antipatterns.md)).
Resolve the helper via the canonical chain (integration-contract §2):
`.aris/tools/capture_filter.py` → `tools/capture_filter.py` →
`$ARIS_REPO/tools/capture_filter.py` (warn-and-skip if unresolved). Run
`python3 <capture_filter> -` on the note text; if it flags **env-failure /
transient-error / negative-tool-claim**, do NOT store it as a durable node —
rewrite it to the *fix / missing config / workaround*, or drop it. Never store
"codex/gemini/the reviewer can't do X" — that gets loaded into every future
session and cited against the agent long after the real cause is gone. (The wiki's
"failed ideas → anti-repeat memory" is the GOOD inverse: a class-level *research*
finding, not operational noise.)

## Wiki Directory Structure

```
research-wiki/
  index.md               # categorical index (auto-generated)
  log.md                 # append-only timeline
  gap_map.md             # field gaps with stable IDs (G1, G2, ...)
  query_pack.md          # compressed summary for /idea-creator (auto-generated, max 8000 chars)
  papers/
    <slug>.md            # one page per paper
  ideas/
    <idea_id>.md         # one page per idea
  experiments/
    <exp_id>.md          # one page per experiment
  claims/
    <claim_id>.md        # one page per testable claim
  graph/
    edges.jsonl          # materialized current relationship graph
```

## Subcommands

## Helper resolution (run before any subcommand below)

All wiki operations except plain directory bootstrap go through a single
canonical helper, `tools/research_wiki.py`. Skills that touch the wiki
must resolve `$WIKI_SCRIPT` via the chain below — never hard-code
`python3 tools/research_wiki.py …`. Hard-coding silently fails when
the project does not have `tools/` on disk (the post-`install_aris.sh`
default), which is exactly the failure mode that left a real user's
`research-wiki/` empty for a week.

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
ARIS_REPO="${ARIS_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills-codex.txt 2>/dev/null)}"
ARIS_REPO="${ARIS_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills-gemini.txt 2>/dev/null)}"
if [ -z "${ARIS_REPO:-}" ] && [ -f "$HOME/.aris/repo" ]; then
  ARIS_REPO=$(cat "$HOME/.aris/repo" 2>/dev/null) || true
fi
WIKI_SCRIPT=".aris/tools/research_wiki.py"
[ -f "$WIKI_SCRIPT" ] || WIKI_SCRIPT="tools/research_wiki.py"
[ -f "$WIKI_SCRIPT" ] || { [ -n "${ARIS_REPO:-}" ] && WIKI_SCRIPT="$ARIS_REPO/tools/research_wiki.py"; }
[ -f "$WIKI_SCRIPT" ] || {
  echo "ERROR: research_wiki.py not found at .aris/tools/, tools/, \$ARIS_REPO/tools/, or via ~/.aris/repo." >&2
  echo "       Fix one of:" >&2
  echo "         1. rerun 'bash tools/install_aris.sh' from the ARIS repo (creates .aris/tools symlink)" >&2
  echo "         2. export ARIS_REPO=<path-to-ARIS-repo>" >&2
  echo "         3. cp <ARIS-repo>/tools/research_wiki.py tools/" >&2
  exit 1
}
```

`/research-wiki` itself is the wiki tool — if the helper is missing the
skill **hard-fails**. Caller skills that update the wiki as a side
effect (`/idea-creator`, `/result-to-claim`, `/research-lit`, `/arxiv`,
`/alphaxiv`, `/deepxiv`, `/semantic-scholar`, `/exa-search`) use the
same chain but **warn-and-skip** instead of hard-failing — their
primary output (idea list, claim verdict, paper summary) must still be
delivered to the user.

### `/research-wiki init`

Initialize the wiki for the current project. After resolving
`$WIKI_SCRIPT` per the chain above:

```bash
python3 "$WIKI_SCRIPT" init research-wiki/
```

The helper creates `research-wiki/{papers,ideas,experiments,claims,graph}/`
plus `index.md`, `log.md`, `gap_map.md`, **`query_pack.md`**, and
`graph/edges.jsonl`, then appends `"Wiki initialized"` to `log.md`.

(Earlier versions of this skill described a prose-only init that
omitted `query_pack.md` — that drifted from the helper and made
`/idea-creator`'s Phase 0 query-pack check fall through to a
`rebuild_query_pack` invocation that, under the old hard-coded path,
silently failed. Delegating init to the helper is the single source of
truth for the wiki schema.)

### `/research-wiki ingest "<paper title>" — arxiv: <id>`

Add a paper to the wiki. This subcommand is thin wrapping around
`python3 "$WIKI_SCRIPT" ingest_paper …`, which is the single
implementation of paper ingest in ARIS (per
[`shared-references/integration-contract.md`](../shared-references/integration-contract.md)
— one helper, no copies). The helper does all of:

1. **Fetch metadata** — queries the arXiv Atom API when `--arxiv-id` is given
   (descriptive User-Agent with the optional `ARIS_VERIFY_EMAIL` contact;
   retries HTTP 429 / 406 and the "Rate exceeded." body; a 406 is re-issued
   through `curl` once)
2. **Generate slug** — `<first_author_last_name><year>_<keyword>`; letters
   outside ASCII (Chinese titles, accented author names) are kept, so two
   Chinese papers by the same author in the same year no longer collide
3. **Check dedup** — skip an existing page unless `--update-on-exist`
4. **Create page** — `papers/<slug>.md` with the schema below
5. **Rebuild `index.md`** and `query_pack.md`
6. **Append `log.md`**

Edge extraction (step 5/8 in the old manual flow) is **not** in
`ingest_paper`; do it as a follow-up with `add_edge` per relationship
identified:

```bash
# arXiv-known paper
python3 "$WIKI_SCRIPT" ingest_paper research-wiki/ \
    --arxiv-id 2501.12345 --thesis "One-line claim from abstract."

# Venue paper with no arXiv mirror
python3 "$WIKI_SCRIPT" ingest_paper research-wiki/ \
    --title "Attention Is All You Need" \
    --authors "Ashish Vaswani, Noam Shazeer, …" --year 2017 --venue "NeurIPS"

# Manual edge after ingest
python3 "$WIKI_SCRIPT" add_edge research-wiki/ \
    --from "paper:vaswani2017_attention_all_you" \
    --to "paper:chen2025_factorized_gap" \
    --type "extends" --evidence "Section 3.2: adapts the encoder block …"
```

Other skills (`/research-lit`, `/arxiv`, `/alphaxiv`, `/deepxiv`,
`/semantic-scholar`, `/exa-search`) call the same helper directly in
their own last step — they don't re-route through `/research-wiki
ingest` as a subcommand, so they don't need an LLM roundtrip.

### `/research-wiki sync — arxiv-ids <id1>,<id2>,...`

Batch backfill: ingest one or more arXiv IDs that were read earlier
without being ingested (e.g., because `research-wiki/` was set up after
the reading happened, or a hook didn't fire).

```bash
# Explicit list
python3 "$WIKI_SCRIPT" sync research-wiki/ \
    --arxiv-ids 2310.06770,1706.03762

# From a file (one id per line, # comments ok)
python3 "$WIKI_SCRIPT" sync research-wiki/ --from-file ids.txt
```

All ids are fetched in **one** arXiv `id_list` request (N papers cost one
request, which avoids burst 429s); ids the batch did not return fall back to a
per-id fetch. Dedup is handled per-id; already-ingested papers are skipped
silently.
This is the recommended **manual repair** step (see integration
contract §5 Backfill). `sync` does not scan session traces — callers
declare the ids explicitly.

**Paper page schema** (exactly what `ingest_paper` and `sync-obsidian`
emit — do not handwrite alternative generated fields):

```markdown
---
type: paper
node_id: paper:<slug>
source: obsidian
obsidian_path: "001-input/PaperRead/PaperNotes/<note>.md"
title: "<full title>"
method_name: "<method>"
authors: ["First A. Author", "Second B. Author"]
year: 2025
venue: "arXiv"
external_ids:
  arxiv: "2501.12345"
  doi: null
  s2: null
zotero:
  item_id: null
  item_key: null
  collection: null
tags: ["tag1", "tag2"]
projection_updated: 2026-04-07T10:12:00Z
---

# <full title>

<!-- BEGIN OBSIDIAN PROJECTION -->
## Agent Summary

- One-line:
- Core problem:
- Key insight:
- System bottleneck:
- Method:
- Key results:
- Limitations:
- Reusable lessons:

## Evaluation Hints

- Workloads:
- Baselines:
- Metrics:
- Artifacts / code:
- Repro risk:

## Related Papers

- paper_ref:
<!-- END OBSIDIAN PROJECTION -->

<!-- BEGIN PROJECT NOTES -->
## Relevance to Current ARIS Project

Manual ARIS notes go here.

## Local Claim / Gap Notes

Manual ARIS notes go here.
<!-- END PROJECT NOTES -->
```

`sync-obsidian` rewrites only the `OBSIDIAN PROJECTION` region and generated
frontmatter. It preserves the `PROJECT NOTES` region byte-for-byte where
practical. `ingest_paper` emits the same markers, with an empty Obsidian
projection and manual ingest notes in `PROJECT NOTES`.

The `PROJECT NOTES` sections start as `_TODO._` scaffolds. `/wiki-enrich` fills
them from alphaXiv / DeepXiv / arXiv content and never touches the Obsidian
projection, the frontmatter or `## Connections`.

### `/research-wiki sync-obsidian --paper-notes-dir <dir>`

Project Obsidian paper notes into `research-wiki/papers/*.md` while keeping
Obsidian as the source of truth for full paper knowledge. This command does
not read Obsidian concept notes and does not write back to Obsidian or Zotero.

```bash
python3 "$WIKI_SCRIPT" sync-obsidian research-wiki/ \
    --paper-notes-dir "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/ob-career/001-input/PaperRead/PaperNotes" \
    --zotero-db "$HOME/Zotero/zotero.sqlite" \
    --dry-run \
    --report obsidian-sync-report.md
```

Rules:

- Matching defaults to strong IDs only: Zotero item id/key, legacy Zotero key, DOI, arXiv id.
- `--match-loose` is required for normalized-title or `method_name` fallback matching.
- `--limit N` processes the newest N notes by mtime descending.
- Zotero is read-only enrichment only; Obsidian values win and conflicts are reported.
- Historical pages without markers are migrated lazily only when touched by this sync.

### `/research-wiki query "<topic>"`

Generate `query_pack.md` — a compressed, context-window-friendly summary:

**Fixed budget (max 8000 chars / ~2000 tokens):**

| Section | Budget | Content |
|---------|--------|---------|
| Project direction | full sections | Structured extraction from `RESEARCH_BRIEF.md` by `## ` heading (Problem / Constraints / Direction / Background / Non-Goals / Domain Knowledge / Existing Results), in priority order. No per-field char cap — the 8000-char assembly loop is the only safety net. Falls back to a flat 600-char slice if the brief uses no known headings. |
| Top 5 gaps | 1200 chars | From gap_map.md, ranked by: unresolved + linked ideas + failed experiments |
| Paper clusters | 1600 chars | 3-5 clusters by tag overlap, 2-3 sentences each |
| Failed ideas | 1400 chars | **Always included** — highest anti-repetition value. Gated on the frontmatter `outcome` (`negative` / `mixed`) only; body text never banlists an idea |
| Top papers | 1800 chars | 8-12 generated paper projections, including Obsidian path and compact agent fields |
| Claims | 1200 chars | Claim PROOF status, name, and statement summary |
| Experiments | 1400 chars | Setup (or hardware/duration), result (or metrics), verdict, and linked claim/idea when available |
| Active chains | 900 chars | Recent relationship chains |
| Open unknowns | 500 chars | Unresolved questions across the wiki |

**Pruning priority** (when over budget): low-ranked papers > cluster detail > chain detail. **Never prune** failed ideas or top gaps first.

**Key rule:** Read from short fields only: generated paper projection, frontmatter, gap summary, failure note, claim summary, experiment setup/result. Do not expand full Obsidian paper notes or concept notes.

### `/research-wiki update <node_id> — <field>: <value>`

Update a specific entity:

```
/research-wiki update paper:chen2025 — relevance: core
/research-wiki update idea:001 — outcome: negative
/research-wiki update claim:C1 — status: refuted
```

After any update: rebuild `query_pack.md`, update `log.md`.

### `/research-wiki lint`

Health check the wiki:

1. **Orphan pages** — entities with zero edges
2. **Stale claims** — claims still `status: drafted` or `status: unproven` (or the legacy `status: reported`) older than 14 days
3. **Contradictions** — claims with both `supports` and `invalidates` edges
4. **Missing connections** — papers sharing 2+ tags but no explicit relationship
5. **Dead ideas** — `stage: proposed` ideas that were never tested
6. **Sparse pages** — pages with 3+ empty sections

Output a `LINT_REPORT.md` with suggested fixes.

### `/research-wiki stats`

Quick overview:

```
📚 Research Wiki Stats
Papers: 28 (12 core, 10 related, 6 peripheral)
Ideas: 7 (3 failed, 1 succeeded, 2 parked)
Experiments: 12
Claims: 15 (2 refuted, 1 sound-modulo-imports, 4 unproven, 8 verified)
Edges: 64
Gaps: 8 (3 unresolved)
Last updated: 2026-04-07T10:12:00Z
```

### Node writers: `add_claim` / `upsert_idea` / `add_experiment`

All four node types are written by deterministic helper commands, never by
freehand markdown. Each writer validates its enums, quarantines model-authored
body text (raw text goes to `graph/quarantine.log`), wires its typed edges with
`add_edge`, rebuilds `index.md` + `query_pack.md`, and appends to `log.md`. All
three **skip an existing page by slug** unless `--update-on-exist` is passed, and
exit non-zero on an invalid value so callers can `|| echo WARN …`.

```bash
# Claim (born only at /proof-checker — Hook 4)
python3 "$WIKI_SCRIPT" add_claim research-wiki/ --slug thm-main-ub \
  --name "Main upper bound" --status verified \
  --provenance ".aris/traces/proof-checker/<run>/" --statement "..." \
  [--description "..."] [--scope "..."] [--evidence "..."] [--tags a,b] \
  [--addresses G2,G10] [--extends paper:slug] [--uses paper:slug] \
  [--depends-on claim:other] [--refutes claim:bad] [--update-on-exist]

# Idea (written by /idea-creator — Hook 2)
python3 "$WIKI_SCRIPT" upsert_idea research-wiki/ --slug kv-cxl --title "..." \
  --stage <proposed|handed_off|parked|archived|active|piloted> --outcome pending \
  [--thesis "..."] [--risks "..."] [--based-on paper:slug,...] [--target-gaps G2,...] \
  [--park-reason <reason> --revisit-condition "..."] [--description "..."] \
  [--tags a,b] [--update-on-exist]

# Experiment (born at /result-to-claim, the verdict owner — Hook 3)
python3 "$WIKI_SCRIPT" add_experiment research-wiki/ --slug exp-001 \
  --idea idea:<id> --verdict <yes|partial|no> --confidence <high|medium|low> \
  [--title "..."] [--date ...] [--hardware ...] [--duration ...] \
  [--metrics "..."] [--reasoning "..."] [--provenance <run dir>] [--tags a,b] \
  --update-on-exist
```

| Writer | Enumerated field | Valid values |
|--------|------------------|--------------|
| `add_claim` | `--status` (PROOF axis only) | `drafted`, `unproven`, `sound-modulo-imports`, `verified`, `refuted`, `retracted` |
| `upsert_idea` | `--outcome` (drives the failed-idea banlist + stats) | `unknown`, `pending`, `negative`, `mixed`, `positive` |
| `upsert_idea` | `--stage` | `proposed`, `active`, `piloted`, `archived`, plus the local pool stages `handed_off` and `parked` |
| `add_experiment` | `--verdict` / `--confidence` | `yes`, `partial`, `no` / `high`, `medium`, `low` |

Edges written: `add_claim` → `addresses_gap` / `extends` / `uses` / `depends_on` /
`refutes`; `upsert_idea` → `inspired_by` (from `--based-on`) and `addresses_gap`
(from `--target-gaps`); `add_experiment` → `idea --tested_by--> exp`. Bare ids are
namespaced (`G2` → `gap:G2`, `foo2024` → `paper:foo2024` / `claim:foo2024` /
`idea:foo2024`); a target missing from the wiki prints a dangling-edge warning
but is still recorded. A `--stage parked` idea should carry both
`--park-reason` and `--revisit-condition` (stored in frontmatter; the helper
warns when either is missing). Pass an explicit `--slug`: without one the
claim/idea slug falls back to the title slugifier, which prefixes
`unknown0000_`.

## Integration with Existing Workflows

All paper-reading skills follow the same **integration contract** (see
[`shared-references/integration-contract.md`](../shared-references/integration-contract.md)):

- single predicate — `[ -d research-wiki/ ]`
- single canonical helper — `python3 "$WIKI_SCRIPT" ingest_paper …` after resolving `$WIKI_SCRIPT` via the chain at the top of this SKILL
- concrete artifact — `papers/<slug>.md` + `log.md` entry
- backfill — `sync --arxiv-ids …`
- diagnostic — `verify_wiki_coverage.sh` (Policy E; resolved per integration-contract §2)

### Hook 1: After `/research-lit` finds papers

```
# At end of research-lit, after synthesis:
if research-wiki/ exists AND $WIKI_SCRIPT resolved (chain at top of this SKILL):
    for paper in top_relevant_papers (limit 8-12):
        python3 "$WIKI_SCRIPT" ingest_paper research-wiki/ \
            --arxiv-id <id> [--thesis "..."] [--tags "..."]
        for each explicit relation to existing wiki paper:
            python3 "$WIKI_SCRIPT" add_edge research-wiki/ \
                --from "paper:<slug>" --to "<target>" \
                --type <extends|contradicts|addresses_gap|...> \
                --evidence "..."
    log "research-lit ingested N papers"
elif research-wiki/ exists but $WIKI_SCRIPT did not resolve:
    warn "wiki update skipped — research_wiki.py unreachable; rerun install_aris.sh"
```

Each paper-reading skill ships its own Step "Update Research Wiki (if
active)" that calls the same helper once per paper it touched. The
business logic is not duplicated — only the loop over that skill's
specific result set differs.

### Hook 2: `/idea-creator` reads AND writes wiki

**Before ideation:**
```
if research-wiki/query_pack.md exists (and < 7 days old):
    prepend query_pack to landscape context
    treat failed ideas as banlist
    treat top gaps as search seeds
    still run fresh literature search for last 3-6 months
```

**After ideation (CRITICAL — without it, `ideas/` stays empty; runs on EVERY
generation, including a re-run with updated constraints):** the page write is a
**deterministic helper command**, not a freehand step the model can skip:
```
for idea in recommended_ideas + parked_ideas + eliminated_ideas:
    python3 "$WIKI_SCRIPT" upsert_idea research-wiki/ \
      --slug <stable-id> --title <title> --stage <proposed|archived> \
      --outcome pending --thesis <...> --risks <...> \
      --based-on <paper:slug,...> --target-gaps <G2,...>
    # one call: writes ideas/<slug>.md, wires inspired_by/addresses_gap edges,
    # rebuilds index + query_pack, logs. Default skip-on-exist (won't clobber an
    # existing idea enriched by /result-to-claim). `outcome` ∈ {unknown, pending,
    # negative, mixed, positive} — the experiment verdict is set later by
    # /result-to-claim, never guessed at ideation.

    # Candidate-pool fields go on the same page through `update` (top-level
    # frontmatter; works on any upsert_idea page):
    python3 "$WIKI_SCRIPT" update research-wiki/ idea:<stable-id> --field pool_status --value <selected|backup|parked|eliminated>
    # parked ideas also carry:
    python3 "$WIKI_SCRIPT" update research-wiki/ idea:<stable-id> --field park_reason --value <park_reason>
    python3 "$WIKI_SCRIPT" update research-wiki/ idea:<stable-id> --field revisit_condition --value "<revisit_condition>"
log "idea-creator wrote N ideas (M recommended, P parked, K eliminated)"
```

`upsert_idea` also accepts `--stage parked` / `--stage handed_off` with
`--park-reason` / `--revisit-condition` for writing a parked idea in one call;
`/idea-creator` uses the upstream stages plus `update` shown above. A parked or
eliminated idea is never put on the failed-idea banlist: only a frontmatter
`outcome: negative | mixed` (set by `/result-to-claim`) does that.

### Hook 3: After `/result-to-claim` verdict

```
# Create/refresh the experiment node FIRST via the deterministic helper (verdict owner
# → --update-on-exist). This is the experiment BIRTH point. add_edge does NOT verify
# node existence, so GATE the supports/invalidates edges below on the node having been
# born (EXP_NODE_OK) — else they'd dangle off a missing exp node.
EXP_NODE_OK = (python3 "$WIKI_SCRIPT" add_experiment research-wiki/ --slug <exp_id> \
  --idea idea:<active_idea> --verdict <yes|partial|no> --confidence <high|medium|low> \
  --metrics <...> --reasoning <...> --provenance <run dir> --update-on-exist) succeeded
  # writes page + idea--tested_by-->exp edge + rebuilds index/query_pack

# Record empirical support as EDGES ONLY, and ONLY if EXP_NODE_OK — never overwrite the
# claim's `status`. A claim's `status` is the PROOF axis (verified / sound-modulo-imports
# / refuted / unproven / drafted / retracted), owned by /proof-checker (the claim birth
# point). Experiment support is a SEPARATE axis carried entirely by supports/invalidates
# edges; writing "supported"/"invalidated" into status is rejected by the validator.
if EXP_NODE_OK:
    for claim_id in resolved_claims:
        if verdict == "yes":
            add_edge(exp_id, claim_id, "supports")
        elif verdict == "partial":
            add_edge(exp_id, claim_id, "supports")   # partial — qualify in --evidence
        else:
            add_edge(exp_id, claim_id, "invalidates")

# Update idea outcome (positive | mixed | negative) by editing the idea page in
# place — never by re-running upsert_idea --update-on-exist, which would clobber
# the enriched body.
update_idea(active_idea_id, outcome=verdict)

# If failed, record WHY for future ideation ("Failure / Risk Notes" and
# "Lessons Learned" sections; query_pack's failed-idea banlist reads them)
if verdict in ("no", "partial"):
    update_idea failure_notes with specific metrics and reasons

rebuild query_pack
log "result-to-claim: exp_id updated, verdict=..."
```

### Hook 4: Claim birth — from `/proof-checker` (the ONLY birth point)

Wiki **claim nodes are born here.** `/proof-checker` Phase 5.5 calls `add_claim`
for each top-level theorem/headline after writing `PROOF_AUDIT.json`, stamping an
honest PROOF-axis `status` and a `provenance` pointer to the audit trace. No other
skill creates a claim node: `/result-to-claim` (Hook 3) only adds empirical
`supports`/`invalidates` *edges* to an already-born claim and never edits its `status`.

```bash
# (run by /proof-checker; shown here for the wiki's record)
python3 "$WIKI_SCRIPT" add_claim research-wiki/ --slug thm-main-ub \
  --name "Main upper bound" --status verified \
  --provenance ".aris/traces/proof-checker/<run>/" --statement "..." --update-on-exist
```

Claim `status` ∈ {`drafted`, `unproven`, `sound-modulo-imports`, `verified`,
`refuted`, `retracted`} — the **proof axis only**. Empirical support is a separate
axis, carried entirely by edges (Hook 3), never written into `status`. Older
local claim pages may still carry the pre-proof-axis `reported` / `supported` /
`invalidated` / `partial` statuses; `stats` still counts them and `lint` still
flags a stale `reported` claim, but new writes go through `add_claim`.

## Re-ideation Trigger

After significant wiki updates, suggest re-running `/idea-creator`:

- ≥5 new papers ingested since last ideation
- ≥3 new failed/partial ideas since last ideation
- New contradiction discovered in the graph
- New gap identified that no existing idea addresses

The system suggests but does not auto-trigger. User decides.

## Key Rules

- **One source of truth for relationships**: `graph/edges.jsonl`. Page `Connections` sections are auto-generated views.
- **Obsidian owns full paper notes**: wiki paper pages are compact ARIS projections plus local project notes.
- **Wiki does not manage concepts**: do not create `research-wiki/concepts/` or parse Obsidian concept notes.
- **Canonical node IDs everywhere**: `paper:<slug>`, `idea:<id>`, `exp:<id>`, `claim:<id>`, `gap:<id>`. Never use raw titles or inconsistent shorthands.
- **Failed ideas are the most valuable memory.** Never prune them from query_pack.
- **query_pack.md is hard-budgeted** at 8000 chars. Deterministic generation, not open-ended summarization.
- **Append to log.md for every mutation.** The log is the audit trail.
- **Reviewer independence applies.** When the wiki is read by cross-model review skills, pass file paths only — do not summarize wiki content for the reviewer.
- **The wiki is UTF-8.** All wiki files are read and written as UTF-8 so a `research-wiki/` stays portable across platforms and collaborators. A wiki created by an older ARIS on a non-UTF-8 locale (e.g. cp936 on Chinese Windows) must be converted to UTF-8 once — back it up first; the helper reports the offending file by name instead of guessing.

## Acknowledgements

Inspired by [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — "compile knowledge once, keep it current, don't re-derive on every query."
