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
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from post_to_x import load_credentials, load_dotenv, send_tweet
from post_to_x_playwright import send_tweet_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_ROOT = Path(r"D:\Operation Log")
BOT_DIR = "TwitterStoryBot"
DEFAULT_MIN_POSTS = 6
DEFAULT_MAX_POSTS = 12
DEFAULT_DAY_START = "08:00"
DEFAULT_DAY_END = "23:30"
DEFAULT_CONTENT_MODE = "classic"
DEFAULT_POST_MODE = "playwright-first"
MAX_TWEET_LEN = 280
MIN_TWEET_LEN = 245
PREFERRED_TWEET_LEN = 275
MAX_TEXT_SIMILARITY = 0.2
TWEET_URL_LEN = 23
URL_RE = re.compile(r"https?://\S+")
TEXT_SIGNATURE_RE = re.compile(r"[^a-z0-9]+")
APPLE_NEWSROOM_RSS_URL = "https://www.apple.com/newsroom/rss-feed.rss"
MACRUMORS_RSS_URL = "https://www.macrumors.com/macrumors.xml"

APP_LINKS = {
    "cleanup_pro": {
        "name": "Cleanup Pro",
        "url": "https://apps.apple.com/app/ai-cleanup-kit/id6757135968",
        "product_url": "https://velocai.net/ai-cleanup-pro/",
    },
    "find_ai": {
        "name": "Find AI",
        "url": "https://apps.apple.com/app/ai-find/id6757230039",
        "product_url": "https://velocai.net/aifind/",
    },
    "bluetooth_explorer": {
        "name": "Bluetooth Explorer",
        "url": "https://apps.apple.com/app/bluetooth-explorer-ai-terminal/id6757826313",
        "product_url": "https://velocai.net/bluetoothexplorer/",
    },
    "translate_ai": {
        "name": "Translate AI",
        "url": "https://apps.apple.com/app/id6757105258",
    },
}

MEDIA_LIBRARY = {
    "velocai_brand": [
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-04.jpg",
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-11.jpg",
        "assets/images/stock-2026-03/stock-09.jpg",
        "assets/images/stock-2026-03/stock-07.jpg",
    ],
    "find_ai": [
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-07.jpg",
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-14.jpg",
        "assets/images/stock-2026-03/stock-02.jpg",
        "assets/images/stock-2026-03/stock-07.jpg",
    ],
    "cleanup_pro": [
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-09.jpg",
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-18.jpg",
        "assets/images/stock-2026-03/stock-04.jpg",
        "assets/images/stock-2026-03/stock-08.jpg",
    ],
    "bluetooth_explorer": [
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-03.jpg",
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-16.jpg",
        "bluetoothexplorer/guid/1.jpg",
        "bluetoothexplorer/guid/2.jpg",
        "assets/images/stock-2026-03/stock-06.jpg",
    ],
    "translate_ai": [
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-05.jpg",
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-14.jpg",
        "assets/images/stock-2026-03/stock-02.jpg",
        "assets/images/stock-2026-03/stock-07.jpg",
    ],
    "apple_hot": [
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-02.jpg",
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-15.jpg",
        "assets/images/stock-2026-03/stock-07.jpg",
        "assets/images/stock-2026-03/stock-08.jpg",
        "assets/images/stock-2026-03-extra20/stock-extra-14.jpg",
    ],
    "trending_hot": [
        "assets/images/curated-people-2026-03-12-unsplash-50/people-unsplash-06.jpg",
        "assets/images/curated-people-2026-03-12-unsplash-50/people-unsplash-17.jpg",
        "assets/images/curated-tech-2026-03-12-unsplash-50/tech-unsplash-20.jpg",
        "assets/images/stock-2026-03/stock-08.jpg",
        "assets/images/stock-2026-03-extra20/stock-extra-11.jpg",
        "assets/images/stock-2026-03-extra20/stock-extra-18.jpg",
    ],
}
MEDIA_DIRECTORY_LIBRARY = {
    "velocai_brand": [
        "assets/images/curated-tech-2026-03-12-unsplash-50",
        "assets/images/pexels-tech-2026-03-14",
    ],
    "find_ai": [
        "assets/images/curated-tech-2026-03-12-unsplash-50",
        "assets/images/pexels-tech-2026-03-14",
    ],
    "cleanup_pro": [
        "assets/images/curated-tech-2026-03-12-unsplash-50",
        "assets/images/pexels-tech-2026-03-14",
    ],
    "bluetooth_explorer": [
        "assets/images/curated-tech-2026-03-12-unsplash-50",
        "assets/images/pexels-tech-2026-03-14",
    ],
    "translate_ai": [
        "assets/images/curated-tech-2026-03-12-unsplash-50",
        "assets/images/pexels-tech-2026-03-14",
    ],
    "apple_hot": [
        "assets/images/curated-tech-2026-03-12-unsplash-50",
        "assets/images/pexels-tech-2026-03-14",
    ],
    "trending_hot": [
        "assets/images/curated-people-2026-03-12-unsplash-50",
        "assets/images/curated-tech-2026-03-12-unsplash-50",
        "assets/images/pexels-people-2026-03-14",
        "assets/images/pexels-tech-2026-03-14",
    ],
}
MEDIA_SHARED_RANDOM_DIRECTORIES = [
    "assets/images/curated-tech-2026-03-12-unsplash-50",
    "assets/images/curated-people-2026-03-12-unsplash-50",
    "assets/images/pexels-tech-2026-03-14",
    "assets/images/pexels-people-2026-03-14",
]
DISALLOWED_MEDIA_NAME_PARTS = (
    "icon",
    "logo",
    "appstore",
    "screenshot",
    "screen-shot",
    "snapshot",
    "capture",
    "diagnostic",
    "diag",
)
DISALLOWED_MEDIA_PATH_PARTS = (
    "guid",
    "screenshots",
    "screenshot",
    "captures",
    "capture",
    "snapshots",
    "snapshot",
    "playwright",
)
DISALLOWED_MEDIA_EXACT_NAMES = {
    "2.png",
    "find-ai.png",
    "aicleanup.png",
    "icon-bluetooth.png",
}
MEDIA_GLOB_PATTERNS = ("*.jpg", "*.jpeg", "*.png", "*.webp")
MEDIA_MIN_BRIGHTNESS = 70.0

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
    "#BuildInPublic",
    "#TechTwitter",
    "#ProductLife",
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
    "#TechTwitter",
    "#BuildInPublic",
]

VELOCAI_APPS = [
    {
        "link_key": "find_ai",
        "name": "Find AI",
        "category": "AirPods and Bluetooth finder app",
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
        "category": "iPhone cleanup app",
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
        "category": "BLE debugging app",
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
    {
        "link_key": "translate_ai",
        "name": "Translate AI",
        "category": "AI translation app",
        "url": APP_LINKS["translate_ai"]["url"],
        "focus": "translate text, voice, and camera content with faster multilingual workflows",
        "use_cases": [
            "translate on-screen text before a travel or shopping decision slows you down",
            "handle quick multilingual chat replies without switching between three different apps",
            "turn camera text and voice snippets into a cleaner cross-language workflow on iPhone",
        ],
        "update_points": [
            "faster language detection before you commit to a translation",
            "clearer voice translation handoff for short live conversations",
            "cleaner camera-text translation results when the source image is busy",
        ],
        "hashtags": "#VelocAI #TranslateAI",
    },
]

VELOCAI_USE_CASE_OPENERS = [
    "This is the kind of thing people actually care about:",
    "A small workflow that matters more than it should:",
    "I keep coming back to this use case:",
]

VELOCAI_UPDATE_OPENERS = [
    "Honestly, the best updates are usually the least dramatic:",
    "A product update is worth noticing when it fixes this:",
    "Small release notes matter when they remove real friction:",
]

APPLE_PRODUCTS = [
    {
        "name": "iPhone 17e",
        "angle": "looks like Apple's attempt to make the mainstream iPhone choice simpler again",
        "hashtags": "#Apple #iPhone17e",
        "link_key": "find_ai",
    },
    {
        "name": "iPad Air (M4)",
        "angle": "is the kind of upgrade that keeps making the iPad line feel more practical for normal work and travel",
        "hashtags": "#Apple #iPadAir",
        "link_key": "cleanup_pro",
    },
    {
        "name": "MacBook Neo",
        "angle": "feels like Apple pushing everyday laptop value harder without turning the product into a compromise",
        "hashtags": "#Apple #MacBookNeo",
        "link_key": "cleanup_pro",
    },
    {
        "name": "AirPods Pro",
        "angle": "still stays in the conversation because convenience and habit often beat spec-sheet debates",
        "hashtags": "#Apple #AirPodsPro",
        "link_key": "find_ai",
    },
]

APPLE_OPENERS = [
    "Small Apple take:",
    "My read on this Apple move:",
    "The Apple angle that feels most real to me:",
]

VELOCAI_USE_CASE_CLOSERS = [
    "Usually the win is just fewer annoying steps on a busy day.",
    "That is what makes a tool feel useful instead of just interesting.",
    "Most people do not want clever. They want clear.",
]

APPLE_MARKET_TOPICS = [
    {
        "key": "airpods",
        "name": "AirPods",
        "keywords": ("airpods", "beats"),
        "link_key": "find_ai",
    },
    {
        "key": "iphone",
        "name": "iPhone",
        "keywords": ("iphone", "ios", "carplay"),
        "link_key": "find_ai",
    },
    {
        "key": "mac",
        "name": "Mac",
        "keywords": ("macbook", "mac mini", "mac studio", "imac", "mac pro", "macos", "mac "),
        "link_key": "cleanup_pro",
    },
    {
        "key": "ipad",
        "name": "iPad",
        "keywords": ("ipad", "apple pencil"),
        "link_key": "cleanup_pro",
    },
    {
        "key": "watch",
        "name": "Apple Watch",
        "keywords": ("apple watch", "watchos"),
        "link_key": "find_ai",
    },
    {
        "key": "vision",
        "name": "Vision",
        "keywords": ("vision", "vision pro"),
        "link_key": "bluetooth_explorer",
    },
    {
        "key": "services",
        "name": "Apple Services",
        "keywords": ("apple intelligence", "siri", "icloud", "app store", "apple music", "apple tv+"),
        "link_key": "bluetooth_explorer",
    },
]

APPLE_STYLE_ROTATION = ["mkbhd", "gurman", "ijustine", "prosser", "macrumors"]
APPLE_HEAT_BLOCKLIST = ("giveaway", "deals:", "top stories", "how to", "save on", "50 years of thinking different")

VELOCAI_USE_CASE_HOOKS = [
    "Useful products remove hesitation.",
    "Good apps earn trust fast.",
    "Small workflow wins compound.",
]

VELOCAI_UPDATE_CLOSERS = [
    "Not flashy, but exactly the kind of change people feel after a week.",
    "That kind of polish rarely trends, but people notice it fast.",
    "Small quality-of-life changes usually age better than loud feature lists.",
]

VELOCAI_UPDATE_HOOKS = [
    "Small fixes move retention.",
    "Good updates remove friction.",
    "Quiet polish matters most.",
]

APPLE_CLOSERS = [
    "That matters more than launch-day hype.",
    "Most people end up buying the product that feels easiest to live with.",
    "A lot of demand still comes down to daily friction, not spec-sheet drama.",
]

APPLE_HOOKS = [
    "Apple wins when choice feels simple.",
    "The real signal is buyer behavior.",
    "Product clarity beats launch noise.",
]

APPLE_EXPERT_ANGLES = [
    "Distribution matters more than hype.",
    "Upgrade logic matters more than specs.",
    "Buyer behavior matters more than margin.",
    "Ecosystem pull beats component drama.",
    "Positioning is the useful lens.",
    "Replacement cycles explain demand.",
]

NEWS_OPENERS = [
    "Quick tech read:",
    "What matters here:",
    "Short product take:",
]

NEWS_CLOSERS = [
    "That is usually where real product leverage shows up.",
    "That matters more than the loudest reaction posts.",
    "Execution usually matters more than the first hype cycle.",
]

NEWS_HOOKS = [
    "Shipping beats hype.",
    "Workflows beat headlines.",
    "Useful product wins.",
]

VELOCAI_USE_CASE_FACT_ANGLES = [
    "The practical question is where it removes user hesitation.",
    "The product value shows up when a messy task becomes a short workflow.",
    "The real benefit is not novelty. It is lower decision friction.",
]

VELOCAI_UPDATE_FACT_ANGLES = [
    "The factual signal is that small reductions in friction compound over repeated use.",
    "The useful detail is how this shortens a real task instead of decorating it.",
    "The retention value usually comes from less hesitation, not louder features.",
]

NEWS_FACT_ANGLES = [
    "The factual read is about shipping cadence, not announcement volume.",
    "The real signal is who is turning platform changes into daily workflows.",
    "The useful interpretation is where product behavior changes, not where attention spikes.",
]

UNIQUE_TAILS = [
    "That is the part that stands out to me.",
    "That feels like the real takeaway.",
    "That is the bit I would actually pay attention to.",
]


@dataclass(frozen=True)
class BotPaths:
    root: Path
    plans: Path
    logs: Path
    locks: Path


@dataclass(frozen=True)
class TimeWindowSpec:
    name: str
    day_start: str
    day_end: str
    min_posts: int
    max_posts: int


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


def parse_window_spec(value: str, index: int) -> TimeWindowSpec:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) != 5:
        raise ValueError(
            "Invalid --window-spec. Expected format: name|HH:MM|HH:MM|min_posts|max_posts"
        )
    name, day_start, day_end, min_posts_raw, max_posts_raw = parts
    if not name:
        name = f"window-{index}"
    parse_hhmm(day_start)
    parse_hhmm(day_end, allow_2400=True)
    try:
        min_posts = int(min_posts_raw)
        max_posts = int(max_posts_raw)
    except ValueError as exc:
        raise ValueError(
            f"Invalid --window-spec post counts for {name}. min_posts and max_posts must be integers."
        ) from exc
    if min_posts < 1:
        raise ValueError(f"Window {name} min_posts must be >= 1.")
    if max_posts < min_posts:
        raise ValueError(f"Window {name} max_posts must be >= min_posts.")
    if day_end != "24:00" and parse_hhmm(day_end, allow_2400=True) <= parse_hhmm(day_start):
        raise ValueError(f"Window {name} day_end must be later than day_start.")
    return TimeWindowSpec(
        name=name,
        day_start=day_start,
        day_end=day_end,
        min_posts=min_posts,
        max_posts=max_posts,
    )


def resolve_window_specs(args: argparse.Namespace) -> list[TimeWindowSpec]:
    raw_specs = getattr(args, "window_spec", None) or []
    if raw_specs:
        windows = [parse_window_spec(value, index + 1) for index, value in enumerate(raw_specs)]
    else:
        windows = [
            TimeWindowSpec(
                name="primary",
                day_start=args.day_start,
                day_end=args.day_end,
                min_posts=args.min_posts,
                max_posts=args.max_posts,
            )
        ]
    names_seen: set[str] = set()
    for window in windows:
        lowered = window.name.lower()
        if lowered in names_seen:
            raise ValueError(f"Duplicate window name: {window.name}")
        names_seen.add(lowered)
    windows.sort(key=lambda window: parse_hhmm(window.day_start))
    return windows


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


def normalize_text_signature(text: str) -> str:
    without_urls = URL_RE.sub(" ", text or "")
    lowered = without_urls.lower()
    normalized = TEXT_SIGNATURE_RE.sub(" ", lowered)
    return " ".join(normalized.split())


def normalize_content_key(value: str) -> str:
    lowered = (value or "").strip().lower()
    normalized = TEXT_SIGNATURE_RE.sub(" ", lowered)
    return " ".join(normalized.split())


def first_meaningful_line(text: str) -> str:
    for line in str(text or "").splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return ""


def text_similarity_key(text: str) -> set[str]:
    signature = normalize_text_signature(text)
    tokens = [token for token in signature.split() if len(token) >= 4]
    return set(tokens)


def text_similarity_ratio(left: str, right: str) -> float:
    left_tokens = text_similarity_key(left)
    right_tokens = text_similarity_key(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    base = len(left_tokens | right_tokens)
    if base == 0:
        return 0.0
    return overlap / base


def collect_posted_text_signatures(paths: BotPaths, exclude_day: date | None = None) -> set[str]:
    signatures: set[str] = set()
    for plan_file in sorted(paths.plans.glob("*.json")):
        try:
            plan_day = date.fromisoformat(plan_file.stem)
        except ValueError:
            plan_day = None
        if exclude_day is not None and plan_day == exclude_day:
            continue
        try:
            plan = load_json(plan_file)
        except Exception:
            continue
        for item in plan.get("items", []):
            if item.get("status") != "posted":
                continue
            signature = normalize_text_signature(str(item.get("text") or ""))
            if signature:
                signatures.add(signature)
    return signatures


def collect_posted_content_keys(paths: BotPaths, exclude_day: date | None = None) -> set[str]:
    keys: set[str] = set()
    for plan_file in sorted(paths.plans.glob("*.json")):
        try:
            plan_day = date.fromisoformat(plan_file.stem)
        except ValueError:
            plan_day = None
        if exclude_day is not None and plan_day == exclude_day:
            continue
        try:
            plan = load_json(plan_file)
        except Exception:
            continue
        for item in plan.get("items", []):
            if item.get("status") != "posted":
                continue
            raw_key = str(item.get("content_key") or "").strip()
            content_key = normalize_content_key(raw_key) if raw_key else ""
            if not content_key:
                content_key = normalize_text_signature(str(item.get("text") or ""))
            if content_key:
                keys.add(content_key)
    return keys


def collect_posted_text_bodies(paths: BotPaths, exclude_day: date | None = None, limit: int = 80) -> list[str]:
    texts: list[str] = []
    plan_files = sorted(paths.plans.glob("*.json"), key=lambda item: item.name, reverse=True)
    for plan_file in plan_files:
        try:
            plan_day = date.fromisoformat(plan_file.stem)
        except ValueError:
            plan_day = None
        if exclude_day is not None and plan_day == exclude_day:
            continue
        try:
            plan = load_json(plan_file)
        except Exception:
            continue
        items = [item for item in plan.get("items", []) if item.get("status") == "posted"]
        items.sort(key=lambda item: str(item.get("posted_at") or item.get("scheduled_at") or ""), reverse=True)
        for item in items:
            text = str(item.get("text") or "").strip()
            if text:
                texts.append(text)
            if len(texts) >= limit:
                return texts
    return texts


def collect_recent_openers(paths: BotPaths, exclude_day: date | None = None, limit: int = 30) -> set[str]:
    openers: set[str] = set()
    for text in collect_posted_text_bodies(paths, exclude_day=exclude_day, limit=limit):
        opener = normalize_content_key(first_meaningful_line(text))
        if opener:
            openers.add(opener)
    return openers


def collect_posted_apple_headlines(paths: BotPaths, exclude_day: date | None = None, limit: int = 60) -> set[str]:
    headlines: set[str] = set()
    plan_files = sorted(paths.plans.glob("*.json"), key=lambda item: item.name, reverse=True)
    for plan_file in plan_files:
        try:
            plan_day = date.fromisoformat(plan_file.stem)
        except ValueError:
            plan_day = None
        if exclude_day is not None and plan_day == exclude_day:
            continue
        try:
            plan = load_json(plan_file)
        except Exception:
            continue
        items = [item for item in plan.get("items", []) if item.get("status") == "posted"]
        items.sort(key=lambda item: str(item.get("posted_at") or item.get("scheduled_at") or ""), reverse=True)
        for item in items:
            headline = normalize_content_key(str(item.get("market_heat_headline") or ""))
            if headline:
                headlines.add(headline)
            if len(headlines) >= limit:
                return headlines
    return headlines


def collect_media_usage_counts(paths: BotPaths, exclude_day: date | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for plan_file in sorted(paths.plans.glob("*.json")):
        try:
            plan_day = date.fromisoformat(plan_file.stem)
        except ValueError:
            plan_day = None
        if exclude_day is not None and plan_day == exclude_day:
            continue
        try:
            plan = load_json(plan_file)
        except Exception:
            continue
        for item in plan.get("items", []):
            media_file = str(item.get("media_file") or "").strip()
            if not media_file:
                continue
            counts[media_file] = counts.get(media_file, 0) + 1
    return counts


def next_unique_text(
    *,
    build_fn: Any,
    used_signatures: set[str],
    used_content_keys: set[str] | None = None,
    recent_texts: list[str] | None = None,
    recent_openers: set[str] | None = None,
    max_attempts: int = 12,
) -> dict[str, Any]:
    last_payload: dict[str, Any] = {}
    content_keys = used_content_keys if used_content_keys is not None else set()
    recent_bodies = recent_texts if recent_texts is not None else []
    opener_pool = recent_openers if recent_openers is not None else set()
    for _ in range(max_attempts):
        payload = build_fn() or {}
        candidate = str(payload.get("text") or "").strip()
        if not candidate:
            continue
        signature = normalize_text_signature(candidate)
        raw_content_key = str(payload.get("content_key") or "").strip()
        content_key = normalize_content_key(raw_content_key) if raw_content_key else signature
        last_payload = {**payload, "text": candidate, "content_key": content_key}
        if signature and signature in used_signatures:
            continue
        if content_key and content_key in content_keys:
            continue
        opener_key = normalize_content_key(first_meaningful_line(candidate))
        if opener_key and opener_key in opener_pool:
            continue
        if any(text_similarity_ratio(candidate, recent_text) > MAX_TEXT_SIMILARITY for recent_text in recent_bodies):
            continue
        if signature:
            used_signatures.add(signature)
        if content_key:
            content_keys.add(content_key)
        if opener_key:
            opener_pool.add(opener_key)
        recent_bodies.append(candidate)
        if len(recent_bodies) > 80:
            del recent_bodies[:-80]
        return last_payload

    fallback = dict(last_payload)
    fallback_text = str(fallback.get("text") or "").strip()
    if fallback_text:
        fallback_content_key = normalize_content_key(str(fallback.get("content_key") or "")) or normalize_text_signature(fallback_text)
        urls = " ".join(match.group(0) for match in URL_RE.finditer(fallback_text))
        base_text = URL_RE.sub("", fallback_text).strip()
        for tail in UNIQUE_TAILS:
            candidate_parts = [f"{base_text} {tail}".strip()]
            if urls:
                candidate_parts.append(urls)
            candidate = clip_tweet("\n\n".join(part for part in candidate_parts if part)).strip()
            signature = normalize_text_signature(candidate)
            content_key = f"{fallback_content_key} {normalize_content_key(tail)}".strip()
            opener_key = normalize_content_key(first_meaningful_line(candidate))
            if signature and signature not in used_signatures and content_key not in content_keys:
                if opener_key and opener_key in opener_pool:
                    continue
                if any(text_similarity_ratio(candidate, recent_text) > MAX_TEXT_SIMILARITY for recent_text in recent_bodies):
                    continue
                used_signatures.add(signature)
                content_keys.add(content_key)
                fallback["text"] = candidate
                fallback["content_key"] = content_key
                if opener_key:
                    opener_pool.add(opener_key)
                recent_bodies.append(candidate)
                if len(recent_bodies) > 80:
                    del recent_bodies[:-80]
                return fallback
            if not signature and content_key not in content_keys:
                if opener_key and opener_key in opener_pool:
                    continue
                if any(text_similarity_ratio(candidate, recent_text) > MAX_TEXT_SIMILARITY for recent_text in recent_bodies):
                    continue
                content_keys.add(content_key)
                fallback["text"] = candidate
                fallback["content_key"] = content_key
                if opener_key:
                    opener_pool.add(opener_key)
                recent_bodies.append(candidate)
                if len(recent_bodies) > 80:
                    del recent_bodies[:-80]
                return fallback
        signature = normalize_text_signature(fallback_text)
        opener_key = normalize_content_key(first_meaningful_line(fallback_text))
        unique_content_key = fallback_content_key
        if not unique_content_key or unique_content_key in content_keys:
            suffix = signature[-12:] if signature else f"fallback{len(content_keys) + 1}"
            unique_content_key = f"{fallback_content_key} {suffix}".strip()
        fallback["content_key"] = unique_content_key
        if signature:
            used_signatures.add(signature)
        if unique_content_key:
            content_keys.add(unique_content_key)
        if opener_key:
            opener_pool.add(opener_key)
        recent_bodies.append(fallback_text)
        if len(recent_bodies) > 80:
            del recent_bodies[:-80]
    return fallback


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


def resolve_playwright_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    output: dict[str, Any] = {}
    if getattr(args, "playwright_chrome_path", None):
        output["chrome_path"] = args.playwright_chrome_path
    if getattr(args, "playwright_user_data_dir", None):
        output["user_data_dir"] = args.playwright_user_data_dir
    if getattr(args, "playwright_profile_directory", None):
        output["profile_directory"] = args.playwright_profile_directory
    if getattr(args, "playwright_proxy_server", None):
        output["proxy_server"] = args.playwright_proxy_server
    if getattr(args, "playwright_login_wait_seconds", None):
        output["login_wait_seconds"] = args.playwright_login_wait_seconds
    return output


def feature_hashtag(feature: str) -> str:
    filtered = "".join(ch for ch in feature.title() if ch.isalnum())
    return filtered or "ProductFeature"


def link_url(link_key: str) -> str:
    return str(APP_LINKS[link_key]["url"])


def product_page_url(link_key: str) -> str:
    return str(APP_LINKS[link_key].get("product_url") or "").strip()


def link_bundle(link_key: str) -> str:
    parts = [link_url(link_key)]
    product_url = product_page_url(link_key)
    if product_url:
        parts.append(product_url)
    return " ".join(parts)


def app_link_bundle(app: dict[str, Any]) -> str:
    link_key = str(app.get("link_key") or "").strip()
    if link_key:
        return link_bundle(link_key)
    return str(app["url"])


_APPLE_FEED_CACHE: list[dict[str, str]] | None = None
_MACRUMORS_FEED_CACHE: list[dict[str, str]] | None = None
_MEDIA_DARKNESS_CACHE: dict[str, bool] = {}


def fetch_latest_apple_entries(limit: int = 8) -> list[dict[str, str]]:
    global _APPLE_FEED_CACHE
    if _APPLE_FEED_CACHE is not None:
        return _APPLE_FEED_CACHE[:limit]

    request = urllib.request.Request(
        APPLE_NEWSROOM_RSS_URL,
        headers={"User-Agent": "weiluoge-x-story-bot/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        xml_text = response.read().decode("utf-8", errors="replace")

    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries: list[dict[str, str]] = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        updated = (entry.findtext("atom:updated", default="", namespaces=ns) or "").strip()
        link = entry.find("atom:link", ns)
        href = (link.attrib.get("href", "") if link is not None else "").strip()
        if title and href:
            entries.append({"title": title, "updated": updated, "url": href})

    _APPLE_FEED_CACHE = entries
    return entries[:limit]


def latest_apple_product_entry() -> dict[str, str] | None:
    product_keywords = ("iphone", "ipad", "macbook", "airpods", "apple watch", "mac", "vision")
    try:
        entries = fetch_latest_apple_entries(limit=12)
    except Exception:
        return None

    for entry in entries:
        lowered = entry["title"].lower()
        if any(keyword in lowered for keyword in product_keywords):
            return entry
    return entries[0] if entries else None


def latest_apple_product_entries(limit: int = 2) -> list[dict[str, str]]:
    product_keywords = ("iphone", "ipad", "macbook", "airpods", "apple watch", "mac", "vision")
    try:
        entries = fetch_latest_apple_entries(limit=max(12, limit * 4))
    except Exception:
        return []

    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        title = str(entry.get("title") or "").strip()
        lowered = title.lower()
        if not title or not any(keyword in lowered for keyword in product_keywords):
            continue
        key = normalize_content_key(title)
        if key in seen:
            continue
        seen.add(key)
        output.append(entry)
        if len(output) >= limit:
            break
    return output


def fetch_latest_macrumors_entries(limit: int = 8) -> list[dict[str, str]]:
    global _MACRUMORS_FEED_CACHE
    if _MACRUMORS_FEED_CACHE is not None:
        return _MACRUMORS_FEED_CACHE[:limit]

    entries = fetch_rss_entries(MACRUMORS_RSS_URL, limit=max(limit, 16))
    normalized = [{**entry, "source": "macrumors"} for entry in entries]
    _MACRUMORS_FEED_CACHE = normalized
    return normalized[:limit]


def parse_feed_datetime(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        pass
    for pattern in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(normalized, pattern)
        except ValueError:
            continue
    return None


def detect_apple_market_topic(title: str) -> dict[str, Any]:
    lowered = title.lower()
    for topic in APPLE_MARKET_TOPICS:
        if any(keyword in lowered for keyword in topic["keywords"]):
            return topic
    return {
        "key": "apple",
        "name": "Apple",
        "keywords": (),
        "link_key": "bluetooth_explorer",
    }


def build_apple_market_heat_queue(
    count: int,
    style_offset: int = 0,
    used_content_keys: set[str] | None = None,
    used_headlines: set[str] | None = None,
) -> list[dict[str, Any]]:
    if count <= 0:
        return []

    entries: list[dict[str, Any]] = []
    try:
        entries.extend({**entry, "source": "apple"} for entry in fetch_latest_apple_entries(limit=max(8, count * 2)))
    except Exception:
        pass
    try:
        entries.extend(fetch_latest_macrumors_entries(limit=max(8, count * 2)))
    except Exception:
        pass

    if not entries:
        return []

    latest_priority_source = latest_apple_product_entries(limit=max(4, count * 2))
    latest_priority_headlines = {normalize_content_key(str(entry.get("title") or "")) for entry in latest_priority_source}

    enriched: list[dict[str, Any]] = []
    used_keys = used_content_keys if used_content_keys is not None else set()
    seen_headlines: set[str] = set()
    historical_headlines = used_headlines if used_headlines is not None else set()
    for index, entry in enumerate(entries):
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        lowered = title.lower()
        if any(blocked in lowered for blocked in APPLE_HEAT_BLOCKLIST):
            continue
        headline_key = normalize_content_key(f"apple_hot {title}")
        plain_headline = normalize_content_key(title)
        if headline_key in used_keys or headline_key in seen_headlines:
            continue
        if plain_headline in historical_headlines and plain_headline not in latest_priority_headlines:
            continue
        topic = detect_apple_market_topic(title)
        updated = parse_feed_datetime(str(entry.get("updated") or ""))
        source_name = str(entry.get("source") or "apple")
        source_weight = 14 if source_name == "apple" else 11
        recency_bonus = max(0, 10 - index)
        score = source_weight + recency_bonus
        if updated is not None:
            age_days = max(0, int((now_local() - updated.astimezone()).total_seconds() // 86400))
            score += max(0, 6 - min(age_days, 6))
        enriched.append(
            {
                **entry,
                "topic": topic,
                "score": score,
                "updated_dt": updated.isoformat() if updated else None,
                "content_key": headline_key,
                "headline_key": plain_headline,
            }
        )
        seen_headlines.add(headline_key)

    if not enriched:
        return []

    product_only = [entry for entry in enriched if str(entry["topic"]["key"]) != "apple"]
    if product_only:
        enriched = product_only

    priority_entries: list[dict[str, Any]] = []
    needed_priority = min(2, count)
    selected_priority_headlines: set[str] = set()
    for entry in latest_priority_source:
        title = str(entry.get("title") or "").strip()
        plain_headline = normalize_content_key(title)
        if not title or plain_headline in selected_priority_headlines:
            continue
        matched = next((item for item in enriched if normalize_content_key(str(item.get("title") or "")) == plain_headline), None)
        if matched is not None:
            priority_entries.append(matched)
            selected_priority_headlines.add(plain_headline)
            if len(priority_entries) >= needed_priority:
                break

    by_topic: dict[str, dict[str, Any]] = {}
    for entry in enriched:
        topic = entry["topic"]
        key = str(topic["key"])
        bucket = by_topic.setdefault(
            key,
            {
                "topic": topic,
                "score": 0,
                "entries": [],
            },
        )
        bucket["score"] += int(entry["score"])
        bucket["entries"].append(entry)

    ranked_topics = sorted(
        by_topic.values(),
        key=lambda item: (
            item["score"],
            max(
                (
                    parse_feed_datetime(str(entry.get("updated") or "")) or datetime.min.replace(tzinfo=now_local().astimezone().tzinfo)
                    for entry in item["entries"]
                ),
                default=datetime.min.replace(tzinfo=now_local().astimezone().tzinfo),
            ),
        ),
        reverse=True,
    )

    queue: list[dict[str, Any]] = []
    style_index = style_offset
    used_queue_keys: set[str] = set()
    last_topic_key: str | None = None
    for entry in priority_entries:
        queue.append(
            {
                "topic": entry["topic"],
                "entry": entry,
                "score": entry["score"],
                "style": APPLE_STYLE_ROTATION[style_index % len(APPLE_STYLE_ROTATION)],
            }
        )
        used_queue_keys.add(str(entry.get("content_key") or ""))
        historical_headlines.add(str(entry.get("headline_key") or ""))
        last_topic_key = str(entry["topic"].get("key") or "")
        style_index += 1
        if len(queue) >= count:
            return queue[:count]

    while len(queue) < count:
        appended = False
        available = []
        for topic_item in ranked_topics:
            entries_for_topic = [
                entry for entry in topic_item["entries"] if str(entry.get("content_key") or "") not in used_queue_keys
            ]
            if entries_for_topic:
                available.append((topic_item, entries_for_topic[0]))
        if not available:
            break

        preferred = [
            pair for pair in available if str(pair[0]["topic"].get("key") or "") != (last_topic_key or "")
        ]
        topic_item, entry = (preferred or available)[0]
        queue.append(
            {
                "topic": topic_item["topic"],
                "entry": entry,
                "score": topic_item["score"],
                "style": APPLE_STYLE_ROTATION[style_index % len(APPLE_STYLE_ROTATION)],
            }
        )
        used_queue_keys.add(str(entry.get("content_key") or ""))
        historical_headlines.add(str(entry.get("headline_key") or ""))
        last_topic_key = str(topic_item["topic"].get("key") or "")
        style_index += 1
        appended = True
        if len(queue) >= count:
            break
        if not appended:
            break
    return queue[:count]


def build_news_heat_queue(count: int, used_content_keys: set[str] | None = None) -> list[dict[str, Any]]:
    if count <= 0:
        return []

    used_keys = used_content_keys if used_content_keys is not None else set()
    queue: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for entry in fetch_official_news_entries(limit=max(8, count * 3)):
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        content_key = normalize_content_key(f"news_hot {title}")
        if content_key in used_keys or content_key in seen_keys:
            continue
        queue.append({**entry, "content_key": content_key})
        seen_keys.add(content_key)
        if len(queue) >= count:
            break
    return queue


def format_feed_date(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%b %d")
    except ValueError:
        pass
    try:
        return datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %z").strftime("%b %d")
    except ValueError:
        return value


def fetch_rss_entries(url: str, limit: int = 8) -> list[dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": "weiluoge-x-story-bot/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        xml_text = response.read().decode("utf-8", errors="replace")

    root = ET.fromstring(xml_text)
    entries: list[dict[str, str]] = []

    channel_items = root.findall(".//item")
    if channel_items:
        for item in channel_items[:limit]:
            title = (item.findtext("title", default="") or "").strip()
            pub_date = (item.findtext("pubDate", default="") or "").strip()
            link = (item.findtext("link", default="") or "").strip()
            if title and link:
                entries.append({"title": title, "updated": pub_date, "url": link})
        return entries

    atom_ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", atom_ns)[:limit]:
        title = (entry.findtext("atom:title", default="", namespaces=atom_ns) or "").strip()
        updated = (entry.findtext("atom:updated", default="", namespaces=atom_ns) or "").strip()
        link = entry.find("atom:link", atom_ns)
        href = (link.attrib.get("href", "") if link is not None else "").strip()
        if title and href:
            entries.append({"title": title, "updated": updated, "url": href})
    return entries


def fetch_anthropic_news_entries(limit: int = 8) -> list[dict[str, str]]:
    request = urllib.request.Request("https://www.anthropic.com/news", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")

    pattern = re.compile(
        r'href="(?P<href>/news/[^"]+)"[^>]*>.*?<h3[^>]*>(?P<title>.*?)</h3>',
        re.IGNORECASE | re.DOTALL,
    )
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in pattern.finditer(html):
        href = match.group("href").strip()
        title = re.sub(r"<[^>]+>", "", match.group("title")).strip()
        if not href or not title or href in seen:
            continue
        seen.add(href)
        entries.append({"title": title, "updated": "", "url": f"https://www.anthropic.com{href}"})
        if len(entries) >= limit:
            break
    return entries


def fetch_official_news_entries(limit: int = 8) -> list[dict[str, str]]:
    sources = [
        ("google", "https://blog.google/technology/ai/rss/"),
        ("microsoft", "https://news.microsoft.com/feed/"),
    ]
    keyword_priority = ("ai", "model", "models", "agent", "agents", "openai", "anthropic", "google", "microsoft")
    collected: list[dict[str, str]] = []
    seen_titles: set[str] = set()

    for source_name, source_url in sources:
        try:
            entries = fetch_rss_entries(source_url, limit=8)
        except Exception:
            continue
        for entry in entries:
            title = str(entry.get("title") or "").strip()
            if not title:
                continue
            key = normalize_content_key(title)
            if key in seen_titles:
                continue
            lowered = title.lower()
            lowered = entry["title"].lower()
            if any(keyword in lowered for keyword in keyword_priority):
                collected.append({**entry, "source": source_name})
                seen_titles.add(key)
                if len(collected) >= limit:
                    return collected[:limit]
        for entry in entries:
            title = str(entry.get("title") or "").strip()
            if not title:
                continue
            key = normalize_content_key(title)
            if key in seen_titles:
                continue
            collected.append({**entry, "source": source_name})
            seen_titles.add(key)
            if len(collected) >= limit:
                return collected[:limit]

    try:
        entries = fetch_anthropic_news_entries(limit=8)
    except Exception:
        entries = []
    for entry in entries:
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        key = normalize_content_key(title)
        if key in seen_titles:
            continue
        collected.append({**entry, "source": "anthropic"})
        seen_titles.add(key)
        if len(collected) >= limit:
            break
    return collected[:limit]


def latest_official_news_entry() -> dict[str, str] | None:
    entries = fetch_official_news_entries(limit=1)
    if entries:
        return entries[0]
    return None


def choose_link_key_for_feature(feature: str) -> str:
    lowered = feature.lower()
    if any(keyword in lowered for keyword in ["cleanup", "duplicate", "photo", "video", "storage", "contact"]):
        return "cleanup_pro"
    if any(
        keyword in lowered
        for keyword in ["translate", "translation", "language", "subtitle", "ocr", "voice", "camera text", "multilingual"]
    ):
        return "translate_ai"
    if any(keyword in lowered for keyword in ["find", "lost", "airpod", "watch"]):
        return "find_ai"
    if any(
        keyword in lowered
        for keyword in ["bluetooth", "ble", "radar", "scan", "device", "signal", "connect", "diagnostic", "packet"]
    ):
        return "bluetooth_explorer"
    return "cleanup_pro"


def existing_media_candidates(group: str) -> list[Path]:
    output: list[Path] = []
    seen: set[str] = set()
    for relative_path in MEDIA_LIBRARY.get(group, []):
        candidate = (REPO_ROOT / relative_path).resolve()
        key = os.path.normcase(str(candidate))
        if candidate.exists() and candidate.is_file() and not is_disallowed_media_path(candidate) and key not in seen:
            output.append(candidate)
            seen.add(key)
    directory_pool = list(MEDIA_SHARED_RANDOM_DIRECTORIES)
    for relative_dir in MEDIA_DIRECTORY_LIBRARY.get(group, []):
        if relative_dir not in directory_pool:
            directory_pool.append(relative_dir)
    for relative_dir in directory_pool:
        directory = (REPO_ROOT / relative_dir).resolve()
        if not directory.exists() or not directory.is_dir():
            continue
        for pattern in MEDIA_GLOB_PATTERNS:
            for candidate in sorted(directory.glob(pattern)):
                key = os.path.normcase(str(candidate))
                if candidate.is_file() and not is_disallowed_media_path(candidate) and key not in seen:
                    output.append(candidate)
                    seen.add(key)
    ensure_media_darkness_cache(output)
    return [candidate for candidate in output if not is_too_dark_media(candidate)]


def media_cache_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def ensure_media_darkness_cache(paths: list[Path]) -> None:
    uncached: list[Path] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        key = media_cache_key(path)
        if key not in _MEDIA_DARKNESS_CACHE:
            uncached.append(path)

    if not uncached:
        return

    if os.name != "nt":
        for path in uncached:
            _MEDIA_DARKNESS_CACHE[media_cache_key(path)] = False
        return

    script = rf"""
$ErrorActionPreference = 'Stop'
$raw = [Console]::In.ReadToEnd()
if (-not $raw) {{
  return
}}
$paths = $raw | ConvertFrom-Json
Add-Type -AssemblyName System.Drawing
$result = @{{}}
foreach ($path in $paths) {{
  try {{
    $bmp = New-Object System.Drawing.Bitmap($path)
    $w = $bmp.Width
    $h = $bmp.Height
    $stepX = [Math]::Max(1, [int]($w / 12))
    $stepY = [Math]::Max(1, [int]($h / 12))
    $sum = 0.0
    $count = 0
    for ($x = 0; $x -lt $w; $x += $stepX) {{
      for ($y = 0; $y -lt $h; $y += $stepY) {{
        $c = $bmp.GetPixel($x, $y)
        $sum += (0.2126 * $c.R + 0.7152 * $c.G + 0.0722 * $c.B)
        $count += 1
      }}
    }}
    $bmp.Dispose()
    $avg = if ($count -gt 0) {{ $sum / $count }} else {{ 255.0 }}
    $result[$path] = [bool]($avg -lt {MEDIA_MIN_BRIGHTNESS})
  }} catch {{
    $result[$path] = $false
  }}
}}
$result | ConvertTo-Json -Compress
"""

    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            input=json.dumps([str(path) for path in uncached], ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=True,
        )
        payload = completed.stdout.strip()
        dark_map = json.loads(payload) if payload else {}
    except Exception:
        dark_map = {}

    for path in uncached:
        key = media_cache_key(path)
        _MEDIA_DARKNESS_CACHE[key] = bool(dark_map.get(str(path), False))


def is_too_dark_media(path: Path) -> bool:
    ensure_media_darkness_cache([path])
    return _MEDIA_DARKNESS_CACHE.get(media_cache_key(path), False)


def is_disallowed_media_path(path: Path) -> bool:
    lowered = path.name.lower()
    path_tokens = "/" + "/".join(part.lower() for part in path.parts) + "/"
    return (
        lowered in DISALLOWED_MEDIA_EXACT_NAMES
        or any(part in lowered for part in DISALLOWED_MEDIA_NAME_PARTS)
        or any(f"/{part}/" in path_tokens for part in DISALLOWED_MEDIA_PATH_PARTS)
    )


def is_disallowed_media(path: Path) -> bool:
    return is_disallowed_media_path(path) or is_too_dark_media(path)


def infer_media_group(text: str, content_slot: str) -> str:
    lowered = text.lower()
    if content_slot == "apple_hot":
        return "apple_hot"
    if content_slot in {"celebrity_humor", "news_hot"} or any(
        keyword in lowered for keyword in ["openai", "anthropic", "amazon", "google", "microsoft", "ai news"]
    ):
        return "trending_hot"
    if "find ai" in lowered or any(keyword in lowered for keyword in ["airpods", "last-seen", "nearby"]):
        return "find_ai"
    if "cleanup pro" in lowered or any(keyword in lowered for keyword in ["cleanup", "duplicate", "storage", "photo"]):
        return "cleanup_pro"
    if "bluetooth explorer" in lowered or any(keyword in lowered for keyword in ["ble", "bluetooth", "packet"]):
        return "bluetooth_explorer"
    return "velocai_brand"


def pick_media_for_item(
    item: dict[str, Any],
    used_media_counts: dict[str, int] | None = None,
) -> tuple[Path, str]:
    item_seed = str(item.get("id") or item.get("scheduled_at") or item.get("text") or "velocai")
    rng = random.Random(item_seed)
    primary_group = infer_media_group(str(item.get("text") or ""), str(item.get("content_slot") or ""))
    group_order = [primary_group, "velocai_brand", "trending_hot"]
    seen: set[str] = set()
    for group in group_order:
        if group in seen:
            continue
        seen.add(group)
        candidates = existing_media_candidates(group)
        if candidates:
            counts = used_media_counts or {}
            ranked = sorted(
                candidates,
                key=lambda path: (
                    counts.get(path.relative_to(REPO_ROOT).as_posix(), 0),
                    rng.random(),
                ),
            )
            return ranked[0], group
    raise ValueError(f"No media files available for item {item.get('id') or 'unknown'}.")


def ensure_item_media(item: dict[str, Any]) -> Path:
    media_file = str(item.get("media_file") or "").strip()
    if media_file:
        candidate = (REPO_ROOT / media_file).resolve()
        if candidate.exists() and candidate.is_file() and not is_disallowed_media(candidate):
            return candidate

    media_path, media_group = pick_media_for_item(item)
    item["media_file"] = media_path.relative_to(REPO_ROOT).as_posix()
    item["media_group"] = media_group
    return media_path


def rebalance_pending_media(plan: dict[str, Any]) -> int:
    used_counts: dict[str, int] = {}
    for item in plan.get("items", []):
        media_file = str(item.get("media_file") or "").strip()
        if media_file:
            used_counts[media_file] = used_counts.get(media_file, 0) + 1

    updated = 0
    pending_items = [item for item in plan.get("items", []) if item.get("status") != "posted"]
    for item in pending_items:
        before = str(item.get("media_file") or "").strip()
        if before:
            used_counts[before] = max(0, used_counts.get(before, 0) - 1)
        media_path, media_group = pick_media_for_item(item, used_media_counts=used_counts)
        after = media_path.relative_to(REPO_ROOT).as_posix()
        item["media_file"] = after
        item["media_group"] = media_group
        used_counts[after] = used_counts.get(after, 0) + 1
        if before != after:
            updated += 1
    return updated


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
        first_url_start = url_matches[0].start()
        prefix = text[:first_url_start].rstrip()
        suffix = " ".join(match.group(0) for match in url_matches).strip()
        candidate = f"{prefix}... {suffix}".strip()
        while prefix and tweet_length(candidate) > MAX_TWEET_LEN:
            prefix = prefix[:-1].rstrip()
            candidate = f"{prefix}... {suffix}".strip()
        if tweet_length(candidate) <= MAX_TWEET_LEN:
            return candidate

    return text[: MAX_TWEET_LEN - 3].rstrip() + "..."


def compose_post(*lines: str) -> str:
    cleaned = [line.strip() for line in lines if line and line.strip()]
    return "\n\n".join(cleaned)


def compact_structure_line(*candidates: str, max_chars: int = 40) -> str:
    cleaned = [candidate.strip() for candidate in candidates if candidate and candidate.strip()]
    if not cleaned:
        return ""
    within_limit = [candidate for candidate in cleaned if len(candidate) <= max_chars]
    if within_limit:
        return min(within_limit, key=len)
    first = cleaned[0]
    return first[:max_chars].rstrip(" ,.;:") + "..."


def sentence_case(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    return cleaned[0].upper() + cleaned[1:]


def app_reference(app: dict[str, Any]) -> str:
    category = str(app.get("category") or "").strip()
    if category:
        return f"{app['name']}, our {category}"
    return str(app["name"])


def pick_fitting_text(candidates: list[str], rng: random.Random) -> str:
    shuffled = list(candidates)
    rng.shuffle(shuffled)
    fitting = [candidate for candidate in shuffled if tweet_length(candidate) <= MAX_TWEET_LEN]
    if not fitting:
        return clip_tweet(shuffled[0])

    in_range = [candidate for candidate in fitting if MIN_TWEET_LEN <= tweet_length(candidate) <= PREFERRED_TWEET_LEN]
    if in_range:
        return sorted(in_range, key=tweet_length, reverse=True)[0]

    near_range = [
        candidate
        for candidate in fitting
        if max(225, MIN_TWEET_LEN - 10) <= tweet_length(candidate) <= MAX_TWEET_LEN
    ]
    if near_range:
        return sorted(near_range, key=tweet_length, reverse=True)[0]

    longest = max(fitting, key=tweet_length)
    clipped = clip_tweet(longest)
    if tweet_length(clipped) >= MIN_TWEET_LEN:
        return clipped
    return longest


def build_classic_story(feature: str, index: int, rng: random.Random) -> dict[str, Any]:
    role = rng.choice(ROLES)
    setup = rng.choice(SETUPS).format(feature=feature)
    punchline = rng.choice(PUNCHLINES)
    tag_line = rng.choice(TAGLINES)
    url = link_bundle(choose_link_key_for_feature(feature))
    feature_tag = f"#{feature_hashtag(feature)}"
    candidates = [
        f"Today in product work, {role} {setup}. {punchline} {feature_tag} {tag_line} {url}",
        f"One tiny team story: {role} {setup}. {punchline} {feature_tag} {url}",
        f"Current build-in-public mood: {role} {setup}. {punchline} {url}",
    ]
    text = pick_fitting_text(candidates, rng)
    return {"text": text, "content_key": normalize_content_key(f"classic {feature} {role} {setup} {punchline}")}


def build_celebrity_post(rng: random.Random) -> dict[str, Any]:
    celebrity = rng.choice(CELEBRITIES)
    setup = rng.choice(CELEBRITY_SETUPS)
    punchline = rng.choice(CELEBRITY_PUNCHLINES)
    tag_line = rng.choice(CELEBRITY_TAGS)
    url = link_bundle("bluetooth_explorer")
    candidates = [
        f"I have a running theory that {celebrity} would be great at {setup}. {punchline} {tag_line} {url}",
        f"Some days I think {celebrity} could walk into a product team and start {setup}. {punchline} {url}",
        f"Tiny morale hack: imagine {celebrity} {setup}. Weirdly effective. {punchline} {url}",
    ]
    text = pick_fitting_text(candidates, rng)
    return {"text": text, "content_key": normalize_content_key(f"celebrity {celebrity} {setup} {punchline}")}


def build_velocai_use_case_post(rng: random.Random) -> dict[str, Any]:
    app = rng.choice(VELOCAI_APPS)
    url = app_link_bundle(app)
    opener = rng.choice(VELOCAI_USE_CASE_OPENERS)
    hook = rng.choice(VELOCAI_USE_CASE_HOOKS)
    use_case = rng.choice(app["use_cases"])
    closer = rng.choice(VELOCAI_USE_CASE_CLOSERS)
    fact_angle = rng.choice(VELOCAI_USE_CASE_FACT_ANGLES)
    product_ref = app_reference(app)
    structure = compact_structure_line(hook, opener)
    candidates = [
        compose_post(
            structure,
            f"{product_ref} helps you {use_case}.",
            fact_angle,
            closer,
            url,
        ),
        compose_post(
            structure,
            f"{product_ref} is at its best when you need to {use_case}.",
            fact_angle,
            url,
        ),
        compose_post(
            compact_structure_line("The practical test is simple."),
            f"It is whether {product_ref} helps you {use_case}.",
            "That is usually where product quality shows up first.",
            url,
        ),
        compose_post(
            compact_structure_line("A useful workflow is obvious."),
            f"{product_ref} makes sense when you want to {use_case}.",
            "That is what lowers hesitation in real use.",
            url,
        ),
    ]
    text = pick_fitting_text(candidates, rng)
    return {
        "text": text,
        "content_key": normalize_content_key(f"velocai_use_case {app['name']} {use_case}"),
        "product_label": product_ref,
    }


def build_velocai_update_post(rng: random.Random, extra_topics: list[str] | None = None) -> dict[str, Any]:
    app = rng.choice(VELOCAI_APPS)
    url = app_link_bundle(app)
    opener = rng.choice(VELOCAI_UPDATE_OPENERS)
    hook = rng.choice(VELOCAI_UPDATE_HOOKS)
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
    fact_angle = rng.choice(VELOCAI_UPDATE_FACT_ANGLES)
    product_ref = app_reference(app)
    structure = compact_structure_line(hook, opener, f"{app['name']} update note.")
    candidates = [
        compose_post(
            structure,
            f"{product_ref} now brings {update_point}.",
            fact_angle,
            closer,
            url,
        ),
        compose_post(
            structure,
            f"{product_ref} gets more useful when updates bring {update_point}.",
            fact_angle,
            url,
        ),
        compose_post(
            compact_structure_line(f"{app['name']} update note."),
            f"{sentence_case(update_point)}.",
            fact_angle,
            url,
        ),
        compose_post(
            compact_structure_line("The update changes the workflow."),
            f"{product_ref} quietly improves {update_point}.",
            "That is usually what users feel before they can name it.",
            url,
        ),
    ]
    text = pick_fitting_text(candidates, rng)
    return {
        "text": text,
        "content_key": normalize_content_key(f"velocai_update {app['name']} {update_point}"),
        "product_label": product_ref,
    }


def build_apple_product_post(rng: random.Random, apple_topic: dict[str, Any] | None = None) -> dict[str, Any]:
    latest_entry = latest_apple_product_entry()
    topic_context = apple_topic or {}
    ranked_entry = topic_context.get("entry") if isinstance(topic_context, dict) else None
    ranked_topic = topic_context.get("topic") if isinstance(topic_context, dict) else None
    style = str(topic_context.get("style") or "").strip().lower()

    if ranked_entry:
        title = str(ranked_entry.get("title") or "").strip()
        entry_date = format_feed_date(str(ranked_entry.get("updated") or ""))
        topic_name = str((ranked_topic or {}).get("name") or "Apple").strip()
        link_key = str((ranked_topic or {}).get("link_key") or "bluetooth_explorer")
        url = link_bundle(link_key)
        source_name = str(ranked_entry.get("source") or "Apple").title()
        source_label = f"{source_name} {entry_date}".strip()
        angle = rng.choice(APPLE_EXPERT_ANGLES)
        style_candidates = {
            "mkbhd": compose_post(
                compact_structure_line("Specs are not the main signal."),
                f"{title} matters because it changes how buyers frame the next {topic_name} decision.",
                angle,
                url,
            ),
            "gurman": compose_post(
                compact_structure_line("The useful signal is operational."),
                f"{source_label} points to where the {topic_name} roadmap is moving next: {title}.",
                angle,
                url,
            ),
            "ijustine": compose_post(
                compact_structure_line("This matters in daily use."),
                f"{title} is exactly the kind of change normal {topic_name} buyers notice after a week, not a keynote.",
                url,
            ),
            "prosser": compose_post(
                compact_structure_line("The question is what behavior changes."),
                f"If {title} shifts how people compare the {topic_name} lineup, the headline was more important than it looked.",
                url,
            ),
            "macrumors": compose_post(
                compact_structure_line("Apple headline, quick read."),
                f"The practical effect is where demand and discussion move around {topic_name}.",
                angle,
                url,
            ),
        }
        preferred_style_candidate = style_candidates.get(style, "")
        if preferred_style_candidate and tweet_length(preferred_style_candidate) <= MAX_TWEET_LEN:
            return {
                "text": preferred_style_candidate,
                "content_key": normalize_content_key(str(ranked_entry.get("content_key") or f"apple_hot {title}")),
                "product_label": topic_name,
            }

        candidates = [
            compose_post(
                compact_structure_line(rng.choice(APPLE_HOOKS)),
                f"{source_label} says more about everyday demand than launch-day hype: {title}.",
                angle,
                url,
            ),
            compose_post(
                compact_structure_line(f"The key lens is {topic_name.lower()} demand."),
                f"{title} points to what normal buyers will care about next.",
                angle,
                url,
            ),
            compose_post(
                compact_structure_line("The commercial logic is clearer now."),
                f"{title} feels like Apple leaning harder into products that are easier to justify in normal life.",
                angle,
                url,
            ),
        ]
        return {
            "text": pick_fitting_text([candidate for candidate in candidates if candidate], rng),
            "content_key": normalize_content_key(str(ranked_entry.get("content_key") or f"apple_hot {title}")),
            "product_label": topic_name,
        }

    if latest_entry:
        entry_date = format_feed_date(latest_entry.get("updated", ""))
        fallback_product = rng.choice(APPLE_PRODUCTS)
        url = link_bundle(fallback_product["link_key"])
        hook = rng.choice(APPLE_HOOKS)
        angle = rng.choice(APPLE_EXPERT_ANGLES)
        candidates = [
            compose_post(
                compact_structure_line(hook),
                f"Apple's {entry_date} update '{latest_entry['title']}' says more about everyday demand than launch-day hype.",
                angle,
                url,
            ),
            compose_post(
                compact_structure_line("The useful lens is buyer demand."),
                f"'{latest_entry['title']}' points to what normal buyers care about next.",
                angle,
                url,
            ),
            compose_post(
                compact_structure_line("The market logic is straightforward."),
                f"'{latest_entry['title']}' feels like Apple leaning harder into products that are easy to justify in normal life.",
                angle,
                url,
            ),
            compose_post(
                compact_structure_line("The hardware is not the whole story."),
                "Apple keeps optimizing for products people can explain to themselves in 10 seconds.",
                angle,
                url,
            ),
        ]
        return {
            "text": pick_fitting_text(candidates, rng),
            "content_key": normalize_content_key(f"apple_hot {latest_entry['title']}"),
            "product_label": fallback_product["name"],
        }

    product = rng.choice(APPLE_PRODUCTS)
    opener = rng.choice(APPLE_OPENERS)
    closer = rng.choice(APPLE_CLOSERS)
    hook = rng.choice(APPLE_HOOKS)
    angle = rng.choice(APPLE_EXPERT_ANGLES)
    url = link_bundle(product["link_key"])
    candidates = [
        compose_post(
            compact_structure_line(hook),
            f"{product['name']} {product['angle']}.",
            angle,
            closer,
            url,
        ),
        compose_post(
            compact_structure_line(opener),
            f"{product['name']} still earns attention because it {product['angle']}.",
            angle,
            closer,
            url,
        ),
        compose_post(
            compact_structure_line(f"{product['name']} still stands out."),
            f"{product['name']} still stands out for a simple reason.",
            f"It {product['angle']}.",
            angle,
            url,
        ),
    ]
    return {
        "text": pick_fitting_text(candidates, rng),
        "content_key": normalize_content_key(f"apple_hot {product['name']}"),
        "product_label": product["name"],
    }


def build_news_hot_post(rng: random.Random, news_entry: dict[str, Any] | None = None) -> dict[str, Any]:
    latest_entry = news_entry or latest_official_news_entry()
    if latest_entry:
        opener = rng.choice(NEWS_OPENERS)
        closer = rng.choice(NEWS_CLOSERS)
        hook = rng.choice(NEWS_HOOKS)
        fact_angle = rng.choice(NEWS_FACT_ANGLES)
        entry_date = format_feed_date(latest_entry.get("updated", ""))
        source_name = str(latest_entry.get("source") or "official source").title()
        url = link_bundle("bluetooth_explorer")
        candidates = [
            compose_post(
                compact_structure_line(hook, opener),
                fact_angle,
                f"{source_name}'s {entry_date} update '{latest_entry['title']}' says the real story is product execution.",
                url,
            ),
            compose_post(
                compact_structure_line(opener, hook),
                fact_angle,
                f"{source_name}'s latest note on {entry_date} is a reminder that shipping useful product beats abstract AI hype.",
                url,
            ),
            compose_post(
                compact_structure_line("Today's useful signal is simple."),
                fact_angle,
                "Scale only matters when teams turn it into products people actually use.",
                url,
            ),
            compose_post(
                compact_structure_line("Headlines are not the whole story."),
                f"'{latest_entry['title']}' matters less as a headline and more as a clue about where product teams are actually heading next.",
                fact_angle,
                url,
            ),
            compose_post(
                compact_structure_line("This is easy to overread."),
                f"I read '{latest_entry['title']}' as a clue about who is actually building toward real product usage next.",
                fact_angle,
                url,
            ),
        ]
        return {
            "text": pick_fitting_text(candidates, rng),
            "content_key": normalize_content_key(str(latest_entry.get("content_key") or f"news_hot {latest_entry['title']}")),
            "product_label": source_name,
        }

    return build_celebrity_post(rng)


def build_content_slots(count: int, content_mode: str, rng: random.Random) -> list[str]:
    if content_mode == "classic":
        return ["classic"] * count

    base_cycle = ["apple_hot", "apple_hot", "velocai_use_case", "apple_hot", "velocai_update", "apple_hot", "news_hot"]
    slots = [base_cycle[index % len(base_cycle)] for index in range(count)]
    if count >= 2:
        while slots.count("apple_hot") < 2:
            slots[min(len(slots) - 1, slots.count("apple_hot"))] = "apple_hot"
    rng.shuffle(slots)
    return slots


def build_story(
    feature: str,
    slot: str,
    index: int,
    rng: random.Random,
    update_topics: list[str] | None = None,
    apple_topic: dict[str, Any] | None = None,
    news_topic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if slot == "classic":
        return build_classic_story(feature=feature, index=index, rng=rng)
    if slot == "celebrity_humor":
        return build_celebrity_post(rng=rng)
    if slot == "news_hot":
        return build_news_hot_post(rng=rng, news_entry=news_topic)
    if slot == "velocai_use_case":
        return build_velocai_use_case_post(rng=rng)
    if slot == "velocai_update":
        return build_velocai_update_post(rng=rng, extra_topics=update_topics)
    if slot == "apple_hot":
        return build_apple_product_post(rng=rng, apple_topic=apple_topic)
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
    window_name: str = "primary",
    used_text_signatures: set[str] | None = None,
    used_content_keys: set[str] | None = None,
    recent_texts: list[str] | None = None,
    recent_openers: set[str] | None = None,
    used_apple_headlines: set[str] | None = None,
    apple_style_offset: int = 0,
    initial_media_counts: dict[str, int] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    generator = rng or random.Random()
    day_token = schedule[0].strftime("%Y%m%d") if schedule else now_local().strftime("%Y%m%d")
    slots = build_content_slots(len(schedule), content_mode=content_mode, rng=generator)
    used_content_key_set: set[str] = used_content_keys if used_content_keys is not None else set()
    if used_text_signatures is None:
        used_signatures = set()
    else:
        used_signatures = used_text_signatures
    apple_market_queue = build_apple_market_heat_queue(
        slots.count("apple_hot"),
        style_offset=apple_style_offset,
        used_content_keys=used_content_key_set,
        used_headlines=used_apple_headlines,
    )
    news_queue = build_news_heat_queue(slots.count("news_hot"), used_content_keys=used_content_key_set)
    apple_market_index = 0
    news_index = 0
    items: list[dict[str, Any]] = []
    used_media_counts: dict[str, int] = dict(initial_media_counts or {})
    for offset, when in enumerate(schedule, start=0):
        index = start_index + offset
        feature = generator.choice(features)
        slot = slots[offset]
        apple_topic = None
        news_topic = None
        if slot == "apple_hot" and apple_market_index < len(apple_market_queue):
            apple_topic = apple_market_queue[apple_market_index]
            apple_market_index += 1
        elif slot == "apple_hot":
            slot = "news_hot" if news_index < len(news_queue) else "velocai_update"
        if slot == "news_hot" and news_index < len(news_queue):
            news_topic = news_queue[news_index]
            news_index += 1
        payload = next_unique_text(
            build_fn=lambda feature=feature, slot=slot, index=index, apple_topic=apple_topic, news_topic=news_topic: build_story(
                feature=feature,
                slot=slot,
                index=index,
                rng=generator,
                update_topics=update_topics,
                apple_topic=apple_topic,
                news_topic=news_topic,
            ),
            used_signatures=used_signatures,
            used_content_keys=used_content_key_set,
            recent_texts=recent_texts,
            recent_openers=recent_openers,
        )
        text = str(payload.get("text") or "").strip()
        item = {
            "id": f"{day_token}-{index:03d}",
            "scheduled_at": when.isoformat(),
            "window_name": window_name,
            "text": text,
            "content_key": str(payload.get("content_key") or normalize_text_signature(text)).strip(),
            "status": "pending",
            "attempts": 0,
            "posted_at": None,
            "tweet_id": None,
            "last_attempt_at": None,
            "last_error": None,
            "content_slot": slot,
        }
        if payload.get("product_label"):
            item["product_label"] = str(payload["product_label"])
        if apple_topic:
            item["market_heat_topic"] = apple_topic["topic"]["key"]
            item["market_heat_score"] = apple_topic["score"]
            item["market_heat_style"] = apple_topic["style"]
            item["market_heat_headline"] = apple_topic["entry"]["title"]
        if news_topic:
            item["news_headline"] = str(news_topic.get("title") or "")
            item["news_source"] = str(news_topic.get("source") or "")
        media_path, media_group = pick_media_for_item(item, used_media_counts=used_media_counts)
        media_key = media_path.relative_to(REPO_ROOT).as_posix()
        used_media_counts[media_key] = used_media_counts.get(media_key, 0) + 1
        items.append(
            {
                **item,
                "media_file": media_key,
                "media_group": media_group,
            }
        )
    return items, slots.count("apple_hot")


def create_plan(
    *,
    day: date,
    windows: list[TimeWindowSpec],
    features: list[str],
    content_mode: str,
    update_topics: list[str] | None,
    paths: BotPaths,
    force: bool = False,
    reference_now: datetime | None = None,
) -> tuple[dict[str, Any], bool]:
    if not windows:
        raise ValueError("At least one time window is required.")

    path = plan_path(paths, day)
    if path.exists() and not force:
        return load_json(path), False

    rng = random.Random()
    items: list[dict[str, Any]] = []
    target_posts = 0
    start_index = 1
    apple_style_offset = 0
    used_text_signatures = collect_posted_text_signatures(paths, exclude_day=day)
    used_content_keys = collect_posted_content_keys(paths, exclude_day=day)
    recent_texts = collect_posted_text_bodies(paths, exclude_day=day)
    recent_openers = collect_recent_openers(paths, exclude_day=day)
    used_apple_headlines = collect_posted_apple_headlines(paths, exclude_day=day)
    used_media_counts = collect_media_usage_counts(paths, exclude_day=day)
    for window in windows:
        window_target = rng.randint(window.min_posts, window.max_posts)
        schedule = build_daily_schedule(
            day=day,
            count=window_target,
            day_start=window.day_start,
            day_end=window.day_end,
            rng=rng,
            reference_now=reference_now,
        )
        window_items, apple_count = build_items(
            schedule=schedule,
            features=features,
            start_index=start_index,
            rng=rng,
            content_mode=content_mode,
            update_topics=update_topics,
            window_name=window.name,
            used_text_signatures=used_text_signatures,
            used_content_keys=used_content_keys,
            recent_texts=recent_texts,
            recent_openers=recent_openers,
            used_apple_headlines=used_apple_headlines,
            apple_style_offset=apple_style_offset,
            initial_media_counts=used_media_counts,
        )
        items.extend(window_items)
        for item in window_items:
            content_key = normalize_content_key(str(item.get("content_key") or ""))
            if content_key:
                used_content_keys.add(content_key)
            text = str(item.get("text") or "").strip()
            if text:
                recent_texts.append(text)
                if len(recent_texts) > 80:
                    del recent_texts[:-80]
                opener = normalize_content_key(first_meaningful_line(text))
                if opener:
                    recent_openers.add(opener)
            media_file = str(item.get("media_file") or "").strip()
            if media_file:
                used_media_counts[media_file] = used_media_counts.get(media_file, 0) + 1
        start_index += len(schedule)
        apple_style_offset += apple_count
        target_posts += window_target
    items.sort(key=lambda item: item["scheduled_at"])
    plan = {
        "date": day.isoformat(),
        "created_at": now_local().isoformat(),
        "min_posts": sum(window.min_posts for window in windows),
        "max_posts": sum(window.max_posts for window in windows),
        "target_posts": target_posts,
        "day_start": windows[0].day_start,
        "day_end": windows[-1].day_end,
        "windows": [
            {
                "name": window.name,
                "day_start": window.day_start,
                "day_end": window.day_end,
                "min_posts": window.min_posts,
                "max_posts": window.max_posts,
            }
            for window in windows
        ],
        "content_mode": content_mode,
        "items": items,
    }
    save_json(path, plan)
    write_log(paths, f"plan_created date={day.isoformat()} target_posts={target_posts}", day)
    return plan, True


def ensure_minimum_items(
    plan: dict[str, Any],
    windows: list[TimeWindowSpec],
    features: list[str],
    content_mode: str,
    update_topics: list[str] | None,
    paths: BotPaths,
    now: datetime,
) -> int:
    items = plan.get("items", [])
    day = date.fromisoformat(plan["date"])
    rng = random.Random()
    start_index = len(items) + 1
    added_total = 0
    apple_style_offset = sum(1 for item in items if item.get("content_slot") == "apple_hot")
    if not windows:
        return 0
    used_text_signatures = collect_posted_text_signatures(paths, exclude_day=day)
    used_content_keys = collect_posted_content_keys(paths, exclude_day=day)
    recent_texts = collect_posted_text_bodies(paths, exclude_day=day)
    recent_openers = collect_recent_openers(paths, exclude_day=day)
    used_apple_headlines = collect_posted_apple_headlines(paths, exclude_day=day)
    used_media_counts = collect_media_usage_counts(paths, exclude_day=day)
    for item in items:
        signature = normalize_text_signature(str(item.get("text") or ""))
        if signature:
            used_text_signatures.add(signature)
        content_key = normalize_content_key(str(item.get("content_key") or ""))
        if content_key:
            used_content_keys.add(content_key)
        text = str(item.get("text") or "").strip()
        if text:
            recent_texts.append(text)
            if len(recent_texts) > 80:
                del recent_texts[:-80]
            opener = normalize_content_key(first_meaningful_line(text))
            if opener:
                recent_openers.add(opener)
        media_file = str(item.get("media_file") or "").strip()
        if media_file:
            used_media_counts[media_file] = used_media_counts.get(media_file, 0) + 1

    for window in windows:
        existing_count = sum(1 for item in items if item.get("window_name") == window.name)
        short = window.min_posts - existing_count
        if short <= 0:
            continue
        schedule = build_daily_schedule(
            day=day,
            count=short,
            day_start=window.day_start,
            day_end=window.day_end,
            rng=rng,
            reference_now=now,
        )
        new_items, apple_count = build_items(
            schedule=schedule,
            features=features,
            start_index=start_index,
            rng=rng,
            content_mode=content_mode,
            update_topics=update_topics,
            window_name=window.name,
            used_text_signatures=used_text_signatures,
            used_content_keys=used_content_keys,
            recent_texts=recent_texts,
            recent_openers=recent_openers,
            used_apple_headlines=used_apple_headlines,
            apple_style_offset=apple_style_offset,
            initial_media_counts=used_media_counts,
        )
        plan["items"].extend(new_items)
        start_index += len(new_items)
        apple_style_offset += apple_count
        added_total += len(new_items)
        items = plan["items"]
        for item in new_items:
            content_key = normalize_content_key(str(item.get("content_key") or ""))
            if content_key:
                used_content_keys.add(content_key)
            text = str(item.get("text") or "").strip()
            if text:
                recent_texts.append(text)
                if len(recent_texts) > 80:
                    del recent_texts[:-80]
                opener = normalize_content_key(first_meaningful_line(text))
                if opener:
                    recent_openers.add(opener)
            media_file = str(item.get("media_file") or "").strip()
            if media_file:
                used_media_counts[media_file] = used_media_counts.get(media_file, 0) + 1

    plan["items"].sort(key=lambda item: item["scheduled_at"])
    plan["target_posts"] = max(int(plan.get("target_posts", 0)), len(plan["items"]))
    return added_total


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
    media_file: Path | None,
    creds: tuple[str, str, str, str] | None,
    playwright_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if method == "playwright":
        return send_tweet_playwright(
            text=text,
            reply_to=None,
            media_files=[media_file] if media_file is not None else None,
            dry_run=False,
            **(playwright_kwargs or {}),
        )
    if method == "api":
        if media_file is not None:
            raise ValueError("X API posting with media is not supported in this repo. Use Playwright posting.")
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
    media_file: Path | None,
    post_mode: str,
    creds: tuple[str, str, str, str] | None,
    playwright_kwargs: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str]:
    errors: list[str] = []
    for method in post_methods_for_mode(post_mode):
        try:
            return (
                send_item_via_method(
                    method=method,
                    text=text,
                    media_file=media_file,
                    creds=creds,
                    playwright_kwargs=playwright_kwargs,
                ),
                method,
            )
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
    playwright_kwargs: dict[str, Any] | None = None,
) -> tuple[int, int]:
    posted_now = 0
    attempted_now = 0

    for item in due_items:
        attempted_now += 1
        item["attempts"] = int(item.get("attempts", 0)) + 1
        item["last_attempt_at"] = now_local().isoformat()
        media_path = ensure_item_media(item)

        if dry_run:
            write_log(
                paths,
                "dry_run item_id="
                f"{item['id']} scheduled_at={item['scheduled_at']} post_mode={post_mode} "
                f"media_file={item.get('media_file', '')}",
                date.fromisoformat(plan["date"]),
            )
            continue

        try:
            result, method = send_item_with_fallback(
                text=item["text"],
                media_file=media_path,
                post_mode=post_mode,
                creds=creds,
                playwright_kwargs=playwright_kwargs,
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
                "posted item_id="
                f"{item['id']} method={method} tweet_id={tweet_id or 'unknown'} "
                f"media_file={item.get('media_file', '')}",
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
    windows = resolve_window_specs(args)
    plan, created = create_plan(
        day=target_day,
        windows=windows,
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
        windows = resolve_window_specs(args)
        playwright_kwargs = resolve_playwright_kwargs(args)
        plan_file = plan_path(paths, target_day)
        if not plan_file.exists():
            create_plan(
                day=target_day,
                windows=windows,
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
            windows=windows,
            features=features,
            content_mode=content_mode,
            update_topics=update_topics,
            paths=paths,
            now=now_local(),
        )
        if added > 0:
            write_log(paths, f"plan_topped_up added={added}", target_day)
        rebalanced = rebalance_pending_media(plan)
        if rebalanced > 0:
            write_log(paths, f"plan_media_rebalanced updated={rebalanced}", target_day)

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
            playwright_kwargs=playwright_kwargs,
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
        target.add_argument(
            "--window-spec",
            action="append",
            help="Repeatable window definition: name|HH:MM|HH:MM|min_posts|max_posts",
        )
        target.add_argument("--playwright-chrome-path", type=Path, help="Explicit Chrome executable path for Playwright posting.")
        target.add_argument("--playwright-user-data-dir", type=Path, help="Explicit Chrome user data dir for Playwright posting.")
        target.add_argument("--playwright-profile-directory", help="Explicit Chrome profile directory name for Playwright posting.")
        target.add_argument("--playwright-proxy-server", help="Explicit proxy server for Playwright posting.")
        target.add_argument(
            "--playwright-login-wait-seconds",
            type=int,
            default=0,
            help="Optional seconds to wait for manual X login when Playwright posting needs it.",
        )

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
        resolve_window_specs(args)
        if not getattr(args, "window_spec", None):
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
