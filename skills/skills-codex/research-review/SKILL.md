***

name: research-review
description: Get a deep critical review of research from GPT via Codex subagent. Use when user says "review my research", "help me review", "get external review", or wants critical feedback on research ideas, papers, or experimental results.
argument-hint: \[topic-or-scope]
allowed-tools: Bash(\*), Read, Grep, Glob, Write, Edit, Agent, mcp\_\_codex\_\_codex, mcp\_\_codex\_\_send_input
-----------------------------------------------------------------------------------------------------------------

# Research Review via Codex subagent (xhigh reasoning)

Get a multi-round critical review of research work from an external LLM with maximum reasoning depth.

## Constants

- REVIEWER\_MODEL = `gpt-5.5` — Model used via Codex subagent. Must be an OpenAI model (e.g., `gpt-5.5`, `o3`, `gpt-4o`)
- **REVIEWER\_BACKEND =** **`codex`** — Default: Codex subagent (xhigh). Override with `— reviewer: oracle-pro` for GPT-5.5 Pro via Oracle MCP. See `shared-references/reviewer-routing.md`.

## Context: $ARGUMENTS

## Prerequisites

- **Codex subagent Server** configured in Claude Code:
  ```bash
  claude mcp add codex -s user -- codex mcp-server
  ```
- This gives Claude Code access to `spawn_agent` and `send_input` tools

## Workflow

### Step 1: Gather Research Context

Before calling the external reviewer, compile a comprehensive briefing:

1. Read project narrative documents (e.g., STORY.md, README.md, paper drafts)
2. Read any memory/notes files for key findings and experiment history
3. Identify: core claims, methodology, key results, known weaknesses

<br />

### Step 2: Initial Review (Round 1)

Send a detailed prompt with xhigh reasoning:

```
spawn_agent:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    [Full research context + specific questions]
    Please act as a senior computer architecture / systems reviewer (MICRO/ISCA/HPCA/ASPLOS/NSDI/SIGCOMM level).
    Domain: AI infrastructure for LLM across compute, memory/storage/data movement, interconnect/network, or runtime/system. Runtime/serving claims are in scope only when tied to a concrete hardware bottleneck.

    Identify:
    1. Logical gaps or unjustified claims (e.g., missing area/power analysis, unrealistic throughput assumptions)
    2. Missing experiments that would strengthen the story:
       - Micro-architectural detail (pipeline stages, critical path, resource usage)
       - Real hardware measurement vs simulation — which claims need real data?
       - Comparison with the closest hardware/system baseline for the selected layer
       - Generalizability: does the result hold across representative LLM infrastructure workloads?
    3. Narrative weaknesses: Is the problem clearly motivated with real system bottleneck numbers?
    4. Whether the hardware contribution is sufficient (area/power overhead acceptable? throughput competitive?)
    5. Whether the chosen AI infrastructure layer and validation backend are coherent. For RDMA/NIC compression, also check RoCEv2/DCQCN/credit flow control and Rx decompression expansion pressure.
    Please be brutally honest.
```

### Step 3: Iterative Dialogue (Rounds 2-N)

Use `send_input` with the returned `agent_id` to continue the conversation:

For each round:

1. **Respond** to criticisms with evidence/counterarguments
2. **Ask targeted follow-ups** on the most actionable points
3. **Request specific deliverables**: experiment designs, paper outlines, claims matrices

Key follow-up patterns:

- "If we reframe X as Y, does that change your assessment?"
- "What's the minimum experiment to satisfy concern Z?"
- "Please design the minimal additional experiment package with the highest acceptance lift per simulator/prototype week"
- "Please write a mock MICRO/ISCA/HPCA/ASPLOS review with scores"
- "Give me a results-to-claims matrix for possible experimental outcomes"

### Step 4: Convergence

Stop iterating when:

- Both sides agree on the core claims and their evidence requirements
- A concrete experiment plan is established
- The narrative structure is settled

### Step 5: Document Everything

Save the full interaction and conclusions to a review document in the project root:

- Round-by-round summary of criticisms and responses
- Final consensus on claims, narrative, and experiments
- Claims matrix (what claims are allowed under each possible outcome)
- Prioritized TODO list with estimated compute costs
- Paper outline if discussed

Update project memory/notes with key review conclusions.

## Key Rules

- ALWAYS use `config: {"model_reasoning_effort": "xhigh"}` for reviews
- Send comprehensive context in Round 1 — the external model cannot read your files
- Be honest about weaknesses — hiding them leads to worse feedback
- Push back on criticisms you disagree with, but accept valid ones
- Focus on ACTIONABLE feedback — "what experiment would fix this?"
- Document the agent_id for potential future resumption
- The review document should be self-contained (readable without the conversation)

## Prompt Templates

### For initial review:

"I'm going to present a computer architecture research project for your critical review. Please act as a senior MICRO/ISCA/HPCA/ASPLOS reviewer. Domain: AI infrastructure for LLM across compute, memory/storage/data movement, interconnect/network, or runtime/system..."

### For experiment design:

"Please design the minimal additional experiment package that gives the highest acceptance lift. Focus on: (1) which claims need real hardware measurement vs simulation, (2) what micro-benchmark or trace workloads cover the key cases, (3) what overhead analysis (area/power/latency/bandwidth) a reviewer would require. Be very specific about configurations."

### For paper structure:

"Please turn this into a concrete paper outline with section-by-section claims and figure plan. Include: motivation with real bottleneck numbers, micro-architecture diagram, end-to-end system integration, evaluation methodology, and comparison to prior art."

### For claims matrix:

"Please give me a results-to-claims matrix: what claim is allowed under each possible outcome of experiments X and Y? (e.g., if throughput improvement < 10%, can we still claim latency benefit?)"

### For mock review:

"Please write a mock MICRO/ISCA review with: Summary, Strengths, Weaknesses, Questions for Authors, Score (1-6 scale), Confidence, and What Would Move Toward Accept."

## Review Tracing

After each `spawn_agent` or `send_input` reviewer call, save the trace following `shared-references/review-tracing.md`. Use `tools/save_trace.sh` or write files directly to `.aris/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
