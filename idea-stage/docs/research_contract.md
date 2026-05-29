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

## Current Evidence Status

- Literature review complete with 18 verified candidate papers.
- **Confirmed externally**: NVIDIA DOCA Compress docs (2026) — BF3 supports deflate/LZ4
  *decompression* only, no hardware compress operation. This invalidated the v1 sender-side
  hardware-compress assumption.
- Idea redesigned to the asymmetric, simulate-first form; design spec written and approved.
- Largest remaining evidence gap: real tensor compression ratios and the simulator profitable region.

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

## Immediate Research Gate

Run M1–M3 from `refine-logs/EXPERIMENT_PLAN.md`: real-tensor compression ratios, BF3 decompress
microbench, and the LLMServingSim profitability sweep. Do not build the FPGA compressor or claim any
speedup until M3 shows a bandwidth-limited profitable region under realistic parameters. **Step 1
(M1, software compression-ratio measurement) is the cheapest go/no-go and runs first.**
