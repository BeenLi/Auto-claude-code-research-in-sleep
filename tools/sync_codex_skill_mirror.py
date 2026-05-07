#!/usr/bin/env python3
"""Synchronize skills/skills-codex from the main skills tree.

The Codex mirror is a generated/adapted view of skills/*, not an independent
authoring surface. By default this script only prints the planned changes; pass
--apply to update the mirror.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
MIRROR_ROOT = SKILLS_ROOT / "skills-codex"
SHARED_REFS = "shared-references"
README_NAMES = {"README.md", "README_CN.md"}
IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}
IGNORED_FILE_NAMES = {".DS_Store"}


@dataclass(frozen=True)
class PlannedChange:
    action: str
    path: str


def is_main_skill_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    name = path.name
    if name == SHARED_REFS or name.startswith("skills-codex"):
        return False
    return (path / "SKILL.md").is_file()


def main_skill_dirs() -> dict[str, Path]:
    return {path.name: path for path in sorted(SKILLS_ROOT.iterdir()) if is_main_skill_dir(path)}


def mirror_skill_dirs() -> dict[str, Path]:
    if not MIRROR_ROOT.exists():
        return {}
    return {
        path.name: path
        for path in sorted(MIRROR_ROOT.iterdir())
        if path.is_dir() and (path / "SKILL.md").is_file()
    }


def ignore_names(_dir: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in IGNORED_FILE_NAMES or name in IGNORED_DIR_NAMES:
            ignored.add(name)
    return ignored


def transform_codex_text(text: str) -> str:
    """Apply small textual adaptations for the Codex subagent runtime."""

    replacements = [
        ("mcp__codex__codex-reply", "send_input"),
        ("mcp__codex__codex", "spawn_agent"),
        ("codex-reply", "send_input"),
        ("Codex MCP thread", "Codex subagent"),
        ("Codex MCP reviewer", "Codex subagent reviewer"),
        ("Codex MCP", "Codex subagent"),
        ("MCP thread", "subagent"),
        ("MCP reviewer", "subagent reviewer"),
        ("threadId", "agent_id"),
        ("thread_id", "agent_id"),
        ("thread ID", "agent id"),
        ("thread id", "agent id"),
        ("same thread", "same agent"),
        ("fresh thread", "fresh agent"),
        ("saved thread", "saved agent"),
        ("Save the agent_id", "Save the agent id"),
        ("returned agent_id", "returned agent id"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def transform_markdown_files(root: Path) -> None:
    for path in root.rglob("*.md"):
        if any(part in IGNORED_DIR_NAMES for part in path.parts):
            continue
        text = path.read_text()
        transformed = transform_codex_text(text)
        if transformed != text:
            path.write_text(transformed)


def build_desired_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=ignore_names)
    transform_markdown_files(target)


def file_bytes(path: Path) -> bytes:
    return path.read_bytes()


def collect_files(root: Path) -> dict[Path, Path]:
    files: dict[Path, Path] = {}
    if not root.exists():
        return files
    for path in root.rglob("*"):
        if any(part in IGNORED_DIR_NAMES for part in path.parts):
            continue
        if path.name in IGNORED_FILE_NAMES:
            continue
        if path.is_file() or path.is_symlink():
            files[path.relative_to(root)] = path
    return files


def trees_equal(left: Path, right: Path) -> bool:
    left_files = collect_files(left)
    right_files = collect_files(right)
    if set(left_files) != set(right_files):
        return False
    for rel in left_files:
        lpath = left_files[rel]
        rpath = right_files[rel]
        if lpath.is_symlink() or rpath.is_symlink():
            if not (lpath.is_symlink() and rpath.is_symlink()):
                return False
            if lpath.readlink() != rpath.readlink():
                return False
            continue
        if not filecmp.cmp(lpath, rpath, shallow=False):
            return False
    return True


def replace_tree(source: Path, dest: Path) -> None:
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        else:
            shutil.rmtree(dest)
    shutil.copytree(source, dest, symlinks=True)


def sync_tree(source: Path, dest: Path, label: str, apply: bool, changes: list[PlannedChange]) -> None:
    with tempfile.TemporaryDirectory(prefix="codex-skill-mirror-") as tmp:
        desired = Path(tmp) / "desired"
        build_desired_tree(source, desired)
        if not dest.exists():
            changes.append(PlannedChange("create", label))
            if apply:
                dest.parent.mkdir(parents=True, exist_ok=True)
                replace_tree(desired, dest)
            return
        if trees_equal(desired, dest):
            return
        changes.append(PlannedChange("update", label))
        if apply:
            replace_tree(desired, dest)


def sync_mirror(apply: bool) -> list[PlannedChange]:
    changes: list[PlannedChange] = []
    main_dirs = main_skill_dirs()
    mirror_dirs = mirror_skill_dirs()

    if not MIRROR_ROOT.exists() and apply:
        MIRROR_ROOT.mkdir(parents=True)

    for name, source in main_dirs.items():
        sync_tree(source, MIRROR_ROOT / name, name, apply, changes)

    for name, dest in mirror_dirs.items():
        if name not in main_dirs:
            changes.append(PlannedChange("delete", name))
            if apply:
                shutil.rmtree(dest)

    shared_source = SKILLS_ROOT / SHARED_REFS
    if shared_source.exists():
        sync_tree(shared_source, MIRROR_ROOT / SHARED_REFS, SHARED_REFS, apply, changes)

    return sorted(changes, key=lambda item: (item.action, item.path))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write planned mirror updates")
    parser.add_argument("--dry-run", action="store_true", help="show planned updates without writing (default)")
    parser.add_argument("--quiet", action="store_true", help="only print summary")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    changes = sync_mirror(apply=args.apply)

    mode = "apply" if args.apply else "dry-run"
    print(f"Codex skill mirror sync ({mode})")
    print(f"  source: {SKILLS_ROOT}")
    print(f"  mirror: {MIRROR_ROOT}")
    print(f"  changes: {len(changes)}")

    if changes and not args.quiet:
        for change in changes:
            print(f"  {change.action:6} {change.path}")
    if not changes:
        print("  clean")
    elif not args.apply:
        print("  dry-run only; rerun with --apply to update the mirror")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
