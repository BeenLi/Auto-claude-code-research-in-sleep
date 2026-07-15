# Evaluation Contract — E0 (Hardware-Encoder-Constrained α Pre-Check, ISCAS 2027 topic gate)

**Status:** PRE-REGISTERED 2026-07-15 → **measured same day: STRONG_GO** (both dtype paths clear
the strict gates under V3: bf16 chan_bt 0.690→0.708 Δ+0.018, fp8_e5m2 chan 0.704→0.721 Δ+0.017;
V0 reproduction ±0.005 OK; see `experiments/m_e0/E0_REPORT.md` + `e0_results.json`).
**User sign-off on Topic A: pending.** This contract was written and committed
**before** any E0 number was produced (project rule). It is the sole substantive go/no-go between
**Topic A** (KV compression egress datapath on VCU118, ISCAS 2027) and **Topic B** (PSP FPGA
first-implementation fallback). Plan of record:
`/Users/bytedance/.claude/plans/wr-zipguard-obsidian-users-bytedance-li-crispy-goose.md`.

**Code:** `experiments/m_e0/` · **Results (to be produced):** `experiments/m_e0/e0_outputs/*.jsonl`,
`e0_results.json`, `E0_REPORT.md`

## Motivation

All locked-in α numbers (M1/M1.5/M1.6) were measured with **software zlib** (`zlib.compress`,
level 6/9, one stream over the whole chunk). FPGA deflate encoders differ in three ways that all
cost ratio (2026-07-14/15 survey, primary sources):

1. **Match-search effort** — AMD Vitis DCL's 2 GB/s GZip/Zlib kernel lands at Silesia ratio 2.70
   vs software zlib -6 at 3.107 (−13%), i.e. roughly **zlib level-1 class**.
2. **Block-level parallelism** — Vitis kernels compress **independent 32 KB blocks** (no
   cross-block history / shared dictionary).
3. **Static vs dynamic Huffman** — static-Huffman designs (Ledwon 4 GB/s: 1.92 Calgary;
   Fowers/MSR 5.6 GB/s: 2.09) pay −20…−27% vs software; Vitis fixed-Huffman kernel: 2.31 (−26%).

Because WR-ZipGuard's entire wire saving is only ~27–30% (α 0.70–0.73), a text-corpus-scale ratio
penalty could halve the saving and gut the frontier. **However** the KV win is dominated by
order-0 entropy coding of the exponent plane (M1: lz4 ≈ no-op on KV; deflate ≈ entropy floor), not
by LZ77 match depth — so the penalty on KV is *expected* to be far smaller than on Silesia. E0
measures it instead of assuming it, with software zlib parameterization as the encoder proxy
(`level=1` ≈ reduced match effort; `Z_FIXED` ≈ static Huffman; 32 KB independent streams ≈ block
parallelism). Vitis HLS csim cross-check of the real kernel is deferred to Phase A (W2–4); zlib
proxies are conservative stand-ins the survey maps onto the hardware design points.

## Scope and method

- **Codec variants** (all remain standard RFC1950 zlib streams a stock decoder — and BF3 hardware,
  M2-proven — can decompress; 32 KB-blocked variants emit one standard stream per block,
  concatenated, per-block container overhead **included** in α):
  | ID | level | strategy | blocking | stands for |
  |---|---|---|---|---|
  | V0 | 6 | default | whole chunk | locked-α reproduction (harness sanity) |
  | V1 | 1 | default | whole chunk | match-effort cost isolated |
  | V2 | 6 | default | 32 KB independent | blocking cost isolated |
  | **V3** | 1 | default | 32 KB independent | **HW-dyn proxy** (Vitis dynamic-Huffman kernel class) |
  | **V4** | 1 | Z_FIXED | 32 KB independent | **HW-static proxy** (Ledwon/Fowers class) |
  | V5 | 6 | Z_FIXED | whole chunk | Huffman-table effect isolated |
- **Transforms × dtypes** (claimable set only, reusing `m1_6/layout.py` verbatim):
  bf16 × {raw, byte_transpose, chan_bt}; fp8_e5m2 × {raw, chan}.
- **Corpus:** captured KV, same protocol as M1.6 (`capture_real_kv`): gpt2 + Qwen2.5-7B +
  Llama-3.1-8B (NousResearch mirror), prefill phase, layer_fracs {0.0, 0.5, 1.0}, K and V,
  chunks {256 KB, 1 MB}, ≤3 chunks/config. Synthetic 7B sweep as control (expected: no chan gain,
  V0 matches m16 synth rows).
- **Aggregation (mirrors M1/M1.5/M1.6):** median α per (model, dtype, method, variant).
  Claim statistic: for `chan`/`chan_bt` paths = **worst of modern-arch {qwen, llama}** (M1.6
  re-registration scope; gpt2 reported as known outlier); for `raw`/`byte_transpose` paths =
  **worst of all three models** (M1/M1.5 all-model scope).

## Pre-registered decision rule (written before data)

Let Δ(path, V) = α_V(claim statistic) − α_V0(claim statistic), and define the two claimable paths
P_bf16 = best of {bf16 byte_transpose, bf16 chan_bt} and P_e5m2 = best of {e5m2 raw, e5m2 chan},
where "best" is chosen under V3 (the HW-dyn proxy).

- **GO-A** iff at least one of P_bf16, P_e5m2 satisfies BOTH:
  (a) α_V3 ≤ **0.75** (M1's original claimability gate), and
  (b) Δ(path, V3) ≤ **+0.03** (keeps B_crit within ~10% of the M3 scenarios: B_crit ∝ (1−α)).
- **STRONG-GO** iff both paths satisfy (a)∧(b) — paper keeps the two-dtype story.
- **NO-GO → Topic B (PSP)** iff neither path satisfies (a)∧(b).
- **V4 (static Huffman) carries no gate**: it is reported as the measured "dynamic Huffman is a
  design requirement" constraint (expected to fail; if it *passes*, the FPGA design space widens
  to the cheaper static-Huffman engines — pure upside, no decision impact).
- Ties/edge: if V3 fails only via (b) but α_V3 ≤ 0.75 holds with Δ ≤ +0.05, the verdict is
  **GO-A-WEAK**: proceed with Topic A but the paper must quote hardware-α (not software-α)
  everywhere and re-derive B_crit from V3 numbers.

## E0b — NetZIP same-corpus comparison (no gate, positioning data only)

- Source: NetZIP artifact, `github.com/ece-fast-lab/MICRO-2025-NetZIP` (Zenodo DOI
  10.5281/zenodo.16976212, MIT) — the Python NetZIP-algorithm implementation (byte/bit-grouping +
  delta over LZ4/Snappy/Zstd/Deflate), NOT the 50 GB data-collection leg.
- Run their grouping+delta on the same captured KV chunks; report α under their LZ4 default and
  under deflate-6 for comparability.
- **Declared adaptations** (their delta base = "previous training iteration", which does not exist
  for KV): run (i) no-delta (grouping only) and (ii) intra-buffer delta as documented variants;
  M1.6 already measured delta-hurts-KV, expectation is (i) ≥ (ii) in usefulness. Any further
  deviation must be logged in E0_REPORT.md before analysis.

## Verification

- Every measurement row carries a **bit-exact roundtrip check**: per-variant decompress
  (block-wise for V2–V4, concatenated) == transformed buffer, and `layout.invert` == original
  chunk. Any failure ⇒ row invalid, run halted, bug fixed before proceeding.
- **V0 must reproduce locked α within ±0.005** per (model, dtype, method) against
  `m16_results.json` / `m15_results.json` medians — else the harness is broken and no E0 verdict
  may be read.
- Synthetic control: chan gain ≈ 0 expected (per M1.6); a large synthetic chan gain ⇒ artifact,
  halt.
- Analysis script (`analyze_e0.py`) implements this contract's rule verbatim and emits the
  GO/NO-GO verdict machine-readably; the human decision (user sign-off) is recorded here in the
  Status line afterwards.
