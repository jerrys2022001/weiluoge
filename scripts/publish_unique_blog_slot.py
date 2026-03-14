#!/usr/bin/env python3
"""Publish one blog slot with uniqueness enforcement and live-news fallback."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from blog_cleanup_focus_scheduler import (
    build_post_meta as build_cleanup_post_meta,
    pick_angle as pick_cleanup_angle,
    render_article_html as render_cleanup_html,
)
from blog_seo_audit import print_report, validate_generated_article
from blog_daily_scheduler import (
    BLOG_INDEX_REL,
    SITEMAP_REL,
    add_git_publish_args,
    parse_iso_date,
    publish_blog_post_to_git,
    update_blog_index,
    update_sitemap,
)
from blog_protocol_daily_scheduler import (
    ANGLES as PROTOCOL_ANGLES,
    build_post_meta as build_protocol_post_meta,
    pick_angle as pick_protocol_angle,
    render_article_html as render_protocol_html,
)
from blog_similarity import load_blog_pages, max_similarity_against_existing
from live_blog_fallback import LiveBlogCandidate, build_live_candidates
from site_tools import build_site_search_index, inject_site_tools_into_file

LIVE_REWRITE_SOFT_THRESHOLD = {
    "cleanup": 0.70,
    "protocol": 0.70,
    "updates": 0.70,
}


@dataclass(frozen=True)
class Candidate:
    lane: str
    origin: str
    identifier: str
    post: object
    html: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish one unique blog article for a scheduled slot, with live-news fallback when local topics repeat."
    )
    parser.add_argument("--lane", choices=["cleanup", "protocol", "updates"], required=True)
    parser.add_argument("--slot-offset", type=int, default=0, help="Preferred local topic offset for this slot.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--date", help="Target publish date in YYYY-MM-DD (default: today).")
    parser.add_argument("--force", action="store_true", help="Overwrite article file if it already exists.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--similarity-threshold", type=float)
    return add_git_publish_args(parser)


def default_similarity_threshold(lane: str) -> float:
    if lane == "cleanup":
        return 0.40
    return 0.50


def default_live_rewrite_threshold(lane: str) -> float:
    return LIVE_REWRITE_SOFT_THRESHOLD[lane]


def build_local_candidates(target_day: date, lane: str, slot_offset: int) -> list[Candidate]:
    candidates: list[Candidate] = []
    if lane == "cleanup":
        from blog_cleanup_focus_scheduler import ANGLES as CLEANUP_ANGLES

        total = len(CLEANUP_ANGLES)
        for step in range(total):
            offset = (slot_offset + step) % total
            angle = pick_cleanup_angle(target_day, offset=offset)
            post = build_cleanup_post_meta(target_day, angle)
            html = render_cleanup_html(target_day, angle, post)
            candidates.append(Candidate(lane=lane, origin="local", identifier=f"cleanup:{offset}", post=post, html=html))
        return candidates
    if lane == "updates":
        return candidates

    total = len(PROTOCOL_ANGLES)
    for step in range(total):
        offset = (slot_offset + step) % total
        angle = pick_protocol_angle(target_day, offset=offset)
        post = build_protocol_post_meta(target_day, angle)
        html = render_protocol_html(target_day, angle, post)
        candidates.append(Candidate(lane=lane, origin="local", identifier=f"protocol:{offset}", post=post, html=html))
    return candidates


def build_fallback_candidates(target_day: date, lane: str) -> list[Candidate]:
    items: list[Candidate] = []
    live_candidates = build_live_candidates(target_day, lane)
    for index, live in enumerate(live_candidates):
        items.append(Candidate(lane=lane, origin="live", identifier=f"{live.source_name}:{index}", post=live.post, html=live.html))
    return items


def cleanup_quota_satisfied(repo_root: Path, target_day: date) -> Candidate | None:
    blog_dir = repo_root / "blog"
    candidates = [*build_local_candidates(target_day, "cleanup", 0), *build_fallback_candidates(target_day, "cleanup")]
    for candidate in candidates:
        article_path = blog_dir / candidate.post.filename
        if article_path.exists():
            return candidate
    return None


def rank_candidates(
    candidates: list[Candidate],
    existing_pages: list[object],
    blog_dir: Path,
    force: bool,
) -> list[tuple[float, Candidate]]:
    ranked: list[tuple[float, Candidate]] = []
    for candidate in candidates:
        article_path = blog_dir / candidate.post.filename
        if article_path.exists() and not force:
            continue
        similarity = max_similarity_against_existing(candidate.html, existing_pages)
        ranked.append((similarity, candidate))
    ranked.sort(key=lambda item: (item[0], item[1].post.filename))
    return ranked


def choose_candidate(
    repo_root: Path,
    target_day: date,
    lane: str,
    slot_offset: int,
    similarity_threshold: float,
    force: bool,
) -> tuple[Candidate, float]:
    blog_dir = repo_root / "blog"
    existing_pages = load_blog_pages(blog_dir)
    local_ranked = rank_candidates(build_local_candidates(target_day, lane, slot_offset), existing_pages, blog_dir, force)
    live_ranked = rank_candidates(build_fallback_candidates(target_day, lane), existing_pages, blog_dir, force)

    strict_local = [item for item in local_ranked if item[0] < similarity_threshold]
    if strict_local:
        return strict_local[0][1], strict_local[0][0]

    strict_live = [item for item in live_ranked if item[0] < similarity_threshold]
    if strict_live:
        return strict_live[0][1], strict_live[0][0]

    live_soft_threshold = default_live_rewrite_threshold(lane)
    soft_live = [item for item in live_ranked if item[0] < live_soft_threshold]
    if soft_live:
        return Candidate(
            lane=soft_live[0][1].lane,
            origin="live-forced",
            identifier=soft_live[0][1].identifier,
            post=soft_live[0][1].post,
            html=soft_live[0][1].html,
        ), soft_live[0][0]

    if live_ranked:
        return Candidate(
            lane=live_ranked[0][1].lane,
            origin="live-forced",
            identifier=live_ranked[0][1].identifier,
            post=live_ranked[0][1].post,
            html=live_ranked[0][1].html,
        ), live_ranked[0][0]

    raise ValueError(
        f"Could not find a publishable {lane} blog candidate. "
        f"strict_threshold={similarity_threshold:.2f} live_soft_threshold={live_soft_threshold:.2f}"
    )


def run(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    blog_dir = repo_root / "blog"
    index_path = repo_root / BLOG_INDEX_REL
    sitemap_path = repo_root / SITEMAP_REL

    if not blog_dir.exists() or not index_path.exists() or not sitemap_path.exists():
        raise ValueError("Missing blog directory, blog index, or sitemap.")

    target_day = parse_iso_date(args.date)
    similarity_threshold = args.similarity_threshold
    if similarity_threshold is None:
        similarity_threshold = default_similarity_threshold(args.lane)
    if args.lane == "cleanup" and not args.force:
        existing_cleanup = cleanup_quota_satisfied(repo_root, target_day)
        if existing_cleanup is not None:
            if args.dry_run:
                print(
                    f"dry_run lane=cleanup origin=existing id=daily-quota-met "
                    f"article={blog_dir / existing_cleanup.post.filename} state=already_present"
                )
                return 0
            print(
                "done "
                "lane=cleanup "
                "origin=existing "
                "id=daily-quota-met "
                "index=unchanged "
                "sitemap=unchanged "
                "git=skipped "
                f"file={existing_cleanup.post.filename}"
            )
            return 0
    candidate, similarity = choose_candidate(
        repo_root=repo_root,
        target_day=target_day,
        lane=args.lane,
        slot_offset=args.slot_offset,
        similarity_threshold=similarity_threshold,
        force=args.force,
    )
    article_path = blog_dir / candidate.post.filename
    existed_before = article_path.exists()
    expected_canonical = f"https://velocai.net/blog/{candidate.post.filename}"
    seo_report = validate_generated_article(candidate.html, expected_canonical=expected_canonical)

    if seo_report.failed:
        print_report(seo_report)
        raise ValueError(
            f"SEO validation failed for {candidate.post.filename}. "
            f"{seo_report.summary()}"
        )

    if args.dry_run:
        state = "would_overwrite" if existed_before else "would_create"
        print_report(seo_report)
        print(
            f"dry_run lane={args.lane} origin={candidate.origin} id={candidate.identifier} "
            f"similarity={similarity:.3f} article={article_path} state={state}"
        )
        return 0

    article_path.write_text(candidate.html, encoding="utf-8")
    inject_site_tools_into_file(article_path)
    index_changed = update_blog_index(index_path, candidate.post)
    sitemap_changed = update_sitemap(sitemap_path, candidate.post)
    inject_site_tools_into_file(index_path)
    build_site_search_index(repo_root)

    git_state = "skipped"
    if args.git_commit or args.git_push:
        git_state = publish_blog_post_to_git(
            repo_root,
            candidate.post,
            remote=args.git_remote,
            branch=args.git_branch,
            push=args.git_push,
        )

    print(
        "done "
        f"lane={args.lane} "
        f"origin={candidate.origin} "
        f"id={candidate.identifier} "
        f"similarity={similarity:.3f} "
        f"seo={seo_report.summary()} "
        f"index={'updated' if index_changed else 'unchanged'} "
        f"sitemap={'updated' if sitemap_changed else 'unchanged'} "
        f"git={git_state} "
        f"file={candidate.post.filename}"
    )
    return 0


def main() -> int:
    parser = parse_args()
    args = parser.parse_args()
    try:
        return run(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
