# Pipeline Summary

**Problem**: BF3/DPU lossless compression for LLM RDMA tensor traffic can save wire time only in specific regimes; naive offload is often defeated by staging and initialization overhead.  
**Final Method Thesis**: WR-ZipGuard uses a measured BF3 break-even frontier and work-request-granular bypass-on-risk gating to compress only profitable LLM tensor chunks.  
**Final Verdict**: READY  
**Date**: 2026-05-28T17:11:30Z

## Final Deliverables

- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Experiment tracker: `refine-logs/EXPERIMENT_TRACKER.md`

## Contribution Snapshot

- **Dominant contribution**: RDMA WR/chunk-granular compression profitability gate for commodity BF3 DPU.
- **Optional supporting contribution**: BF3 LLM tensor break-even frontier.
- **Explicitly rejected complexity**: SHARP collectives, new ASIC/FPGA codec in the main path, lossy compression, production NCCL driver/plugin.

## Must-Prove Claims

- WR-ZipGuard safely avoids negative BF3 compression cases while capturing positive wire-time savings.
- Work-request/chunk granularity and tensor-aware sampling matter beyond PEDAL-style static compression.

## First Runs to Launch

1. R001: DOCA capability inventory.
2. R002: raw RDMA baseline.
3. R004: cold vs warm BF3 frontier.

## Main Risks

- **No profitable BF3 region**: treat as a negative frontier and design-guidance paper, not a forced system speedup.
- **Proxy semantics viewed as weak**: report the transfer boundary explicitly and avoid full one-sided transparency claims.
- **Baseline artifact gap**: reimplement PEDAL-style static behavior if no public artifact is available.

## Next Action

Proceed to `/experiment-bridge`.
