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

PREFIX_TO_LANE = {
    "bluetooth-industry-update-": "protocol",
    "iphone-storage-full-cleanup-five-step-order-live-source-update-": "cleanup",
    "find-ai-live-device-finding-update-": "find",
    "dualshot-camera-product-demo-tutorial-guide-live-source-update-": "dualshot",
    "translate-ai-live-translation-workflow-update-": "translate",
    "octopus-mobile-codex-workflow-live-source-update-": "octopus",
}

MAX_NEWS_SOURCE_AGE_DAYS = 365


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


def lane_for_name(filename: str) -> str:
    for prefix, lane in PREFIX_TO_LANE.items():
        if filename.startswith(prefix):
            return lane
    return "updates"


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


def find_feed_item(source_name: str, target_link: str) -> FeedItem | None:
    source = next((item for item in BRIEF_SOURCES if item.source_name == source_name), None)
    if source is None:
        return None
    try:
        items = parse_feed_items(fetch_bytes(source.feed_url))
    except Exception:
        return None
    for item in items:
        if item.link == target_link and item.published_at is not None:
            return item
    return None


def source_slug_for_live_file(filename: str, source_name: str) -> str | None:
    from live_blog_fallback import render_source_slug_for_lane

    lane = lane_for_name(filename)
    if lane in {"cleanup", "dualshot", "find", "octopus", "translate"}:
        if source_name == "OpenAI News":
            return "ai"
        if "Bluetooth" in source_name or source_name in {"BeaconZone", "Blecon", "Nordic News", "Nordic GetConnected"}:
            return "bluetooth"
        if source_name in {"9to5Mac", "MacRumors", "AppleInsider", "MacStories", "Ars Technica Apple", "Cult of Mac"}:
            return "apple"
        return render_source_slug_for_lane(lane, "apple")
    return source_slug_for_name(filename)


def refresh_posts(repo_root: Path, target_date: str, dry_run: bool) -> int:
    blog_dir = repo_root / "blog"
    index_path = blog_dir / "index.html"
    sitemap_path = repo_root / "sitemap.xml"
    files = sorted(blog_dir.glob(f"*{target_date}.html"))

    refreshed = 0
    for path in files:
        html = path.read_text(encoding="utf-8")
        try:
            source_name = parse_source_name(html)
        except ValueError:
            print(f"skip {path.name} missing source metadata", file=sys.stderr)
            continue
        source_slug = source_slug_for_live_file(path.name, source_name)
        if source_slug is None:
            continue
        try:
            source_link = parse_source_link(html)
        except ValueError:
            print(f"skip {path.name} missing source link", file=sys.stderr)
            continue
        item = find_feed_item(source_name, source_link)
        if item is None:
            print(f"skip {path.name} missing recent feed item", file=sys.stderr)
            continue

        source_day = item.published_at.astimezone().date() if item.published_at else None
        if source_day is None or source_day > date.fromisoformat(target_date) or (date.fromisoformat(target_date) - source_day).days > MAX_NEWS_SOURCE_AGE_DAYS:
            print(f"skip {path.name} stale source date {source_day.isoformat() if source_day else 'unknown'}", file=sys.stderr)
            continue

        candidate = build_candidate_from_item(
            target_day=date.fromisoformat(target_date),
            source_slug=source_slug,
            source_name=source_name,
            item=item,
            lane=lane_for_name(path.name),
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
