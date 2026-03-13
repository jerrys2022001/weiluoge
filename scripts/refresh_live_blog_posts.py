#!/usr/bin/env python3
"""Refresh existing live fallback blog posts to the current template."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from blog_daily_scheduler import update_blog_index, update_sitemap
from home_brief_daily_scheduler import BRIEF_SOURCES, FeedItem, fetch_bytes, parse_feed_items
from live_blog_fallback import build_candidate_from_item
from site_tools import build_site_search_index, inject_site_tools_into_file


PREFIX_TO_SLUG = {
    "apple-feature-performance-commentary-": "apple",
    "ai-technology-outlook-": "ai",
    "bluetooth-industry-update-": "bluetooth",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh live fallback blog posts to the latest HTML template.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--date", required=True, help="Target publish date in YYYY-MM-DD.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def source_slug_for_name(filename: str) -> str | None:
    for prefix, source_slug in PREFIX_TO_SLUG.items():
        if filename.startswith(prefix):
            return source_slug
    return None


def parse_source_name(html: str) -> str:
    match = re.search(r"Source:\s*([^<]+)</p>", html)
    if not match:
        raise ValueError("Cannot find source name in live blog file.")
    return match.group(1).strip()


def parse_source_link(html: str) -> str:
    match = re.search(r'<section class="sources".*?<a href="([^"]+)"', html, re.DOTALL)
    if not match:
        match = re.search(r'<section class="panel">\s*<h2>Source Attribution</h2>\s*<p><a href="([^"]+)"', html, re.DOTALL)
    if not match:
        raise ValueError("Cannot find source link in live blog file.")
    return match.group(1).strip()


def parse_page_title(html: str) -> str:
    match = re.search(r"<title>(.*?)\s*\|", html, re.DOTALL)
    if not match:
        raise ValueError("Cannot find title in live blog file.")
    return match.group(1).strip()


def parse_meta_description(html: str) -> str:
    match = re.search(r'<meta\s+name="description"\s+content="(.*?)"\s*/?>', html, re.DOTALL)
    return match.group(1).strip() if match else ""


def find_feed_item(source_name: str, target_link: str) -> FeedItem | None:
    source = next((item for item in BRIEF_SOURCES if item.source_name == source_name), None)
    if source is None:
        return None
    try:
        items = parse_feed_items(fetch_bytes(source.feed_url))
    except Exception:
        return None
    for item in items:
        if item.link == target_link:
            return item
    return None


def fallback_feed_item(title: str, link: str, summary: str) -> FeedItem:
    return FeedItem(title=title, link=link, summary=summary, published_at=None, image_url="")


def refresh_posts(repo_root: Path, target_date: str, dry_run: bool) -> int:
    blog_dir = repo_root / "blog"
    index_path = blog_dir / "index.html"
    sitemap_path = repo_root / "sitemap.xml"
    files = sorted(blog_dir.glob(f"*{target_date}.html"))

    refreshed = 0
    for path in files:
        source_slug = source_slug_for_name(path.name)
        if source_slug is None:
            continue
        html = path.read_text(encoding="utf-8")
        source_name = parse_source_name(html)
        source_link = parse_source_link(html)
        current_title = parse_page_title(html)
        current_summary = parse_meta_description(html)
        item = find_feed_item(source_name, source_link)
        if item is None:
            base_title = re.sub(r":\s*(Apple Feature and Performance Commentary|AI Technology Outlook|Bluetooth Standards and Application Commentary)$", "", current_title)
            item = fallback_feed_item(base_title, source_link, current_summary)

        candidate = build_candidate_from_item(
            target_day=date.fromisoformat(target_date),
            source_slug=source_slug,
            source_name=source_name,
            item=item,
            filename=path.name,
        )

        if dry_run:
            print(f"would_refresh {path.name} -> title={candidate.post.title}")
            refreshed += 1
            continue

        path.write_text(candidate.html, encoding="utf-8")
        inject_site_tools_into_file(path)
        update_blog_index(index_path, candidate.post)
        update_sitemap(sitemap_path, candidate.post)
        refreshed += 1

    if not dry_run:
        inject_site_tools_into_file(index_path)
        build_site_search_index(repo_root)
    print(f"refreshed={refreshed}")
    return 0


def main() -> int:
    args = parse_args()
    try:
        return refresh_posts(args.repo_root.resolve(), args.date, args.dry_run)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
