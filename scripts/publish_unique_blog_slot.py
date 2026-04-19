#!/usr/bin/env python3
"""Publish one blog slot with uniqueness enforcement and live-news fallback."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, timedelta
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
    post_meta_from_article_file,
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
from blog_find_ai_daily_scheduler import (
    ANGLES as FIND_ANGLES,
    build_post_meta as build_find_post_meta,
    pick_angle as pick_find_angle,
    render_article_html as render_find_html,
)
from blog_translate_ai_daily_scheduler import (
    ANGLES as TRANSLATE_ANGLES,
    build_post_meta as build_translate_post_meta,
    pick_angle as pick_translate_angle,
    render_article_html as render_translate_html,
)
from blog_dualshot_daily_scheduler import (
    ANGLES as DUALSHOT_ANGLES,
    build_post_meta as build_dualshot_post_meta,
    pick_angle as pick_dualshot_angle,
    render_article_html as render_dualshot_html,
)
from blog_similarity import load_blog_pages, max_similarity_against_existing
from live_blog_fallback import LiveBlogCandidate, build_live_candidates
from site_tools import build_site_search_index, inject_site_tools_into_file

LIVE_REWRITE_SOFT_THRESHOLD = {
    "cleanup": 0.70,
    "protocol": 0.70,
    "find": 0.70,
    "dualshot": 0.70,
    "translate": 0.70,
    "updates": 0.70,
}
MIN_DAILY_BLUETOOTH_POSTS = 2
MIN_DAILY_TRANSLATE_POSTS = 1
MIN_DAILY_FIND_POSTS = 1
MIN_DAILY_DUALSHOT_POSTS = 1
LOCK_TIMEOUT_SECONDS = 20 * 60
LOCK_POLL_SECONDS = 5
ENABLE_UPDATES_LANE_ENV = "WEILUOGE_ENABLE_UPDATES_LANE"
RECENT_REPEAT_LOOKBACK_DAYS = 7
DATE_SUFFIX_RE = re.compile(r"-\d{4}-\d{2}-\d{2}\.html$")


@dataclass(frozen=True)
class Candidate:
    lane: str
    origin: str
    identifier: str
    post: object
    html: str


class PublishLock:
    def __init__(self, repo_root: Path, timeout_seconds: int = LOCK_TIMEOUT_SECONDS, poll_seconds: int = LOCK_POLL_SECONDS):
        self._lock_path = repo_root / ".tmp" / "blog-publish.lock"
        self._timeout_seconds = timeout_seconds
        self._poll_seconds = poll_seconds
        self._fd: int | None = None

    def _read_lock_metadata(self) -> tuple[int | None, int | None]:
        try:
            raw = self._lock_path.read_text(encoding="utf-8").strip()
        except OSError:
            return None, None
        values: dict[str, str] = {}
        for part in raw.split():
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            values[key] = value
        pid = values.get("pid")
        created = values.get("time")
        return (
            int(pid) if pid and pid.isdigit() else None,
            int(created) if created and created.isdigit() else None,
        )

    def _pid_is_running(self, pid: int | None) -> bool:
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _clear_stale_lock_if_needed(self) -> bool:
        pid, created_at = self._read_lock_metadata()
        lock_age = time.time() - created_at if created_at is not None else None
        stale_by_pid = pid is None or not self._pid_is_running(pid)
        stale_by_age = lock_age is not None and lock_age > self._timeout_seconds
        if not stale_by_pid and not stale_by_age:
            return False
        try:
            self._lock_path.unlink()
        except FileNotFoundError:
            return True
        except OSError:
            return False
        return True

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
                if self._clear_stale_lock_if_needed():
                    continue
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
    parser.add_argument("--lane", choices=["cleanup", "protocol", "find", "dualshot", "translate", "updates"], required=True)
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
    if lane == "translate":
        total = len(TRANSLATE_ANGLES)
        for step in range(total):
            offset = (slot_offset + step) % total
            angle = pick_translate_angle(target_day, offset=offset)
            post = build_translate_post_meta(target_day, angle)
            html = render_translate_html(target_day, angle, post)
            candidates.append(Candidate(lane=lane, origin="local", identifier=f"translate:{offset}", post=post, html=html))
        return candidates
    if lane == "dualshot":
        total = len(DUALSHOT_ANGLES)
        for step in range(total):
            offset = (slot_offset + step) % total
            angle = pick_dualshot_angle(target_day, offset=offset)
            post = build_dualshot_post_meta(target_day, angle)
            html = render_dualshot_html(target_day, angle, post)
            candidates.append(Candidate(lane=lane, origin="local", identifier=f"dualshot:{offset}", post=post, html=html))
        return candidates
    if lane == "find":
        total = len(FIND_ANGLES)
        for step in range(total):
            offset = (slot_offset + step) % total
            angle = pick_find_angle(target_day, offset=offset)
            post = build_find_post_meta(target_day, angle)
            html = render_find_html(target_day, angle, post)
            candidates.append(Candidate(lane=lane, origin="local", identifier=f"find:{offset}", post=post, html=html))
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
    if lane in {"cleanup", "translate", "find", "dualshot"}:
        return items
    live_candidates = build_live_candidates(target_day, lane)
    if live_candidates:
        rotate = slot_offset % len(live_candidates)
        live_candidates = live_candidates[rotate:] + live_candidates[:rotate]
    for index, live in enumerate(live_candidates):
        items.append(Candidate(lane=lane, origin="live", identifier=f"{live.source_name}:{index}", post=live.post, html=live.html))
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


def is_translate_candidate(candidate: Candidate) -> bool:
    return candidate.post.filename.startswith("translate-ai-")


def is_find_candidate(candidate: Candidate) -> bool:
    return candidate.post.filename.startswith("find-ai-")


def list_same_day_prefixed_posts(blog_dir: Path, target_day: date, prefix: str) -> list[Path]:
    suffix = f"-{target_day.isoformat()}.html"
    return sorted(path for path in blog_dir.glob(f"*{suffix}") if path.name.startswith(prefix))


def count_same_day_bluetooth_posts(blog_dir: Path, target_day: date) -> int:
    return len(list_same_day_prefixed_posts(blog_dir, target_day, "bluetooth-"))


def count_same_day_translate_posts(blog_dir: Path, target_day: date) -> int:
    return len(list_same_day_prefixed_posts(blog_dir, target_day, "translate-ai-"))


def count_same_day_find_posts(blog_dir: Path, target_day: date) -> int:
    return len(list_same_day_prefixed_posts(blog_dir, target_day, "find-ai-"))


def count_same_day_dualshot_posts(blog_dir: Path, target_day: date) -> int:
    return len(list_same_day_prefixed_posts(blog_dir, target_day, "dualshot-camera-"))


def existing_daily_quota_file(repo_root: Path, target_day: date, lane: str) -> str | None:
    blog_dir = repo_root / "blog"
    if lane == "cleanup":
        existing_cleanup = cleanup_quota_satisfied(repo_root, target_day)
        if existing_cleanup is not None:
            return existing_cleanup.post.filename
        return None

    prefix_targets = {
        "protocol": ("bluetooth-", MIN_DAILY_BLUETOOTH_POSTS),
        "translate": ("translate-ai-", MIN_DAILY_TRANSLATE_POSTS),
        "find": ("find-ai-", MIN_DAILY_FIND_POSTS),
        "dualshot": ("dualshot-camera-", MIN_DAILY_DUALSHOT_POSTS),
    }
    config = prefix_targets.get(lane)
    if config is None:
        return None
    prefix, target_count = config
    matches = list_same_day_prefixed_posts(blog_dir, target_day, prefix)
    if len(matches) >= target_count:
        return matches[0].name
    return None


def evaluate_candidates(
    candidates: list[Candidate],
    existing_pages: list[object],
    blog_dir: Path,
    force: bool,
) -> list[tuple[float, Candidate]]:
    evaluated: list[tuple[float, Candidate]] = []
    for candidate in candidates:
        article_path = blog_dir / candidate.post.filename
        if article_path.exists() and not force:
            continue
        similarity = max_similarity_against_existing(candidate.html, existing_pages)
        evaluated.append((similarity, candidate))
    evaluated.sort(key=lambda item: item[0])
    return evaluated


def topic_stem_from_filename(filename: str) -> str:
    return DATE_SUFFIX_RE.sub("", filename)


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def collect_recent_repeat_keys(
    blog_dir: Path,
    target_day: date,
    lookback_days: int = RECENT_REPEAT_LOOKBACK_DAYS,
) -> set[str]:
    keys: set[str] = set()
    for days_back in range(1, lookback_days + 1):
        day = target_day - timedelta(days=days_back)
        suffix = f"-{day.isoformat()}.html"
        for path in blog_dir.glob(f"*{suffix}"):
            keys.add(f"stem:{topic_stem_from_filename(path.name)}")
            try:
                meta = post_meta_from_article_file(path)
            except ValueError:
                continue
            if meta.title:
                keys.add(f"title:{normalize_title(meta.title)}")
    return keys


def candidate_repeats_recent_topic(candidate: Candidate, recent_keys: set[str]) -> bool:
    stem_key = f"stem:{topic_stem_from_filename(candidate.post.filename)}"
    if stem_key in recent_keys:
        return True
    title = getattr(candidate.post, "title", "")
    if title and f"title:{normalize_title(title)}" in recent_keys:
        return True
    return False


def split_recent_repeats(
    ranked: list[tuple[float, Candidate]],
    recent_keys: set[str],
) -> tuple[list[tuple[float, Candidate]], list[tuple[float, Candidate]]]:
    fresh: list[tuple[float, Candidate]] = []
    repeated: list[tuple[float, Candidate]] = []
    for item in ranked:
        if candidate_repeats_recent_topic(item[1], recent_keys):
            repeated.append(item)
        else:
            fresh.append(item)
    return fresh, repeated


def first_local_candidate_below_threshold(
    ranked: list[tuple[float, Candidate]],
    similarity_threshold: float,
) -> tuple[Candidate, float] | None:
    for similarity, candidate in ranked:
        if similarity < similarity_threshold:
            return candidate, similarity
    return None


def choose_from_ranked_candidates(
    *,
    lane: str,
    blog_dir: Path,
    target_day: date,
    similarity_threshold: float,
    local_ranked: list[tuple[float, Candidate]],
    live_ranked: list[tuple[float, Candidate]],
) -> tuple[Candidate, float] | None:
    bluetooth_quota_open = lane == "updates" and count_same_day_bluetooth_posts(blog_dir, target_day) < MIN_DAILY_BLUETOOTH_POSTS
    preferred_live_ranked = [item for item in live_ranked if is_bluetooth_candidate(item[1])] if bluetooth_quota_open else live_ranked
    fallback_live_ranked = live_ranked if preferred_live_ranked else []

    if lane in {"translate", "find", "dualshot"}:
        for similarity, candidate in local_ranked:
            if similarity < similarity_threshold:
                return candidate, similarity
        for similarity, candidate in local_ranked:
            return candidate, similarity
        return None

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

    for similarity, candidate in preferred_live_ranked:
        return Candidate(
            lane=candidate.lane,
            origin="live-forced",
            identifier=candidate.identifier,
            post=candidate.post,
            html=candidate.html,
        ), similarity

    for similarity, candidate in fallback_live_ranked:
        return Candidate(
            lane=candidate.lane,
            origin="live-forced",
            identifier=candidate.identifier,
            post=candidate.post,
            html=candidate.html,
        ), similarity

    for similarity, candidate in local_ranked:
        return Candidate(
            lane=candidate.lane,
            origin="local-forced",
            identifier=candidate.identifier,
            post=candidate.post,
            html=candidate.html,
        ), similarity

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
    recent_repeat_keys = collect_recent_repeat_keys(blog_dir, target_day)
    local_ranked = evaluate_candidates(build_local_candidates(target_day, lane, slot_offset), existing_pages, blog_dir, force)
    fresh_local_ranked, repeated_local_ranked = split_recent_repeats(local_ranked, recent_repeat_keys)

    early_local_choice = first_local_candidate_below_threshold(fresh_local_ranked, similarity_threshold)
    if early_local_choice is not None:
        return early_local_choice

    live_ranked = evaluate_candidates(build_fallback_candidates(target_day, lane, slot_offset), existing_pages, blog_dir, force)
    fresh_live_ranked, repeated_live_ranked = split_recent_repeats(live_ranked, recent_repeat_keys)

    chosen = choose_from_ranked_candidates(
        lane=lane,
        blog_dir=blog_dir,
        target_day=target_day,
        similarity_threshold=similarity_threshold,
        local_ranked=fresh_local_ranked,
        live_ranked=fresh_live_ranked,
    )
    if chosen is not None:
        return chosen

    chosen = choose_from_ranked_candidates(
        lane=lane,
        blog_dir=blog_dir,
        target_day=target_day,
        similarity_threshold=similarity_threshold,
        local_ranked=repeated_local_ranked,
        live_ranked=repeated_live_ranked,
    )
    if chosen is not None:
        return chosen

    live_soft_threshold = default_live_rewrite_threshold(lane)
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

    with PublishLock(repo_root):
        if args.lane == "updates" and os.environ.get(ENABLE_UPDATES_LANE_ENV) != "1":
            print(
                "done "
                "lane=updates "
                "origin=disabled "
                "id=legacy-scheduled-updates-disabled "
                "index=unchanged "
                "sitemap=unchanged "
                "git=skipped "
                f"env={ENABLE_UPDATES_LANE_ENV}"
            )
            return 0
        if not args.force:
            existing_file = existing_daily_quota_file(repo_root, target_day, args.lane)
            if existing_file is not None:
                if args.dry_run:
                    print(
                        f"dry_run lane={args.lane} origin=existing id=daily-quota-met "
                        f"article={blog_dir / existing_file} state=already_present"
                    )
                    return 0
                print(
                    "done "
                    f"lane={args.lane} "
                    "origin=existing "
                    "id=daily-quota-met "
                    "index=unchanged "
                    "sitemap=unchanged "
                    "git=skipped "
                    f"file={existing_file}"
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
