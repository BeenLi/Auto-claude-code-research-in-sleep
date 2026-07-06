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
- **Confirmed on real BF3 hardware** (2026-06-16, `bf3_server`, DOCA 2.9): `doca_caps` reports
  `task_compress_deflate=unsupported`, `task_decompress_deflate/lz4_stream/lz4_block=supported`
  (2 MB/task). **C2 correctness proven**: the BF3 hardware engine decompresses real FP8_E5M2 KV
  compressed with **stock `zlib.compress()`** (and raw deflate) **bit-exactly** — the asymmetric
  "standard compressor → commodity-DPU hardware decompress" path works on silicon.
- **M2 throughput measured (doca_bench) — red-line verdict GREEN** (2026-06-16): BF3 deflate
  decompress saturates at a **~170–175 Gib/s (~23 GB/s ≈ 188 Gbps) engine ceiling**, reachable from
  a single host core with deep queue (pipelining gives an 8× jump over single-shot — red line 3 is
  real and required). D_eff is chunk-gated: 256 KB → 141 Gbps, 1 MB → 180, 2 MB → 188; tiny chunks
  (≤4 KB → 6.5 Gbps) are hopeless. So BF3 decompress does **not** bottleneck KV transfer at the
  ≤100 Gbps target for **chunks ≥256 KB** (red lines 1+2 clear). **Design constraint surfaced**: the
  per-WR gate must **aggregate KV into ≥256 KB chunks** and keep the pipeline full. Caveats: this is
  decompress-only (sender still needs the M4b FPGA) and engine-throughput in host memory — the full
  in-RDMA-pipeline D_eff incl. staging/copy-out (the "staging shim" exposed cost) needs M4a. D_eff(chunk)
  handed to M3 as the measured decompress parameter.
- **Scaling ceiling — likely PCIe-x8 artifact, attribution pending** (2026-06-16, corrected): the
  ~188 Gbps egress ceiling does not scale with parallel contexts (4 contexts = 4×42.6 = 170 Gib/s = 1),
  so the 4 share one bottleneck — but `lspci` shows the BF3 link is **Gen5 x8 (downgraded from x16)**
  ≈27 GB/s practical/dir, and our egress 23.5 GB/s is ~87% of it, so **the bottleneck is most likely the
  host PCIe write-back, not the decompress silicon**. Earlier "hard engine ceiling / can't match 400 G
  NIC" was an over-claim → it is a *system* ceiling under host-memory + x8-slot integration; on a x16
  slot or with DPU-local memory the ceiling could be ~2× higher (~376 Gbps), widening the profitable
  bandwidth region. **Resolve via the host-vs-DPU-memory test** (planned M2 dimension, skipped; needs DPU
  ARM access — rshim present on bf3_server, tmfifo/SSH not yet configured). Scope conclusion holds *for
  this setup*: compression pays when path bottleneck `B < D_eff_out ≈ 188 Gbps` (full 1.4× below ~135),
  WR-ZipGuard targets bandwidth-limited (not line-rate-saturated) flows; profitable region triply bounded
  **FP8_E5M2 × path-BW < ~188 Gbps (possibly x8-limited) × chunk ≥256 KB**.
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
- **Profitability is dtype-gated by byte entropy** (2026-06-15; validated across synthetic + gpt2 +
  **Qwen2.5-7B**, generator 30/30 on Qwen): the <0.75 ratio exists only for low-entropy KV, and deflate
  achieves ≈ the order-0 entropy floor in every case. On real Qwen2.5-7B KV: **FP8_E5M2** deflate 0.732
  (entropy floor 0.730) **clears**; **FP8_E4M3** 0.837 (floor 0.838) and **BF16 — the *default* dtype**
  0.802 (floor 0.792) **provably cannot** — their byte entropy alone exceeds the ceiling, so no codec
  (zstd-22 big window confirmed) and no chunk size (flat 64K–16M) / seq length (1K–128K) helps.
  Nuance: it is **not** "FP8 compresses better" — FP8_E4M3 is the *least* compressible; specifically
  **FP8_E5M2's 2-bit mantissa** yields the low-entropy byte stream. WR-ZipGuard's profitable regime is
  thus **FP8_E5M2 KV transfer specifically** — a real but specific slice of serving; this is the
  measured, dtype-resolved negative-result map (with a provable BF16 impossibility) to lead the paper.
  Open framing tension: the most *bit-exact-motivated* dtype is arguably BF16 (accuracy-sensitive,
  can't quantize), yet BF16 can't be profitably compressed — so scope the niche to FP8_E5M2 deployments
  needing bit-exact wire savings.
- **M1.5 float-split preprocessing GREEN** (2026-06-25; `experiments/m1_5/`, 49 unit tests;
  `refine-logs/EVALUATION_CONTRACT_M1.5.md`): a cheap reversible **byte-transpose before deflate**
  (SoA 2-byte de-interleave, kept as ONE standard deflate stream BF3 decompresses) **rehabilitates
  BF16 — the default KV dtype — from raw 0.79–0.80 to ~0.70** on real gpt2 (0.705) + Qwen2.5-7B
  (0.708) KV, crossing the 0.75 gate. The win is entirely the exponent plane (high byte → ~0.40; low
  byte + mantissa ~1.0). The split does NOT help fp8 (byte-transpose is a 1-byte no-op; bit-split
  makes deflate worse); fp8_e5m2 keeps its raw path. Widens the **dtype set** (BF16 default → high
  applicability), NOT the M3 **bandwidth region** (bf16 ~30% wire saving ≈ e5m2 ~27%). Open:
  receive-side un-transpose must run off-GPU (host/DPU-ARM), T_xform not yet in the break-even model.
- **M3 profitability frontier YELLOW** (2026-06; `experiments/m3/`, 46 unit tests, M3_REPORT.md):
  for the measured envelope (e5m2 α=0.732, 2MB chunks), compression pays only for B < 5.9/10.5/17.2
  Gbps at 25/50/100 Gbps FPGA compress bands; **hard ceiling ~50 Gbps** even with a free compressor
  (α≈0.73 → only 27% wire saving). LLMServingSim cross-check PASS (TTFT ∝ bytes/link_bw, R²=1.0).
  Verdict: real but narrow bandwidth-limited region (cross-AZ/oversubscribed/WAN-ish), not
  mainstream 100–400 Gbps DC.
- **Literature refresh 2026-07-06** (three parallel web sweeps + primary-source verification; full
  table in `LITERATURE_REVIEW.md` Section 1c). Headlines: **(1) TRACE** (arXiv 2509.03377, IEEE TC)
  achieves **lossless BF16 KV α≈0.53** via channel-major disaggregated bit-plane layout — in custom
  CXL-controller silicon. Threat: order-0 byte entropy after byte-transpose is NOT the floor;
  channel-major reordering exploits structure we haven't tapped. Opportunity: it is a pure layout
  permutation, so it may port to our single-standard-deflate-stream/BF3 constraint → **M1.6 tests
  this** (pre-registered: GREEN if bf16 ≤0.65 or e5m2 ≤0.70 on captured KV). **(2) Custom-decoder
  ceilings quantified**: UCCL-Zip v2 (ANS, custom bitstream) reports bf16 0.64 / e5m2 0.70 / e4m3
  0.77 — our commodity-decodable α pays only +0.06/+0.03/+0.05 vs it; **SplitZip v3's BF16 ratio is
  1.324× (α≈0.755, and e5m2 only 1.14×=0.877) — WORSE than our 0.70/0.73** despite its 613/2182 GB/s
  GPU throughput. **(3)** New lossy/verified alternatives to defuse: SpectrumKV (per-token mixed
  precision for PD transfer), VeriCache (lossy draft + full-KV verify ⇒ bit-identical outputs),
  KVTC (PCA+quant+deflate, storage). **(4)** Exponent-coding lineage grew: DFloat11 (NeurIPS'25),
  Unweight (Cloudflare, top-16 exponent palette), Huff-LLM — all weights, all custom decoders; and
  **ECF8 (2510.02676) gives THEORY** (α-stable SGD ⇒ provably low exponent entropy) that elevates
  our measured exponent-plane floors to a principled claim. **(5) Gate still unclaimed**: nearest new
  work is NetSenseML (congestion-reactive lossy gradient compression, training) and CIDR'26 "Waiting
  to Decompress" (LLMs-as-text-compressors storage economics, ~10yr break-even) — neither does
  per-transfer, bit-exact, measured-frontier profitability gating. **(6) Ecosystem**: BF4 still shows
  NO hardware compress engine (re-verified; recheck at DOCA 3.x GA); no production lossless KV
  compression in vLLM/SGLang/Mooncake/NIXL/LMCache as of 2026-07 — precise form (second pass, same
  day): what IS merged is lossy (LMCache's only codec is CacheGen, quant+entropy coding; vLLM ships
  FP8 KV quantization; SGLang HiCache is tiering with no codec; KVTC→Dynamo KVBM is
  announced-not-shipped and lossy overall), while the lossless GPU codecs (DietGPU, UCCL-Zip,
  SplitZip, ZipNN, TRACE) are all unmerged research; CXL substrate competition rising
  (TraCT, SAC, CXL-SpecKV) → keeps our positioning on multi-rack bandwidth-constrained fabrics.
- **M1.6 channel-major layout RED (pre-registered), architecture-dependent gain** (2026-07-06, same
  day as the refresh; `experiments/m1_6/`, 69 unit tests; tracker R015): TRACE's channel-major
  mechanism ported to ONE standard deflate stream gives a **real gain only on the modern model** —
  Qwen2.5-7B bf16 0.708→**0.671** (chan_bt), fp8_e5m2 0.732→**0.704** (chan; first fp8 transform win,
  ANS-parity with UCCL-Zip 0.70) — while gpt2 improves only 0.008/0.007, so the pre-registered
  worst-model rule lands RED (missed YELLOW by 0.002/0.004; spreads 0.025/0.020 > 0.01 agreement
  bound). Synthetic control: zero chan gain (no artifact). Delta coding hurts. **TRACE gap priced**:
  portable share of its 0.80→0.53 is 0.80→0.671; the remaining ~0.14 α is its custom silicon
  (`experiments/m1_6/commodity_decode_cost.json`). **M3 frontier stays YELLOW at every new α**
  (B_crit@100G 17.2→≤21.1 Gbps; ceiling 50→62 Gbps; `experiments/m3/m3_outputs/alpha_refresh.json`).
  Claimable multi-model α remains M1.5's; qwen-only numbers quoted as architecture-conditional.
  **Third-model extension resolved same day (Llama-3.1-8B, rule pre-registered before capture):
  e5m2 chan 0.730→0.699 agrees with Qwen (±0.005) → gpt2 confirmed the outlier → RE-REGISTERED
  narrow claim: fp8_e5m2 YELLOW on modern-architecture (GQA/RoPE) KV, α\*=worst-of-modern=0.704,
  BF3-decodable single deflate stream, ANS-parity with UCCL-Zip's custom codec (0.70). bf16 NOT
  re-registered — Llama 0.690 clears YELLOW individually but sits 0.019 from Qwen (gradient
  0.697/0.690/0.671, not a clean split); claimable bf16 stays M1.5's byte-transpose 0.705–0.709
  (now three-model). All-models M1.6 verdict stays RED.**
- Largest remaining evidence gap: M4a in-pipeline prototype (staging cost, off-GPU inverse
  placement — now chan⁻¹∘bt⁻¹) and M4b FPGA compress for the measured end-to-end speedup; SHOULD:
  third-model M1.6 capture, T_xform in the break-even model.

## Key Decisions

- **BF3 is decompress-only** → drop sender-side BF3 hardware compression; adopt asymmetric execution
  (custom/software compress + commodity BF3 hardware decompress, standard bitstream format).
- **Simulate-first** → prove the profitable region in LLMServingSim under *measured* parameters
  before committing to FPGA RTL; this is the project-wide go/no-go (M3).
- **Split M4** → M4a software compress (mechanism + decompress path, weeks) decoupled from M4b FPGA
  compress (headline speedup, contingent on M3 green); RTL never sits on the critical path.
- **Primary = inference KV (A); training (B) deferred out of M1** (decided 2026-06-16). Near-term work
  scopes to inference KV only: dense training tensors are near-tautological at the same BF16 entropy
  floor, capturing real ones needs a full training loop (forward+backward+optimizer), and training is
  NetZIP's turf — handled as a *parameterized M3 comparison* using NetZIP's reported numbers, not
  measured here. Revisit only if the paper needs the SimAI appendix (then a small synthetic probe,
  incl. the GELU/SwiGLU activation-sparsity question, not a full axis).
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
- **Positioning refinements from the 2026-07-06 literature refresh** →
  (1) **TRACE joins ShadowServe/UCCL-Zip as a first-class attack surface**. Defusal line: "TRACE
  needs new CXL-controller silicon at the receiver; we constrain to a single standard deflate
  stream that already-shipped BF3s decode in hardware — and M1.6 measures how much of TRACE's
  channel-major layout gain survives that commodity constraint." Either M1.6 outcome feeds the
  paper: GREEN widens the frontier; RED becomes the measured "cost of commodity decode".
  (2) **Reframe the codec story**: exponent entropy coding is now commodity knowledge (DietGPU,
  ZipNN, DFloat11, Unweight, SplitZip, UCCL-Zip, ECF8's theory). Our contribution is explicitly NOT
  a codec — it is (a) *where* to decode (shipped commodity DPU hardware, zero receiver GPU/SM cost,
  zero new silicon) and (b) *when* to bother (the measured per-WR break-even frontier with
  bypass-on-risk). Lead with those two questions; cite ECF8 to make the exponent-plane floors
  principled rather than empirical.
  (3) **Gate-novelty delta, sharpened against the two nearest neighbors** (E4): NetSenseML gates
  *lossy gradient* compression during *training* by reacting to congestion heuristics; CIDR'26
  "Waiting to Decompress" prices *LLMs-as-text-compressors* for cold *storage* over multi-year
  horizons. WR-ZipGuard's gate decides per RDMA work request, on a *bit-exact* path, from a
  *measured* device frontier (compress band × D_eff(chunk) × α(dtype) × link state) with a
  conservative bypass — per-transfer wire-time profitability gating on a real DPU decompress path
  remains unclaimed in the literature (three independent sweeps concur, 2026-07-06).
  (4) **Quote SplitZip v3's numbers in related work**: its custom GPU codec reaches only α≈0.755
  (bf16) / 0.877 (e5m2) vs our BF3-decodable 0.70 / 0.73 — the "fast custom codec" does not
  dominate the ratio axis; it trades ratio for GPU throughput, reinforcing the off-GPU niche.
  (5) **Lossy/verified alternatives get one shared defusal paragraph** (SpectrumKV, VeriCache,
  KVTC, EVICPRESS, HACK): all either change bytes (accuracy governance burden) or spend receiver
  GPU compute (VeriCache draft+verify); WR-ZipGuard is bit-exact on the wire with the receiver GPU
  untouched — and it composes with them (a gate can front any of these as the lossy tier).
  (6) **CXL substrate risk** (TraCT, SAC, CXL-SpecKV): concede the rack; keep the multi-rack /
  cross-AZ / oversubscribed regime — which is exactly M3's measured profitable region anyway.
  (7) **State the ecosystem-gap claim in its precise, attack-proof form** (2026-07-06 second
  verification pass, prompted by "haven't the GPU-codec papers been merged?"): GPU-compression
  papers HAVE merged into production stacks — but everything merged is **lossy** (LMCache/CacheGen
  is its docs' only codec, quant+entropy coding; vLLM's native path is FP8 KV quantization;
  KVTC→Dynamo KVBM is announced 2026-03 but not shipped, and lossy overall). What has never shipped
  is *bit-exact lossless* KV compression in any serving/transfer stack; the lossless codecs
  (DietGPU, UCCL-Zip, SplitZip, ZipNN, TRACE) are all unmerged research. Write it as **"what ships
  is lossy; lossless remains unshipped"**, never as "no KV compression in production". Watch item:
  if NVIDIA lands KVTC/nvCOMP-deflate in Dynamo KVBM, deflate-on-KV becomes mainstream practice —
  that *helps* the narrative (deflate legitimized on KV) and does not touch the transfer-side
  bit-exact gate; re-check before submission.

## Immediate Research Gate

Run M1–M3 from `refine-logs/EXPERIMENT_PLAN.md`: real-tensor compression ratios, BF3 decompress
microbench, and the LLMServingSim profitability sweep. Do not build the FPGA compressor or claim any
speedup until M3 shows a bandwidth-limited profitable region under realistic parameters. **Step 1
(M1, software compression-ratio measurement) is the cheapest go/no-go and runs first.**
