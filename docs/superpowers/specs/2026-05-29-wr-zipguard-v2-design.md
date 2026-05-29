# WR-ZipGuard v2 — Design Spec

**Date**: 2026-05-29
**Status**: approved (brainstorming)
**Supersedes**: the BF3-hardware-compress assumption in the original Workflow 1 artifacts

## Why this redesign exists

The original WR-ZipGuard assumed commodity **BF3 DOCA Compress** could compress LLM tensor
chunks on the sender side. The NVIDIA DOCA Compress documentation (2026) confirms BF3 supports
**decompression only** (deflate + LZ4 decompress); it exposes **no hardware compress operation**
(BF2 has deflate compress, BF3 does not). The literature review actually captured this fact
("BF3 deflate/LZ4 decompression support"), but later pipeline stages diluted it into a generic
"capability must be queried" risk, leaving an over-stated `feasibility=4/5` and `refine=9.0`.

A sender-side compression gate therefore has **no hardware fast path on BF3**. This spec rebuilds
the idea around what BF3 *can* do (hardware decompress) plus a custom/software compressor, and
de-risks the whole thing with a simulate-first go/no-go gate before any FPGA RTL is written.

## One-line thesis

In disaggregated LLM inference KV-cache transfer, a **per-work-request profitability gate** plus
**asymmetric execution** — sender compresses into a *standard* deflate/LZ4 bitstream, receiver
decompresses with **commodity BF3 hardware** — reduces KV transfer time in bandwidth-limited
regimes while a bypass-on-risk rule guarantees no regression elsewhere. The profitable region is
first proven in simulation parameterized by *measured* parameters, then realized on a 2–4 node
prototype.

## Contributions (and differentiation)

- **C1 — Profitability gate**: per-WR/chunk decision (`compress` vs `raw`) with bypass-on-risk,
  bit-exact restore, per-QP ordering. *NetZIP compresses everything with no gate.*
- **C2 — Asymmetric execution**: private/custom logic only on the compress side; the wire format is
  *standard* (deflate / LZ4 block) so a **commodity DPU hardware decompressor** can consume it.
  *NetZIP uses a private format on both ends; SplitZip/KVServe/KVCodec live entirely on the GPU and
  never touch the DPU/RDMA path.*
- **C3 — Design-space study (Phase-0 contribution)**: a realistic-parameter map of *when* KV
  transfer compression is profitable, parameterized by measured compression ratios and measured BF3
  decompress throughput. Doubles as motivation and as the negative-result fallback.

## Scope

- **Primary scenario (A)**: disaggregated inference KV-cache transfer (LLMServingSim; BF16/FP8 KV
  blocks; baselines SplitZip / KVServe / KVCodec / ShadowServe; metrics TTFT / TPOT / bytes-on-wire
  / p99).
- **Supplementary scenario (B)**: training gradient/activation transfer (SimAI; baselines
  NetZIP / DGC). Generalization check only — **not** a headline claim.

## Methodology — simulate-first, parameter-grounded

The simulation phase does **not** bind the compressor location. It injects an envelope
`(compression_ratio, compress_latency, decompress_latency, effective_bw)`, but **every parameter
must have a real source** (the guardrail that keeps this out of "assumed-gain" territory):

| Parameter | Source (no FPGA build required) |
|---|---|
| Compression ratio | **M1**: run deflate/LZ4/zstd on *real* KV/gradient/activation tensors |
| BF3 decompress throughput | **M2**: measured on the actual SmartNIC |
| Compress throughput envelope | NetZIP numbers + FPGA deflate IP datasheets (conservative band) |

Simulator caveat: SimAI and LLMServingSim do **not** natively model a compression engine; a
latency+byte-reduction model must be injected on the transfer path. Simulation results therefore
state **potential** benefit; the real prototype (M4b) states **realized** benefit.

## Milestones

| Milestone | Content | Go/No-Go gate |
|---|---|---|
| **M1** | Real KV (+gradient/activation) tensors → software compression-ratio distribution | Some phase exceeds ratio threshold, else stop |
| **M2** | BF3 hardware decompress throughput + cold/warm/staging microbench | Decompress is not the bottleneck |
| **M3** | LLMServingSim benefit sweep, injected with real envelope (M1 ratio + M2 decompress + FPGA-compress estimate) | **A bandwidth-limited profitable region exists = project-wide gate** |
| **M4a** | Software-compress + BF3-hardware-decompress prototype, 2–4 nodes | Mechanism correct, bit-exact, in-situ decompress throughput, gate overhead |
| **M4b** | Swap in FPGA compressor on same pipeline (reports throughput/area/timing — absorbs old M5) | **Real end-to-end KV speedup (headline)**, lands inside M3 envelope, projection error <15% |
| **M5** | Ablations: remove sampling / bypass / persistent context | Each component measurably matters |

B (training/SimAI) rides as a secondary workload axis in M3 and an optional check in M4b; it is not
a separate milestone.

## Why M4 is split

M4a uses **software** compression on purpose: it proves the *mechanism* (gate decisions,
bypass-on-risk, bit-exact restore, and crucially that a software-produced **standard** bitstream is
correctly and quickly decompressed by **commodity BF3 hardware**) in weeks, without gating on
6-month FPGA RTL. But software compress (~hundreds of MB/s) cannot saturate 100–400 Gbps line rate,
so the gate will correctly bypass most chunks — M4a yields a *correctness/safety* result, not a
*speedup* result. The headline speedup therefore requires the FPGA compressor (M4b), sequenced
after the M3 go/no-go so RTL never sits on the critical path to a publishable result.

## Non-goals

- No new compression algorithm (use standard deflate/LZ4 formats).
- No lossy compression.
- No NCCL/RDMA driver modification as the primary route.
- No ASIC tape-out.
- FPGA work (M4b) demonstrates realizability; it is not required to land in the RDMA datapath as the
  *only* result — M4a + M3 provide a publishable floor.

## Success condition

Real prototype reduces TTFT / KV transfer time in at least one bandwidth-limited regime, with no
p99 regression in no-gain regimes; simulation projection error <15%. If M3 finds no profitable
region, pivot honestly to a "commodity DPU KV compression profitability frontier" negative-result /
design-guidance paper (the C3 Phase-0 contribution backs this up).

## Open items deferred past design

- Target venue/timeline assumed NSDI/ASPLOS/MICRO-class, 3–6 months to first credible result.
- Exact hardware topology for M4b (FPGA SmartNIC on sender + BF3 on receiver) to be confirmed when
  M3 clears the gate.
