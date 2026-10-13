# Workflow 1 Checkpoints

Use these visible summaries when Workflow 1 runs under `/idea-discovery` or
`/research-pipeline`. Keep them short; they are control points, not reports.

## Literature scope

Show after `/research-lit`:

- inferred AI infrastructure layer
- top `B*` bottlenecks and `S*` solution attempts
- available `EC-P*` platforms and `EC-W*` workloads
- top `G*` residual-gap seeds
- any scope correction needed before idea generation

## Idea selection

Show after `/idea-creator`, novelty checks, and review:

- ranked idea title and one-line shape
- `overall_merit_score`
- `evaluation_feasibility_score`
- `evaluation_feasibility_breakdown`
- `core_baseline` short ID
- `baseline_artifact_readiness`
- `canon_mapping`
- `handoff_to_workflow_1_5`
- `main_blocker` for backups, and `park_reason` plus `revisit_condition` for parked ideas
- pool counts: active, parked, eliminated on evidence

Only the selected top idea proceeds to `/research-refine-pipeline`. Ready
backups and parked ideas remain documented in `IDEA_REPORT.md`.

## Refined proposal ready

Show after `/research-refine-pipeline`:

- problem anchor
- method thesis
- dominant contribution
- required experiment blocks
- `refine_overall_score`, `refine_verdict`, `drift_status`, and
  `handoff_refresh_status`
- paths to `refine-logs/FINAL_PROPOSAL.md` and `refine-logs/EXPERIMENT_PLAN.md`
- Workflow 1 exit-gate status

This checkpoint ends Workflow 1. Execution starts in Workflow 1.5.
