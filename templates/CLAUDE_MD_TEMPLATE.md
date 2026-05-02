# Project: {project-name}

## Pipeline Status

```yaml
stage: idle          # idle | idea-discovery | implementation | training | review | paper
idea: ""             # Current idea title (one line)
contract: idea-stage/docs/research_contract.md
current_branch: ""   # Git branch for this idea
baseline: ""         # Baseline numbers for comparison
training_status: idle  # idle | running | complete | failed
language: en         # en | zh — controls skill output language (see shared-references/output-language.md)
active_tasks: []
next: ""             # Concrete next step
last_updated: ""     # YYYY-MM-DD HH:mm — auto-updated by skills on every output write
```

## State Persistence Rules

Pipeline Status update triggers:
- Stage transitions, idea selection, baseline confirmed, training start/stop
- User says "save" / "record" / "new session" / "wrap up"
- Before any long pause or handoff

Research Contract update triggers:
- Idea selected or changed; if the idea fails, select the next candidate from `idea-stage/IDEA_CANDIDATES.md` and overwrite the contract
- `refine-logs/FINAL_PROPOSAL.md` or `refine-logs/EXPERIMENT_PLAN.md` generated/updated
- Baseline reproduced, major result obtained, Mx Go/No-Go completed, or `/result-to-claim` resolves claim support

On new session or post-compaction recovery:
1. Read ## Pipeline Status
2. Read idea-stage/docs/research_contract.md (the active idea's focused context)
3. Read project notes if any (e.g., experiment logs, decision rationale)
4. If active_tasks is non-empty → check remote status, rebuild monitoring
5. Resume work without asking the user

## Project Constraints

- {constraint 1}
- {constraint 2}

## Non-Goals

- {non-goal 1}

## Compute Budget

- {budget details, e.g., "8x A100 for 24h via vast.ai"}
