# M1 实验清单 — Real Tensor Compressibility Corpus

> **目标**: 测量真实 LLM tensor 的 lossless 压缩率分布，判断是否存在盈利性压缩区间。
> **Block**: Block 1 (EXPERIMENT_PLAN.md)
> **Tracker ID**: R003
> **优先级**: MUST-RUN (FIRST — 最便宜的 go/no-go)
> **预计耗时**: hours–1 day
> **日期**: 2026-06-05

---

## 0. 前置检查 (Pre-flight)

- [ ] **0.1** 确认 Python 环境 (3.10+) 和依赖库可用
  ```bash
  python3 -c "import numpy; import torch; print('ok')"
  ```
- [ ] **0.2** 安装压缩库绑定
  ```bash
  pip install zstandard lz4 python-snappy  # zstd, lz4, snappy (参考)
  # deflate 用 Python stdlib zlib
  ```
- [ ] **0.3** 确认磁盘空间 ≥ 50GB（用于存储生成的 tensor corpus）
- [ ] **0.4** 确认 GPU 可用（用于生成 FP8/BF16 tensor）或 fallback 到 CPU 生成
- [ ] **0.5** 记录环境信息（写入 M1 输出目录）
  ```yaml
  python_version: ...
  torch_version: ...
  zstd_version: ...
  lz4_version: ...
  cpu: ...
  gpu: ... (if available)
  ```

---

## 1. Tensor Corpus 生成

### 1.1 覆盖矩阵

#### 1.1.1 Primary Axis: KV Cache Tensors（主要）

| 维度 | 取值 | 理由 |
|---|---|---|
| **Phase** | Prefill KV, Decode KV | Prefill 大批量连续写入，Decode 单 token 追加；熵分布不同 |
| **Tensor 类型** | Key tensor (K), Value tensor (V) | K/V 统计特性不同（K 经过 RoPE 旋转，V 不经过） |
| **Dtype** | BF16, FP8_E4M3, FP8_E5M2 | 覆盖主流推理精度；FP8 粒度更粗可能更难压缩 |
| **模型规模** | 7B, 13B (有 GPU 则加 70B) | 不同层数/维度，head_dim 不同影响字节模式 |
| **序列长度** | 1K, 4K, 8K, 32K, 128K | 短序列 KV 块小，长序列 KV 块大；长上下文的 KV cache 是核心场景 |
| **层深度** | Layer 0 (浅), Layer N/2 (中), Layer N-1 (深) | 不同层的 K/V 分布可能不同（浅层更通用，深层更专门化） |
| **块大小 (chunk)** | 4KB, 16KB, 64KB, 256KB, 1MB, 4MB, 16MB, 64MB | 覆盖从单 attention head 块到完整 KV 层的范围 |

- [ ] **1.1.1a** 生成 Prefill K tensor 矩阵（遍历 dtype × model_size × seq_len × layer_depth × chunk_size）
- [ ] **1.1.1b** 生成 Prefill V tensor 矩阵
- [ ] **1.1.1c** 生成 Decode K tensor 矩阵（Decode 的单 token KV 追加模式 — 可能需要用拼接模拟）
- [ ] **1.1.1d** 生成 Decode V tensor 矩阵

#### 1.1.2 Supplementary Axis: 训练 Tensor（次要，optional）

| 维度 | 取值 | 理由 |
|---|---|---|
| **Tensor 类型** | Gradients, Activations, Optimizer states (Adam moment1, moment2) | 补充验证训练场景 (SimAI axis) |
| **Dtype** | FP32, BF16, FP8_E4M3 | 训练常用精度 |
| **模型规模** | 7B, 13B | 与主要 axis 对齐 |
| **块大小** | 64KB, 256KB, 1MB, 4MB, 16MB | 训练通信 chunk 通常较大 |

- [ ] **1.1.2a** 生成 Gradient tensor 矩阵
- [ ] **1.1.2b** 生成 Activation tensor 矩阵
- [ ] **1.1.2c** 生成 Optimizer state tensor 矩阵

### 1.2 生成方法

#### 方法 A: 合成生成（确定性，可复现）

- [ ] **1.2.1** 实现 `generate_kv_tensor(phase, tensor_type, dtype, model_cfg, seq_len, layer_idx)` 
  - 使用 HuggingFace model config 获取 head_dim, num_heads, num_layers
  - 对于 K tensor：模拟 RoPE 旋转后的分布（正弦位置编码叠加到随机初始化权重）
  - 对于 V tensor：直接使用截断正态分布（模仿真实 V 的统计特性）
  - 记录生成 seed，保证可复现
- [ ] **1.2.2** 实现 `generate_training_tensor(tensor_type, dtype, model_cfg, microbatch_size)`
  - Gradients：从截断正态分布采样（模仿反向传播梯度）
  - Activations：从 ReLU/GELU 后的分布采样
  - Optimizer states：从 Adam moment 分布采样

#### 方法 B: 真实捕获（优先，如果可行）

- [ ] **1.2.3** 尝试从 vLLM / SGLang 推理运行中 hook KV cache tensor
  - Hook 点：attention 层 forward 之后，KV cache 写入之前
  - 优先于合成生成（如果可行）
- [ ] **1.2.4** 如果 vLLM hook 不可行，降级为 PyTorch 手动 forward KV 提取
  ```python
  # 最小化方案：用 HuggingFace model 跑一个 batch，提取各层 K/V
  model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-7b-hf")
  # forward pass with output_attentions=True, 记录每层 K/V
  ```

#### 方法 C: 公开数据集

- [ ] **1.2.5** 搜索是否有公开的 LLM KV cache tensor dataset（如 LLMServingSim 的 trace）
- [ ] **1.2.6** 如果有，下载并纳入 corpus

### 1.3 Corpus 完整性检查

- [ ] **1.3.1** 每个 (phase, tensor_type, dtype, model_size, seq_len) 组合至少生成 10 个独立 sample（不同 seed）
- [ ] **1.3.2** 验证 chunk 边界对齐（chunk 大小 N 意味着取 tensor 的前 N 字节或 reshape 后的 N 字节连续块）
- [ ] **1.3.3** 检查 tensor 熵的多样性：计算每个 chunk 的字节级 Shannon 熵，确认覆盖低熵到高熵范围
  - 预期：FP8 高熵（>7 bits/byte），BF16 中高熵（~6-7 bits/byte）
  - 如果所有样本熵 > 7.5 → 基本不可压缩 → 可能直接 go/no-go 红灯
- [ ] **1.3.4** Corpus manifest 生成：记录每个 chunk 的元数据
  ```json
  {
    "chunk_id": "prefill_K_bf16_7b_8k_layer16_1MB_seed42",
    "phase": "prefill",
    "tensor_type": "K",
    "dtype": "bf16",
    "model_size": "7B",
    "seq_len": 8192,
    "layer_idx": 16,
    "chunk_size_bytes": 1048576,
    "shannon_entropy_bits_per_byte": 6.82,
    "generation_method": "synthetic",
    "seed": 42
  }
  ```

---

## 2. 压缩测量协议

### 2.1 Codec 矩阵

| Codec | Level / Variant | 备注 |
|---|---|---|
| **deflate (zlib)** | 1, 6, 9 | 标准格式，BF3 硬件解压支持 ✅ |
| **LZ4** | fast (acceleration=1), HC (level=9) | 标准格式，BF3 硬件解压支持 ✅ |
| **zstd** | 1, 3, 19 | 参考 baseline（BF3 不支持 zstd 解压，但对比参考价值高） |
| **snappy** | default | 参考 baseline（Google 内部常用，轻量级） |
| **none (raw)** | — | 基准：原始大小 |

- [ ] **2.1.1** 确认 deflate/zlib 级别映射
  - Level 1: 最快，压缩比最低
  - Level 6: zlib 默认，平衡
  - Level 9: 最慢，压缩比最高
- [ ] **2.1.2** 确认 LZ4 变体
  - LZ4 fast: `lz4.compress(data, compression_level=1)` — 亚 GB/s 延迟
  - LZ4 HC: `lz4.compress(data, compression_level=9)` — ~100-300 MB/s，更高压缩比
- [ ] **2.1.3** 确认 zstd 级别
  - Level 1: 快速
  - Level 3: 默认
  - Level 19: 高压缩（可能非常慢，仅作参考）

### 2.2 测量协议（每个 chunk × 每个 codec × 每个 level）

- [ ] **2.2.1** 预热: 每个 codec 在启动时跑 3 次 warmup（丢弃结果，让 CPU cache / branch predictor 预热）
- [ ] **2.2.2** 正式测量: 每个 (chunk, codec, level) 跑 5 次独立 compress，记录：
  ```json
  {
    "original_size_bytes": 1048576,
    "compressed_size_bytes": 523456,
    "compression_ratio": 0.499,
    "compress_time_us": [2340, 2310, 2370, 2290, 2350],
    "compress_time_us_p50": 2340,
    "compress_time_us_p99": 2370,
    "compress_throughput_mbps": 448.0,
    "checksum_original": "sha256:abc123...",
    "checksum_compressed": "sha256:def456..."
  }
  ```
- [ ] **2.2.3** 验证无损往返：对每个 compressed blob 执行 decompress，逐字节对比原始数据，记录 bit-exact 与否
- [ ] **2.2.4** 记录每次 compress 的 wall-clock 时间（`time.perf_counter_ns()`）和 CPU 时间

### 2.3 内存/缓存控制

- [ ] **2.3.1** 每个 measurement batch 之间 `gc.collect()` + 清空 filesystem cache（如果可能）
- [ ] **2.3.2** 将 chunk 数据 pin 到内存中，避免 swap
- [ ] **2.3.3** 固定 CPU affinity（`taskset` 或 `os.sched_setaffinity`），减少 NUMA 噪声
- [ ] **2.3.4** 关闭 turbo boost / 固定 CPU 频率（如果权限允许）以减少方差；否则至少记录当前 governor

---

## 3. 统计分析计划

### 3.1 描述性统计（每个 tensor 配置 × 每个 codec）

- [ ] **3.1.1** 压缩率分布
  - mean, median, p25, p75, p90, p99 compression ratio
  - Histogram (40 bins, 0–1.0 ratio range)
  - Kernel density estimate (KDE) overlay
- [ ] **3.1.2** 压缩吞吐量分布
  - mean, p50, p99 compress throughput (MB/s, input side)
- [ ] **3.1.3** 按 phase 分组对比
  - Prefill KV vs Decode KV 的 compression ratio 是否有显著差异？
  - 使用 Mann-Whitney U test（非参数，不假设正态分布）

### 3.2 维度归因分析

- [ ] **3.2.1** 主效应分析：哪个维度对 compression ratio 影响最大？
  - ANOVA / Eta-squared: dtype vs phase vs tensor_type vs model_size vs chunk_size
  - 预期：dtype (FP8 vs BF16) 和 chunk_size 是主要影响因素
- [ ] **3.2.2** 交互效应：dtype × phase 交互是否显著？
  - 例如，FP8 Prefill K 是否比 BF16 Decode V 更难压缩？
- [ ] **3.2.3** Chunk size 效应
  - Small (4KB–64KB) vs Medium (256KB–1MB) vs Large (4MB–64MB)
  - LZ4/deflate 在更大块上有更多冗余可挖掘；zstd 受益最大

### 3.3 盈利性阈值分析（初步）

- [ ] **3.3.1** 计算"盈利性压缩比阈值"作为带宽和压缩吞吐量的函数：
  ```
  α_threshold(B, C, T_fixed, S) = 1 - B * (S/C + T_fixed) / S
  ```
- [ ] **3.3.2** 设定三种场景的参数范围：

  | 场景 | 压缩吞吐 C | 带宽 B | 固定开销 T_fixed | 典型 chunk S | α_threshold |
  |---|---|---|---|---|---|
  | **悲观** (SW compress, 25 Gbps) | 500 MB/s | 3.1 GB/s | 50 μs | 1 MB | ~0.38 |
  | **保守** (SW compress, 100 Gbps) | 500 MB/s | 12.5 GB/s | 50 μs | 1 MB | < 0 (不可盈利) |
  | **乐观** (FPGA compress, 100 Gbps) | 50 GB/s | 12.5 GB/s | 20 μs | 1 MB | ~0.75 |
  | **激进** (FPGA compress, 400 Gbps) | 100 GB/s | 50 GB/s | 20 μs | 4 MB | ~0.50 |
  | **极激进** (FPGA compress, 400 Gbps) | 100 GB/s | 50 GB/s | 20 μs | 64 MB | ~0.50 |

  **关键结论**: 软件压缩在 ≥100 Gbps 下不可能盈利（B/C > 1）。M1 的压缩率阈值应面向 FPGA 场景：**ratio ≤ 0.5–0.75 即可盈利**。

- [ ] **3.3.3** 绘制 α_threshold 热力图（x = chunk_size, y = bandwidth, color = profitable ratio ceiling）
- [ ] **3.3.4** 将实测压缩率分布叠加到热力图上，标注"可行区"

### 3.4 Go/No-Go 决策规则

- [ ] **3.4.1** **GREEN**: 至少一个 tensor phase × codec 组合的 p50 压缩率 ≤ 0.75（乐观 FPGA 阈值），且该 phase 覆盖 ≥20% 的 KV 传输量 → 进入 M2
- [ ] **3.4.2** **YELLOW**: 仅在大 chunk (≥16 MB) 或仅 zstd level 19 等"慢" codec 下达标 → 进入 M2 但标注风险（盈利窗口窄）
- [ ] **3.4.3** **RED**: 所有 phase × codec 组合的 p50 压缩率 > 0.85 → 停止，考虑 negative-result paper
  - 问：FP8/BF16 的高熵是否导致所有 lossless codec 失败？
  - 问：是否有其他场景（非 KV）可压缩？
- [ ] **3.4.4** **UNEXPECTED**: 如果软件压缩 + 低带宽 (< 25 Gbps) 场景下某些 chunk 可盈利 → 记录为 M4a 的潜在演示场景

---

## 4. 输出产物

### 4.1 数据文件

- [ ] **4.1.1** `m1_outputs/compressibility_corpus.parquet` — 完整测量数据，每行一个 (chunk, codec, level) 测量
  - Schema: `chunk_id, phase, tensor_type, dtype, model_size, seq_len, layer_idx, chunk_size_bytes, shannon_entropy, codec, level, original_size, compressed_size, ratio, compress_time_us_p50, compress_time_us_p99, compress_throughput_mbps, checksum_original, checksum_compressed, is_bit_exact`
- [ ] **4.1.2** `m1_outputs/corpus_manifest.parquet` — Chunk 元数据（1.3.4）
- [ ] **4.1.3** `m1_outputs/threshold_analysis.json` — 3.3 节的计算结果

### 4.2 图表

- [ ] **4.2.1** **Figure 1a**: 压缩率分布直方图（按 phase × dtype × codec 分面）
  - x = compression ratio, y = count, faceted by (tensor_type: K/V) × (phase: prefill/decode)
  - color = codec (deflate-6, lz4-fast, zstd-3, raw)
  - 虚线标注 α = 0.5 和 0.75 阈值
- [ ] **4.2.2** **Figure 1b**: 压缩率 vs chunk size 散点图
  - x = chunk_size (log scale), y = compression ratio, color = codec, shape = dtype
  - 叠加 loess 平滑趋势线
  - 结论用一句话：随着 chunk 增大，压缩率是否显著改善？
- [ ] **4.2.3** **Figure 1c**: 压缩吞吐量 vs 压缩率 trade-off
  - x = compress_throughput_mbps (log scale), y = compression_ratio
  - 每个点 = 一个 codec × level, 用 convex hull 标注 Pareto 前沿
  - 标注 BF3 支持的 codec（deflate, LZ4）vs 不支持的（zstd）
- [ ] **4.2.4** **Figure 1d**: 盈利性热力图
  - x = chunk_size (log), y = bandwidth (Gbps), color = α_threshold (profitable ratio ceiling)
  - 叠加 3 条 contour 线：实测 p25 / p50 / p75 压缩率对应的 profitable boundary
- [ ] **4.2.5** **Table 1**: 摘要表 — 每个 phase × dtype × codec 的压缩率 p50/p90，标注是否超过阈值

### 4.3 报告

- [ ] **4.3.1** `m1_outputs/M1_REPORT.md` — 包含：
  1. 执行摘要（能否盈利性压缩？GREEN/YELLOW/RED）
  2. 关键发现（哪个 tensor phase 最可压缩？哪个 codec 最优？）
  3. 盈利性分析
  4. 对 M2/M3 的建议参数范围
  5. 限制和注意事项

---

## 5. 执行顺序和预计耗时

| 步骤 | 内容 | 预计耗时 | 依赖 | 可并行 |
|---|---|---|---|---|
| 0 | 前置检查和环境搭建 | 30 min | — | — |
| 1.1 | 合成 KV tensor 生成 | 1–2 hours | 0 | — |
| 1.2 | 真实捕获尝试 | 2–4 hours | 0 | 1.1 |
| 2.1 | 压缩测量 (deflate + LZ4) | 3–6 hours | 1.1 or 1.2 | 跨 codec 可并行 |
| 2.2 | 压缩测量 (zstd + snappy) | 2–4 hours | 1.1 or 1.2 | 2.1 |
| 3.1–3.2 | 统计分析 | 1–2 hours | 2.1, 2.2 | — |
| 3.3–3.4 | 阈值分析和决策 | 1 hour | 3.1 | — |
| 4 | 图表和报告 | 2–3 hours | 3 | — |
| **总计** | | **12–22 hours** | | |

并行策略：tensor 生成后，deflate/LZ4/zstd 测量可以在不同机器/进程上并行跑。

---

## 6. 风险和缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 真实 KV tensor 无法获取（无 GPU / vLLM 不可用） | 中 | 中 | 降级到合成生成；在报告中明确标注限制 |
| 所有 tensor 均不可压缩 (ratio > 0.9) | 中高 | 高 | 这就是 M1 要回答的问题；RED 决策并 pivot |
| 合成 tensor 分布与真实 tensor 差异大 | 中 | 中 | 至少用 HuggingFace model forward 提取几个真实 KV block 做对比验证 |
| 压缩测量噪声大（CPU 频率波动） | 低 | 低 | 5 次测量 + 固定 CPU freq + warmup |
| 大 chunk (64MB) 生成内存不足 | 低 | 中 | 限制大 chunk 的 sample 数量（每配置 3 个而非 10 个） |
| FP8 tensor 生成不标准（E4M3 vs E5M2 差异） | 中 | 低 | 两种格式都生成，分别测量 |

---

## 7. 给 M3 (LLMServingSim Sweep) 的输出接口

M1 的输出需要直接可注入 M3 的 simulator。确保：

- [ ] **7.1** 每个 tensor phase × dtype × size bucket 提供压缩率的 **分布参数**（不仅仅是点估计）
  ```json
  {
    "phase": "prefill",
    "tensor_type": "K",
    "dtype": "bf16", 
    "size_bucket": "1MB-4MB",
    "codec": "deflate-6",
    "ratio_distribution": {
      "type": "beta",  // Beta 分布拟合 [0,1] 区间的压缩率
      "alpha": 2.3,
      "beta": 1.7,
      "p50": 0.62,
      "p90": 0.78
    }
  }
  ```
- [ ] **7.2** 提供 codec 的压缩吞吐量 CPA (cycles-per-byte) 模型参数（供 M3 中的延迟模型使用）
  ```json
  {
    "codec": "deflate-6",
    "cpa_mean": 12.4,  // CPU cycles per input byte
    "cpa_std": 1.2,
    "fixed_overhead_us": 15.0
  }
  ```
- [ ] **7.3** 明确标注哪些结果是 **synthetic** 哪些是 **captured**，M3 需要据此调整置信度

---

## 8. 检查清单总览（快速扫描版）

```
[ ] 0.1–0.5  环境就绪
[ ] 1.1       合成 KV tensor corpus 生成（至少 500 个 chunk）
[ ] 1.2       尝试真实 tensor 捕获（vLLM hook 或 HF forward）
[ ] 1.3       Corpus 完整性验证 + 熵检查
[ ] 2.1–2.2   deflate(1,6,9) + LZ4(fast,HC) + zstd(1,3,19) 全量测量
[ ] 2.3       无损往返验证通过
[ ] 3.1–3.2   压缩率分布 + 维度归因分析完成
[ ] 3.3       盈利性阈值计算（3 种场景 × chunk size sweep）
[ ] 3.4       Go/No-Go 决策输出 (GREEN / YELLOW / RED)
[ ] 4.1       数据文件输出 (.parquet + .json)
[ ] 4.2       5 张图 + 1 张表 生成
[ ] 4.3       M1_REPORT.md 完成
[ ] 7.1–7.3   M3 接口数据准备
```

---

## 附录 A: 盈利性阈值数学推导

### 基本不等式

设 chunk 大小为 S (bytes)，链路带宽为 B (bytes/s)，压缩吞吐量为 C (input bytes/s)，解压吞吐量为 D (input bytes/s)，压缩比为 α = compressed_size / original_size，固定开销（staging、metadata、DMA setup）为 T_fixed。

**无压缩传输时间**: T_raw = S / B

**压缩路径传输时间**: T_comp = S / C + α·S / B + α·S / D + T_fixed

**盈利条件**: T_comp < T_raw

展开：
```
S / C + α·S / B + α·S / D + T_fixed < S / B
α·S / B + α·S / D < S / B - S / C - T_fixed
α·S · (1/B + 1/D) < S/B - S/C - T_fixed
α < (S/B - S/C - T_fixed) / (S · (1/B + 1/D))
α < (1/B - 1/C - T_fixed/S) / (1/B + 1/D)
```

### 简化形式（当 D ≫ B 时，即解压不成为瓶颈）

如果 BF3 解压吞吐 D ≫ B（解压快于传输），则 1/D → 0：
```
α < 1 - B/C - B·T_fixed/S
```

### 关键洞察

1. **软件压缩 (C ≈ 0.5 GB/s)**：如果 B > 0.5 GB/s（即 > 4 Gbps），则 B/C > 1 → α < 负数 → **永不可盈利**（任何 S）
2. **FPGA 压缩 (C ≈ 50–100 GB/s)**：如果 B = 12.5 GB/s (100 Gbps)，则 B/C ≈ 0.125–0.25 → α < 0.75–0.875 → **有盈利窗口**
3. **Chunk 大小效应**：B·T_fixed/S 随 S 增大而减小 → **大 chunk 盈利窗口更宽**

### M1 的实际意义

M1 测量的是 α 的分布。将实测 α 分布与上述阈值比较，即可判断：
- 是否需要 FPGA 级别的压缩吞吐才能盈利？
- 哪些 chunk size 和 tensor phase 有最大的盈利概率？
- 是否存在"软件压缩 + 低带宽"的特殊盈利场景（例如跨 region KV 传输）？
