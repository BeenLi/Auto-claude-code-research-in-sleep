# Experiment Log — WR-ZipGuard

Workflow 1.5 execution log. Initial results separated per the experiment-bridge
output spec. Contract: `refine-logs/EVALUATION_CONTRACT.md`.

---

## M1 — Real Tensor Compressibility Corpus (tracker R003)

**Status (2026-06-15)**: deployed to myDevbox; pipeline validated; first real signal
obtained (provisional GREEN, narrow); synthetic generator cross-validated against
real gpt2 KV (20/20). Code: `experiments/m1/` (66 unit tests, all pass on box).
Platform: myDevbox (Debian, Python 3.13, 64-core x86_64, 251 GB RAM, **no GPU**;
pip + hf-mirror.com reachable, huggingface.co blocked → `HF_ENDPOINT=hf-mirror.com`).

### Baseline reproduction status
- `core_baseline = raw` (no compression, ratio = 1.0): implemented as the `none`
  codec; exact by construction. Go/No-Go = **go**. No external baseline to
  reproduce in M1 (SplitZip/KVServe/KVCodec deferred to M3/M4).

### Idea smoke status
- **Unit tests**: 62/62 pass locally (Mac dev venv) **and on myDevbox**.
- **Synthetic pipeline smoke** (box, `tiny` model): 648 rows, **0 bit-exact
  roundtrip failures**, 2.6 s; generate→measure→aggregate→go/no-go end-to-end OK.
- **HF capture smoke** (gpt2, CPU forward, via `HF_ENDPOINT=https://hf-mirror.com`):
  432 rows, **0 bit-exact failures**, 12 layers. (First attempt hit a transformers
  5.x bug — `DynamicCache` not subscriptable; fixed with a tested `_kv_layers`
  normalizer handling tuple / `.layers` / `.key_cache` / `to_legacy_cache`.)

### Completed runs
- R003-smoke-synth: `m1_outputs/smoke.jsonl` (648 rows, 0 failures). Pipeline proof.
- **R003-prelim-synth** (2026-06-15): 7B config, BF16/FP8_E4M3/FP8_E5M2,
  prefill+decode, K+V, seq 1024, layers {0,last}, chunks {64KB,1MB}, codecs
  {none,deflate,lz4}, seeds {42,43}. **1728 rows, 0 bit-exact failures, 181 s.**
  `m1_outputs/compressibility_corpus.jsonl` + `threshold_analysis.json`.
  - **VERDICT: GREEN (narrow)** — only deflate on FP8_E5M2 clears the 0.75 ceiling
    (p50 **0.715**). Full picture (p50, pooled over levels/seeds/layers/chunks):

    | codec | bf16 | fp8_e4m3 | fp8_e5m2 |
    |---|---|---|---|
    | **deflate** | 0.792 | 0.818 | **0.715** |
    | **lz4** | 0.996–0.999 | ~1.000 | 0.993–0.998 |

  - **Key finding**: of the two BF3-decompressible codecs, **only deflate
    compresses KV bytes; lz4 ≈ no-op (~1.0)**. Expected: deflate's Huffman stage
    exploits the biased byte-value (exponent) distribution of float tensors, while
    lz4 is match-only and finds little literal repetition. Directly steers M2/M4 to
    deflate and corroborates NE-2 / NetZIP's exponent-structure premise.
  - **Caveats (why this is provisional, not a claim)**: single seq_len; 2 seeds;
    bounded chunks; no zstd reference. GREEN hangs on one dtype × one codec.
- **R003-validate** (2026-06-15): cross-validate synthetic vs real gpt2 KV
  (`cap_smoke.jsonl`, 432 rows). **GENERATOR VALIDATED: 20/20 overlapping configs
  match** (tol 0.08, deltas 0.007–0.017). Real KV is marginally *less* compressible
  than synthetic (e.g. bf16 deflate: syn 0.793 vs cap 0.800; fp8_e4m3: syn 0.818 vs
  cap 0.835), so the generator is slightly optimistic but within tolerance; lz4≈1.0
  confirmed on real bytes. **Important**: the captured overlap covers bf16 + fp8_e4m3
  at 64KB/prefill only (gpt2 decode KV too small to chunk; fp8_e5m2 not in this
  capture) — so the GREEN-driving fp8_e5m2=0.715 is **not yet cross-validated**, and
  on the validated dtypes deflate lands ~0.80–0.84, *above* the 0.75 ceiling.

### Failed / stuck runs
- None. (Earlier rsync transfer failed on shell-banner corruption; switched to
  tar-over-ssh — resolved.)

### Missing artifacts / limitations
- **No GPU on myDevbox** → real captures use HF CPU forward (degraded from vLLM
  online hook, per contract) and an ungated model (gpt2 smoke; Qwen2.5-7B /
  Mistral-7B for fuller anchors). No HF token available.
- Preliminary sweep is **synthetic-only and bounded** (3 seeds, ≤5 chunks/config,
  seq ≤ 8k); not yet cross-validated against captures, so its verdict is
  provisional until the validity guard runs.

### Metric coverage
- compression ratio (per phase/dtype/codec/chunk) ✓, compress throughput ✓,
  byte-level Shannon entropy ✓, bit-exact roundtrip ✓. Distribution-fit params +
  codec CPA model for the M3 handoff: not yet (post-full-grid).

### Claim impact
- C3 input (go/no-go): **provisional GREEN** keeps the asymmetric thesis alive into
  M2 — but narrow, and only via deflate. The lz4≈no-op result sharpens C2: the
  "commodity BF3 decompress" path is only useful for the **deflate** stream, so M2
  must bench BF3 **deflate** decompress specifically, and the profitability frontier
  must use deflate ratios (~0.72–0.82), not an optimistic blended codec number.
- Method note: `M1_CHECKLIST §3.3.2` example threshold table is internally
  inconsistent with its own Appendix A formula (it marks software compression as
  profitable when B>C, which Appendix A insight #1 says is impossible). The code
  encodes the *derivation*; the table needs correcting in M1_REPORT.

### Next runs to launch
1. **Validate the GREEN-driving cell**: capture with fp8_e5m2 (and larger anchors —
   Qwen2.5-7B/Mistral-7B via the mirror) to confirm the 0.715 that GREEN rests on;
   the validated dtypes so far (bf16/fp8_e4m3) sit at ~0.80–0.84, above 0.75.
2. Full grid (10 seeds, seq 1k–128k, chunks 4KB–64MB, + zstd reference) → corpus,
   figures, `M1_REPORT.md`; recompute go/no-go per-level (not pooled).
3. Add the deflate vs lz4 split + the corrected Appendix-A threshold table to M1_REPORT.
4. Hand M3 the deflate ratio distribution + CPA model (only deflate matters; lz4≈no-op).
