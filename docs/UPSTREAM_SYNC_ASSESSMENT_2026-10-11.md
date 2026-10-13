# 2026-10-11 Upstream 同步评估

本文评估 `wanshuiyin/Auto-claude-code-research-in-sleep:main`（以下简称 upstream）自上次同步以来的更新，判断哪些值得合入当前这个面向**计算机体系结构 / AI Infra 硬件方向**、并强调**资源可行性（开源仿真器、单台 FPGA 算力）**的定制分支。

姊妹文档：[UPSTREAM_UPDATE_EXPERIENCE_GUIDE_2026-05-07.md](UPSTREAM_UPDATE_EXPERIENCE_GUIDE_2026-05-07.md)（上一次同步的经验）。

## 0. 一句话结论

**不要 `git merge upstream/main`。** 用“按条目 cherry-pick / 按路径 checkout + 重新生成 Codex 镜像”的方式，分五个桶逐步吸收。第一件事是换掉已经失效的 `codex mcp-server` 评审通道。

## 1. 分叉现状

| 指标 | 数值 |
|---|---|
| merge-base | `e99d45c`（2026-04-21） |
| 本地独有提交 | 56 |
| upstream 独有提交 | 573（其中约 280 条是 README / docs 改动） |
| 按提交标题匹配、本地已 cherry-pick 的 upstream 提交 | 14（`git cherry` 只认出 4 条，因为当时解冲突改了 patch-id） |
| `git merge-tree` 干跑冲突文件 | 170 = 95 个主线文件 + 75 个 `skills/skills-codex*` 镜像文件 |
| 本地测试收集 | 342 个测试，收集正常 |

本地定制的核心落在这些文件（本地改动量 / upstream 改动量，行数 +/-）：

| 文件 | 本地 | upstream |
|---|---|---|
| `skills/idea-creator/SKILL.md` | 396/164 | 373/81 |
| `skills/research-lit/SKILL.md` | 486/233 | 495/58 |
| `skills/research-refine/SKILL.md` | 174/103 | 43/15 |
| `skills/research-review/SKILL.md` | 107/23 | 129/17 |
| `skills/experiment-bridge/SKILL.md` | 152/308 | 55/8 |
| `skills/experiment-queue/SKILL.md` | 158/247 | 149/35 |
| `skills/run-experiment/SKILL.md` | 64/264 | 19/3 |
| `skills/monitor-experiment/SKILL.md` | 56/94 | 10/1 |
| `skills/idea-discovery/SKILL.md` | 99/180 | 228/32 |
| `tools/research_wiki.py` | 1463/158 | 1066/81 |
| `tools/install_aris.sh` | 400/99 | 688/23 |

本地还删除了 `tools/smart_update.sh|ps1`、`tools/install_aris_codex.sh` 等安装链（`32fda95`），用 `tools/sync_codex_skill_mirror.py` 替代了 upstream 的镜像生成器，把 13 个 skill 移到了 `_unused_skills_backup/`，并删除了 `LICENSE`（`e18a270`，疑似误删）。

## 2. P0：立即处理 —— `codex mcp-server` 已失效

- 本机 `codex-cli 0.156.0`，`codex --help` 的子命令列表里**没有 `mcp-server`**（upstream 2026-09-10 News：0.154 起移除）；`codex exec resume` 子命令存在，满足 codex-exec 桥的前提。
- 本仓库 `CLAUDE.md` 的 MCP 段落仍写着 `codex mcp-server`。`claude mcp list` 当前**没有注册任何 `codex` 服务器**，所以这个失效目前是潜在的而不是正在发生的：一旦要走“Claude 调 Codex 评审”的路径（`/research-review`、`/auto-review-loop` 等），必须用 codex-exec 注册。
- upstream 的替代品：`mcp-servers/codex-exec/server.py`（`17da4d6`），通过 `codex exec` / `codex exec resume` 复刻 `codex` + `codex-reply` 两个工具和 `{threadId, content}` 返回格式，skill 侧零改动，纯 Python 3.9+，无第三方依赖。
- 合入方式：直接 `git checkout upstream/main -- mcp-servers/codex-exec tests/test_codex_exec_bridge.py`，零冲突；该测试是纯 stdlib 的 `unittest`，不依赖 upstream 新增的 `tests/conftest.py`。然后按其 README 注册：

```bash
claude mcp remove codex -s user
claude mcp add codex -s user -- python3 "$PWD/mcp-servers/codex-exec/server.py"
```

同批可选：`mcp-servers/grok-exec`、`mcp-servers/antigravity-exec`（`5895d19`，用已有 CLI 登录态桥接 Grok / Gemini）。

## 3. 桶 1：干净新增，零重叠，直接拿

这些路径本地不存在，`checkout upstream/main -- <path>` 即可。注意新 skill 会引用 `shared-references/`，先拿引用再拿 skill。

### 3.1 新 shared-references（本地缺失 8 个）

| 文件 | 用途 | 与本分支的关系 |
|---|---|---|
| `compute-env-contract.md` | 声明式环境 spec + 内容哈希账本 + 三级验证（`569dd51`，改自 Anthropic Claude Science） | **最贴合“资源可行性”目标**，但示例是 CUDA/pip 中心；spec 形状（base / 有序安装阶段 / smoke probes）可直接套到 gem5、Verilator、Vivado 工具链 |
| `review-scope-limits.md` | 约束评审模型“可以提议什么”，防 over-defense（`90a65e2`） | 直接可用 |
| `acceptance-gate.md` | 写作前先谈好验收合同（LOOPS III） | 直接可用 |
| `taste-calibration.md` | 加权评审轴 + 参考锚点（LOOPS VI） | 直接可用 |
| `output-composition.md` | 子 skill 输出组合合同（#280） | 直接可用 |
| `fan-out-pattern.md` | 可移植的 fan-out 模式 | 直接可用 |
| `external-cadence.md` | integrity-forensics 依赖 | 随 forensics 一起拿 |
| `skill-governance.md` | 自动生成 skill 的出处门控 | 可选 |

### 3.2 新 skill（14 个真正新增；另 13 个是本地已归档的 patent / vast-gpu 等，见第 7 节）

| skill | 依赖 | 建议 |
|---|---|---|
| `render-html` | `scripts/render_html.py`；引用 integration-contract / review-tracing / reviewer-routing | **拿**。Markdown→单文件 HTML，upstream 已在 8 个工作流检查点自动触发（`eda1c84`），本地可先手动用 |
| `web-debug-search` | 无 | **拿**。调试报错时多源搜索，与硬件工具链报错（Vivado/gem5 build）同样适用 |
| `paper-poster-html` | `taste-calibration.md`；含 `scripts/_posterly/`、6 套会议 token | **拿**。upstream 已把 LaTeX `paper-poster` 退化为跳转桩（12/1090） |
| `paper-talk` + `slides-polish` | effort-contract 等已存在 | 拿，低优先 |
| `resubmit-pipeline` | assurance-contract / review-tracing | 拿，投稿换会场时用 |
| `integrity-forensics` | `tools/forensics_gate.py`、`external-cadence.md` | 拿，投稿前反“自动研究痕迹”门 |
| `research-implement-feature` | acceptance-gate / review-scope-limits 等 | 拿，“实现 X”带假设账本 |
| `wiki-enrich` | **`tools/research_wiki.py`** | 先核对它调用的子命令在本地 1463 行定制版里是否存在，再拿 |
| `meta-apply` | 配合 `meta-optimize`（upstream 重写 202/18） | 与桶 2 的 meta-optimize 一起拿 |
| `paper-illustration-image2` | `mcp-servers/codex-image2` | 可选，需 Codex 图像能力 |
| `proof-orchestrator` + `lean-formalize` | 理论证明轨道 | 可选，体系结构方向用得少 |
| `interview-cheatsheet` | render-html | 跳过 |

### 3.3 新 tools / MCP / 模板

| 路径 | 作用 | 建议 |
|---|---|---|
| `tools/iteration_log.py` | 过夜循环“0 新发现→强制换框架”的停滞检测（`06039a8`） | **拿**，与本地过夜实验循环直接相关 |
| `tools/watchdog.py` 的 `loop` 任务类型 | 过夜循环静默死亡检测（`ead2485`） | 拿（watchdog.py 属桶 2，本地只改了 10/5 行） |
| `tools/idea_discovery_gate.py` | idea-discovery 阶段证据门（`b2af612`） | 拿，配合桶 3 的 idea-discovery 改动 |
| `tools/review_gate.py`、`tools/provenance.py` | 评审出处 / 门控 | 随 auto-review-loop 一起拿 |
| `tools/extract_paper_style.py` | `style-ref:` 风格模仿（`a5a9ffe`） | 可选 |
| `templates/claude-hooks/corpus_write_guard.*` | 防 skill 语料被误写的 hook | 可选 |
| `aris-monitor/` | 浮窗会话监视器（`9d5a908`） | 可选，独立目录零冲突 |
| `LICENSE` | MIT，本地 `e18a270` 误删 | **恢复**：`git checkout upstream/main -- LICENSE` |

## 4. 桶 2：本地轻改、upstream 重写 —— 整体换 upstream 版，再补回本地小改

本地在这些文件上的改动只有三类，都可机械重放：

1. `REVIEWER_MODEL gpt-5.4 → gpt-5.5`：upstream 已经升到 `gpt-5.6-sol`（`6142715`）再到 `gpt-6-astra`（`0472e53`），直接用 upstream，不必重放。
2. wiki helper 解析链：upstream 同源（#204），且多了第四层 `~/.aris/repo`（`3c58cac`），直接用 upstream。
3. `idea-stage/docs/research_contract.md` 路径约定：本地有 18 个主线文件引用它，**必须重放**。用 `grep -rl 'docs/research_contract.md' skills/ | grep -v skills-codex` 定位。

本地在 auto-review-loop、proof-checker、experiment-audit、reviewer-routing 等文件里还有一块“Reviewer Calling Convention / `mcp__manual_review__*`”接线和 result-to-claim 的 evidence pre-check Step 1.5，它们来自 5 月 cherry-pick 的 #246 与 Hermes borrow，**upstream 当前版本本身就带**（已逐文件核对），不需要重放；只需在换版后 diff 一眼本地多出的 1-2 处引用（auto-review-loop 本地 9 处 vs upstream 7 处，reviewer-routing 5 vs 4）。

### 4.1 upstream 重写幅度大的文件

| 文件 | 本地 | upstream | upstream 主要内容 |
|---|---|---|---|
| `skills/auto-review-loop/SKILL.md` | 69/27 | 741/65 | 对抗默认立场、trace 调试纪律（`831af52`）、路径化上下文（`7c02daf`）、scope-limits（`90a65e2`）、xhigh 为常规档（`5a8c4e3`）、Copilot 评审后端 |
| `skills/proof-checker/SKILL.md` | 49/22 | 412/29 | `--deep-fix`、`--restatement-check`、claim 层写 wiki |
| `skills/paper-writing/SKILL.md` | 36/8 | 359/38 | 写前验收合同（LOOPS III）、HTML 自动输出、“press-release principle” |
| `skills/paper-write/SKILL.md` | 3/3 | 154/11 | GAP_REPORT + DATA_NEEDED、自信措辞（`e9e51ff`） |
| `skills/paper-plan/SKILL.md` | 7/6 | 103/8 | GAP_REPORT、AAAI 页预算 |
| `skills/citation-audit/SKILL.md` | 4/4 | 191/22 | `--uncited`、`--soft-only` |
| `skills/meta-optimize/SKILL.md` | 8/2 | 202/18 | harness-diet 删除分析、trigger-rate 测量、privilege split |
| `skills/result-to-claim/SKILL.md` | 65/9 | 146/25 | evidence pre-check 变成真实可执行步骤（`f7e2712`） |
| `skills/rebuttal/SKILL.md` | 32/7 | 124/37 | per-reviewer thread 模式 |
| `skills/auto-paper-improvement-loop/SKILL.md` | 35/27 | 267/38 | 同 auto-review-loop 一系列 |
| `skills/{arxiv,alphaxiv,deepxiv,exa-search,semantic-scholar}/SKILL.md` | ~20/8 | ~50/25 | 403/429 规避、wiki ingest 可靠性、hallucinated 子命令容错 |
| `skills/shared-references/reviewer-routing.md` | 90/3 | 777/8 | 两档 effort、HTTP fallback、Copilot/Antigravity 路由 |
| `skills/shared-references/review-tracing.md` | 6/6 | 290/13 | 评审 trace 规范 |
| `skills/shared-references/integration-contract.md` | 61/6 | 313/11 | 集成合同 |
| `tools/watchdog.py` | 10/5 | 138/26 | loop 存活检测、tasks.json 加锁（`e3cd5c3`） |
| `tools/save_trace.sh` | 8/7 | 365/56 | — |
| `mcp-servers/llm-chat/server.py` | 6/4 | 403/42 | 清理 + HTTP reviewer fallback（`2bc0e9d`） |
| `mcp-servers/claude-review/server.py` | 115/16 | 119/18 | 两边体量接近，**本地 `3324c89` 修过 Codex 集成**，需逐 hunk 看 |

### 4.2 已 cherry-pick 但 upstream 后续有修补的文件（只取“pick 之后的漂移”）

| 文件 | 漂移 | 值得取的修补 |
|---|---|---|
| `mcp-servers/manual-review/server.py` | +128 | 原子写 `prompt.md`（`f25ded4`）、stdio rebind 推迟到 main（`1c0ba03`）、Windows 解码、跨家族门（`6be7b60`） |
| `tools/verify_papers.py` | 341 行改动 | arXiv 406 当限流（`1075e21`）、S2 API key + 节流（`7554932`）、“拒绝≠未验证”（`e64c347`） |
| `tools/run_state.py` | +194 | 配合 idea-discovery 证据门与 resumable-runs |
| `skills/kill-argument/SKILL.md` | +87 | fan-out 可移植 |
| `skills/openalex/SKILL.md` + `tools/openalex_fetch.py` | +56 / +27 | null 字段（`7f4d3d9`）、保留 OA 状态（`d5efb01`） |
| `skills/shared-references/wiki-helper-resolution.md` | +48 | 第四层 `~/.aris/repo` |
| `injection-hygiene.md` / `resumable-runs.md` / `gemini-search` | +28 / +11 / +10 | 小修 |

## 5. 桶 3：双方都重写 —— 这是本分支的“主权区”，只搬思路不搬补丁

对每个文件，把 upstream 的提交当作“待评估的想法”逐条看，不要尝试三方合并。

### 5.1 `idea-creator` / `idea-discovery`

| upstream 提交 | 想法 | 与本地定制的关系 |
|---|---|---|
| `b2af612` + `a387947` + `tools/idea_discovery_gate.py` | 阶段证据门：每阶段必须留下可验证证据，门只给 verdict 不给“通过” | **拿**，与本地 `workflow1_exit_gate.sh` / checkpoints 同向，可并存 |
| `ffec4b7` (#409) | 评审证据必须落盘（durable） | 拿 |
| `0b4dd9d` (#410) | `AUTO_PROCEED=true` 检查点真正非阻塞 | **拿**，修的是本地也会遇到的 CLI 回合制问题 |
| `73ed2a7` (#421) | 明确 research-review 什么算“正面裁决”；novelty-check 的 PROCEED WITH CAUTION 算正面 | 拿 |
| `06039a8` / `ead2485` | 停滞→强制换框架；循环静默死亡检测 | 拿（工具在桶 1/2） |
| `c03f839` (#306) / `bb3bb9d` (#408) | `upsert_idea` 确定性写 wiki；读时扫描缓存的 wiki 上下文 | 拿，但要移植到本地的 `research_wiki.py` |
| `b11bd2b` / `5d0169b` / `1eb5828` | tier-portable fan-out；output-composition 合同；每个 idea 先用白话写方法 | 拿，低风险 |
| **`78ad58d` (#419) / `014c16e` (#420) / `fd6b7c6` (#422)** | **放宽淘汰**：双评审模型取并集、“让证据来杀 idea 而不是预判的反对意见”、评审排名只分配 pilot 名额不做淘汰、“目标是创造力，简洁只是形式” | **与本地 `evaluation_feasibility_score` 占 40% 的硬门方向相反**，见第 8 节决策点 1 |

### 5.2 `research-lit` / `research-review` / `research-refine`

| upstream 提交 | 想法 | 关系 |
|---|---|---|
| `3362645` verify-papers 预检 | 搜索前幻觉过滤 | 本地已有 `verify_papers.py` + Step 2.5 门（`5e1210b`）；只取桶 2 的 verify_papers.py 修补 |
| `faca11c` (#386) | wiki 全路径 UTF-8、本地源 miss 不再静默 | 拿，中文论文多的本地尤其需要 |
| `363589d` (#425) / `90a65e2` (#397) | research-review 加 scope block；评审提议边界 | 拿，与本地“generalize reviewer checks 4-5”（`112c18b`）互补 |
| `17da4d6` | research-review 接 codex-exec | 随 P0 一起 |
| `df108b0` taste-calibration | research-refine 加权评审轴 | 可选 |

### 5.3 `experiment-bridge` / `experiment-queue` / `run-experiment` / `monitor-experiment`

| upstream 提交 | 想法 | 关系 |
|---|---|---|
| **`6be7b60` (#393)** | **调度器 60 秒杀掉健康任务然后挂死**的 bug 修复 | **必须手工移植**：upstream 修在 `skills/experiment-queue/scripts/queue_manager.py`（新路径），本地 helper 在 `tools/experiment_queue/queue_manager.py` 且带本地 `cosim_protocol.py`；先确认本地版本是否有同样的 `depends_on` 裸字符串 / 心跳判定逻辑 |
| `1faf11c` LOOPS V | 重启教义：坏掉的尝试可以丢弃重建，有硬状态边界 | 拿思路 |
| `831af52` | 对抗默认立场 + research-contract 接线 | 本地已有 research_contract 约定，对比后取其一 |
| `90a65e2` (#397) | experiment-bridge Phase 2.5 评审边界 | 拿 |
| **`569dd51` / `e31a6b0` compute-env-contract** | 声明式环境 + 哈希账本 + 有序安装阶段 | **与本地“资源可行性”目标最契合，但落点正是本地为仿真器/FPGA 重写的 run-experiment**，见第 8 节决策点 2 |

### 5.4 `research-wiki` + `tools/research_wiki.py`

upstream 加了 claim 层（`f4181a5`）、`upsert_idea`（`c03f839`）、`add_experiment`（`47ef940`），四种节点全部确定性写入；外加 UTF-8 / 中文 slug（`5d8e9e2`）/ 旧编码友好报错（`2f00c51`）/ arXiv UA + 批量 id（`146b328`）/ query_pack 结构化抽取（`55bd4cd`）。本地版本多了 1463 行（Obsidian 投影同步、Zotero、resolver、renderer 等，各有测试）。**按函数逐个移植**，先跑本地 7 个 `test_research_wiki_*.py` 作为回归基线。

### 5.5 `tools/install_aris.sh`

upstream 的改动是选择性安装 / Copilot profile / 平台自动探测，全部建立在本地已删除的 `smart_update` + `install_aris_codex.sh` 链上。**不动**，除非决定恢复 upstream 安装链。

## 6. 桶 4：看起来诱人，但和本地已删的基础设施纠缠

| 项目 | 为什么先不拿 |
|---|---|
| 选择性安装（`tools/skill-groups.tsv`、`tools/skill_picker.py`，#358/#366） | 依赖 upstream 版 `install_aris.sh` + `smart_update*`；可以只借“skill 分组目录”这个想法 |
| 插件打包（`.claude-plugin/`、`.codex-plugin/`、`commands/setup.md`，#437） | 自带 skill 清单断言（78/79 个），本地裁剪过的树按定义不满足 |
| `.github/workflows/*`（inventory 检查、lint、测试套件） | 同上；`test-suite.yml` 可单独借来跑本地 342 个测试 |
| Copilot CLI 支持（`install_aris_copilot.sh`、`.github/agents/*`、`copilot_native_evidence.py`） | 只在用 Copilot 时有意义 |
| `tools/smart_update.sh|ps1` | 本地 `32fda95` 有意删除；干跑合并会把它们复活（modify/delete 冲突） |

## 7. 桶 5：本地已归档的 skill

`claims-drafting`、`embodiment-description`、`figure-description`、`invention-structuring`、`jurisdiction-format`、`patent-*`、`specification-writing`、`qzcli`、`vast-gpu`、`serverless-modal`、`idea-discovery-robot` 在 `_unused_skills_backup/`。upstream 对它们的改动（主要是 compute-env-contract 接线）无关紧要；若将来恢复，直接取 upstream 版本而不是 backup 版本。

## 8. 需要你拍板的两个决策点

**决策点 1 —— idea 淘汰松紧。** upstream 8 月的三条提交（#419/#420/#422）把方向改成“先发散，排名只分配 pilot 名额，不做淘汰，让证据而非预判来杀 idea”。本地的定制是 `overall_merit 60% + evaluation_feasibility 40%`，feasibility ≤ 3 直接标 `designed_not_run`，且 `handoff_to_workflow_1_5: ready` 只给 4/5 分。两者并非不可调和：可以保留本地的 feasibility 打分和 handoff 门，但采纳 upstream 的“不因为有邻居 / 看起来弱就删”与“双模型并集”——即 feasibility 低的 idea 保留在候选池并标注，而不是在 Phase 2 被删。需要你确认是否接受这个折中。

**决策点 2 —— compute-env-contract 怎么落地。** 它是最贴合“资源可行性”目标的 upstream 新增，但示例全是 CUDA/pip。两条路：(a) 只拿 `shared-references/compute-env-contract.md` 原文作为参考，不改 run-experiment；(b) 为本地写一个硬件版 env-spec（`base: gem5 v24 / Verilator 5.x / Vivado 2025.1`，`pip_phases` 换成 `toolchain_phases`，`smoke.import_names` 换成 `smoke.commands`），接到本地 run-experiment / experiment-queue。(b) 价值更高但工作量约一个下午。

### 决议（2026-10-13）

- **决策点 1 已定**：保留 feasibility 打分和 handoff 门，低分 idea 留在候选池标注而不是删除。实现为 `pool_status: selected | backup | parked | eliminated`；`parked` 带 `park_reason` 与 `revisit_condition`，只有 `already_done`（同机制同结论且有引用）和 `refuted_by_NE-*` 两种证据可以淘汰。改动在 idea-creator、idea-discovery、research-pipeline、`idea-handoff-schema.md`、两份 IDEA 模板、checkpoints 与 playbook。
- **决策点 2 已定**：写硬件版 env-spec。实验室资源（64 核 CPU + 8×L40 服务器；3 块 VCU118）登记在 `skills/shared-references/lab-resources.yaml`；规则在 `skills/shared-references/hw-env-contract.md`（扩展原样引入的 upstream `compute-env-contract.md`）；项目模板 `templates/HW_ENV_SPEC_TEMPLATE.yaml`。已接入 idea-creator 打分、experiment-plan、experiment-bridge、run-experiment、experiment-queue、research-refine。`hw-env-contract.md` §2 的资源匹配表已按实验室条件填写：服务器有 BF2，FPGA 可作 RDMA NIC（需先有 RoCE 栈），没有以太网交换机，但有直连线缆，可做一对一链路实验。

## 9. 推荐执行顺序与操作规程

1. **P0**：`codex-exec` + 重新注册 MCP + 更新 `CLAUDE.md` 的 MCP 段落。
2. **桶 1**：先 8 个 shared-references → `LICENSE` → `tools/iteration_log.py`、`idea_discovery_gate.py` → 新 skill（render-html、web-debug-search、paper-poster-html 优先）。
3. **桶 2b 漂移**：manual-review、verify_papers.py、run_state.py、openalex。
4. **桶 2**：逐文件 `git checkout upstream/main -- <file>`，然后 grep 重放 `idea-stage/docs/research_contract.md` 约定；`claude-review/server.py` 单独逐 hunk 看。
5. **桶 3**：一次一个文件，按第 5 节的表格逐条决定，两个决策点先定。
6. 每一步之后：

```bash
git checkout HEAD -- 'skills/skills-codex*'          # 丢掉任何 cherry-pick 带进来的镜像 hunk
python3 tools/sync_codex_skill_mirror.py --apply     # 用本地生成器重建镜像
python3 -m pytest -q
```

镜像不参与解冲突，170 个冲突文件立刻变成 95 个。

单条 upstream 提交的吸收方式：

```bash
git cherry-pick -n <sha>                              # 不自动提交
git checkout HEAD -- 'skills/skills-codex*'           # 去掉镜像
git status                                            # 只保留想要的路径
```

整文件直接取 upstream 版本：

```bash
git checkout upstream/main -- <path>
```

upstream remote 已添加为 `upstream`（`https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep.git`）。
