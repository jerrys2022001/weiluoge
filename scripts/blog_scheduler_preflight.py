#!/usr/bin/env python3
"""Run a lightweight health check before the morning blog window."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path


REQUIRED_MODULES = (
    "blog_daily_scheduler",
    "blog_cleanup_focus_scheduler",
    "blog_protocol_daily_scheduler",
    "blog_find_ai_daily_scheduler",
    "blog_dualshot_daily_scheduler",
    "blog_translate_ai_daily_scheduler",
    "publish_unique_blog_slot",
    "run_scheduled_blog_slot",
    "blog_publish_watchdog",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate that scheduled blog publishing modules import cleanly.")
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    scripts_dir = repo_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    failed: list[str] = []
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
            print(f"ok module={module_name}")
        except Exception as exc:  # noqa: BLE001 - we want the full preflight surface.
            print(f"fail module={module_name} error={exc}", file=sys.stderr)
            failed.append(module_name)

    if failed:
        print("failed_modules=" + ",".join(failed), file=sys.stderr)
        return 1

    print(f"preflight_ok modules={len(REQUIRED_MODULES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
