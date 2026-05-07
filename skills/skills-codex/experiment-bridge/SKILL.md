---
name: experiment-bridge
description: "Workflow 1.5 for Computer Architecture research: turn EXPERIMENT_PLAN.md and idea-stage evaluation handoff fields into an EVALUATION_CONTRACT.md, backend manifest, baseline reproduction path, sanity runs, and initial results."
argument-hint: [experiment-plan-path-or-topic]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, Skill, spawn_agent, send_input
---

# Workflow 1.5: Experiment Bridge

Bridge a claim-driven architecture experiment plan into executable simulator, analytical, or prototype experiments. This workflow chooses the evaluation backend from the selected idea's `core_baseline` and `canon_mapping`; it does not use a global fixed simulator default.

## Inputs

Prefer:

1. `refine-logs/EXPERIMENT_PLAN.md`
2. `refine-logs/EXPERIMENT_TRACKER.md`
3. `refine-logs/FINAL_PROPOSAL.md`
4. `idea-stage/IDEA_REPORT.md`
5. `idea-stage/docs/research_contract.md`

Extract:

- claims and success criteria
- claim boundary and unsupported claims that must not be implied by results
- `core_baseline`
- `canon_mapping`
- `metrics`
- `target_validation_style`
- `evaluation_target_clarity`
- `evaluation_target_feasibility`
- `baseline_reproducibility`
- `evaluation_environment_access`
- `idea_adapter_cost`
- `pilot_runtime_cost`
- `handoff_to_workflow_1_5`
- run order and milestones
- baselines and ablations
- required outputs and metrics
- resource needs: CPU, memory, walltime, license, board/testbed

## Default Execution Path

1. Parse `Evaluation Inputs` from `EXPERIMENT_PLAN.md` and the selected idea's handoff plan.
2. Evaluate the Workflow 1 → 1.5 handoff gate.
3. Write `refine-logs/EVALUATION_CONTRACT.md` before implementation.
4. Map `handoff_to_workflow_1_5` to `idea_execution_readiness`.
5. Select an evaluation backend from `core_baseline` and `canon_mapping`.
6. Apply the baseline reproduction Go/No-Go rule.
7. Run baseline smoke first when required.
8. Generate or reuse scripts/configs for the selected backend.
9. Run the smallest sanity/smoke stage for the idea variant.
10. Review code/configs before launching expensive runs.
11. Use `/run-experiment` for one-off runs or `/experiment-queue` for grids.
12. Collect result JSON/logs into `refine-logs/EXPERIMENT_LOG.md`.

## Evaluation Contract

Write this file before changing experiment code:

```markdown
# Evaluation Contract

- **core_baseline**:
- **baseline_source**:
- **baseline_evaluation_platform**:
- **baseline_workload**:
- **baseline_metrics_used**:
- **selected_evaluation_backend**:
- **workload**:
- **metrics**:
- **target_validation_style**: analytical_model | simulator_evaluation | prototype_measurement
- **evaluation_target_clarity**: clear | partial | missing
- **evaluation_target_feasibility**: high | medium | low | unknown
- **baseline_reproducibility**: official_artifact | open_source_system | config_reproducible | paper_only | proprietary_or_unavailable | unknown
- **evaluation_environment_access**: ready | small_adapter_needed | major_bringup_needed | unavailable | unknown
- **idea_adapter_cost**: parameter_or_config_only | small_local_patch | moderate_adapter | major_system_change | new_platform_or_prototype
- **pilot_runtime_cost**: minutes_to_hours | one_to_two_days | multi_day_to_two_weeks | long_running_or_large_scale | unknown
- **handoff_to_workflow_1_5**: ready | needs_canon_clarification | designed_not_run
- **handoff_gate_status**: pass | needs_canon_clarification | blocked
- **handoff_gate_notes**:
- **baseline_reproduction_mode**: run_official | configure_existing | reimplement_minimal | compare_to_paper_number | not_currently_reproducible
- **baseline_go_no_go**: go | no_go | deferred
- **baseline_smoke_required**: true | false
- **baseline_evidence_strength**: strong | moderate | weak | unavailable
- **idea_execution_readiness**: ready | adapter_needed | platform_bringup | blocked | unknown
- **calibration_note**: [optional; do not require calibration unless needed for this idea]
```

Workflow 1 → 1.5 handoff gate:

- `core_baseline` must be a `CB*` candidate, or `new baseline with rationale`.
- `canon_mapping.platform` must cite `EC-P*`; `canon_mapping.workload` must cite `EC-W*`.
- `metrics` must name the decisive metric and why it decides the idea.
- `target_validation_style` must be `analytical_model`, `simulator_evaluation`, or `prototype_measurement`.
- `evaluation_target_clarity` must be `clear` or an explicitly acceptable `partial`; `missing` sets `handoff_gate_status: blocked`.
- `evaluation_target_feasibility` and its four subfields must be present; `unknown` sets `handoff_gate_status: needs_canon_clarification`, and `low` is allowed only for deferred or platform-bringup paths.
- `evaluation_environment_access: unknown` sets `handoff_gate_status: needs_canon_clarification`.

Handoff/readiness mapping:

- `handoff_to_workflow_1_5: ready` plus `evaluation_target_feasibility: high|medium` and `evaluation_environment_access: ready` maps to `idea_execution_readiness: ready`.
- `handoff_to_workflow_1_5: ready` plus `evaluation_target_feasibility: high|medium` and `evaluation_environment_access: small_adapter_needed` maps to `idea_execution_readiness: adapter_needed`.
- `handoff_to_workflow_1_5: needs_canon_clarification` stops execution and returns to `/research-lit` or to an explicit Evaluation Canon / Core Baseline Candidates clarification step.
- `handoff_to_workflow_1_5: designed_not_run`, `evaluation_target_feasibility: low`, or `evaluation_environment_access: major_bringup_needed` maps to `idea_execution_readiness: platform_bringup` unless the artifact/workload path is unavailable.
- `handoff_to_workflow_1_5: designed_not_run` plus an unavailable environment, missing artifact, or proprietary artifact maps to `idea_execution_readiness: blocked`.
- `evaluation_target_feasibility: low` should not enter immediate execution unless the user explicitly chooses a long-horizon platform bring-up.
- `evaluation_target_feasibility: unknown` stops execution until artifact, platform, workload, or comparison-target status is clarified.

Baseline reproduction Go/No-Go:

- `official_artifact` or `open_source_system`: set `baseline_smoke_required: true`; baseline smoke must pass before immediate idea execution. If smoke fails, set `baseline_go_no_go: no_go`.
- `config_reproducible`: reproduce the core configuration before idea execution; adapters are allowed, but configuration differences must be recorded in `handoff_gate_notes` or the manifest.
- `paper_only`: allow `baseline_reproduction_mode: reimplement_minimal`, but set `baseline_evidence_strength: weak` and do not claim the baseline is fully reproduced.
- `proprietary_or_unavailable`: set `baseline_go_no_go: deferred` and do not enter immediate execution.
- `unknown`: clarify artifact/source status before execution; do not select a backend as execution-ready.

Backend selection rules:

- Prefer the core baseline's original platform and workload when they are available or can be configured with small adapter work.
- If the original baseline platform is unavailable, select the most comparable open-source platform/workload under the same `Evaluation Canon` mapping.
- If no comparable backend exists, mark `idea_execution_readiness: blocked` or `platform_bringup`, and do not pretend the idea is runnable.
- Select `metrics` for the idea. They may reuse `baseline_metrics_used`, but must include the decisive idea-specific metric when the mechanism needs one.
- `analytical_model`, `simulator_evaluation`, and `prototype_measurement` are target validation styles, not fixed backend names.

## Code/Config Review

Before expensive runs, review:

- Does the implementation match the claim?
- Are required outputs and metrics produced?
- Does the selected backend actually correspond to `core_baseline` and `canon_mapping`?
- Is the baseline reproduction mode honest about artifact availability?
- Are idea-specific metrics implemented, not only inherited baseline metrics?
- Are simulator versions, commands, and config files recorded?

## Output

Write or update:

- `refine-logs/EXPERIMENT_MANIFEST.yaml`
- `refine-logs/EVALUATION_CONTRACT.md`
- `refine-logs/EXPERIMENT_TRACKER.md`
- `refine-logs/EXPERIMENT_LOG.md`

Initial results must separate:

- baseline reproduction status,
- idea smoke status,
- completed runs,
- failed/stuck runs,
- missing artifacts,
- metric coverage,
- claim impact,
- next runs to launch.

## Research Contract Postcondition

At this workflow exit, apply `shared-references/research-contract-maintenance.md` to refresh `idea-stage/docs/research_contract.md` if evidence changed.
This is only a workflow-exit gate; execution details stay in `refine-logs/EXPERIMENT_PLAN.md` and results stay in `refine-logs/EXPERIMENT_LOG.md`.
