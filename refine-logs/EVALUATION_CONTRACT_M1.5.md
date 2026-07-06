# Evaluation Contract — M1.5 (Float-Split / Bit-Plane Preprocessing)

**Status:** GREEN (bf16 rehabilitated; fp8 unaffected) · decided on real captured KV
**Code:** `experiments/m1_5/` (49 unit tests) · **Results:** `experiments/m1_5/m15_results.json`,
`M1_5_REPORT.md`

## Motivation

M1 measured deflate on the **raw, interleaved** KV byte stream and concluded **BF16 "provably
can't compress"** (α ≈ 0.79 ≈ its order-0 byte-entropy floor 0.773), leaving **FP8_E5M2 the only
profitable dtype**. Real GPU-side codecs (DietGPU / UCCL-Zip / NetZIP / ZipNN) apply a **data-layout
transform before compression** — grouping the low-entropy exponent apart from the near-random
mantissa — which can beat the raw-byte floor. M1.5 asks whether such a transform changes WR-ZipGuard's
dtype gate, **under the hard constraint that the receiver is commodity BF3 doing one standard deflate
decompress**.

## Scope and method

- **Transforms** (reversible, applied on the sender before deflate):
  - `byte_transpose` — Structure-of-Arrays 2-byte de-interleave (a pure permutation; FPGA-/memcpy-cheap;
    **no-op for 1-byte fp8**). **The deployment candidate** — its inverse is a single strided copy
    runnable off-GPU.
  - `bitplane` — exact sign/exp/mantissa field split, bit-packed (the DietGPU/NetZIP mechanism proper;
    sub-byte gather, costlier). Diagnostic / ceiling.
- **Claimable α = `concat` mode**: transform then deflate the **whole buffer as ONE stream**. This is
  what BF3 decompresses in hardware (the bit-exact path M2 proved). `per-plane` mode (compress sign+exp,
  store mantissa RAW) is reported as the **DietGPU-style ceiling but is NOT BF3-claimable** (it needs N
  streams / a custom codec).
- **Codec:** deflate (zlib L6) only — the BF3-decodable codec. zstd/ANS are excluded (not BF3-decodable).
- **Corpus:** the M1 harness reused verbatim (`synth`, `m1_codecs`, `entropy`). Synthetic 7B sweep +
  **real captured KV (gpt2 + Qwen2.5-7B)** via `capture_hf_kv` helpers. Chunks ≥ 256 KB (BF3 break-even).
- **Decisive data = captured KV.** The standard-normal synthetic generator narrows the exponent spread
  and inflates the exponent plane (~0.04–0.06 α), so the verdict is decided on real KV; synthetic is breadth.

## Go/No-Go criteria (pre-registered)

- **GREEN** — best **concat** deflate α (single stream) for a dtype M1 gated OUT (bf16 or fp8_e4m3)
  is **≤ 0.75 on captured KV**, transform is **bit-exact**, and the inverse is an **off-GPU
  permutation-class** operation.
- **YELLOW** — concat α improves by ≥ 0.03 vs the in-harness raw baseline for some dtype/chunk but none
  newly cross 0.75, **or** the crossing appears only on synthetic and is not confirmed on captured KV.
- **RED** — captured concat α within seed-noise of raw (the per-plane exp gain is unreachable through
  a single-stream commodity decompressor) → M1's raw-byte / fp8_e5m2-only conclusion stands.

## Result (this contract → GREEN)

| dtype | raw α | best split α (concat) | method | gpt2 | qwen2.5-7b | synthetic | verdict |
|---|---|---|---|---|---|---|---|
| **bf16** | 0.79–0.80 | **0.70–0.71** | byte_transpose | 0.705 | 0.708 | 0.702 | **rehabilitated** ✅ |
| fp8_e4m3 | 0.82–0.84 | 0.82–0.84 (no-op) / 0.85 (bit-split worse) | — | neutral | neutral | neutral | stays OUT |
| fp8_e5m2 | 0.72–0.73 | 0.73 (no-op) / 0.83–0.86 (bit-split **worse**) | — | neutral | neutral | neutral | keep RAW path |

bf16's win is **entirely the exponent plane** (high byte deflates to ~0.40; low byte + all mantissa are
incompressible at ~1.0). `byte_transpose` (≈ 2500–2750 MB/s software) clears the gate on its own;
`bitplane` adds only ≈ 0.002–0.006 for ~40× the cost — **not worth it**.

## What we CAN claim

- M1's "BF16 provably can't compress" was **specific to raw interleaved bytes**. A cheap reversible
  byte-transpose drops bf16 KV to **≈ 0.70 on real gpt2 + Qwen2.5-7B**, crossing the 0.75 gate — so the
  **profitable dtype set widens to include bf16, the *default* KV dtype** (high applicability).
- The transform is a **pure permutation**; its inverse is a single strided copy that can run **off the
  GPU** (host CPU / DPU-ARM), preserving WR-ZipGuard's differentiator. **Bit-exact** verified; the concat
  output is **one standard deflate stream** (the BF3 path proven in M2).

## What we CANNOT claim

- **NOT that the M3 profitable-bandwidth region materially widens.** bf16 at α≈0.70 gives ~30% wire
  saving vs fp8_e5m2's ~27% — the binding M3 constraint (`α < (1−α)·D_egress`) is **barely moved**;
  B_crit shifts only marginally. The contribution is **dtype coverage, not bandwidth reach**. Same narrow
  bandwidth-limited regime.
- **NOT that any transform helps fp8.** byte_transpose is a no-op (1 byte); bit-split **regresses** both
  fp8 formats (deflate's byte-level LZ matching is destroyed; the fp8 mantissa is near-full-entropy).
  fp8_e4m3 stays OUT; fp8_e5m2 keeps M1's raw path.
- **NOT the literature ANS ratios** (bf16 ~0.64, e5m2 ~0.70): those use custom ANS/Huffman codecs BF3
  cannot decode. Only deflate-on-the-transformed-stream is claimable here.
- **NOT a profitability verdict from α alone.** `T_xform_send` + `T_xform_recv` are not yet in the
  break-even model, and the **inverse placement (host/DPU-ARM/GPU) and its throughput on the real target
  are unmeasured** — if the inverse lands on the GPU the differentiator is violated (ties to M2's blocked
  DPU-ARM access).
- fp8 captures use a **naive astype quantizer** (saturation tames the exponent plane); real scaled-fp8 may
  differ. Saturation fraction not yet reported.

## Open items (feed M3-refresh / M4)

1. **bf16 in the M3 frontier**: re-run with α≈0.70 to quantify the (expected marginal) band shift.
2. **T-inverse placement + throughput** on host CPU / DPU-ARM (off-GPU, target > 5 GB/s) on the real
   target — the open design question; couples to the M2 x8/DPU-ARM item.
3. Fold `T_xform` cost into `profitability.py`; report fp8 saturation fraction.
