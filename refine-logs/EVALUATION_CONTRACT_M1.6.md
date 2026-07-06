# Evaluation Contract — M1.6 (Channel-Major Layout Transforms, TRACE-inspired)

**Status:** RED per the pre-registered worst-model rule (decided 2026-07-06, same day, on captured
gpt2 + Qwen2.5-7B KV) — **with a real, architecture-dependent gain on the modern model** that the
worst-model clause excludes from the claim: qwen bf16 0.708→**0.671** (chan_bt), qwen fp8_e5m2
0.732→**0.704** (chan, first fp8 transform win, ANS-parity with UCCL-Zip); gpt2 only 0.697/0.724
(misses YELLOW by 0.002/0.004; cross-model spread 0.025/0.020 > the 0.01 agreement bound). Synthetic
control confirmed zero artifact gain. All rows bit-exact. Claimable multi-model α remains M1.5's.
**Third-model extension RESOLVED (2026-07-06, Llama-3.1-8B, per the pre-registered rule below):
fp8_e5m2 RE-REGISTERED as YELLOW (modern-arch scope) at α\*=0.704** — Llama 0.699 agrees with Qwen
0.704 within 0.005, gpt2 confirmed the outlier. **bf16 NOT re-registered** — Llama 0.690 lands in
the pre-registered in-between zone (clears YELLOW individually but 0.019 from Qwen > the 0.01
bound); the three models form a gradient (0.697/0.690/0.671), not a clean modern/legacy split.
See `experiments/m1_6/M1_6_REPORT.md`.
**Code:** `experiments/m1_6/` (69 unit tests) · **Results:** `experiments/m1_6/m16_results.json`,
`M1_6_REPORT.md`, `commodity_decode_cost.json`

## Motivation

The 2026-07-06 literature refresh surfaced **TRACE** (arXiv 2509.03377, IEEE TC in press): **lossless
BF16 KV at α ≈ 0.53** via a *channel-major, disaggregated bit-plane layout* + KV-specific transform —
in **custom CXL-controller silicon**. This breaks M1/M1.5's implicit "byte-transpose + deflate ≈ the
floor" story: order-0 byte entropy (even after byte-transpose) does **not** bound what a *reordering*
transform can expose, because real KV has strong **per-channel scale structure** (each head_dim channel
has a characteristic magnitude → near-constant exponent within a channel) that the token-major wire
layout interleaves away.

TRACE's layout step is a **pure permutation** — the same complexity class as M1.5's byte_transpose. M1.6
asks: **how much of TRACE's channel-major gain survives WR-ZipGuard's hard constraint** that the result
is ONE standard deflate stream a commodity BF3 decompresses (no custom silicon, no multi-stream codec)?

Either answer feeds the paper: a large gain widens the M3 frontier (α↓ ⇒ (1−α)·D_egress ↑); a small one
becomes the honest, measured **"cost of commodity decode"** against TRACE.

## Scope and method

- **Transforms** (all reversible; inverse = permutation-class + prefix-sum, runnable off-GPU):
  - `chan` — channel-major reorder: view the chunk as `(rows, head_dim)` values (head_dim is the fastest
    axis in both captured and synthetic layouts), transpose to `(head_dim, rows)` so each channel's
    values are contiguous. Element-wise (values move atomically). No-op knowledge needed at the
    receiver beyond `head_dim` (1 metadata byte).
  - `chan_bt` — `chan` then M1.5's `byte_transpose` (for 2-byte bf16: groups each channel's exponent
    bytes contiguously). For 1-byte fp8, `byte_transpose` is identity ⇒ `chan_bt` ≡ `chan`.
  - `chan_bt_delta` — `chan_bt` then global byte-wise delta (mod-256). Near-constant per-channel
    exponent streams become near-zero runs. Inverse = cumsum mod 256 (cheap, off-GPU).
  - `bt_delta` — `byte_transpose` then delta, **no reorder** (isolates the reorder's contribution from
    the delta's).
  - `delta` — delta alone (control).
  - M1.5's `byte_transpose` is re-measured in-harness as the reference baseline.
- **Claimable α = concat mode only**: one standard deflate (zlib L6) stream over the whole transformed
  buffer — the M2-proven BF3 path. zstd/ANS/custom bitstreams excluded.
- **Corpus:** M1/M1.5 harness reused verbatim (`synth`, `m1_codecs`, `chunking`, capture helpers).
  Synthetic 7B sweep + **real captured KV (gpt2 + Qwen2.5-7B)**. Chunks ≥ 256 KB.
- **Decisive data = captured KV** (same rule as M1.5), and **doubly so here**: the standard-normal
  synthetic generator has *no per-channel scale structure*, so it should show ~no `chan` gain — synthetic
  serves as harness validation and as a mechanism probe (a large synthetic `chan` gain would indicate a
  bug or an artifact), NOT as evidence.
- **Excluded:** bit-plane (sub-byte) variants — M1.5 showed the byte-level transpose captures the
  exponent-plane win at ~40× less cost, and bitplane *hurts* fp8; TRACE's precision-proportional fetch
  and its custom entropy stage — not portable to a single deflate stream.

## Go/No-Go criteria (pre-registered)

Let α* = best concat α across M1.6 methods, medians on captured KV, both models agreeing (±0.01):

- **GREEN** — **bf16 α\* ≤ 0.65** or **fp8_e5m2 α\* ≤ 0.70**, bit-exact, single-stream. (≥0.05 α gain
  for bf16 over M1.5's 0.705, i.e. wire saving 30%→≥35%, enough to visibly move the M3 B_crit; or the
  first-ever fp8 transform win.)
- **YELLOW** — bf16 α\* ∈ (0.65, 0.695] or fp8_e5m2 α\* ∈ (0.70, 0.72]: real but small improvement —
  fold into M3 refresh, report as "TRACE's mechanism survives commodity decode only partially".
- **RED** — no method beats the M1.5 baselines by > 0.01 on captured KV: channel-major structure is
  unreachable through a single deflate stream → M1.5's α (bf16 0.70 / e5m2 0.73) stands as the
  commodity-decode frontier; TRACE's remaining gap (0.70→0.53) is priced as custom-silicon-only.
- Disqualifiers regardless of α: any bit-exact failure; verdict-driving gain appearing only on
  synthetic; a method whose inverse cannot run off-GPU as a permutation/prefix-sum-class op.

## What we CAN claim if GREEN/YELLOW

- A commodity-decodable α below M1.5's, with the same single-deflate-stream/BF3 execution (C2 intact),
  at permutation-class sender cost; the measured fraction of TRACE's layout gain that needs no new
  silicon.

## What we CANNOT claim (any verdict)

- **NOT TRACE parity**: TRACE's 0.53 includes a KV-specific transform + hardware entropy stage we
  deliberately exclude; we measure the *portable subset*.
- **NOT profitability from α alone**: T_xform (now possibly reorder+transpose+delta) still not in the
  break-even model; receive-side inverse placement/throughput on the real target still unmeasured
  (M1.5 open item, unchanged).
- **NOT fp8 scaled-quantizer realism** (same naive-astype caveat as M1.5).
- Chunk-boundary caveat: chunks are cut at byte offsets; a chunk spans whole `(row, head_dim)` rows
  only because 256KB/1MB are multiples of head_dim×itemsize for gpt2 (64) and Qwen2.5-7B (128); the
  gate must enforce this alignment in deployment (1 line, but it is a real constraint — record it).

## Open items this feeds

1. E3: M3 frontier re-run with the best claimable bf16 (and e5m2, if improved) α.
2. E2: the "cost of commodity decode" table (ours vs TRACE 0.53 / UCCL-Zip ANS 0.64 / DFloat11 0.70 /
   SplitZip 0.755).
3. M4a: the receive-side inverse is now (possibly) reorder∘transpose∘cumsum — same off-GPU placement
   question, slightly higher cost; measure there.

## Third-model extension (pre-registered 2026-07-06, BEFORE the capture runs)

**Question:** is gpt2 the architecture outlier (per-channel scale structure being a property of
modern GQA/RoPE KV), or is the Qwen gain model-idiosyncratic?

- **Model:** one Llama-3.1-8B-class modern GQA/RoPE model, captured with the *identical* harness and
  parameters as gpt2/Qwen (seq 512, 64 decode tokens, layer fracs 0/0.5/1, chunks 256KB/1MB, all six
  methods, deflate L6, bf16 + both fp8). Primary: `NousResearch/Meta-Llama-3.1-8B` (ungated mirror of
  the gated meta-llama repo); fallback if unavailable via hf-mirror: `mistralai/Mistral-7B-v0.3`
  (also GQA/RoPE). One model, chosen before seeing any numbers; no shopping for a third model after
  results.
- **Agreement test (per dtype, medians on captured KV, best method):** the new model *agrees with
  Qwen* if |α_new − α_qwen| ≤ 0.01 (the existing agreement bound), and *sides with gpt2* if its best
  α misses the YELLOW cutoff (bf16 > 0.695, e5m2 > 0.72).
- **Re-registration rule:** IF the new model agrees with Qwen AND worst-of-{Qwen, new model} clears
  the original thresholds (bf16 ≤ 0.65 GREEN / ≤ 0.695 YELLOW; e5m2 ≤ 0.70 GREEN / ≤ 0.72 YELLOW)
  → re-register the layout claim **scoped to modern-architecture (GQA/RoPE) KV**, with gpt2 reported
  as the measured architecture outlier, verdict labeled "GREEN/YELLOW (modern-arch scope)". The
  all-models verdict of this contract **stays RED** — the re-registration is a new, narrower claim,
  not a revision of this one.
- IF the new model sides with gpt2, or lands in between (neither within 0.01 of Qwen nor past the
  YELLOW cutoff) → **no re-registration**; the Qwen numbers remain a single-model
  architecture-conditional observation and the paper says so.
- Disqualifiers unchanged (any bit-exact failure; off-GPU-inverse class violation).

**RESOLUTION (2026-07-06, capture ran same day on myDevbox; 288 rows, 0 bit-exact failures;
`m16_outputs/three_model_analysis.json`):**

| dtype | Llama-3.1-8B best | Qwen best | diff | agreement (≤0.01) | worst-of-modern | outcome |
|---|---|---|---|---|---|---|
| fp8_e5m2 | **0.699** (chan) | 0.704 | 0.005 | ✔ agrees | 0.704 | **RE-REGISTERED: YELLOW (modern-arch scope)** — 0.70 < 0.704 ≤ 0.72 |
| bf16 | **0.690** (chan_bt) | 0.671 | 0.019 | ✘ (in-between: clears YELLOW individually, not within bound) | — | **NO re-registration** (strict rule; reported as observation) |

gpt2 is confirmed as the architecture outlier for e5m2. For bf16 the three models form a gradient
(gpt2 0.697 > Llama 0.690 > Qwen 0.671) rather than a clean modern/legacy split — the honest
statement is "channel-major gain grows with architecture modernity" and only the e5m2 claim is
registered. The re-registered claim: **on modern-architecture (GQA/RoPE) KV, fp8_e5m2 `chan` +
single-stream deflate reaches α\*=0.704 (worst of Qwen2.5-7B/Llama-3.1-8B), BF3-decodable,
bit-exact — ANS-parity with UCCL-Zip's custom-bitstream 0.70**. The all-models verdict of this
contract remains RED, unchanged.
