# Evaluation Contract — WR-ZipGuard M1 (Real Tensor Compressibility Corpus)

> Workflow 1.5 (experiment-bridge) gate, written before implementation.
> **Scope: M1 only** (Block 1 of `EXPERIMENT_PLAN.md`, tracker R003). M2–M4b get their own
> contracts. The idea-level handoff fields in `EXPERIMENT_PLAN.md` describe the whole project; the
> three scope corrections below adapt them to the M1 software measurement, which is the cheapest
> go/no-go and has none of M4b's FPGA dependencies.

## Scope corrections vs the idea-level handoff (rationale)

1. **Feasibility is per-milestone, not idea-level.** `EXPERIMENT_PLAN.md` reports
   `evaluation_feasibility_score: 3`, downgraded because the *headline speedup* needs an FPGA
   compressor in M4b. M1 is pure-CPU software compression measurement: deps installable, first
   signal in hours, no special hardware. **M1 feasibility = 5.** The idea-level 3 is recorded in
   `handoff_gate_notes` and applies to M4b, not here.
2. **`target_validation_style` for M1 is `prototype_measurement`.** The plan's
   `simulation_gate_then_prototype_measurement` is the whole-project arc; M1 itself measures real
   compression ratios/throughput on real bytes (M3 is the `simulator_evaluation` step).
3. **Baseline for M1 is `raw` (no compression, ratio = 1.0), not the paper-only KV systems.**
   SplitZip/KVServe/KVCodec are contextual baselines for M3/M4; M1's only reference is uncompressed
   transfer, which is trivially available and needs no reproduction.

## Contract fields

- **core_baseline**: `raw` — uncompressed bytes, compression ratio = 1.0, the reference every codec
  must beat. (Contextual codec baselines SplitZip/KVServe/KVCodec deferred to M3/M4.)
- **baseline_artifact_readiness**:
  - score: 2
  - status: config_reproducible
  - verification_status: verified
  - evidence: "raw" is the identity transform; bytes-on-wire = original size by construction.
  - adapter_notes: none — implemented as the `none` codec in the codec matrix.
- **baseline_source**: n/a (no-op reference, not an external system)
- **baseline_evaluation_platform**: myDevbox (Debian, Python 3.13, 64-core x86_64, 251 GB RAM, no GPU)
- **baseline_workload**: BF16/FP8 KV tensor chunks (synthetic primary + HF-captured anchors)
- **baseline_metrics_used**: bytes-on-wire (= original size for raw)
- **selected_evaluation_backend**: CPU software compression measurement (deflate/LZ4/zstd via Python
  bindings on myDevbox); prototype_measurement style, no simulator and no GPU in M1.
- **workload**: see `M1_CHECKLIST.md` §1.1 coverage matrix — phase × K/V × dtype (BF16/FP8_E4M3/
  FP8_E5M2) × model scale × seq_len × layer depth × chunk size; supplementary training tensors.
- **metrics**: **compression-ratio distribution per phase/dtype/codec (decisive)**; compress
  throughput (MB/s); byte-level Shannon entropy; bit-exact roundtrip rate; (for M3 handoff) ratio
  distribution params + codec CPA model.
- **negative_evidence_response**: addresses NE-2 — M1 is the direct test of NE-2's claim ("standard
  lossless codecs on raw BF16/FP8 KV give poor compression"). A RED result *confirms* NE-2 and pivots
  to the negative-result paper; a GREEN result bounds where NE-2 does not hold.
- **target_validation_style**: prototype_measurement
- **evaluation_target_clarity**: clear
- **evaluation_feasibility_score**: 5 (M1 scope)
- **evaluation_feasibility_breakdown**:
  - platform_workload_access: myDevbox reachable (ssh), pip network live, 745 GB free; no GPU →
    synthetic generation via numpy+ml_dtypes (CPU), real anchors via HF CPU forward. No HF token →
    ungated model (Qwen2.5-7B / Mistral-7B-v0.3) for captures, not gated Llama-2.
  - evaluation_adapter_cost: low — standard codec bindings; synthetic generator + streaming harness
    are the only new code; both unit-tested.
  - first_signal_runtime: hours (synthetic sweep is CPU-bound but embarrassingly parallel across 64
    cores; HF anchor captures are minutes each for a handful of samples).
- **refine_overall_score**: 9 (from REFINE_STATE.json)
- **refine_verdict**: READY
- **drift_status**: preserved
- **handoff_refresh_status**: passed
- **handoff_to_workflow_1_5**: ready
- **handoff_gate_status**: pass
- **handoff_gate_notes**: idea-level `evaluation_feasibility_score: 3` originates from M4b (FPGA
  compressor must be custom-built) and is scoped away from M1, which is CPU-only and scores 5.
  No `conflicts: NE-*` present. GPU unavailable on myDevbox → real-capture path uses HF CPU forward
  (degraded from vLLM online hook) and an ungated model; recorded as an M1 limitation, not a blocker.
- **baseline_reproduction_mode**: configure_existing (raw = no-op identity; nothing to reproduce)
- **baseline_go_no_go**: go
- **baseline_smoke_required**: false (raw needs no smoke; the smoke run instead validates the
  codec+measurement pipeline end-to-end on one chunk)
- **baseline_evidence_strength**: strong (raw is exact by construction)
- **idea_execution_readiness**: ready

## M1 success / go-no-go (mirrors M1_CHECKLIST §3.4)

- **GREEN**: ≥1 tensor phase × BF3-supported codec (deflate/LZ4) reaches p50 ratio ≤ 0.75 on a phase
  covering ≥20% of KV transfer volume → proceed to M2.
- **YELLOW**: target met only on large chunks (≥16 MB) or only via slow codecs (e.g. zstd-19) →
  proceed to M2 but flag a narrow profitability window.
- **RED**: all phase × codec p50 ratios > 0.85 → stop; pivot to the negative-result / profitability-
  atlas paper. (Consistent with the M2 red-line pivot in `EXPERIMENT_PLAN.md` Block 2.)

## Validity guard (synthetic vs captured)

M1's "measured" credibility requires the synthetic generator to match real KV byte statistics. At
overlapping configs, cross-validate synthetic vs HF-captured ratio distributions + Shannon entropy;
match → trust the full synthetic sweep, divergence → recalibrate the generator. Every output row is
tagged `synthetic` or `captured` (M1_CHECKLIST §7.3) so M3 can weight confidence.

## Outputs (per bridge output spec)

- code: `experiments/m1/` (unit-tested core + CLI scripts)
- data/report: `m1_outputs/` on myDevbox → `compressibility_corpus.parquet`, `corpus_manifest`,
  `threshold_analysis.json`, figures, `M1_REPORT.md`
- run log: `refine-logs/EXPERIMENT_LOG.md` (baseline / smoke / completed / failed / missing /
  metric-coverage / claim-impact / next)
