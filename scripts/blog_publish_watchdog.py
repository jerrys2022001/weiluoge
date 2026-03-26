#!/usr/bin/env python3
"""Verify scheduled blog slots ran and backfill any missing ones."""

from __future__ import annotations

import argparse
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
    BlogTask("WeiLuoGe-Live-Update-Blog-Morning-1", "updates", 0),
    BlogTask("WeiLuoGe-Translate-AI-Blog-Morning-1", "translate", 0),
    BlogTask("WeiLuoGe-Translate-AI-Blog-Morning-2", "translate", 1),
)
TARGET_DAILY_TOTAL = 6
TARGET_DAILY_BLUETOOTH = 3
TARGET_DAILY_TRANSLATE = 2


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
    result = subprocess.run(
        ["schtasks", "/Query", "/FO", "LIST", "/V", "/TN", task_name],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return None, None

    output = result.stdout
    date_match = re.search(r"Last Run Time:\s+(\d{4})/(\d{1,2})/(\d{1,2})", output)
    last_run = None
    if date_match:
        last_run = date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))

    result_match = re.search(r"Last Result:\s+(-?\d+)", output)
    last_result = int(result_match.group(1)) if result_match else None
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


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    target_day = parse_iso_date(args.date)
    blog_dir = repo_root / "blog"

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

    posts = list_same_day_posts(blog_dir, target_day)
    total_count = len(posts)
    bluetooth_count = count_bluetooth_posts(posts)
    translate_count = count_translate_posts(posts)
    print(
        f"post_count total={total_count} bluetooth={bluetooth_count} translate={translate_count} "
        f"target_total={TARGET_DAILY_TOTAL} target_bluetooth={TARGET_DAILY_BLUETOOTH} target_translate={TARGET_DAILY_TRANSLATE}"
    )

    if not args.dry_run:
        backfill_round = 0
        while (
            total_count < TARGET_DAILY_TOTAL
            or bluetooth_count < TARGET_DAILY_BLUETOOTH
            or translate_count < TARGET_DAILY_TRANSLATE
        ):
            if bluetooth_count < TARGET_DAILY_BLUETOOTH:
                lane = "updates"
            elif translate_count < TARGET_DAILY_TRANSLATE:
                lane = "translate"
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
                f"total={total_count} bluetooth={bluetooth_count} translate={translate_count}"
            )
            code = run_slot(repo_root, synthetic, target_day, False)
            if code != 0:
                failed.append(synthetic.task_name)
                break
            posts = list_same_day_posts(blog_dir, target_day)
            total_count = len(posts)
            bluetooth_count = count_bluetooth_posts(posts)
            translate_count = count_translate_posts(posts)

    print(f"watchdog rerun_count={rerun_count} failed={len(failed)} dry_run={str(args.dry_run).lower()}")
    if failed:
        print("failed_tasks=" + ",".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
