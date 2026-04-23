#!/usr/bin/env python3
"""Catch up missed morning publish tasks after a late user logon."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date, datetime, time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Catch up morning blog and homepage publish tasks after logon."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--date", help="Target date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--blog-ready-after", default="08:35")
    parser.add_argument("--home-ready-after", default="08:40")
    return parser.parse_args()


def parse_iso_date(raw: str | None, fallback: date) -> date:
    if not raw:
        return fallback
    return date.fromisoformat(raw)


def parse_clock(raw: str) -> time:
    hour_text, minute_text = raw.split(":", 1)
    return time(hour=int(hour_text), minute=int(minute_text))


def append_log(repo_root: Path, message: str) -> None:
    log_dir = repo_root / "output" / "morning-catchup-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    log_path = log_dir / f"{datetime.now().astimezone().date().isoformat()}.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def run_command(label: str, args: list[str], repo_root: Path) -> int:
    completed = subprocess.run(
        args,
        cwd=repo_root,
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
    append_log(repo_root, f"{label} exit={completed.returncode}")
    return completed.returncode


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    now = datetime.now().astimezone()
    target_day = parse_iso_date(args.date, now.date())
    blog_ready_after = parse_clock(args.blog_ready_after)
    home_ready_after = parse_clock(args.home_ready_after)

    blog_allowed = target_day != now.date() or now.time() >= blog_ready_after
    home_allowed = target_day != now.date() or now.time() >= home_ready_after
    append_log(
        repo_root,
        "start "
        f"now={now.isoformat()} "
        f"target_day={target_day.isoformat()} "
        f"blog_allowed={str(blog_allowed).lower()} "
        f"home_allowed={str(home_allowed).lower()}",
    )

    if not blog_allowed and not home_allowed:
        message = (
            "skip_before_window "
            f"now={now.strftime('%H:%M:%S')} "
            f"blog_ready_after={args.blog_ready_after} "
            f"home_ready_after={args.home_ready_after}"
        )
        print(message)
        append_log(repo_root, message)
        return 0

    exit_codes: list[int] = []

    if blog_allowed:
        blog_args = [
            sys.executable,
            str(repo_root / "scripts" / "blog_publish_watchdog.py"),
            "--repo-root",
            str(repo_root),
            "--date",
            target_day.isoformat(),
        ]
        exit_codes.append(run_command("blog_watchdog", blog_args, repo_root))
    else:
        append_log(repo_root, f"blog_watchdog skipped now={now.strftime('%H:%M:%S')}")

    if home_allowed:
        home_log_dir = repo_root / "output" / "home-brief-logs"
        home_args = [
            sys.executable,
            str(repo_root / "scripts" / "home_brief_daily_scheduler.py"),
            "check",
            "--repo-root",
            str(repo_root),
            "--git-commit",
            "--git-push",
            "--log-dir",
            str(home_log_dir),
        ]
        exit_codes.append(run_command("home_brief_check", home_args, repo_root))
    else:
        append_log(repo_root, f"home_brief_check skipped now={now.strftime('%H:%M:%S')}")

    if any(code != 0 for code in exit_codes):
        append_log(repo_root, "done status=failed")
        return 1

    append_log(repo_root, "done status=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
