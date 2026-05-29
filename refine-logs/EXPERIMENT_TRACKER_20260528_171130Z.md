# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | DOCA capability inventory | BF3 + DOCA Compress | local | supported tasks, max buffer, firmware, DOCA version | MUST | TODO | run before assuming codec support |
| R002 | M0 | raw RDMA baseline | ib_send_bw / custom verbs | 2-node | p50/p99 latency, bandwidth | MUST | TODO | host buffers first |
| R003 | M1 | tensor corpus generation | KV/activation/gradient chunks | synthetic + captured if possible | dtype, size, entropy sample | MUST | TODO | align with EC-W4 |
| R004 | M2 | cold vs warm frontier | DOCA path sweep | train/held-out chunks | compression ratio, exposed latency | MUST | TODO | captures NE-1 |
| R005 | M2 | pre-registered buffer sweep | DOCA + buffer pool | train/held-out chunks | staging time, latency | MUST | TODO | tests amortization |
| R006 | M3 | WR gate smoke | WR-ZipGuard prototype | 2-node host buffers | correctness, latency | MUST | TODO | bitwise compare every chunk |
| R007 | M3 | policy comparison | raw/static/always/WR-ZipGuard | held-out chunks | p99, false positives, bytes | MUST | TODO | main method proof |
| R008 | M3 | ablation | no sampling/no bypass/no pool | held-out chunks | p99, false positives | MUST | TODO | novelty isolation |
| R009 | M4 | KV transfer harness | vLLM/Mooncake-like path | 2-4 nodes | TTFT, TPOT, bytes | MUST | TODO | bandwidth-limited regime |
| R010 | M4 | activation transfer harness | pipeline p2p transfer | 2-4 nodes | transfer time, stage bubble | SHOULD | TODO | run if KV path stalls |
| R011 | M5 | SimAI projection | measured frontier model | scale sweep | step time, sensitivity | NICE | TODO | report only if calibrated |
| R012 | M5 | LLMServingSim projection | measured frontier model | serving traces | TTFT, throughput | NICE | TODO | report only if calibrated |
