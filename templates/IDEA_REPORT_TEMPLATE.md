# Research Idea Report

**Direction**: [research direction]
**Generated**: [UTC ISO-8601 timestamp]
**Pipeline**: research-lit -> idea-creator -> novelty-check -> research-review -> research-refine-pipeline

## Executive Summary

[Best idea, key evidence, and next step.]

## Literature Landscape

[Summary from `idea-stage/LITERATURE_REVIEW.md`.]

## Recommended Ideas

### Idea 1: [title] -- RECOMMENDED

- **Idea shape**: [compact summary of gap, mechanism/study, and why the answer matters]
- **negative_evidence_response**: [n/a | evades: NE-* (...) | addresses: NE-* (...) | conflicts: NE-* (...)]
- **Status**: selected
- **overall_merit_score**: [1-5] -- [rationale]
- **evaluation_feasibility_score**: [1-5]
- **Feasibility Breakdown**:
  - *platform_workload_access*: [ready | near_ready | nontrivial | weak | blocked -- evidence]
  - *baseline_artifact_readiness*: [score/status/verification/evidence/adapter notes]
  - *evaluation_adapter_cost*: [small | moderate | major | new_platform | blocked -- evidence]
  - *first_signal_runtime*: [minutes | hours | 1-2_days | multi_day | weeks | blocked -- decisive metric]
- **Evaluation handoff**: follow `skills/shared-references/idea-handoff-schema.md`
- **Novelty check**: [confirmed / needs work / killed]
- **Reviewer score**: [score]
- **Next step**: `/research-refine-pipeline`

### Idea 2: [title] -- BACKUP

- **Idea shape**:
- **negative_evidence_response**:
- **Status**: backup
- **overall_merit_score**:
- **evaluation_feasibility_score**:
- **Feasibility Breakdown**:
  - *platform_workload_access*:
  - *baseline_artifact_readiness*:
  - *evaluation_adapter_cost*:
  - *first_signal_runtime*:
- **Evaluation handoff**: follow `skills/shared-references/idea-handoff-schema.md`
- **Main blocker**:

## Deferred Ideas

| Idea | Reason deferred | Required clarification or platform path |
|------|-----------------|-----------------------------------------|
| [idea] | [main_blocker] | [what must become available] |

## Eliminated Ideas

| Idea | Category | Reason | Revisit condition |
|------|----------|--------|-------------------|
| [idea] | [already_done / low_overall_merit / no_credible_evaluation_path] | [why] | [condition] |

## Evaluation Handoff Summary

Use the canonical fields and domains in
`skills/shared-references/idea-handoff-schema.md`.

| Idea | overall_merit_score | evaluation_feasibility_score | evaluation_feasibility_breakdown | baseline_artifact_readiness | core_baseline | canon_mapping | metrics | target_validation_style | evaluation_target_clarity | baseline_verification_delta | negative_evidence_response | refine_overall_score | refine_verdict | drift_status | handoff_refresh_status | handoff_to_workflow_1_5 | main_blocker |
|------|---------------------|-------------------------------|--------------------------------|-----------------------------|---------------|---------------|---------|-------------------------|---------------------------|-----------------------------|----------------------------|----------------------|----------------|--------------|------------------------|-------------------------|--------------|
| Idea 1 | 5 | 5 -- ready platform, small/no adapter, minutes-to-hours first signal | platform_workload_access=ready; evaluation_adapter_cost=small; first_signal_runtime=hours | score=2; status=official_artifact; verification=verified; evidence=research_lit; adapter=minor | IB1: verified system | platform=[EC-P1]; workload=[EC-W1] | [metric] | simulator_evaluation | clear | verified_by_research_lit | n/a | 9 | READY | preserved | passed | ready | none |

## Refined Proposal

- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Research contract: `idea-stage/docs/research_contract.md`

## Next Steps

- [ ] Run `tools/workflow1_exit_gate.sh`
- [ ] Enter Workflow 1.5 with `/experiment-bridge`
