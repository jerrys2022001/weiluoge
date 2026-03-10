#!/usr/bin/env python3
"""Create and run daily random story posts for X (Twitter)."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from post_to_x import load_credentials, load_dotenv, send_tweet
from post_to_x_playwright import send_tweet_playwright

DEFAULT_LOG_ROOT = Path(r"D:\Operation Log")
BOT_DIR = "TwitterStoryBot"
DEFAULT_MIN_POSTS = 5
DEFAULT_MAX_POSTS = 10
DEFAULT_DAY_START = "08:00"
DEFAULT_DAY_END = "23:30"
DEFAULT_CONTENT_MODE = "classic"
DEFAULT_POST_MODE = "playwright-first"
MAX_TWEET_LEN = 280
TWEET_URL_LEN = 23
URL_RE = re.compile(r"https?://\S+")

APP_LINKS = {
    "cleanup_pro": {
        "name": "Cleanup Pro",
        "url": "https://apps.apple.com/app/ai-cleanup-kit/id6757135968",
    },
    "find_ai": {
        "name": "Find AI",
        "url": "https://apps.apple.com/app/ai-find/id6757230039",
    },
    "bluetooth_explorer": {
        "name": "Bluetooth Explorer",
        "url": "https://apps.apple.com/app/bluetooth-explorer-ai-terminal/id6757826313",
    },
}

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

CELEBRITIES = [
    "Taylor Swift",
    "Ryan Reynolds",
    "Keanu Reeves",
    "Zendaya",
    "Tim Cook",
    "Dwayne Johnson",
]

CELEBRITY_SETUPS = [
    "reading a BLE error log out loud and somehow making the whole room less tense",
    "turning a messy product bug into something that sounds weirdly survivable",
    "looking at a crash log and making it feel 20% less dramatic",
    "finding the one joke that keeps a frustrating debug session from becoming a bad day",
]

CELEBRITY_PUNCHLINES = [
    "Honestly, half of debugging is technical and half is emotional support.",
    "A good joke still fixes morale faster than one more panicked refresh.",
    "Some bugs need a debugger. Some just need better timing.",
    "That is unironically one of the healthier ways to survive product work.",
]

CELEBRITY_TAGS = [
    "#CelebrityHumor #TechTwitter",
    "#DailyLaugh #BuildInPublic",
    "#TechHumor #SocialMedia",
]

VELOCAI_APPS = [
    {
        "link_key": "find_ai",
        "name": "Find AI",
        "url": APP_LINKS["find_ai"]["url"],
        "focus": "recover nearby AirPods and Bluetooth accessories with distance radar and last-seen hints",
        "use_cases": [
            "track down AirPods before they disappear into couch-cushion history",
            "check nearby Bluetooth accessories without guessing which device is actually yours",
            "narrow down lost-device searches with calmer, faster iPhone workflows",
        ],
        "update_points": [
            "faster nearby refresh when you are tracking accessories in crowded spaces",
            "clearer last-seen hints so recovery feels less like guesswork",
            "less noisy radar feedback when multiple Bluetooth devices show up at once",
        ],
        "hashtags": "#VelocAI #FindAI",
    },
    {
        "link_key": "cleanup_pro",
        "name": "Cleanup Pro",
        "url": APP_LINKS["cleanup_pro"]["url"],
        "focus": "clear duplicate photos, large videos, and outdated contacts with safer cleanup flows",
        "use_cases": [
            "clear storage without accidentally deleting the photo you actually needed",
            "review large videos and duplicate photos with less cleanup anxiety",
            "keep contact cleanup understandable before you commit to bulk actions",
        ],
        "update_points": [
            "safer review steps before deleting duplicate photos or large videos",
            "clearer contact cleanup decisions so bulk actions feel less risky",
            "faster sorting for large storage libraries on iPhone",
        ],
        "hashtags": "#VelocAI #CleanupPro",
    },
    {
        "link_key": "bluetooth_explorer",
        "name": "Bluetooth Explorer",
        "url": APP_LINKS["bluetooth_explorer"]["url"],
        "focus": "scan devices, inspect services, test packets, and debug BLE sessions with structured logs",
        "use_cases": [
            "scan BLE devices and inspect services without bouncing between three different tools",
            "debug BLE sessions with structured logs when device behavior gets weird",
            "test packets and characteristics with a workflow that stays readable under pressure",
        ],
        "update_points": [
            "cleaner service and characteristic views during BLE checks",
            "structured logs that make repeat debugging sessions easier to compare",
            "quicker packet testing flows when you are validating a device",
        ],
        "hashtags": "#VelocAI #BluetoothExplorer",
    },
]

VELOCAI_USE_CASE_OPENERS = [
    "One small but real iPhone workflow we built for:",
    "A use case we keep seeing in normal everyday moments:",
    "This is the kind of task people want to finish without overthinking:",
]

VELOCAI_UPDATE_OPENERS = [
    "My favorite kind of product update is the boring useful kind:",
    "A version update is worth noticing when it improves this:",
    "Small release notes matter most when they remove a little daily friction:",
]

APPLE_PRODUCTS = [
    {
        "name": "AirPods Pro",
        "angle": "still one of the easiest Apple buys when somebody wants low-friction audio, quick pairing, and solid ANC",
        "hashtags": "#Apple #AirPodsPro",
        "link_key": "find_ai",
    },
    {
        "name": "iPhone Pro",
        "angle": "keeps staying in the conversation because camera, battery, and ecosystem convenience still drive daily use",
        "hashtags": "#Apple #iPhone",
        "link_key": "cleanup_pro",
    },
    {
        "name": "Apple Watch",
        "angle": "keeps winning on habit because health nudges and quick-glance utility are hard to replace once they stick",
        "hashtags": "#Apple #AppleWatch",
        "link_key": "find_ai",
    },
    {
        "name": "MacBook Air",
        "angle": "stays popular because light weight and battery life solve more real workdays than flashy specs do",
        "hashtags": "#Apple #MacBookAir",
        "link_key": "cleanup_pro",
    },
    {
        "name": "iPad Pro",
        "angle": "still gets attention whenever people want a flexible mix of media, sketching, travel, and light laptop replacement",
        "hashtags": "#Apple #iPadPro",
        "link_key": "cleanup_pro",
    },
]

APPLE_OPENERS = [
    "My Apple take today:",
    "A mildly unexciting Apple opinion:",
    "One Apple product opinion I keep coming back to:",
]

VELOCAI_USE_CASE_CLOSERS = [
    "Usually the real win is just fewer annoying steps on a busy day.",
    "That is the difference between an app sounding smart and actually being useful.",
    "Most people do not want a clever workflow. They want a calmer one.",
]

VELOCAI_UPDATE_CLOSERS = [
    "Not flashy, but exactly the sort of thing people feel after a week of real use.",
    "That kind of polish rarely trends, but it makes the app feel calmer immediately.",
    "Small quality-of-life changes usually age better than loud feature lists.",
]

APPLE_CLOSERS = [
    "Not the hottest take, just the one that keeps proving true.",
    "Sometimes the most popular Apple product is simply the least annoying one to live with.",
    "A lot of product decisions end up being less about specs and more about daily friction.",
]


@dataclass(frozen=True)
class BotPaths:
    root: Path
    plans: Path
    logs: Path
    locks: Path


def now_local() -> datetime:
    return datetime.now().astimezone()


def parse_hhmm(value: str, *, allow_2400: bool = False) -> dt_time:
    if allow_2400 and value == "24:00":
        return dt_time(0, 0)
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


def normalize_text_items(items: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = item.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        output.append(cleaned)
        seen.add(key)
    return output


def normalize_features(features: list[str]) -> list[str]:
    return normalize_text_items(features)


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


def resolve_update_topics(args: argparse.Namespace) -> list[str]:
    combined: list[str] = []

    env_topics = os.getenv("X_STORY_UPDATE_TOPICS", "").strip()
    if env_topics:
        combined.extend(part.strip() for part in env_topics.split(","))

    if getattr(args, "update_topics", None):
        combined.extend(part.strip() for part in args.update_topics.split(","))

    update_topics_file = getattr(args, "update_topics_file", None)
    if update_topics_file:
        raw = update_topics_file.read_text(encoding="utf-8").splitlines()
        combined.extend(line.strip() for line in raw if line.strip() and not line.strip().startswith("#"))

    return normalize_text_items(combined)


def feature_hashtag(feature: str) -> str:
    filtered = "".join(ch for ch in feature.title() if ch.isalnum())
    return filtered or "ProductFeature"


def link_url(link_key: str) -> str:
    return str(APP_LINKS[link_key]["url"])


def choose_link_key_for_feature(feature: str) -> str:
    lowered = feature.lower()
    if any(keyword in lowered for keyword in ["cleanup", "duplicate", "photo", "video", "storage", "contact"]):
        return "cleanup_pro"
    if any(keyword in lowered for keyword in ["find", "lost", "airpod", "watch"]):
        return "find_ai"
    if any(
        keyword in lowered
        for keyword in ["bluetooth", "ble", "radar", "scan", "device", "signal", "connect", "diagnostic", "packet"]
    ):
        return "bluetooth_explorer"
    return "cleanup_pro"


def clip_tweet(text: str) -> str:
    if tweet_length(text) <= MAX_TWEET_LEN:
        return text

    url_matches = list(URL_RE.finditer(text))
    if url_matches:
        last_url_start = url_matches[-1].start()
        prefix = text[:last_url_start].rstrip()
        suffix = text[last_url_start:].strip()
        candidate = f"{prefix}… {suffix}".strip()
        while prefix and tweet_length(candidate) > MAX_TWEET_LEN:
            prefix = prefix[:-1].rstrip()
            candidate = f"{prefix}… {suffix}".strip()
        if tweet_length(candidate) <= MAX_TWEET_LEN:
            return candidate

    return text[: MAX_TWEET_LEN - 3].rstrip() + "..."


def tweet_length(text: str) -> int:
    length = 0
    cursor = 0
    for match in URL_RE.finditer(text):
        length += len(text[cursor:match.start()])
        length += TWEET_URL_LEN
        cursor = match.end()
    length += len(text[cursor:])
    return length


def first_fitting_text(candidates: list[str]) -> str:
    for candidate in candidates:
        if tweet_length(candidate) <= MAX_TWEET_LEN:
            return candidate
    return clip_tweet(candidates[-1])


def clip_tweet(text: str) -> str:
    if tweet_length(text) <= MAX_TWEET_LEN:
        return text

    url_matches = list(URL_RE.finditer(text))
    if url_matches:
        last_url_start = url_matches[-1].start()
        prefix = text[:last_url_start].rstrip()
        suffix = text[last_url_start:].strip()
        candidate = f"{prefix}... {suffix}".strip()
        while prefix and tweet_length(candidate) > MAX_TWEET_LEN:
            prefix = prefix[:-1].rstrip()
            candidate = f"{prefix}... {suffix}".strip()
        if tweet_length(candidate) <= MAX_TWEET_LEN:
            return candidate

    return text[: MAX_TWEET_LEN - 3].rstrip() + "..."


def pick_fitting_text(candidates: list[str], rng: random.Random) -> str:
    shuffled = list(candidates)
    rng.shuffle(shuffled)
    return first_fitting_text(shuffled)


def build_classic_story(feature: str, index: int, rng: random.Random) -> str:
    role = rng.choice(ROLES)
    setup = rng.choice(SETUPS).format(feature=feature)
    punchline = rng.choice(PUNCHLINES)
    tag_line = rng.choice(TAGLINES)
    url = link_url(choose_link_key_for_feature(feature))
    feature_tag = f"#{feature_hashtag(feature)}"
    candidates = [
        f"Today in product work, {role} {setup}. {punchline} {feature_tag} {tag_line} {url}",
        f"One tiny team story: {role} {setup}. {punchline} {feature_tag} {url}",
        f"Current build-in-public mood: {role} {setup}. {punchline} {tag_line} {url}",
    ]
    return pick_fitting_text(candidates, rng)


def build_celebrity_post(rng: random.Random) -> str:
    celebrity = rng.choice(CELEBRITIES)
    setup = rng.choice(CELEBRITY_SETUPS)
    punchline = rng.choice(CELEBRITY_PUNCHLINES)
    tag_line = rng.choice(CELEBRITY_TAGS)
    url = link_url("bluetooth_explorer")
    candidates = [
        f"I have a running theory that {celebrity} would be great at {setup}. {punchline} {tag_line} {url}",
        f"Some days I think {celebrity} could walk into a product team and start {setup}. {punchline} {url}",
        f"Tiny morale hack: imagine {celebrity} {setup}. Weirdly effective. {punchline} {tag_line} {url}",
    ]
    return pick_fitting_text(candidates, rng)


def build_velocai_use_case_post(rng: random.Random) -> str:
    app = rng.choice(VELOCAI_APPS)
    opener = rng.choice(VELOCAI_USE_CASE_OPENERS)
    use_case = rng.choice(app["use_cases"])
    closer = rng.choice(VELOCAI_USE_CASE_CLOSERS)
    candidates = [
        f"{opener} {app['name']} helps you {use_case}. {closer} {app['hashtags']} {app['url']}",
        f"We built {app['name']} for the moments when you need to {use_case}. {closer} {app['url']}",
        f"{app['name']} is for the moments when you want to {use_case}. Usually the best feature is just less friction. {app['hashtags']} {app['url']}",
    ]
    return pick_fitting_text(candidates, rng)


def build_velocai_update_post(rng: random.Random, extra_topics: list[str] | None = None) -> str:
    app = rng.choice(VELOCAI_APPS)
    opener = rng.choice(VELOCAI_UPDATE_OPENERS)
    update_pool = list(app["update_points"])
    if extra_topics:
        app_keys = {app["name"].lower(), app["name"].split(":")[0].lower()}
        for topic in extra_topics:
            if ":" in topic:
                prefix, body = topic.split(":", 1)
                if prefix.strip().lower() in app_keys and body.strip():
                    update_pool.append(body.strip())
                continue
            update_pool.append(topic)
    update_point = rng.choice(update_pool)
    closer = rng.choice(VELOCAI_UPDATE_CLOSERS)
    candidates = [
        (
            f"{opener} {app['name']} gets more useful when updates bring {update_point}. "
            f"{closer} #VelocAI #AppUpdate {app['url']}"
        ),
        (
            f"We care about updates like this: {app['name']} now brings {update_point}. "
            f"{closer} {app['url']}"
        ),
        f"{app['name']} update note: {update_point}. Small fix on paper, nicer daily use in practice. #VelocAI #AppUpdate {app['url']}",
    ]
    return pick_fitting_text(candidates, rng)


def build_apple_product_post(rng: random.Random) -> str:
    product = rng.choice(APPLE_PRODUCTS)
    opener = rng.choice(APPLE_OPENERS)
    closer = rng.choice(APPLE_CLOSERS)
    url = link_url(product["link_key"])
    candidates = [
        f"{opener} {product['name']} {product['angle']}. {closer} {product['hashtags']} {url}",
        f"If someone asks me which Apple product still earns the attention, {product['name']} {product['angle']}. {closer} {url}",
        f"{product['name']} still stands out for a simple reason: it {product['angle']}. {product['hashtags']} {url}",
    ]
    return pick_fitting_text(candidates, rng)


def build_content_slots(count: int, content_mode: str, rng: random.Random) -> list[str]:
    if content_mode == "classic":
        return ["classic"] * count

    base_cycle = ["celebrity_humor", "velocai_use_case", "apple_hot", "velocai_update"]
    slots = [base_cycle[index % len(base_cycle)] for index in range(count)]
    rng.shuffle(slots)
    return slots


def build_story(
    feature: str,
    slot: str,
    index: int,
    rng: random.Random,
    update_topics: list[str] | None = None,
) -> str:
    if slot == "classic":
        return build_classic_story(feature=feature, index=index, rng=rng)
    if slot == "celebrity_humor":
        return build_celebrity_post(rng=rng)
    if slot == "velocai_use_case":
        return build_velocai_use_case_post(rng=rng)
    if slot == "velocai_update":
        return build_velocai_update_post(rng=rng, extra_topics=update_topics)
    if slot == "apple_hot":
        return build_apple_product_post(rng=rng)
    raise ValueError(f"Unsupported content slot: {slot}")


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
    if day_end == "24:00":
        end_dt = datetime.combine(day + timedelta(days=1), dt_time(0, 0), tzinfo=tz)
    else:
        end_dt = datetime.combine(day, parse_hhmm(day_end, allow_2400=True), tzinfo=tz)
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
    content_mode: str = DEFAULT_CONTENT_MODE,
    update_topics: list[str] | None = None,
) -> list[dict[str, Any]]:
    generator = rng or random.Random()
    day_token = schedule[0].strftime("%Y%m%d") if schedule else now_local().strftime("%Y%m%d")
    slots = build_content_slots(len(schedule), content_mode=content_mode, rng=generator)
    items: list[dict[str, Any]] = []
    for offset, when in enumerate(schedule, start=0):
        index = start_index + offset
        feature = generator.choice(features)
        items.append(
            {
                "id": f"{day_token}-{index:03d}",
                "scheduled_at": when.isoformat(),
                "text": build_story(
                    feature=feature,
                    slot=slots[offset],
                    index=index,
                    rng=generator,
                    update_topics=update_topics,
                ),
                "status": "pending",
                "attempts": 0,
                "posted_at": None,
                "tweet_id": None,
                "last_attempt_at": None,
                "last_error": None,
                "content_slot": slots[offset],
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
    content_mode: str,
    update_topics: list[str] | None,
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
    items = build_items(
        schedule=schedule,
        features=features,
        rng=rng,
        content_mode=content_mode,
        update_topics=update_topics,
    )
    plan = {
        "date": day.isoformat(),
        "created_at": now_local().isoformat(),
        "min_posts": min_posts,
        "max_posts": max_posts,
        "target_posts": target_posts,
        "day_start": day_start,
        "day_end": day_end,
        "content_mode": content_mode,
        "items": items,
    }
    save_json(path, plan)
    write_log(paths, f"plan_created date={day.isoformat()} target_posts={target_posts}", day)
    return plan, True


def ensure_minimum_items(
    plan: dict[str, Any],
    min_posts: int,
    features: list[str],
    content_mode: str,
    update_topics: list[str] | None,
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
    if plan["day_end"] == "24:00":
        end_dt = datetime.combine(day + timedelta(days=1), dt_time(0, 0), tzinfo=tz)
    else:
        end_dt = datetime.combine(day, parse_hhmm(plan["day_end"], allow_2400=True), tzinfo=tz)
    anchor = max(start_dt, now + timedelta(minutes=1))
    schedule = random_datetimes_between(anchor, end_dt, short, rng)
    start_index = len(items) + 1
    plan["items"].extend(
        build_items(
            schedule=schedule,
            features=features,
            start_index=start_index,
            rng=rng,
            content_mode=content_mode,
            update_topics=update_topics,
        )
    )
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


def post_methods_for_mode(post_mode: str) -> list[str]:
    mapping = {
        "playwright-first": ["playwright", "api"],
        "api-first": ["api", "playwright"],
        "playwright": ["playwright"],
        "api": ["api"],
    }
    try:
        return mapping[post_mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported post mode: {post_mode}") from exc


def format_post_exception(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        return parse_http_error(exc)
    if isinstance(exc, URLError):
        return f"Network error: {exc.reason}"
    if isinstance(exc, (RuntimeError, ValueError)):
        return str(exc)
    if isinstance(exc, subprocess.CalledProcessError):
        details = (exc.stderr or exc.stdout or "").strip()
        return details or f"Process failed with exit code {exc.returncode}"
    if isinstance(exc, FileNotFoundError):
        return str(exc)
    return f"Unexpected error: {exc}"


def send_item_via_method(
    *,
    method: str,
    text: str,
    creds: tuple[str, str, str, str] | None,
) -> dict[str, Any] | None:
    if method == "playwright":
        return send_tweet_playwright(text=text, reply_to=None, dry_run=False)
    if method == "api":
        if creds is None:
            raise ValueError("X API credentials are required for API posting.")
        api_key, api_key_secret, access_token, access_token_secret = creds
        return send_tweet(
            text=text,
            reply_to=None,
            base_url=os.getenv("X_API_BASE_URL", "https://api.x.com"),
            dry_run=False,
            api_key=api_key,
            api_key_secret=api_key_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
    raise ValueError(f"Unsupported posting method: {method}")


def send_item_with_fallback(
    *,
    text: str,
    post_mode: str,
    creds: tuple[str, str, str, str] | None,
) -> tuple[dict[str, Any] | None, str]:
    errors: list[str] = []
    for method in post_methods_for_mode(post_mode):
        try:
            return send_item_via_method(method=method, text=text, creds=creds), method
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{method}: {format_post_exception(exc)}")
    raise RuntimeError(" | ".join(errors))


def extract_post_metadata(result: dict[str, Any] | None, method: str) -> tuple[str | None, str | None]:
    if not isinstance(result, dict):
        return None, None
    if method == "api":
        tweet_id = str(result.get("data", {}).get("id") or "").strip() or None
        return tweet_id, None
    tweet_id = str(result.get("tweetId") or result.get("tweet_id") or "").strip() or None
    tweet_url = str(result.get("tweetUrl") or result.get("tweet_url") or "").strip() or None
    return tweet_id, tweet_url


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
    post_mode: str,
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
                f"dry_run item_id={item['id']} scheduled_at={item['scheduled_at']} post_mode={post_mode}",
                date.fromisoformat(plan["date"]),
            )
            continue

        try:
            result, method = send_item_with_fallback(
                text=item["text"],
                post_mode=post_mode,
                creds=creds,
            )
            tweet_id, tweet_url = extract_post_metadata(result, method)
            item["status"] = "posted"
            item["posted_at"] = now_local().isoformat()
            item["tweet_id"] = tweet_id
            if tweet_url:
                item["tweet_url"] = tweet_url
            item["post_method"] = method
            item["last_error"] = None
            posted_now += 1
            write_log(
                paths,
                f"posted item_id={item['id']} method={method} tweet_id={tweet_id or 'unknown'}",
                date.fromisoformat(plan["date"]),
            )
        except Exception as exc:  # noqa: BLE001
            item["status"] = "pending"
            item["last_error"] = format_post_exception(exc)
            write_log(
                paths,
                f"post_failed item_id={item['id']} post_mode={post_mode} error={item['last_error']}",
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
    update_topics = resolve_update_topics(args)
    plan, created = create_plan(
        day=target_day,
        min_posts=args.min_posts,
        max_posts=args.max_posts,
        day_start=args.day_start,
        day_end=args.day_end,
        features=features,
        content_mode=args.content_mode,
        update_topics=update_topics,
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
        update_topics = resolve_update_topics(args)
        plan_file = plan_path(paths, target_day)
        if not plan_file.exists():
            create_plan(
                day=target_day,
                min_posts=args.min_posts,
                max_posts=args.max_posts,
                day_start=args.day_start,
                day_end=args.day_end,
                features=features,
                content_mode=args.content_mode,
                update_topics=update_topics,
                paths=paths,
                force=False,
                reference_now=now_local(),
            )

        plan = load_json(plan_file)
        content_mode = str(plan.get("content_mode") or args.content_mode or DEFAULT_CONTENT_MODE)
        added = ensure_minimum_items(
            plan=plan,
            min_posts=args.min_posts,
            features=features,
            content_mode=content_mode,
            update_topics=update_topics,
            now=now_local(),
        )
        if added > 0:
            write_log(paths, f"plan_topped_up added={added}", target_day)

        due_items = due_pending_items(plan, now_local())
        if args.max_per_run > 0:
            due_items = due_items[: args.max_per_run]

        post_mode = getattr(args, "post_mode", DEFAULT_POST_MODE)
        creds: tuple[str, str, str, str] | None = None
        if due_items and not args.dry_run and "api" in post_methods_for_mode(post_mode):
            creds = load_credentials()

        attempted_now, posted_now = process_due_items(
            plan=plan,
            due_items=due_items,
            paths=paths,
            dry_run=args.dry_run,
            creds=creds,
            post_mode=post_mode,
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
        target.add_argument(
            "--content-mode",
            default=DEFAULT_CONTENT_MODE,
            choices=["classic", "velocai-mix"],
            help="Content template mix to use.",
        )
        target.add_argument(
            "--post-mode",
            default=DEFAULT_POST_MODE,
            choices=["playwright-first", "api-first", "playwright", "api"],
            help="Posting backend order.",
        )
        target.add_argument("--update-topics", help="Comma-separated update topic extensions.")
        target.add_argument("--update-topics-file", type=Path, help="Path to optional update-topic text file.")
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
        parse_hhmm(args.day_end, allow_2400=True)
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
