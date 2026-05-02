# Output Versioning Protocol

When writing any output file that would overwrite an existing file, use timestamped filename + fixed-name latest copy:

1. Write output to timestamped file: `{FILENAME}_{YYYYMMDD_HHmmssZ}.md` (or `.json`, `.tex` as appropriate)
   - Use UTC for filename timestamps (for example, `date -u +%Y%m%d_%H%M%SZ`).
   - Use UTC ISO-8601 with a trailing `Z` for in-file metadata fields such as `Generated`, `timestamp`, `generated_at`, `started_at`, and `start_time` (for example, `date -u +%Y-%m-%dT%H:%M:%SZ`).
   - Timestamp precision to seconds to reduce collisions. In the rare case of sub-second conflicts, append `_2`, `_3` etc.
   - Place the timestamped file in the same directory as the fixed-name file
2. Copy the same content to the fixed-name file: `{FILENAME}.md` (overwrites the previous latest copy)
3. Downstream skills always read the fixed-name file — they do not need to know about timestamps

## Directory Structure

All ARIS output files are organized by workflow stage:

```
project/
├── CLAUDE.md                              # Dashboard (root — read by all stages)
├── findings.md                            # Cross-stage discovery log (root — append-only)
├── MANIFEST.md                            # Output tracking manifest (root)
│
├── idea-stage/                            # W1: Idea Discovery
│   ├── IDEA_REPORT.md                     # Latest copy
│   ├── IDEA_REPORT_20250615_143022.md     # Timestamped version
│   ├── IDEA_CANDIDATES.md
│   ├── REF_PAPER_SUMMARY.md
│   └── docs/
│       └── research_contract.md
│
├── refine-logs/                           # W1.5: Experiment Planning & Refinement
│   ├── EXPERIMENT_PLAN.md
│   ├── EXPERIMENT_TRACKER.md
│   ├── EXPERIMENT_RESULTS.md
│   ├── FINAL_PROPOSAL.md
│   ├── PIPELINE_SUMMARY.md
│   ├── REFINE_STATE.json
│   ├── REVIEW_SUMMARY.md
│   ├── REFINEMENT_REPORT.md
│   └── round_N_*.md
│
├── review-stage/                          # W2: Auto Review
│   ├── AUTO_REVIEW.md
│   └── REVIEW_STATE.json
│
├── paper/                                 # W3: Paper Writing
│   ├── main.tex
│   └── roundN/
│
└── research-wiki/                         # Persistent knowledge base
```

## What to Timestamp

Files that get overwritten on re-runs:
- `IDEA_REPORT.md`, `IDEA_CANDIDATES.md`, `REF_PAPER_SUMMARY.md`
- `EXPERIMENT_PLAN.md`, `EXPERIMENT_TRACKER.md`, `EXPERIMENT_RESULTS.md`
- `FINAL_PROPOSAL.md`, `PIPELINE_SUMMARY.md`
- `AUTO_REVIEW.md` (when starting a new review loop, not within a loop)
- `paper/main.tex`
- State files: `REFINE_STATE.json`, `REVIEW_STATE.json`

## What NOT to Timestamp

- **Append-only files**: `findings.md`, `research-wiki/log.md` — these accumulate entries, not overwrite
- **Per-round files**: `refine-logs/round_N_*.md` — already versioned by round number
- **Dashboard**: `CLAUDE.md` — single source of truth, always latest
- **MANIFEST.md** — append-only tracking file

Never delete timestamped files. They are the permanent history.

## Path Fallback Rule (Backward Compatibility)

Skills that **read** stage-scoped files must fall back to the old root-level location for projects created before this layout was introduced:

```
# For idea-stage files:
Read from idea-stage/IDEA_REPORT.md
If not found → fall back to ./IDEA_REPORT.md

Read from idea-stage/IDEA_CANDIDATES.md
If not found → fall back to ./IDEA_CANDIDATES.md

# For review-stage files:
Read from review-stage/AUTO_REVIEW.md
If not found → fall back to ./AUTO_REVIEW.md

Read from review-stage/REVIEW_STATE.json
If not found → fall back to ./REVIEW_STATE.json
```

Skills that **write** always use the stage-scoped path (never write to root). This ensures new runs migrate output forward while old projects continue to work.

## Migration for Existing Projects

If you find root-level files (`IDEA_REPORT.md`, `AUTO_REVIEW.md`, etc.) and the stage directories do not yet exist, you may optionally offer to migrate:

```
📁 Found legacy root-level files. Migrate to stage directories?
  mv IDEA_REPORT.md idea-stage/IDEA_REPORT.md
  mv AUTO_REVIEW.md review-stage/AUTO_REVIEW.md
  (etc.)
Only do this if the user confirms — do not auto-migrate silently.
```

## Stale State Detection

Before reading a state file (`REFINE_STATE.json`, `REVIEW_STATE.json`, `DSE_STATE.json`):
1. Check the file's last modified time via `ls -la` or `stat`
2. Default staleness threshold: **24 hours** (individual skills may override — e.g., `auto-review-loop` uses 24h, `research-refine` uses 24h). If a skill defines its own threshold, that takes precedence.
3. If older than the threshold, warn the user:
   "⚠️ State file {filename} is {N} hours/days old. It may be from a previous research direction. Continue with this state, or start fresh?"
4. If the user chooses to start fresh, write a timestamped archive copy and proceed without the old state
