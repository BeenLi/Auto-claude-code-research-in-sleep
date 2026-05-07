# Idea Discovery Report

**Direction**: Lossless Communication Compression  
**Generated**: 2026-05-07T06:07:21Z  
**Pipeline**: research-lit → idea-creator → novelty-check → research-review → research-refine-pipeline  
**Ideas evaluated**: 10 generated → 6 survived filtering → 4 received handoff plans → 1 recommended  
**Language**: zh

---

## Executive Summary

本轮结论很硬：**不要把主 idea 放在 generic collective/KV/network lossless compression**。截至 2026-05-07，NetZIP、ZipCCL、UCCL-Zip、SplitZip、ZipServ、Quad Length Codes 已经把“压通信 payload 本身”的显性空间占得很满。最值得推进的是：

> **C-Share: Multi-Resource Fairness for Shared Lossless Communication Compression on DPUs/NICs**

它把压缩从“每条 flow 的优化”转成“多租户基础设施服务”：DPU/NIC compression engine 同时消耗 compressed input bytes、original/output bytes、engine cycles、DMA/host-memory traffic。现有 per-flow compression、Rx expansion budgeting 和 DPU QoS 都没有把这些资源放进同一个公平性/准入控制模型。外部 gpt-5.5 reviewer 给出 **5/6, confidence high**，但明确要求：至少要有 trace replay + analytical model + 最小 DPU/engine microbenchmark 或硬件 sanity check，不能只停在抽象调度。

---

## Literature Landscape

Phase 1 产物见 `idea-stage/LITERATURE_REVIEW.md`。核心判断如下：

- `NetZIP` 已经覆盖 NIC/FPGA in-network lossless compression for training traffic。
- `ZipCCL`、`UCCL-Zip`、`SplitZip` 把 GPU collective、P2P、KV-transfer compression 做到非常近的直接竞品区。
- `ZipServ`、`Quad` 说明硬件友好的 fixed-format decode/placement 是关键，但 codec-only novelty 风险高。
- `BlueField/PEDAL` 与 2026-05-06 的 SmartNIC DPU offload characterization 说明：DPU/NIC 侧 compression 的真正瓶颈往往是 engine invocation、DMA、on-card/host memory traffic 和服务隔离。
- 因此结构性缺口是 **shared compression service accounting and fairness**，不是单点 compression ratio。

---

## Generated Ideas

### Idea 1: C-Share — Multi-Resource Fairness for Shared Lossless Communication Compression on DPUs/NICs — RECOMMENDED

- **Idea shape**: 把 DPU/NIC 上的 lossless compressor/decompressor 当作多租户共享服务，而不是 per-flow acceleration block。C-Share 跟踪四类资源：compressed input bytes、original/decompressed output bytes、engine cycles、DMA/host-memory traffic；用 original-byte credits、engine-time tokens、output-byte caps、age buckets 形成硬件可实现的准入/调度器。目标是避免高压缩比租户、checkpoint burst 或 KV burst 在共享 compression service 中制造 noisy-neighbor 和 tail latency collapse。
- **Overall merit**: 1 — 方向新，能把已有 compression works 的盲点转成架构/系统问题；正负结果都能改变 DPU/NIC compression service 设计判断。
- **core_baseline**: CB3 FIFO DPU compression service; CB4 ratio-greedy compression; CB5 per-flow compressed communication; CB6 current Rx expansion budgeter; CB7 DPU QoS without compression hints.
- **canon_mapping**: platform=[EC-P1, EC-P7, EC-P6 optional, EC-P3 optional]; workload=[EC-W4, EC-W1, EC-W2, EC-W3].
- **metrics**: SLO-goodput and p99 latency under tenant mix; secondary: fairness index, engine occupancy, output bytes admitted/dropped, DMA/host-memory bytes, compressed/original byte throughput.
- **target_validation_style**: analytical_model + simulator_evaluation + optional prototype_measurement.
- **evaluation_target_clarity**: clear.
- **evaluation_target_feasibility**: high for first signal; medium for full reviewer-grade package if BlueField hardware is unavailable.
- **baseline_reproducibility**: requires_reimplementation.
- **evaluation_environment_access**: ready for analytical/trace replay; unknown for DPU hardware.
- **idea_adapter_cost**: moderate_adapter.
- **pilot_runtime_cost**: minutes_to_hours.
- **Expected outcome**: Show FIFO/wire-byte/ratio-greedy schedulers can improve aggregate throughput while violating tenant SLOs or causing output/DMA bursts; C-Share trades a small throughput cost for substantially lower p99 and better fairness.
- **Feasibility**: existing `experiments/rx-expansion` analytical machinery can be generalized; synthetic and public LLM communication profiles can seed traces; optional BlueField/PEDAL-style C-engine parameters can calibrate engine service time.
- **Estimated effort**: days for P0/P1; weeks for hardware sanity.
- **Risk**: MEDIUM.
- **handoff_to_workflow_1_5**: ready.
- **platform_access_path**: extend local analytical model + trace replay first; add DPU C-engine microbench if hardware appears.
- **main_blocker**: none for first signal; hardware_access for full validation.
- **Novelty check**: PROCEED WITH CAUTION. Closest prior: NetZIP, ZipCCL/UCCL-Zip, BlueField/PEDAL, DPU QoS/fair scheduling. Differentiator: multi-resource compression-service fairness and admission, not compression algorithm.
- **Reviewer score**: 5/6, confidence high.
- **Reviewer's likely objection**: “This is just multi-resource scheduling applied to compression.” The defense must show compression creates a distinct resource vector and failure mode not captured by generic DRF/QoS.
- **Why we should do this**: It is the only candidate that meaningfully escapes the crowded codec/library lane while staying close to available ARIS simulation assets.

#### Evaluation Handoff Plan

- **core_baseline**: CB3, CB4, CB5, CB6, CB7.
- **canon_mapping**: platform=[EC-P1, EC-P7, EC-P6 optional]; workload=[EC-W4, EC-W1, EC-W2, EC-W3].
- **metrics**: SLO-goodput, p99 latency, fairness index, engine occupancy, DMA/host-memory bytes.
- **target_validation_style**: analytical_model + simulator_evaluation.
- **evaluation_target_clarity**: clear.
- **evaluation_target_feasibility**: high first-signal / medium full.
- **baseline_reproducibility**: requires_reimplementation.
- **evaluation_environment_access**: ready for first signal.
- **idea_adapter_cost**: moderate_adapter.
- **pilot_runtime_cost**: minutes_to_hours.
- **platform_access_path**: `experiments/rx-expansion` generalized into compression-service simulator.
- **main_blocker**: none for P0/P1; hardware_access for P3.
- **handoff_to_workflow_1_5**: ready.

### Idea 2: Compressibility-Aware Expert-Parallel Token Exchange — BACKUP

- **Idea shape**: 对 MoE expert-parallel dispatch/combine traffic 进行 compressibility-aware packing/routing，保持 activation bit-exact，但把 token grouping、codebook reuse 和 network path selection 绑定到 compressibility hints。
- **Overall merit**: 2 — MoE EP 是热门 LLM infra bottleneck，但 DeepEP/UCCL-EP/UCCL-Zip 已经非常近。
- **core_baseline**: CB1, CB5; new_baseline_with_rationale=DeepEP/UCCL-EP where available.
- **canon_mapping**: platform=[EC-P5, EC-P7]; workload=[EC-W1, EC-W4].
- **metrics**: EP token exchange latency, p99, network bytes, codebook overhead.
- **target_validation_style**: simulator_evaluation.
- **evaluation_target_clarity**: partial.
- **evaluation_target_feasibility**: medium.
- **baseline_reproducibility**: open_source_system.
- **evaluation_environment_access**: small_adapter_needed.
- **idea_adapter_cost**: major_system_change.
- **pilot_runtime_cost**: one_to_two_days.
- **Risk**: MEDIUM-HIGH.
- **handoff_to_workflow_1_5**: needs_canon_clarification.
- **main_blocker**: unclear_comparison_target.
- **Novelty check**: PROCEED WITH CAUTION. UCCL-EP/UCCL-Zip overlap is strong; must prove token compressibility/routing failure mode is distinct.

### Idea 3: DCA-Aware Compression Placement for SmartNIC DPU Offload — BACKUP

- **Idea shape**: 以 2026 SmartNIC DPU offload 的 memory-to-communication ratio 和 no-DCA DRAM traffic amplification 为问题锚，建立 GPU/CPU/DPU/NIC compression placement model，决定何时让 DPU C-engine 处理通信 payload，何时保持 GPU/host-side compression。
- **Overall merit**: 2 — 新 evidence 很强，但容易被认为 placement/roofline 工程化。
- **core_baseline**: CB2, CB3, CB5.
- **canon_mapping**: platform=[EC-P1, EC-P3, EC-P6]; workload=[EC-W1, EC-W2, EC-W3].
- **metrics**: E2E latency, DRAM/DMA bytes, engine occupancy, GPU idle.
- **target_validation_style**: analytical_model + prototype_measurement.
- **evaluation_target_clarity**: partial.
- **evaluation_target_feasibility**: medium if hardware access exists; unknown otherwise.
- **baseline_reproducibility**: paper_only / hardware-dependent.
- **evaluation_environment_access**: unknown.
- **idea_adapter_cost**: moderate_adapter.
- **pilot_runtime_cost**: one_to_two_days.
- **handoff_to_workflow_1_5**: designed_not_run.
- **main_blocker**: hardware_access.
- **Novelty check**: PROCEED WITH CAUTION. Best as C-Share ablation/extension rather than standalone idea.

### Idea 4: Checkpoint/Model-Load Compression Placement Controller — DEFERRED

- **Idea shape**: 对 LLM checkpoint writes 和 model-load/weight streaming，在 GPU nvCOMP、CPU LZ4/Zstd、DPU C-engine、NIC FPGA、storage-side compression 之间做 placement roofline and runtime policy。
- **Overall merit**: 3 — practical but likely incremental.
- **core_baseline**: CB2, CB8.
- **canon_mapping**: platform=[EC-P1, EC-P3, EC-P5, EC-P6]; workload=[EC-W2, EC-W5].
- **metrics**: checkpoint time, model-load time, storage/network bytes, GPU idle.
- **target_validation_style**: analytical_model.
- **evaluation_target_clarity**: clear.
- **evaluation_target_feasibility**: high for model, medium for system.
- **handoff_to_workflow_1_5**: designed_not_run.
- **main_blocker**: low_overall_merit.
- **Novelty check**: CAUTION. NVIDIA nvCOMP and storage compression materials make standalone novelty weak.

### Idea 5: Trace-Guided Codebook Reuse for Recurrent LLM Communication — BACKUP / DEFERRED

- **Idea shape**: 利用 layer/step/request 级通信分布稳定性，在 NIC/DPU 侧复用小 codebook，减少在线统计和 header overhead；适用于 gradients、KV、expert tokens。
- **Overall merit**: 3 — plausible but close to SplitZip calibrated codebooks and ZipCCL exponent coding.
- **core_baseline**: CB5.
- **canon_mapping**: platform=[EC-P5, EC-P7]; workload=[EC-W1, EC-W3].
- **metrics**: codebook hit rate, ratio, compression latency, E2E speedup.
- **target_validation_style**: simulator_evaluation.
- **evaluation_target_clarity**: partial.
- **evaluation_target_feasibility**: medium.
- **handoff_to_workflow_1_5**: needs_canon_clarification.
- **main_blocker**: unclear_comparison_target.

### Idea 6: Compression-Aware Collective Schedule Selection — DEFERRED

- **Idea shape**: 选择 ring/tree/all-to-all/reduce-scatter 变体时纳入 compression ratio、codec latency、network congestion，使 schedule 不只按 message size 决策。
- **Overall merit**: 3 — useful，但 ZipCCL/UCCL-Zip already adaptive；hardware novelty weak.
- **core_baseline**: CB1, CB5.
- **canon_mapping**: platform=[EC-P5]; workload=[EC-W1].
- **target_validation_style**: simulator_evaluation.
- **evaluation_target_feasibility**: high.
- **handoff_to_workflow_1_5**: designed_not_run.
- **main_blocker**: low_overall_merit.

---

## Eliminated Ideas

| Idea | Category | Reason | Revisit condition |
|---|---|---|---|
| Generic NIC-side lossless compression for gradients/activations | already_done | NetZIP directly covers algorithm/hardware co-design in NIC datapath | Only revisit with a new control-plane or fairness boundary |
| Generic GPU collective lossless compression | already_done | ZipCCL and UCCL-Zip are direct 2026 competitors | Only revisit if evaluating them as baselines |
| Lossless KV-cache transfer compression | already_done | UCCL-Zip and SplitZip are too close and very recent | Only revisit as workload for shared-service scheduling |
| New e4m3/BF16 lossless codec only | low_overall_merit | Quad/ZipServ/SplitZip occupy hardware-friendly codec space | Revisit only with hardware-service interaction |
| Pure checkpoint compression tool | low_overall_merit | NVIDIA nvCOMP-style workflow makes implementation too engineering-heavy | Revisit as workload inside C-Share |

---

## Deferred / Designed-Not-Run Ideas

| Idea | Reason deferred | Required clarification or platform path |
|---|---|---|
| DCA-aware placement | hardware_access | Need BlueField/DPU or reliable DPU memory traffic counters |
| Checkpoint/model-load placement | low_overall_merit | Need non-obvious algorithmic insight beyond roofline placement |
| EP token exchange | unclear_comparison_target | Need DeepEP/UCCL-EP/UCCL-Zip baseline availability and token traces |
| Trace-guided codebook reuse | prior_work_overlap | Need evidence codebooks remain stable in a way SplitZip/ZipCCL do not exploit |

---

## Evaluation Handoff Summary

| Idea | overall_merit_score | evaluation_target_feasibility | baseline_reproducibility | evaluation_environment_access | idea_adapter_cost | pilot_runtime_cost | core_baseline | canon_mapping | metrics | target_validation_style | evaluation_target_clarity | handoff_to_workflow_1_5 | main_blocker |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|
| C-Share | 1 | high | requires_reimplementation | ready | moderate_adapter | minutes_to_hours | CB3/CB4/CB5/CB6/CB7 | platform=[EC-P1,EC-P7]; workload=[EC-W4,EC-W1,EC-W2,EC-W3] | SLO-goodput, p99, fairness, engine occupancy | analytical_model + simulator_evaluation | clear | ready | none |
| EP token exchange | 2 | medium | open_source_system | small_adapter_needed | major_system_change | one_to_two_days | CB1/CB5/DeepEP | platform=[EC-P5,EC-P7]; workload=[EC-W1,EC-W4] | EP latency, bytes, p99 | simulator_evaluation | partial | needs_canon_clarification | unclear_comparison_target |
| DCA-aware placement | 2 | unknown | paper_only | unknown | moderate_adapter | one_to_two_days | CB2/CB3/CB5 | platform=[EC-P1,EC-P3,EC-P6]; workload=[EC-W1,EC-W2,EC-W3] | memory traffic, latency, engine occupancy | analytical_model + prototype_measurement | partial | designed_not_run | hardware_access |
| Checkpoint placement | 3 | medium | open_source_system | small_adapter_needed | moderate_adapter | one_to_two_days | CB2/CB8 | platform=[EC-P1,EC-P5,EC-P6]; workload=[EC-W2] | checkpoint time, GPU idle | analytical_model | clear | designed_not_run | low_overall_merit |

---

## Refined Proposal

- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Tracker: `refine-logs/EXPERIMENT_TRACKER.md`
- Pipeline summary: `refine-logs/PIPELINE_SUMMARY.md`

---

## Next Steps

- [ ] `/experiment-bridge` should create `refine-logs/EVALUATION_CONTRACT.md` for C-Share.
- [ ] First run should be P0 analytical/trace replay only; no hardware claim.
- [ ] Add optional BlueField/DPU microbenchmark only after P0/P1 shows unfairness exists.
- [ ] Use `/auto-review-loop` after first C-Share evidence pack.

