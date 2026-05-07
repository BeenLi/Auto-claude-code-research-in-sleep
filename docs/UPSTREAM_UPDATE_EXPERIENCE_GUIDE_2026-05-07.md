# 2026-05-07 Upstream Update Experience Guide

本文说明当前 `myMain` 分支刚合入的 upstream 更新，以及如何最快体验这些更新。

## 一句话总结

这批更新主要让 ARIS 的工具链更可靠：文献检索新增 Gemini/OpenAlex，实验队列能正确找到并部署 helper，项目安装会创建 `.aris/tools`，research wiki 的 helper 解析不再依赖硬编码 `tools/` 路径。

当前分支新增的关键提交：

```text
79ff10e feat(research-lit): add gemini and openalex as literature search sources
879f877 fix(gemini-search): correct npm package name to @google/gemini-cli
d985e82 fix(research-lit,openalex): make new sources strictly opt-in for safe merge
f1c4a70 feat(install): add optional .aris/tools symlink during install (#174 Phase 0)
e2612d4 fix(experiment-queue): repair orchestration paths so queue actually launches
cf6f4ad feat(idea-discovery): include gemini in Phase 1 literature survey by default
7f73f0c fix(research-wiki): caller skills resolve helper via fallback chain
3729946 docs: document project-local tools symlink install flow
be6229e fix: keep research wiki helper resolution test py39-compatible
```

## 最快体验路径

如果你只想最快用上这些能力，在目标项目里执行：

```bash
ARIS_REPO=/Users/bytedance/Tools/Auto-claude-code-research-in-sleep
PROJECT=/path/to/your/project

bash "$ARIS_REPO/tools/install_aris.sh" "$PROJECT" --no-doc
```

如果目标项目已经安装过 ARIS，则改用 reconcile：

```bash
bash "$ARIS_REPO/tools/install_aris.sh" "$PROJECT" --reconcile --no-doc
```

确认 `.aris/tools` 已就位：

```bash
ls -l "$PROJECT/.aris/tools"
```

预期看到它指向 ARIS repo 的 `tools/`：

```text
.aris/tools -> /Users/bytedance/Tools/Auto-claude-code-research-in-sleep/tools
```

这一步是体验 research-wiki helper fallback、experiment-queue helper fallback、未来 tools helper 迁移的最快入口。

## 更新内容

### 1. 项目安装新增 `.aris/tools`

`tools/install_aris.sh` 现在会在目标项目创建：

```text
<project>/.aris/tools -> <aris-repo>/tools
```

这个 symlink 不写入 `installed-skills.txt`，而是通过 exact target 判断是否由 ARIS 管理：

- 如果 `.aris/tools` 正好指向 `<aris-repo>/tools`，卸载时会安全移除。
- 如果 `.aris/tools` 是用户自己的目录、文件、或指向其他位置的 symlink，installer 会保留它。
- `--dry-run` 会预览该 symlink 操作。

最快验证：

```bash
bash "$ARIS_REPO/tools/install_aris.sh" "$(mktemp -d)" --aris-repo "$ARIS_REPO" --dry-run --no-doc
```

### 2. `/experiment-queue` 路径修复

实验队列不再假设 helper 在错误路径下。现在 helper 解析顺序是：

```text
.aris/tools/experiment_queue/
tools/experiment_queue/
$ARIS_REPO/tools/experiment_queue/
```

同时修复了远端启动文档中的几个容易踩坑的点：

- 使用真实路径 `tools/experiment_queue/queue_manager.py` 和 `build_manifest.py`。
- 远端运行目录使用 `~/.aris_queue/runs/<RUN_TS>`，避免 `/tmp` 冲突。
- `scp` 使用 remote-relative path，避免 SFTP 模式不展开 `$HOME`。
- 启动参数使用 `--log-dir`，不再误用 `--log`。
- 保存 `run_meta.txt`，便于恢复和监控。

最快验证：

```bash
python3 "$ARIS_REPO/tools/experiment_queue/build_manifest.py" --help
python3 "$ARIS_REPO/tools/experiment_queue/queue_manager.py" --help
```

### 3. `/research-lit` 新增 Gemini 和 OpenAlex

新增两个文献源：

- `gemini`: 用 Gemini 做广覆盖文献发现，适合补关键词检索漏掉的方向。
- `openalex`: 用 OpenAlex 开放引用图补充论文元数据、机构、引用等信息。

默认行为保持安全：普通 `/research-lit "topic"` 不会自动触发 Gemini/OpenAlex；它们必须显式指定。

最快体验：

```text
/research-lit "DPU NIC lossless compression fairness for LLM communication" — sources: all, gemini
/research-lit "DPU NIC lossless compression fairness for LLM communication" — sources: openalex
```

OpenAlex helper 需要 Python `requests`。如果未安装，会优雅跳过并提示：

```bash
python3 -m pip install requests
```

Gemini CLI 包名修正为：

```bash
npm install -g @google/gemini-cli
```

### 4. `/idea-discovery` 默认带 Gemini

`/idea-discovery` 的 Phase 1 现在会在用户没有显式指定 `— sources:` 时，调用：

```text
/research-lit "$ARGUMENTS" — sources: all, gemini
```

如果你想关闭 Gemini，显式指定 sources 即可：

```text
/idea-discovery "NIC/DPU compression for LLM serving" — sources: all
```

最快体验：

```text
/idea-discovery "NIC/DPU compression for LLM serving"
```

有 Gemini CLI 时会走 Gemini 扩展检索；没有时 `/research-lit` 会跳过该 source，不影响主流程。

### 5. `/research-wiki` helper fallback 修复

过去多个 skill 写死：

```bash
python3 tools/research_wiki.py ...
```

这在项目级安装后容易失败，因为目标项目通常只有 `.aris/tools`，没有自己的 `tools/` 目录。

现在统一使用：

```text
.aris/tools/research_wiki.py
tools/research_wiki.py
$ARIS_REPO/tools/research_wiki.py
```

行为差异：

- `/research-wiki` 自己找不到 helper 时 hard-fail。
- `/research-lit`、`/idea-creator`、`/result-to-claim`、paper-reading skills 找不到 helper 时 warn-and-skip，只跳过 wiki 副作用，不丢主输出。

最快体验：

```bash
cd "$PROJECT"
python3 .aris/tools/research_wiki.py init research-wiki
test -f research-wiki/query_pack.md
```

然后跑一次带 wiki 副作用的文献流程：

```text
/research-lit "DPU NIC compression fairness" — sources: all
```

### 6. 本地维护文档已更新

`tools/SKILL_SYNC_AND_INSTALL.md` 已补充 `.aris/tools` 的安装、reconcile、卸载语义。以后修改安装链或 helper resolution 时，应同步维护这份文档。

## 推荐验证命令

在 ARIS repo 里运行：

```bash
python3 -m pytest tests/test_install_aris_tools_symlink.py tests/test_research_wiki_helper_resolution.py -q
python3 tools/experiment_queue/build_manifest.py --help
python3 tools/experiment_queue/queue_manager.py --help
python3 -S tools/openalex_fetch.py search test --max 1
bash tools/install_aris.sh "$(mktemp -d)" --aris-repo "$PWD" --dry-run --no-doc
```

预期：

- 两个 pytest 文件通过。
- experiment queue 两个 helper 能打印 `--help`。
- `python3 -S tools/openalex_fetch.py ...` 在缺 `requests` 时返回清晰提示，不出现 traceback。
- installer dry-run 会显示 `.aris/tools` symlink 计划。

## C-Share 当前建议

当前 C-Share 已进入 implementation 阶段。最快收益来自两件事：

1. 先重跑 `install_aris.sh`，确保 `.aris/tools` 存在。
2. 后续启动 `/experiment-bridge` 或实验队列时，优先使用新的 `/experiment-queue` helper 解析和远端 run directory 规范。

如果要补文献校准，用：

```text
/research-lit "shared DPU NIC lossless compression service fairness LLM communication" — sources: all, gemini, openalex
```

如果只想保持传统低成本检索，用：

```text
/research-lit "shared DPU NIC lossless compression service fairness LLM communication" — sources: all
```
