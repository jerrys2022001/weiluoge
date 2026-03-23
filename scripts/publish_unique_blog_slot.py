#!/usr/bin/env python3
"""Publish one blog slot with uniqueness enforcement and live-news fallback."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
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
MAX_FORCED_SIMILARITY = 0.98
MIN_DAILY_BLUETOOTH_POSTS = 3
LOCK_TIMEOUT_SECONDS = 20 * 60
LOCK_POLL_SECONDS = 5


@dataclass(frozen=True)
class Candidate:
    lane: str
    origin: str
    identifier: str
    post: object
    html: str
    source_link: str = ""


class PublishLock:
    def __init__(self, repo_root: Path, timeout_seconds: int = LOCK_TIMEOUT_SECONDS, poll_seconds: int = LOCK_POLL_SECONDS):
        self._lock_path = repo_root / ".tmp" / "blog-publish.lock"
        self._timeout_seconds = timeout_seconds
        self._poll_seconds = poll_seconds
        self._fd: int | None = None

    def __enter__(self) -> "PublishLock":
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + self._timeout_seconds
        while True:
            try:
                self._fd = os.open(str(self._lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                payload = f"pid={os.getpid()} time={int(time.time())}\n".encode("utf-8")
                os.write(self._fd, payload)
                return self
            except FileExistsError:
                if time.time() >= deadline:
                    raise ValueError(
                        f"Timed out waiting for publish lock: {self._lock_path}"
                    )
                time.sleep(self._poll_seconds)

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            self._lock_path.unlink()
        except FileNotFoundError:
            pass


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


def build_fallback_candidates(target_day: date, lane: str, slot_offset: int) -> list[Candidate]:
    items: list[Candidate] = []
    live_candidates = build_live_candidates(target_day, lane)
    if live_candidates:
        rotate = slot_offset % len(live_candidates)
        live_candidates = live_candidates[rotate:] + live_candidates[:rotate]
    for index, live in enumerate(live_candidates):
        items.append(Candidate(lane=lane, origin="live", identifier=f"{live.source_name}:{index}", post=live.post, html=live.html, source_link=live.link))
    return items


def cleanup_quota_satisfied(repo_root: Path, target_day: date) -> Candidate | None:
    blog_dir = repo_root / "blog"
    candidates = [*build_local_candidates(target_day, "cleanup", 0), *build_fallback_candidates(target_day, "cleanup", 0)]
    for candidate in candidates:
        article_path = blog_dir / candidate.post.filename
        if article_path.exists():
            return candidate
    return None


def is_bluetooth_candidate(candidate: Candidate) -> bool:
    return candidate.post.filename.startswith("bluetooth-")


def count_same_day_bluetooth_posts(blog_dir: Path, target_day: date) -> int:
    suffix = f"-{target_day.isoformat()}.html"
    return sum(1 for path in blog_dir.glob(f"*{suffix}") if path.name.startswith("bluetooth-"))


def collect_existing_external_links(blog_dir: Path) -> set[str]:
    links: set[str] = set()
    for path in blog_dir.glob("*.html"):
        if path.name == "index.html":
            continue
        text = path.read_text(encoding="utf-8")
        for link in re.findall(r'href="(https://[^"]+)"', text):
            links.add(link)
    return links


def evaluate_candidates(
    candidates: list[Candidate],
    existing_pages: list[object],
    blog_dir: Path,
    force: bool,
) -> list[tuple[float, Candidate]]:
    existing_links = collect_existing_external_links(blog_dir)
    evaluated: list[tuple[float, Candidate]] = []
    for candidate in candidates:
        article_path = blog_dir / candidate.post.filename
        if article_path.exists() and not force:
            continue
        if candidate.source_link and candidate.source_link in existing_links and not force:
            continue
        similarity = max_similarity_against_existing(candidate.html, existing_pages)
        evaluated.append((similarity, candidate))
    return evaluated


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
    local_ranked = evaluate_candidates(build_local_candidates(target_day, lane, slot_offset), existing_pages, blog_dir, force)
    live_ranked = evaluate_candidates(build_fallback_candidates(target_day, lane, slot_offset), existing_pages, blog_dir, force)
    bluetooth_quota_open = lane == "updates" and count_same_day_bluetooth_posts(blog_dir, target_day) < MIN_DAILY_BLUETOOTH_POSTS
    preferred_live_ranked = [item for item in live_ranked if is_bluetooth_candidate(item[1])] if bluetooth_quota_open else live_ranked
    fallback_live_ranked = live_ranked if preferred_live_ranked else []

    for similarity, candidate in local_ranked:
        if similarity < similarity_threshold:
            return candidate, similarity

    for similarity, candidate in preferred_live_ranked:
        if similarity < similarity_threshold:
            return candidate, similarity
    if preferred_live_ranked is not live_ranked:
        for similarity, candidate in fallback_live_ranked:
            if similarity < similarity_threshold:
                return candidate, similarity

    live_soft_threshold = default_live_rewrite_threshold(lane)
    for similarity, candidate in preferred_live_ranked:
        if similarity < live_soft_threshold:
            return Candidate(
                lane=candidate.lane,
                origin="live-forced",
                identifier=candidate.identifier,
                post=candidate.post,
                html=candidate.html,
            ), similarity
    if preferred_live_ranked is not live_ranked:
        for similarity, candidate in fallback_live_ranked:
            if similarity < live_soft_threshold:
                return Candidate(
                    lane=candidate.lane,
                    origin="live-forced",
                    identifier=candidate.identifier,
                    post=candidate.post,
                    html=candidate.html,
                ), similarity

    if preferred_live_ranked:
        similarity, candidate = preferred_live_ranked[0]
        if similarity < MAX_FORCED_SIMILARITY:
            return Candidate(
                lane=candidate.lane,
                origin="live-forced",
                identifier=candidate.identifier,
                post=candidate.post,
                html=candidate.html,
            ), similarity

    if fallback_live_ranked:
        similarity, candidate = fallback_live_ranked[0]
        if similarity < MAX_FORCED_SIMILARITY:
            return Candidate(
                lane=candidate.lane,
                origin="live-forced",
                identifier=candidate.identifier,
                post=candidate.post,
                html=candidate.html,
            ), similarity

    raise ValueError(
        f"Could not find a publishable {lane} blog candidate. "
        f"strict_threshold={similarity_threshold:.2f} live_soft_threshold={live_soft_threshold:.2f} max_forced_similarity={MAX_FORCED_SIMILARITY:.2f}"
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

    with PublishLock(repo_root):
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
