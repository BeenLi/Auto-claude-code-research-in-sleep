# M1.5 — Float-Split / Bit-Plane Preprocessing → GREEN (bf16 rehabilitated)

**One-line verdict:** A cheap, reversible **byte-transpose before deflate rehabilitates BF16 KV** —
M1's "BF16 provably can't compress" was an artifact of measuring **raw interleaved bytes**. On real
gpt2 + Qwen2.5-7B KV, byte-transpose drops bf16 from α≈0.79–0.80 to **≈0.70–0.71**, crossing the 0.75
profitability gate. The transform does **not** help fp8 (no-op for the 1-byte formats; bit-split makes
them worse). **The profitable *dtype* set widens to the default dtype (bf16); the profitable
*bandwidth* region does not.**

## Why this milestone exists

The user observed that GPU-side compressors (DietGPU, which **UCCL-Zip** wraps; **NetZIP**, **ZipNN**)
transform float data *before* compression — grouping exponent bits/bytes together (low entropy,
compressible) and leaving the mantissa (near-random) alone — to beat the naive byte-entropy floor. M1
had concluded BF16/FP8_E4M3 "provably can't compress" based on **order-0 byte entropy of the raw
stream**, which does **not** bound the achievable ratio after a structure-exposing layout transform.
M1.5 measures the transformed-stream α under WR-ZipGuard's hard constraint: the receiver is **commodity
BF3 doing one standard deflate decompress** (no custom codec).

## Method (reuses the M1 harness verbatim)

- Transforms (`floatsplit.py`, bit-exact reversible — verified):
  - **`byte_transpose`** — Structure-of-Arrays 2-byte de-interleave. Pure permutation (FPGA-/memcpy-cheap);
    **no-op for 1-byte fp8**. Inverse = one strided copy, runnable **off-GPU**. *The deployment candidate.*
  - **`bitplane`** — exact sign/exp/mantissa field split, bit-packed. The DietGPU/NetZIP mechanism proper;
    sub-byte gather (costlier). Diagnostic / ceiling.
- **Claimable α = `concat`**: transform → deflate the **whole buffer as ONE stream** (what BF3 decompresses
  in hardware; the bit-exact path proven in M2). `per-plane` (compress sign+exp, store mantissa RAW) is
  the **DietGPU-style ceiling but is NOT BF3-claimable**.
- Codec: deflate (zlib L6), the only BF3-decodable codec. Corpus: synthetic 7B sweep + **real captured KV
  (gpt2, Qwen2.5-7B)**. Chunks ≥ 256 KB. **Verdict decided on captured KV** (synthetic narrows the
  exponent spread and inflates the win).

## Results

α = compressed/original (lower = better); gate = 0.75. Medians.

| dtype | source | raw α | **byte_transpose** | bitplane | exp-plane | mantissa-plane | xform MB/s |
|---|---|---|---|---|---|---|---|
| **bf16** | gpt2 | 0.800 | **0.705** ✅ | 0.703 | 0.403 | 1.000 | 2726 |
| **bf16** | Qwen2.5-7B | 0.799 | **0.708** ✅ | 0.704 | 0.405 | 1.000 | 2753 |
| **bf16** | synthetic | 0.792 | **0.702** ✅ | 0.697 | 0.388 | 1.000 | 2476 |
| fp8_e4m3 | gpt2 | 0.834 | 0.834 (no-op) | 0.849 ✗ | 0.706 | 1.000 | — |
| fp8_e4m3 | Qwen2.5-7B | 0.837 | 0.837 (no-op) | 0.831 | 0.695 | 1.000 | — |
| fp8_e5m2 | gpt2 | 0.731 | 0.731 (no-op) | 0.857 ✗ | 0.785 | 1.000 | — |
| fp8_e5m2 | Qwen2.5-7B | 0.732 | 0.732 (no-op) | 0.828 ✗ | 0.759 | 1.000 | — |

**Reading the table:**
1. **bf16 is rehabilitated on real KV.** Both real models and synthetic land at ≈0.70–0.71 < 0.75. The
   synthesizer's heavy-tailed worry (0.752) did **not** materialize on gpt2 or Qwen2.5-7B.
2. **The win is entirely the exponent plane.** bf16's high byte (sign‖exp[7:1]) deflates to ≈0.40; the
   low byte (exp[0]‖mantissa) and all fp8 mantissas are incompressible (≈1.0). This is a hard floor no
   permutation can beat (the rigorous `mantissa_fraction_floor`: bf16 0.5, fp8_e5m2 0.375, fp8_e4m3 0.5,
   all unreachable since sign is ~1.0 bit and exponent retains ~2.5 bits).
3. **The split does not help fp8.** byte_transpose is a no-op (1 byte); bit-split **regresses** both fp8
   formats — sub-byte packbits destroys deflate's byte-level LZ matching and the fp8 mantissa is
   near-full-entropy. fp8_e5m2 keeps M1's raw path (0.73).
4. **byte_transpose is the deployment choice.** ≈2500–2750 MB/s in pure Python (an FPGA/DPU-ARM strided
   copy is far faster), vs bitplane's ≈40–65 MB/s for only ≈0.002–0.006 better α.

Independently cross-checked with a **fresh from-scratch implementation** (zero reuse of `floatsplit`):
bf16 0.792→0.704 bit-exact, single-deflate-stream roundtrip True; fp8 bit-split 0.716→0.845 / 0.818→0.848.

## Implications for WR-ZipGuard

**Widens the dtype set, not the bandwidth region.**
- **+ Dtype coverage (the real win):** WR-ZipGuard's profitable set goes from "FP8_E5M2 only" to
  **"BF16 (via cheap byte-transpose) ≈0.70, AND FP8_E5M2 (raw) ≈0.73."** BF16 is the *default* KV dtype,
  so this materially **raises applicability** — most deployments serve bf16 KV.
- **− Bandwidth reach (unchanged):** bf16 at α≈0.70 saves ~30% on the wire vs fp8_e5m2's ~27%. The
  binding M3 constraint (`α < (1−α)·D_egress`) barely moves; B_crit shifts only marginally. M1.5 does
  **not** lift WR-ZipGuard out of the narrow bandwidth-limited (cross-AZ / oversubscribed / WAN-ish)
  regime. The headline remains "compression pays only on bandwidth-limited fabrics."
- **C2 (commodity decompress) survives:** the transformed buffer is a **standard single deflate stream**;
  BF3 decompresses it bit-exactly (the M2-proven path). The added step is the receive-side **un-transpose**,
  a strided copy that **must stay off the GPU** (host CPU / DPU-ARM) to preserve the differentiator.

## Caveats / open items

- **α-only, not profitability:** `T_xform_send`/`T_xform_recv` are not yet in `profitability.py`, and the
  inverse placement + throughput on the **real target are unmeasured** (couples to M2's blocked DPU-ARM
  access). If the un-transpose lands on the GPU the off-GPU differentiator is violated.
- **fp8 quantizer:** captures use naive `astype` (saturation tames the exponent plane); real scaled-fp8
  may differ. Saturation fraction not yet reported. (bf16 is the models' native dtype — no such artifact.)
- **per-plane is diagnostic only** — not BF3-claimable (needs N streams). Literature ANS ratios
  (bf16 ~0.64) are not achievable on BF3's deflate-only path.

## Next

1. Re-run the **M3 frontier with bf16 α≈0.70** to quantify the (expected marginal) band shift.
2. Measure **T-inverse on host CPU / DPU-ARM** (off-GPU, target > 5 GB/s) on the real BF3 target.
3. Fold `T_xform` into the break-even model; report fp8 saturation fraction.

Code: `experiments/m1_5/` (49 unit tests) · results `m15_results.json` · contract
`refine-logs/EVALUATION_CONTRACT_M1.5.md`.
