#!/usr/bin/env python3
"""Refresh historical generated blog posts with the latest templates."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from blog_cleanup_focus_scheduler import ANGLES as CLEANUP_ANGLES
from blog_cleanup_focus_scheduler import build_post_meta as build_cleanup_post_meta
from blog_cleanup_focus_scheduler import render_article_html as render_cleanup_html
from blog_daily_scheduler import BLOG_INDEX_REL, SITEMAP_REL, parse_iso_date, update_blog_index, update_sitemap
from blog_daily_scheduler import ANGLES as DAILY_ANGLES
from blog_daily_scheduler import build_post_meta as build_daily_post_meta
from blog_daily_scheduler import render_article_html as render_daily_html
from blog_protocol_daily_scheduler import ANGLES as PROTOCOL_ANGLES
from blog_protocol_daily_scheduler import build_post_meta as build_protocol_post_meta
from blog_protocol_daily_scheduler import render_article_html as render_protocol_html
from blog_seo_audit import validate_generated_article
from site_tools import build_site_search_index, inject_site_tools_into_file


@dataclass(frozen=True)
class TemplateRenderer:
    lane: str
    build_post_meta: object
    render_html: object


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh historical generated blog posts using the latest templates.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def slug_date_from_name(filename: str) -> tuple[str, date] | None:
    if not filename.endswith(".html"):
        return None
    stem = filename[:-5]
    parts = stem.rsplit("-", 3)
    if len(parts) != 4:
        return None
    slug = parts[0]
    iso = "-".join(parts[1:])
    try:
        return slug, parse_iso_date(iso)
    except ValueError:
        return None


def build_renderers() -> dict[str, TemplateRenderer]:
    renderers: dict[str, TemplateRenderer] = {}
    for angle in CLEANUP_ANGLES:
        renderers[angle.slug_prefix] = TemplateRenderer(
            lane="cleanup",
            build_post_meta=build_cleanup_post_meta,
            render_html=render_cleanup_html,
        )
    for angle in PROTOCOL_ANGLES:
        renderers[angle.slug_prefix] = TemplateRenderer(
            lane="protocol",
            build_post_meta=build_protocol_post_meta,
            render_html=render_protocol_html,
        )
    for angle in DAILY_ANGLES:
        renderers[angle.slug_prefix] = TemplateRenderer(
            lane="daily",
            build_post_meta=build_daily_post_meta,
            render_html=render_daily_html,
        )
    return renderers


def refresh(repo_root: Path, dry_run: bool) -> int:
    blog_dir = repo_root / "blog"
    index_path = repo_root / BLOG_INDEX_REL
    sitemap_path = repo_root / SITEMAP_REL
    renderers = build_renderers()

    refreshed = 0
    audited = 0
    lane_counter: Counter[str] = Counter()
    warnings: list[str] = []

    for path in sorted(blog_dir.glob("*.html")):
        if path.name == "index.html":
            continue
        parsed = slug_date_from_name(path.name)
        if parsed is None:
            continue
        slug, publish_day = parsed
        renderer = renderers.get(slug)
        if renderer is None:
            continue

        post = renderer.build_post_meta(publish_day, next(angle for angle in (
            CLEANUP_ANGLES if renderer.lane == "cleanup" else
            PROTOCOL_ANGLES if renderer.lane == "protocol" else
            DAILY_ANGLES
        ) if angle.slug_prefix == slug))
        html = renderer.render_html(publish_day, next(angle for angle in (
            CLEANUP_ANGLES if renderer.lane == "cleanup" else
            PROTOCOL_ANGLES if renderer.lane == "protocol" else
            DAILY_ANGLES
        ) if angle.slug_prefix == slug), post)

        report = validate_generated_article(html, expected_canonical=f"https://velocai.net/blog/{post.filename}")
        audited += 1
        if report.failed:
            warnings.append(f"{path.name}: SEO failed ({report.summary()})")
            continue

        original = path.read_text(encoding="utf-8")
        if original == html:
            continue

        lane_counter[renderer.lane] += 1
        refreshed += 1

        if dry_run:
            continue

        path.write_text(html, encoding="utf-8")
        inject_site_tools_into_file(path)
        update_blog_index(index_path, post)
        update_sitemap(sitemap_path, post)

    if not dry_run and refreshed:
        inject_site_tools_into_file(index_path)
        build_site_search_index(repo_root)

    print(
        "done "
        f"refreshed={refreshed} "
        f"audited={audited} "
        f"cleanup={lane_counter['cleanup']} "
        f"protocol={lane_counter['protocol']} "
        f"daily={lane_counter['daily']} "
        f"dry_run={str(dry_run).lower()}"
    )
    for item in warnings:
        print(f"warn {item}")
    return 0


def main() -> int:
    args = parse_args()
    return refresh(args.repo_root.resolve(), args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
