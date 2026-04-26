# Idea Candidates

**Generated**: 2026-04-26 10:26 CST  
**Effort**: beast  

| # | Idea | Layer | Pilot Signal | Novelty | Risk | Status |
|---:|---|---|---|---|---|---|
| 1 | Rx Expansion Budgeting for Compressed RDMA | interconnect+memory | DESIGNED_NOT_RUN | High | Medium | SELECTED |
| 2 | Fixed-Format Tensor Codec for FPGA RDMA Payloads | interconnect+codec | DESIGNED_NOT_RUN | High | Med-High | BACKUP |
| 3 | Compression-Aware DCQCN/PFC for Variable Ratio Flows | network | DESIGNED_NOT_RUN | High | High | BACKUP |
| 4 | DPU Compression Interference Cartography | DPU/runtime | SKIPPED: hardware | Med-High | Platform | BACKUP |
| 5 | NIC/CXL-Aware Compressed KV Spill Path | memory/runtime | DESIGNED_NOT_RUN | Medium | Med-High | BACKUP |
| 6 | Checkpoint Burst Compression in DPU/NIC/Storage Path | storage | DESIGNED_NOT_RUN | Medium | Medium | BACKUP |

## Active Idea: #1 - Rx Expansion Budgeting for Compressed RDMA

- **Hypothesis**: compressed RDMA needs output-byte admission/scheduling because decompressed Rx writes can exceed PCIe/host-memory budget even when wire bytes look safe.
- **Key evidence**: NetZIP validates in-network compression value; RoCE BALBOA enables FPGA RDMA modification; Ecco/ZipServ/DECA/Quad show decoder format and placement dominate real hardware benefit.
- **Next step**: implement the experiment plan starting with analytical break-even and htsim/gem5 window-level smoke tests.

