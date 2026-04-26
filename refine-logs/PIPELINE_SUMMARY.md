# Pipeline Summary

**Command**: `/research-pipeline "nic lossless compression"` restarted from `/idea-discovery "nic lossless compression"`  
**Generated**: 2026-04-26 10:26 CST  
**Effort**: beast  
**Reviewer difficulty**: nightmare  
**Stage reached**: Workflow 1 complete; ready for implementation bridge  
**Nightmare review gate**: BLOCKED by sandbox/API connectivity; internal adversarial assessment saved in `review-stage/AUTO_REVIEW.md`

## What Changed

- Rebuilt `research-wiki/` from scratch and ingested 12 core papers.
- Refreshed literature across NIC/DPU, RDMA, LLM codec, memory/cache, runtime/serving, storage/checkpoint, and host Rx path.
- Rejected the prior narrow "shared DPU compression QoS" idea as the main path because it requires BlueField hardware and is less aligned with the simulator-first AGENTS.md anchor.
- Selected **Rx Expansion Budgeting for Compressed RDMA** as the new active idea.

## Selected Idea

Compressed RDMA must budget decompressed output bytes, not just compressed wire bytes. The proposed EARB mechanism tracks expansion ratio, Rx output-byte credits, decompression queue pressure, and feedback to RDMA control so receiver-side PCIe/host-memory/Rx-buffer bottlenecks do not become hidden tail-latency failures.

## Key Artifacts

- Literature report: `nic-lossless-compression/research-lit/2026-04-26.md`
- Idea report: `idea-stage/IDEA_REPORT.md`
- Idea candidates: `idea-stage/IDEA_CANDIDATES.md`
- Final proposal: `refine-logs/FINAL_PROPOSAL.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Review gate record: `review-stage/AUTO_REVIEW.md`
- Research wiki query pack: `research-wiki/query_pack.md`

## Blockers / Degradations

- `deepxiv` CLI is not installed, so DeepXiv was recorded as unavailable rather than fabricated.
- Local shell network cannot resolve arXiv/Semantic Scholar API hosts, so arXiv/S2 adapters degraded; browser/web search was used for current metadata.
- Zotero/Obsidian MCP resources are not exposed in this Codex environment.
- `codex exec` nightmare review could not reach `api.openai.com`; fallback Claude review returned a disabled-organization API error.

## Next Step

Start Workflow 1.5 implementation from `refine-logs/EXPERIMENT_PLAN.md`: analytical break-even model, then htsim/standalone flow simulator smoke test, then gem5/htsim window co-simulation.
