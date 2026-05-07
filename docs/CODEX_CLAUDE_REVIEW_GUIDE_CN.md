# Codex + Claude 审稿人指南

让 ARIS 以以下方式运行：

- **Codex** 作为主执行者
- **Claude Code CLI** 作为审稿人
- 通过本地 `claude-review` MCP bridge 连接两者

这条路径是对上游 Codex 原生方案的**增量叠加**，不会替代 `skills/skills-codex/`。

## 架构

- 基础技能包：`skills/skills-codex/`
- 审稿覆盖层：`skills/skills-codex-claude-review/`
- 审稿 bridge：`mcp-servers/claude-review/`

安装顺序必须保持：

1. 先安装 `skills/skills-codex/*`
2. 再安装 `skills/skills-codex-claude-review/*`
3. 最后单独注册 `claude-review` MCP

## 安装

```bash
# 只需把 ARIS 克隆到一个稳定位置。
git clone https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep.git ~/aris_repo

# 在每个 Codex 项目中安装 base skills + Claude-review overlay。
cd /path/to/your/project
bash ~/aris_repo/tools/install_aris.sh . --target codex --with-claude-review-overlay
```

安装器会在 `.agents/skills/` 下创建扁平项目级 symlink，写入
`.aris/installed-skills-codex.txt`，并选择 Claude-review overlay。
`claude-review` MCP bridge 需要单独注册。之后更新 skill 内容只需要在
`~/aris_repo` 里 `git pull`；只有新增/删除 skill 或切换 reviewer 时才需要重跑安装器。

如果你的 Claude 登录依赖 `claude-aws` 之类的 shell helper，请改用 wrapper：

```bash
codex mcp remove claude-review
codex mcp add claude-review -- ~/aris_repo/mcp-servers/claude-review/run_with_claude_aws.sh
```

如果你想固定 Claude 审稿模型：

```bash
codex mcp remove claude-review
codex mcp add claude-review --env CLAUDE_REVIEW_MODEL=claude-opus-4-1 -- python3 ~/aris_repo/mcp-servers/claude-review/server.py
```

## 验证

1. 检查 MCP 注册：

```bash
codex mcp list
```

2. 检查 Claude CLI 登录：

```bash
claude -p "Reply with exactly READY" --output-format json --tools ""
```

3. 在项目中启动 Codex：

```bash
codex -C /path/to/your/project
```

## 哪些技能会被覆盖

覆盖层只替换 review-heavy 技能：

- `research-review`
- `novelty-check`
- `research-refine`
- `auto-review-loop`
- `paper-plan`
- `paper-figure`
- `paper-write`
- `auto-paper-improvement-loop`

其余技能仍然来自上游原生 `skills/skills-codex/`。

## 异步 reviewer 流程

对于长论文或长项目审稿，请使用：

- `review_start`
- `review_reply_start`
- `review_status`

原因是这条宿主链路里的 review hop 更长：

`Codex -> claude-review MCP -> 本地 Claude CLI -> Claude 后端`

多出来的本地 CLI hop，正是长同步 reviewer 调用更容易撞上 Codex 侧 MCP 超时的主要原因。

## 项目配置

这条路径不要求你新建特殊项目配置文件。

- 继续使用现有 `CLAUDE.md`
- 保持原有项目目录结构
- 只需要切换 Codex 安装的技能文件和 MCP 注册

## 维护

重新生成这个 overlay 包：

```bash
python3 tools/generate_codex_claude_review_overrides.py
```
