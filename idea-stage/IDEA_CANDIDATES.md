# Idea Candidates

| # | Idea | Pilot Signal | Novelty | Reviewer Score | Status |
|---|------|-------------|---------|---------------|--------|
| 1 | Interference Cartography and QoS-Aware Scheduling for Shared DPU Compression Engines | SKIPPED | Confirmed | High | RECOMMENDED |
| 2 | What LLM State Is Actually Compressible Under DPU Constraints? | SKIPPED | Moderate | Med-High | BACKUP |
| 3 | Fixed-Tile KV Compression for DPU Fetch Paths | SKIPPED | — | Low | ELIMINATED |

## Active Idea: #1 — Interference Cartography and QoS-Aware Scheduling for Shared DPU Compression Engines
- Hypothesis: The main QoS failure mode on shared DPU compressors is head-of-line blocking from bad tenant mixes, and a simple size/compressibility-aware scheduler can provide strong p99 isolation with modest throughput loss.
- Key evidence: Needs BlueField DPU for pilot mapping.
- Next step: /research-refine-pipeline or secure hardware.
