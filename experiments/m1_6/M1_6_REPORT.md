# M1.6 — Channel-Major Layout Transforms → RED (pre-registered), with an architecture-dependent gain

**One-line verdict:** Under the pre-registered worst-captured-model rule the verdict is **RED**
(bf16 α\*=0.697 > 0.695, fp8_e5m2 α\*=0.724 > 0.72 — both set by gpt2, missing the YELLOW cutoffs
by 0.002/0.004). But the models **disagree beyond the pre-set 0.01 bound**, and that disagreement is
the finding: on **Qwen2.5-7B — the modern, deployment-representative architecture — the mechanism
delivers a real gain** (bf16 **0.708 → 0.671**, fp8_e5m2 **0.732 → 0.704**, the first fp8 transform
win in this project). Per-channel scale structure is strong in GQA/RoPE-era KV and weak in gpt2.

**Third-model update (same day):** Llama-3.1-8B was captured under the pre-registered extension rule
(written before the run). Outcome: **fp8_e5m2 re-registered as YELLOW on modern-architecture KV at
α\*=0.704** (Llama 0.699 within 0.005 of Qwen; gpt2 confirmed the outlier); **bf16 NOT re-registered**
(Llama 0.690 clears YELLOW individually but sits 0.019 from Qwen — a gradient, not a clean split).
The all-models verdict stays RED. Details below.

## Why this milestone exists

The 2026-07-06 literature refresh surfaced **TRACE** (arXiv 2509.03377): lossless bf16 KV at
**α≈0.53** via a channel-major bit-plane layout — in **custom CXL-controller silicon**. Its layout
step is a pure permutation, the same complexity class as M1.5's byte-transpose. M1.6 measured how
much of that gain survives WR-ZipGuard's constraint: **ONE standard deflate stream that shipped BF3
hardware decompresses** (no new silicon, no multi-stream codec), with an off-GPU permutation /
prefix-sum inverse.

## Results (α = compressed/original, deflate L6 single stream, medians, captured KV decides)

| dtype | source | raw | byte_transpose (M1.5) | **chan_bt / chan (M1.6)** | Δ vs M1.5 | best method |
|---|---|---|---|---|---|---|
| bf16 | gpt2 | 0.800 | 0.705 | **0.697** | −0.008 | chan_bt |
| bf16 | **meta-llama-3.1-8b** | 0.799 | 0.709 | **0.690** | −0.019 | chan_bt |
| bf16 | **qwen2.5-7b** | 0.799 | 0.708 | **0.671** | **−0.037** | chan_bt |
| bf16 | synthetic | 0.792 | 0.702 | 0.702 | 0.000 (control ✓) | — |
| fp8_e5m2 | gpt2 | 0.731 | 0.731 (no-op) | **0.724** | −0.007 | chan |
| fp8_e5m2 | **meta-llama-3.1-8b** | 0.730 | 0.730 (no-op) | **0.699** | **−0.031** | chan |
| fp8_e5m2 | **qwen2.5-7b** | 0.732 | 0.732 (no-op) | **0.704** | **−0.028** | chan |
| fp8_e4m3 | qwen2.5-7b | 0.837 | 0.837 (no-op) | 0.826 | −0.011 (stays OUT) | chan |

4068 rows (612 captured across gpt2/Qwen2.5-7B/Llama-3.1-8B + 3456 synthetic), **0 bit-exact
failures** (transform∘invert AND single-deflate-stream roundtrip asserted per chunk).

**Reading the table:**
1. **The mechanism is real and it is structure, not artifact.** The synthetic control (standard-normal
   KV, no per-channel scale structure) shows exactly zero `chan` gain (0.702 = 0.702) — precisely as
   the contract predicted. The captured gains are per-channel scale structure.
2. **It is architecture-dependent.** Qwen2.5-7B (GQA, RoPE, RMSNorm) has strong per-channel structure
   → bf16 −0.037; gpt2 (2019, learned positional embeddings) has little → −0.008. The pre-registered
   worst-model rule therefore lands RED even though the modern model clears the YELLOW band easily.
3. **First fp8 transform win.** 1-byte values can't be byte-transposed, but they CAN be reordered:
   `chan` takes qwen e5m2 to **0.704 — ANS parity with UCCL-Zip's custom GPU codec (0.70)** through
   a commodity-decodable stream.
4. **Delta coding hurts.** `chan_bt_delta` regresses gpt2 (0.719 vs 0.697) and doesn't beat `chan_bt`
   where it helps (qwen 0.692 vs 0.671): within-channel exponent sequences are not smooth enough for
   delta to beat deflate's own LZ matching. Deploy candidate stays pure-permutation.
5. **TRACE's remaining gap is now priced.** Of TRACE's bf16 0.80→0.53 total win, the portion portable
   to a single deflate stream is 0.80→**0.671** (qwen). The remaining ~0.14 α requires their custom
   bit-plane entropy silicon — that is the measured **cost of commodity decode** vs TRACE.
6. Throughput: `chan_bt` ≈1450 MB/s single-thread numpy (vs byte_transpose 2800); still
   permutation-class — DPU-ARM/FPGA implementations are far faster. Inverse = strided copy, off-GPU.

## Third-model extension: Llama-3.1-8B (pre-registered rule, resolved 2026-07-06)

The extension rule was written into `EVALUATION_CONTRACT_M1.6.md` *before* the capture ran
(model fixed in advance: `NousResearch/Meta-Llama-3.1-8B`, the ungated mirror; identical harness
and parameters; agreement bound ±0.01 vs Qwen per dtype; re-register scoped to modern-architecture
KV iff agreement AND worst-of-modern clears the original thresholds). 288 rows, 0 bit-exact failures.

| dtype | Llama best | Qwen best | diff | outcome |
|---|---|---|---|---|
| fp8_e5m2 | **0.699** (chan) | 0.704 | 0.005 ✔ | **RE-REGISTERED: YELLOW (modern-arch scope), α\*=worst-of-modern=0.704** |
| bf16 | **0.690** (chan_bt) | 0.671 | 0.019 ✘ | NO re-registration (in-between zone; observation only) |

- **The registered narrow claim:** on modern-architecture (GQA/RoPE) KV, `chan` + single-stream
  deflate reaches **fp8_e5m2 α\*=0.704, BF3-decodable, bit-exact — ANS-parity with UCCL-Zip's
  custom-bitstream 0.70**. gpt2 (0.724) is reported as the measured architecture outlier.
- **bf16 is a gradient, not a split:** gpt2 0.697 > Llama 0.690 > Qwen 0.671. Both modern models
  individually clear the 0.695 YELLOW cutoff, but the 0.019 spread exceeds the pre-set agreement
  bound, so no bf16 claim is registered — the honest sentence is "the channel-major gain grows with
  architecture modernity", and M1.5's byte-transpose numbers remain the claimable bf16 α.
- Llama's K compresses better than its V (bf16 0.685/0.696) — the reverse of gpt2. Per-tensor
  structure is itself architecture-dependent; the gate never needs to know which, it measures.

## Implications for WR-ZipGuard

- **Claimable multi-model α stays M1.5's** (bf16 0.705–0.708, e5m2 0.731–0.732) under our own
  worst-model discipline. **Architecture-conditional** numbers (bf16 0.671, e5m2 0.704 on Qwen-class
  models) may be quoted with the explicit caveat, and modern serving models are Qwen-class, not
  gpt2-class — a plausible SHOULD follow-up is a third modern model (e.g. Llama-3.1-8B) to test
  whether gpt2 is the outlier; if it is, the criteria could be re-registered on modern-architecture KV.
- **M3 frontier (E3, `experiments/m3/m3_outputs/alpha_refresh.json`):** the band shift is real but
  modest and **does not change M3's YELLOW verdict** at any new α: B_crit@100Gbps-FPGA goes
  17.2 → 18.7 (M1.5 bf16) → 19.4 (worst-model M1.6) → **21.1 Gbps** (qwen-only); free-compressor
  ceiling 50 → 62 Gbps. Still a bandwidth-limited (cross-AZ / oversubscribed) play.
- **C2 intact:** everything here is one standard deflate stream; the receive side adds an inverse
  permutation (chan⁻¹ ∘ bt⁻¹), off-GPU-feasible; alignment constraint: chunks must be multiples of
  head_dim × itemsize (256 KB / 1 MB qualify for head_dim 64/128).

## Caveats / open items

- T_xform (now reorder + transpose) and the receive-side inverse remain **outside the break-even
  model**; inverse placement/throughput on the real target unmeasured (couples to M2's DPU-ARM block).
- fp8 captures still use the naive `astype` quantizer (M1.5 caveat, unchanged).
- ~~gpt2-vs-qwen disagreement rests on two models~~ **Resolved**: Llama-3.1-8B captured same day
  under the pre-registered extension → e5m2 claim re-registered on modern-arch scope; bf16 remains
  unregistered (gradient across architectures). A fourth model could tighten the bf16 question but
  no further capture is planned before M4a.

Code: `experiments/m1_6/` (69 unit tests) · results `m16_results.json`, `commodity_decode_cost.json`
· contract `refine-logs/EVALUATION_CONTRACT_M1.6.md` · frontier refresh
`experiments/m3/alpha_refresh.py` + `m3_outputs/alpha_refresh.json`.
