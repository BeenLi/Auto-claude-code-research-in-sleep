# Research Wiki Query Pack

_Auto-generated. Do not edit._

## Open Gaps
# Gap Map

_Rebuilt from scratch on 2026-04-26 for `/idea-discovery "nic lossless compression"`._

| Gap | Type | Layer | Summary | Status |
|---|---|---|---|---|
| G1 | unexplored_regime | interconnect+memory | Rx decompression expansion can make compressed RDMA wire-safe but receiver-output-unsafe. | active |
| G2 | untested_assumption | interconnect | RDMA congestion/control signals observe wire bytes, not decompressed output-byte pressure. | active |
| G3 | cross_domain_transfer | NIC codec | ZipServ/Ecco/Quad-style fixed or pipelined decoding has not been mapped to FPGA RDMA payload constraints. | open |
| G4 | contradictory_findings | RDMA semantics | Transparent bump-in-wire compression conflicts with protocol-visible payload-size metadata requirements. | open |
| G5 | unasked_question | DPU runtime | Shared DPU compression-engine interference under multi-tenant mixes lacks a compressor-specific cartography. | backup |
| G6 | cross_layer | memory/runtime/network | KV/cache compression may shift bottlenecks between HBM/CXL/PCIe/NIC rather than removing them. | open |
| G7 | storage_pipeline | storage/network | LLM checkpoint/model-load compression needs a joint storage/DPU/NI
## Key Papers (19 total)
- [paper:agrawal2026_quad_length_codes] Quad Length Codes for Lossless Compression of e4m3: A small-LUT prefix code trades slight compression loss for much faster hardware decoding of e4m3 collective data.
- [paper:al2024_accelerating_lossy_lossless] Accelerating Lossy and Lossless Compression on Emerging BlueField DPU Architectures: DPU C-Engine offload for DEFLATE/LZ4
- [paper:al2025_optinic_resilient_tailoptimal] OptiNIC: A Resilient and Tail-Optimal RDMA NIC for Distributed ML Workloads: Eliminates NIC retransmissions for best-effort out-of-order RDMA
- [paper:al2026_quad_length_codes] Quad Length Codes for Lossless Compression of e4m3: Hybrid prefix coding scheme for e4m3
- [paper:al2026_ucclzip_lossless_compression] UCCL-Zip: Lossless Compression Supercharged GPU Communication: Unified design integrating lossless compression directly into GPU communication primitives
- [paper:al2026_zipserv_fast_memoryefficient] ZipServ: Fast and Memory-Efficient LLM Inference with Hardware-Aware Lossless Compression: Tensor-Core-Aware Triple Bitmap Encoding
- [paper:cavigelli2019_ebpc_extended_bitplane] EBPC: Extended Bit-Plane Compression for Deep Neural Network Inference and Training Accelerators: Bit-plane compression reaches high ratios for DNN feature and gradient maps with compact 65nm hardware, making it a candidate for NIC-side ML tensor c
- [paper:cheng2025_ecco_improving_memory] Ecco: Improving Memory Bandwidth and Capacity for LLMs via Entropy-Aware Cache Compression: LLM cache compression can be hardware-viable when the decoder is parallelized and pipelined, suggesting a transferable design pattern for NIC Rx decom
- [paper:fan2026_zipserv_fast_memoryefficient] ZipServ: Fast and Memory-Efficient LLM Inference with Hardware-Aware Lossless Compression: Fixed-format loss
