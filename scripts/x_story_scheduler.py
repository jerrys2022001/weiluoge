#!/usr/bin/env python3
"""Create and run daily random story posts for X (Twitter)."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from post_to_x import load_credentials, load_dotenv, send_tweet

DEFAULT_LOG_ROOT = Path(r"D:\Operation Log")
BOT_DIR = "TwitterStoryBot"
DEFAULT_MIN_POSTS = 10
DEFAULT_MAX_POSTS = 20
DEFAULT_DAY_START = "08:00"
DEFAULT_DAY_END = "23:30"
MAX_TWEET_LEN = 280

DEFAULT_FEATURES = [
    "smart cleanup",
    "bluetooth radar",
    "auto scan",
    "device diagnostics",
    "battery monitor",
    "quick connect",
    "duplicate remover",
    "privacy mode",
    "history export",
    "smart alerts",
    "signal strength map",
    "bulk actions",
]

ROLES = [
    "our PM",
    "the QA lead",
    "our intern",
    "a beta tester",
    "our support engineer",
    "the founder",
]

SETUPS = [
    "turned on {feature} five minutes before a demo",
    "asked {feature} to fix one tiny issue",
    "tested {feature} on a Monday with no coffee",
    "enabled {feature} and forgot to tell the rest of the team",
    "ran {feature} during a release freeze",
    "used {feature} while saying this should be easy",
]

PUNCHLINES = [
    "Now the bug report writes itself and asks for annual leave.",
    "The dashboard got so calm we thought the app was asleep.",
    "Even the error logs started using polite language.",
    "Support tickets dropped faster than our office Wi-Fi on Fridays.",
    "The app solved it so fast we had to invent a new problem.",
    "Our standup got shorter, but our jokes got longer.",
]

TAGLINES = [
    "#ProductHumor #BuildInPublic",
    "#SaaS #ProductHumor",
    "#IndieDev #ProductStory",
    "#ProductLife #TechHumor",
]


@dataclass(frozen=True)
class BotPaths:
    root: Path
    plans: Path
    logs: Path
    locks: Path


def now_local() -> datetime:
    return datetime.now().astimezone()


def parse_hhmm(value: str) -> dt_time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ValueError(f"Invalid HH:MM time: {value}") from exc


def parse_date(value: str | None) -> date:
    if value is None:
        return now_local().date()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date: {value}. Expected YYYY-MM-DD.") from exc


def ensure_directories(log_root: Path) -> BotPaths:
    root = log_root / BOT_DIR
    plans = root / "plans"
    logs = root / "logs"
    locks = root / "locks"
    for path in [root, plans, logs, locks]:
        path.mkdir(parents=True, exist_ok=True)
    return BotPaths(root=root, plans=plans, logs=logs, locks=locks)


def plan_path(paths: BotPaths, day: date) -> Path:
    return paths.plans / f"{day.isoformat()}.json"


def log_path(paths: BotPaths, day: date) -> Path:
    return paths.logs / f"{day.isoformat()}.log"


def write_log(paths: BotPaths, message: str, day: date | None = None) -> None:
    stamp = now_local().isoformat()
    target_day = day or now_local().date()
    line = f"{stamp} {message}\n"
    log_file = log_path(paths, target_day)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(line)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def load_env() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    env_files = [repo_root / ".env"]
    cwd_env = Path.cwd() / ".env"
    if cwd_env != env_files[0]:
        env_files.append(cwd_env)
    for env_file in env_files:
        load_dotenv(env_file)


def normalize_features(features: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for feature in features:
        cleaned = feature.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        output.append(cleaned)
        seen.add(key)
    return output


def resolve_features(args: argparse.Namespace) -> list[str]:
    combined: list[str] = list(DEFAULT_FEATURES)

    env_features = os.getenv("X_STORY_FEATURES", "").strip()
    if env_features:
        combined.extend(part.strip() for part in env_features.split(","))

    if args.features:
        combined.extend(part.strip() for part in args.features.split(","))

    if args.features_file:
        raw = args.features_file.read_text(encoding="utf-8").splitlines()
        combined.extend(line.strip() for line in raw if line.strip() and not line.strip().startswith("#"))

    features = normalize_features(combined)
    if not features:
        raise ValueError("No features available for content generation.")
    return features


def feature_hashtag(feature: str) -> str:
    filtered = "".join(ch for ch in feature.title() if ch.isalnum())
    return filtered or "ProductFeature"


def clip_tweet(text: str) -> str:
    if len(text) <= MAX_TWEET_LEN:
        return text
    return text[: MAX_TWEET_LEN - 3].rstrip() + "..."


def build_story(feature: str, index: int, rng: random.Random) -> str:
    role = rng.choice(ROLES)
    setup = rng.choice(SETUPS).format(feature=feature)
    punchline = rng.choice(PUNCHLINES)
    tag_line = rng.choice(TAGLINES)
    story = (
        f"Story {index}: {role} {setup}. {punchline} "
        f"#{feature_hashtag(feature)} {tag_line}"
    )
    return clip_tweet(story)


def random_datetimes_between(
    start_at: datetime,
    end_at: datetime,
    count: int,
    rng: random.Random,
) -> list[datetime]:
    if count <= 0:
        return []

    if end_at <= start_at:
        end_at = start_at + timedelta(minutes=max(1, count))

    span_seconds = int((end_at - start_at).total_seconds())
    if span_seconds + 1 >= count:
        offsets = sorted(rng.sample(range(span_seconds + 1), count))
    else:
        offsets = sorted(rng.randint(0, span_seconds) for _ in range(count))
    return [start_at + timedelta(seconds=offset) for offset in offsets]


def build_daily_schedule(
    day: date,
    count: int,
    day_start: str,
    day_end: str,
    rng: random.Random,
    reference_now: datetime | None = None,
) -> list[datetime]:
    tz = (reference_now or now_local()).tzinfo
    start_dt = datetime.combine(day, parse_hhmm(day_start), tzinfo=tz)
    end_dt = datetime.combine(day, parse_hhmm(day_end), tzinfo=tz)
    if end_dt <= start_dt:
        raise ValueError("day-end must be later than day-start.")

    if reference_now and day == reference_now.date():
        start_dt = max(start_dt, reference_now + timedelta(minutes=1))

    return random_datetimes_between(start_dt, end_dt, count, rng)


def build_items(
    schedule: list[datetime],
    features: list[str],
    start_index: int = 1,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    generator = rng or random.Random()
    day_token = schedule[0].strftime("%Y%m%d") if schedule else now_local().strftime("%Y%m%d")
    items: list[dict[str, Any]] = []
    for offset, when in enumerate(schedule, start=0):
        index = start_index + offset
        feature = generator.choice(features)
        items.append(
            {
                "id": f"{day_token}-{index:03d}",
                "scheduled_at": when.isoformat(),
                "text": build_story(feature=feature, index=index, rng=generator),
                "status": "pending",
                "attempts": 0,
                "posted_at": None,
                "tweet_id": None,
                "last_attempt_at": None,
                "last_error": None,
            }
        )
    return items


def create_plan(
    *,
    day: date,
    min_posts: int,
    max_posts: int,
    day_start: str,
    day_end: str,
    features: list[str],
    paths: BotPaths,
    force: bool = False,
    reference_now: datetime | None = None,
) -> tuple[dict[str, Any], bool]:
    if min_posts < 1:
        raise ValueError("min-posts must be at least 1.")
    if max_posts < min_posts:
        raise ValueError("max-posts must be >= min-posts.")

    path = plan_path(paths, day)
    if path.exists() and not force:
        return load_json(path), False

    rng = random.Random()
    target_posts = rng.randint(min_posts, max_posts)
    schedule = build_daily_schedule(
        day=day,
        count=target_posts,
        day_start=day_start,
        day_end=day_end,
        rng=rng,
        reference_now=reference_now,
    )
    items = build_items(schedule=schedule, features=features, rng=rng)
    plan = {
        "date": day.isoformat(),
        "created_at": now_local().isoformat(),
        "min_posts": min_posts,
        "max_posts": max_posts,
        "target_posts": target_posts,
        "day_start": day_start,
        "day_end": day_end,
        "items": items,
    }
    save_json(path, plan)
    write_log(paths, f"plan_created date={day.isoformat()} target_posts={target_posts}", day)
    return plan, True


def ensure_minimum_items(
    plan: dict[str, Any],
    min_posts: int,
    features: list[str],
    now: datetime,
) -> int:
    items = plan.get("items", [])
    short = min_posts - len(items)
    if short <= 0:
        return 0

    day = date.fromisoformat(plan["date"])
    rng = random.Random()
    tz = now.tzinfo
    start_dt = datetime.combine(day, parse_hhmm(plan["day_start"]), tzinfo=tz)
    end_dt = datetime.combine(day, parse_hhmm(plan["day_end"]), tzinfo=tz)
    anchor = max(start_dt, now + timedelta(minutes=1))
    schedule = random_datetimes_between(anchor, end_dt, short, rng)
    start_index = len(items) + 1
    plan["items"].extend(build_items(schedule=schedule, features=features, start_index=start_index, rng=rng))
    plan["target_posts"] = max(int(plan.get("target_posts", 0)), len(plan["items"]))
    return short


def parse_http_error(exc: HTTPError) -> str:
    details = ""
    try:
        details = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:
        details = ""
    if details:
        return f"HTTP {exc.code}: {details}"
    return f"HTTP {exc.code}"


def due_pending_items(plan: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in plan.get("items", []):
        if item.get("status") == "posted":
            continue
        scheduled_at = datetime.fromisoformat(item["scheduled_at"])
        if scheduled_at <= now:
            output.append(item)
    output.sort(key=lambda item: item["scheduled_at"])
    return output


def acquire_lock(lock_file: Path, stale_minutes: int = 30) -> bool:
    if lock_file.exists():
        age_seconds = now_local().timestamp() - lock_file.stat().st_mtime
        if age_seconds > stale_minutes * 60:
            lock_file.unlink(missing_ok=True)
    try:
        fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(f"{os.getpid()} {now_local().isoformat()}\n")
    return True


def release_lock(lock_file: Path) -> None:
    lock_file.unlink(missing_ok=True)


def process_due_items(
    plan: dict[str, Any],
    due_items: list[dict[str, Any]],
    paths: BotPaths,
    dry_run: bool,
    creds: tuple[str, str, str, str] | None,
) -> tuple[int, int]:
    posted_now = 0
    attempted_now = 0

    for item in due_items:
        attempted_now += 1
        item["attempts"] = int(item.get("attempts", 0)) + 1
        item["last_attempt_at"] = now_local().isoformat()

        if dry_run:
            write_log(
                paths,
                f"dry_run item_id={item['id']} scheduled_at={item['scheduled_at']}",
                date.fromisoformat(plan["date"]),
            )
            continue

        assert creds is not None
        api_key, api_key_secret, access_token, access_token_secret = creds
        try:
            result = send_tweet(
                text=item["text"],
                reply_to=None,
                base_url=os.getenv("X_API_BASE_URL", "https://api.x.com"),
                dry_run=False,
                api_key=api_key,
                api_key_secret=api_key_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
            )
            tweet_id = ""
            if isinstance(result, dict):
                tweet_id = str(result.get("data", {}).get("id", ""))
            item["status"] = "posted"
            item["posted_at"] = now_local().isoformat()
            item["tweet_id"] = tweet_id or None
            item["last_error"] = None
            posted_now += 1
            write_log(
                paths,
                f"posted item_id={item['id']} tweet_id={tweet_id or 'unknown'}",
                date.fromisoformat(plan["date"]),
            )
        except HTTPError as exc:
            item["status"] = "pending"
            item["last_error"] = parse_http_error(exc)
            write_log(
                paths,
                f"post_failed item_id={item['id']} error={item['last_error']}",
                date.fromisoformat(plan["date"]),
            )
        except URLError as exc:
            item["status"] = "pending"
            item["last_error"] = f"Network error: {exc.reason}"
            write_log(
                paths,
                f"post_failed item_id={item['id']} error={item['last_error']}",
                date.fromisoformat(plan["date"]),
            )
        except Exception as exc:  # noqa: BLE001
            item["status"] = "pending"
            item["last_error"] = f"Unexpected error: {exc}"
            write_log(
                paths,
                f"post_failed item_id={item['id']} error={item['last_error']}",
                date.fromisoformat(plan["date"]),
            )
    return attempted_now, posted_now


def summarize(plan: dict[str, Any]) -> tuple[int, int]:
    items = plan.get("items", [])
    posted = sum(1 for item in items if item.get("status") == "posted")
    pending = len(items) - posted
    return posted, pending


def cmd_plan(args: argparse.Namespace, paths: BotPaths) -> int:
    target_day = parse_date(args.date)
    features = resolve_features(args)
    plan, created = create_plan(
        day=target_day,
        min_posts=args.min_posts,
        max_posts=args.max_posts,
        day_start=args.day_start,
        day_end=args.day_end,
        features=features,
        paths=paths,
        force=args.force,
        reference_now=now_local(),
    )
    status = "created" if created else "exists"
    print(f"[{status}] plan={plan_path(paths, target_day)} total={len(plan['items'])}")
    return 0


def cmd_run(args: argparse.Namespace, paths: BotPaths) -> int:
    target_day = parse_date(args.date)
    lock_file = paths.locks / f"{target_day.isoformat()}.lock"
    if not acquire_lock(lock_file):
        write_log(paths, "run_skipped reason=lock_exists", target_day)
        print("another run is still active, skip this cycle")
        return 0

    try:
        features = resolve_features(args)
        plan_file = plan_path(paths, target_day)
        if not plan_file.exists():
            create_plan(
                day=target_day,
                min_posts=args.min_posts,
                max_posts=args.max_posts,
                day_start=args.day_start,
                day_end=args.day_end,
                features=features,
                paths=paths,
                force=False,
                reference_now=now_local(),
            )

        plan = load_json(plan_file)
        added = ensure_minimum_items(plan=plan, min_posts=args.min_posts, features=features, now=now_local())
        if added > 0:
            write_log(paths, f"plan_topped_up added={added}", target_day)

        due_items = due_pending_items(plan, now_local())
        if args.max_per_run > 0:
            due_items = due_items[: args.max_per_run]

        creds: tuple[str, str, str, str] | None = None
        if due_items and not args.dry_run:
            creds = load_credentials()

        attempted_now, posted_now = process_due_items(
            plan=plan,
            due_items=due_items,
            paths=paths,
            dry_run=args.dry_run,
            creds=creds,
        )
        save_json(plan_file, plan)

        posted_total, pending_total = summarize(plan)
        write_log(
            paths,
            "run_done attempted_now="
            f"{attempted_now} posted_now={posted_now} posted_total={posted_total} pending_total={pending_total}",
            target_day,
        )
        print(
            "run complete: "
            f"attempted_now={attempted_now} posted_now={posted_now} "
            f"posted_total={posted_total} pending_total={pending_total}"
        )
        return 0
    finally:
        release_lock(lock_file)


def parser_for_parent() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Random daily X story scheduler. Guarantees at least min-posts planned per day."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(target: argparse.ArgumentParser) -> None:
        target.add_argument("--date", help="Target date (YYYY-MM-DD). Default: today.")
        target.add_argument(
            "--log-root",
            type=Path,
            default=DEFAULT_LOG_ROOT,
            help=f"Log root path (default: {DEFAULT_LOG_ROOT}).",
        )
        target.add_argument("--min-posts", type=int, default=DEFAULT_MIN_POSTS, help="Minimum posts per day.")
        target.add_argument("--max-posts", type=int, default=DEFAULT_MAX_POSTS, help="Maximum posts per day.")
        target.add_argument("--day-start", default=DEFAULT_DAY_START, help="Schedule start time (HH:MM).")
        target.add_argument("--day-end", default=DEFAULT_DAY_END, help="Schedule end time (HH:MM).")
        target.add_argument("--features", help="Comma-separated feature list override/extension.")
        target.add_argument("--features-file", type=Path, help="Path to features text file.")

    plan_parser = sub.add_parser("plan", help="Create one random schedule plan for the day.")
    add_common(plan_parser)
    plan_parser.add_argument("--force", action="store_true", help="Recreate plan even if it already exists.")

    run_parser = sub.add_parser("run", help="Post all due items in today's plan.")
    add_common(run_parser)
    run_parser.add_argument("--dry-run", action="store_true", help="Do not send to X, only log actions.")
    run_parser.add_argument(
        "--max-per-run",
        type=int,
        default=50,
        help="Limit number of due posts handled in one run (0 means unlimited).",
    )
    return parser


def main() -> int:
    load_env()
    parser = parser_for_parent()
    args = parser.parse_args()

    try:
        parse_hhmm(args.day_start)
        parse_hhmm(args.day_end)
        if args.max_posts < args.min_posts:
            raise ValueError("max-posts must be >= min-posts.")
        if args.min_posts < 1:
            raise ValueError("min-posts must be >= 1.")
        if hasattr(args, "max_per_run") and args.max_per_run < 0:
            raise ValueError("max-per-run must be >= 0.")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    paths = ensure_directories(args.log_root)
    try:
        if args.command == "plan":
            return cmd_plan(args, paths)
        if args.command == "run":
            return cmd_run(args, paths)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Unsupported command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
