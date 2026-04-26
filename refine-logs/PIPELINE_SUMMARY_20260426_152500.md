# Pipeline Summary

**Command**: `/research-pipeline "nic lossless compression"` restarted from `/idea-discovery "nic lossless compression"`
**Generated**: 2026-04-26 10:26 CST
**Effort**: beast
**Reviewer difficulty**: nightmare
**Stage reached**: Workflow 1 complete; ready for implementation bridge
**Nightmare review gate**: Completed via oracle-pro browser mode on 2026-04-26 12:22 CST; score 5/10, verdict almost, confidence high.
**Trace/payload evidence update**: Implemented on 2026-04-26 15:01 CST.
**M1 analytical update**: P0-only break-even evidence pack completed on 2026-04-26 15:25 CST.

## What Changed

- Rebuilt `research-wiki/` from scratch and ingested 12 core papers.
- Refreshed literature across NIC/DPU, RDMA, LLM codec, memory/cache, runtime/serving, storage/checkpoint, and host Rx path.
- Rejected the prior narrow "shared DPU compression QoS" idea as the main path because it requires BlueField hardware and is less aligned with the simulator-first AGENTS.md anchor.
- Selected **Rx Expansion Budgeting for Compressed RDMA** as the new active idea.
- Added the M0/M1 trace/payload evidence split: Chakra/ASTRA-sim are schedule-only sources; payload compressibility now comes from P0 literature ratios, P1 local real tensor bytes, optional P2 DDP buckets, or optional P3 public artifact payloads.
- Generated the M1 P0-only analytical sensitivity pack: 960 rows, 384 output-unsafe rows, conditional Go for M2 model plumbing only.

## Selected Idea

Compressed RDMA must budget decompressed output bytes, not just compressed wire bytes. The proposed EARB mechanism tracks expansion ratio, Rx output-byte credits, decompression queue pressure, and feedback to RDMA control so receiver-side PCIe/host-memory/Rx-buffer bottlenecks do not become hidden tail-latency failures.

## Key Artifacts

- Literature report: `nic-lossless-compression/research-lit/2026-04-26.md`
- Idea report: `idea-stage/IDEA_REPORT.md`
- Idea candidates: `idea-stage/IDEA_CANDIDATES.md`
- Final proposal: `refine-logs/FINAL_PROPOSAL.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- M1 report: `experiments/rx-expansion/results/M1_GO_NOGO_REPORT.md`
- M1 JSON/CSV: `experiments/rx-expansion/results/m1_break_even.json`, `experiments/rx-expansion/results/m1_break_even.csv`
- Review gate record: `review-stage/AUTO_REVIEW.md`
- Research wiki query pack: `research-wiki/query_pack.md`

## Blockers / Degradations

- `deepxiv` CLI is not installed, so DeepXiv was recorded as unavailable rather than fabricated.
- Local shell network cannot resolve arXiv/Semantic Scholar API hosts, so arXiv/S2 adapters degraded; browser/web search was used for current metadata.
- Zotero/Obsidian MCP resources are not exposed in this Codex environment.
- Initial `codex exec` nightmare review could not reach `api.openai.com`; fallback Claude review returned a disabled-organization API error. This was later rerun successfully with Oracle browser mode.

## Next Step

Use the P0-only M1 evidence pack for targeted Go/No-Go review or M2 model-plumbing decision. Do not claim real compressed communication payload behavior from this pack.
