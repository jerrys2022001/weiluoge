#!/usr/bin/env python3
"""Run a scheduled blog slot with local scheduler code against a clean worktree."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ENABLE_POST_PUBLISH_INDEX_ENV = 'WEILUOGE_ENABLE_POST_PUBLISH_INDEX'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scheduled blog publishing from a clean worktree.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lane", choices=["cleanup", "protocol", "find", "translate", "updates"], required=True)
    parser.add_argument("--slot-offset", type=int, default=0)
    parser.add_argument("--date")
    parser.add_argument("--git-commit", action="store_true")
    parser.add_argument("--git-push", action="store_true")
    parser.add_argument("--git-remote", default="origin")
    parser.add_argument("--git-branch", default="main")
    parser.add_argument("--similarity-threshold", type=float)
    parser.add_argument("--enable-post-publish-index", action="store_true", help="Request Search Console indexing after publish for this run.")
    parser.add_argument("--post-publish-index-delay-seconds", type=int, default=300)
    parser.add_argument("--skip-post-publish-index", action="store_true")
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


def resolve_script_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run_command(cwd: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
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
    if check and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def append_run_log(repo_root: Path, message: str) -> None:
    log_dir = repo_root / ".tmp" / "scheduled-blog-runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    log_path = log_dir / f"{now:%Y-%m-%d}.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{now:%Y-%m-%d %H:%M:%S%z}] {message}\n")


def extract_published_file(output: str) -> str | None:
    match = re.search(r"\bfile=([^\s]+\.html)\b", output)
    if match:
        return match.group(1)
    return None


def trigger_post_publish_index(repo_root: Path, published_file: str, delay_seconds: int) -> None:
    script_path = repo_root / "scripts" / "google_index_after_publish.py"
    if not script_path.exists():
        print(f"post_publish_index skipped missing_script={script_path}", file=sys.stderr)
        return

    command = [
        sys.executable,
        str(script_path),
        "--repo-root",
        str(repo_root),
        "--blog-file",
        published_file,
        "--delay-seconds",
        str(delay_seconds),
    ]
    result = subprocess.run(
        command,
        cwd=repo_root,
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
        print(
            f"post_publish_index failed file={published_file} code={result.returncode}",
            file=sys.stderr,
        )


def should_trigger_post_publish_index(args: argparse.Namespace) -> bool:
    if args.dry_run or args.skip_post_publish_index:
        return False
    if args.enable_post_publish_index:
        return True
    return str(os.environ.get(ENABLE_POST_PUBLISH_INDEX_ENV, "")).strip() == "1"

def build_publish_command(script_root: Path, repo_root: Path, args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(script_root / "scripts" / "publish_unique_blog_slot.py"),
        "--repo-root",
        str(repo_root),
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
    return command


def ref_exists(repo_root: Path, git_command: str, ref_name: str) -> bool:
    result = subprocess.run(
        [git_command, "rev-parse", "--verify", ref_name],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode == 0


def select_worktree_ref(repo_root: Path, git_command: str, args: argparse.Namespace) -> tuple[str, str]:
    remote_ref = f"{args.git_remote}/{args.git_branch}"
    fetch_completed = run_command(
        repo_root,
        [git_command, "fetch", args.git_remote, args.git_branch],
        check=False,
    )
    if fetch_completed.returncode == 0 and ref_exists(repo_root, git_command, remote_ref):
        return remote_ref, "fetched_remote"

    if ref_exists(repo_root, git_command, remote_ref):
        print(
            f"fetch failed for {remote_ref}; using cached tracking ref instead",
            file=sys.stderr,
        )
        return remote_ref, "cached_remote"

    if ref_exists(repo_root, git_command, args.git_branch):
        print(
            f"fetch failed and remote ref missing; using local branch {args.git_branch} instead",
            file=sys.stderr,
        )
        return args.git_branch, "local_branch"

    print("fetch failed and local branch missing; using HEAD instead", file=sys.stderr)
    return "HEAD", "head_fallback"


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    script_root = resolve_script_root()
    git_command = resolve_git_command()
    (repo_root / ".tmp").mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="scheduled-blog-", dir=str(repo_root / ".tmp")))
    worktree_path = temp_root / "worktree"
    try:
        append_run_log(
            repo_root,
            f"start lane={args.lane} offset={args.slot_offset} date={args.date or 'today'} dry_run={str(args.dry_run).lower()}",
        )
        worktree_ref, ref_source = select_worktree_ref(repo_root, git_command, args)
        append_run_log(repo_root, f"worktree_ref={worktree_ref} source={ref_source}")
        run_command(
            repo_root,
            [git_command, "worktree", "add", "--detach", str(worktree_path), worktree_ref],
        )

        command = build_publish_command(script_root, worktree_path, args)
        completed = run_command(worktree_path, command, check=False)
        publish_output = (completed.stdout or "") + "\n" + (completed.stderr or "")
        published_file = extract_published_file(publish_output)
        if completed.returncode != 0:
            print(
                f"worktree publish failed for lane={args.lane} code={completed.returncode}; retrying with local repo state",
                file=sys.stderr,
            )
            append_run_log(
                repo_root,
                f"worktree_publish_failed lane={args.lane} code={completed.returncode} fallback=local_repo",
            )
            fallback_command = build_publish_command(script_root, repo_root, args)
            fallback_completed = run_command(repo_root, fallback_command)
            publish_output = (fallback_completed.stdout or "") + "\n" + (fallback_completed.stderr or "")
            published_file = extract_published_file(publish_output)
        if should_trigger_post_publish_index(args) and published_file is not None:
            trigger_post_publish_index(repo_root, published_file, args.post_publish_index_delay_seconds)
        append_run_log(
            repo_root,
            f"done lane={args.lane} offset={args.slot_offset} published_file={published_file or 'none'}",
        )
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
