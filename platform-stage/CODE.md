# 实验代码位置(仓库分工约定,2026-07-17 用户决定)

本仓库(Auto-claude-code-research-in-sleep)只记录 **idea / 实验报告 / 数据 / 决策**。
平台线(Stage A–E)的**全部实验代码**统一在独立私有仓库:

**https://github.com/BeenLi/vcu118-roce-platform**(git 开在 myDevbox `~/vcu118-roce-platform`)

| 内容 | 位置 |
|---|---|
| Stage A csim 脚本 + 签名 TB + csim golden | `stage_a_csim/` |
| Stage B/C xsim 工作区(HLS RTL 含 SIM_ZERO_INIT 手补、Coyote 包装含 STAGE-B FIX、L0 三模块、TB、运行/校验脚本、帧捕获 golden) | `roce-rtl-sim/`(myDevbox `~/vcu118-roce-platform/roce-rtl-sim`) |
| Stage D 载体集成 + 综合(rtl / sim / syn / xdc) | `stage_d_shell/` |
| Stage E 上板环回(run_hw_axi tcl + RUNBOOK) | `stage_e/` |
| 平台可用期 ④ codec(HLS csim/csynth + 数据) | `codec/` |
| 上游依赖(fpga-network-stack 等 submodule) | `third_party/` |

历史注记:`stage_b_sim/`、`stage_c_sim/` 曾短暂入库本仓库(提交 7696541 / 24941a0,
历史中仍可见),按分工约定已从分支顶端移除,正本即上述代码仓库。
