from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import research_wiki as wiki


class ObsidianPaperParserTest(unittest.TestCase):
    def test_extracts_frontmatter_chinese_sections_and_related_wikilinks(self):
        with tempfile.TemporaryDirectory(prefix="aris-parser-") as tmp:
            note = Path(tmp) / "CXL KV Cache Offload.md"
            note.write_text(
                """---
title: "CXL KV Cache Offload for LLM Serving"
method_name: "KV-Migrate"
authors: ["Alice Smith", "Bob Lee"]
year: 2025
venue: "OSDI"
tags: ["llm", "systems"]
zotero_item_key: ABC123
zotero_collection: PaperRead
arxiv_id: "2501.12345"
created: 2026-05-18
---

# CXL KV Cache Offload for LLM Serving

## 一句话总结

把冷 KV cache 迁移到 CXL 内存以降低 GPU HBM 压力。

## 这篇论文为什么重要

- LLM serving 的长上下文请求会让 KV cache 成为容量瓶颈。
- 现有 CPU offload 会带来明显 PCIe 往返延迟。

## 关键 insight

KV cache 访问存在温度分层，可以把冷块移到 CXL。

### 系统瓶颈

GPU HBM 容量和跨设备带宽共同限制吞吐。

## 系统设计总览

系统在 prefill 后预测冷 KV block 并异步迁移。

## 核心结果

在 ShareGPT workload 上吞吐提升 1.4x。

## 批判性思考

对短上下文收益有限。

## 经验与可迁移启示

KV 迁移策略可以复用于多 GPU 分层缓存。

## 实验设置

- Workloads: ShareGPT, LongBench
- Baselines: vLLM, CPU offload
- Metrics: TTFT, throughput

## 相关工作定位

对比 [[FlashAttention]] 和 [[PagedAttention|Paged Attention]]。
"""
            )

            projection = wiki.parse_obsidian_paper_note(note)

        self.assertEqual(projection.title, "CXL KV Cache Offload for LLM Serving")
        self.assertEqual(projection.method_name, "KV-Migrate")
        self.assertEqual(projection.authors, ["Alice Smith", "Bob Lee"])
        self.assertEqual(projection.year, 2025)
        self.assertEqual(projection.zotero_item_key, "ABC123")
        self.assertEqual(projection.doi, "")
        self.assertIn("KV cache", projection.fields["one_line"])
        self.assertIn("容量瓶颈", projection.fields["core_problem"])
        self.assertIn("CXL", projection.fields["key_insight"])
        self.assertIn("GPU HBM", projection.fields["system_bottleneck"])
        self.assertIn("ShareGPT", projection.fields["workloads"])
        self.assertEqual(projection.related_papers, ["FlashAttention", "PagedAttention"])


if __name__ == "__main__":
    unittest.main()
