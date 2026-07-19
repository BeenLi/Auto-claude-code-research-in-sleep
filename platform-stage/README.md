# platform-stage/ 文档目录

WR-ZipGuard · VCU118 RoCE 平台阶段的全部文档(报告/设计/决策)。本目录**只存文档与数据**;
实验代码统一在私有代码仓 [vcu118-roce-platform](https://github.com/BeenLi/vcu118-roce-platform)
(分工约定见 [CODE.md](CODE.md),2026-07-17 用户决定)。

命名规则:本地文件名 = 英文描述名(方便 grep 与 git 历史);页面 `<title>` = 中文全称
(= claude.ai Artifact 列表里显示的名称)。发布用 Artifact,**线上以 Artifact 链接为准**,
本地 HTML 是源文件。

## 现行文档(主入口)

| 本地文件 | Artifact 标题 | 链接 |
|---|---|---|
| [LEARNING_GUIDE.html](LEARNING_GUIDE.html) | 《VCU118 RoCE 平台:学习与集成指南》 | [4e143779](https://claude.ai/code/artifact/4e143779-6219-44e0-9849-bf027c75dd12) |
| [ROCEV2_PRIMER.html](ROCEV2_PRIMER.html) | 《RoCE v2 协议入门》(前置知识) | [5c9c5da5](https://claude.ai/code/artifact/5c9c5da5-4dce-4023-8958-7d738610025f) |
| [FRAMEWORKS_PRIMER.html](FRAMEWORKS_PRIMER.html) | 《三框架入门:fns · Corundum · BALBOA》(前置知识) | [c3fd7041](https://claude.ai/code/artifact/c3fd7041-528d-48a5-8cdd-c61920de5656) |

**LEARNING_GUIDE = 三合一主文档**(2026-07-19 由《集成手册》+《学习导览》+《阶段索引》合并):
仪表盘(阶段状态 + 报告入口 + 决策摘要)置顶 → §0 总览 → §1 架构 → §4 学习路线 →
§5 Stage A–E 执行标准 → §6 已知雷 → §7 后续路标 → §8 接口速查表。§2/§3 即上面两篇前置文档。

## 实验报告(Stage A–E + 平台可用期④)

报告结构统一为:回答什么问题 / 原理 / 装置 / 做了什么 / 结果怎么看 / 发现与边界 / 结论与移交。

| 阶段 | 本地文件 | 结论 | Artifact |
|---|---|---|---|
| A · 环境 + csim 冒烟 | [STAGE_A_REPORT.html](STAGE_A_REPORT.html) | PASS 07-16 | [2b164b5e](https://claude.ai/code/artifact/2b164b5e-ea63-4357-b2d6-608d064fdf6d) |
| B · roce_stack 独立 RTL 仿真 | [STAGE_B_REPORT.html](STAGE_B_REPORT.html) | PASS 07-17 | [cb8beb47](https://claude.ai/code/artifact/cb8beb47-7788-4440-9158-8eb3520e253d) |
| C · doorbell L0 + 内存胶水 | [STAGE_C_REPORT.html](STAGE_C_REPORT.html) | PASS 07-17 | [325d9489](https://claude.ai/code/artifact/325d9489-6908-4831-9c7c-0713ff603199) |
| D · 载体集成 + 综合 | [STAGE_D_REPORT.html](STAGE_D_REPORT.html) | PASS 07-17(250MHz 收敛) | [53fcf419](https://claude.ai/code/artifact/53fcf419-00fe-4b91-8354-f03753426e29) |
| E · 上板环回首光 | [STAGE_E_REPORT.html](STAGE_E_REPORT.html) | PASS 07-17 夜(真链路全环) | [c69771a8](https://claude.ai/code/artifact/c69771a8-46f2-4579-99bb-4cace4f2ea9f) |
| ④ · codec 插入(压缩 WRITE 全环) | [CODEC_INTEGRATION_REPORT.html](CODEC_INTEGRATION_REPORT.html) | PASS 仿真级 07-19 | [f1878f64](https://claude.ai/code/artifact/f1878f64-34a9-4fc9-975f-ef17fcc514fd) |

平台可用期 ①(链路状态寄存器)②(多段写板测 tcl)不单独成报告,结论入 LEARNING_GUIDE 仪表盘
决策摘要(07-18 板上全绿行)。

## 设计文档(Markdown,不发布 Artifact)

| 本地文件 | 内容 | 对应工作项 |
|---|---|---|
| [DOORBELL_SQRING_RETRANS_DESIGN.md](DOORBELL_SQRING_RETRANS_DESIGN.md) | L1 doorbell(SQ 环)+ 重传 URAM 再安置,含评审记录 | 平台可用期 ③(旧名 PLATFORM_USABLE_P3_DESIGN.md) |
| [CODEC_INTEGRATION_DESIGN.md](CODEC_INTEGRATION_DESIGN.md) | codec 插入(E0 变换 + Vitis DCL gzip CU 存转发),含评审与结果 | 平台可用期 ④(旧名 PLATFORM_USABLE_P4_CODEC_DESIGN.md) |

## 历史沿革(2026-07-19 文档重组)

- 删除:`PLATFORM_INTEGRATION_GUIDE.html`(手册)、`LEARNING_ROADMAP.html`(导览)、
  `STAGE_LOG.html`(索引)——内容并入 LEARNING_GUIDE,git 历史可追(commit `deb8728` 之前)。
- 改名(git mv,commit `ec7ec45`):P3/P4 前缀文件 → 描述名(见上表"旧名"列)。
  "P3/P4" = 平台可用期第 ③/④ 项的旧编号。
- Artifact URL 变迁:`4e143779` 原为《阶段索引》,现为《学习与集成指南》(4/6 份报告的回链
  因此保持有效);原《集成手册》`db3cafcb` 与《学习导览》`d5cc763b` 两个 Artifact 已废弃
  (可在 claude.ai 的 Artifacts 列表删除);报告与前置文档 URL 不变/新增。
