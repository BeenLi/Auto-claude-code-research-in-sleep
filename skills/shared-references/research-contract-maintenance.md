# Research Contract Maintenance Protocol

Canonical path: `idea-stage/docs/research_contract.md`.

## Purpose

The research contract is the active idea's thin claim boundary and recovery context. It is not the experiment plan, the experiment log, or a TODO list.

## Template

When creating `idea-stage/docs/research_contract.md` from scratch, use `templates/RESEARCH_CONTRACT_TEMPLATE.md` as the structural template.

For updates, preserve the template section names and update only the sections affected by the current research gate.

## File Roles

- `idea-stage/IDEA_REPORT.md`: raw idea report with the full 8-12 idea pool.
- `idea-stage/IDEA_CANDIDATES.md`: compact 3-5 idea candidate pool for switching ideas.
- `idea-stage/docs/research_contract.md`: selected idea, intended claims, evidence boundary, key decisions, and current research gate.
- `refine-logs/EXPERIMENT_PLAN.md`: experiment execution blueprint. `/experiment-plan` is the semantic owner.
- `refine-logs/EXPERIMENT_LOG.md` and Mx reports: factual result records.

## Research Contract Postcondition

Refresh `idea-stage/docs/research_contract.md` at these gates:

- After an idea is selected from `idea-stage/IDEA_REPORT.md` or `idea-stage/IDEA_CANDIDATES.md`.
- After `refine-logs/FINAL_PROPOSAL.md` or `refine-logs/EXPERIMENT_PLAN.md` is generated or materially updated.
- After a baseline is reproduced.
- After major results or an Mx Go/No-Go review.
- After `/result-to-claim` resolves supported, partial, or unsupported claims.
- If the current idea fails, return to `idea-stage/IDEA_CANDIDATES.md`, select the next candidate, and overwrite the contract with the new active idea rather than accumulating stale context.

## Do Not Include

- Ordinary code TODOs or shell/session state.
- Full experiment blocks from `refine-logs/EXPERIMENT_PLAN.md`.
- Raw logs or complete result tables.
- Unsupported claims phrased as paper-ready evidence.
