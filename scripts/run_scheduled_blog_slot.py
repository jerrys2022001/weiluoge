#!/usr/bin/env python3
"""Run a scheduled blog slot from a clean worktree based on origin/main."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scheduled blog publishing from a clean origin/main worktree.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lane", choices=["cleanup", "protocol", "updates"], required=True)
    parser.add_argument("--slot-offset", type=int, default=0)
    parser.add_argument("--date")
    parser.add_argument("--git-commit", action="store_true")
    parser.add_argument("--git-push", action="store_true")
    parser.add_argument("--git-remote", default="origin")
    parser.add_argument("--git-branch", default="main")
    parser.add_argument("--similarity-threshold", type=float)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def resolve_git_command() -> str:
    resolved = shutil.which("git")
    if resolved:
        return resolved

    candidates = [
        Path(r"C:\Program Files\Git\cmd\git.exe"),
        Path(r"C:\Program Files\Git\bin\git.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "Git" / "cmd" / "git.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise SystemExit("Unable to resolve git executable for scheduled blog publishing.")


def run_command(cwd: Path, args: list[str]) -> None:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    git_command = resolve_git_command()
    (repo_root / ".tmp").mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="scheduled-blog-", dir=str(repo_root / ".tmp")))
    worktree_path = temp_root / "worktree"
    try:
        run_command(repo_root, [git_command, "fetch", args.git_remote, args.git_branch])
        run_command(repo_root, [git_command, "worktree", "add", "--detach", str(worktree_path), f"{args.git_remote}/{args.git_branch}"])

        command = [
            sys.executable,
            str(worktree_path / "scripts" / "publish_unique_blog_slot.py"),
            "--repo-root",
            str(worktree_path),
            "--lane",
            args.lane,
            "--slot-offset",
            str(args.slot_offset),
            "--git-remote",
            args.git_remote,
            "--git-branch",
            args.git_branch,
        ]
        if args.date:
            command.extend(["--date", args.date])
        if args.git_commit:
            command.append("--git-commit")
        if args.git_push:
            command.append("--git-push")
        if args.similarity_threshold is not None:
            command.extend(["--similarity-threshold", str(args.similarity_threshold)])
        if args.force:
            command.append("--force")
        if args.dry_run:
            command.append("--dry-run")

        run_command(worktree_path, command)
        return 0
    finally:
        subprocess.run(
            [git_command, "worktree", "remove", str(worktree_path), "--force"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
