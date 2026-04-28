# LLM Workloads and Infrastructure Bottlenecks 解析

**文档背景与上下文**：
本文档旨在深度解析 ARIS 项目 `GEMINI.md` 配置中 `Domain Profile` 章节的一项关键指令。该指令划定了当前 AI 基础设施研究的**范围边界（Scope）**与**破局思路**。

> **原文引用 (`GEMINI.md` > Domain Profile)**:
> "The default emphasis is LLM inference and serving, but the agent must also track training, fine-tuning, checkpointing, multimodal/VLM, reasoning, RAG, and agentic multi-call workloads when they affect infrastructure bottlenecks."

以下是站在“AI 基础设施研究者”视角的硬核技术解读，基于 Oracle Pro (GPT-5.4-Pro) 的深度分析整理而成。

---

## 核心主旨：什么是“基础设施瓶颈的偏移”？

在计算机体系结构与系统研究的语境下，这句配置的核心含义是：**“大语言模型（LLM）的常规推理与服务（Inference & Serving）是目前研究的默认基本盘，但你绝不能仅仅盯着这个场景。当训练、微调、检查点、多模态、推理模型、RAG 和智能体工作流这些相对复杂的负载导致了系统出现新的性能瓶颈时，你必须敏锐地捕捉并研究它们。”**

不要死磕在一个 7B 模型跑几十个词的传统推理场景下卷 GPU 算子优化。如果你能发现 RAG 流水线中 SSD 访存拖慢了 GPU 利用率，或者发现多智能体调度下 KV Cache 产生大量重复命中可以被卸载（Offload）到 CXL 内存，或者因为频繁 Checkpoint 导致的 PCIe 带宽堵塞——这些“导致瓶颈转移”的地方，往往才是顶级学术会议（如 MICRO, ISCA, OSDI）最喜欢看到的高价值跨层系统（Cross-layer）设计切入点。

---

## 一、 这些是当前重要的 LLM 负载吗？

**非常重要，且它们代表着工业界和学术界目前的真实痛点。**

1. **Benchmark 的风向已经转变**：2026年4月发布的 MLPerf Inference v6.0 已经明确将多模态视觉模型（VLM）、复杂推理/代码模型（DeepSeek-R1/GPT-OSS 120B）等纳入了一等公民基准测试中 [3][4]。简单的单轮短文本对话已经无法代表当前 LLM 系统的全貌。
2. **生产环境的常态**：在真实的生产环境中，纯粹的从头训练（Pre-training）可能掌握在少数巨头手里 [5]，但**微调（Fine-tuning, 如 LoRA/QLoRA）**则是成千上万中小企业每天都在跑的负载 [6][7]。而 **RAG（检索增强生成）** 和 **Agentic（多工具调用智能体）** 则是目前让 LLM 真正落地的最核心的业务形态 [8]。

---

## 二、 为什么它们会对基础设施产生“不同于标准推理”的性能瓶颈？

标准的大模型推理（Standard LLM Inference），在计算机体系结构上的瓶颈模型已经相对清晰且固化：
> **典型的瓶颈是**：Prefill（首 token 计算阶段）通常是**算力受限（Compute-bound）**的矩阵乘法；而 Decode（逐个 token 生成阶段）则是严重的**内存带宽受限（Memory-bandwidth-bound）**，因为需要反复将庞大模型权重和不断增长的 KV Cache 数据从 HBM (显存) 中搬运到计算单元 [1][2]。

但是，当引入这句话中提到的这些其他负载时，**系统的木桶效应（瓶颈）会立刻发生大规模的偏移**：

### 1. RAG（检索增强生成）与 Agentic Workflow（智能体工作流）
* **标准的推理**：`Prompt -> LLM -> Answer`
* **RAG / Agent 推理**：`User Query -> Embedding 计算 -> 向量数据库(Vector DB)搜索 -> 结果重排(Reranking) -> Context 组装 -> LLM Prefill -> LLM Decode -> Tool 调用网络通信 -> 返回...`
* **瓶颈偏移**：原本你以为性能卡在 GPU 的显存带宽上，但在 RAG/Agent 负载下，系统的关键路径（Critical Path）突然变成了**异构数据流（Heterogeneous Dataflow）的流转**。瓶颈可能转移到了 CPU 的标量计算、SSD/内存的随机访存（搜索阶段）、网络请求的尾延迟（Tail Latency），或者因为塞入了巨量检索文档而导致原本不痛不痒的 **Prefill 阶段算力和 KV Cache 容量瞬间爆表**。此外，多轮循环还让**跨轮次调度（Workflow Scheduling）和 KV Cache 复用**变得至关重要 [14][15][16]。

### 2. 多模态 / VLM（视觉语言模型）
* **标准推理**：输入是文本 token。
* **VLM 推理**：引入了高分辨率图像或视频帧，这些必须经过 Vision Encoder（例如 ViT）编码成极大量的视觉 Token。
* **瓶颈偏移**：这种“视觉 token 洪流”极大地改变了 Workload 的几何结构（Token Geometry）。它把系统瓶颈硬生生拉回了前序的**多媒体预处理、主机到设备（PCIe/NVLink）的数据搬运带宽**，以及极其夸张的**首轮长序列 Prefill 算力墙（Visual Memory Wall）** [12][13]。

### 3. 复杂推理模型（Reasoning Models, 例如 DeepSeek-R1, O1 等）
* **标准推理**：输出数量和输入数量存在一定比例。
* **Reasoning 推理**：它要在内部进行极长的思维链（Chain-of-Thought, CoT）、多树搜索甚至自我验证。输出（Decode）的长度被极其拉长。
* **瓶颈偏移**：因为 Decode 阶段占据了绝对主导地位，导致这类模型的测试时计算量（Test-time compute）方差极大。它的瓶颈是对持续的 **Decode 带宽挤压** 以及更严苛的**动态准入控制（Dynamic Admission Control）和延迟感知调度**的挑战 [8]。

### 4. 训练、微调（Fine-tuning）与检查点（Checkpointing）
* **推理**：只需要存放权重 + KV Cache。
* **训练/微调**：系统必须额外存放激增的内存：激活值（Activations）、梯度（Gradients）和优化器状态（Optimizer States）。
* **瓶颈偏移**：对于训练，瓶颈变成了跨卡/跨机网络的**集合通信带宽（All-reduce/All-gather）**以及 **HBM 容量** [9][10]。对于微调（如大规模 LoRA 托管），瓶颈则变成了“如何在一台机器上快速切换和调度成百上千个小的 Adapter 权重而不引发内存碎片（HBM Fragmentation）” [11]。而 Checkpointing 则直接引出了纯纯的**分布式存储阵列 I/O 的瞬时突发带宽（Burst Storage I/O）**问题。

---

## 三、 研究方法论总结（Methodological Rules）

对于 AI 基础设施研究者而言，上述分析推导出了几个关键的系统性原则：

1. **不要对单一的 Benchmark 形状产生过拟合（Do not overfit to one benchmark shape）**：单轮短文本的 serving 结果无法预测长上下文 RAG、VLM、推理或 Agentic 负载下的性能。
2. **分离 Prefill 和 Decode**：它们有着不同的算术强度、批处理行为、内存压力和 SLO 影响。将它们合并成一个平均的 “tokens/s” 指标会掩盖真正的瓶颈 [1]。
3. **测量工作流级别的指标（Measure workflow-level metrics）**：对于现代应用，相关指标包括 TTFT（首字延迟）、TPOT（输出字延迟）、p95/p99 延迟、SLO 下的有效吞吐（Goodput）、每次成功任务的成本、每次请求的能耗、缓存命中率、向量检索延迟、检查点开销、恢复时间以及模型 FLOP 利用率。
4. **关注模型状态的生命周期（Model state lifetime matters）**：KV Cache、LoRA Adapter、检索索引、优化器状态、检查点和工具输出有着不同的生命周期和复用模式。架构选择应由哪些状态是热数据、冷数据、共享数据、持久化数据或关键容灾数据来驱动。
5. **异构协同设计至关重要（Heterogeneous co-design matters）**：优化 GPU 矩阵乘法本身可能无法改善端到端的任务延迟，必须跨 CPU、内存、网络和存储进行分析。
6. **瓶颈日益动态化（The bottleneck is increasingly dynamic）**：这使得准入控制、调度、缓存和解耦与原始加速器的峰值 FLOPS 一样重要。

---

## 参考文献与扩展阅读

- [1] [Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve](https://arxiv.org/html/2403.02310v1)
- [2] [Efficient Memory Management for Large Language Model Serving with PagedAttention (vLLM)](https://arxiv.org/abs/2309.06180)
- [3] [MLCommons Releases New MLPerf Inference v6.0 Benchmark Results](https://mlcommons.org/2026/04/mlperf-inference-v6-0-results/)
- [4] [A new GPT-OSS benchmark and DeepSeek R1 updates for latency-optimized reasoning](https://mlcommons.org/2026/03/mlperf-inference-gpt-oss/)
- [5] [MLCommons Releases MLPerf Training v5.1 Results](https://mlcommons.org/2025/11/training-v5-1-results/)
- [6] [LoRA selected as the fine-tuning technique added to MLPerf Training v4.0](https://mlcommons.org/2024/06/lora-fine-tuning-mlperf-training-v4-0/)
- [7] [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [8] [The Cost of Dynamic Reasoning: Demystifying AI Agents and Test-Time Scaling from an AI Infrastructure Perspective](https://arxiv.org/abs/2506.04301)
- [9] [ZeRO: Memory Optimizations Toward Training Trillion Parameter Models](https://arxiv.org/abs/1910.02054)
- [10] [MegaScale: Scaling Large Language Model Training to More Than 10,000 GPUs](https://www.usenix.org/conference/nsdi24/presentation/jiang-ziheng)
- [11] [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314)
- [12] [Efficient Inference for Large Vision-Language Models: Bottlenecks, Techniques, and Prospects](https://arxiv.org/html/2604.05546v1)
- [13] [Call for Submission: Qwen3 VL MoE for MLPerf Inference v6.0](https://mlcommons.org/2026/02/vlm-inference-shopify/)
- [14] [Sutradhara: An Intelligent Orchestrator-Engine Co-design for Tool-based Agentic Inference](https://arxiv.org/html/2601.12967v3)
- [15] [Efficient LLM Serving for Agentic Workflows: A Data Systems Perspective](https://arxiv.org/html/2603.16104v1)
- [16] [AIOS: LLM Agent Operating System](https://openreview.net/forum?id=L4HHkCDz2x)
