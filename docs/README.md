# docs/ 目录说明

本目录混居两类文档，注意区分：

## 1. WR-ZipGuard 平台深潜笔记（研究项目文档）

2026-07-23 自代码仓 `vcu118-roce-platform`（myDevbox）的 `docs/` 移入本仓（按 2026-07-17
仓库分工：docs 仓 = idea/报告/数据/决策，代码仓只留实验代码）。远端副本已删除，**本目录是唯一正本**。

| 文件 | 标题 | 内容 |
|---|---|---|
| [verbs-coyote-platform.html](verbs-coyote-platform.html) | 三层世界：verbs 栈 · Coyote shell · 本平台 | RDMA 抽象（WQE/保护/完成/SG）在三层实现里的重组与取舍；§10 = 2026-07-23 决策「L2 三条路与 CX-5 站落点」（选定 fns 自家 mac_ip_encode/ip_handler 套装，CX-5 互操作站开工时插装，Stage D 保持认证态） |
| [hls-stream-depth-deep-dive.html](hls-stream-depth-deep-dive.html) | #pragma HLS STREAM depth 深度解析 | 以 RoCEv2 核为标本：pragma 在 csim 被丢弃 vs RTL 物化为 FIFO、FIFO 物理解剖（握手/穿越延迟/存储介质后缀）、csim 只建模一半流控、法证一例「csim 报告里的 1999」、全设计 89 条 pragma 的 depth 五层分类学 |
| [roce_stack-interfaces.html](roce_stack-interfaces.html) | roce_stack 接口速查笔记 | Coyote SV 包装层五个接口面速查：控制面 metaIntf、用户数据面 AXI4S+req_t、重传缓冲面、网络面、统计计数；metaIntf 与 AXI4S 的区分原理 + 交叉参考 |

阶段实验报告（Stage A–E、codec 集成等）的正本在 [`platform-stage/`](../platform-stage/)；
实验代码正本在代码仓 `vcu118-roce-platform`（见 [`platform-stage/CODE.md`](../platform-stage/CODE.md)）。

## 2. ARIS 框架文档（上游框架自带）

其余 `*_GUIDE*.md` / `*_ADAPTATION*.md` / `ARIS-Code-README_*.md` 及图片资产均为 ARIS
框架自身的适配与使用文档，由仓库根部 [`README.md`](../README.md) 索引，本分支不维护其内容
（upstreamMain 框架镜像，勿在本分支修改）。
