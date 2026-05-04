#!/usr/bin/env python3
"""Verify scheduled blog slots ran and backfill any missing ones."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath

from blog_cleanup_focus_scheduler import ANGLES as CLEANUP_ANGLES
from blog_dualshot_daily_scheduler import ANGLES as DUALSHOT_ANGLES


@dataclass(frozen=True)
class BlogTask:
    task_name: str
    lane: str
    slot_offset: int


BLOG_TASKS: tuple[BlogTask, ...] = (
    BlogTask("WeiLuoGe-Storage-Impact-Blog-Daily-1", "cleanup", 0),
    BlogTask("WeiLuoGe-Bluetooth-Protocol-Blog-Morning-1", "protocol", 0),
    BlogTask("WeiLuoGe-Bluetooth-Protocol-Blog-Morning-2", "protocol", 1),
    BlogTask("WeiLuoGe-Find-AI-Blog-Morning-1", "find", 0),
    BlogTask("WeiLuoGe-DualShot-Camera-Blog-Morning-1", "dualshot", 0),
    BlogTask("WeiLuoGe-Translate-AI-Blog-Morning-1", "translate", 0),
)
TARGET_DAILY_TOTAL = 6
TARGET_DAILY_CLEANUP = 1
TARGET_DAILY_BLUETOOTH = 2
TARGET_DAILY_FIND = 1
TARGET_DAILY_DUALSHOT = 1
TARGET_DAILY_TRANSLATE = 1
INDEX_ARTICLE_RE = re.compile(r"<article>.*?</article>", re.IGNORECASE | re.DOTALL)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
CLEANUP_SLUG_PREFIXES = tuple(angle.slug_prefix for angle in CLEANUP_ANGLES)
DUALSHOT_SLUG_PREFIXES = tuple(angle.slug_prefix for angle in DUALSHOT_ANGLES)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill missing scheduled blog slots after the morning run window.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--date", help="Target date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--git-remote", default="origin")
    parser.add_argument("--git-branch", default="main")
    parser.add_argument("--settle-seconds", type=int, default=420)
    parser.add_argument("--settle-poll-seconds", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def parse_iso_date(raw: str | None) -> date:
    if not raw:
        return date.today()
    return date.fromisoformat(raw)


def query_task_info(task_name: str) -> tuple[date | None, int | None]:
    powershell_script = (
        "$info = Get-ScheduledTaskInfo -TaskName '{name}' -ErrorAction SilentlyContinue; "
        "if ($null -eq $info) {{ exit 1 }}; "
        "[pscustomobject]@{{ LastRunTime = $info.LastRunTime; LastTaskResult = $info.LastTaskResult }} "
        "| ConvertTo-Json -Compress"
    ).format(name=task_name.replace("'", "''"))
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", powershell_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return None, None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, None

    last_run = None
    raw_last_run = payload.get("LastRunTime")
    if isinstance(raw_last_run, str) and len(raw_last_run) >= 10:
        try:
            last_run = date.fromisoformat(raw_last_run[:10])
        except ValueError:
            last_run = None

    raw_last_result = payload.get("LastTaskResult")
    last_result = int(raw_last_result) if isinstance(raw_last_result, int | float) else None
    return last_run, last_result


def run_slot(repo_root: Path, task: BlogTask, target_day: date, dry_run: bool) -> int:
    args = [
        sys.executable,
        str(repo_root / "scripts" / "run_scheduled_blog_slot.py"),
        "--repo-root",
        str(repo_root),
        "--lane",
        task.lane,
        "--slot-offset",
        str(task.slot_offset),
        "--date",
        target_day.isoformat(),
    ]
    if dry_run:
        args.append("--dry-run")
    else:
        args.extend(["--git-commit", "--git-push"])

    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


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

    raise SystemExit("Unable to resolve git executable for blog watchdog.")


def run_git_command(repo_root: Path, git_command: str, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [git_command, *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and completed.returncode != 0:
        command_preview = " ".join(args)
        raise ValueError(f"git command failed ({command_preview}): {completed.stderr.strip()}")
    return completed


def ref_exists(repo_root: Path, git_command: str, ref_name: str) -> bool:
    completed = run_git_command(repo_root, git_command, ["rev-parse", "--verify", ref_name], check=False)
    return completed.returncode == 0


def resolve_content_ref(repo_root: Path, git_command: str, remote: str, branch: str) -> str:
    remote_ref = f"{remote}/{branch}"
    fetch_completed = run_git_command(repo_root, git_command, ["fetch", remote, branch], check=False)
    if fetch_completed.returncode == 0 and ref_exists(repo_root, git_command, remote_ref):
        return remote_ref

    if ref_exists(repo_root, git_command, remote_ref):
        print(
            f"fetch failed for {remote_ref}; using cached tracking ref instead",
            file=sys.stderr,
        )
        return remote_ref

    if ref_exists(repo_root, git_command, branch):
        print(
            f"fetch failed and remote ref missing; using local branch {branch} instead",
            file=sys.stderr,
        )
        return branch

    print("fetch failed and local branch missing; using HEAD instead", file=sys.stderr)
    return "HEAD"


def list_same_day_posts(repo_root: Path, git_command: str, content_ref: str, target_day: date) -> list[str]:
    suffix = f"-{target_day.isoformat()}.html"
    completed = run_git_command(
        repo_root,
        git_command,
        ["ls-tree", "-r", "--name-only", content_ref, "--", "blog"],
    )
    return sorted(
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip().endswith(suffix)
        and post_is_indexable_at_ref(repo_root, git_command, content_ref, line.strip())
    )


def post_is_indexable_at_ref(repo_root: Path, git_command: str, content_ref: str, relative_path: str) -> bool:
    completed = run_git_command(
        repo_root,
        git_command,
        ["show", f"{content_ref}:{relative_path}"],
        check=False,
    )
    if completed.returncode != 0:
        return False
    return '<meta name="robots" content="noindex' not in completed.stdout.lower()


def normalize_title(value: str) -> str:
    return " ".join(value.lower().replace("| velocai blog", "").split())


def read_post_title(repo_root: Path, git_command: str, content_ref: str, relative_path: str) -> str:
    text = run_git_command(
        repo_root,
        git_command,
        ["show", f"{content_ref}:{relative_path}"],
    ).stdout
    match = TITLE_RE.search(text)
    if match is None:
        return PurePosixPath(relative_path).stem
    return match.group(1).strip()


def duplicate_titles_for_day(repo_root: Path, git_command: str, content_ref: str, paths: list[str]) -> list[str]:
    title_counts = Counter(
        normalize_title(read_post_title(repo_root, git_command, content_ref, path))
        for path in paths
    )
    return sorted(title for title, count in title_counts.items() if count > 1)


def blog_index_article_count(repo_root: Path, git_command: str, content_ref: str) -> int:
    text = run_git_command(
        repo_root,
        git_command,
        ["show", f"{content_ref}:blog/index.html"],
    ).stdout
    return len(INDEX_ARTICLE_RE.findall(text))


def assert_publish_integrity(
    repo_root: Path,
    git_command: str,
    content_ref: str,
    target_day: date,
    previous_index_count: int | None,
) -> tuple[int, list[str]]:
    current_index_count = blog_index_article_count(repo_root, git_command, content_ref)
    if previous_index_count is not None and current_index_count < previous_index_count:
        raise ValueError(
            "Blog index article count decreased unexpectedly after publish. "
            f"before={previous_index_count} after={current_index_count}"
        )

    duplicate_titles = duplicate_titles_for_day(
        repo_root,
        git_command,
        content_ref,
        list_same_day_posts(repo_root, git_command, content_ref, target_day),
    )
    if duplicate_titles:
        preview = ", ".join(duplicate_titles[:3])
        raise ValueError(
            "Duplicate same-day blog titles detected after publish. "
            f"titles={preview}"
        )

    return current_index_count, duplicate_titles


def count_matching_posts(paths: list[str], prefixes: tuple[str, ...]) -> int:
    return sum(1 for path in paths if PurePosixPath(path).name.startswith(prefixes))


def count_cleanup_posts(paths: list[str]) -> int:
    return count_matching_posts(paths, CLEANUP_SLUG_PREFIXES)


def count_bluetooth_posts(paths: list[str]) -> int:
    return count_matching_posts(paths, ("bluetooth-",))


def count_find_posts(paths: list[str]) -> int:
    return count_matching_posts(paths, ("find-ai-",))


def count_dualshot_posts(paths: list[str]) -> int:
    return count_matching_posts(paths, DUALSHOT_SLUG_PREFIXES)


def count_translate_posts(paths: list[str]) -> int:
    return count_matching_posts(paths, ("translate-ai-",))


def quota_met(
    total_count: int,
    cleanup_count: int,
    bluetooth_count: int,
    find_count: int,
    dualshot_count: int,
    translate_count: int,
) -> bool:
    return (
        total_count >= TARGET_DAILY_TOTAL
        and cleanup_count >= TARGET_DAILY_CLEANUP
        and bluetooth_count >= TARGET_DAILY_BLUETOOTH
        and find_count >= TARGET_DAILY_FIND
        and dualshot_count >= TARGET_DAILY_DUALSHOT
        and translate_count >= TARGET_DAILY_TRANSLATE
    )


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    target_day = parse_iso_date(args.date)
    git_command = resolve_git_command()
    content_ref = resolve_content_ref(repo_root, git_command, args.git_remote, args.git_branch)
    previous_index_count = blog_index_article_count(repo_root, git_command, content_ref)

    posts = list_same_day_posts(repo_root, git_command, content_ref, target_day)
    total_count = len(posts)
    cleanup_count = count_cleanup_posts(posts)
    bluetooth_count = count_bluetooth_posts(posts)
    find_count = count_find_posts(posts)
    dualshot_count = count_dualshot_posts(posts)
    translate_count = count_translate_posts(posts)

    if quota_met(total_count, cleanup_count, bluetooth_count, find_count, dualshot_count, translate_count):
        print(
            f"quota_already_met total={total_count} cleanup={cleanup_count} bluetooth={bluetooth_count} "
            f"find={find_count} dualshot={dualshot_count} translate={translate_count} target_total={TARGET_DAILY_TOTAL}"
        )
        print("watchdog rerun_count=0 failed=0 dry_run=" + str(args.dry_run).lower())
        return 0

    settle_seconds = 0 if args.dry_run else max(0, args.settle_seconds)
    settle_poll_seconds = max(1, args.settle_poll_seconds)
    if settle_seconds:
        print(
            f"quota_missing_wait total={total_count} cleanup={cleanup_count} bluetooth={bluetooth_count} "
            f"find={find_count} dualshot={dualshot_count} translate={translate_count} "
            f"settle_seconds={settle_seconds}"
        )
        deadline = time.monotonic() + settle_seconds
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            time.sleep(min(settle_poll_seconds, max(0.0, remaining)))
            content_ref = resolve_content_ref(repo_root, git_command, args.git_remote, args.git_branch)
            posts = list_same_day_posts(repo_root, git_command, content_ref, target_day)
            total_count = len(posts)
            cleanup_count = count_cleanup_posts(posts)
            bluetooth_count = count_bluetooth_posts(posts)
            find_count = count_find_posts(posts)
            dualshot_count = count_dualshot_posts(posts)
            translate_count = count_translate_posts(posts)
            if quota_met(total_count, cleanup_count, bluetooth_count, find_count, dualshot_count, translate_count):
                print(
                    f"quota_reached_after_wait total={total_count} cleanup={cleanup_count} "
                    f"bluetooth={bluetooth_count} find={find_count} dualshot={dualshot_count} "
                    f"translate={translate_count} target_total={TARGET_DAILY_TOTAL}"
                )
                print("watchdog rerun_count=0 failed=0 dry_run=false")
                return 0

    failed: list[str] = []
    rerun_count = 0
    for task in BLOG_TASKS:
        last_run, last_result = query_task_info(task.task_name)
        needs_rerun = last_run != target_day or last_result not in {0}
        if not needs_rerun:
            print(f"ok task={task.task_name} date={target_day.isoformat()} result={last_result}")
            continue

        rerun_count += 1
        print(
            f"rerun task={task.task_name} lane={task.lane} offset={task.slot_offset} "
            f"last_run={(last_run.isoformat() if last_run else 'missing')} last_result={last_result}"
        )
        code = run_slot(repo_root, task, target_day, args.dry_run)
        if code != 0:
            failed.append(task.task_name)
            continue
        if not args.dry_run:
            content_ref = resolve_content_ref(repo_root, git_command, args.git_remote, args.git_branch)
            try:
                previous_index_count, _ = assert_publish_integrity(
                    repo_root,
                    git_command,
                    content_ref,
                    target_day,
                    previous_index_count,
                )
            except ValueError as exc:
                failed.append(task.task_name)
                print(str(exc), file=sys.stderr)
                break

        posts = list_same_day_posts(repo_root, git_command, content_ref, target_day)
        total_count = len(posts)
        cleanup_count = count_cleanup_posts(posts)
        bluetooth_count = count_bluetooth_posts(posts)
        find_count = count_find_posts(posts)
        dualshot_count = count_dualshot_posts(posts)
        translate_count = count_translate_posts(posts)
        if quota_met(total_count, cleanup_count, bluetooth_count, find_count, dualshot_count, translate_count):
            print(
                f"quota_reached_after_rerun total={total_count} cleanup={cleanup_count} bluetooth={bluetooth_count} "
                f"find={find_count} dualshot={dualshot_count} translate={translate_count} target_total={TARGET_DAILY_TOTAL}"
            )
            break

    posts = list_same_day_posts(repo_root, git_command, content_ref, target_day)
    total_count = len(posts)
    cleanup_count = count_cleanup_posts(posts)
    bluetooth_count = count_bluetooth_posts(posts)
    find_count = count_find_posts(posts)
    dualshot_count = count_dualshot_posts(posts)
    translate_count = count_translate_posts(posts)
    print(
        f"post_count total={total_count} cleanup={cleanup_count} bluetooth={bluetooth_count} find={find_count} "
        f"dualshot={dualshot_count} translate={translate_count} target_total={TARGET_DAILY_TOTAL} "
        f"target_cleanup={TARGET_DAILY_CLEANUP} target_bluetooth={TARGET_DAILY_BLUETOOTH} "
        f"target_find={TARGET_DAILY_FIND} target_dualshot={TARGET_DAILY_DUALSHOT} "
        f"target_translate={TARGET_DAILY_TRANSLATE}"
    )

    if not args.dry_run:
        backfill_round = 0
        while not quota_met(total_count, cleanup_count, bluetooth_count, find_count, dualshot_count, translate_count):
            if cleanup_count < TARGET_DAILY_CLEANUP:
                lane = "cleanup"
            elif bluetooth_count < TARGET_DAILY_BLUETOOTH:
                lane = "protocol"
            elif find_count < TARGET_DAILY_FIND:
                lane = "find"
            elif dualshot_count < TARGET_DAILY_DUALSHOT:
                lane = "dualshot"
            else:
                lane = "translate"
            synthetic = BlogTask(
                task_name=f"watchdog-backfill-{lane}-{backfill_round}",
                lane=lane,
                slot_offset=backfill_round,
            )
            rerun_count += 1
            backfill_round += 1
            print(
                f"backfill task={synthetic.task_name} lane={lane} offset={synthetic.slot_offset} "
                f"total={total_count} cleanup={cleanup_count} bluetooth={bluetooth_count} find={find_count} "
                f"dualshot={dualshot_count} translate={translate_count}"
            )
            code = run_slot(repo_root, synthetic, target_day, False)
            if code != 0:
                failed.append(synthetic.task_name)
                break
            content_ref = resolve_content_ref(repo_root, git_command, args.git_remote, args.git_branch)
            try:
                previous_index_count, _ = assert_publish_integrity(
                    repo_root,
                    git_command,
                    content_ref,
                    target_day,
                    previous_index_count,
                )
            except ValueError as exc:
                failed.append(synthetic.task_name)
                print(str(exc), file=sys.stderr)
                break
            posts = list_same_day_posts(repo_root, git_command, content_ref, target_day)
            total_count = len(posts)
            cleanup_count = count_cleanup_posts(posts)
            bluetooth_count = count_bluetooth_posts(posts)
            find_count = count_find_posts(posts)
            dualshot_count = count_dualshot_posts(posts)
            translate_count = count_translate_posts(posts)

    print(f"watchdog rerun_count={rerun_count} failed={len(failed)} dry_run={str(args.dry_run).lower()}")
    if failed:
        print("failed_tasks=" + ",".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
