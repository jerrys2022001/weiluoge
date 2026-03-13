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
    parser.add_argument("--similarity-threshold", type=float, default=0.30)
    return add_git_publish_args(parser)


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
    live_candidates = []
    if lane == "updates":
        seen_names: set[str] = set()
        for source_lane in ("cleanup", "protocol"):
            for live in build_live_candidates(target_day, source_lane):
                if live.post.filename in seen_names:
                    continue
                seen_names.add(live.post.filename)
                live_candidates.append(live)
    else:
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
    candidate_sets = [build_local_candidates(target_day, lane, slot_offset), build_fallback_candidates(target_day, lane)]

    for group in candidate_sets:
        for candidate in group:
            article_path = blog_dir / candidate.post.filename
            if article_path.exists() and not force:
                continue
            similarity = max_similarity_against_existing(candidate.html, existing_pages)
            if similarity < similarity_threshold:
                return candidate, similarity
    raise ValueError(
        f"Could not find a unique {lane} blog candidate below similarity threshold {similarity_threshold:.2f}."
    )


def run(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    blog_dir = repo_root / "blog"
    index_path = repo_root / BLOG_INDEX_REL
    sitemap_path = repo_root / SITEMAP_REL

    if not blog_dir.exists() or not index_path.exists() or not sitemap_path.exists():
        raise ValueError("Missing blog directory, blog index, or sitemap.")

    target_day = parse_iso_date(args.date)
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
        similarity_threshold=args.similarity_threshold,
        force=args.force,
    )
    article_path = blog_dir / candidate.post.filename
    existed_before = article_path.exists()

    if args.dry_run:
        state = "would_overwrite" if existed_before else "would_create"
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
