# Research Contract: WR-ZipGuard (v2 — asymmetric, simulate-first)

> Focused working context for the currently selected idea. Read this before resuming Workflow 1.5.
> v2 supersedes the BF3-hardware-compress assumption; see
> `docs/superpowers/specs/2026-05-29-wr-zipguard-v2-design.md`.

## Selected Idea

- **Description**: WR-ZipGuard is a per-work-request profitability gate for LLM KV-cache transfer in
  disaggregated inference, executed **asymmetrically**: the sender compresses a chunk into a
  *standard* deflate/LZ4 bitstream only when profitable, and the receiver decompresses it with
  **commodity BF3 hardware**. A simulate-first study, parameterized by measured compression ratios
  and measured BF3 decompress throughput, proves a profitable region exists before any FPGA is built.
- **Source**: `idea-stage/IDEA_REPORT.md` (Idea 1), redesigned 2026-05-29 after confirming BF3 is
  hardware-decompress-only.
- **Selection rationale**: Keeps the defensible parts of the original idea (the gate, the
  RDMA-safe execution) while removing the broken premise (BF3 sender-side hardware compression). The
  asymmetric "custom/software compress + commodity DPU hardware decompress, standard format" framing
  is the cleanest differentiator from NetZIP (full-custom both ends, no gate) and from
  SplitZip/KVServe/KVCodec (GPU-side, no DPU/RDMA gate).

## Core Claims

1. **C1 — Gate**: A per-WR/chunk profitability gate with bypass-on-risk captures profitable BF3/RDMA
   KV compression opportunities while never regressing p99 on unprofitable chunks, with bit-exact
   delivery and preserved per-QP ordering.
2. **C2 — Asymmetric execution**: A sender-side compressor emitting a *standard* deflate/LZ4
   bitstream can be decompressed by **commodity BF3 hardware** correctly and at useful throughput;
   this commodity-decompress path is the structural novelty over NetZIP.
3. **C3 — Profitability frontier**: A realistic-parameter simulation (real compression ratios + real
   BF3 decompress throughput) identifies the bandwidth-limited regime where KV compression is
   profitable, and a real 2–4 node prototype lands within 15% of that projection.

## Method Summary

WR-ZipGuard has three pieces. **(1) A measured profitability frontier**: software-measured
compression ratios on real KV/gradient/activation tensors plus measured BF3 hardware decompress
throughput feed a simulator sweep that maps where KV compression beats raw transfer. **(2) A
sender-side gate**: for each chunk it estimates whether compression saves more wire time than it
costs (sample + compress + metadata + decompress + copy-out), and compresses only when a
conservative lower bound on gain is positive; otherwise it sends raw (bypass-on-risk). **(3)
Asymmetric execution**: the sender emits a standard deflate/LZ4 bitstream; the receiver decompresses
with commodity BF3 hardware, restores bit-exact bytes to the registered region, and per-QP sequence
numbers preserve ordering.

The first prototype targets vLLM/Mooncake-like KV-transfer boundaries. The compressor is **software
in M4a** (proves mechanism + the commodity-decompress path) and an **FPGA compressor in M4b**
(provides the measured end-to-end speedup), sequenced after the simulation go/no-go.

## Experiment Design Pointer

- **Plan**: `refine-logs/EXPERIMENT_PLAN.md`
- **Baselines**: raw RDMA/NCCL KV transfer; static always-compress; static size threshold;
  SplitZip/KVServe/KVCodec numbers as contextual baselines when reproducible; NetZIP/DGC for the
  supplementary training workload.
- **Metrics**: TTFT, TPOT, exposed transfer latency, p99 latency, bytes-on-wire, compression ratio,
  false-positive compression rate, BF3 decompress throughput, bitwise correctness.
- **Execution note**: Detailed run order lives in `refine-logs/EXPERIMENT_TRACKER.md`.

## Claim Boundary

Supported now: the redesigned idea is feasible enough to enter the simulate-first phase. Current
evidence supports planning, not performance claims.

Not supported yet: any claim that BF3 compresses (it does not — decompress only); any end-to-end KV
speedup number; any claim that software compression saturates line rate (it does not — the speedup
requires the FPGA compressor); any claim of full transparent one-sided GPUDirect compression.

Evidence required to strengthen claims: real tensor compression ratios (M1), BF3 decompress
microbench (M2), a simulator profitable region under real parameters (M3), a bit-exact prototype
through the commodity BF3 decompress path (M4a), and a measured FPGA-compressor end-to-end speedup
(M4b).

Novelty/competitive risk: next-gen **BF4** may add hardware compress, which would erode the
"commodity decompress only, custom compress" framing — scope the contribution explicitly to the
**BF3 commodity install base** and treat BF4 as future work, not a threat to the BF3 result.

## Current Evidence Status

- Literature review complete with 18 verified candidate papers, plus a post-run update (LITERATURE_REVIEW.md
  Section 1b) adding ZipCCL (2604.27844), UCCL-Zip (2604.17172), HACK (2502.03589, lossy), and
  NVIDIA ICMSP/BF4/NIXL/Dynamo (CES 2026).
- **Confirmed externally**: NVIDIA DOCA Compress docs (2026) — BF3 supports deflate/LZ4
  *decompression* only, no hardware compress operation. This invalidated the v1 sender-side
  hardware-compress assumption.
- Idea redesigned to the asymmetric, simulate-first form; design spec written and approved.
- **Novelty check done** (search-grounded, 2026-05-29; trace
  `.aris/traces/novelty-check/20260529_wr-zipguard-v2/report.md`): overall **~5–6/10, PROCEED WITH
  CAUTION**. Per-claim — C2 asymmetric/commodity-BF3-decompress path **MEDIUM-HIGH** (no prior
  lossless KV work uses commodity DPU hardware decompress); C1 per-WR gate **LOW alone / MEDIUM in
  combination** (adaptive "when not to compress" is decades old; novelty is RDMA-WR granularity +
  tensor-aware sampling + measured BF3 frontier); C3 RDMA-WR-granular bit-exact preservation
  **MEDIUM**.
- **Codex gpt-5.5 cross-model verdict folded in** (2026-06-12, xhigh; full text in the novelty
  trace): **5/10, PROCEED WITH CAUTION** — slightly harsher. C1 downgraded to **LOW** (KVServe
  already adapts when/how to compress KV), C2 downgraded to **MEDIUM** (novelty is
  deployment/integration; DOCA staging weakens "transparent RDMA" claims), C3 **MEDIUM**. Strongest
  drafted attack: "assembly of known pieces" (SplitZip + UCCL-Zip + KVServe + PEDAL + ShadowServe),
  reducible to "a measured staging shim with a cost model". Positioning survives narrowly only if
  the paper leads with the honest negative result. ShadowServe and UCCL-Zip flagged as
  underweighted attack surfaces.
- **ICMSP/NIXL positioning verified against primary sources** (2026-06-12, deep-research, 14 claims
  confirmed 3-0): NVIDIA press release + developer blog + CMX product page describe BF4's KV-pipeline
  accelerators as crypto/CRC only — no hardware compression engine and no compression step anywhere
  in the Dynamo/NIXL/CMX KV path; NIXL BackendGuide.md and a repo code/issue search show zero
  data-plane compression. The "they move bytes, no lossless compression, no per-WR gate" claim is
  **confirmed** (caveat: absence of public evidence, not formal proof; recheck before submission).
  Bonus finding: NIXL's pluggable backend architecture (SB API + Plugin Manager) supports framing
  WR-ZipGuard as a *pluggable gate on the NIXL transfer path* rather than a competitor.
- **M1 first signal obtained** (2026-06-15, myDevbox; `refine-logs/EXPERIMENT_LOG.md`):
  preliminary synthetic sweep (7B, 1728 rows, 0 bit-exact failures) → **provisional GREEN but
  narrow**. Of the two BF3-decompressible codecs, **only deflate compresses KV (~0.72–0.84); lz4 is a
  no-op (~1.0)** — the expected entropy-coding-vs-match-only split, corroborating NE-2/NetZIP. The
  synthetic generator is **cross-validated against real gpt2 KV (40/40 configs match, incl.
  fp8_e5m2)**, so the ratios are trustworthy. **GREEN confirmed on real KV**: fp8_e5m2 deflate-6/9
  lands at ~0.73 on real gpt2 KV (syn 0.715), below the 0.75 ceiling. **But** the software deflate
  throughput at that ratio is only ~17 MB/s, so by the break-even math software compression never
  pays at any real link rate — M1 establishes the *ratio* exists; realizing it needs hardware-speed
  compression (M4b FPGA), which is the project thesis. Consequence for design: the asymmetric path is
  **deflate-only** (lz4≈no-op on KV); M2 benches BF3 **deflate** decompress; M3's frontier uses
  deflate ratios with an FPGA-speed compress band.
- **Profitability is dtype-gated by byte entropy** (2026-06-15 sweep): the <0.75 ratio exists only for
  low-entropy KV. FP8_E5M2 (2 mantissa bits, byte entropy 5.49, floor 0.686, deflate 0.716) clears;
  FP8_E4M3 (~0.82) and **BF16 — the *default* KV dtype — provably cannot** (order-0 entropy floor
  **0.773 > 0.75**; even big-window zstd-22 only reaches 0.777, flat across chunks 64K–16M and seq
  1K–128K). So WR-ZipGuard's profitable regime is **FP8_E5M2 KV transfer specifically** — a real but
  specific slice of serving. This is the measured, dtype-resolved negative-result map (with a provable
  BF16 impossibility) to lead the paper with. Open question the contribution must address: the most
  *bit-exact-motivated* dtype is arguably BF16 (accuracy-sensitive, can't quantize), yet BF16 can't be
  profitably compressed — so frame the niche as FP8_E5M2 deployments that need bit-exact wire savings.
- Largest remaining evidence gap: validate fp8_e5m2, run the full M1 grid (+zstd, larger seq/chunks),
  then BF3 decompress microbench (M2) and the simulator profitable region (M3).

## Key Decisions

- **BF3 is decompress-only** → drop sender-side BF3 hardware compression; adopt asymmetric execution
  (custom/software compress + commodity BF3 hardware decompress, standard bitstream format).
- **Simulate-first** → prove the profitable region in LLMServingSim under *measured* parameters
  before committing to FPGA RTL; this is the project-wide go/no-go (M3).
- **Split M4** → M4a software compress (mechanism + decompress path, weeks) decoupled from M4b FPGA
  compress (headline speedup, contingent on M3 green); RTL never sits on the critical path.
- **Primary = inference KV (A), supplementary = training (B)**.
- **No new codec** → use standard deflate/LZ4 so the commodity decompressor applies; novelty is the
  gate + asymmetric execution, not the codec.
- **Novelty positioning (from novelty check)** → lead the paper with the *measured negative result*
  (when commodity-DPU KV compression does NOT pay) + the gate, not "another lossless KV codec".
  Frame the deployability delta explicitly: commodity BF3 decompress, no custom HW both ends (vs
  NetZIP). Vs NVIDIA ICMSP/NIXL: "they move KV bytes off-GPU over RDMA; we decide *which* bytes are
  worth compressing and do it bit-exact on the same commodity DPU path." The biggest review risk is
  an "ICMSP/NIXL already move KV + UCCL-Zip already does lossless comm compression ⇒ incremental"
  framing; the asymmetric-commodity-decompress angle + the gate are the defensible core.
- **Positioning refinements from the Codex cross-model verdict (2026-06-12)** → (1) do **not** sell
  the gate (C1) as novelty — it is the mechanism; the publishable contribution is the measured
  profitability frontier / negative-result atlas + the deployability gap vs custom HW and GPU-side
  codecs; (2) frame WR-ZipGuard as a **NIXL-compatible data-reduction gate** (NIXL has a pluggable
  backend architecture), not a competing KV-movement architecture; (3) candidate paper identity:
  "the BF3 commodity decompression profitability atlas for LLM KV transfer, with a conservative
  WR-level bypass gate and bit-exact NIXL/RDMA-compatible execution"; (4) treat ShadowServe and
  UCCL-Zip as first-class related work to defuse, alongside NetZIP/ICMSP.

## Immediate Research Gate

Run M1–M3 from `refine-logs/EXPERIMENT_PLAN.md`: real-tensor compression ratios, BF3 decompress
microbench, and the LLMServingSim profitability sweep. Do not build the FPGA compressor or claim any
speedup until M3 shows a bandwidth-limited profitable region under realistic parameters. **Step 1
(M1, software compression-ratio measurement) is the cheapest go/no-go and runs first.**
