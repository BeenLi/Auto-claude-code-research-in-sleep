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
## Key Papers (12 total)
- [paper:agrawal2026_quad_length_codes] Quad Length Codes for Lossless Compression of e4m3: A small-LUT prefix code trades slight compression loss for much faster hardware decoding of e4m3 collective data.
- [paper:cavigelli2019_ebpc_extended_bitplane] EBPC: Extended Bit-Plane Compression for Deep Neural Network Inference and Training Accelerators: Bit-plane compression reaches high ratios for DNN feature and gradient maps with compact 65nm hardware, making it a candidate for NIC-side ML tensor c
- [paper:cheng2025_ecco_improving_memory] Ecco: Improving Memory Bandwidth and Capacity for LLMs via Entropy-Aware Cache Compression: LLM cache compression can be hardware-viable when the decoder is parallelized and pipelined, suggesting a transferable design pattern for NIC Rx decom
- [paper:fan2026_zipserv_fast_memoryefficient] ZipServ: Fast and Memory-Efficient LLM Inference with Hardware-Aware Lossless Compression: Fixed-format lossless encoding plus fused decompression/compute can avoid variable-bitstream overheads in LLM inference.
- [paper:gerogiannis2025_deca_nearcore_llm] DECA: A Near-Core LLM Decompression Accelerator Grounded on a 3D Roofline Model: Compressed LLM execution needs a joint model of memory, vector, and matrix-engine limits; decompression location matters as much as codec ratio.
- [paper:heer2025_roce_balboa_serviceenhanced] RoCE BALBOA: Service-enhanced Data Center RDMA for SmartNICs: An open 100G RoCEv2 FPGA stack demonstrates SmartNIC service insertion and provides a platform for compression/protocol experiments.
- [paper:huang2025_netzip_algorithmhardware_codesign] NetZIP: Algorithm/Hardware Co-design of In-network Lossless Compression for Distributed Large Model Training: FPGA-NIC lossless compression for gradients and activations lowers distributed
