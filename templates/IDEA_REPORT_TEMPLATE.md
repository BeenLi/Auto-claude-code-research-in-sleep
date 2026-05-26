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
- **Overall merit**: [1-4] -- [rationale]
- **Evaluation handoff**: follow `skills/shared-references/idea-handoff-schema.md`
- **Novelty check**: [confirmed / needs work / killed]
- **Reviewer score**: [score]
- **Next step**: `/research-refine-pipeline`

### Idea 2: [title] -- BACKUP

- **Idea shape**:
- **negative_evidence_response**:
- **Status**: backup
- **Overall merit**:
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

| Idea | overall_merit_score | evaluation_target_feasibility | baseline_evaluability_score | core_baseline | canon_mapping | metrics | target_validation_style | evaluation_target_clarity | evaluation_environment_access | idea_adapter_cost | pilot_runtime_cost | negative_evidence_response | handoff_to_workflow_1_5 | main_blocker |
|------|---------------------|-------------------------------|----------------------------|---------------|---------------|---------|-------------------------|---------------------------|-------------------------------|-------------------|--------------------|----------------------------|-------------------------|--------------|
| Idea 1 | 1 | high | 2 | IB1: verified system | platform=[EC-P1]; workload=[EC-W1] | [metric] | simulator_evaluation | clear | ready | small_local_patch | minutes_to_hours | n/a | ready | none |

## Refined Proposal

- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Research contract: `idea-stage/docs/research_contract.md`

## Next Steps

- [ ] Run `tools/workflow1_exit_gate.sh`
- [ ] Enter Workflow 1.5 with `/experiment-bridge`
