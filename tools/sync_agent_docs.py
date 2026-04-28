#!/usr/bin/env python3
"""
Sync Agent Documentation Script

This script uses `GEMINI.md` as the Single Source of Truth (SSoT)
and automatically generates/updates `CLAUDE.md` and `AGENTS.md` (for Codex),
handling the necessary tool-specific string replacements.

Usage:
    python3 tools/sync_agent_docs.py
"""

import os
import sys

def sync_docs():
    # Get project root directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    gemini_path = os.path.join(base_dir, 'GEMINI.md')
    claude_path = os.path.join(base_dir, 'CLAUDE.md')
    agents_path = os.path.join(base_dir, 'AGENTS.md')

    if not os.path.exists(gemini_path):
        print(f"Error: {gemini_path} not found.")
        sys.exit(1)

    with open(gemini_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # --- 1. Generate CLAUDE.md ---
    claude_content = content.replace('# GEMINI.md', '# CLAUDE.md')
    claude_content = claude_content.replace(
        'guidance to Gemini (Gemini.ai/code)', 
        'guidance to Claude Code (claude.ai/code)'
    )
    claude_content = claude_content.replace(
        'Gemini implements fixes', 
        'Claude implements fixes'
    )
    claude_content = claude_content.replace(
        'illustration` (gemini/mermaid/false)', 
        'illustration` (claude/mermaid/false)'
    )

    with open(claude_path, 'w', encoding='utf-8') as f:
        f.write(claude_content)
    print(f"✅ Synced: {claude_path}")

    # --- 2. Generate AGENTS.md (Codex) ---
    agents_content = content.replace('# GEMINI.md', '# AGENTS.md')
    agents_content = agents_content.replace(
        'guidance to Gemini (Gemini.ai/code)', 
        'guidance to Codex (Codex.ai/code)'
    )
    agents_content = agents_content.replace(
        'Gemini implements fixes', 
        'Codex implements fixes'
    )
    agents_content = agents_content.replace(
        'illustration` (gemini/mermaid/false)', 
        'illustration` (codex/mermaid/false)'
    )

    with open(agents_path, 'w', encoding='utf-8') as f:
        f.write(agents_content)
    print(f"✅ Synced: {agents_path}")

if __name__ == '__main__':
    sync_docs()
