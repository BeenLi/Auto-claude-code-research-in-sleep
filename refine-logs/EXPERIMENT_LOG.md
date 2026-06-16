# Experiment Log — WR-ZipGuard

Workflow 1.5 execution log. Initial results separated per the experiment-bridge
output spec. Contract: `refine-logs/EVALUATION_CONTRACT.md`.

---

## M1 — Real Tensor Compressibility Corpus (tracker R003)

**Status (2026-06-15)**: deployed to myDevbox; pipeline validated; **GREEN confirmed
on real KV** (fp8_e5m2 deflate ~0.73 < 0.75); generator cross-validated 40/40 vs real
gpt2 KV. Caveat: profitable *ratio* exists, but software compress is 17 MB/s →
realizing it needs the M4b FPGA. Code: `experiments/m1/` (66 unit tests, pass on box).
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
  cap 0.835); lz4≈1.0 confirmed on real bytes.
- **R003-validate-fp8e5m2** (2026-06-15): capture incl. fp8_e5m2 (`cap_fp8e5m2.jsonl`,
  576 rows, 0 failures). **GENERATOR VALIDATED: 40/40 match**. **The GREEN-driving
  cell is now confirmed on real KV**: fp8_e5m2 deflate-6/9 syn 0.715 vs **real gpt2
  0.729–0.735** — still below the 0.75 ceiling (deflate-1 is marginal at 0.75).
- **Throughput trade-off (decisive nuance)**: fp8_e5m2 deflate software throughput is
  only **17 MB/s (level 6/9) / 32 MB/s (level 1)**. Per the break-even math, C≈17 MB/s
  is profitable only for links slower than ~0.14 Gbps → **software deflate never pays
  at any real link rate**, and there is no software level that both compresses enough
  AND runs fast. M1 thus separates cleanly: a profitable *ratio* exists (GREEN), but
  realizing it needs **hardware-speed compression (M4b FPGA)** — confirming the
  project thesis and the contract claim boundary, and making M3's FPGA-param frontier
  the real gate.
- **R003-bf16-sweep** (2026-06-15): does BF16 (the *default* KV dtype) ever clear 0.75
  at larger chunks / longer sequences? `bf16_chunk_seq_sweep.jsonl`, 1920 rows, 0
  failures. **No — flat 0.792–0.794** across chunks 64K→16M and seq 1K→128K (min
  0.792). Larger chunks/sequences do nothing: deflate's LZ77 window caps at 32KB and
  KV byte stats are stationary across positions.
- **Entropy-floor result (BF16 is a provable no)**: BF16 KV byte entropy = 6.185
  bits/byte → order-0 floor **0.773 > 0.75**, i.e. *no* lossless codec can make BF16 KV
  profitable. Confirmed: zstd-22 (big window) reaches only 0.777 ≈ floor; deflate 0.792.
  FP8_E5M2 byte entropy 5.486 → floor 0.686, deflate 0.716 (clears). **The profitability
  gate is byte entropy, set by mantissa width**: FP8_E5M2 (2 mantissa bits) clears;
  FP8_E4M3 (3 bits, ~0.82) and BF16 (8 bits, floor 0.773) do not. The negative-result
  map is now sharp and dtype-resolved.
- **R003-qwen-anchor** (2026-06-15): real **Qwen2.5-7B** KV (head_dim 128, GQA 4 KV
  heads, seq 2048; `cap_qwen7b.jsonl`, 324 rows, 0 failures). **GENERATOR VALIDATED
  30/30**. Confirms the whole picture on a production 7B model, with deflate landing
  **at the order-0 entropy floor** in every case:

  | Qwen2.5-7B real KV | deflate-6 | entropy | floor H/8 | clears 0.75? |
  |---|---|---|---|---|
  | BF16 | 0.802 | 6.335 | 0.792 | no |
  | FP8_E4M3 | 0.837 | 6.701 | 0.838 | no |
  | FP8_E5M2 | **0.732** | 5.839 | 0.730 | **yes** |

  **Correction to "more quantization ⇒ more compressible"**: FP8_E4M3 is the *least*
  compressible (0.837, worse than BF16). It is specifically **FP8_E5M2's 2-bit mantissa**
  that yields a low-entropy byte stream. Validated now across synthetic + gpt2 +
  Qwen2.5-7B; deltas 0.012–0.028, lz4 still ≈no-op (Qwen K 0.97–0.98).

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
- C3 input (go/no-go): **GREEN, but dtype-gated to FP8_E5M2 KV.** The profitable ratio
  (<0.75) exists only where byte entropy is low enough: FP8_E5M2 (floor 0.686, deflate
  0.716) clears; FP8_E4M3 (~0.82) and **BF16 — the default dtype — provably cannot**
  (entropy floor 0.773 > 0.75; zstd-22 big window only 0.777). WR-ZipGuard's profitable
  regime is **FP8_E5M2 KV transfer specifically**, realized at hardware compress speed.
- Sharpens C2 (commodity BF3 path): useful only for the **deflate** stream (lz4≈no-op),
  on FP8_E5M2 KV. M2 benches BF3 deflate decompress; M3's frontier uses FP8_E5M2 deflate
  ratios with an FPGA-speed compress band.
- Strengthens the negative-result lead: a measured, dtype-resolved map of when
  commodity-DPU KV compression does/doesn't pay, with a *provable* BF16 impossibility.
- Method note: `M1_CHECKLIST §3.3.2` example threshold table is internally
  inconsistent with its own Appendix A formula (it marks software compression as
  profitable when B>C, which Appendix A insight #1 says is impossible). The code
  encodes the *derivation*; the table needs correcting in M1_REPORT.

### Next runs to launch
1. **Qwen2.5-7B / Mistral-7B anchor** (via hf-mirror) — confirm fp8_e5m2 deflate ~0.73
   holds on a large modern model with real FP8 inference dtype, not just gpt2.
2. Full grid (10 seeds, seq 1k–128k, chunks 4KB–64MB, + zstd reference) → corpus,
   figures, `M1_REPORT.md`; recompute go/no-go per-level (not pooled).
3. Add to M1_REPORT: deflate-vs-lz4 split; the ratio×throughput Pareto (software is
   ratio-OK but throughput-hopeless → FPGA-needed); corrected Appendix-A table.
4. Hand M3 the **deflate** ratio distribution + CPA/throughput model (lz4≈no-op), with
   the FPGA-speed compress band as the profitable-region parameter.

---

## M2 — BF3 Hardware Decompress Microbenchmark (tracker R004/R005)

**Status (2026-06-16)**: **unblocked** — real BlueField-3 available on `bf3_server`
(10.154.163.113, root; MT43244 BF3 + integrated ConnectX-7 at c8:00.0; DOCA 2.9.2005).
Peer `bf3_client` (10.154.163.112) available for the later M4 RDMA prototype. **C2
correctness proven; throughput (D_eff) next.**

### Capability query (doca_caps -p c8:00.0) — citable C2 evidence
- `task_compress_deflate` = **unsupported** → BF3 has **no hardware compress**, confirming
  the asymmetric premise on real silicon (not just DOCA docs).
- `task_decompress_deflate` = **supported**; `task_decompress_lz4_stream` / `lz4_block` =
  **supported**. Max decompress buffer **2 MB/task**, buffer-list ≤128 (design constraint:
  chunks >2 MB must split across a buffer list or multiple tasks).

### Correctness (R004) — DONE, bit-exact on hardware
- Built DOCA `decompress_deflate` sample (meson/ninja) → `/tmp/dd_build/doca_decompress_deflate`.
- Input: real **FP8_E5M2 KV** chunk (1 MB), deflate-compressed two ways on myDevbox.
- **BF3 hardware decompress → bit-exact** (sha256 identical to original) for **both**:
  - **stock `zlib.compress()`** (zlib header + Adler-32), `--with-frame` — the cleanest
    "standard format" case; BF3 even validates the Adler checksum.
  - **raw deflate** (wbits=-15), no frame.
- This is C2's structural novelty demonstrated: a standard/commodity compressor's stream is
  decompressed correctly by commodity BF3 hardware — the differentiator over NetZIP.

### Throughput / D_eff (R005) — measured via doca_bench (deflate decompress, host mem)
Command: `doca_bench --device c8:00.0 --pipeline-steps doca_compress::decompress
-a doca_compress.algorithm=deflate --data-provider file --uniform-job-size <comp_size>
--job-output-buffer-size 2097152 --mode throughput`. Egress = decompressed output rate.

- **Pipelining is decisive (red line 3)**: 1 job in flight = latency-bound **21 Gib/s**; queue
  depth 64 = **170 Gib/s** — an **8× jump from depth alone**. Engine ceiling ~170–175 Gib/s is
  **flat across 1→16 host cores** (a single core with deep queue saturates it) → it's a device
  ceiling, and overlap is real **and required**.
- **Chunk size gates D_eff (red line 2)** — egress (≈ Gib/s ×0.134 = GB/s), profitable iff D_eff>B:

  | orig chunk | D_eff egress | GB/s | Gbps | profitable B ceiling |
  |---|---|---|---|---|
  | 4 KB | 6.07 Gib/s | 0.81 | 6.5 | hopeless (~5 µs/task overhead) |
  | 64 KB | 69.8 Gib/s | 9.36 | 75 | ≤75 Gbps |
  | 256 KB | 131.7 Gib/s | 17.7 | 141 | ≤141 Gbps |
  | 1 MB | 167.5 Gib/s | 22.5 | 180 | ≤180 Gbps |
  | 2 MB | 174.9 Gib/s | 23.5 | 188 | ≤188 Gbps (≈ ceiling) |

### M2 red-line verdict (R005) — GREEN for the target regime
- **Red line 1 (D_eff ≤ B_t)**: CLEARED — at ≥256 KB chunks D_eff (141–188 Gbps) > 100 Gbps;
  even 64 KB clears ≤50 Gbps. Only trips at tiny (≤4 KB) chunks or >~140–188 Gbps links.
- **Red line 2 (fixed cost)**: CLEARED for ≥256 KB (the ~5 µs/task overhead amortizes; D_eff
  plateaus near the engine cap). Tiny chunks don't amortize.
- **Red line 3 (pipelining)**: CLEARED — engine saturates with deep queues; design **must** keep
  many tasks in flight (single-shot is 8× slower).
- **Verdict: GREEN** — BF3 deflate decompress sustains 141–188 Gbps (≥256 KB chunks), not a
  bottleneck at the ≤100 Gbps bandwidth-limited target. **Design constraint: aggregate KV into
  ≥256 KB chunks** before compressing (the per-WR gate should batch), and keep the pipeline full.
- **D_eff(chunk) handed to M3** as the measured decompress parameter for the frontier.

### Honest caveats on the M2 numbers
- **Decompress side only.** The compress side is still 17 MB/s software → the asymmetric path's
  sender needs the M4b FPGA; M2 confirms only the receiver.
- **Engine throughput, not full in-pipeline D_eff.** doca_bench measures the decompress engine in
  host memory; the integrated RDMA path adds NIC-recv staging + copy-out (the "staging shim" cost).
  The in-pipeline D_eff (and exposed WR latency) needs the M4a prototype — could be lower than the
  engine ceiling here.
- **2 MB/task cap**: chunks >2 MB need buffer-list splitting (≤128), untested.
