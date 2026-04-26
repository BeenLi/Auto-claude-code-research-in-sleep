# Final Method Proposal

**Selected idea**: Rx Expansion Budgeting for Compressed RDMA  
**Generated**: 2026-04-26 10:26 CST  
**Effort**: beast  

## 1. Problem Anchor

NIC/DPU-side lossless compression reduces RDMA wire bytes, but the receiver must still materialize the original uncompressed bytes into host memory, GPU memory, or a staging buffer. With LLM tensors, per-flow compression ratios vary over time and across layers. A 400Gbps NIC receiving data at 2-3x compression ratio can create 800-1200Gbps of decompressed output demand, shifting the bottleneck from the link to Rx decompression engines, PCIe, host-memory writes, and Rx SRAM buffering. Existing NIC compression work largely treats this as an implementation detail rather than a control-plane resource.

## 2. Method Thesis

Build an **Expansion-Aware RDMA Rx Budgeter (EARB)** that accounts for both compressed wire bytes and decompressed output bytes. EARB estimates per-flow expansion ratio, allocates output-byte credits across Rx queues, schedules decompression engines by output pressure, and feeds an expansion-aware signal into RDMA congestion/credit control before hidden Rx stalls turn into tail-latency spikes or retransmissions.

## 3. Dominant Contribution

The contribution is a NIC/RDMA control mechanism for a new bottleneck created by compression:

- **Dual-byte accounting**: separate compressed ingress bytes, decompressed output bytes, and buffered expansion debt.
- **Output-byte credit allocator**: per-flow or per-tenant budget that protects PCIe/host-memory write bandwidth.
- **Rx decompression scheduler**: schedules engines and buffers using predicted output bytes, not only packet arrival order.
- **Feedback hook**: exposes expansion pressure to sender-side rate/credit control or marks flows before Rx SRAM overflow.

## 4. Scope Boundaries

- No claim that EARB invents a better compression algorithm.
- No full production RoCE implementation in Workflow 1.5; simulator-first validation is the primary path.
- No Soft-RoCE as a substitute for RDMA behavior.
- No application-level speedup claim until closed-loop network + host pressure evidence exists.

## 5. Must-Prove Claims

1. **C1 - Hidden bottleneck**: naive compressed RDMA can increase Rx stalls/tail latency because output-byte demand exceeds receiver-side memory/PCIe budget.
2. **C2 - Predictability**: short-window expansion estimates predict dangerous output pressure well enough for control.
3. **C3 - Control benefit**: EARB reduces p99/p999 FCT, Rx queue stalls, drops/retransmissions, or completion latency versus naive compressed RDMA and wire-byte-only controls.
4. **C4 - Practicality**: bookkeeping SRAM, metadata, and scheduler latency are small enough for NIC/DPU implementation.

## 6. Reviewer-Risk Register

| Risk | Why it matters | Mitigation |
|---|---|---|
| "This is just flow control" | Reviewer may view dual-byte accounting as obvious | Show baseline RDMA controls observe the wrong byte domain and fail under variable ratio |
| "Simulator is too abstract" | Main validation is simulator-first | Use htsim for network, gem5 for host-memory windows, and analytical bounds to triangulate |
| "Compression ratios are workload-dependent" | LLM tensors may not compress enough | Include synthetic ratio sweeps plus tensor-inspired distributions from NetZIP/Quad/Ecco-style data |
| "NetZIP already did it" | Direct competitor | Position NetZIP as compression datapath; EARB is Rx expansion/control-plane mechanism |

