# Research Contract: [Idea Name]

> **A focused working document for the currently selected idea.** Created when an idea is chosen from `IDEA_REPORT.md` or `IDEA_CANDIDATES.md`, updated at research milestones, and read on session recovery — not the full IDEA_REPORT with all 8-12 candidates.
>
> **Why this file exists:** After brainstorming, `IDEA_REPORT.md` contains many candidate ideas. Keeping all of them in context pollutes the LLM's working memory and degrades output quality. This contract extracts *only the active idea* into a standalone claim boundary, so new sessions and post-compaction recovery load focused context instead of the entire idea pool.

## Selected Idea

- **Description**: [One-paragraph summary of the idea]
- **Source**: IDEA_REPORT.md, Idea #N
- **Selection rationale**: [Why this idea over others — pilot results, novelty score, feasibility]

## Core Claims

1. [Main claim — what your method achieves]
2. [Supporting claim — why it works / when it works best]
3. [Optional: scope/limitation claim]

## Method Summary

[2-3 paragraphs: How the method works. Enough detail that a new session can understand the approach without reading the full codebase.]

## Experiment Design Pointer

- **Plan**: `refine-logs/EXPERIMENT_PLAN.md`
- **Baselines**: [What you compare against]
- **Metrics**: [Primary and secondary metrics]
- **Execution note**: The detailed run order and experiment blocks live in the plan; do not copy them here.

## Claim Boundary

[What the current evidence allows you to claim, what it does not yet support, and what evidence would be required to strengthen the claim.]

## Current Evidence Status

> Updated after baselines, major results, Mx Go/No-Go reviews, or `/result-to-claim`. Keep this short; link to logs and reports.

- [Current evidence milestone]
- [Supported / partial / unsupported claim state]
- [Largest remaining evidence gap]

## Key Decisions

- [Decision 1: Why approach X over Y — with reasoning]
- [Decision 2: Why this hyperparameter / architecture choice]
- [Known limitations / risks and how you plan to handle them]

## Immediate Research Gate

[One sentence: the next research gate, and what must not be claimed until that gate passes.]
