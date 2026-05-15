#!/usr/bin/env python3
"""Replace weak cleanup live-news pages with practical cleanup guides.

Some historical cleanup slots were filled from broad live news because the
fixed topic pool had repeated too often. If there is no strong, recent cleanup
news source, a practical evergreen cleanup guide is better than forcing a weak
news hook into the article body.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

from blog_cleanup_focus_scheduler import ANGLES, build_post_meta, pick_angle, render_article_html
from blog_daily_scheduler import BLOG_INDEX_REL, SITEMAP_REL, PostMeta, update_blog_index, update_sitemap
from site_tools import build_site_search_index, inject_site_tools_into_file


CLEANUP_LIVE_PATTERN = "iphone-storage-full-cleanup-five-step-order-live-source-update-*-*.html"
DATE_SUFFIX_RE = re.compile(r"-(\d{4}-\d{2}-\d{2})\.html$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair weak cleanup live-source blog pages.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--start-date", default="2026-05-04", help="First publish date to repair.")
    parser.add_argument("--end-date", default="2026-05-14", help="Last publish date to repair.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def date_from_filename(filename: str) -> date | None:
    match = DATE_SUFFIX_RE.search(filename)
    if not match:
        return None
    return date.fromisoformat(match.group(1))


def merge_meta(original_filename: str, target_day: date) -> tuple[PostMeta, str]:
    angle = pick_angle(target_day, offset=target_day.day % len(ANGLES))
    generated = build_post_meta(target_day, angle)
    post = PostMeta(
        filename=original_filename,
        title=generated.title,
        description=generated.description,
        teaser=generated.teaser,
        topic=generated.topic,
        published_iso=generated.published_iso,
    )
    return post, render_article_html(target_day, angle, post)


def run(repo_root: Path, start_day: date, end_day: date, dry_run: bool) -> int:
    blog_dir = repo_root / "blog"
    index_path = repo_root / BLOG_INDEX_REL
    sitemap_path = repo_root / SITEMAP_REL
    repaired = 0

    for path in sorted(blog_dir.glob(CLEANUP_LIVE_PATTERN)):
        publish_day = date_from_filename(path.name)
        if publish_day is None or publish_day < start_day or publish_day > end_day:
            continue

        post, html = merge_meta(path.name, publish_day)
        if dry_run:
            print(f"would_repair {path.name} -> {post.title}")
        else:
            path.write_text(html, encoding="utf-8")
            inject_site_tools_into_file(path)
            update_blog_index(index_path, post)
            update_sitemap(sitemap_path, post)
        repaired += 1

    if not dry_run and repaired:
        inject_site_tools_into_file(index_path)
        build_site_search_index(repo_root)

    print(f"repaired={repaired}")
    return 0


def main() -> int:
    args = parse_args()
    return run(
        args.repo_root.resolve(),
        date.fromisoformat(args.start_date),
        date.fromisoformat(args.end_date),
        args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
