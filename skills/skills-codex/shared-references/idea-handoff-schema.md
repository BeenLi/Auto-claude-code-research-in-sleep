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

## Evaluation Canon

In this workflow, `Evaluation Canon` means only the literature-derived platform and workload reference set. It is made of `EC-P*` platform rows and `EC-W*` workload rows from the Landscape Pack.

`canon_mapping` is only `platform=[EC-P*]; workload=[EC-W*]`. Baselines, metrics, validation style, feasibility, and clarity are not canon; they are idea-level handoff decisions derived after the platform/workload provenance is known.

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
| `baseline_reproducibility` | `official_artifact` \| `open_source_system` \| `config_reproducible` \| `paper_only` \| `proprietary_or_unavailable` \| `unknown` | Feeds `baseline_artifact_readiness.score` and `baseline_artifact_readiness.status`. |

## Idea-Level Fields

The handoff keeps `baseline_artifact_readiness` and `evaluation_feasibility_score` as the merged gate fields.
"Baseline" (code availability) is strictly separate from "Platform/Workload Access": a baseline can be reproducible while the target hardware, trace, or workload remains hard to access.

`baseline_artifact_readiness.score` carries the baseline gate. It replaces the
legacy standalone baseline-code score so the readiness score, artifact status,
verification status, evidence, and adapter notes stay in one object.
`evaluation_feasibility_score` carries the environment, adapter, and runtime readiness gate.
`evaluation_feasibility_breakdown` records `platform_workload_access`, `evaluation_adapter_cost`, and `first_signal_runtime` while referencing `baseline_artifact_readiness` for the baseline dimension.

Canonical compact form for reports:

```yaml
baseline_artifact_readiness:
  score: 0 | 1 | 2
  status: official_artifact | open_source_system | config_reproducible | paper_only | proprietary_or_unavailable | unknown
  verification_status: verified | unverified | verify_pending | error
  evidence: "[paper/system/artifact URL or verification note]"
  adapter_notes: "[minor config change / reimplementation needed / blocked]"
evaluation_feasibility_breakdown:
  platform_workload_access: ready | near_ready | nontrivial | weak | blocked
  baseline_artifact_readiness: "[reference the baseline_artifact_readiness object]"
  evaluation_adapter_cost: small | moderate | major | new_platform | blocked
  first_signal_runtime: minutes | hours | 1-2_days | multi_day | weeks | blocked
```

| field | domain | semantics |
|---|---|---|
| `core_baseline` | idea-local baseline record | Required. Must include a baseline ID, paper/system, verification status, addressed `B*`/`S*`, canon mapping, metrics, artifact status, and reproducibility. |
| `baseline_artifact_readiness` | structured object or compact `score=<0\|1\|2>; status=<...>; verification=<...>` | Hard baseline gate. `2` = verified and official/open-source/config reproducible. `1` = verified but paper-only or unknown reproducibility. `0` = proprietary/unavailable or unverified-only. `baseline_artifact_readiness.score: 0` cannot be `handoff_to_workflow_1_5: ready`. |
| `baseline_verification_delta` | `verified_by_research_lit` \| `new_baseline_lookup` \| `verification_unresolved` | Records whether the baseline was already verified by `/research-lit`, added by `/idea-creator` through a narrow lookup, or left unresolved. |
| `canon_mapping` | `platform=[EC-P*]; workload=[EC-W*]` | Must resolve to the Landscape Pack Evaluation Canon. |
| `metrics` | list | Must include the metric that decides the idea. |
| `target_validation_style` | `analytical_model` \| `simulator_evaluation` \| `prototype_measurement` | Target validation style, not necessarily the final backend name. |
| `evaluation_target_clarity` | `clear` \| `partial` \| `missing` | `missing` blocks Workflow 1.5. |
| `evaluation_feasibility_score` | `1` \| `2` \| `3` \| `4` \| `5` | High-is-better merged feasibility gate. `5` = ready evaluation path. `4` = near-ready path with minor adapter work. `3` = feasible but nontrivial bring-up. `2` = weak feasibility or large platform/prototype cost. `1` = no credible evaluation path. |
| `evaluation_feasibility_breakdown` | structured object or compact text containing `platform_workload_access`, `evaluation_adapter_cost`, and `first_signal_runtime` | Required rationale for `evaluation_feasibility_score`; `baseline_artifact_readiness` is the baseline dimension and must remain consistent with this breakdown. |
| `refine_overall_score` | `0`-`10` | Latest `/research-refine` overall score for the selected refined method. Ready handoff requires `>= 9`. |
| `refine_verdict` | `READY` \| `REVISE` \| `RETHINK` | Latest `/research-refine` verdict. Ready handoff requires `READY`. |
| `drift_status` | `preserved` \| `corrected` \| `drifted` | Whether refinement preserved the selected idea's Problem Anchor and handoff assumptions. Ready handoff requires `preserved` or `corrected`. |
| `handoff_refresh_status` | `passed` \| `failed` \| `not_run` | Whether refinement refreshed `core_baseline`, `canon_mapping`, `baseline_artifact_readiness`, `evaluation_feasibility_score`, `target_validation_style`, and `metrics` after the final method changed. Ready handoff requires `passed`. |
| `handoff_to_workflow_1_5` | `ready` \| `needs_canon_clarification` \| `designed_not_run` | `ready` requires `baseline_artifact_readiness.score` 1 or 2, `evaluation_feasibility_score` 4 or 5, clear baseline, canon mapping, metrics, validation style, `refine_verdict: READY`, `refine_overall_score >= 9`, non-drifted `drift_status`, and `handoff_refresh_status: passed`. Workflow 1.5 owns `blocked` readiness outcomes after evaluating the selected idea. |
| `main_blocker` | `none` \| `missing_artifact` \| `trace_unavailable` \| `backend_adapter` \| `platform_bringup` \| `unclear_canon_mapping` \| `unclear_comparison_target` \| `no_credible_evaluation_path` \| `unclear_negative_evidence_response` \| `other` | Required when the handoff is not ready. |
| `negative_evidence_response` | `n/a` \| `evades: NE-* (...)` \| `addresses: NE-* (...)` \| `conflicts: NE-* (...)` | Required audit trail for the Section 2.5 Negative Evidence hard gate. Every surviving idea must explain how it handles any relevant `NE-*` affected assumption, or use `n/a` when no `NE-*` applies. |

ready handoff requires `evaluation_feasibility_score` 4 or 5. Scores 1-3
belong in backup, deferred, clarification, or designed-not-run entries.

## Workflow 1 Exit Gate

Before `/experiment-bridge`, run `tools/workflow1_exit_gate.sh` or apply the
same checks manually:

- `idea-stage/IDEA_REPORT.md` exists and contains the selected idea handoff row.
- `refine-logs/FINAL_PROPOSAL.md` exists for the selected idea.
- `refine-logs/EXPERIMENT_PLAN.md` exists for the selected idea.
- `baseline_artifact_readiness.score` is 1 or 2.
- `baseline_artifact_readiness.score: 0` is not marked `handoff_to_workflow_1_5: ready`.
- `evaluation_feasibility_score` is 4 or 5.
- `evaluation_feasibility_breakdown` records `platform_workload_access`,
  `evaluation_adapter_cost`, and `first_signal_runtime`.
- `refine_verdict` is `READY`.
- `refine_overall_score` is at least 9.
- `drift_status` is `preserved` or `corrected`.
- `handoff_refresh_status` is `passed`.
- `canon_mapping` references both `EC-P*` and `EC-W*`.
- `core_baseline`, `metrics`, `target_validation_style`,
  `evaluation_target_clarity`, `evaluation_feasibility_score`,
  `evaluation_feasibility_breakdown`, `baseline_artifact_readiness`,
  `baseline_verification_delta`, `negative_evidence_response`,
  `refine_overall_score`, `refine_verdict`, `drift_status`, and
  `handoff_refresh_status` are present.
- `negative_evidence_response` is present so Workflow 1.5 can audit the
  Section 2.5 Negative Evidence gate.

The gate does not run experiments. It only decides whether Workflow 1 produced
enough structured evidence for Workflow 1.5 to start.
