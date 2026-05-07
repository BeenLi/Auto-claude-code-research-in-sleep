# 文献综述：Lossless Communication Compression

**Generated**: 2026-05-07T06:07:21Z  
**Skill**: /research-lit  
**Direction**: Lossless Communication Compression  
**Scope**: AI infrastructure for LLM，硬件倾向系统研究；主层为 interconnect/network，扩展到 DPU/NIC service、GPU collective、KV transfer、checkpoint/model-load、memory/data movement。  
**结论先行**: 2026 年 4-5 月之后，通用 “把 LLM 通信流量做 lossless compression” 已经拥挤。NetZIP、ZipCCL、UCCL-Zip、SplitZip、ZipServ 和 Quad Length Codes 把 NIC/GPU/KV/collective/weight 侧的基础压缩路径基本占住。新的机会不在“再做一个 codec”，而在共享压缩服务的多资源公平性、压缩放置决策、DPU/NIC engine contention、以及 compression 与实际数据移动边界的控制。

---

## Source Audit

| Source | 状态 | 本次处理 |
|---|---|---|
| Local PDFs | 可用 | `papers/Cavigelli 等 - 2019 - EBPC...pdf` 是 DNN bit-plane compression 背景；本轮只作为 cross-domain codec evidence。 |
| Zotero | 不可用 | `zotero_get_collections` 返回 localhost 502；本轮降级到 repo 历史综述、arXiv、web。 |
| Historical repo notes | 可用 | 读取 `nic-lossless-compression/research-lit/2026-04-26.md` 和 `experiments/rx-expansion/results/M1_GO_NOGO_REPORT.md`。 |
| arXiv API script | 部分可用 | 成功召回 ZipCCL、UCCL-Zip、ZipServ、Quad、RoCE BALBOA、SmartNIC DPU offload；后续 novelty 批量查询触发 429/timeout。 |
| Web search / WebFetch | 可用 | 查验 NetZIP、ZipCCL、UCCL-Zip、SplitZip、ZipServ、UCCL repo、BlueField/DPU/SmartNIC 资料。 |
| Semantic Scholar / DeepXiv | 未请求 | 本次默认 `sources: all` 不强制 S2/DeepXiv；未把其结果作为核心证据。 |

---

## Section 1 - Core Paper / Artifact Table

| 论文 / Artifact | 年份 / Venue | Layer | 方法 / 贡献 | 关键信号 | Evidence |
|---|---:|---|---|---|---|
| [NetZIP: Algorithm/Hardware Co-design of In-network Lossless Compression](https://experts.esf.edu/esploro/outputs/conferenceProceeding/NetZIP-AlgorithmHardware-Co-design-of-In-network-Lossless/99994610004826) | MICRO 2025 | NIC/network | FPGA-NIC bump-in-the-wire lossless compression for gradients/activations | 报告对 Llama/GPT 训练流量的显著压缩增益和约 35% training-time reduction；直接占住“NIC 侧训练通信压缩”主张 | peer-reviewed |
| [ZipCCL](https://papers.cool/arxiv/2604.27844) | arXiv 2026-04-30 | GPU collective/runtime | lossless compressed collectives for LLM training，exponent coding + GPU kernels + adaptive collective strategies | 64-GPU dense/MoE，communication time up to 1.35x improvement，E2E training up to 1.18x | preprint |
| [UCCL-Zip](https://arxiv.org/abs/2604.17172) | arXiv 2026-04 | GPU P2P/collective | 把 lossless compression 融入 GPU P2P 和 NCCL-style persistent kernels | 报告 RL weight sync up to 47.5% faster、vLLM E2E latency up to 10% lower；P2P/KV/collective 均被覆盖 | preprint |
| [SplitZip](https://arxiv-troller.com/paper/3161180/) | arXiv 2026-05 | KV transfer | GPU-friendly lossless KV-cache transfer compression with calibrated exponent codebook | 报告 BF16 KV transfer speedup up to 1.32x、TTFT up to 1.30x；KV-transfer lossless compression 变成拥挤方向 | title/abstract-only |
| [ZipServ](https://arxiv.org/abs/2603.17435) | ASPLOS 2026 / arXiv | inference compute/memory | fixed-format lossless weight compression + fused GPU decompression-GEMM | model size up to 30% reduction、kernel up to 2.21x、E2E inference average 1.22x | peer-reviewed/preprint metadata |
| [Quad Length Codes for e4m3](https://arxiv.org/abs/2602.17849) | arXiv 2026 | codec/hardware | e4m3 hardware-friendly lossless code with small LUT, simpler than Huffman decode | 牺牲少量 ratio 换更快/更简单硬件 decode；提示 communication codec 应优先考虑 decoder placement | preprint |
| [RoCE BALBOA](https://arxiv.org/abs/2507.20412) | arXiv 2025 | SmartNIC/RDMA platform | open-source 100G RoCEv2-compatible FPGA RDMA stack | 可作为 compression service / scheduling / protocol-extension 的 prototype substrate | preprint |
| [UCCL repo](https://github.com/uccl-project/uccl) | active project | GPU communication | UCCL covers collectives, P2P/KV transfer, expert-parallel communication, multi-vendor network paths | 说明 public baseline canons 正快速聚合到 UCCL/NCCL-family harness | open-source artifact |
| [Communication Offloading on SmartNIC DPUs](https://arxiv.org/abs/2605.04842) | arXiv 2026-05-06 | DPU/offload | SmartNIC DPU communication offload characterization | memory-to-communication ratio 是 offload predictor；无 DCA 下 DRAM traffic 可极端放大，是 compression service placement 的重要新信号 | preprint |
| BlueField / PEDAL DPU compression line | IEEE Micro/IPDPS 2024 | DPU compression | DPU C-engine / compression engine characterization and MPI integration | DPU compression can accelerate jobs, but DMA/invocation/scheduling overhead dominates small or contended workloads | peer-reviewed |
| [NVIDIA nvCOMP checkpoint blog](https://developer.nvidia.com/blog/cut-checkpoint-costs-with-about-30-lines-of-python-and-nvidia-nvcomp/) | 2026-04 | checkpoint/storage | GPU-side lossless checkpoint compression recipe | checkpoint compression has strong practical pressure, but pure placement optimization risks being seen as engineering | vendor technical evidence |
| [SmartNIC survey / shell review](https://www.mdpi.com/2076-3417/16/3/1476) | 2026 | SmartNIC architecture | survey of FPGA shells, DPU fixed-function offloads, multi-tenant isolation | 明确 DPU/SmartNIC 的 compression/QoS/isolation/parallelism constraints，可支撑 multi-resource fairness framing | survey |

---

## Section 2 - Landscape Map

### 1. Generic communication compression is now crowded

NetZIP covers in-network/NIC-side lossless compression for distributed model training. ZipCCL and UCCL-Zip push compression into GPU collectives and P2P/KV paths. SplitZip makes disaggregated KV-cache transfer compression a very recent direct competitor. Therefore, a new idea cannot simply be “compress gradients/KV/weights over the network”；它必须解释为什么现有 per-flow / per-collective compression 在共享硬件服务、placement、fairness、feedback 或 correctness boundary 上仍然失败。

### 2. Codec ratio is secondary to placement and service contention

ZipServ、Quad、UCCL-Zip 和 SplitZip 都强调 GPU/hardware-friendly decode path。DPU papers 则提醒我们：即使 accelerator 很快，host-DPU DMA、engine invocation、on-card memory traffic 和 lack of direct cache access 也能吞掉收益。对 Workflow 1 来说，最值得挖的是“压缩服务消耗哪些资源、由谁计费、谁会被 noisy neighbor 伤害”，而不是单个 codec 的平均压缩率。

### 3. Multi-tenant DPU/NIC service 是结构性缺口

DPU/SmartNIC 已经被定位为多租户基础设施边界，承担 security、storage、RDMA、QoS、telemetry 和 compression 等 offload。可是现有 LLM compression papers 大多评价单 workload 或单 communication library，没有把 compression engine cycles、compressed input bytes、original/output bytes、DMA/PCIe/host-memory writes 放进同一个 scheduling/fairness model。

### 4. Checkpoint/model-load compression 是强实用场景，但 novelty 风险高

NVIDIA nvCOMP blog 和 storage/DPU 生态说明 checkpoint compression 有明确 ROI。但如果只做 GPU/CPU/DPU/SSD placement roofline，容易变成工程调参。这个方向可作为 supporting workload，或者用来证明 C-Share 的共享服务价值，不适合作为本轮主 idea。

### 5. KV 和 expert-parallel 是热门但拥挤的备选

UCCL repo 明确覆盖 P2P/KV/EP，UCCL-Zip 和 SplitZip 已经对 KV/P2P lossless compression 给出端到端数字。MoE expert-parallel token exchange 仍可能有 compressibility-aware packing/placement 机会，但需要非常强的 trace evidence 才能避免“又一个 UCCL-Zip/DeepEP tweak”。

---

## Section 3 - Structural Gaps

1. **Shared compression-service fairness gap**：现有 work 优化单 flow 或单 library 的 compression time/ratio，没有回答多个 tenant/traffic class 共享 DPU/NIC compression engine 时，按 wire bytes、job count、original bytes、engine cycles、output bytes 哪个维度公平。
2. **Engine-time vs output-byte accounting gap**：已有本地 Rx expansion budgeting 处理 receiver output-byte pressure，但没有处理 shared compressor/decompressor engine time、DMA staging、host-memory traffic 和 tenant fairness。
3. **Compression placement under DPU memory traffic gap**：SmartNIC DPU offload 新证据显示 memory-to-communication ratio 和 DCA 缺失可决定 offload 成败；lossless compression placement 需要把 on-card/host memory traffic 纳入一等资源。
4. **Checkpoint burst service gap**：checkpoint/model-load burst 很适合作为共享压缩服务压力源，但现有系统多关注单任务 size reduction 或 GPU-side compression，缺少多租户 burst + shared engine SLO map。
5. **EP/KV compressibility variability gap**：KV/EP traffic 的 compressibility 可能随 request/model/expert routing 波动，现有 systems 通常只给平均收益，缺少 workload-aware “when not to compress” control。
6. **Hardware-feasible control gap**：很多 compression scheduler 可以在软件里算，但 NIC/DPU 侧需要 line-rate 近似、少状态、可解释的 token/counter design。

---

## Section 4 - Competitive Landscape

| Competitor | Solves | Leaves open | Positioning implication |
|---|---|---|---|
| NetZIP | NIC-side in-network lossless compression for training gradients/activations | Multi-tenant shared compression service fairness; engine/DMA/output multi-resource accounting | 不要再主张“NIC compression itself”；必须主张 shared-service control |
| ZipCCL / UCCL-Zip | GPU collective/P2P lossless compression with runtime integration | DPU/NIC engine sharing, tenant isolation, compression-service scheduling | 可作为 per-flow/per-library baseline |
| SplitZip | Lossless KV-cache transfer compression | Multi-tenant shared service and cross-traffic fairness | KV-only idea 风险高；KV 可做 workload |
| ZipServ / Quad | Hardware-friendly fixed-format codec/decode placement | Communication-service arbitration and DPU/NIC resource management | Codec insights 可迁移，但不要做 codec-only |
| BlueField/PEDAL | DPU compression acceleration and MPI integration | Multi-resource fairness under mixed LLM traffic; SLO-aware shared engine scheduler | C-Share 可直接把它们作为 closest DPU baseline |
| RoCE BALBOA / ReCoNIC | Prototype substrate for FPGA RDMA services | Compression policy itself | 可作为 optional hardware validation path |

---

## Landscape Pack

### Topic Scope

- original_topic: Lossless Communication Compression
- inferred_ai_infra_layer: multi-layer with interconnect/network and DPU/NIC service primary
- included_layers: interconnect/network, SmartNIC/DPU runtime, GPU communication, memory/data movement, checkpoint/storage, LLM serving runtime when tied to hardware bottleneck
- excluded_layers: pure model quantization/pruning, lossy semantic compression, pure codec papers without communication/service bottleneck, software-only scheduling with no hardware resource boundary
- search_neighborhood: same-layer + LLM communication expansion
- expanded_terms: lossless communication compression, NIC compression, DPU compression, SmartNIC QoS, GPU collectives, NCCL/UCCL, KV cache transfer, RDMA, checkpoint compression, model-load compression, decompression placement, engine contention

### Bottleneck Evidence

| bottleneck_id | layer | bottleneck | evidence_level | supporting_papers | decisive_metrics |
|---|---|---|---|---|---|
| B1 | GPU/network | collective/P2P communication bandwidth can dominate LLM training/serving | preprint + peer-reviewed | NetZIP, ZipCCL, UCCL-Zip | comm time, all-reduce/all-gather latency, E2E tokens/s |
| B2 | DPU/NIC service | shared compression engines consume engine cycles, DMA bandwidth, memory traffic, and output bytes | peer-reviewed + preprint | PEDAL, BlueField line, SmartNIC DPU offload | engine occupancy, DMA bytes, p99 service latency |
| B3 | memory/data movement | decode/compression placement affects intermediate traffic and GPU/host memory pressure | peer-reviewed + preprint | ZipServ, Quad, DECA/Ecco background | bytes moved, decode latency, memory bandwidth |
| B4 | serving/KV | disaggregated KV transfer becomes TTFT/tail bottleneck | preprint + artifact | UCCL-Zip, SplitZip, UCCL KV transfer blog | KV transfer latency, TTFT, request throughput |
| B5 | checkpoint/storage | checkpoint compression reduces storage/network burst but placement is platform-dependent | vendor technical evidence + systems prior | nvCOMP checkpoint blog, RDMA storage/DPU papers | checkpoint write/load time, GPU idle time, storage BW |
| B6 | multi-tenant infra | DPU/SmartNIC isolation/QoS is first-class but compression is not yet scheduled as a multi-resource service | survey + docs | SmartNIC shell survey, BlueField docs | fairness index, SLO violations, noisy-neighbor slowdown |

### Mechanism Clusters

| cluster | layer | mechanism_family | representative_papers | plateau_or_missing_piece |
|---|---|---|---|---|
| NIC/network compression | interconnect | in-network compressor/decompressor | NetZIP, RoCE BALBOA | lacks shared-service fairness and multi-resource accounting |
| GPU communication compression | GPU collective/P2P | fused GPU compression/decompression | ZipCCL, UCCL-Zip, SplitZip | mostly library-local, not shared DPU/NIC service |
| Hardware-friendly codecs | codec/compute | fixed-format / LUT / exponent coding | Quad, ZipServ, SplitZip | ratio/decode optimized, not scheduling/fairness aware |
| DPU compression offload | DPU runtime | C-engine / accelerator scheduling | BlueField/PEDAL | lacks tenant-aware engine/DMA/output accounting |
| Checkpoint/model-load compression | storage/data movement | GPU/CPU/DPU/storage placement | nvCOMP, storage/DPU systems | strong practical value, weak standalone novelty |

### Evaluation Canon

| canon_id | category | item | applies_to_layer_or_subtopic | supporting_papers | evidence_level | adoption_strength | artifact_or_access | limitations | notes |
|---|---|---|---|---|---|---|---|---|---|
| EC-P1 | evaluation_platform | analytical multi-resource model | DPU/NIC compression service, checkpoint placement | all mechanism clusters | local-note | common | ready | abstraction risk | first triage backend |
| EC-P2 | evaluation_platform | htsim / RDMA-style network simulator | RDMA/NIC scheduling and FCT | local Rx expansion, NetZIP positioning | local-note | occasional | partial | needs compression-ratio injection | can reuse existing model ideas |
| EC-P3 | evaluation_platform | gem5/window-level PCIe/host-memory model | DPU offload memory traffic, output/DMA pressure | SmartNIC DPU offload, local rx-expansion | preprint + local | occasional | partial | model plumbing needed | good for DCA/memory traffic sensitivity |
| EC-P4 | evaluation_platform | RoCE BALBOA / ReCoNIC FPGA RDMA stack | hardware feasibility | RoCE BALBOA, ReCoNIC | preprint | occasional | open-source/partial | platform bring-up | optional, not first gate |
| EC-P5 | evaluation_platform | NCCL/UCCL-style GPU collective/P2P harness | GPU communication compression baselines | UCCL, ZipCCL, UCCL-Zip | artifact/preprint | common | open-source | GPU cluster access | baseline source, not necessarily implementation target |
| EC-P6 | evaluation_platform | BlueField/DPU C-engine microbenchmark harness | DPU compression service | BlueField/PEDAL | peer-reviewed | occasional | hardware-dependent | hardware access unknown | optional but reviewer-requested |
| EC-P7 | evaluation_platform | LLM serving / trace replay harness | KV, inference, multi-tenant service | UCCL/SplitZip/vLLM-like systems | preprint/artifact | common | public/open-source partial | trace realism | supports mixed workload replay |
| EC-W1 | benchmark_workload | LLM training collectives: gradients/activations/params, dense and MoE | collective compression | NetZIP, ZipCCL | peer/preprint | common | public configs partial | exact traces scarce | crowded but necessary baseline |
| EC-W2 | benchmark_workload | checkpoint/model-load bursts over RDMA/GDS/storage | storage/data movement compression | nvCOMP, RDMA storage | vendor/preprint | occasional | synthetic/public partial | real checkpoint traces needed | supporting workload |
| EC-W3 | benchmark_workload | KV cache transfer/migration/spill traffic | disaggregated serving | UCCL-Zip, SplitZip | preprint | common | open-source partial | rapidly changing | crowded, use as workload not sole idea |
| EC-W4 | benchmark_workload | multi-tenant DPU/NIC communication-service mixes | shared compression service | SmartNIC survey, DPU offload | survey/preprint | weak_or_missing | requires reimplementation | no standard trace | best novelty gap |
| EC-W5 | benchmark_workload | inference weight/KV streaming in vLLM-like serving | serving compression | ZipServ, UCCL-Zip | peer/preprint | common | open-source partial | application integration | secondary workload |

### Core Baseline Candidates

| baseline_id | baseline_name | paper_or_system | scenario | evaluation_platform_used | workload_used | metrics_used | artifact_status | notes |
|---|---|---|---|---|---|---|---|---|
| CB1 | uncompressed communication | standard RDMA/NCCL/UCCL | all scenarios | EC-P2/EC-P5/EC-P7 | EC-W1-EC-W5 | latency, throughput, FCT, TTFT | open_source_system | must always include |
| CB2 | generic software compression | LZ4/Zstd/nvCOMP where applicable | CPU/GPU compression | EC-P1/EC-P5/EC-W2 | EC-W2/EC-W5 | ratio, runtime, bytes moved | open_source_system | sanity baseline |
| CB3 | FIFO DPU compression service | BlueField/PEDAL-style engine queue | DPU compression | EC-P1/EC-P6 | EC-W4 | p99 latency, engine occupancy | requires_reimplementation | key C-Share baseline |
| CB4 | ratio-greedy compression | compress high-ratio jobs first | shared service | EC-P1/EC-P7 | EC-W4 | throughput, fairness, SLO | requires_reimplementation | exposes unfairness |
| CB5 | per-flow compressed communication | NetZIP/ZipCCL/UCCL-Zip-like | training/KV/P2P | EC-P5/EC-P7 | EC-W1/EC-W3 | comm time, E2E speedup | paper_only/open partial | represents current best single-flow approach |
| CB6 | current Rx expansion budgeter | local ARIS project | receiver output-byte admission | EC-P1/EC-P2/EC-P3 | RDMA compressed traffic | output bytes, stalls, FCT | local | must compare to show new service-fairness dimension |
| CB7 | DPU QoS without compression hints | DPU/SmartNIC QoS configs | multi-tenant services | EC-P6/EC-P7 | EC-W4 | fairness, p99, SLO | config_reproducible | tests whether compression-specific accounting matters |
| CB8 | checkpoint placement heuristic | GPU-only nvCOMP or CPU zstd | checkpoint/model load | EC-P1/EC-P5 | EC-W2 | checkpoint time, GPU idle | open_source_system | backup idea baseline |

### Gap Seeds

| gap_id | gap_type | layer | hardware_bottleneck | supporting_papers | evidence_level | possible_mechanism_hint | minimum validation backend | decisive_metric | main_risk_or_kill_reason |
|---|---|---|---|---|---|---|---|---|---|
| G1 | unasked_question | DPU/NIC service | shared engine cycles + DMA + output bytes under tenants | PEDAL, SmartNIC survey, UCCL-Zip | peer/preprint | multi-resource compression-service scheduler | EC-P1 + EC-P7 | SLO-goodput, fairness, p99 | reviewer may call it generic scheduling |
| G2 | unexplored_regime | DPU memory/offload | compression offload can amplify DPU/host memory traffic | SmartNIC DPU offload 2026 | preprint | DCA/memory-aware compression placement | EC-P1 + EC-P3 | memory traffic, speedup, engine occupancy | hardware evidence needed |
| G3 | cross_domain_transfer | checkpoint/storage | burst compression under shared DPU/NIC service | nvCOMP, storage DPU | vendor/preprint | checkpoint-aware admission / burst isolation | EC-P1 + EC-P7 | checkpoint time, p99 interference | standalone novelty weak |
| G4 | contradictory_findings | GPU vs DPU placement | GPU compression saves network but consumes SM/memory; DPU saves GPU but adds DMA | UCCL-Zip, PEDAL, SmartNIC offload | preprint/peer | placement oracle/controller | EC-P1 + EC-P5/P6 | E2E latency vs resource use | may be engineering |
| G5 | unasked_question | MoE EP | token traffic compressibility varies with expert routing | UCCL-EP, UCCL-Zip | preprint/artifact | compressibility-aware EP packing | EC-P5 + EC-P7 | EP latency, network utilization | incremental risk |
| G6 | hardware_control | NIC/FPGA | line-rate scheduler must use small state | RoCE BALBOA, SmartNIC shells | preprint/survey | token counters + age buckets | EC-P1 + EC-P4 | LUT/BRAM/state, line-rate feasibility | platform bring-up |

