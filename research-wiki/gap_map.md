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
| G7 | storage_pipeline | storage/network | LLM checkpoint/model-load compression needs a joint storage/DPU/NIC budget model. | open |
| G8 | placement_model | compute+network | There is no DECA-style roofline for NIC/RDMA decompression placement. | open |
