### A. Verdict

**Conditional Go for M2 model plumbing only.**

- The M1 model has provided a sufficient analytical foundation for moving to the next stage. While M1 is purely analytical and based on literature-derived compression ratios, the validation of the expansion-aware RDMA model is technically sound for proceeding to M2, where more detailed simulation and experimentation will take place. However, real-world validation of payload compressibility and further experiments beyond theoretical assumptions (P1/P2/P3) are still required.

---

### B. Fatal or near-fatal concerns

1. **Lack of real communication payload evidence (P1/P2/P3)**: As outlined in the M1 evidence, the current results are purely analytical and not grounded in real payload compressibility. Without actual tensor or communication payload data, any conclusions made during M1 remain speculative and can’t be generalized to actual RDMA workloads.

2. **Limited scope of M1 results**: M1 results are highly constrained to the literature-derived ratio models, which do not necessarily match actual RDMA traffic. The transition from theoretical sensitivity to real-world payload behavior must be handled with care in the next stage.

3. **Output-byte control bottleneck hypothesis**: The analysis largely assumes that output bytes will be the limiting factor. However, without including concrete evidence from actual RDMA traffic, it risks being too narrow and missing deeper, complex interactions that might emerge with real-world conditions.

---

### C. Technical gaps by layer

1. **RDMA semantics**: The current model assumes RDMA operations with fixed assumptions about flow types, message sizes, and compression behavior. However, real RDMA systems involve dynamic adjustments for network congestion, error handling, retransmissions, and adaptive flow control, all of which are not yet modeled.

2. **Queueing/control**: The decomposition of the RX expansion scheduling and feedback system requires a more robust model of the RX queueing mechanisms. The current model focuses on decompressor throughput but doesn't sufficiently capture queue pressure, dynamic scheduling, and potentially adaptive feedback systems.

3. **Workload/payload evidence**: This is the largest gap. The models and the assumptions based on synthetic data (P0-level compression ratios) are not directly applicable to real LLM or RDMA workloads. Without real payload evidence (e.g., P2/P3), it’s hard to claim real-world benefits in the scheduling mechanism.

4. **Hardware feasibility**: The experiment plan should incorporate a stronger baseline regarding hardware validation for decompression and throughput measurement. Hardware costs and the impact of token buckets on NIC/DPU side need a clearer evaluation in terms of resource usage (e.g., SRAM, metadata size).

5. **Evaluation methodology**: M1's evaluation lacks direct ties to actual RDMA payload behavior. The transition from analytical results to simulation needs a clear, reproducible, and hardware-consistent evaluation methodology that can connect theory with practical deployment.

---

### D. Strongest baselines and ablations

1. **Receiver decompressed-byte token bucket**: This baseline is well-posed for comparing the benefits of the proposed EARB scheduler. However, an additional **static per-QP decompressed-byte cap** could be useful to test if static limitations at the flow level impact the scheduler performance.

2. **Uncompressed RDMA**: Comparing against this baseline is essential, but a stronger comparison can come from adding an **exact-original-byte receiver credit** mechanism. This would test the assumption that compression might shift bottlenecks from wire byte constraints to decompression/output byte pressure.

3. **Naive compressed RDMA**: As the direct competitor, evaluating this baseline against the scheduler will provide insights into how much improvement the EARB mechanism can bring, especially when applied with varying link speeds and flow types.

---

### E. Minimal M2 plan

1. **Add receiver decompressed-byte token bucket**: This should be implemented as a non-oracle baseline to capture the most likely realistic baseline for comparison.

2. **Simulate decompression service and output buffers**: Model decompression as both input-byte and output-byte work. Include realistic flow models that account for both decompression delays and output buffer constraints (e.g., Rx SRAM).

3. **Performance thresholds**: Sweep over realistic workloads with different offered loads (compressed vs same-original), and measure p99 FCT, output write pressure, and Rx SRAM utilization.

4. **Expand to multi-tenant regime**: Include scenarios that simulate contention for receiver-side resources, such as buffer overflow or under-utilization in a multi-tenant setup.

5. **Run multiple link-speed scenarios**: Test across 100/200/400/800Gbps links to ensure scalability under varying network capacities.

---

### F. Results-to-claims matrix

| M2 Outcome | Strong success (>=20% FCT improvement) | Weak success (<=20% FCT improvement) | Failure (no improvement) |
|------------|----------------------------------------|-------------------------------------|--------------------------|
| **p99 FCT/latency** | Real reduction in p99 latency and stalls from receiver expansion-aware budgeting. | Minimal latency improvements; may indicate bottlenecks outside decompression path. | No improvement or regression in tail latency. |
| **Expansion debt** | Clear reduction in expansion debt, showing the benefit of the scheduler. | Minor debt reduction, not significant for practical use. | No noticeable debt reduction. |
| **Fairness** | Improved fairness, reducing latency skew between tenants. | Some improvement but still uneven fairness. | Fairness degraded or unchanged. |

---

### G. Mock review with score/confidence

- **Score**: **4/6 (Weak Accept)**
- **Confidence**: **High**
- **Reason for score**: The current work makes a clear case for exploring the decompression expansion bottleneck and proposes a plausible mechanism. However, M1 results are theoretical, and further evidence from real communication payloads and more detailed hardware modeling is necessary to strengthen the claims. The real challenge is to prove the mechanism with actual LLM-like traffic rather than theoretical models.

---

### H. Concrete TODO list

1. **Move to P1/P2/P3 evidence collection**: Gather real RDMA communication profiles (tensor/KV/checkpoint data) and push for P2/P3-level evidence.
2. **Model queueing and control more accurately**: Implement more detailed queue models that account for dynamic feedback and congestion avoidance.
3. **Add stronger hardware validation**: Sketch out the hardware cost of the decompression and scheduling mechanism in terms of SRAM and metadata footprint.
4. **Extend ablations**: Test with static Rx output partitioning, FIFO decompression, and weighted fair sharing to identify if there’s a simpler solution before committing to the more complex EARB scheduler.
5. **Refine evaluation methodology**: Transition from synthetic data (P0) to real tensor data and RDMA communication traffic to increase the credibility of the model's real-world relevance.
