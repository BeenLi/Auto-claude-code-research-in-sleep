# Literature Review: In-RNIC Lossless Compression for LLM Cross-Machine Communication

**Generated**: 2026-05-28T17:11:30Z  
**Skill**: /research-lit  
**Original input**: `.worktrees/testResearchLit/idea-stage/RESEARCH_BRIEF.md`  
**Input mode**: 2 -- research brief path  
**Verifier receipt**: `.aris/verify-papers/verified_papers.json` (`WARN`: all 18 candidates verified; warning is `crossref_polite_pool_email_unset`)

Brief loaded: topic="In-RNIC Lossless Compression Engine for LLM Cross-Machine Communication"; known=4 mandatory papers/systems; non-goals=4.

## Section 0 -- Source Audit

| Source | Status | Action Taken / Notes |
|---|---|---|
| Research brief | used | Parsed problem, known papers, constraints, domain knowledge, validation resources, non-goals. |
| Zotero | attempted_empty | `zotero_semantic_search` and item search returned no matching library entries for the query. |
| Obsidian | used | Found and read notes for BlueField DPU compression comparison, C-engine, NetZIP, SplitZip, and KVServe. |
| Local PDFs | partial | `papers/Cavigelli 等 - 2019 - EBPC...pdf` exists; relevant as neural-network compression hardware background, not central to RNIC/RDMA LLM communication. |
| arXiv | used | Queried RDMA/DPU compression, KV-cache compression, disaggregated serving, and lossless tensor compression; verified arXiv IDs with `tools/verify_papers.py`. |
| OpenAlex | used | Retrieved/verified metadata for PEDAL and NetZIP, plus KVCodec metadata where arXiv title variants differed. |
| Web / proceedings | used | Used ACM/DOI, OSTI, NVIDIA DOCA docs, NSF PDF, arXiv pages, and conference/proceedings pages. |
| Gemini | skipped | CLI exists but failed authentication due location/tier eligibility; optional source skipped without blocking. |

## Section 1 -- Paper Table

| Paper | Venue | Year | Method | Key Result | Eval Platform | Workload | Baseline | Relevance | Source | Verification | Preprint | Full Text | Artifact |
|---|---:|---:|---|---|---|---|---|---|---|---|---|---|---|
| [Accelerating Lossy and Lossless Compression on Emerging BlueField DPU Architectures](https://doi.org/10.1109/IPDPS57955.2024.00040) | IPDPS | 2024 | PEDAL library; DOCA init amortization, buffer pooling, 3-byte algorithm header, MPICH integration | Up to 101x compression-time improvement and 88x communication-latency reduction in MPI path | BlueField-2/3 DPU, MPICH | MPI_Send/Recv communication | CPU/SoC/C-engine compression paths | Mandatory closest DPU system prior art; solves MPI message boundary, not transparent RNIC/RDMA WR boundary | Obsidian, OSTI, OpenAlex | verified | no | yes | unknown |
| [Compression Analysis for BlueField-2/-3 Data Processing Units: Lossy and Lossless Perspectives](https://par.nsf.gov/servlets/purl/10538184) | IEEE Micro / HOTI theme | 2024 | BF2/BF3 C-engine and SoC characterization | C-engine can give up to 26.8x compression speedup, but 90.4% overhead from staging/init; BF3 matrix differs by algorithm | BF2/BF3 DPU | seven HPC datasets, message-like traces | SoC software paths | Establishes the real DPU bottleneck: integration and data movement, not just codec kernel speed | Web, Obsidian | verified_by_url | no | yes | no |
| [DOCA Compress](https://docs.nvidia.com/doca/sdk/doca-compress/index.html) | NVIDIA docs | 2026 | Official hardware-accelerated compress/decompress API | Current docs list host/DPU memory regions and BF3 deflate/LZ4 decompression support; per-device capabilities must be queried | BlueField DPU | DOCA buffers | none/NA | Corrects a key assumption: do not assume all desired algorithms are compression-capable on BF3 C-engine | Web | verified_by_url | no | yes | yes |
| [NetZIP: Algorithm/Hardware Co-design of In-network Lossless Compression for Distributed Large Model Training](https://doi.org/10.1145/3725843.3756079) | MICRO | 2025 | Tensor-aware preprocessing plus NIC bump-in-the-wire lossless compression | Reports 35% lower training time; standard raw tensor codecs are ineffective or too slow | FPGA prototype + SimAI | gradients and activations for Llama/GPT-style training | LZ4/Snappy/Zstd/Deflate on CPU/GPU/SNIC, no compression | Closest training-side in-network lossless compression competitor; custom NIC hardware, not commodity BF3 RDMA-transparent path | Obsidian, ACM/ESF, OpenAlex | verified | no | yes | unknown |
| [ShadowServe: Interference-Free KV Cache Fetching for Distributed Prefix Caching](https://arxiv.org/abs/2509.16857) | arXiv | 2025 | SmartNIC-offloaded prefix-cache fetch data plane | Up to 2.2x lower loaded TPOT and 1.38x lower TTFT in <=20 Gbps scenarios | SmartNIC + LLM serving stack | distributed prefix caching | SOTA remote prefix fetching | Direct SmartNIC KV-transfer competitor; emphasizes offload and interference avoidance more than BF3 C-engine lossless compression | arXiv, Web | verified | yes | yes | unknown |
| [Efficient Remote KV Cache Reuse with GPU-native Video Codec](https://arxiv.org/abs/2602.09725) | SIGCOMM | 2026 | KVCodec using GPU-native media ASICs and codec-friendly tensor layout | Up to 3.51x TTFT reduction while preserving lossless accuracy | diverse NVIDIA GPUs | remote KV cache reuse | SOTA remote KV reuse methods | Crowds KV-cache compression angle; uses GPU media ASIC rather than DPU/RNIC | arXiv, OpenAlex | verified | yes | yes | unknown |
| [SplitZip: Ultra Fast Lossless KV Compression for Disaggregated LLM Serving](https://arxiv.org/abs/2605.01708) | arXiv | 2026 | GPU-friendly fixed-width exponent coding for BF16/FP8 KV tensors | 613.3 GB/s compression, 2181.8 GB/s decompression, up to 1.30x TTFT speedup | H200/Mooncake/SGLang-style serving | BF16/FP8 KV transfer | prior lossless codecs, raw transfer | Very recent direct KV lossless competitor; makes "new KV lossless codec" a crowded angle | arXiv | verified | yes | yes | unknown |
| [KVServe: Service-Aware KV Cache Compression for Communication-Efficient Disaggregated LLM Serving](https://arxiv.org/abs/2605.13734) | arXiv | 2026 | Offline Pareto profiling plus online bandwidth/SLO-aware compression controller | Up to 9.13x JCT speedup and 32.8x TTFT reduction in evaluated disaggregated serving scenarios | vLLM, A100/H100/RTX tiers, shaped networks | GSM8K, HumanEval, LongBench-style tasks | CacheGen, KIVI, DuoAttention, BF16 | Crowds the "tensor-type-aware policy" angle for KV serving; useful policy baseline | arXiv, Obsidian | verified | yes | yes | unknown |
| [P/D-Serve: Serving Disaggregated Large Language Model at Scale](https://arxiv.org/abs/2408.08147) | arXiv | 2024 | production disaggregated serving with optimized D2D KV transfer | 60% throughput, 42% TTFT-SLO, 46% D2D transfer-time improvements; 6.7x over aggregated baseline | Ascend/MindSpore commercial deployment | P/D serving, RoCE, D2D KV transfer | aggregated LLM serving | Shows KV transfer over RDMA is operationally central, but not compression-focused | arXiv | verified | yes | yes | unknown |
| [DistServe](https://arxiv.org/abs/2401.09670) | OSDI/arXiv | 2024 | disaggregated prefill/decode placement and resource optimization | 7.4x more served requests or 12.6x tighter SLO than SOTA while satisfying >90% requests | GPU cluster simulator/prototype | prefill/decode serving | colocated serving systems | Canonical P/D disaggregation workload source; communication caused by disaggregation is modeled, not compressed | arXiv | verified | yes | yes | unknown |
| [Mooncake](https://arxiv.org/abs/2407.00079) | arXiv | 2024 | KVCache-centric serving architecture and scheduler | Up to 525% simulated throughput improvement; 75% more real requests under workload | Kimi serving platform | long-context KV cache serving | baseline serving method | Practical KV-cache pool context for remote KV movement | arXiv | verified | yes | yes | unknown |
| [MemServe](https://arxiv.org/abs/2406.17565) | arXiv | 2024 | context caching + elastic distributed memory pool | Improves JCT and time-to-first-token through MemPool APIs and global scheduling | distributed serving instances | inter/intra-request KV reuse | serving baselines | Context for distributed KV cache movement and reuse | arXiv | verified | yes | yes | unknown |
| [TraCT](https://arxiv.org/abs/2512.18194) | arXiv | 2025 | CXL shared-memory KV transfer and rack-wide prefix-aware cache | Up to 9.8x average TTFT reduction, 6.2x P99 reduction, 1.6x peak throughput | Dynamo-like serving + CXL | rack-scale P/D serving | RDMA and DRAM caching baselines | Alternative to NIC/RDMA path; useful excluded competitor and stressor | arXiv | verified | yes | yes | unknown |
| [Deep Gradient Compression](https://arxiv.org/abs/1712.01887) | ICLR/arXiv | 2018 | lossy sparsification with momentum correction and warm-up | 270x-600x gradient size reduction without accuracy loss in studied tasks | GPU clusters | DNN training gradients | dense SGD | Non-goal competitor: lossy, convergence-risk path; helps motivate lossless only | arXiv | verified | yes | yes | yes |
| [Activations and Gradients Compression for Model-Parallel Training](https://arxiv.org/abs/2401.07788) | arXiv | 2024 | lossy TopK/AQ-SGD on model-parallel activations and gradients | Finds gradients need milder compression than activations; strong TopK can hurt performance | model-parallel training experiments | activations and gradients | no compression, error feedback | Negative evidence for blanket compression; lossy and not RNIC | arXiv | verified | yes | yes | unknown |
| [Accelerating Distributed Deep Learning using Lossless Homomorphic Compression](https://arxiv.org/abs/2402.07529) | arXiv | 2024 | lossless homomorphic compression compatible with in-network aggregation | Aims to merge worker compression with in-network aggregation | distributed DL | gradients / aggregation | standard collectives | Relevant to SHARP/in-network reduction compatibility; not DPU/RDMA transparent | arXiv | verified | yes | yes | unknown |
| [Quad Length Codes for Lossless Compression of e4m3](https://arxiv.org/abs/2602.17849) | arXiv | 2026 | hardware-friendly lossless codes for FP8 E4M3 | Simpler than Huffman; 13.9% compressibility vs 15.9% for Huffman | analytical/hardware design | E4M3 symbols | Huffman/universal codes | Relevant to FPGA/ASIC stretch path; not commodity BF3 | arXiv | verified | yes | yes | unknown |
| [Palladium](https://arxiv.org/abs/2505.11339) | arXiv | 2025 | DPU-enabled zero-copy multi-node RDMA serverless data plane | 20.9x RPS improvement and 21x latency reduction in best case | BlueField-like DPU + RDMA | serverless functions | CPU-bound data plane | Context for DPU RDMA offload patterns and RDMA isolation; not compression | arXiv | verified | yes | yes | unknown |
| [ROS2: RDMA-First Object Storage with SmartNIC Offload](https://arxiv.org/abs/2509.13997) | arXiv | 2025 | RDMA-first object storage with BF3 SmartNIC-offloaded client | BF3 offload can preserve RDMA efficiency; TCP on SmartNIC lags host | BF3 SmartNIC + DAOS | GPU-centric storage I/O | host DAOS client, TCP/RDMA | Context for DPU-resident RDMA services and why RDMA matters | arXiv | verified | yes | yes | unknown |
| [Revisiting Disaggregated LLM Serving for Performance and Energy Implications](https://arxiv.org/abs/2601.08833) | arXiv | 2026 | systematic P/D serving benchmark across KV transfer media and energy | Finds P/D benefits are not guaranteed; depend on load and transfer medium | GPU profiling + DVFS | disaggregated serving variants | colocated serving | Negative evidence: disaggregation/KV transfer optimization is workload dependent | arXiv | verified | yes | yes | unknown |

### Section 1b -- Newly surfaced competitors (post-run update 2026-05-29, WR-ZipGuard v2 redesign)

> Added after the original Workflow 1 run. These postdate the initial review and were
> surfaced while positioning WR-ZipGuard v2 against the latest collective-communication and
> KV-transfer compression work. See `docs/superpowers/specs/2026-05-29-wr-zipguard-v2-design.md`.

| Paper | Venue | Year | Method | Key Result | Eval Platform | Workload | Baseline | Relevance | Source | Verification | Preprint | Full Text | Artifact |
|---|---:|---:|---|---|---|---|---|---|---|---|---|---|---|
| [ZipCCL: Efficient Lossless Data Compression of Communication Collectives for Accelerating LLM Training](https://arxiv.org/abs/2604.27844) | arXiv | 2026 | GPU-side lossless exponent coding exploiting near-Gaussian tensor distribution; adaptive collective switching | Up to 1.35x comm-time reduction, 1.18x end-to-end training speedup on 64 GPUs (MoE + dense) | 64-GPU cluster | training collectives (activations/gradients/params) | NCCL, DietGPU/nvCOMP | Newest lossless collective compressor; **GPU-side, training only, no DPU/RDMA, no per-message gate** -- differentiates WR-ZipGuard's off-GPU/commodity-decompress + gate angle | Web, arXiv | verified_by_url | yes | yes | unknown |
| [UCCL-Zip: Lossless Compression Supercharged GPU Communication](https://arxiv.org/abs/2604.17172) | arXiv | 2026 | Lossless compression fused into GPU comm primitives (Uzip-P2P split-send pipeline; Uzip-NCCL persistent-kernel fusion) | Up to 47.5% faster RL weight sync; up to 10% lower vLLM inference latency; no app changes | GPU cluster | RL weight sync + LLM inference (vLLM) | NCCL | **Closest new competitor touching inference**; still **GPU-side, no DPU, not KV-transfer-specific, no profitability gate** -- reveals NCCL/compression incompatibility | Web, arXiv | verified_by_url | yes | yes | yes |
| [HACK: Homomorphic Acceleration via Compression of the KV Cache for Disaggregated LLM Inference](https://arxiv.org/abs/2502.03589) | arXiv | 2025 | Compute directly on quantized KV (homomorphic), skipping dequantization | Up to 70.9% JCT reduction vs disaggregated baseline; 52.3% vs SOTA KV quant | trace-driven disaggregated serving | disaggregated KV transfer | KV quantization methods | Same problem (KV transmission in disaggregation) but **lossy quantization + GPU compute** -- WR-ZipGuard is lossless bit-exact, off-GPU | Web, arXiv | verified_by_url | yes | yes | unknown |
| [NVIDIA ICMSP/CMX / BlueField-4 / NIXL / Dynamo](https://nvidianews.nvidia.com/news/nvidia-bluefield-4-powers-new-class-of-ai-native-storage-infrastructure-for-the-next-frontier-of-ai) | NVIDIA (CES 2026) | 2026 | BF4-managed KV-cache placement/offload across G1-G4 tiers (GPU mem, CPU mem, local NVMe, shared storage); Dynamo KVBM + NIXL orchestrate movement; DOCA-integrated | ~10x prefill (VAST DataStore); BF4 up to 800 Gbps | BlueField-4 DPU + RDMA + NVMe | disaggregated/agentic KV cache movement | GPU-resident KV | **Industrial occupant of "DPU moves KV off-GPU over RDMA"** but **moves bytes, no lossless compression, no per-WR gate** -- verified against primary sources 2026-06-12 (press release + dev blog + CMX page list only crypto/CRC engines in BF4 KV pipeline; NIXL BackendGuide/repo have zero data-plane compression; deep-research trace, 14 claims @ 3-0). NIXL has a pluggable backend arch (SB API + Plugin Manager) -> WR-ZipGuard can also be framed as a *pluggable gate* on the NIXL path, not only a competitor. BF4 is newer than our BF3 -- scope/positioning risk | NVIDIA newsroom, [dev blog](https://developer.nvidia.com/blog/introducing-nvidia-bluefield-4-powered-inference-context-memory-storage-platform-for-the-next-frontier-of-ai/), [CMX page](https://www.nvidia.com/en-us/data-center/ai-storage/cmx/), [NIXL repo](https://github.com/ai-dynamo/nixl), blocksandfiles | verified | n/a | n/a | n/a |

### Section 1c -- Literature refresh (post-run update 2026-07-06, after M1/M1.5/M2/M3)

> Three parallel web sweeps (KV-transfer/serving, DPU/NIC hardware, codecs/gating) covering
> ~2026-03 onward, run after M1.5 completed. Every row below was verified against its primary
> source (arXiv abstract or full-text HTML fetched directly) before inclusion; agent-reported
> numbers that could not be confirmed are flagged. Ratios α = compressed/original (lower is
> better) unless noted.

| Paper | Venue | Year | Method | Key Result | Eval Platform | Workload | Baseline | Relevance | Source | Verification | Preprint | Full Text | Artifact |
|---|---:|---:|---|---|---|---|---|---|---|---|---|---|---|
| [TRACE: Unlocking Effective CXL Bandwidth via Lossless Compression and Precision Scaling](https://arxiv.org/abs/2509.03377) | arXiv / IEEE TC (in press) | 2025-26 | **Lossless** channel-major disaggregated bit-plane layout + KV-specific transform + commodity entropy codecs, in a custom 7nm CXL-controller (SystemVerilog, 256 GB/s, +7.2% area) | **46.9% lossless BF16 KV reduction (alpha ~0.53)**, per-layer up to 2.69x; GPT-OSS-120B 4.24x throughput once KV spills to CXL | custom CXL controller RTL | BF16 KV + weights (+MXFP4) | generic CXL compression | **TOP new item — both threat and opportunity.** Breaks our implicit "byte-transpose+deflate ~= the floor": channel-major reordering exploits higher-order structure that order-0 byte entropy does not bound. But their transform is a layout permutation — potentially portable to our single-standard-deflate-stream/BF3 constraint (M1.6 tests this). Custom silicon vs our shipped-commodity decode is the positioning line | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | unknown |
| [SpectrumKV: Per-Token Mixed-Precision KV Cache Transfer for Prefill-Decode Disaggregated LLM Serving](https://arxiv.org/abs/2606.08635) | arXiv | 2026 | Per-token precision assignment (FP16 sinks / INT8 / INT4) for PD KV transfer; deployment-time NIAH probe gates INT4 tolerance | 50-62% TTFT reduction at 50% KV budget; ppl +1.97/-0.06/-0.44% vs PDTrim's +22-36% | GPU serving | PD-disaggregated KV transfer | PDTrim, uniform quant | Closest new problem-space neighbor (same PD-transfer bottleneck) but **lossy**; its tolerance-probe "gate" is accuracy-gating, not wire-time profitability-gating — sharpens both our lossless and our gate deltas | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | unknown |
| [VeriCache: Turning Lossy KV Cache into Lossless LLM Inference](https://arxiv.org/abs/2605.17613) | arXiv | 2026 | Draft tokens with compressed KV, verify against full KV in parallel (HBM-bound decode overlaps PCIe/network-bound full-KV fetch) | Up to 4x throughput vs full-KV **with bit-identical outputs** | GPU serving | long-context decode + remote prefix caching | full-KV inference | A different route to "lossless": semantics-level verification instead of bit-exact wire encoding. Must defuse: needs GPU draft+verify compute and the full KV still moves; ours is bit-exact on the wire with zero GPU involvement | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | unknown |
| [DFloat11: 70% Size, 100% Accuracy — Lossless LLM Compression via Dynamic-Length Float](https://arxiv.org/abs/2504.11651) | NeurIPS | 2025 | Dynamic-length entropy coding of BF16 driven by exponent frequency; custom GPU decompression kernel (SRAM LUTs) | ~30% lossless size reduction (alpha ~0.70 on weights); Llama-405B on one 8x80GB node | GPU | BF16 **weights** (not KV) | CPU offload | Missed in earlier sweeps; joins ZipNN/DietGPU in the "custom-decoder exponent entropy coding" lineage. alpha ~0.70 on weights matches our byte-transpose+deflate 0.70 on KV — evidence the exponent plane is *the* win everywhere | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | yes |
| [To Compress or Not? ... Exponent Concentration (ECF8)](https://arxiv.org/abs/2510.02676) | arXiv | 2025 | Theory: exponent entropy is provably low (alpha-stable distributions induced by SGD), bound ~FP4.67; ECF8 entropy-aware format | Up to 26.9% lossless weight memory saving, 177% throughput | LLMs+DiTs to 671B | weights | FP8 formats | **Free theoretical backing** for M1/M1.5's measured finding that the exponent plane carries all compressibility — cite to elevate our empirical floors to a principled claim | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | unknown |
| [KV Cache Transform Coding (KVTC)](https://arxiv.org/abs/2511.01815) | ICLR | 2026 | PCA decorrelation + adaptive quantization + entropy coding (nvCOMP deflate) for KV **storage** | Up to 20x (40x+ niche) compression, accuracy maintained | GPU | KV storage/reuse | eviction, quant, SVD | **Lossy** transform coding that happens to use deflate; storage- not transfer-focused. Defuse: "uses deflate" != bit-exact lossless wire path. **Watch item (2026-07-06): NVIDIA states KVTC "will integrate" into Dynamo's KV Block Manager with vLLM ecosystem support ([opensourceforu 2026-03](https://www.opensourceforu.com/2026/03/nvidia-brings-20x-memory-savings-to-open-source-llm-infrastructure/)) — planned, not shipped; if it lands, deflate-on-KV becomes mainstream practice (storage-side, lossy overall), which legitimizes deflate without touching our transfer-side bit-exact gate** | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | unknown |
| [NetSenseML: Network-Adaptive Compression for Distributed ML](https://arxiv.org/abs/2506.16235) | arXiv | 2025 | Congestion-reactive gating of gradient quantization/pruning/compression during **training** | 1.55-9.84x training throughput vs compression-enabled baselines under constrained BW | GPU cluster | training gradients | static compression | Nearest new gate-like work. Delta: reactive congestion heuristic on lossy gradient path vs our **measured per-WR break-even frontier** on a bit-exact DPU decompress path with bypass-on-risk | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | unknown |
| [Waiting to Decompress: The Economics of LLM-Based Compression](https://www.vldb.org/cidrdb/papers/2026/p34-kipf.pdf) | CIDR | 2026 | Cost model for **LLM-as-compressor** storage economics (compression cost vs storage savings) | LLM-based compression breaks even after ~10 years; GPU compress cost dominates | analytical | general data at rest | uncompressed storage | Weaker overlap than the title suggests: storage-at-rest economics of LLMs as codecs, NOT per-transfer tensor-compression profitability. Cite as adjacent economics framing; our wire-time break-even frontier remains unclaimed | CIDR proceedings | verified (located + scanned 2026-07-06) | no | yes | unknown |
| [SAC: Disaggregated KV Cache for Sparse Attention LLMs with CXL](https://arxiv.org/abs/2606.19746) | arXiv | 2026 | CXL cache-line-granular on-demand fetch of top-k KV entries (sparse attention); **no compression** | 2.1x throughput, 9.7x lower TTFT, 1.8x lower TBT vs RDMA (DeepSeek-V3.2/SGLang) | CXL testbed | sparse-attention KV fetch | RDMA full-fetch | CXL substrate competition (with TraCT, CXL-SpecKV): avoids the NIC hop entirely at rack scale. Pushes our positioning to multi-rack / bandwidth-constrained fabrics — consistent with M3's measured regime | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | unknown |
| [CXL-SpecKV: Disaggregated FPGA Speculative KV-Cache](https://arxiv.org/abs/2512.11920) | FPGA'26 (oral) | 2025-26 | CXL + FPGA speculative KV prefetch incl. an FPGA compression/decompression engine (losslessness unspecified in abstract) | Up to 4x bandwidth-requirement reduction, 3.2x throughput vs GPU-only, 2.8x memory cost | FPGA + CXL | datacenter KV serving | GPU-only | Custom-FPGA relative of our M4b path but on CXL; differentiator: our decompressor is *shipped commodity BF3*, zero new hardware at the receiver | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | yes (GitHub) |
| [Huff-LLM: End-to-End Lossless Compression for Efficient LLM Inference](https://arxiv.org/abs/2502.00922) | arXiv | 2025 | Bit-group Huffman so weights stay compressed everywhere incl. on-chip buffers | Lossless weight compression (bf16 ~1.37-1.38x per full text — unconfirmed from abstract) | HW-aware design | weights | uncompressed | Lineage item (custom decoder, weights); not KV, not transfer | arXiv | verified existence; ratio unconfirmed | yes | yes | unknown |
| [Unweight (Cloudflare)](https://blog.cloudflare.com/unweight-tensor-compression/) | Cloudflare blog | 2026 | Huffman on BF16 exponent byte with per-tensor top-16 palette; rare exponents verbatim per row; decompress in GPU shared mem feeding tensor cores | ~30% on MLP exponent streams; 13-22% whole-model, bit-exact; H100 kernels open-sourced | H100 | MLP **weights** | uncompressed | Industry adoption of exponent-palette entropy coding (weights). Same top-16-exponent trick as SplitZip; custom GPU decode. Strengthens "exponent coding is commodity knowledge; the open question is *where* to decode and *when* to bother" — our exact two contributions | Cloudflare | verified (post fetched 2026-07-06) | n/a | yes | yes |
| [TStore: Rethinking AI Model Hub with Tensor-Centric Compression](https://arxiv.org/abs/2604.17104) | arXiv | 2026 | Tensor-level fingerprinting/clustering + delta compression for model-hub storage | Substantial storage savings on real repositories | storage system | checkpoints/weights at rest | model-level dedup | Peripheral (storage dedup); cite only if reviewers raise checkpoint compression | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | unknown |
| [EVICPRESS: Joint KV-Cache Compression and Eviction](https://arxiv.org/abs/2512.14946) | arXiv | 2025 | **Lossy** joint compression+eviction placement across storage tiers via a quality/delay utility | Up to 2.19x TTFT at equal quality (12 datasets, 5 models) | GPU serving | KV tiering | compress-only / evict-only | Lossy policy relative of the gate idea (utility-driven placement); ours is bit-exact wire profitability | arXiv | verified (abstract fetched 2026-07-06) | yes | yes | unknown |
| [Bit-Plane Compression (BPC)](https://doi.org/10.1145/3007787.3001172) | ISCA | 2016 | Delta + bit-plane transpose + XOR (DBX) transform, then cheap hardware RLE/frequent-pattern encoders, cache-line granularity | ~2x effective memory bandwidth in many-core/GPU memory systems at memory-path hardware cost | GPU/many-core memory system | memory/link traffic (semantics-oblivious) | FPC/C-Pack-class hw compressors | **Ancestor of the hardware transform-before-cheap-codec lineage** (added 2026-07-06 while placing TRACE): same core insight as TRACE's bit-plane stage — transpose so same-significance bits across neighboring values become contiguous. TRACE = BPC's transposition + float-field disaggregation + tensor-semantic channel reorder (the only hardware-free step → ported as M1.6) + commodity entropy codecs in CXL silicon. Also explains M1.6's delta finding: BPC's delta pays because it feeds bit-level XOR+RLE; under byte-oriented deflate, delta HURTS (0.719 vs 0.697). Integer-leaning (paper concedes floats compress worse — the gap float-field-aware descendants fill). Cite as the lineage root in related work | ACM ([ISCA'16 PDF](https://lph.ece.utexas.edu/merez/uploads/MattanErez/isca2016_bpc.pdf), [NVIDIA Research](https://research.nvidia.com/publication/2016-06_bit-plane-compression-transforming-data-better-compression-many-core)) | verified (DOI + abstract checked 2026-07-06) | n/a | yes | n/a |

**Updates to known entries (verified against latest versions, 2026-07-06):**

- **SplitZip v3** (2026-06-23): BF16 KV compression ratio is **rho = 1.324x, i.e. alpha ~0.755** —
  *worse ratio than our BF3-decodable byte-transpose+deflate 0.70*, and its FP8_E5M2 result is only
  1.14x (alpha ~0.877) vs our raw-deflate 0.73. SplitZip wins throughput (613/2182 GB/s GPU) with a
  custom bitstream; we win ratio *and* commodity decode. This is a positioning gift: quote it.
- **UCCL-Zip v2** (2026-04-21): adds FP8 via 2xFP8→16-bit packing + joint exponent extraction into
  DietGPU ANS (custom bitstream): alpha bf16 **0.64**, fp8_e5m2 **0.70**, fp8_e4m3 **0.77** (also
  fp16 0.83, fp32 0.82). These are the honest "custom-decoder ceiling" numbers for the
  cost-of-commodity-decode comparison: our BF3-decodable path pays +0.06 (bf16 0.70 vs 0.64) and
  +0.03 (e5m2 0.73 vs 0.70).
- **BlueField-4 / ecosystem re-check (2026-07-06):** still **no hardware compress engine** in any
  public BF4/DOCA documentation (BF2 had compress+decompress; BF3 decompress-only; BF4 KV-pipeline
  accelerators remain crypto/CRC). No production lossless KV compression in
  vLLM/SGLang/Mooncake/NIXL/LMCache as of 2026-07; LMCache ships a *pluggable* SERDE compression
  interface and NIXL remains compression-free — both are concrete integration hooks for the gate.
  Re-verify BF4 at DOCA 3.x GA before submission.
- **"No production lossless KV compression" — precise form (second verification pass 2026-07-06,
  prompted by the challenge "haven't the GPU-codec papers been merged?"):** GPU-compression papers
  HAVE been merged, but everything merged is **lossy**. (a) **LMCache**: CacheGen is merged as a
  SERDE and is the *only* compression codec its docs list; mechanism = quantization + entropy
  coding of quantized values (paper reports ≤~2% accuracy delta) — not bit-exact
  ([serde docs](https://docs.lmcache.ai/kv_cache_optimizations/compression/index.html)).
  (b) **vLLM**: native KV "compression" today is FP8 KV-cache quantization (lossy); KVTC→Dynamo
  KVBM is announced as planned (2026-03), not shipped, and lossy overall (PCA + adaptive quant;
  only the final nvCOMP-deflate stage is lossless). (c) **SGLang**: HiCache is GPU/host/storage
  *tiering* (HiRadixTree, 3FS-style L3 backends) with no compression codec in the transfer path
  ([HiCache design](https://docs.sglang.io/advanced_features/hicache_design.html)). (d) The
  **lossless** GPU-codec papers — DietGPU (Meta research prototype), UCCL-Zip, SplitZip, ZipNN
  (weights/model files, HF-hub scenario), TRACE (custom silicon) — remain unmerged research code in
  every serving stack. Paper phrasing: **"what ships is lossy; lossless remains unshipped"** — never
  the attackable "no KV compression in production".

## Section 2 -- Problem-Anchored Clusters

### Cluster A: Raw RDMA bandwidth is still a first-order limit for LLM tensor movement

**Unresolved bottleneck**: LLM training and disaggregated serving both materialize large tensors across machines: gradients/activations in training, KV blocks in serving. P/D-Serve reports cluster-level RDMA D2D KV transfer as a major practical issue, and DistServe explicitly places P/D stages according to bandwidth. NetZIP shows that on lower-bandwidth cloud-like training nodes, tensor communication can dominate iteration time.

**Tried so far**: systems schedule around the bottleneck (DistServe, Mooncake, MemServe, P/D-Serve), compress on GPU/media ASICs (KVCodec, SplitZip), or design custom in-network compression hardware (NetZIP).

**Where they plateau**: scheduling reduces unnecessary movement but does not reduce bytes for unavoidable transfers; GPU codecs compete for GPU-side resources or assume framework hooks; NetZIP shows high-upside custom hardware but not commodity BF3 RNIC transparency.

### Cluster B: BF3 C-engine speed does not equal end-to-end compression benefit

**Unresolved bottleneck**: BlueField compression characterization shows the C-engine can be fast, but system overhead dominates unless initialization, memory registration, staging, and buffering are amortized. Current DOCA docs and characterization tables also show algorithm support is narrower than a blanket "DEFLATE/zlib/LZ4 compression" claim.

**Tried so far**: PEDAL solves the MPI message path by pre-initializing at `MPI_Init`, pooling buffers, and adding compact headers. That is a strong system idea, but it relies on MPI message boundaries and does not solve GPUDirect/NCCL/RDMA work-request granularity.

**Where it plateaus**: the next hard boundary is not "can the DPU compress a buffer"; it is "can a DPU resident path see the right tensor/message boundary, decide whether compression is worthwhile, and preserve RDMA ordering/completion semantics without modifying NCCL or the application?"

### Cluster C: KV-cache compression is suddenly crowded, but mostly above the RNIC

**Unresolved bottleneck**: KV cache transfer is now a visible bottleneck in P/D serving, remote prefix reuse, and distributed prefix caching. SplitZip, KVCodec, and KVServe all target this bottleneck in 2026.

**Tried so far**: KVCodec uses GPU-native media ASICs; SplitZip is a GPU-friendly lossless BF16/FP8 exponent codec; KVServe adds service-aware profile selection; ShadowServe moves prefix-cache fetches to a SmartNIC data plane.

**Where it plateau**: these systems mostly require serving-stack or GPU-side hooks. They do not answer whether commodity BF3/DPU compression can act transparently below the serving framework, nor whether RDMA-level compression can coexist with GPUDirect and QP completion semantics.

### Cluster D: Training-side lossless compression has strong custom-hardware prior art

**Unresolved bottleneck**: training tensors have enough structure to exploit, but standard raw-tensor lossless codecs are often ineffective or slow. NetZIP identifies BF16 exponent/mantissa structure and builds a custom NIC path.

**Tried so far**: NetZIP's byte/bit grouping plus LZ4 accelerator; homomorphic lossless compression for aggregation; lossy gradient sparsification.

**Where it plateaus**: a BF3 commodity path cannot assume NetZIP-like custom hardware. It must either use C-engine-supported algorithms, ARM software paths, or small FPGA/ASIC stretch components. That makes the commodity RNIC question narrower but still valuable.

### Cluster E: Static compression decisions are fragile

**Unresolved bottleneck**: compression profitability depends on tensor phase, message size, compressibility, bandwidth, GPU/CPU contention, and SLO. KVServe shows static KV compression profiles can be suboptimal or even harmful.

**Tried so far**: KVServe adds online service-aware control; PEDAL amortizes compression overhead for MPI; SplitZip chooses a fixed fast lossless codec; NetZIP uses tensor-aware preprocessing.

**Where it plateaus**: no existing system provides a BF3/RDMA work-request-level profitability gate that combines cheap compressibility sampling, DOCA context state, link pressure, and RDMA message-boundary safety.

## Section 2.5 -- Negative Evidence

| negative_id | claim | source | affected_methods | affected_assumption | confidence | linked_gaps |
|---|---|---|---|---|---|---|
| NE-1 | BF C-engine offload can be slower or marginal when initialization/staging dominates; reported overhead is 90.4% in characterization. | Compression Analysis; BlueField DPU Compression Papers Comparison | S1, naive DPU C-engine offload | "hardware compression speed alone determines end-to-end benefit" | high | G1, G2 |
| NE-2 | Standard lossless codecs on raw BF16 gradients/activations often give poor compression or net slowdown; custom tensor-aware layout/codec is needed. | NetZIP; SplitZip | S2, S3 generic raw-tensor codec use | "any lossless codec over raw tensor bytes will save enough bandwidth" | high | G1, G4 |
| NE-3 | Static KV compression can be suboptimal or harmful as bandwidth, workload, quality budget, and SLO change. | KVServe; Revisiting Disaggregated LLM Serving | S3, S4 static profile use | "one compression profile is safe across serving contexts" | medium | G1, G3 |
| NE-4 | P/D disaggregation and KV movement optimization do not guarantee speed or energy benefit; payoff depends on transfer medium and load. | Revisiting Disaggregated LLM Serving | S5 blanket disaggregation optimization | "KV transfer optimization always improves E2E performance" | medium | G3, G5 |

## Section 3 -- Structural Gaps

**Cross-domain transfer**

1. `PEDAL -> RDMA/NCCL`: PEDAL's core insight, amortize DOCA init and reuse buffers, has not been translated to RDMA WR or GPUDirect boundaries. This gap anchors `B3`, `B4`, and `G1`.
2. `KVServe -> DPU/RNIC`: KVServe's service-aware profitability model exists above the serving framework; the missing translation is a lower-level gate that works with RDMA link pressure, completion ordering, and DPU hardware state (`B2`, `B5`, `G3`).

**Contradictory findings**

1. NetZIP and SplitZip show tensor-specific lossless compression can help, while BlueField characterization shows generic DPU hardware offload can be defeated by fixed overhead. The contradiction is not about compressibility; it is about where the codec sits and what overheads are exposed (`NE-1`, `NE-2`, `G1`).

**Untested assumptions**

1. The brief assumes BF3 C-engine can handle the desired LZ4/zlib/DEFLATE compression path. Current DOCA docs and characterization tables require per-device support checks and show an asymmetric support matrix (`B3`, `G2`).
2. The brief assumes RNIC interception can remain transparent for GPUDirect/NCCL. The literature does not show a commodity BF3 design preserving RDMA ordering, completion, and remote memory layout while changing byte counts (`B4`, `G1`).

**Unexplored regimes**

1. Work-request-sized and page-sized LLM tensor chunks are under-characterized for BF3 C-engine profitability. Existing BlueField studies use HPC datasets and MPI-style messages, not BF16/FP8 KV/gradient blocks across RDMA QPs (`B3`, `B5`, `G2`).
2. Pipeline-parallel activation transfers may be an easier first regime than all-reduce: point-to-point, message-boundary-friendly, and still tensor-rich. This is less explored than gradient all-reduce and KV transfer (`B1`, `G4`).

**Unasked diagnostic questions**

1. What is the "compression break-even frontier" for BF3 under real LLM tensor distributions: minimum message size, minimum ratio, maximum allowed staging overhead, and link-rate threshold? (`G2`)
2. Can a DPU gate reliably reject non-profitable chunks quickly enough that failed compression attempts do not harm latency? (`G1`, `G3`)

## Section 4 -- Landscape Pack

### Topic Scope

- original_topic: In-RNIC Lossless Compression Engine for LLM Cross-Machine Communication from `idea-stage/RESEARCH_BRIEF.md`
- inferred_layer: interconnect/network + DPU/NIC data path + AI infrastructure runtime boundary
- non_goals: lossy compression, tape-out ASIC, general-purpose non-ML network compression, modifying NCCL/RDMA drivers as the primary route
- most defensible narrowed scope: commodity BF3/DPU RDMA work-request-granular lossless compression gating and characterization for LLM tensor traffic; custom FPGA/ASIC codec only as a stretch comparison

### Bottleneck Evidence

#### Bottlenecks

| bottleneck_id | bottleneck | context | decisive_metrics | representative_papers | current_status | residual_gap |
|---|---|---|---|---|---|---|
| B1 | RDMA link saturation for LLM training tensors | gradients, activations, and collectives move GB-scale tensors across nodes | step time, collective time, link utilization, bytes sent | [NetZIP](https://doi.org/10.1145/3725843.3756079), [DGC](https://arxiv.org/abs/1712.01887) | Custom hardware and lossy software routes exist; commodity RNIC path is open | no commodity BF3 RDMA-transparent lossless path with proven break-even |
| B2 | KV-cache transfer dominates disaggregated serving | P/D separation and remote prefix reuse turn KV into explicit network payload | TTFT, TPOT, JCT, request throughput, bytes per request | [DistServe](https://arxiv.org/abs/2401.09670), [P/D-Serve](https://arxiv.org/abs/2408.08147), [KVServe](https://arxiv.org/abs/2605.13734) | GPU/media and runtime policy solutions are advancing quickly | DPU/RNIC-transparent solution space not resolved |
| B3 | BF3 compression offload overhead and algorithm support mismatch | DOCA init, buffer staging, and per-device algorithm matrix dominate naive C-engine use | compression throughput, exposed latency, CPU/ARM utilization, staging time | [Compression Analysis](https://par.nsf.gov/servlets/purl/10538184), [PEDAL](https://doi.org/10.1109/IPDPS57955.2024.00040), [DOCA Compress](https://docs.nvidia.com/doca/sdk/doca-compress/index.html) | PEDAL solves MPI-style path; docs require capability checks | no RDMA/GPUDirect-aware buffer reuse + capability-aware path |
| B4 | RDMA semantic preservation under byte-count-changing compression | RDMA RC/UD, QP ordering, completions, and remote memory placement assume exact payload semantics | correctness, completion order, memory layout, fallback latency | [Palladium](https://arxiv.org/abs/2505.11339), [ROS2](https://arxiv.org/abs/2509.13997) | DPU RDMA offload is feasible in other domains | no demonstrated transparent compression shim for LLM RDMA tensors |
| B5 | Phase-specific compressibility variance | BF16/FP8 KV, gradients, activations, and optimizer traffic expose different entropy | compression ratio, reject-rate, false-positive compression attempts | [SplitZip](https://arxiv.org/abs/2605.01708), [NetZIP](https://doi.org/10.1145/3725843.3756079), [KVServe](https://arxiv.org/abs/2605.13734) | Tensor-aware codecs/policies exist above or inside custom hardware | no BF3/RDMA-local compressibility atlas and gate |

#### Solution Attempts

| solution_id | bottleneck_ids | mechanism_family | representative_papers | best_outcome | missing_piece |
|---|---|---|---|---|---|
| S1 | B3 | DPU compression library + MPI integration | [PEDAL](https://doi.org/10.1109/IPDPS57955.2024.00040) | up to 101x compression time improvement and 88x latency reduction | MPI message boundary; not RNIC/GPUDirect transparent |
| S2 | B1, B5 | custom in-network tensor-aware lossless codec | [NetZIP](https://doi.org/10.1145/3725843.3756079), [Quad Length Codes](https://arxiv.org/abs/2602.17849) | NetZIP reports 35% lower training time | custom hardware/prototype path; commodity BF3 gap remains |
| S3 | B2, B5 | GPU-side KV compression codecs | [SplitZip](https://arxiv.org/abs/2605.01708), [KVCodec](https://arxiv.org/abs/2602.09725) | SplitZip 613.3 GB/s encode and 1.30x TTFT; KVCodec 3.51x TTFT | serving/GPU hook required; not RNIC transparent |
| S4 | B2, B5 | service-aware adaptive KV compression policy | [KVServe](https://arxiv.org/abs/2605.13734) | up to 9.13x JCT and 32.8x TTFT improvements | above-runtime policy; no DPU state or RDMA completion semantics |
| S5 | B2 | disaggregated serving scheduling / KV pool | [DistServe](https://arxiv.org/abs/2401.09670), [P/D-Serve](https://arxiv.org/abs/2408.08147), [Mooncake](https://arxiv.org/abs/2407.00079), [MemServe](https://arxiv.org/abs/2406.17565) | DistServe 7.4x requests; P/D-Serve 46% D2D transfer-time improvement | schedules movement but rarely compresses unavoidable bytes |
| S6 | B2, B4 | SmartNIC/DPU data plane offload | [ShadowServe](https://arxiv.org/abs/2509.16857), [Palladium](https://arxiv.org/abs/2505.11339), [ROS2](https://arxiv.org/abs/2509.13997) | ShadowServe 2.2x lower loaded TPOT; Palladium 20.9x RPS | not commodity BF3 C-engine tensor compression |

### Evaluation Canon

#### Platforms

| platform_id | evaluation_platform | access_readiness | supported_workloads | validates_refs | artifact_access_path | platform_limitations |
|---|---|---|---|---|---|---|
| EC-P1 | BF3 DPU + DOCA Compress microbenchmark harness | ready | EC-W4, EC-W5 | B3, S1 | lab BF3 + DOCA SDK; NVIDIA docs | capability matrix must be queried; LZ4/zlib compression may not be hardware-supported |
| EC-P2 | A100 multi-node RDMA/GPUDirect cluster | ready | EC-W1, EC-W2, EC-W3, EC-W5 | B1, B2, B4, B5 | user-listed validation resource | may need counters/tracing to observe QP/message boundaries; NCCL internals should remain unmodified |
| EC-P3 | vLLM/Mooncake/SGLang-style disaggregated serving harness or LLMServingSim | small_adapter_needed | EC-W3 | B2, S3, S4, S5 | LLMServingSim repo; serving framework adapters | simulator fidelity and KV trace realism must be checked |
| EC-P4 | SimAI collective simulator | small_adapter_needed | EC-W1, EC-W2 | B1, S2 | SimAI repo | compression model must be injected carefully; not a replacement for BF3 measurements |
| EC-P5 | FPGA/ASIC codec prototype or RTL model | major_bringup_needed | EC-W1, EC-W3, EC-W4 | B1, B5, S2 | none_found in current repo | stretch only under 3-month timeline |
| EC-P6 | SmartNIC prefix-cache offload prototype | unknown | EC-W3 | B2, S6 | ShadowServe artifact unknown | may not match available BF3 C-engine path |

#### Workloads

| workload_id | workload | bottlenecks | workload_characteristics | representative_papers | representativeness_limits |
|---|---|---|---|---|---|
| EC-W1 | NCCL/SimAI gradient all-reduce and all-gather tensors | B1, B4, B5 | BF16/FP16 gradient/activation tensors; Llama/GPT-style model scales; ring/tree collectives | [NetZIP](https://doi.org/10.1145/3725843.3756079), [DGC](https://arxiv.org/abs/1712.01887) | simulator may miss real GPUDirect/RDMA staging overhead |
| EC-W2 | pipeline-parallel activation point-to-point transfer | B1, B4, B5 | per-layer activation messages between adjacent pipeline stages; easier WR boundary than all-reduce | [NetZIP](https://doi.org/10.1145/3725843.3756079), [Activations and Gradients Compression](https://arxiv.org/abs/2401.07788) | fewer public LLM-specific traces |
| EC-W3 | disaggregated serving KV-cache transfer / remote prefix reuse | B2, B4, B5 | BF16/FP8 KV blocks; long-context 32K-128K; P/D separation; prefix-cache fetch | [KVServe](https://arxiv.org/abs/2605.13734), [SplitZip](https://arxiv.org/abs/2605.01708), [KVCodec](https://arxiv.org/abs/2602.09725) | synthetic traces may hide multi-tenant tails |
| EC-W4 | captured LLM tensor chunk compressibility corpus | B3, B5 | BF16/FP8 KV, gradients, activations, optimizer states; chunk sizes 4KB-16MB | [Compression Analysis](https://par.nsf.gov/servlets/purl/10538184), [SplitZip](https://arxiv.org/abs/2605.01708) | must be produced locally; no universal public corpus |
| EC-W5 | RDMA WR/QP microbenchmarks | B3, B4 | message size, MTU, QP count, RC/UD, link rate, GPUDirect vs host buffers | [Palladium](https://arxiv.org/abs/2505.11339), [ROS2](https://arxiv.org/abs/2509.13997) | microbenchmarks must be tied back to real tensor phases |

### Competitive Landscape

selection_rule: ranked by overlap with commodity interconnect lossless compression and LLM tensor movement, then by recency and reported end-to-end evidence.

#### Competitors

| competitor_id | papers | B*_scope | eval_tier | what_it_solves | residual_gap | NE_link |
|---|---|---|---|---|---|---|
| C1 | [PEDAL](https://doi.org/10.1109/IPDPS57955.2024.00040), IPDPS 2024 | B3 (adj: B4) | MPI messages @ BF2/BF3 DPU | Shows how to amortize DOCA init and buffer overhead in a real communication stack | RDMA WR/GPUDirect transparency and LLM tensor policies remain -> G1 | NE-1 |
| C2 | [NetZIP](https://doi.org/10.1145/3725843.3756079), MICRO 2025 | B1 (adj: B5) | LLM training tensors @ custom NIC/FPGA + SimAI | Shows tensor-aware lossless compression can reduce large-model training time | commodity BF3 C-engine and RDMA semantic path not covered -> G2 | NE-2 |
| C3 | [SplitZip](https://arxiv.org/abs/2605.01708), arXiv 2026 | B2 (adj: B5) | KV transfer @ GPU serving stack | Shows lossless BF16/FP8 KV compression can be extremely fast on GPUs | no DPU/RNIC-transparent path; GPU resource/interference question remains -> G3 | NE-2 |

#### Excluded Competitors

| excluded_paper | shared_B* | eval_tier | excluded_reason | revisit_condition |
|---|---|---|---|---|
| [KVServe](https://arxiv.org/abs/2605.13734) | B2, B5 | KV compression policy @ vLLM/GPU | policy competitor rather than commodity RNIC/DPU datapath; still important baseline for adaptive decisions | include directly if selected idea focuses on runtime policy rather than RDMA path |
| [KVCodec](https://arxiv.org/abs/2602.09725) | B2, B5 | remote KV reuse @ GPU media ASIC | strong KV compression baseline but not lossless generic RNIC/DPU path | include directly for KV-only idea |
| [ShadowServe](https://arxiv.org/abs/2509.16857) | B2, B4 | prefix caching @ SmartNIC | SmartNIC data-plane competitor but not BF3 C-engine tensor compression | include directly if selected idea becomes SmartNIC KV fetch rather than RDMA compression gate |
| [TraCT](https://arxiv.org/abs/2512.18194) | B2 | CXL KV transfer @ rack scale | alternative transfer substrate; not compression/RDMA | include if argument becomes "avoid NIC hop" |

### Gap Seeds

| gap_id | bottleneck_id | source_gap_ref | mechanism_hint | validation_target | decisive_metric | kill_reason |
|---|---|---|---|---|---|---|
| G1 | B4 | B4.residual_gap + NE-1 | RDMA WR-granular DPU compression gate with persistent DOCA contexts, pre-registered buffers, and bypass-on-risk semantics | EC-P1 + EC-P2; EC-W5 then EC-W1/EC-W3 | exposed latency reduction at fixed correctness and no ordering violation | if staging/bypass overhead exceeds saved wire time for >80% target tensors |
| G2 | B3 | B3.residual_gap | BF3 LLM tensor compression atlas and break-even frontier across C-engine/SoC/software paths | EC-P1 + EC-W4 | break-even frontier predicts wins/losses within 10% | if no LLM phase has positive break-even under available BF3 support |
| G3 | B2 | S4.missing_piece + NE-3 | DPU-local profitability model using link pressure, chunk compressibility sample, and DOCA queue state | EC-P2 + EC-P3 + EC-W3 | TTFT/TPOT improvement without GPU-side codec interference | if KVServe/SplitZip always dominate and DPU adds no isolation benefit |
| G4 | B1 | S2.missing_piece + NE-2 | activation-first DPU compression path for pipeline-parallel point-to-point messages | EC-P2 + EC-P4 + EC-W2 | step-time reduction on activation transfer with no model accuracy change | if activation tensors are not compressible enough or WR granularity is inaccessible |
| G5 | B2 | NE-4 | negative-result diagnostic: when not to disaggregate/compress KV under realistic link/load/sequence regimes | EC-P3 + EC-W3 | decision boundary that avoids false-positive compression/disaggregation | if boundary is already captured by KVServe/Revisiting without new platform insight |
