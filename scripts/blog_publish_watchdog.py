#!/usr/bin/env python3
"""Verify scheduled blog slots ran and backfill any missing ones."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


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
    BlogTask("WeiLuoGe-Translate-AI-Blog-Morning-1", "translate", 0),
    BlogTask("WeiLuoGe-Translate-AI-Blog-Morning-2", "translate", 1),
)
TARGET_DAILY_TOTAL = 6
TARGET_DAILY_BLUETOOTH = 2
TARGET_DAILY_TRANSLATE = 2
TARGET_DAILY_FIND = 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill missing scheduled blog slots after the morning run window.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--date", help="Target date in YYYY-MM-DD. Defaults to today.")
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


def list_same_day_posts(blog_dir: Path, target_day: date) -> list[Path]:
    suffix = f"-{target_day.isoformat()}.html"
    return sorted(blog_dir.glob(f"*{suffix}"))


def count_bluetooth_posts(paths: list[Path]) -> int:
    return sum(1 for path in paths if path.name.startswith("bluetooth-"))


def count_translate_posts(paths: list[Path]) -> int:
    return sum(1 for path in paths if path.name.startswith("translate-ai-"))


def count_find_posts(paths: list[Path]) -> int:
    return sum(1 for path in paths if path.name.startswith("find-ai-"))


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    target_day = parse_iso_date(args.date)
    blog_dir = repo_root / "blog"

    posts = list_same_day_posts(blog_dir, target_day)
    total_count = len(posts)
    bluetooth_count = count_bluetooth_posts(posts)
    translate_count = count_translate_posts(posts)
    find_count = count_find_posts(posts)

    if total_count >= TARGET_DAILY_TOTAL:
        print(
            f"quota_already_met total={total_count} bluetooth={bluetooth_count} "
            f"translate={translate_count} find={find_count} target_total={TARGET_DAILY_TOTAL}"
        )
        print("watchdog rerun_count=0 failed=0 dry_run=" + str(args.dry_run).lower())
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

        posts = list_same_day_posts(blog_dir, target_day)
        total_count = len(posts)
        bluetooth_count = count_bluetooth_posts(posts)
        translate_count = count_translate_posts(posts)
        find_count = count_find_posts(posts)
        if total_count >= TARGET_DAILY_TOTAL:
            print(
                f"quota_reached_after_rerun total={total_count} bluetooth={bluetooth_count} "
                f"translate={translate_count} find={find_count} target_total={TARGET_DAILY_TOTAL}"
            )
            break

    posts = list_same_day_posts(blog_dir, target_day)
    total_count = len(posts)
    bluetooth_count = count_bluetooth_posts(posts)
    translate_count = count_translate_posts(posts)
    find_count = count_find_posts(posts)
    print(
        f"post_count total={total_count} bluetooth={bluetooth_count} translate={translate_count} find={find_count} "
        f"target_total={TARGET_DAILY_TOTAL} target_bluetooth={TARGET_DAILY_BLUETOOTH} "
        f"target_translate={TARGET_DAILY_TRANSLATE} target_find={TARGET_DAILY_FIND}"
    )

    if not args.dry_run:
        backfill_round = 0
        while (
            total_count < TARGET_DAILY_TOTAL
            or bluetooth_count < TARGET_DAILY_BLUETOOTH
            or translate_count < TARGET_DAILY_TRANSLATE
            or find_count < TARGET_DAILY_FIND
        ):
            if bluetooth_count < TARGET_DAILY_BLUETOOTH:
                lane = "protocol"
            elif translate_count < TARGET_DAILY_TRANSLATE:
                lane = "translate"
            elif find_count < TARGET_DAILY_FIND:
                lane = "find"
            else:
                lane = "cleanup"
            synthetic = BlogTask(
                task_name=f"watchdog-backfill-{lane}-{backfill_round}",
                lane=lane,
                slot_offset=backfill_round,
            )
            rerun_count += 1
            backfill_round += 1
            print(
                f"backfill task={synthetic.task_name} lane={lane} offset={synthetic.slot_offset} "
                f"total={total_count} bluetooth={bluetooth_count} translate={translate_count} find={find_count}"
            )
            code = run_slot(repo_root, synthetic, target_day, False)
            if code != 0:
                failed.append(synthetic.task_name)
                break
            posts = list_same_day_posts(blog_dir, target_day)
            total_count = len(posts)
            bluetooth_count = count_bluetooth_posts(posts)
            translate_count = count_translate_posts(posts)
            find_count = count_find_posts(posts)

    print(f"watchdog rerun_count={rerun_count} failed={len(failed)} dry_run={str(args.dry_run).lower()}")
    if failed:
        print("failed_tasks=" + ",".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
