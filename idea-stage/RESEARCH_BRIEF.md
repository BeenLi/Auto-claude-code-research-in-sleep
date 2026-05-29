# Research Brief: In-RNIC Lossless Compression Engine for LLM Cross-Machine Communication

> Input document for `/idea-discovery` or `/research-pipeline`.

---

## Problem Statement

Distributed LLM training and inference increasingly rely on high-speed RDMA fabrics (InfiniBand / RoCE) to move tensors across machines. As model scale grows, cross-machine communication has become a first-order bottleneck: in tensor-parallel and pipeline-parallel training, all-reduce collective operations over gradients and activations can consume 30–60% of total step time at 100B+ parameter scale. In inference disaggregation (prefill/decode split), KV cache migration across nodes adds latency spikes that directly degrade SLO attainment. Even at 400 Gb/s HDR/NDR, the sustained all-reduce and KV-transfer demands of large-scale LLM workloads saturate the available link bandwidth within each computation step, leaving communication as the dominant bottleneck.

Current compression approaches offload the compression work to the CPU or GPU before issuing RDMA send operations. This has two compounding costs: it occupies GPU SMs or CPU cores that should be doing compute, and it forces the full tensor to be materialized in CPU-accessible memory before transmission (breaking zero-copy RDMA semantics). DPUs such as BlueField-3 sit on the wire between the host and the fabric, providing a natural interception point for compression without stealing GPU or CPU cycles. Critically, BlueField DPUs already contain a dedicated hardware **C-engine** (compression accelerator) alongside the ARM SoC cores — the C-engine is not software running on ARM; it is a fixed-function hardware block that can accelerate DEFLATE, zlib, and LZ4 at hardware throughput, achieving up to 26.8× speedup over CPU baselines. The design space for a codec engine therefore spans three tiers: (1) the built-in C-engine (available today, limited to supported algorithms); (2) a custom FPGA bitstream co-located with or replacing the C-engine path (more algorithm flexibility, line-rate capable); and (3) a dedicated ASIC integrated into the NIC data path (highest throughput, lowest latency, longest lead time).

The opportunity is to design a **RDMA-transparent lossless compression engine on the DPU** that intercepts tensor traffic at the RNIC level, applies lossless compression, transmits a smaller payload over the wire, and decompresses at the remote DPU before delivering to the target HBM or DRAM — all without modifying the application or RDMA stack semantics. The key research questions are: (1) which communication patterns in LLM training/inference have sufficient compressibility under lossless constraints to justify on-path compression overhead; (2) which lossless algorithms (LZ4, Zstd, ANS, etc.) achieve acceptable throughput at DPU line rates given BF3's ARM core count and DRAM bandwidth; and (3) how does lossless compression interact with RDMA ordering guarantees and collective semantics (e.g., SHARP in-network reductions).

---

## Background

- **Field**: Computer Architecture / Systems / Networking
- **AI infra layer**: Interconnect/network + compute/accelerator co-design
- **Sub-area**: NIC/DPU compression, LLM distributed training/inference, RDMA fabric optimization
- **Hardware bottleneck**: RDMA link saturation; NIC Rx/Tx buffer pressure under sustained all-reduce and KV-cache migration traffic; C-engine/FPGA/ASIC codec throughput vs. line rate; DOCA initialization and buffer staging overhead dominating end-to-end compression latency (known from prior characterization: 90.4% of compression time is system overhead, not the algorithm itself)

- **Key papers I've read**:
  - **Efficient Remote KV Cache Reuse with GPU-native Video Codec**: uses GPU-side video codec (NVENC/NVDEC) to compress KV cache before remote transfer; demonstrates KV tensors are highly compressible with video codecs; offloads compression to GPU encoder — the DPU angle is the key differentiator from this work
  - **ShadowServe: Interference-Free KV Cache Fetching for Distributed Prefix Caching**: addresses KV cache fetch latency in disaggregated serving; identifies network transfer as the binding bottleneck for prefix-cache hit latency; does not compress the KV payload
  - **NetZIP: Algorithm/Hardware Co-design of In-network Lossless Compression for Distributed Large Model Training**: closest prior art — lossless compression co-designed with in-network hardware for distributed training; establishes feasibility of in-network lossless compression for ML traffic; key differences to establish: (a) DPU (commodity programmable NIC) vs. custom switch ASIC, (b) coverage of inference workloads (KV-cache migration, disaggregated serving) vs. training-only, (c) RDMA-transparent interception model vs. application-layer integration
  - **Accelerating Lossy and Lossless Compression on Emerging BlueField DPU Architectures — PEDAL** (2024): proposes PEDAL unified compression library; pre-initializes DOCA at MPI_Init time, pools buffers, uses 3-byte header for algorithm identification; integrates into MPICH MPI_Send/Recv path; achieves up to 101× compression time improvement and 88× communication latency reduction; closest system design prior art for our work

- **What I already tried**: N/A (new project)

- **What didn't work**: N/A

---

## Constraints

- **Validation resources**:
  - *Real hardware*: A100 GPU cluster (multi-node) — measure actual all-reduce and KV-transfer traffic patterns, achieve ground-truth bandwidth and latency numbers
  - *DPU prototype*: Servers with BlueField-3 DPU — use the built-in C-engine via DOCA Compress API as the primary hardware baseline; characterize C-engine throughput and DOCA overhead on LLM tensor traffic patterns; FPGA or custom ASIC path as stretch goal for higher throughput or algorithm flexibility; measure end-to-end communication speedup on A100 cluster
  - *Simulation*: 64-core CPU / 251 GB RAM / 1 TB disk Linux server running:
    - [LLMServingSim](https://github.com/casys-kaist/LLMServingSim) — model KV-cache migration traffic patterns at scale beyond available physical cluster
    - [SimAI](https://github.com/aliyun/SimAI) — model collective communication (all-reduce, all-gather) timing with compressed payloads; sweep cluster sizes and model configs not available in lab

- **Timeline**: 3 months to submission (today: 2026-05-25)

- **Target venue**:
  - Primary: [ASPLOS 2027](https://www.asplos-conference.org/asplos2027/cfp/) **September Cycle** — deadline **2026-09-09** (~3.5 months); strong fit for cross-layer system co-design framing (runtime adaptive policy + DPU offload + collective integration)
  - Fallback: [HPCA 2027](https://conf.researchr.org/track/hpca-2027/hpca-2027-main-conference) — deadline **2026-07-24** (~2 months); only viable if DPU microbench results are strong by late June; hardware-architecture framing (DPU pipeline design, compression engine characterization)

---

## What I'm Looking For

- [x] New research direction from scratch
- [ ] Improvement on existing method
- [ ] Diagnostic study / analysis paper
- [ ] Other

**Specific asks**:
1. Which communication phases (gradient all-reduce / pipeline activation / KV-cache migration / optimizer state scatter-gather) have the highest lossless compressibility and are most network-bottlenecked — i.e., where is the ROI largest?
2. Which lossless algorithms (LZ4, DEFLATE, zlib) does the BF3 C-engine natively support, and what is the achievable throughput on LLM tensor traffic? For algorithms not supported by the C-engine (e.g., Zstd, ANS), does an FPGA implementation close the gap?
3. Is there prior work on in-NIC / in-DPU lossless compression specifically for ML tensor traffic (not general TCP/network compression)?
4. What novelty angle is least crowded: (a) DPU offload architecture and compression pipeline design, (b) tensor-type-aware algorithm selection policy, (c) integration with RDMA semantics and GPUDirect, (d) integration with collective primitives (SHARP / NCCL)?

---

## Domain Knowledge

- BlueField-3 contains a dedicated **C-engine** (hardware compression accelerator) alongside 16 Arm Cortex-A78 SoC cores and a ConnectX-7 NIC ASIC; the C-engine is a fixed-function block, not software — it natively accelerates DEFLATE, zlib, and LZ4; BF3 C-engine is up to 58% faster than BF2 C-engine on decompression; peak host-facing bandwidth ~400 Gb/s
- The dominant cost in DPU compression is **not** the compression algorithm: DOCA initialization accounts for 51.7% and buffer staging 38.6% of total end-to-end time (90.4% system overhead combined, per characterization papers); the C-engine itself is fast — the system integration is the bottleneck
- PEDAL (prior art) solved the MPI case by pre-initializing DOCA at MPI_Init and pooling buffers; the open problem is applying the same principle to RDMA-layer tensor traffic (all-reduce, KV-cache migration) without MPI's explicit message boundaries
- RDMA semantics (RC/UD) guarantee ordering within a QP; compression must preserve message boundaries and ordering — byte-stream compression across RDMA Write payloads is non-trivial; likely need to compress at the WR (work request) granularity
- Gradient tensors in training have inter-iteration correlation and repetitive bit patterns (many near-zero FP16 values) that lossless compressors can exploit; exact lossless ratio depends on layer type and training stage — needs empirical characterization
- KV caches for long-context LLMs (128K tokens, GQA) are large (tens of GB per request), mostly FP16/BF16; lossless compression preserves numerical precision and avoids any risk to generation quality or attention correctness
- Pipeline parallelism activation tensors are sent point-to-point (not collective), making them easier to intercept with per-QP compression without coordinating across ranks
- NCCL bypasses the CPU for collective operations when using RDMA GPUDirect; DPU-level interception of GPUDirect traffic requires careful integration with the GPUDirect RDMA path (this may be a key technical risk)

---

## Non-Goals

- Lossy compression of any kind (quantization, top-K sparsification, SVD sketch) — lossless only; correctness is non-negotiable
- Tape-out of a full custom ASIC (too long a timeline); FPGA prototyping and architectural characterization are in scope
- General-purpose network compression unrelated to ML tensor traffic
- Modifying NCCL internals or the RDMA driver stack (prefer transparent interception via DOCA or eBPF-style hooks)
- WAN / inter-datacenter links (focus on intra-datacenter RDMA fabric)

---

## Existing Results (if any)

None yet. Starting from scratch.

**Anticipated baseline numbers** (from prior work, for sizing):
- A100 NVLink intra-node: ~600 GB/s aggregate; cross-node RDMA via IB HDR: ~25 GB/s per link (200 Gb/s)
- Typical LLM all-reduce bottleneck at 70B param scale: ~5–15 GB per step for FP16 gradients with ZeRO-1; ring all-reduce at 8-node = each node sends/receives ~5–15 GB
- BF3 C-engine peak compression speedup: up to 26.8× over CPU baseline (from characterization papers); but end-to-end gain is gated by DOCA overhead — without amortization, the system overhead dominates
- PEDAL demonstrated up to 101× compression time improvement and 88× communication latency reduction in MPI by amortizing DOCA init and pooling buffers; these are the reference numbers to beat or extend into the RDMA/LLM serving path
- KV cache per request at 32K context, Llama-70B, GQA: ~4–8 GB; migration latency at 25 GB/s link: ~160–320 ms — directly visible in TTFT for decode-disaggregated serving