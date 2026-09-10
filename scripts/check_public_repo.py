#!/usr/bin/env python3
"""Fail when known internal material or credential formats enter this public repo."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKED_PATH_PARTS = {
    ".private",
    ".codex-tmp-private",
    "docs-private",
    "personal",
    "veai-private",
}
BLOCKED_FILENAMES = {"PUBLIC_LAUNCH_DRAFT.md", "public-files.txt", "export_public.py"}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}
SKIP_PARTS = {".git", "__pycache__", ".venv", "node_modules"}


def relative_paths(staged: bool) -> list[Path]:
    if staged:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return [Path(line) for line in result.stdout.splitlines() if line]
    return [path.relative_to(ROOT) for path in ROOT.rglob("*") if path.is_file()]


def check_paths(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for relative in paths:
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        if relative.name in BLOCKED_FILENAMES or any(part in BLOCKED_PATH_PARTS for part in relative.parts):
            errors.append(f"internal-only path is not allowed: {relative}")
            continue
        path = ROOT / relative
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"possible {label} in: {relative}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="check only staged added, copied, modified, or renamed files")
    args = parser.parse_args()
    errors = check_paths(relative_paths(args.staged))
    if errors:
        print("Public-repository check failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print("Public-repository check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
