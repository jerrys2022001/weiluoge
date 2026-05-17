#!/usr/bin/env python3
"""Re-render recent live blog pages from their existing source metadata."""

from __future__ import annotations

import argparse
import re
from datetime import date, datetime, timezone
from pathlib import Path

from blog_daily_scheduler import BLOG_INDEX_REL, SITEMAP_REL, update_blog_index, update_sitemap
from home_brief_daily_scheduler import FeedItem
from live_blog_fallback import build_candidate_from_item, render_source_slug_for_lane
from refresh_live_blog_posts import lane_for_name, parse_source_link, parse_source_name, source_slug_for_name
from site_tools import build_site_search_index, inject_site_tools_into_file


DATE_SUFFIX_RE = re.compile(r"-(\d{4}-\d{2}-\d{2})\.html$")
SOURCE_DATE_RE = re.compile(r"Source date:\s*([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})")
MONTHS = {
    month: index
    for index, month in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
}
LIVE_MARKERS = (
    "live-source-update",
    "bluetooth-industry-update-",
    "live-device-finding-update",
    "live-translation-workflow-update",
    "mobile-codex-workflow-live-source-update",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize recent live blog pages with the current template.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--start-date", default="2026-05-04")
    parser.add_argument("--end-date", default="2026-05-14")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def date_from_filename(filename: str) -> date | None:
    match = DATE_SUFFIX_RE.search(filename)
    return date.fromisoformat(match.group(1)) if match else None


def parse_source_date(html: str, fallback: date) -> date:
    match = SOURCE_DATE_RE.search(html)
    if not match:
        return fallback
    return date(int(match.group(3)), MONTHS[match.group(1)], int(match.group(2)))


def parse_source_title(html: str, source_name: str) -> str:
    match = re.search(r'<section class="sources".*?<a href="[^"]+"[^>]*>(.*?)</a>', html, re.DOTALL)
    if match:
        label = re.sub(r"<[^>]+>", " ", match.group(1))
        label = re.sub(r"\s+", " ", label).strip()
        prefix = f"{source_name}: "
        return label[len(prefix) :] if label.startswith(prefix) else label
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
    if title_match:
        return re.sub(r"<[^>]+>", " ", title_match.group(1)).strip()
    return source_name


def parse_summary(html: str) -> str:
    hero_match = re.search(r'<div class="hero">.*?</p>\s*<p>(.*?)</p>', html, re.DOTALL)
    if hero_match:
        text = re.sub(r"<[^>]+>", " ", hero_match.group(1))
        return re.sub(r"\s+", " ", text).strip()
    meta_match = re.search(r'<meta\s+name="description"\s+content="(.*?)"', html, re.DOTALL)
    return meta_match.group(1).strip() if meta_match else ""


def source_slug_for_page(filename: str, source_name: str) -> str | None:
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


def should_normalize(path: Path) -> bool:
    return any(marker in path.name for marker in LIVE_MARKERS)


def run(repo_root: Path, start_day: date, end_day: date, dry_run: bool) -> int:
    blog_dir = repo_root / "blog"
    index_path = repo_root / BLOG_INDEX_REL
    sitemap_path = repo_root / SITEMAP_REL
    normalized = 0

    for path in sorted(blog_dir.glob("*.html")):
        publish_day = date_from_filename(path.name)
        if publish_day is None or publish_day < start_day or publish_day > end_day or not should_normalize(path):
            continue
        html = path.read_text(encoding="utf-8")
        try:
            source_name = parse_source_name(html)
            source_link = parse_source_link(html)
        except ValueError:
            continue
        source_slug = source_slug_for_page(path.name, source_name)
        if source_slug is None:
            continue
        source_day = parse_source_date(html, publish_day)
        if source_day > publish_day or (publish_day - source_day).days > 365:
            continue
        source_dt = datetime(source_day.year, source_day.month, source_day.day, tzinfo=timezone.utc)
        item = FeedItem(
            title=parse_source_title(html, source_name),
            link=source_link,
            summary=parse_summary(html),
            published_at=source_dt,
            image_url="",
        )
        candidate = build_candidate_from_item(
            publish_day,
            source_slug,
            source_name,
            item,
            lane=lane_for_name(path.name),
            filename=path.name,
        )
        if dry_run:
            print(f"would_normalize {path.name} -> {candidate.post.title}")
        else:
            path.write_text(candidate.html, encoding="utf-8")
            inject_site_tools_into_file(path)
            update_blog_index(index_path, candidate.post)
            update_sitemap(sitemap_path, candidate.post)
        normalized += 1

    if not dry_run and normalized:
        inject_site_tools_into_file(index_path)
        build_site_search_index(repo_root)

    print(f"normalized={normalized}")
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
