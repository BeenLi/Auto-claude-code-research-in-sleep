# E0 Report — Hardware-Encoder-Constrained α Pre-Check (ISCAS 2027 topic gate)

**Verdict: STRONG_GO** (2026-07-15, same-day as pre-registration; decision rule applied verbatim
by `analyze_e0.py`; user sign-off pending — to be recorded in
`refine-logs/EVALUATION_CONTRACT_E0.md` Status line).

E0 asked: do WR-ZipGuard's locked software-zlib α numbers survive the three constraints real FPGA
deflate encoders impose — level-1-class match search, static-vs-dynamic Huffman, independent 32 KB
blocks? If yes, Topic A (KV compression egress datapath on VCU118, ISCAS 2027) is technically
sound; if no, fall back to Topic B (PSP).

## E0a — Verdict table (captured KV, claim statistics per contract)

| path (claim scope) | V0 = zlib-6 whole-chunk | **V3 = HW-dyn proxy** (level-1 + 32 KB blocks) | Δ | gates (α≤0.75, Δ≤0.03) |
|---|---|---|---|---|
| bf16 `chan_bt` (worst-of-modern) | 0.690 | **0.708** | +0.018 | **pass** |
| fp8_e5m2 `chan` (worst-of-modern) | 0.704 | **0.721** | +0.017 | **pass** |
| bf16 `byte_transpose` (worst-of-all, conservative) | 0.709 | 0.726 | +0.017 | also passes |
| fp8_e5m2 `raw` (worst-of-all) | 0.732 | 0.750 | +0.018 | at the gate edge |

Hygiene: V0 reproduces every locked M1.5/M1.6 median within ±0.005 (`locked_reference.json`);
synthetic control shows zero chan gain (no artifact); 0 bit-exact failures across 312 captured +
384 synthetic rows; 61 unit tests.

## E0a — Decomposition (what hardware actually costs)

- **32 KB independent blocking is nearly free**: V2−V0 = +0.000…+0.004. The KV win needs no
  cross-block history — consistent with the entropy-coding (not LZ-match) mechanism.
- **Match effort is the whole penalty**: V1−V0 ≈ V3−V2 ≈ +0.02. Level-1-class hardware match
  engines are fine.
- **Static Huffman is catastrophic**: V4 lands at bf16 0.81 / e5m2 0.97–1.02 (V5 confirms it is
  the Huffman table, not blocking). **Dynamic Huffman is a measured hardware design requirement**
  — the Vitis dynamic-Huffman kernel class (2 GB/s/CU) is the right design point; the cheaper
  static-Huffman engines (Ledwon/Fowers class) are ruled out for KV.
- e5m2 raw hits exactly 0.750 under V3 → the `chan` transform becomes *more* necessary under
  hardware constraints (0.721 with, 0.750 without).

## E0b — NetZIP-algorithm on our KV corpus (positioning, no gate)

Port of the Zenodo artifact's algorithm (byte/bit-grouping + min-base delta), certified
byte-identical against their torch code (`check_netzip_equivalence.py`). Declared adaptations:
cross-iteration diff arms N/A for KV; min base = same buffer's 1st percentile.

| arm | invertible? | their LZ4-1 default | zlib-6 | vs ours |
|---|---|---|---|---|
| original (raw) | — | **1.000** (lz4 no-op on KV; reconfirms M1/NE-2) | 0.799–0.800 | our raw same |
| byte_grouped | yes (== our byte_transpose) | 0.846–0.851 | **0.705–0.709 — identical to our M1.5 numbers** (mechanism cross-validated) | tie under deflate; collapses under their codec |
| bit_grouped | yes | 0.764–0.796 | 0.705–0.745 | never better than byte_grouped |
| diff_min_* | **NO — 61.7% of values fail best-effort recovery; 26.2% carry >1% relative error** (float32 subtract of percentile base, re-cast bf16 = quantization in disguise) | 0.523–0.668 | 0.492–0.656 | not claimable by any bit-exact path |

**Positioning yield**: (1) NetZIP's only KV-applicable *lossless* arms match-or-lose to our
pipeline, and no channel-major arm exists — our chan/chan_bt 0.671–0.704 strictly beats them;
(2) their level-1 LZ4 codec class collapses on KV without deflate-class entropy coding —
the "lightweight codec + transform" recipe does not transfer from gradients to KV;
(3) their artifact's biggest KV "win" (diff_min ~0.49–0.55) is not lossless — quote with the
invertibility numbers. Caveat for the paper: this characterizes the *Zenodo artifact's* ratio
arms; before submission, verify against the paper text whether their hardware per-packet
min-base delta is integer (invertible) or float (this arm) — scope the claim accordingly.

## Consequences

- **Topic A locked (pending sign-off)**: hardware-α story survives; the paper must quote V3-class
  α (0.708/0.721) rather than software zlib-6 α, and B_crit refreshes accordingly
  ((1−α): 0.310→0.292 bf16, 0.296→0.279 e5m2 — a ~6% frontier haircut, well inside the pre-registered
  tolerance).
- **Design constraints for the RTL phase (W2–4)**: dynamic-Huffman deflate engine (Vitis DCL class);
  32 KB independent blocks are architecturally free to exploit for per-block parallelism;
  chan reorder engine is mandatory for the fp8_e5m2 path.
- E0b table = the "compression-ratio comparison" row block for the paper's Table 3.

## Reproduce

```bash
# myDevbox, venv ../m1/.venv, HF offline from cache
PYTHONPATH=../m1:../m1_5:../m1_6 python run_e0.py synthetic --out e0_outputs/e0_synth.jsonl --seq-lens 8192 --seeds 42,43
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=../m1:../m1_5:../m1_6 python run_e0.py capture --model gpt2 --out e0_outputs/e0_gpt2.jsonl   # + Qwen/Qwen2.5-7B, NousResearch/Meta-Llama-3.1-8B
python analyze_e0.py --corpus e0_outputs/e0_*.jsonl --reference locked_reference.json --out e0_outputs/e0_verdict.json
python check_netzip_equivalence.py netzip_artifact/compression_ratio_calculation/compression_ratio_calculation.py
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=../m1:../m1_5:../m1_6 python run_netzip.py --model gpt2 --out e0_outputs/netzip_gpt2.jsonl  # + qwen, llama
```
