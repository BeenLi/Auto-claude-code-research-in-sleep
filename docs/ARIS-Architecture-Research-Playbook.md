[GitHub 原文](https://github.com/BeenLi/Auto-claude-code-research-in-sleep/blob/myMain/docs/ARIS-Architecture-Research-Playbook.md)
本文档把当前仓库的 ARIS 工作流展开到 skill、reviewer、状态文件和中间产物级别。
## 0.1 总览
**Workflow 1 -- Idea Discovery** (`/idea-discovery "topic"`): `research-lit` -> `idea-creator` -> `novelty-check` -> `research-review` -> `research-refine` -> `experiment-plan`

**Workflow 1.5 -- Experiment Bridge** (`/experiment-bridge`): Reads `refine-logs/EXPERIMENT_PLAN.md` -> implements code -> deploys experiments -> collects initial results in `EXPERIMENT_LOG.md`

**Workflow 2 -- Auto Review Loop** (`/auto-review-loop "scope"`): Up to 4 rounds: external LLM review -> identify weaknesses -> agent implements fixes -> re-review until score >= 6/10

**Workflow 3 -- Paper Writing** (`/paper-writing "NARRATIVE_REPORT.md"`): `paper-plan` -> `paper-figure` -> `paper-write` -> `paper-compile` -> `auto-paper-improvement-loop`

**Workflow 4 -- Rebuttal** (`/rebuttal "paper/ + reviews"`): Parses external reviews -> enforces coverage and grounding -> drafts text-only rebuttal


- reviewer routing：默认 Codex MCP xhigh，显式 `-- reviewer: oracle-pro` 才走 Oracle GPT-5.5 Pro。
- reviewer trace：每次 reviewer/critique 调用应写 `.aris/traces/<skill>/<UTC-date>_runNN/`。
- 状态恢复：`refine-logs/REFINE_STATE.json`、`review-stage/REVIEW_STATE.json`、`rebuttal/REBUTTAL_STATE.md`。
- 产物追踪：`MANIFEST.md`、timestamped artifact、latest copy。
- 横向记忆与优化：`research-wiki`、`.aris/meta/events.jsonl`、`meta-optimize`。

## 0.2 End-to-End Diagram

图源文件：

- `figures/aris-workflow-overview.mmd`
- `figures/aris-workflow-overview.md`

```mermaid
%%{init: {"theme": "base", "flowchart": {"curve": "basis", "nodeSpacing": 34, "rankSpacing": 58}, "themeVariables": {"background": "#FFFFFF", "primaryColor": "#E8F1FF", "primaryBorderColor": "#2563EB", "primaryTextColor": "#0F172A", "lineColor": "#475569", "tertiaryColor": "#F8FAFC", "clusterBkg": "#F8FAFC", "clusterBorder": "#CBD5E1"}}}%%
flowchart TB
    U["User topic<br/>RESEARCH_BRIEF.md"]

    subgraph W1["W1 idea-discovery"]
        direction LR
        LIT["research-lit"] --> IDEA["idea-creator"] --> NOV["novelty-check"] --> RRV["research-review"] --> RFP["research-refine-pipeline<br/>(research-refine + experiment-plan)"] --> O1["W1 artifacts<br/>idea / proposal / plan / contract"]
    end

    subgraph W15["W1.5 experiment-bridge"]
        direction LR
        ECON["evaluation contract<br/>handoff gate"] --> BACK["backend selection<br/>baseline Go/No-Go"] --> CODE["scripts / configs / tests"] --> SAN["baseline smoke<br/>idea sanity"] --> EXEC["run or queue"] --> O15["experiment artifacts<br/>contract / manifest / tracker / logs"]
    end

    subgraph W2["W2 review-loop"]
        direction LR
        REV["review"] --> FIX["fix / run"] --> STATE["state update"] --> CLAIM["result-to-claim<br/>optional"]
    end

    subgraph W3["W3 paper"]
        direction LR
        PLAN["paper-plan"] --> FIG["figures"] --> WRITE["paper-write"] --> COMP["paper-compile"] --> AUD["proof / claim / citation audits"] --> IMP["improvement loop"]
    end

    subgraph W4["W4 rebuttal"]
        direction LR
        RAW["raw reviews"] --> BOARD["issue board"] --> STRAT["strategy"] --> DRAFT["paste-ready response"]
    end

    R["Reviewer backend<br/>Codex xhigh / Oracle Pro"]
    X["Records and memory<br/>.aris/traces / MANIFEST<br/>research-wiki / events"]

    U --> LIT
    O1 --> ECON
    O15 --> REV
    CLAIM --> PLAN
    IMP --> RAW

    R -. novelty / proposal .-> NOV
    R -. review gate .-> RRV
    R -. loop review .-> REV
    R -. paper audits .-> AUD
    R -. rebuttal stress test .-> STRAT

    X -. trace .-> RRV
    X -. ledger .-> O1
    X -. run logs .-> O15
    X -. review state .-> STATE
    X -. audit records .-> AUD
    X -. rebuttal state .-> DRAFT

    classDef user fill:#FFF7ED,stroke:#EA580C,color:#1F2937,stroke-width:1.4px
    classDef skill fill:#E8F1FF,stroke:#2563EB,color:#0F172A,stroke-width:1.4px
    classDef artifact fill:#ECFDF5,stroke:#059669,color:#052E2B,stroke-width:1.4px
    classDef reviewer fill:#F5F3FF,stroke:#7C3AED,color:#1E1B4B,stroke-width:1.5px
    classDef record fill:#F8FAFC,stroke:#64748B,color:#111827,stroke-width:1.3px,stroke-dasharray:4 3

    class U user
    class LIT,IDEA,NOV,RRV,RFP,ECON,BACK,CODE,SAN,EXEC,REV,FIX,STATE,PLAN,FIG,WRITE,COMP,AUD,IMP,RAW,BOARD,STRAT,DRAFT skill
    class O1,O15,CLAIM artifact
    class R reviewer
    class X record

    style W1 fill:#F8FAFC,stroke:#BFDBFE,stroke-width:1px
    style W15 fill:#F8FAFC,stroke:#BFDBFE,stroke-width:1px
    style W2 fill:#F8FAFC,stroke:#BFDBFE,stroke-width:1px
    style W3 fill:#F8FAFC,stroke:#BFDBFE,stroke-width:1px
    style W4 fill:#F8FAFC,stroke:#BFDBFE,stroke-width:1px
```

## 0.3 Reviewer Interaction Diagram

图源文件：

- `figures/aris-reviewer-interaction.mmd`
- `figures/aris-reviewer-interaction.md`

```mermaid
%%{init: {"theme": "base", "themeVariables": {"background": "#FFFFFF", "actorBkg": "#E8F1FF", "actorBorder": "#2563EB", "actorTextColor": "#0F172A", "actorLineColor": "#2563EB", "activationBkgColor": "#DBEAFE", "activationBorderColor": "#1D4ED8", "sequenceNumberColor": "#FFFFFF", "sequenceNumberBackground": "#2563EB", "signalColor": "#334155", "signalTextColor": "#111827", "labelBoxBkgColor": "#FFF7ED", "labelBoxBorderColor": "#EA580C", "labelTextColor": "#1F2937", "loopTextColor": "#7C2D12", "noteBkgColor": "#ECFDF5", "noteBorderColor": "#059669"}}}%%
sequenceDiagram
    autonumber
    participant U as User
    participant E as ARIS executor
    participant R as Reviewer backend
    participant T as Trace store
    participant A as Artifacts

    U->>E: invoke skill with topic and optional reviewer override
    E->>A: read primary files and prior state
    E->>E: build reviewer prompt from role, task, file paths, schema
    alt default reviewer
        E->>R: mcp__codex__codex, reasoning xhigh
    else reviewer: oracle-pro
        E->>R: mcp__oracle__consult, model gpt-5-5-pro, files attached
    end
    R-->>E: score, concerns, minimum fixes, verdict
    E->>T: save request, raw response, metadata, thread id
    E->>A: update AUTO_REVIEW or audit artifact
    alt loop continues
        E->>A: implement fixes, run experiments, recompile, or reframe claims
        E->>R: reply or fresh review depending on skill rules
    else terminal
        E->>A: mark state completed and write handoff artifact
    end
```

## 0.4 Workflow Details

### 0.4.1 Workflow 1: Idea Discovery

Command:

```bash
/idea-discovery "topic"
```

Actual chain:

```text
research-lit -> idea-creator -> novelty-check -> research-review -> research-refine-pipeline
```


`research-refine-pipeline` is the canonical outer step for the Workflow 1 tail. Internally it first stabilizes the method through `research-refine`, then turns the stable proposal into a claim-driven experiment roadmap through `experiment-plan`. 
Lite mode is the exception: **if reviewer score is below 6 or the evaluation handoff is unclear** (==这里reviewer的分数是如何评的？==), Workflow 1 may run only `/research-refine`, skip `/experiment-plan`, and record the remaining risk instead of producing a ready Workflow 1.5 handoff.

Inputs:

- **User topic** or `RESEARCH_BRIEF.md`.
- Optional reference paper via `REF_PAPER`; this writes `idea-stage/REF_PAPER_SUMMARY.md` before the literature pass.
- Existing `research-wiki/` if initialized.
- Local papers, Zotero, web/arXiv/Semantic Scholar depending on selected sources.
- Research Domain from `AGENTS.md`: This ARIS instance is configured for **Computer Architecture / AI Infrastructure for LLM** research with a hardware-leaning systems focus.

Controls and limits:

- `MAX_HANDOFF_IDEAS = 6`: write evaluation handoff plans for at most six strong ideas.
- `MAX_READY_FOR_WORKFLOW_1_5 = 3`: mark at most three ideas as immediate Workflow 1.5 candidates.
- `AUTO_PROCEED = true`: proceed with the best option at checkpoints unless the user overrides.
- `COMPACT = false`: when enabled, write a lean `idea-stage/IDEA_CANDIDATES.md` for recovery and downstream handoff.
- `REF_PAPER = false`: when set, summarize the reference paper and use it as context for literature and idea generation.
- `REVIEWER_MODEL = gpt-5.5`: reviewer model passed to review/refine sub-skills via Codex subagent/Codex MCP.
- `OUTPUT_DIR = idea-stage/`: all idea-stage outputs are written under this directory. (由于workflow1有多个SKILL，需要具体看是哪个SKILLS产出了文件，就看那个SKILLS中约束的OUTPUT_DIR为准)
- `ARXIV_DOWNLOAD = false`: default metadata-only; when true, Phase 1 downloads top relevant arXiv PDFs.

Important outputs:

- `idea-stage/LITERATURE_REVIEW.md` and timestamped copy.
- `idea-stage/IDEA_REPORT.md` and timestamped copy.
- `idea-stage/IDEA_CANDIDATES.md` and timestamped copy.
- `refine-logs/FINAL_PROPOSAL.md`.
- `refine-logs/REVIEW_SUMMARY.md`, `refine-logs/score-history.md`, `refine-logs/round-*.md`.
- `refine-logs/EXPERIMENT_PLAN.md`.
- `refine-logs/EXPERIMENT_TRACKER.md`.
- `refine-logs/PIPELINE_SUMMARY.md`.
- `idea-stage/docs/research_contract.md`, refreshed after the selected idea has proposal and plan outputs.
- `MANIFEST.md` rows for every durable artifact.
- Optional `research-wiki/` updates.
- Reviewer traces under `.aris/traces/` for `research-review`, `research-refine`, novelty or idea critiques.
#### 0.4.1.1 Workflow 1 Sub-Skill Details

Compact dataflow:

```text
topic / RESEARCH_BRIEF.md / RefPaper
-> idea-stage/LITERATURE_REVIEW.md / Landscape Pack
-> idea-stage/IDEA_REPORT.md / evaluation_handoff_plan
-> Novelty Check Report
-> research-review feedback
-> refine-logs/FINAL_PROPOSAL.md / refine-logs/EXPERIMENT_PLAN.md / idea-stage/docs/research_contract.md
```

`/research-lit` turns the topic into a landscape and evaluation canon.

- Inputs: user topic or `RESEARCH_BRIEF.md`, prior `idea-stage/LITERATURE_REVIEW.md` if any, optional `research-wiki/`, Zotero, Obsidian notes, local paper library, web/arXiv/Semantic Scholar/OpenAlex/Gemini sources depending on availability and source selection.
- Process: audit source availability, infer the AI infrastructure layer, search primary and adjacent literature, analyze papers, synthesize mechanism clusters and structural gaps.
- Outputs: `idea-stage/LITERATURE_REVIEW_{YYYYMMDD_HHmmssZ}.md`, latest copy `idea-stage/LITERATURE_REVIEW.md`, optional downloaded PDFs or wiki updates, and `MANIFEST.md` rows.
- Handoff: Section 5 `Landscape Pack` is the machine-readable contract for `/idea-creator`; it must preserve `Evaluation Canon`, `Core Baseline Candidates`, simulator/prototype readiness, and `Gap Seeds`.
- Stop or degrade: missing sources are recorded in Source Audit and the skill continues with available sources; software-only topics without concrete hardware bottlenecks should be marked out-of-scope unless explicitly requested.

##### 0.4.1.1.1 research-lit 处理流程详解

`research-lit` 是 Workflow 1 的证据入口,把一个 topic 字符串变成一份"可被 `/idea-creator` 机器读取的研究地形图"。整体由 8 个阶段构成:Step 0/0a/0b/0c 加载已知资料、Step 1 外部检索、Step 1.5 全文可用性检查、Step 2 单篇结构化抽取、Step 3 跨论文综合、Step 4 整理输出、Step 5 写文件、Step 6 写 wiki。

**关键 Constants(决定行为面)**

| Constant           | 默认值                       | 作用                                                             |
| ------------------ | ------------------------- | -------------------------------------------------------------- |
| `REVIEWER_BACKEND` | `codex` (xhigh)           | reviewer 走 Codex MCP;`-- reviewer: oracle-pro` 切换到 GPT-5.5 Pro |
| `PAPER_LIBRARY`    | `papers/` 或 `literature/` | 本地 PDF 路径,支持 `-- paper library:` 内联覆盖                          |
| `MAX_LOCAL_PAPERS` | 20                        | 本地 PDF 扫描上限                                                    |
| `ARXIV_DOWNLOAD`   | `false`                   | 默认只取 metadata;`true` 时下载 top 3-5 PDF                           |
| `EXTENDED_TOPICS`  | `[]`                      | 相邻领域 topic 列表,结果进 Section 1b 而不污染主表                            |

**Step 0 系列 — 加载先验与本地源**

- **Step 0(载入历史)**:先读 `idea-stage/LITERATURE_REVIEW.md`,如存在则把其中论文表当成基线,后续只补"日期更新或不在表内"的新论文,并在输出里用 🆕 标记。
- **Step 0a(Zotero)**:三阶段——Phase A 通过 `zotero_get_collections` 拿全集合树,按主题关键词片段(case-insensitive)匹配任意深度集合,并补一遍 `zotero_search_items` 文本搜索;Phase B 仅当 `EXTENDED_TOPICS` 非空时做跨域扩展,且只保留 MICRO/ISCA/HPCA/ASPLOS/NSDI/SIGCOMM/OSDI/ATC/EuroSys/FCCM/DAC 等 top-tier venue 论文,打 `[cross-domain]` 标签;Phase C 抽用户的高亮、笔记、tag 与集合路径。
- **Step 0b(Obsidian)**:搜索 vault 与 tag,跟 wikilink 抓出用户已"加工过"的笔记摘要(比 raw PDF 更有价值)。
- **Step 0c(本地 PDF)**:Glob 扫 PAPER_LIBRARY,与 Zotero 结果去重(按文件名/标题),每篇读前 3 页提取 title/authors/year/contribution/relevance,最多 `MAX_LOCAL_PAPERS` 篇。

任何 MCP 不可用都**静默 skip**——绝不因 MCP 缺失而失败,只在 Section 0 Source Audit 中记录降级。

**Step 1 — 外部检索(多源并行 + 优先级)**

按可靠性优先级:

| 优先级 | 源 | 用法 | 关键经验 |
|---|---|---|---|
| **S1** | DBLP 会议页 (`dblp.org/db/conf/{venue}/{venue}{year}.html`) | 拉完整论文列表后按相关性筛选 | 最可靠,无 keyword 限制,无 rate-limit;**当前年 + 上一年**都要抓 |
| **S2** | 会议 program 主页 | 只在会议结束 < 8 周且 DBLP 未索引时用 | URL 模式见 SKILL.md 表格(ASPLOS/MICRO/ISCA/HPCA/SIGCOMM/NSDI/OSDI/ATC/EuroSys/FCCM) |
| **S3** | Semantic Scholar API | keyword 搜索 + 补 IEEE/ACM journal | 频繁 HTTP 429,**不要当主源**,只覆盖 EXTENDED_TOPICS |
| **S3b** | IEEE Xplore API | 需要免费 API key | 可选,S3 限流时用 |
| **S4** | WebSearch | 兜底找 arXiv 镜像 | `"title" site:arxiv.org` 风格,不要做 venue 主搜 |
| arXiv | arXiv API (`tools/arxiv_fetch.py`) | **总是运行**,结构化拉 title/abstract/authors/categories/dates | 与 WebSearch 合并去重 |

可选源(必须显式 `-- sources:` 启用,默认 `all` 不含):`semantic-scholar`、`deepxiv`(渐进式 paper-brief/head/section)、`exa`(broad web + content extraction)、`gemini`(MCP 优先、CLI 兜底,主题分解 + 别名扩展)、`openalex`(开放引文图 + 机构 + 资助)。

**去重链**:arXiv ID → DOI → 标准化 title 三级匹配;同一篇在 arXiv + S2 都命中时,优先 S2 venue/citation 但保留 arXiv PDF 链接;OpenAlex 的机构与资助信息单独保留为唯一价值字段。

**Step 1.5 — 全文可用性检查**

对每篇 web-only 来源的论文,先匹配本地库 → 标 ✅ local;若都拿不到全文则进入"⚠️ NO FULL TEXT 清单",**不暂停**流水线、不阻塞,Step 2 退化为只读 title+abstract,并在输出中提示用户后续手动下载。

**Step 2 — 单篇结构化抽取(11 字段)**

每篇论文产 1 行结构化记录:

`Problem` / `Method` / `Results` / `Relevance` / `Source` / `Evaluation Platform` / `Workload` / `Compared Baselines` / `Metrics` / `Artifact Availability` / `Evaluation Limitations`

Artifact 走 `official_artifact` / `open_source_system` / `config_reproducible` / `paper_only` / `unavailable` / `not_reported` 枚举——这套枚举直接喂给 Step 3e 的 Landscape Pack。

**Step 3 — 综合(产出地形图,5 子步)**

- **3a Landscape Map**:把所有论文分 3-6 个 sub-direction cluster,每个 cluster 给 1 句话定义 + 论文列表 + "已经做到哪 / 卡在哪"。
- **3b Consensus & Disagreements**:点出共识(如 "100Gbps 硬件 LZ4 已被解决")与活跃争议(冲突结论或对立设计哲学);若 Obsidian 有用户笔记,在此融合用户视角。
- **3c Structural Gaps**(idea-creator 直接消费):5 个 lens——cross-domain transfer / contradictory findings / untested assumptions / unexplored regimes / unasked diagnostic questions。每个 gap 必须 ground 到具体论文或显式 negative evidence。
- **3d Competitive Landscape**:top 3 最直接竞争者的"claim vs leave-open + 是否同方向 + 是否 peer-reviewed"。
- **3e Landscape Pack**:固定 7 块表的机器契约,见下节。

**Landscape Pack 七块表(下游 `/idea-creator` 的契约)**

| 块                               | 内容                                                                                                                                                             | 稳定 ID                               |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Topic Scope                     | original_topic                                            | —                                   |
| Bottleneck Evidence             | bottleneck + supporting_papers + decisive_metrics                                                                                     | `bottleneck_id`                     |
| Mechanism Clusters              | mechanism_family + representative_papers + plateau_or_missing_piece                                                                                            | cluster name                        |
| **Evaluation Canon**            | item + supporting_papers + adoption_strength + artifact_or_access + limitations                                                       | **`EC-P*`(平台) / `EC-W*`(workload)** |
| **Core Baseline Candidates**    | baseline_name + paper_or_system + scenario + evaluation_platform_used + workload_used + metrics_used + artifact_status                                         | **`CB*`**                           |
| Simulator / Prototype Readiness | backend + readiness(ready/partial/future) + what_it_can_validate + blocker                                                                       | —                                   |
| **Gap Seeds**                   | gap_type + bottleneck + supporting_papers + possible_mechanism_hint + minimum_validation_backend + decisive_metric + main_risk_or_kill_reason | **`gap_id`**                        |

下游 `/idea-creator` 通过 `canon_mapping: platform=[EC-P*]; workload=[EC-W*]` 引用 Canon;`core_baseline` 从 `CB*` 池中选;Gap Seeds 是 ideation 起点。**禁止跨主题复用** Canon/baseline——每个 topic 现搜现填。

**Step 4 — 输出(7 个 Section)**

`LITERATURE_REVIEW.md` 固定结构:Section 0 Source Audit / Section 1 Paper Table(主) / Section 1b Cross-domain References / Section 2 Landscape Map / Section 3 Structural Gaps / Section 4 Competitive Landscape / **Section 5 Landscape Pack**(机器契约)。Zotero 来源论文加 📚 + 集合路径,新增论文加 🆕。

**Step 5 — 文件落盘**

- 时间戳历史副本:`idea-stage/LITERATURE_REVIEW_{YYYYMMDD_HHmmssZ}.md`(UTC,`date -u +%Y%m%d_%H%M%SZ`)
- 固定 latest 副本:`idea-stage/LITERATURE_REVIEW.md`(下游永远读这份)
- 两份都进 `MANIFEST.md`,stage 标 `idea-discovery`
- 若 Zotero 导出过 BibTeX,追加 `references.bib`

**Step 6 — Research Wiki Ingest(条件)**

只在 `research-wiki/` 目录存在时运行,走 `tools/research_wiki.py` ingest_paper 子命令(优先 `.aris/tools/`,然后项目 `tools/`,最后 `ARIS_REPO`)。对 top 8-12 篇论文用 arXiv ID 调用一次,helper 内部完成 slug 生成 / metadata 抓取 / 去重 / 页面渲染 / index 重建 / query_pack 重建 / log append。helper 不可用时**只 warn 不 fail**,可由 `/research-wiki sync --arxiv-ids …` 后补。

**端到端流程图**

```mermaid
%%{init: {"theme": "base", "flowchart": {"curve": "basis", "nodeSpacing": 38, "rankSpacing": 56}, "themeVariables": {"background": "#FFFFFF", "primaryColor": "#E8F1FF", "primaryBorderColor": "#2563EB", "primaryTextColor": "#0F172A", "lineColor": "#475569", "clusterBkg": "#F8FAFC", "clusterBorder": "#CBD5E1"}}}%%
flowchart TB
    topic["User topic<br/>+ optional RESEARCH_BRIEF.md / REF_PAPER"]

    subgraph priorAndLocal["Step 0 / 0a / 0b / 0c: 加载先验 + 本地源"]
        direction LR
        prevReview["Step 0<br/>读 idea-stage/<br/>LITERATURE_REVIEW.md"]
        zotero["Step 0a Zotero MCP<br/>集合 + tag + 标注"]
        obsidian["Step 0b Obsidian<br/>笔记 + wikilink"]
        localPdf["Step 0c 本地 PDF<br/>papers/, literature/"]
    end

    subgraph externalSearch["Step 1: 外部检索 (S1-S4 + arXiv)"]
        direction LR
        dblp["DBLP 会议页 S1<br/>(最可靠)"]
        confProg["会议 program 页 S2"]
        s2api["Semantic Scholar S3<br/>(限流)"]
        arxivApi["arXiv API<br/>(始终运行)"]
    end

    fulltext["Step 1.5<br/>全文可用性检查<br/>(NO FULL TEXT 降级)"]
    analyze["Step 2<br/>每篇 11 字段抽取"]
    synthesis["Step 3<br/>Landscape 综合<br/>(3a-3e)"]
    writeOut["Step 4-5<br/>写 LITERATURE_REVIEW.md<br/>+ 时间戳副本 + MANIFEST"]
    wikiIngest["Step 6<br/>research-wiki ingest<br/>(可选, helper 缺失只 warn)"]

    topic -->|"topic + sources flags"| priorAndLocal
    priorAndLocal -->|"去重后已知集合"| externalSearch
    externalSearch -->|"候选论文 (含 cross-domain 标记)"| fulltext
    fulltext -->|"可读论文 + degrade 标记"| analyze
    analyze -->|"论文结构化表"| synthesis
    synthesis -->|"7 块 Landscape Pack"| writeOut
    writeOut -->|"top 8-12 arXiv IDs"| wikiIngest

    classDef inputCls fill:#10B981,color:#fff,stroke:#047857,stroke-width:1.5px
    classDef searchCls fill:#3B82F6,color:#fff,stroke:#1D4ED8,stroke-width:1.4px
    classDef processCls fill:#8B5CF6,color:#fff,stroke:#6D28D9,stroke-width:1.4px
    classDef outCls fill:#F97316,color:#fff,stroke:#C2410C,stroke-width:1.4px

    class topic inputCls
    class prevReview,zotero,obsidian,localPdf,dblp,confProg,s2api,arxivApi searchCls
    class fulltext,analyze,synthesis processCls
    class writeOut,wikiIngest outCls
```

**Step 3 综合子流程图(Landscape Pack 生成)**

```mermaid
%%{init: {"theme": "base", "flowchart": {"curve": "basis", "nodeSpacing": 32, "rankSpacing": 50}, "themeVariables": {"background": "#FFFFFF", "primaryColor": "#E8F1FF", "primaryBorderColor": "#2563EB", "primaryTextColor": "#0F172A", "lineColor": "#475569", "clusterBkg": "#F8FAFC", "clusterBorder": "#CBD5E1"}}}%%
flowchart TB
    papers["Step 2 输出:<br/>已抽取 11 字段的论文集合"]
    map3a["3a Landscape Map<br/>3-6 个 sub-direction cluster"]
    consensus["3b Consensus 与 Disagreement<br/>+ Obsidian 用户视角"]
    gaps["3c Structural Gaps<br/>5 lens 分析<br/>(cross-domain / contradiction /<br/>untested / unexplored / unasked)"]
    competing["3d Competitive Landscape<br/>top 3 直接竞争者定位"]
    pack["3e Landscape Pack<br/>Section 5 机器契约"]

    subgraph packBlocks["Landscape Pack 七块"]
        direction TB
        topicScope["Topic Scope"]
        bnEvidence["Bottleneck Evidence<br/>(bottleneck_id)"]
        mechClusters["Mechanism Clusters"]
        evalCanon["Evaluation Canon<br/>EC-P* 平台 / EC-W* workload"]
        coreBaseline["Core Baseline Candidates<br/>CB* 池"]
        simReadiness["Simulator / Prototype<br/>Readiness"]
        gapSeeds["Gap Seeds<br/>(gap_id, ground to paper)"]
    end

    papers -->|"按 method 聚类"| map3a
    map3a -->|"sub-direction 视图"| consensus
    consensus -->|"共识 + 争议"| gaps
    gaps -->|"5 lens gap 候选"| competing
    competing -->|"竞争定位 + 风险"| pack
    pack -->|"落 7 块表"| packBlocks

    classDef synthCls fill:#3B82F6,color:#fff,stroke:#1D4ED8,stroke-width:1.4px
    classDef contractCls fill:#8B5CF6,color:#fff,stroke:#6D28D9,stroke-width:1.4px
    classDef inputCls fill:#10B981,color:#fff,stroke:#047857,stroke-width:1.5px

    class papers inputCls
    class map3a,consensus,gaps,competing synthCls
    class pack,topicScope,bnEvidence,mechClusters,evalCanon,coreBaseline,simReadiness,gapSeeds contractCls
```

**降级与红线**

- **MCP 缺失零失败**:Zotero / Obsidian / Gemini MCP / Exa / DeepXiv / OpenAlex 任一不可用都静默 skip,只在 Source Audit 留记录。
- **rate-limit**:Semantic Scholar 重试一次仍 429 就放弃,改回 S1/S2/S4;DBLP keyword API 直接禁用,只用 DBLP 直链。
- **ACM DL / IEEE Xplore**:返回 403,**绝不**声称搜过这两个站点。
- **Section 5 缺则 Workflow 1 死**:Landscape Pack 七块表缺任意一块,下游 `/idea-creator` 会在 `canon_mapping` 处出 `unclear_canon_mapping`,导致 idea 全部进 `needs_canon_clarification`。

`/idea-creator` turns the landscape into ranked, evaluable ideas.

- Inputs: `idea-stage/LITERATURE_REVIEW.md`, its `Landscape Pack`, optional `idea-stage/REF_PAPER_SUMMARY.md`, optional `research-wiki/` query pack, and domain constraints.
- Process: load prior memory, generate 8-12 ideas, filter by architecture/systems relevance, extract evaluation canon mappings, run first-pass ranking, and prepare deeper validation for top ideas.
- Outputs: `idea-stage/IDEA_REPORT_{YYYYMMDD_HHmmssZ}.md`, latest copy `idea-stage/IDEA_REPORT.md`, optional `idea-stage/IDEA_CANDIDATES.md` in compact mode, wiki idea pages when enabled, and `MANIFEST.md` rows.
- Handoff: writes `evaluation_handoff_plan` for the top 4-6 ideas and marks at most 2-3 immediate Workflow 1.5 candidates with `handoff_to_workflow_1_5`.
- Stop or degrade: Workflow 1 does not run pilots or baseline reproduction; unclear platform/workload/baseline paths become `needs_canon_clarification` or `designed_not_run`, not fake readiness.

`/novelty-check` tests whether the selected idea has a defensible technical delta.

- Inputs: top idea description, method shape, core technical claims, and closest papers already known from literature review.
- Process: extract 3-5 novelty-bearing claims, search each claim across recent literature and major architecture/systems venues, read close abstracts/related-work sections, and ask a reviewer model for cross-check.
- Outputs: a structured `Novelty Check Report` with proposed method, core claims, closest prior work, overall novelty score, recommendation, risk, and suggested positioning.
- Handoff: updates the idea report or selection rationale with closest prior work and differentiators before `/research-review`.
- Stop or degrade: `ABANDON` kills or demotes the idea; `PROCEED WITH CAUTION` requires the next review/refinement step to explicitly address overlap risk.

`/research-review` supplies the external reviewer gate before method refinement.

- Inputs: selected idea, evaluation handoff plan, novelty evidence, proposal or narrative files if present, experiment context if any, and known weaknesses.
- Process: gather research context, send an xhigh senior architecture/systems reviewer prompt, iterate only on actionable questions, and converge on claim/evidence requirements.
- Outputs: reviewer score or verdict, logical gaps, missing experiments, narrative weaknesses, minimum viable fixes, claims matrix, and prioritized TODOs when requested.
- Handoff: provides the review summary and concrete objections that `/research-refine-pipeline` must either resolve or preserve as known risks.
- Stop or degrade: if reviewer feedback exposes an unstable thesis or unclear evaluation target, Workflow 1 should use lite mode or return to idea/canon clarification instead of forcing an experiment plan.

`/research-refine-pipeline` is the canonical Workflow 1 tail.

- Inputs: reviewed selected idea, novelty result, review feedback, evaluation handoff plan, constraints, target venue, and existing `refine-logs/` files if resuming.
- Process: triage whether the current proposal is stale, run or reuse `research-refine`, run the planning gate, run `experiment-plan`, write an integration summary, and refresh the research contract.
- Outputs: `refine-logs/FINAL_PROPOSAL.md`, `refine-logs/REVIEW_SUMMARY.md`, `refine-logs/REFINEMENT_REPORT.md`, `refine-logs/EXPERIMENT_PLAN.md`, `refine-logs/EXPERIMENT_TRACKER.md`, `refine-logs/PIPELINE_SUMMARY.md`, and refreshed `idea-stage/docs/research_contract.md`.
- Handoff: this package is the input to Workflow 1.5; `EXPERIMENT_PLAN.md` owns execution details, while `research_contract.md` owns active idea and claim boundaries.
- Stop or degrade: if the method remains `REVISE`, planning may continue only when weaknesses are explicit; otherwise tighten the proposal before producing a full experiment roadmap.

Wrapper boundary:

- `research-refine` owns the Problem Anchor, method thesis, contribution focus, review rounds, drift checks, final proposal, and refinement history.
- `experiment-plan` owns the Claim Map, paper storyline, Evaluation Inputs, experiment blocks, run order, validation budget, tracker, and Workflow 1.5 handoff fields.
- `research-refine-pipeline` coordinates the two and writes the integrated summary; it does not make `research-refine` or `experiment-plan` obsolete.

#### 0.4.1.2 Workflow 1 Output Templates

These are compact template summaries for auditing output shape. The detailed canonical templates live in the child skill files.

`idea-stage/LITERATURE_REVIEW.md`:

- Header: generation date, skill name, original topic query.
- Section 0 `Source Audit`: source, status, action taken or fallback notes.
- Section 1 `Paper Table`: paper, venue, year, method, key result, relevance, source.
- Section 1b `Cross-domain References`: adjacent-domain papers and transferable insights.
- Section 2 `Landscape Map`: 3-5 paragraphs by sub-direction cluster.
- Section 3 `Structural Gaps`: cross-domain transfer, contradictions, untested assumptions, unexplored regimes, unasked questions.
- Section 4 `Competitive Landscape`: top competing papers and positioning notes.
- Section 5 `Landscape Pack`: topic scope, bottleneck evidence, mechanism clusters, `Evaluation Canon`, `Core Baseline Candidates`, simulator/prototype readiness, `Gap Seeds`.

`idea-stage/IDEA_REPORT.md`:

- Header: direction, UTC generation time, generated/survived/handoff/recommended counts.
- `Landscape Summary`: concise synthesis from the literature review.
- `Recommended Ideas`: ranked ideas with idea shape, merit, `core_baseline`, `canon_mapping`, metrics, validation style, feasibility fields, platform path, blocker, reviewer objection, and rationale.
- `Eliminated Ideas`: idea, category, reason, revisit condition.
- `Deferred / Designed-Not-Run Ideas`: why deferred and what must become available.
- `Evaluation Handoff Summary`: compact table of ranking, feasibility, baseline, canon, metrics, validation style, handoff status, blocker.
- `Suggested Execution Order` and `Next Steps`: selected idea goes to `/research-refine-pipeline`, then Workflow 1.5 creates `EVALUATION_CONTRACT.md`.

`Novelty Check Report`:

- `Proposed Method`: 1-2 sentence method description.
- `Core Claims`: each claim with novelty level and closest paper.
- `Closest Prior Work`: paper, year, venue, overlap, key difference.
- `Overall Novelty Assessment`: score, recommendation, key differentiator, reviewer risk.
- `Suggested Positioning`: how to frame the contribution without overclaiming novelty.

`refine-logs/REVIEW_SUMMARY.md`:

- Header: problem, initial approach, date, rounds, final score, final verdict.
- `Problem Anchor`: the invariant problem statement used across rounds.
- `Round-by-Round Resolution Log`: reviewer concerns, simplifications or modernization, solved status, remaining risk.
- `Overall Evolution`: how the method became concrete, focused, and less overbuilt.
- `Final Status`: anchor, focus, platform status, strongest parts, remaining weaknesses.

`refine-logs/FINAL_PROPOSAL.md`:

- Clean final proposal only.
- It should not include round history, raw reviewer text, or review chatter.
- If the verdict is not `READY`, it still holds the best current proposal version with limitations expressed honestly.

`refine-logs/REFINEMENT_REPORT.md`:

- Header: problem, initial approach, date, rounds, final score, final verdict.
- `Output Files`: links to review summary and final proposal.
- `Score Evolution`: round-by-round rubric table.
- `Round-by-Round Review Record`: concern, change, result.
- `Final Proposal Snapshot`: short thesis summary pointing to `FINAL_PROPOSAL.md`.
- `Method Evolution Highlights`, `Pushback / Drift Log`, `Remaining Weaknesses`, and optional raw reviewer response details.

`refine-logs/EXPERIMENT_PLAN.md`:

- Header: problem, method thesis, date.
- `Claim Map`: claim, why it matters, minimum convincing evidence, linked blocks.
- `Paper Storyline`: main-paper proof, appendix support, intentionally cut experiments.
- `Evaluation Inputs`: `core_baseline`, `canon_mapping`, metrics, validation style, clarity, feasibility, baseline reproducibility, environment access, adapter cost, pilot runtime cost.
- `Experiment Blocks`: claim tested, purpose, referenced Evaluation Inputs, workload/configuration, compared systems, decisive metrics, setup, success criterion, failure interpretation, table/figure target, priority.
- `Run Order and Milestones`, `Validation Budget`, `Risks and Mitigations`, `Final Checklist`.

`refine-logs/EXPERIMENT_TRACKER.md`:

- Compact execution table with `Run ID`, milestone, purpose, system/variant, split or workload, metrics, priority, status, notes.
- It is execution-oriented and should not duplicate the full experiment-plan prose.

`refine-logs/PIPELINE_SUMMARY.md`:

- Header: problem, final method thesis, final verdict, date.
- `Final Deliverables`: proposal, review summary, experiment plan, tracker.
- `Contribution Snapshot`: dominant contribution, optional supporting contribution, intentionally rejected complexity.
- `Must-Prove Claims`, `First Runs to Launch`, `Main Risks`, `Next Action`.

`idea-stage/docs/research_contract.md`:

- Selected idea, intended claims, evidence boundary, key decisions, and current research gate.
- It points to `refine-logs/EXPERIMENT_PLAN.md` for execution details and to result logs for factual evidence.
- It must not copy full experiment blocks, raw logs, ordinary code TODOs, or unsupported claims phrased as paper-ready evidence.

### 0.4.2 Workflow 1.5: Experiment Bridge

Command:

```bash
/experiment-bridge
```

Inputs:

- `refine-logs/EXPERIMENT_PLAN.md`.
- Optional `refine-logs/EXPERIMENT_TRACKER.md`.
- Optional `refine-logs/FINAL_PROPOSAL.md`.
- `idea-stage/IDEA_REPORT.md` and `idea-stage/docs/research_contract.md` when available.
- Evaluation handoff fields from Workflow 1: `core_baseline`, `canon_mapping`, `metrics`, `target_validation_style`, feasibility, environment access, adapter cost, pilot runtime cost, and `handoff_to_workflow_1_5`.

Internal stages:

1. Parse claims, claim boundaries, baselines, ablations, metrics, resource needs, and Workflow 1 evaluation handoff fields.
2. Evaluate the Workflow 1 -> 1.5 handoff gate before implementation.
3. Write `refine-logs/EVALUATION_CONTRACT.md` first.
4. Map `handoff_to_workflow_1_5` to `idea_execution_readiness`.
5. Select the evaluation backend from `core_baseline` and `canon_mapping`; do not use a global fixed simulator default.
6. Apply the baseline reproduction Go/No-Go rule.
7. Run baseline smoke first when required.
8. Write or update `refine-logs/EXPERIMENT_MANIFEST.yaml`.
9. Generate or reuse scripts, configs, tests, simulator glue, and result directories for the selected backend.
10. Run the smallest idea sanity/smoke case.
11. Review code/config before expensive runs.
12. Route execution:
   - small one-off job -> `/run-experiment`;
   - grid, many seeds, or phase dependencies -> `/experiment-queue`.
13. Collect logs/results into `refine-logs/EXPERIMENT_LOG.md` or project-specific experiment result files.

Important outputs:

- `refine-logs/EVALUATION_CONTRACT.md`.
- `refine-logs/EXPERIMENT_MANIFEST.yaml`.
- `refine-logs/EXPERIMENT_TRACKER.md`.
- `refine-logs/EXPERIMENT_LOG.md`.
- Experiment code/configs/tests, for this repo currently under `experiments/rx-expansion/` and `tests/`.
- Result files such as `.json`, `.csv`, reports, plots, simulator logs.

Missing detail in the original diagram: `experiment-bridge` is not only "implement\_code"; it must lock the evaluation contract before implementation, preserve claim boundaries, prove baseline status honestly, run sanity checks, and produce machine-readable evidence for later audits.

### 0.4.3 Workflow 2: Auto Review Loop

Command:

```bash
/auto-review-loop "scope"
```

Inputs:

- `refine-logs/EXPERIMENT_PLAN.md`.
- Experiment results and logs.
- Implementation code.
- `review-stage/AUTO_REVIEW.md` and `review-stage/REVIEW_STATE.json` if resuming.
- Optional `findings.md` / `EXPERIMENT_LOG.md` when compact mode is enabled.

Reviewer modes:

- `medium`: Codex MCP xhigh review.
- `hard`: reviewer memory plus debate protocol.
- `nightmare`: reviewer reads repo directly and verifies code/results.
- `-- reviewer: oracle-pro`: one-shot or final stress review through Oracle GPT-5.5 Pro when explicitly requested.

Loop details:

```text
Phase A: reviewer reads artifacts and scores work
Phase B: executor parses score, verdict, critical weaknesses
Phase B.5: reviewer memory update, hard/nightmare only
Phase B.6: debate protocol, hard/nightmare only
Human checkpoint: optional
Phase C: implement fixes or launch experiments
Phase D: wait for results
Phase E: document round and update REVIEW_STATE
Repeat until score threshold or max rounds
```

Important outputs:

- `review-stage/AUTO_REVIEW.md`.
- `review-stage/AUTO_REVIEW_<UTC timestamp>.md`.
- `review-stage/REVIEW_STATE.json`.
- `review-stage/REVIEW_STATE_<UTC timestamp>.json`.
- Optional `CLAIMS_FROM_RESULTS.md` from `/result-to-claim`.
- Optional updates to `research-wiki/ideas/*`, `research-wiki/claims/*`, and graph edges.
- `.aris/traces/auto-review-loop/...` or `.aris/traces/research-review/...`.

Missing detail in the original diagram: Workflow 2 is not just review/fix. It owns reviewer memory, debate, state recovery, raw response preservation, Feishu notifications when configured, and the bridge to claims for paper writing.

### 0.4.4 Workflow 3: Paper Writing

Command:

```bash
/paper-writing "NARRATIVE_REPORT.md"
```

Inputs:

- `NARRATIVE_REPORT.md` or `STORY.md`.
- `CLAIMS_FROM_RESULTS.md` if generated.
- `review-stage/AUTO_REVIEW.md`.
- `idea-stage/IDEA_REPORT.md`.
- Experiment result files, figure/table data, and known limitations.
- Optional existing `PAPER_PLAN.md` to skip planning.

Detailed chain:

```text
paper-plan -> paper-figure -> figure-spec/paper-illustration/mermaid-diagram
-> paper-write -> paper-compile
-> proof-checker if theory
-> paper-claim-audit
-> auto-paper-improvement-loop
-> final paper-claim-audit
-> citation-audit
-> tools/verify_paper_audits.sh
-> final report
```

Important outputs:

- `PAPER_PLAN.md`.
- `figures/` scripts, plots, tables, specs, SVG/PDF/PNG.
- `paper/main.tex`.
- `paper/sections/*.tex`.
- `paper/references.bib`.
- `paper/main.pdf`.
- `PAPER_IMPROVEMENT_LOG.md`.
- `paper/PROOF_AUDIT.{md,json}` when applicable.
- `paper/PAPER_CLAIM_AUDIT.{md,json}`.
- `paper/CITATION_AUDIT.{md,json}`.
- `paper/.aris/audit-verifier-report.json`.
- Final paper-writing report.

Missing detail in the original diagram: Workflow 3 has multiple assurance gates. A paper can compile and still fail submission readiness if claim, proof, or citation audits fail.

### 0.4.5 Workflow 4: Rebuttal

Command:

```bash
/rebuttal "paper/ + reviews" -- venue: ICML
```

Inputs:

- Paper source or PDF.
- Raw external reviews.
- Venue rules, length limit, response mode.
- Current stage: initial rebuttal or follow-up.

Outputs:

- `rebuttal/REVIEWS_RAW.md`.
- `rebuttal/ISSUE_BOARD.md`.
- `rebuttal/STRATEGY_PLAN.md`.
- `rebuttal/EVIDENCE_LEDGER.md`.
- `rebuttal/REBUTTAL_DRAFT_rich.md`.
- `rebuttal/PASTE_READY.txt`.
- `rebuttal/REVISION_PLAN.md`.
- `rebuttal/FOLLOWUP_LOG.md` for later rounds.
- `rebuttal/REBUTTAL_STATE.md`.

Safety gates:

- provenance gate: every factual statement has a source.
- commitment gate: every promise is approved or marked future work.
- coverage gate: every reviewer concern is answered, deferred, or needs user input.

Missing detail in the original diagram: rebuttal is a first-class workflow, not an afterthought after paper writing.

## 0.5 Skill Input / Output Matrix

| Skill                          | Main input                                           | Reviewer interaction                          | Main output                                                   |
| ------------------------------ | ---------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------- |
| `/research-pipeline`           | broad topic, optional `RESEARCH_BRIEF.md`            | delegates to child workflow reviewers         | `NARRATIVE_REPORT.md`, pipeline report, optional paper        |
| `/idea-discovery`              | topic or brief                                       | delegates to idea/review/refine-pipeline skills | `idea-stage/IDEA_REPORT.md`, `idea-stage/IDEA_CANDIDATES.md`, `research_contract.md` |
| `/research-lit`                | topic, sources, optional wiki                        | optional deep reviewer for synthesis          | topic-scoped literature report, wiki paper ingest             |
| `/idea-creator`                | research-lit output, wiki query pack, domain profile | external idea critique when configured        | ranked ideas, pilot table, `IDEA_REPORT.md`                   |
| `/novelty-check`               | top idea and related work                            | reviewer/critic call, traced                  | novelty risk report, prior-work objections                    |
| `/research-review`             | proposal, plan, paper, results, file paths           | Codex xhigh or Oracle Pro                     | review report, score, Go/No-Go, traces                        |
| `/research-refine`             | selected idea and grounding material                 | multi-round proposal review                   | `FINAL_PROPOSAL.md`, `REVIEW_SUMMARY.md`, `REFINE_STATE.json` |
| `/experiment-plan`             | refined proposal                                     | may use reviewer feedback indirectly          | `EXPERIMENT_PLAN.md`, tracker-ready milestones                |
| `/research-refine-pipeline`    | reviewed selected idea and evaluation handoff        | composes refine review and experiment planning | `FINAL_PROPOSAL.md`, `EXPERIMENT_PLAN.md`, `PIPELINE_SUMMARY.md` |
| `/experiment-bridge`           | `EXPERIMENT_PLAN.md`, handoff fields, research contract | code/config review before expensive runs      | evaluation contract, backend manifest, tracker, logs/results  |
| `/run-experiment`              | one run spec                                         | normally no reviewer                          | single run output, logs, status                               |
| `/experiment-queue`            | job grid or phase manifest                           | normally no reviewer                          | queue state, wave results, retry/stuck status                 |
| `/auto-review-loop`            | code/results/claims/scope                            | core iterative reviewer loop                  | `AUTO_REVIEW.md`, `REVIEW_STATE.json`, optional claims        |
| `/result-to-claim`             | results and review conclusions                       | Codex judge of claim support                  | `CLAIMS_FROM_RESULTS.md`, wiki claim updates                  |
| `/paper-writing`               | `NARRATIVE_REPORT.md`, claims, review history        | delegates to plan/audit/improvement reviewers | full paper directory, PDF, final report                       |
| `/paper-plan`                  | narrative, claims, review history                    | outline review via reviewer model             | `PAPER_PLAN.md`                                               |
| `/paper-figure`                | paper plan and result data                           | figure quality review                         | reproducible figures, tables, LaTeX snippets                  |
| `/figure-spec`                 | architecture/workflow figure request                 | no external reviewer by default               | deterministic SVG/PDF/spec JSON                               |
| `/paper-illustration`          | method description                                   | image generation/review path                  | AI-generated illustration assets                              |
| `/mermaid-diagram`             | diagram request                                      | syntax/visual verification                    | `.mmd`, `.md`, rendered image                                 |
| `/paper-write`                 | `PAPER_PLAN.md`                                      | section-level quality review                  | LaTeX source and bibliography                                 |
| `/paper-compile`               | `paper/`                                             | no reviewer by default                        | `paper/main.pdf`, compile fixes                               |
| `/proof-checker`               | paper proofs                                         | rigorous reviewer/proof critic                | `PROOF_AUDIT.{md,json}`                                       |
| `/paper-claim-audit`           | paper plus raw result files                          | zero-context reviewer                         | `PAPER_CLAIM_AUDIT.{md,json}`                                 |
| `/citation-audit`              | paper bibliography and citations                     | web/DBLP/arXiv-aware reviewer                 | `CITATION_AUDIT.{md,json}`                                    |
| `/auto-paper-improvement-loop` | compiled paper                                       | multi-round paper reviewer                    | improved PDFs, `PAPER_IMPROVEMENT_LOG.md`                     |
| `/rebuttal`                    | paper, raw reviews, venue rules                      | stress-test reviewer and follow-up continuity | rebuttal directory and paste-ready response                   |
| `/research-wiki`               | papers, ideas, experiments, claims                   | no reviewer by default                        | persistent memory pages, graph edges, query pack              |
| `/meta-optimize`               | `.aris/meta/events.jsonl`, traces                    | reviewer-gated harness optimization           | proposed skill/routing improvements                           |

## 0.6 Reviewer and Trace Contract

Default reviewer behavior:

- All review calls default to Codex MCP with xhigh reasoning.
- `-- reviewer: oracle-pro` is explicit opt-in and routes to Oracle GPT-5.5 Pro when available.
- Browser-mode Oracle is acceptable for one-shot reviews, but not ideal for tight multi-round loops.
- Reviewer independence means the executor should pass primary file paths and tasks, not pre-digested summaries, whenever the reviewer can read files directly.

Trace files:

```text
.aris/traces/<skill>/<UTC-date>_runNN/
  run.meta.json
  001-<purpose>.request.json
  001-<purpose>.response.md
  001-<purpose>.meta.json
```

Trace metadata should preserve:

- skill and purpose;
- UTC timestamp;
- tool name, model, thread id;
- prompt snapshot;
- raw reviewer response.

## 0.7 Artifact and State Map

```text
project/
  AGENTS.md                         # domain profile, current pipeline state
  MANIFEST.md                       # output ledger
  .aris/
    meta/events.jsonl               # hook/meta events
    traces/                         # reviewer call evidence
  research-wiki/                    # persistent papers/ideas/claims/experiments
  idea-stage/
    IDEA_REPORT.md
    IDEA_CANDIDATES.md
    docs/research_contract.md
  refine-logs/
    FINAL_PROPOSAL.md
    REVIEW_SUMMARY.md
    REFINE_STATE.json
    EXPERIMENT_PLAN.md
    EVALUATION_CONTRACT.md
    EXPERIMENT_MANIFEST.yaml
    EXPERIMENT_TRACKER.md
    EXPERIMENT_LOG.md
    PIPELINE_SUMMARY.md
  experiments/
    <project-specific code, configs, results>
  review-stage/
    AUTO_REVIEW.md
    REVIEW_STATE.json
  figures/
    scripts, specs, plots, tables, mermaid diagrams
  paper/
    main.tex
    sections/
    references.bib
    main.pdf
    PROOF_AUDIT.{md,json}
    PAPER_CLAIM_AUDIT.{md,json}
    CITATION_AUDIT.{md,json}
  rebuttal/
    REVIEWS_RAW.md
    ISSUE_BOARD.md
    STRATEGY_PLAN.md
    REBUTTAL_DRAFT_rich.md
    PASTE_READY.txt
    REVISION_PLAN.md
    REBUTTAL_STATE.md
```

## 0.8 Practical Checklist

Before calling a workflow "complete", check:

- Did every durable artifact get a `MANIFEST.md` row?
- Did reviewer calls write `.aris/traces/...`?
- Did state files mark `"status": "completed"` when the loop ended?
- Did Workflow 2 generate or explicitly skip `CLAIMS_FROM_RESULTS.md`?
- Did Workflow 3 run proof, claim, and citation audits when detectors matched?
- Did `tools/verify_paper_audits.sh` pass before declaring submission readiness?
- Did `AGENTS.md` Pipeline Status get updated on stage transition or handoff?


# 1 skills同步
> 参考：tools/SKILL_SYNC_AND_INSTALL.md

```bash
# 1. Edit the source skill

$EDITOR skills/<skill-name>/SKILL.md
  

# 2. Sync the Codex mirror

## step1 确认当前是否有改动没有同步
python3 tools/sync_codex_skill_mirror.py --dry-run 

## step2 进行同步
python3 tools/sync_codex_skill_mirror.py --apply

## step3 再次检查是否同步干净
python3 tools/sync_codex_skill_mirror.py --dry-run


# 3. ## Unified Project Install

bash tools/install_aris.sh --target claude
bash tools/install_aris.sh /path/to/target/repo --target claude


bash tools/install_aris.sh --target codex 
bash tools/install_aris.sh /path/to/target/repo --target codex


bash tools/install_aris.sh --target gemini 
bash tools/install_aris.sh /path/to/target/repo --target gemini
```
For Codex reviewer overlays, keep the overlay flag when reconciling:

```bash
bash tools/install_aris.sh --target codex --with-claude-review-overlay

bash tools/install_aris.sh --target codex --with-gemini-review-overlay
```