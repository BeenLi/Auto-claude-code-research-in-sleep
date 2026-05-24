# Workflow 1 Idea Handoff Schema

This is the canonical Workflow 1 -> 1.5 handoff surface. Workflow 1 prepares
these fields; Workflow 1.5 validates them before executing anything.

## Outputs Covered

- `idea-stage/IDEA_REPORT.md`
- Optional `idea-stage/IDEA_CANDIDATES.md`
- `refine-logs/FINAL_PROPOSAL.md`
- `refine-logs/EXPERIMENT_PLAN.md`
- `idea-stage/docs/research_contract.md`

Only the selected top idea enters `/research-refine-pipeline`. Other viable
ideas remain in `IDEA_REPORT.md` as `backup` or `deferred` options.

## Idea-Local Baseline Record

Each surviving idea owns one `core_baseline` idea-local baseline record. It is
not a global pool.

| field | domain | notes |
|---|---|---|
| `baseline_id` | stable short string | Scoped to the idea. |
| `paper_or_system` | string | Title or system name; should match a verified paper, competitor, or explicit quick lookup. |
| `verification_status` | `verified` \| `unverified` \| `verify_pending` \| `error` | Comes from the candidate-paper verification flow. |
| `addresses` | list of `B*` and/or `S*` IDs | Must resolve against the loaded Landscape Pack. |
| `canon_mapping` | `platform=[EC-P*]; workload=[EC-W*]` | The platform ID must reference `EC-P*`; the workload ID must reference `EC-W*`. |
| `metrics` | list | Decisive metric first, secondary metrics only when needed. |
| `artifact_status` | `yes` \| `partial` \| `no` \| `unknown` | Code/data availability. |
| `baseline_reproducibility` | `official_artifact` \| `open_source_system` \| `config_reproducible` \| `paper_only` \| `proprietary_or_unavailable` \| `unknown` | Feeds `baseline_evaluability_score`. |

## Idea-Level Fields

| field | domain | semantics |
|---|---|---|
| `baseline_evaluability_score` | `0` \| `1` \| `2` | Hard gate. `2` = official/open-source/config reproducible. `1` = paper-only or unknown. `0` = proprietary/unavailable or unverified-only. `baseline_evaluability_score: 0` cannot be `handoff_to_workflow_1_5: ready`. |
| `canon_mapping` | `platform=[EC-P*]; workload=[EC-W*]` | Must resolve to the Landscape Pack Evaluation Canon. |
| `metrics` | list | Must include the metric that decides the idea. |
| `target_validation_style` | `analytical_model` \| `simulator_evaluation` \| `prototype_measurement` | Target validation style, not necessarily the final backend name. |
| `evaluation_target_clarity` | `clear` \| `partial` \| `missing` | `missing` blocks Workflow 1.5. |
| `evaluation_target_feasibility` | `high` \| `medium` \| `low` \| `unknown` | Aggregate of the feasibility subfields below. |
| `baseline_reproducibility` | same domain as `core_baseline.baseline_reproducibility` | May be repeated at idea level for table summaries. |
| `evaluation_environment_access` | `ready` \| `small_adapter_needed` \| `major_bringup_needed` \| `unavailable` \| `unknown` | Unknown or unavailable blocks immediate execution. |
| `idea_adapter_cost` | `parameter_or_config_only` \| `small_local_patch` \| `moderate_adapter` \| `major_system_change` \| `new_platform_or_prototype` | Estimated idea-specific modification cost. |
| `pilot_runtime_cost` | `minutes_to_hours` \| `one_to_two_days` \| `multi_day_to_two_weeks` \| `long_running_or_large_scale` \| `unknown` | First-signal runtime estimate. Workflow 1 estimates this but does not run it. |
| `platform_access_path` | string | Repository, artifact, simulator, benchmark, trace, or adapter path. |
| `handoff_to_workflow_1_5` | `ready` \| `needs_canon_clarification` \| `designed_not_run` | `ready` requires `baseline_evaluability_score` 1 or 2 plus clear baseline, canon mapping, metrics, and validation style. |
| `main_blocker` | `none` \| `missing_artifact` \| `trace_unavailable` \| `backend_adapter` \| `platform_bringup` \| `unclear_canon_mapping` \| `unclear_comparison_target` \| `no_credible_evaluation_path` \| `other` | Required when the handoff is not ready. |

## Workflow 1 Exit Gate

Before `/experiment-bridge`, run `tools/workflow1_exit_gate.sh` or apply the
same checks manually:

- `idea-stage/IDEA_REPORT.md` exists and contains the selected idea handoff row.
- `refine-logs/FINAL_PROPOSAL.md` exists for the selected idea.
- `refine-logs/EXPERIMENT_PLAN.md` exists for the selected idea.
- `baseline_evaluability_score: 0` is not marked `handoff_to_workflow_1_5: ready`.
- `canon_mapping` references both `EC-P*` and `EC-W*`.
- `core_baseline`, `metrics`, `target_validation_style`,
  `evaluation_target_clarity`, `evaluation_target_feasibility`,
  `evaluation_environment_access`, `idea_adapter_cost`, and
  `pilot_runtime_cost` are present.

The gate does not run experiments. It only decides whether Workflow 1 produced
enough structured evidence for Workflow 1.5 to start.
