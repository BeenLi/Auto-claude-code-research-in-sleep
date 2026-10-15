"""Main-tree skills serve both Claude and Gemini installs, so their ARIS_REPO
resolvers must read both install manifests (the Codex mirror reads its own)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ".aris/installed-skills.txt"
GEMINI = ".aris/installed-skills-gemini.txt"
READ_RE = re.compile(r"awk -F'\\t' '\$1==\"repo_root\"\{print \$2; exit\}' (\.aris/installed-skills[a-z-]*\.txt)")


def main_tree_markdown() -> list[Path]:
    return [
        path
        for path in sorted((REPO_ROOT / "skills").rglob("*.md"))
        if not path.relative_to(REPO_ROOT / "skills").parts[0].startswith(("skills-codex", "_unused"))
    ]


def test_every_claude_manifest_read_falls_back_to_the_gemini_manifest() -> None:
    unpaired = []
    for path in main_tree_markdown():
        reads = READ_RE.findall(path.read_text(encoding="utf-8"))
        for i, manifest in enumerate(reads):
            if manifest == CLAUDE and (i + 1 >= len(reads) or reads[i + 1] != GEMINI):
                unpaired.append(str(path.relative_to(REPO_ROOT)))
    assert unpaired == [], "Claude manifest read without the Gemini fallback right after it"


def test_canonical_resolver_finds_the_repo_from_a_gemini_install(tmp_path: Path) -> None:
    contract = (REPO_ROOT / "skills/shared-references/integration-contract.md").read_text(encoding="utf-8")
    section = contract.split("#### Resolver block", 1)[1]
    block = section.split("```bash\n", 1)[1].split("```", 1)[0]
    (tmp_path / ".aris").mkdir()
    (tmp_path / ".aris" / "installed-skills-gemini.txt").write_text(f"repo_root\t{REPO_ROOT}\n")
    script = block.replace("<helper>", "research_wiki.py") + '\nprintf "%s|%s" "$ARIS_REPO" "$HELPER"\n'

    result = subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{REPO_ROOT}|{REPO_ROOT}/tools/research_wiki.py"
