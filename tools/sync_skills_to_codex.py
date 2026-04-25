#!/usr/bin/env python3
"""Sync Claude Code native skills to Codex compatible versions.

Reads skills from `skills/` directory, replaces all mcp__codex__codex and
mcp__codex__codex-reply references with spawn_agent and send_input, and
writes the converted files to `skills/skills-codex/`.
"""

import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "skills"
DEST_ROOT = REPO_ROOT / "skills" / "skills-codex"

# Text replacements
TEXT_REPLACEMENTS = [
    ("mcp__codex__codex-reply", "send_input"),
    ("mcp__codex__codex", "spawn_agent"),
    ("returned `threadId`", "returned agent id"),
    ("returned threadId", "returned agent id"),
    ("saved `threadId`", "saved agent id"),
    ("saved threadId", "saved agent id"),
    ("`spawn_agent` reviewer call", "`spawn_agent` (`spawn_agent`) reviewer call"), # fix edge cases if needed
]

def convert_content(text: str) -> str:
    # 1. Handle tool definitions in YAML blocks
    
    # Replace mcp__codex__codex block
    def replace_mcp_codex(match):
        block = match.group(0)
        # Change tool name
        block = block.replace("mcp__codex__codex:", "spawn_agent:")
        
        # Check for reasoning_effort
        effort_match = re.search(r'config:\s*\{"model_reasoning_effort":\s*"([^"]+)"\}', block)
        if effort_match:
            effort = effort_match.group(1)
            # Remove config line
            block = re.sub(r'^[ \t]*config:.*$\n', '', block, flags=re.MULTILINE)
            # Insert reasoning_effort
            block = block.replace("spawn_agent:\n", f"spawn_agent:\n  reasoning_effort: {effort}\n")
        
        # Replace prompt: with message:
        block = re.sub(r'^[ \t]*prompt:\s*\|', '  message: |', block, flags=re.MULTILINE)
        return block

    text = re.sub(r'^mcp__codex__codex:[\s\S]*?(?=^[^ \t]|^$)', replace_mcp_codex, text, flags=re.MULTILINE)
    
    # Replace mcp__codex__codex-reply block
    def replace_mcp_reply(match):
        block = match.group(0)
        block = block.replace("mcp__codex__codex-reply:", "send_input:")
        block = re.sub(r'^[ \t]*prompt:\s*\|', '  message: |', block, flags=re.MULTILINE)
        return block

    text = re.sub(r'^mcp__codex__codex-reply:[\s\S]*?(?=^[^ \t]|^$)', replace_mcp_reply, text, flags=re.MULTILINE)

    # 2. Handle text replacements
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
        
    # Clean up double spawn_agent if accidentally created
    text = text.replace("`spawn_agent` (`spawn_agent`)", "`spawn_agent`")

    return text

def main():
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    
    # Exclude directories
    exclude_dirs = {"skills-codex", "skills-codex-claude-review", "skills-codex-gemini-review"}
    
    count = 0
    for src_path in SRC_ROOT.rglob("*"):
        if src_path.is_dir():
            continue
            
        rel_path = src_path.relative_to(SRC_ROOT)
        
        # Skip if in excluded dirs
        if rel_path.parts[0] in exclude_dirs:
            continue
            
        dest_path = DEST_ROOT / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if src_path.suffix == ".md" and src_path.name == "SKILL.md":
            content = src_path.read_text(encoding="utf-8")
            converted = convert_content(content)
            dest_path.write_text(converted, encoding="utf-8")
        else:
            # Direct copy for other files (templates, etc.)
            shutil.copy2(src_path, dest_path)
            
        count += 1

    print(f"Successfully synced {count} files to {DEST_ROOT}")

if __name__ == "__main__":
    main()
