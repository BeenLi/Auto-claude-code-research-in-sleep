# Research Idea Report

**Direction**: `/idea-discovery "nic lossless compression"`  
**Generated**: 2026-04-26 10:26 CST  
**Effort**: beast  
**Reviewer difficulty configured**: nightmare  
**Research Wiki**: rebuilt from scratch before use  
**Ideas generated**: 24 generated -> 12 survived hard gates -> 6 recommended -> 1 selected for refinement  
**Scope rule**: cover the full AI infrastructure stack, but keep hardware bottleneck and validation path mandatory.

---

## Landscape Summary

The literature now has a strong direct competitor in **NetZIP (MICRO 2025)**, so a publishable direction cannot be "put lossless compression in the NIC" in generic form. The more defensible gap is the system consequence of compression inside RDMA: compressed wire bytes decouple from decompressed host-output bytes, and this can move congestion from the link into Rx decompression engines, PCIe/host-memory writes, Rx SRAM buffers, and RDMA completion latency.

Cross-stack work matters. **Ecco, ZipServ, DECA, and Quad Length Codes** show that hardware-friendly decompression format and placement dominate real benefit. **Stratum/Kelle** show memory/runtime layers can dominate LLM serving. **Toasty** shows the host Rx path itself is a first-order network I/O bottleneck. These papers collectively support a full-stack compression-control idea rather than a network-only mechanism.

---

## Top Recommendation

### Idea 1 - Rx Expansion Budgeting for Compressed RDMA

- **One-sentence summary**: Add an expansion-aware Rx budgeter and feedback loop so compressed RDMA traffic is admitted/scheduled by decompressed output-byte pressure, not only wire-byte pressure.
- **Core hypothesis**: Under variable LLM tensor compressibility, naive compressed RDMA can reduce link bytes while increasing Rx stalls, host-write bursts, and tail FCT; tracking expansion ratio and output-byte credits avoids this hidden bottleneck.
- **AI infra layer**: multi-layer: interconnect/network + memory/data movement + runtime/serving.
- **Hardware bottleneck**: decompression output bandwidth, PCIe/host-memory writes, Rx SRAM occupancy, decompression-engine queueing.
- **Minimum viable experiment**: analytical model + csg-htsim flow simulation + gem5/htsim window-level co-simulation for Rx output-byte pressure.
- **Contribution type**: NIC/RDMA protocol-control co-design.
- **Validation backend**: ready/partial: analytical model ready; htsim/gem5 adapter partial.
- **Pilot signal**: DESIGNED_NOT_RUN; analytical sanity check shows 400Gbps compressed ingress at 2.0-3.0x expansion demands 800-1200Gbps decompressed output movement, exceeding PCIe 5.0 x16 one-direction budget.
- **Novelty quick-check**: NetZIP demonstrates compression but not expansion-aware RDMA control; RoCE BALBOA offers a stack but not this policy; Ecco/ZipServ/DECA solve decoder locality in other layers, not RDMA Rx feedback.
- **Risk**: MEDIUM. Reviewer will demand credible closed-loop simulation and realistic ratio traces.
- **Why selected**: best match to AGENTS.md simulator-first anchor and strongest differentiation from NetZIP.

---

## Recommended Backups

### Idea 2 - Fixed-Format Tensor Codec for FPGA RDMA Payloads

- **Layer**: interconnect + compute/codec.
- **Hypothesis**: ZipServ/Quad/Ecco-style fixed or bounded-length decoding will beat LZ/Huffman-style variable bitstreams for FPGA NIC line-rate decompression under RDMA MTU constraints.
- **Backend**: HLS/RTL sketch + trace compression study.
- **Win metric**: 100/200/400Gbps line-rate feasibility, LUT/BRAM/DSP footprint, ratio vs LZ4/NetZIP transform.
- **Risk**: MEDIUM-HIGH. Needs codec insight, not just engineering.

### Idea 3 - Compression-Aware DCQCN/PFC for Variable Ratio Flows

- **Layer**: interconnect/network.
- **Hypothesis**: DCQCN/ECN trained on queue occupancy and wire bytes misallocates rates when flows have different expansion ratios; a dual-byte congestion signal improves tail FCT and fairness.
- **Backend**: htsim with compressed-byte/original-byte accounting.
- **Risk**: HIGH. Protocol claim may require more realism than htsim alone.

### Idea 4 - DPU Compression Interference Cartography

- **Layer**: DPU/runtime.
- **Hypothesis**: Shared DPU compression engines have structured HoL/interference under mixed chunk sizes and compressibility; a small scheduler can reduce p99 latency.
- **Backend**: BlueField or replay simulator.
- **Risk**: LOW scientifically, HIGH platform access.
- **Status**: strong backup from prior run, but less aligned with the simulator-first AGENTS.md anchor.

### Idea 5 - NIC/CXL-Aware Compressed KV Spill Path

- **Layer**: memory/data movement + runtime.
- **Hypothesis**: KV cache spill/fetch should be scheduled by decompression placement and CXL/PCIe bandwidth, not just capacity savings.
- **Backend**: analytical + trace replay using LLM serving traces.
- **Risk**: MEDIUM-HIGH. May become a software runtime paper unless hardware path is explicit.

### Idea 6 - Checkpoint Burst Compression in DPU/NIC/Storage Path

- **Layer**: storage/checkpoint/data pipeline.
- **Hypothesis**: LLM checkpoint save/load bursts benefit from DPU/NIC inline compression only when compression, DMA, SSD, and network queues are jointly budgeted.
- **Backend**: storage trace replay + analytical model.
- **Risk**: MEDIUM. Needs representative checkpoint traces.

---

## Surviving Idea Table

| Rank | Idea | Layer | Backend | Readiness | Novelty | Risk | Status |
|---:|---|---|---|---|---|---|---|
| 1 | Rx Expansion Budgeting for Compressed RDMA | interconnect+memory | analytical+htsim+gem5 | partial | high | medium | SELECTED |
| 2 | Fixed-Format Tensor Codec for FPGA RDMA Payloads | interconnect+codec | HLS/RTL+trace | partial | high | med-high | backup |
| 3 | Compression-Aware DCQCN/PFC | network | htsim | partial | high | high | backup |
| 4 | DPU Compression Interference Cartography | DPU/runtime | BlueField+replay | future | medium-high | platform | backup |
| 5 | NIC/CXL-Aware Compressed KV Spill Path | memory/runtime | trace+model | partial | medium | med-high | backup |
| 6 | Checkpoint Burst Compression in DPU/NIC/Storage Path | storage | trace replay | partial | medium | medium | backup |
| 7 | 3D Roofline for NIC Decompression Placement | compute+network | analytical | ready | medium | medium | watch |
| 8 | RDMA Metadata Contract for Compressed Payloads | protocol | design+micro-sim | partial | medium | high | watch |
| 9 | Compression-Ratio Telemetry for LLM Collectives | network/runtime | trace+htsim | partial | medium | medium | watch |
| 10 | Rx Cache-Warm Decompression Buffers | host/network | gem5+microbench | partial | medium | medium | watch |
| 11 | P4 Switch Hints for Compressed RDMA | network | ns-3/P4 sketch | future | low-medium | high | eliminate |
| 12 | Pure BlueField Library Tuning | DPU/runtime | DPU microbench | future | low | low | eliminate |

---

## Eliminated Themes

| Theme | Reason |
|---|---|
| Generic "NIC LZ4 accelerator" | NetZIP and commercial IP make this too incremental. |
| Pure LLM model compression | Out of scope unless it creates a concrete hardware/data-movement bottleneck. |
| Software-only serving scheduler | Rejected unless tied to HBM/CXL/PCIe/NIC pressure. |
| Soft-RoCE-only validation | AGENTS.md requires real RDMA or credible RDMA simulator; Soft-RoCE cannot support protocol claims. |

---

## Decision

Proceed with **Idea 1: Rx Expansion Budgeting for Compressed RDMA**. It preserves the current ARIS simulator-first anchor (`gem5 + Broadcom/csg-htsim + cosim_gem5_htsim`), directly differentiates from NetZIP, and gives a clear hardware/system claim: compressed RDMA must budget decompressed output bytes, not just compressed wire bytes.

