---
name: experiment-bridge
description: "Workflow 1.5 for Computer Architecture research: turn EXPERIMENT_PLAN.md and idea-stage evaluation handoff fields into an EVALUATION_CONTRACT.md, backend manifest, baseline reproduction path, sanity runs, and initial results."
argument-hint: "[experiment-plan-path-or-topic]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill, mcp__codex__codex, mcp__codex__codex-reply
---

# Workflow 1.5: Experiment Bridge

Bridge a claim-driven architecture experiment plan into executable simulator, analytical, or prototype experiments. This workflow chooses the evaluation backend from the selected idea's `core_baseline` plus the platform/workload IDs in `canon_mapping`; it does not use a global fixed simulator default.

Workflow 1 handoff fields and the pre-bridge exit gate are defined in
`../shared-references/idea-handoff-schema.md`.

## Inputs

Prefer:

1. `refine-logs/EXPERIMENT_PLAN.md`
2. `refine-logs/EXPERIMENT_TRACKER.md`
3. `refine-logs/FINAL_PROPOSAL.md`
4. `idea-stage/IDEA_REPORT.md`
5. `idea-stage/docs/research_contract.md`

If `idea-stage/docs/research_contract.md` does not exist yet (idea selected outside
`/idea-discovery`, or an older run), create it now per
`../shared-references/research-contract-maintenance.md` from the selected idea and the
plan's claims. `/result-to-claim` and `/ablation-planner` read it as the claims source,
and session recovery starts from it.

Extract the canonical idea handoff fields from
`../shared-references/idea-handoff-schema.md`, plus:

- claims and success criteria
- claim boundary and unsupported claims that must not be implied by results
- run order and milestones
- baselines and ablations
- required outputs and metrics
- resource needs: CPU, memory, walltime, license, board/testbed
- lab inventory and env-spec: resolve `lab-resources.yaml` and `.aris/compute/env-spec.yaml` per `../shared-references/hw-env-contract.md` §0; create a missing env-spec from `templates/HW_ENV_SPEC_TEMPLATE.yaml`

## Default Execution Path

1. Parse `Evaluation Inputs` from `EXPERIMENT_PLAN.md` and the selected idea's handoff plan.
2. Evaluate the Workflow 1 → 1.5 handoff gate.
3. Write `refine-logs/EVALUATION_CONTRACT.md` before implementation.
4. Map `handoff_to_workflow_1_5` to `idea_execution_readiness`.
5. Select an evaluation backend from `core_baseline` plus the platform/workload IDs in `canon_mapping`.
6. Apply the baseline reproduction Go/No-Go rule.
7. Validate the environment first (env-spec tiers 1 and 2 per `../shared-references/hw-env-contract.md` §5, ledger block appended), then run baseline smoke when required.
8. Generate or reuse scripts/configs for the selected backend.
9. Run the smallest sanity/smoke stage for the idea variant. A failing sanity or baseline smoke run goes through **Sanity Failures** below.
10. Review code/configs before launching expensive runs.
11. Use `/run-experiment` for one-off runs or `/experiment-queue` for grids.
12. Collect result JSON/logs into `refine-logs/EXPERIMENT_LOG.md`.

## Evaluation Contract

Write this file before changing experiment code:

```markdown
# Evaluation Contract

- **core_baseline**:
- **baseline_artifact_readiness**:
  - score: 2 | 1 | 0
  - status: official_artifact | open_source_system | config_reproducible | paper_only | proprietary_or_unavailable | unknown
  - verification_status: verified | unverified | verify_pending | error
  - evidence:
  - adapter_notes:
- **baseline_source**:
- **baseline_evaluation_platform**:
- **baseline_workload**:
- **baseline_metrics_used**:
- **selected_evaluation_backend**:
- **workload**:
- **metrics**:
- **negative_evidence_response**: n/a | evades: NE-* (...) | addresses: NE-* (...) | conflicts: NE-* (...)
- **target_validation_style**: analytical_model | simulator_evaluation | prototype_measurement
- **evaluation_target_clarity**: clear | partial | missing
- **evaluation_feasibility_score**: 1 | 2 | 3 | 4 | 5 -- include environment/access, adapter, and runtime rationale
- **evaluation_feasibility_breakdown**:
  - platform_workload_access:
  - evaluation_adapter_cost:
  - first_signal_runtime:
- **refine_overall_score**: 0-10
- **refine_verdict**: READY | REVISE | RETHINK
- **drift_status**: preserved | corrected | drifted
- **handoff_refresh_status**: passed | failed | not_run
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

- `core_baseline` must be an idea-local baseline record with baseline ID, paper/system, verification status, addressed `B*`/`S*`, platform/workload mapping, metrics, artifact status, and reproducibility.
- `baseline_artifact_readiness.score: 0` blocks `handoff_gate_status: pass` and prevents immediate execution.
- `refine_verdict` must be `READY`, `refine_overall_score` must be at least
  `9`, `drift_status` must be `preserved` or `corrected`, and
  `handoff_refresh_status` must be `passed` before immediate execution.
- `canon_mapping.platform` must cite `EC-P*`; `canon_mapping.workload` must cite `EC-W*`.
- `metrics` must name the decisive metric and why it decides the idea.
- `negative_evidence_response` must be present. If it cites `conflicts: NE-*`,
  set `handoff_gate_status: blocked` until the conflict is reviewed and either
  scoped away or resolved in `/research-lit` / `/idea-creator`.
- `target_validation_style` must be `analytical_model`, `simulator_evaluation`, or `prototype_measurement`.
- `evaluation_target_clarity` must be `clear` or an explicitly acceptable `partial`; `missing` sets `handoff_gate_status: blocked`.
- `evaluation_feasibility_score` must be present and must be an integer from `1` to `5`. Scores `1`-`3` are allowed only for deferred, clarification, or platform-bringup paths; immediate ready handoffs require `4` or `5`.
- `evaluation_feasibility_breakdown` must include `platform_workload_access`,
  `evaluation_adapter_cost`, and `first_signal_runtime`; the baseline dimension
  lives in `baseline_artifact_readiness`.

Handoff/readiness mapping:

- `handoff_to_workflow_1_5: ready` plus `evaluation_feasibility_score: 5` maps to `idea_execution_readiness: ready`.
- `handoff_to_workflow_1_5: ready` plus `evaluation_feasibility_score: 4` maps to `idea_execution_readiness: adapter_needed`.
- `handoff_to_workflow_1_5: ready` plus `evaluation_feasibility_score <= 3` is an invalid handoff; stop and return to Workflow 1 clarification.
- `handoff_to_workflow_1_5: needs_canon_clarification` stops execution and returns to `/research-lit` or to explicit Evaluation Canon / baseline clarification.
- `handoff_to_workflow_1_5: designed_not_run` or `evaluation_feasibility_score: 2` or `3` maps to `idea_execution_readiness: platform_bringup` unless the artifact/workload path is unavailable.
- `handoff_to_workflow_1_5: designed_not_run` plus an unavailable environment, missing artifact, or proprietary artifact maps to `idea_execution_readiness: blocked`.
- `evaluation_feasibility_score: 1` stops execution until artifact, platform, workload, or comparison-target status is clarified.

Baseline reproduction Go/No-Go:

- `official_artifact` or `open_source_system`: set `baseline_smoke_required: true`; baseline smoke must pass before immediate idea execution. If smoke fails, set `baseline_go_no_go: no_go`.
- `config_reproducible`: reproduce the core configuration before idea execution; adapters are allowed, but configuration differences must be recorded in `handoff_gate_notes` or the manifest.
- `paper_only`: allow `baseline_reproduction_mode: reimplement_minimal`, but set `baseline_evidence_strength: weak` and do not claim the baseline is fully reproduced.
- `proprietary_or_unavailable`: set `baseline_go_no_go: deferred` and do not enter immediate execution.
- `unknown`: clarify artifact/source status before execution; do not select a backend as execution-ready.

Backend selection rules:

- Prefer the core baseline's original platform and workload when they are available or can be configured with small adapter work.
- If the original baseline platform is unavailable, select the most comparable open-source platform/workload under the same EC-P*/EC-W* mapping.
- If no comparable backend exists, mark `idea_execution_readiness: blocked` or `platform_bringup`, and do not pretend the idea is runnable.
- Select `metrics` for the idea. They may reuse `baseline_metrics_used`, but must include the decisive idea-specific metric when the mechanism needs one.
- `analytical_model`, `simulator_evaluation`, and `prototype_measurement` are target validation styles, not fixed backend names.

## Code/Config Review

Before expensive runs, review:

- Does the implementation match the claim?
- Are required outputs and metrics produced?
- Does the selected backend actually correspond to `core_baseline` and the platform/workload IDs in `canon_mapping`?
- Is the baseline reproduction mode honest about artifact availability?
- Are idea-specific metrics implemented, not only inherited baseline metrics?
- Are simulator versions, commands, and config files recorded?

Unless the run passes `— code_review: false`, send this review to the cross-model
reviewer as well. Give it paths, not a summary of the code
(`../shared-references/reviewer-independence.md`), and trace the call per
`../shared-references/review-tracing.md`:

```
mcp__codex__codex:
  model: gpt-6-astra
  config: {"model_reasoning_effort": "xhigh"}
  sandbox: read-only
  prompt: |
    Review the experiment implementation for correctness before expensive runs.
    Read: refine-logs/EVALUATION_CONTRACT.md, refine-logs/EXPERIMENT_PLAN.md,
    refine-logs/EXPERIMENT_MANIFEST.yaml, and [paths of the scripts and configs].

    Check:
    1. Does the implementation match the claim?
    2. Are required outputs and metrics produced?
    3. Does the selected backend actually correspond to `core_baseline` and the
       platform/workload IDs in `canon_mapping`?
    4. Is the baseline reproduction mode honest about artifact availability?
    5. Are idea-specific metrics implemented, not only inherited baseline metrics?
    6. Are simulator versions, commands, and config files recorded?

    For each issue found, specify: CRITICAL / MAJOR / MINOR and the exact fix.

    === SCOPE LIMITS (these bound what you PROPOSE, never what you look for) ===
    Report anything that is actually wrong here — including a rare-looking case, if
    this repo actually produces it. Then keep the fix in scope:
    1. This is a RESEARCH-WORKFLOW tool, not a security paper. Verification is
       welcome; over-defense is not. Assume a cooperating operator on their own
       machine — a malicious local user is NOT in the threat model.
    2. Do NOT propose SHA / hash / content-fingerprint / digest-binding schemes.
       Reporting a real defect in hashing code that already exists is fine.
    3. NO speculative machinery: do not add feature flags, migration frameworks,
       compat layers, wrappers, pins, or similar mechanisms unless evidence shows
       a current repo defect they fix or an explicit existing invariant they must
       preserve. "Load-bearing", "compatibility", and "not scaffolding" are labels,
       not evidence. Point to the failing path/artifact or invariant, and check the
       proposal's factual premises, such as whether a named package version exists.
    4. NO corner-case obsession: exotic encodings, symlink races, RTL text and
       millisecond races are out of scope unless you can show the case arises here.
    5. Where a rubric or checklist is genuinely needed, do not over-mechanize
       judgement. A clear sentence a human reads beats a scored table nobody
       maintains.
    Exception: code that runs remote commands, starts a network service, or installs
    an MCP server runs on the user's machine with their credentials — trust-boundary
    findings there are in scope and the default is strict.
    Say plainly when something is correct. Do not manufacture findings.
```

The scope block is verbatim from `../shared-references/review-scope-limits.md`; keep
it in sync with that file. On the result:

- No CRITICAL issues → proceed.
- CRITICAL issues → fix them and re-submit (at most 2 rounds).
- Codex MCP unavailable → apply the checklist above as a self-review, note in
  `refine-logs/EXPERIMENT_LOG.md` that the cross-model review was skipped, and proceed.

## Sanity Failures

A failing sanity or smoke run is debugged before anyone is asked. Budget: up to
**2 patch attempts** on the same failure, then up to **2 clean reimplements** (4 total).

1. **Read the error** — simulator stderr, the per-run log, tool reports, and the
   env-spec ledger. Place the failure with the diagnosis table in
   `../shared-references/hw-env-contract.md` §5 before patching: tool-version drift,
   a held device lock, or a missing license is an environment problem, not a code bug.
   (The same read-the-primary-artifact discipline applies to a surprising reviewer
   verdict: see `../shared-references/review-tracing.md` § *Debugging With Traces*.)
2. **Patch and re-run** — at most two targeted patches on the same failure.
3. **Both patches failed on the same failure? → Discard and reimplement cleanly**
   (up to 2 reimplements). Rewriting the failing script or config from
   `EXPERIMENT_PLAN.md`, `EVALUATION_CONTRACT.md`, and the research contract is a peer
   move to another patch, not a last resort. Delete ONLY the attempt's own
   code/scaffolding (scripts and configs this workflow generated). Never deletable:
   the plan, `EVALUATION_CONTRACT.md`, `EXPERIMENT_TRACKER.md`, the env-spec and its
   `.aris/compute/<host-id>.md` ledger, user-authored project source (simulator
   models, RTL, baseline artifacts), collected data, and results (see
   `../shared-references/external-cadence.md` § *Let a broken attempt restart, not
   just patch*).
4. **Budget exhausted, or two reimplements failed the SAME way?** → stop and report
   every attempted fix with its error log. Two clean reimplements failing identically
   usually means the plan, the baseline artifact, or the environment is wrong — say so
   explicitly, because that (not the broken build itself) is what needs the human. Do
   not launch the full runs on broken code.

For baseline smoke, patch or rebuild only the adapter, config, or wrapper this workflow
wrote — never the baseline artifact itself. A baseline smoke that still fails after this
budget records `baseline_go_no_go: no_go`.

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
