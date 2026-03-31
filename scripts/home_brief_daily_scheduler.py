#!/usr/bin/env python3
"""Refresh the homepage daily briefing section with product-relevant live news."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from html import escape, unescape
from pathlib import Path
import subprocess
from PIL import Image, ImageStat

from blog_daily_scheduler import add_git_publish_args, resolve_git_command, run_git_command

SITE_URL = "https://velocai.net"
HOME_INDEX_REL = Path("index.html")
SITEMAP_REL = Path("sitemap.xml")
BRIEF_IMAGES_REL = Path("assets/images/home-briefing")
APPLE_PARK_FALLBACK_REL = Path("assets/images/hero-2026-03/Apple-Park-Rainbow-Arches.jpg")
BRIEF_HISTORY_REL = Path("assets/data/product-pulse")
BRIEF_HISTORY_MANIFEST_REL = BRIEF_HISTORY_REL / "history.json"
DEFAULT_LOG_DIR_REL = Path("output/home-brief-logs")
SECTION_START = "<!-- va-today-brief:start -->"
SECTION_END = "<!-- va-today-brief:end -->"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
)
ASCII_REPLACEMENTS = (
    ("\u00a0", " "),
    ("\u00ae", "(R)"),
    ("\u2122", "(TM)"),
    ("\u20ac", "EUR"),
    ("\u2026", "..."),
    ("\u2018", "'"),
    ("\u2019", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2013", "-"),
    ("\u2014", "-"),
)
BRIEF_STAMP_RE = re.compile(
    r'va-briefing-stamp">Updated daily 08:30 <span aria-hidden="true">\|</span> ([A-Za-z]+ \d{1,2}, \d{4}) at',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FeedItem:
    title: str
    link: str
    summary: str
    published_at: datetime | None
    image_url: str


@dataclass(frozen=True)
class BriefSource:
    slug: str
    eyebrow: str
    source_name: str
    source_url: str
    feed_url: str
    keywords: tuple[str, ...]
    fallback_image: str
    item_count: int


BRIEF_SOURCES: tuple[BriefSource, ...] = (
    BriefSource(
        slug="apple",
        eyebrow="Apple Releases",
        source_name="Apple Newsroom",
        source_url="https://www.apple.com/newsroom/",
        feed_url="https://www.apple.com/newsroom/rss-feed.rss",
        keywords=("iphone", "ipad", "mac", "macbook", "airpods", "watch", "vision", "ios", "m5", "neo", "pro"),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=1,
    ),
    BriefSource(
        slug="apple",
        eyebrow="Apple Releases",
        source_name="MacRumors",
        source_url="https://www.macrumors.com/",
        feed_url="https://www.macrumors.com/macrumors.xml",
        keywords=("apple", "iphone", "ipad", "mac", "macbook", "neo", "air", "pro", "studio display"),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="apple",
        eyebrow="Apple Releases",
        source_name="AppleInsider",
        source_url="https://appleinsider.com/",
        feed_url="https://appleinsider.com/rss/news/",
        keywords=("apple", "iphone", "ipad", "mac", "macbook", "neo", "air", "pro", "vision"),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="apple",
        eyebrow="Apple Releases",
        source_name="MacStories",
        source_url="https://www.macstories.net/",
        feed_url="https://www.macstories.net/feed/",
        keywords=("apple", "iphone", "ipad", "mac", "macbook", "app", "ios", "ipados", "automation", "shortcuts"),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=1,
    ),
    BriefSource(
        slug="apple",
        eyebrow="Apple Releases",
        source_name="9to5Mac",
        source_url="https://9to5mac.com/",
        feed_url="https://9to5mac.com/feed/",
        keywords=("apple", "iphone", "ipad", "mac", "macbook", "app store", "apple tv", "neo", "fold"),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="apple",
        eyebrow="Apple Releases",
        source_name="Cult of Mac",
        source_url="https://www.cultofmac.com/",
        feed_url="https://www.cultofmac.com/feed/",
        keywords=("apple", "iphone", "ipad", "mac", "macbook", "airpods", "ios", "vision", "apple tv", "airpods max"),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="semiconductor",
        eyebrow="Semiconductor Breakthroughs",
        source_name="Semiconductor Engineering",
        source_url="https://semiengineering.com/",
        feed_url="https://semiengineering.com/feed/",
        keywords=(
            "chip",
            "semiconductor",
            "yield",
            "nanosheet",
            "packaging",
            "nand",
            "memory",
            "fab",
            "transistor",
            "radar",
            "lithography",
            "breakthrough",
        ),
        fallback_image="/assets/images/stock-2026-03-extra20/stock-extra-14.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="semiconductor",
        eyebrow="Semiconductor Breakthroughs",
        source_name="SemiWiki",
        source_url="https://semiwiki.com/",
        feed_url="https://semiwiki.com/feed/",
        keywords=(
            "chip",
            "chiplet",
            "semiconductor",
            "foundry",
            "verification",
            "silicon",
            "noc",
            "design",
            "synopsys",
            "data wave",
        ),
        fallback_image="/assets/images/stock-2026-03-extra20/stock-extra-11.jpg",
        item_count=1,
    ),
    BriefSource(
        slug="semiconductor",
        eyebrow="Semiconductor Breakthroughs",
        source_name="NVIDIA Newsroom",
        source_url="https://nvidianews.nvidia.com/",
        feed_url="https://nvidianews.nvidia.com/releases.xml",
        keywords=(
            "nvidia",
            "jensen",
            "gpu",
            "blackwell",
            "nemotron",
            "gtc",
            "dgx",
            "grace",
            "omniverse",
            "ai chip",
            "server",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-07.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="semiconductor",
        eyebrow="Semiconductor Breakthroughs",
        source_name="NVIDIA Blog",
        source_url="https://blogs.nvidia.com/",
        feed_url="https://blogs.nvidia.com/feed/",
        keywords=(
            "nvidia",
            "jensen",
            "gpu",
            "blackwell",
            "gtc",
            "grace",
            "rtx",
            "dgx",
            "ai factory",
            "physical ai",
            "server",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-07.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="ai",
        eyebrow="AI Developments",
        source_name="OpenAI News",
        source_url="https://openai.com/news/",
        feed_url="https://openai.com/news/rss.xml",
        keywords=(
            "ai",
            "model",
            "chatgpt",
            "reasoning",
            "multimodal",
            "agent",
            "coding",
            "science",
            "research",
            "instruction",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=1,
    ),
    BriefSource(
        slug="ai",
        eyebrow="AI Developments",
        source_name="MIT Technology Review",
        source_url="https://www.technologyreview.com/",
        feed_url="https://www.technologyreview.com/feed/",
        keywords=(
            "ai",
            "model",
            "agent",
            "chip",
            "semiconductor",
            "robot",
            "physical ai",
            "nvidia",
            "targeting",
            "military",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=1,
    ),
    BriefSource(
        slug="ai",
        eyebrow="AI Developments",
        source_name="Tom's Hardware",
        source_url="https://www.tomshardware.com/",
        feed_url="https://www.tomshardware.com/feeds/all",
        keywords=(
            "ai",
            "agent",
            "llm",
            "model",
            "chatgpt",
            "gemini",
            "gpu",
            "inference",
            "training",
            "reasoning",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=1,
    ),
    BriefSource(
        slug="industry",
        eyebrow="Industry Product Watch",
        source_name="Electrek",
        source_url="https://electrek.co/",
        feed_url="https://electrek.co/feed/",
        keywords=(
            "tesla",
            "musk",
            "robot",
            "humanoid",
            "optimus",
            "ev",
            "battery",
            "robotaxi",
            "xai",
            "energy",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-10.jpg",
        item_count=1,
    ),
    BriefSource(
        slug="industry",
        eyebrow="Industry Product Watch",
        source_name="TechCrunch",
        source_url="https://techcrunch.com/",
        feed_url="https://techcrunch.com/feed/",
        keywords=(
            "nvidia",
            "jensen",
            "musk",
            "tesla",
            "xai",
            "grok",
            "apple",
            "ai",
            "robot",
            "chip",
            "device",
            "hardware",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-10.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="bluetooth",
        eyebrow="Bluetooth Standards & Uses",
        source_name="Bluetooth SIG",
        source_url="https://www.bluetooth.com/blog/",
        feed_url="https://www.bluetooth.com/blog/feed/",
        keywords=(
            "bluetooth core",
            "auracast",
            "connection intervals",
            "channel sounding",
            "industrial",
            "tracking",
            "monitoring",
            "audio",
            "standard",
            "innovation",
            "application",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-06.jpg",
        item_count=1,
    ),
    BriefSource(
        slug="bluetooth",
        eyebrow="Bluetooth Standards & Uses",
        source_name="Nordic News",
        source_url="https://www.nordicsemi.com/Nordic-news",
        feed_url="https://www.nordicsemi.com/RSS?contentType=News",
        keywords=(
            "bluetooth",
            "ble",
            "le audio",
            "direction finding",
            "find my",
            "tracking",
            "nrf connect",
            "gatt",
            "wireless",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-06.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="bluetooth",
        eyebrow="Bluetooth Standards & Uses",
        source_name="Nordic GetConnected",
        source_url="https://blog.nordicsemi.com/getconnected",
        feed_url="https://blog.nordicsemi.com/getconnected/rss.xml",
        keywords=(
            "bluetooth",
            "ble",
            "le audio",
            "direction finding",
            "find my",
            "tracking",
            "nrf connect",
            "gatt",
            "wireless",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-06.jpg",
        item_count=2,
    ),
)

EXTRA_SAME_DAY_SOURCES: tuple[BriefSource, ...] = (
    BriefSource(
        slug="apple",
        eyebrow="Apple Releases",
        source_name="Ars Technica Apple",
        source_url="https://arstechnica.com/apple/",
        feed_url="https://feeds.arstechnica.com/arstechnica/apple",
        keywords=("apple", "iphone", "ipad", "mac", "macbook", "airpods", "ios", "vision", "apple tv"),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="apple",
        eyebrow="Apple Releases",
        source_name="Apple World Today",
        source_url="https://appleworld.today/",
        feed_url="https://appleworld.today/feed/",
        keywords=("apple", "iphone", "ipad", "mac", "macbook", "airpods", "ios", "watch", "vision"),
        fallback_image="/assets/images/stock-2026-03/stock-08.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="industry",
        eyebrow="Industry Product Watch",
        source_name="Samsung Global Newsroom",
        source_url="https://news.samsung.com/global",
        feed_url="https://news.samsung.com/global/feed",
        keywords=("samsung", "galaxy", "display", "chip", "ai", "device", "buds", "tv", "phone", "monitor"),
        fallback_image="/assets/images/stock-2026-03/stock-10.jpg",
        item_count=2,
    ),
)

MEDIA_NS = {
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}
APPLE_PARK_FALLBACK = "/" + APPLE_PARK_FALLBACK_REL.as_posix()
FALLBACK_THEME_MAP: dict[str, tuple[str, ...]] = {
    "apple": ("apple",),
    "ai": ("ai",),
    "industry": ("industry",),
    "bluetooth": ("bluetooth",),
    "semiconductor": ("semiconductor",),
}
SCREENSHOT_NAME_PARTS = (
    "screenshot",
    "screen-shot",
    "screen_shot",
    "screen capture",
    "screen-capture",
    "screen_capture",
)
DARK_IMAGE_BRIGHTNESS_THRESHOLD = 56.0
MIN_BRIEF_ITEMS = 10
RECENT_BACKFILL_DAYS = 7
MIN_SAME_DAY_ITEMS = 8
BRIEF_HISTORY_KEEP_DAYS = 90
SLUG_MAX_COUNTS = {
    "apple": 5,
}
SLUG_MIN_COUNTS = {
    "apple": 4,
    "semiconductor": 1,
    "industry": 1,
    "ai": 1,
    "bluetooth": 1,
}
SLUG_PRIORITY_ORDER = ("apple", "semiconductor", "industry", "ai", "bluetooth")


@dataclass(frozen=True)
class BriefEntry:
    index: int
    source: BriefSource
    item: FeedItem


@dataclass(frozen=True)
class CandidateEntry:
    phase: int
    source: BriefSource
    item: FeedItem


@dataclass(frozen=True)
class RenderEntry:
    entry: BriefEntry
    image_src: str
    fallback_src: str


IMAGE_HEALTH_CACHE: dict[str, bool] = {}
HOME_BRIEFING_IMAGE_POOL_CACHE: dict[str, dict[str, list[str]]] = {}
FORCED_FALLBACK_IMAGE_HOSTS = {
    "photos5.appleinsider.com",
    "i0.wp.com",
}


def fetch_bytes(url: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(3):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - network variability
            last_error = exc
            if attempt >= 2:
                break
            time.sleep(1.2 * (attempt + 1))
    assert last_error is not None
    raise last_error


def fetch_url(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> tuple[bytes, dict[str, str], str]:
    merged_headers = {"User-Agent": USER_AGENT}
    if headers:
        merged_headers.update(headers)

    last_error: Exception | None = None
    for attempt in range(3):
        request = urllib.request.Request(url, headers=merged_headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
                response_headers = {key.lower(): value for key, value in response.headers.items()}
                return payload, response_headers, response.geturl()
        except Exception as exc:  # pragma: no cover - network variability
            last_error = exc
            if attempt >= 2:
                break
            time.sleep(1.2 * (attempt + 1))

    assert last_error is not None
    raise last_error


def clean_text(value: str) -> str:
    text = unescape(value or "")
    for old, new in ASCII_REPLACEMENTS:
        text = text.replace(old, new)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+more[^a-z0-9]*$", "", text, flags=re.IGNORECASE)
    return text.strip()


def clip_text(value: str, limit: int = 210) -> str:
    cleaned = clean_text(value)
    if len(cleaned) <= limit:
        return cleaned
    trimmed = cleaned[:limit].rsplit(" ", 1)[0].strip()
    return f"{trimmed}..."


def parse_datetime(value: str) -> datetime | None:
    raw = clean_text(value)
    if not raw:
        return None

    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
        except ValueError:
            continue

    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)


def extract_image_url(node: ET.Element) -> str:
    media_thumbnail = node.find("media:thumbnail", MEDIA_NS)
    if media_thumbnail is not None and media_thumbnail.attrib.get("url"):
        return media_thumbnail.attrib["url"].strip()

    media_content = node.find("media:content", MEDIA_NS)
    if media_content is not None and media_content.attrib.get("url"):
        return media_content.attrib["url"].strip()

    for child in list(node):
        if not child.tag.endswith("link"):
            continue
        rel = (child.attrib.get("rel") or "").strip().lower()
        href = (child.attrib.get("href") or "").strip()
        media_type = (child.attrib.get("type") or "").strip().lower()
        if href and rel == "enclosure" and (not media_type or media_type.startswith("image/")):
            return href

    enclosure = node.find("enclosure")
    if enclosure is not None:
        url = (enclosure.attrib.get("url") or "").strip()
        media_type = (enclosure.attrib.get("type") or "").strip().lower()
        if url and (not media_type or media_type.startswith("image/")):
            return url

    encoded = node.findtext("content:encoded", default="", namespaces=MEDIA_NS)
    joined_text = " ".join(
        filter(
            None,
            [
                encoded,
                node.findtext("description", default=""),
                node.findtext("content", default=""),
            ],
        )
    )
    match = re.search(r"""https?://[^"' >]+?\.(?:jpg|jpeg|png|webp)(?:\?[^"' >]+)?""", joined_text, flags=re.IGNORECASE)
    if match:
        return match.group(0)

    return ""


def parse_feed_items(xml_bytes: bytes) -> list[FeedItem]:
    root = ET.fromstring(xml_bytes)
    items: list[FeedItem] = []

    if root.tag.endswith("feed"):
        for entry in root.findall("atom:entry", ATOM_NS):
            link_url = ""
            for link_node in entry.findall("atom:link", ATOM_NS):
                rel = (link_node.attrib.get("rel") or "alternate").strip().lower()
                href = (link_node.attrib.get("href") or "").strip()
                if not href:
                    continue
                if rel == "enclosure":
                    continue
                link_url = href
                break

            items.append(
                FeedItem(
                    title=clean_text(entry.findtext("atom:title", default="", namespaces=ATOM_NS)),
                    link=link_url,
                    summary=clean_text(
                        entry.findtext("atom:summary", default="", namespaces=ATOM_NS)
                        or entry.findtext("atom:content", default="", namespaces=ATOM_NS)
                    ),
                    published_at=parse_datetime(
                        entry.findtext("atom:updated", default="", namespaces=ATOM_NS)
                        or entry.findtext("atom:published", default="", namespaces=ATOM_NS)
                    ),
                    image_url=extract_image_url(entry),
                )
            )
        return [item for item in items if item.title and item.link]

    for node in root.findall(".//item"):
        items.append(
            FeedItem(
                title=clean_text(node.findtext("title", default="")),
                link=clean_text(node.findtext("link", default="")),
                summary=clean_text(node.findtext("description", default="")),
                published_at=parse_datetime(node.findtext("pubDate", default="")),
                image_url=extract_image_url(node),
            )
        )
    return [item for item in items if item.title and item.link]


def score_item(item: FeedItem, keywords: tuple[str, ...]) -> int:
    haystack = f"{item.title} {item.summary} {item.link}".lower()
    keyword_score = 0
    for keyword in keywords:
        lowered = keyword.lower()
        if re.search(r"[a-z0-9]", lowered) and " " not in lowered:
            pattern = rf"(?<![a-z0-9]){re.escape(lowered)}(?![a-z0-9])"
            matched = re.search(pattern, haystack) is not None
        else:
            matched = lowered in haystack
        if matched:
            keyword_score += 1

    if ":" in item.title:
        keyword_score -= 1
    if "writes the" in haystack or "editor" in haystack or "analysis" in haystack or "opinion" in haystack:
        keyword_score -= 1

    return keyword_score


def select_item(items: list[FeedItem], keywords: tuple[str, ...]) -> FeedItem:
    if not items:
        raise ValueError("Feed returned no usable items.")
    ranked = max(
        enumerate(items),
        key=lambda pair: (
            pair[1].published_at.timestamp() if pair[1].published_at else 0.0,
            score_item(pair[1], keywords),
            -pair[0],
        ),
    )
    return ranked[1]


def select_items(items: list[FeedItem], keywords: tuple[str, ...], limit: int) -> list[FeedItem]:
    if limit <= 0:
        return []
    ranked = sorted(
        enumerate(items),
        key=lambda pair: (
            pair[1].published_at.timestamp() if pair[1].published_at else 0.0,
            score_item(pair[1], keywords),
            -pair[0],
        ),
        reverse=True,
    )
    selected: list[FeedItem] = []
    seen_links: set[str] = set()
    for _, item in ranked:
        if score_item(item, keywords) <= 0:
            continue
        if item.link in seen_links:
            continue
        selected.append(item)
        seen_links.add(item.link)
        if len(selected) >= limit:
            break
    return selected


def format_card_date(value: datetime | None) -> str:
    if value is None:
        return "LATEST"
    return value.astimezone().strftime("%b %d").upper()


def format_refresh_time(value: datetime) -> str:
    local = value.astimezone()
    offset = local.strftime("%z")
    pretty_offset = f"UTC{offset[:3]}:{offset[3:]}" if offset else "Local time"
    return f"{local.strftime('%B %d, %Y at %H:%M')} ({pretty_offset})"


def is_same_local_day(value: datetime | None, target_day: date) -> bool:
    if value is None:
        return False
    return value.astimezone().date() == target_day


def is_within_recent_window(value: datetime | None, target_day: date, days: int) -> bool:
    if value is None:
        return False
    local_day = value.astimezone().date()
    oldest_day = target_day - timedelta(days=max(days - 1, 0))
    return oldest_day <= local_day <= target_day


def is_screenshot_like_path(path: Path) -> bool:
    lowered = path.name.lower()
    return any(part in lowered for part in SCREENSHOT_NAME_PARTS)


def is_dark_image(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            grayscale = image.convert("L")
            stat = ImageStat.Stat(grayscale)
            brightness = float(stat.mean[0]) if stat.mean else 0.0
            return brightness < DARK_IMAGE_BRIGHTNESS_THRESHOLD
    except Exception:
        return True


def is_dark_image_bytes(payload: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(payload)) as image:
            grayscale = image.convert("L")
            stat = ImageStat.Stat(grayscale)
            brightness = float(stat.mean[0]) if stat.mean else 0.0
            return brightness < DARK_IMAGE_BRIGHTNESS_THRESHOLD
    except Exception:
        return True


def collect_home_briefing_fallbacks(repo_root: Path) -> dict[str, list[str]]:
    cache_key = str(repo_root.resolve())
    cached = HOME_BRIEFING_IMAGE_POOL_CACHE.get(cache_key)
    if cached is not None:
        return {key: list(value) for key, value in cached.items()}

    pools: dict[str, list[str]] = {}
    root = repo_root / BRIEF_IMAGES_REL
    if root.exists():
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}:
                continue
            if is_screenshot_like_path(path) or is_dark_image(path):
                continue
            theme_key = path.name.split("-", 1)[0].lower()
            pools.setdefault(theme_key, []).append("/" + path.relative_to(repo_root).as_posix())

    HOME_BRIEFING_IMAGE_POOL_CACHE[cache_key] = {key: list(value) for key, value in pools.items()}
    return {key: list(value) for key, value in pools.items()}


def pick_fallback_image(repo_root: Path, item: FeedItem, source: BriefSource) -> str:
    pools = collect_home_briefing_fallbacks(repo_root)
    theme_keys = FALLBACK_THEME_MAP.get(source.slug, (source.slug,))
    candidates: list[str] = []

    for theme_key in theme_keys:
        candidates.extend(pools.get(theme_key, []))

    if not candidates:
        for values in pools.values():
            candidates.extend(values)

    if not candidates:
        return APPLE_PARK_FALLBACK

    seed = f"{source.slug}|{item.link}|{item.title}".encode("utf-8", errors="ignore")
    digest = hashlib.sha1(seed).hexdigest()
    index = int(digest[:8], 16) % len(candidates)
    return candidates[index]


def candidate_sort_key(candidate: CandidateEntry) -> tuple[int, float, int]:
    published_ts = candidate.item.published_at.timestamp() if candidate.item.published_at else 0.0
    relevance = score_item(candidate.item, candidate.source.keywords)
    return (candidate.phase, -published_ts, -relevance)


def choose_balanced_entries(candidates: list[CandidateEntry]) -> list[tuple[BriefSource, FeedItem]]:
    ranked = sorted(candidates, key=candidate_sort_key)
    selected: list[tuple[BriefSource, FeedItem]] = []
    seen_links: set[str] = set()
    slug_counts: dict[str, int] = {}

    def can_take(candidate: CandidateEntry, enforce_caps: bool = True) -> bool:
        if candidate.item.link in seen_links:
            return False
        if not enforce_caps:
            return True
        limit = SLUG_MAX_COUNTS.get(candidate.source.slug)
        if limit is None:
            return True
        return slug_counts.get(candidate.source.slug, 0) < limit

    def take(candidate: CandidateEntry) -> None:
        selected.append((candidate.source, candidate.item))
        seen_links.add(candidate.item.link)
        slug_counts[candidate.source.slug] = slug_counts.get(candidate.source.slug, 0) + 1

    for slug in SLUG_PRIORITY_ORDER:
        minimum = SLUG_MIN_COUNTS.get(slug, 0)
        if minimum <= 0:
            continue
        for candidate in ranked:
            if candidate.source.slug != slug:
                continue
            if slug_counts.get(slug, 0) >= minimum:
                break
            if not can_take(candidate, enforce_caps=True):
                continue
            take(candidate)

    for candidate in ranked:
        if len(selected) >= MIN_BRIEF_ITEMS:
            break
        if not can_take(candidate, enforce_caps=True):
            continue
        take(candidate)

    if len(selected) < MIN_BRIEF_ITEMS:
        for candidate in ranked:
            if len(selected) >= MIN_BRIEF_ITEMS:
                break
            if not can_take(candidate, enforce_caps=False):
                continue
            take(candidate)

    return selected[:MIN_BRIEF_ITEMS]


def collect_source_items(sources: tuple[BriefSource, ...]) -> list[tuple[BriefSource, list[FeedItem]]]:
    collected: list[tuple[BriefSource, list[FeedItem]]] = []
    for source in sources:
        try:
            items = parse_feed_items(fetch_bytes(source.feed_url))
        except Exception as exc:  # pragma: no cover - network/source variability
            print(f"skip_source source={source.source_name} error={exc}", file=sys.stderr)
            continue
        collected.append((source, items))
    return collected


def extend_candidate_pool(
    candidate_pool: list[CandidateEntry],
    source_items_map: list[tuple[BriefSource, list[FeedItem]]],
    target_day: date,
) -> None:
    for source, items in source_items_map:
        same_day_items = [item for item in items if is_same_local_day(item.published_at, target_day)]
        for item in select_items(same_day_items, source.keywords, max(source.item_count * 3, MIN_BRIEF_ITEMS)):
            candidate_pool.append(CandidateEntry(phase=0, source=source, item=item))

    for source, items in source_items_map:
        recent_items = [
            item
            for item in items
            if is_within_recent_window(item.published_at, target_day, RECENT_BACKFILL_DAYS)
        ]
        for item in select_items(recent_items, source.keywords, max(source.item_count * 4, MIN_BRIEF_ITEMS)):
            candidate_pool.append(CandidateEntry(phase=1, source=source, item=item))

    for source, items in source_items_map:
        for item in select_items(items, source.keywords, max(source.item_count * 6, MIN_BRIEF_ITEMS)):
            candidate_pool.append(CandidateEntry(phase=2, source=source, item=item))


def enforce_min_same_day_entries(
    selected_entries: list[tuple[BriefSource, FeedItem]],
    candidates: list[CandidateEntry],
    target_day: date,
) -> list[tuple[BriefSource, FeedItem]]:
    same_day_count = sum(1 for _, item in selected_entries if is_same_local_day(item.published_at, target_day))
    if same_day_count >= MIN_SAME_DAY_ITEMS:
        return selected_entries

    selected_links = {item.link for _, item in selected_entries}
    slug_counts = Counter(source.slug for source, _ in selected_entries)

    ranked_same_day_candidates = sorted(
        [candidate for candidate in candidates if is_same_local_day(candidate.item.published_at, target_day)],
        key=candidate_sort_key,
    )

    def replacement_index() -> int | None:
        best_index: int | None = None
        best_key: tuple[int, float] | None = None
        for idx, (source, item) in enumerate(selected_entries):
            if is_same_local_day(item.published_at, target_day):
                continue
            minimum = SLUG_MIN_COUNTS.get(source.slug, 0)
            replace_score = 1 if slug_counts.get(source.slug, 0) > minimum else 0
            published_ts = item.published_at.timestamp() if item.published_at else 0.0
            key = (replace_score, -published_ts)
            if best_key is None or key > best_key:
                best_key = key
                best_index = idx
        return best_index

    for candidate in ranked_same_day_candidates:
        if same_day_count >= MIN_SAME_DAY_ITEMS:
            break
        if candidate.item.link in selected_links:
            continue

        idx = replacement_index()
        if idx is None:
            break

        old_source, old_item = selected_entries[idx]
        slug_counts[old_source.slug] = max(0, slug_counts.get(old_source.slug, 0) - 1)
        selected_links.discard(old_item.link)

        selected_entries[idx] = (candidate.source, candidate.item)
        slug_counts[candidate.source.slug] = slug_counts.get(candidate.source.slug, 0) + 1
        selected_links.add(candidate.item.link)
        same_day_count += 1

    return selected_entries


def normalize_image_url(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("http://"):
        return "https://" + cleaned[len("http://") :]
    return cleaned


def extract_image_host(url: str) -> str:
    cleaned = normalize_image_url(url)
    if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
        return ""
    return urllib.parse.urlparse(cleaned).netloc.lower()


def derive_image_extension(content_type: str, final_url: str, image_bytes: bytes) -> str:
    lowered_type = (content_type or "").lower()
    if "jpeg" in lowered_type or "jpg" in lowered_type:
        return ".jpg"
    if "png" in lowered_type:
        return ".png"
    if "webp" in lowered_type:
        return ".webp"
    if "gif" in lowered_type:
        return ".gif"
    if "avif" in lowered_type:
        return ".avif"

    path = urllib.parse.urlparse(final_url or "").path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext

    header = image_bytes[:16]
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return ".webp"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand in {b"avif", b"avis"}:
            return ".avif"
    return ".jpg"


def extract_page_meta_image(article_url: str) -> str:
    article = normalize_image_url(article_url)
    if not article.startswith("https://"):
        return ""
    try:
        payload, _, final_url = fetch_url(
            article,
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            timeout=20,
        )
    except Exception:
        return ""

    html = payload.decode("utf-8", errors="replace")
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+property=["\']og:image:url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']',
        r'<img[^>]+src=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = normalize_image_url(urllib.parse.urljoin(final_url, match.group(1).strip()))
        if candidate:
            return candidate
    return ""


def download_image_to_repo(
    repo_root: Path,
    source: BriefSource,
    item: FeedItem,
    image_url: str,
    target_day: date,
) -> tuple[str, str] | None:
    candidate = normalize_image_url(image_url)
    if not candidate or candidate.startswith("/"):
        return None
    if extract_image_host(candidate) in FORCED_FALLBACK_IMAGE_HOSTS:
        return None
    parsed_path_name = Path(urllib.parse.urlparse(candidate).path).name
    if parsed_path_name and is_screenshot_like_path(Path(parsed_path_name)):
        return None

    try:
        payload, headers, final_url = fetch_url(
            candidate,
            headers={
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": item.link,
            },
            timeout=20,
        )
    except Exception:
        return None

    content_type = (headers.get("content-type") or "").lower()
    if not content_type.startswith("image/"):
        return None
    if len(payload) < 256:
        return None
    final_name = Path(urllib.parse.urlparse(final_url or candidate).path).name
    if final_name and is_screenshot_like_path(Path(final_name)):
        return None
    if is_dark_image_bytes(payload):
        return None

    day_folder = BRIEF_IMAGES_REL / target_day.isoformat()
    target_dir = repo_root / day_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha1(f"{source.slug}|{item.link}|{candidate}".encode("utf-8", errors="ignore")).hexdigest()[:16]
    extension = derive_image_extension(content_type, final_url, payload)
    filename = f"{source.slug}-{digest}{extension}"
    target_path = target_dir / filename
    target_path.write_bytes(payload)
    return ("/" + (day_folder / filename).as_posix(), (day_folder / filename).as_posix())


def is_image_url_healthy(url: str) -> bool:
    cleaned = normalize_image_url(url)
    if not cleaned:
        return False
    if cleaned.startswith("/"):
        return True
    if extract_image_host(cleaned) in FORCED_FALLBACK_IMAGE_HOSTS:
        IMAGE_HEALTH_CACHE[cleaned] = False
        return False
    cached = IMAGE_HEALTH_CACHE.get(cleaned)
    if cached is not None:
        return cached

    request = urllib.request.Request(
        cleaned,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Range": "bytes=0-2048",
        },
    )
    healthy = False
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            healthy = response.status < 400 and content_type.startswith("image/")
    except Exception:
        healthy = False

    IMAGE_HEALTH_CACHE[cleaned] = healthy
    return healthy


def resolve_story_image_url(repo_root: Path, item: FeedItem, source: BriefSource) -> tuple[str, str]:
    fallback_image = pick_fallback_image(repo_root, item, source)
    primary_image = normalize_image_url(item.image_url)
    if primary_image and is_image_url_healthy(primary_image):
        return primary_image, fallback_image
    return fallback_image, fallback_image


def prepare_render_entries(
    repo_root: Path,
    entries: list[BriefEntry],
    target_day: date,
) -> tuple[list[RenderEntry], list[str]]:
    rendered: list[RenderEntry] = []
    asset_paths: list[str] = []

    for entry in entries:
        source = entry.source
        item = entry.item
        fallback_image = pick_fallback_image(repo_root, item, source)

        image_src = fallback_image
        attempted_urls = [
            normalize_image_url(item.image_url),
            extract_page_meta_image(item.link),
        ]
        for candidate in attempted_urls:
            if not candidate:
                continue
            downloaded = download_image_to_repo(repo_root, source, item, candidate, target_day)
            if downloaded:
                image_src, relative_path = downloaded
                asset_paths.append(relative_path)
                break

        rendered.append(RenderEntry(entry=entry, image_src=image_src, fallback_src=fallback_image))

    unique_asset_paths = list(dict.fromkeys(asset_paths))
    return rendered, unique_asset_paths


def render_entry(render_entry_item: RenderEntry) -> str:
    entry = render_entry_item.entry
    source = entry.source
    item = entry.item
    image_url = render_entry_item.image_src
    fallback_image = render_entry_item.fallback_src
    image_alt = f"{item.title} thumbnail"
    return f"""      <article class="va-brief-item va-brief-item-{escape(source.slug)}">
        <div class="va-brief-index" aria-hidden="true">{entry.index}</div>
        <div class="va-brief-body">
          <p class="va-brief-label">{escape(source.eyebrow)}</p>
          <h3><a href="{escape(item.link)}" target="_blank" rel="noopener noreferrer">{escape(item.title)}</a></h3>
          <p class="va-brief-summary">{escape(clip_text(item.summary or item.title, limit=168))}</p>
          <p class="va-brief-meta"><span class="va-brief-source">{escape(source.source_name)}</span> <span aria-hidden="true">|</span> {escape(format_card_date(item.published_at))}</p>
        </div>
        <a class="va-brief-thumb" href="{escape(item.link)}" target="_blank" rel="noopener noreferrer" aria-label="Open story: {escape(item.title)}">
          <img src="{escape(image_url)}" alt="{escape(image_alt)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-fallback-src="{escape(fallback_image)}" onerror="if(this.dataset.fallbackSrc && this.src !== this.dataset.fallbackSrc){{this.src=this.dataset.fallbackSrc;}}this.onerror=null;">
        </a>
      </article>"""


def render_column(entries: list[RenderEntry]) -> str:
    return "\n".join(render_entry(entry) for entry in entries)


def build_section_html(entries: list[RenderEntry], refreshed_at: datetime) -> str:
    midpoint = (len(entries) + 1) // 2
    left_column = entries[:midpoint]
    right_column = entries[midpoint:]
    empty_state = ""
    if not entries:
        empty_state = """
      <div class="va-briefing-empty">
        <p>Today's publisher-matched stories will appear here as soon as the tracked sources publish same-day updates.</p>
      </div>"""
    display_date = escape(refreshed_at.strftime("%B %d, %Y"))
    default_date = refreshed_at.date().isoformat()
    return f"""
    <div class="va-briefing-head" hidden>
      <div class="va-briefing-title-wrap">
        <p class="va-briefing-section-label">Top Stories</p>
        <h2 class="va-briefing-heading">Product <span class="is-accent">Pulse</span></h2>
      </div>
      <p class="va-briefing-stamp">Updated daily 08:30 <span aria-hidden="true">|</span> {escape(format_refresh_time(refreshed_at))}</p>
    </div>
    <div class="va-briefing-controls" data-product-pulse-controls hidden>
      <div class="va-briefing-history-copy">
        <p class="va-briefing-history-label">History Browser</p>
        <div class="va-briefing-history-status" data-product-pulse-status>
          Viewing {display_date}'s stored briefing.
        </div>
      </div>
      <div class="va-briefing-history-picker" data-briefing-calendar>
        <span>View date</span>
        <button
          class="va-briefing-history-trigger"
          type="button"
          aria-expanded="false"
          aria-haspopup="dialog"
          data-briefing-calendar-trigger
        >
          <span data-briefing-calendar-trigger-label>{display_date}</span>
          <span aria-hidden="true">▾</span>
        </button>
        <div class="va-briefing-calendar" data-briefing-calendar-panel hidden>
          <div class="va-briefing-calendar-head">
            <button
              class="va-briefing-calendar-nav"
              type="button"
              aria-label="Show previous month"
              data-briefing-calendar-prev
            >
              ‹
            </button>
            <div class="va-briefing-calendar-head-selectors">
              <label class="va-briefing-calendar-select-wrap">
                <span class="va-visually-hidden">Choose month</span>
                <select class="va-briefing-calendar-select" data-briefing-calendar-month aria-label="Choose month"></select>
              </label>
              <label class="va-briefing-calendar-select-wrap">
                <span class="va-visually-hidden">Choose year</span>
                <select class="va-briefing-calendar-select" data-briefing-calendar-year aria-label="Choose year"></select>
              </label>
            </div>
            <button
              class="va-briefing-calendar-nav"
              type="button"
              aria-label="Show next month"
              data-briefing-calendar-next
            >
              ›
            </button>
          </div>
          <div class="va-briefing-calendar-weekdays" aria-hidden="true">
            <span>Su</span>
            <span>Mo</span>
            <span>Tu</span>
            <span>We</span>
            <span>Th</span>
            <span>Fr</span>
            <span>Sa</span>
          </div>
          <div class="va-briefing-calendar-grid" data-briefing-calendar-grid></div>
        </div>
        <select
          id="va-product-pulse-date"
          name="product-pulse-date"
          data-product-pulse-select
          data-history-manifest="/{BRIEF_HISTORY_MANIFEST_REL.as_posix()}"
          data-default-date="{default_date}"
          aria-label="Choose a Product Pulse date"
          hidden
        >
          <option value="{default_date}">{display_date}</option>
        </select>
      </div>
    </div>
    <div class="va-briefing-panel" data-product-pulse-panel>
{empty_state}
      <div class="va-briefing-grid">
        <div class="va-briefing-column">
{render_column(left_column)}
        </div>
        <div class="va-briefing-column">
{render_column(right_column)}
        </div>
      </div>
    </div>
"""


def replace_section(index_html: str, section_html: str) -> str:
    pattern = re.compile(
        rf"({re.escape(SECTION_START)})(.*)({re.escape(SECTION_END)})",
        flags=re.DOTALL,
    )
    match = pattern.search(index_html)
    if match is None:
        raise ValueError("Cannot find homepage briefing markers in index.html.")
    return index_html[: match.start(2)] + "\n" + section_html.strip("\n") + "\n  " + index_html[match.end(2) :]


def update_homepage(index_path: Path, section_html: str) -> bool:
    original = index_path.read_text(encoding="utf-8")
    updated = replace_section(original, section_html)
    if updated == original:
        return False
    index_path.write_text(updated, encoding="utf-8")
    return True


def serialize_render_entry(render_entry_item: RenderEntry) -> dict[str, object]:
    entry = render_entry_item.entry
    source = entry.source
    item = entry.item
    return {
        "index": entry.index,
        "slug": source.slug,
        "eyebrow": source.eyebrow,
        "source_name": source.source_name,
        "source_url": source.source_url,
        "title": item.title,
        "link": item.link,
        "summary": clip_text(item.summary or item.title, limit=240),
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "display_date": format_card_date(item.published_at),
        "image_src": render_entry_item.image_src,
        "fallback_src": render_entry_item.fallback_src,
    }


def collect_history_entries(history_dir: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    if not history_dir.exists():
        return entries

    for child in history_dir.glob("*.json"):
        if child.name == BRIEF_HISTORY_MANIFEST_REL.name:
            continue
        try:
            payload = json.loads(child.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        date_value = payload.get("date")
        if not isinstance(date_value, str):
            continue
        entries.append(
            {
                "date": date_value,
                "path": f"/{BRIEF_HISTORY_REL.as_posix()}/{child.name}",
                "item_count": int(payload.get("item_count", 0) or 0),
                "refreshed_at": payload.get("refreshed_at"),
            }
        )

    entries.sort(key=lambda entry: str(entry.get("date", "")), reverse=True)
    return entries


def update_history_manifest(repo_root: Path) -> str:
    history_dir = repo_root / BRIEF_HISTORY_REL
    history_dir.mkdir(parents=True, exist_ok=True)
    entries = collect_history_entries(history_dir)[:BRIEF_HISTORY_KEEP_DAYS]
    latest_date = entries[0]["date"] if entries else None
    latest_updated_at = entries[0].get("refreshed_at") if entries else None
    manifest_payload = {
        "latest_date": latest_date,
        "updated_at": latest_updated_at,
        "entries": entries,
    }
    manifest_path = repo_root / BRIEF_HISTORY_MANIFEST_REL
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return BRIEF_HISTORY_MANIFEST_REL.as_posix()


def write_brief_history_snapshot(
    repo_root: Path,
    entries: list[RenderEntry],
    refreshed_at: datetime,
) -> list[str]:
    history_dir = repo_root / BRIEF_HISTORY_REL
    history_dir.mkdir(parents=True, exist_ok=True)

    snapshot_rel = BRIEF_HISTORY_REL / f"{refreshed_at.date().isoformat()}.json"
    snapshot_path = repo_root / snapshot_rel
    snapshot_payload = {
        "date": refreshed_at.date().isoformat(),
        "refreshed_at": refreshed_at.isoformat(),
        "item_count": len(entries),
        "items": [serialize_render_entry(entry) for entry in entries],
    }
    snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_rel = update_history_manifest(repo_root)
    return [snapshot_rel.as_posix(), manifest_rel]


def extract_brief_section(index_html: str) -> str:
    pattern = re.compile(
        rf"{re.escape(SECTION_START)}(.*?){re.escape(SECTION_END)}",
        flags=re.DOTALL,
    )
    match = pattern.search(index_html)
    if match is None:
        raise ValueError("Cannot find homepage briefing markers in supplied index.html content.")
    return match.group(1)


def parse_archived_brief_snapshot(index_html: str) -> tuple[str, str | None, list[dict[str, object]]]:
    section_html = extract_brief_section(index_html)
    stamp_match = BRIEF_STAMP_RE.search(section_html)
    if stamp_match is None:
        raise ValueError("Cannot find briefing date stamp in archived homepage.")

    snapshot_date = datetime.strptime(stamp_match.group(1), "%B %d, %Y").date().isoformat()
    refreshed_match = re.search(
        r'va-briefing-stamp">Updated daily 08:30 <span aria-hidden="true">\|</span> ([A-Za-z]+ \d{1,2}, \d{4} at \d{2}:\d{2} \(UTC[+\-]\d{2}:\d{2}\))',
        section_html,
    )
    refreshed_label = refreshed_match.group(1) if refreshed_match else None

    items: list[dict[str, object]] = []
    article_blocks = re.findall(
        r'(<article class="va-brief-item va-brief-item-[^"]+">.*?</article>)',
        section_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for article_html in article_blocks:
        slug_match = re.search(r'va-brief-item-([^"\s]+)', article_html)
        index_match = re.search(r'<div class="va-brief-index" aria-hidden="true">(\d+)</div>', article_html)
        eyebrow_match = re.search(r'<p class="va-brief-label">(.*?)</p>', article_html, flags=re.DOTALL)
        title_match = re.search(r'<h3><a href="(.*?)"[^>]*>(.*?)</a></h3>', article_html, flags=re.DOTALL)
        summary_match = re.search(r'<p class="va-brief-summary">(.*?)</p>', article_html, flags=re.DOTALL)
        meta_match = re.search(
            r'<p class="va-brief-meta"><span class="va-brief-source">(.*?)</span> <span aria-hidden="true">\|</span> (.*?)</p>',
            article_html,
            flags=re.DOTALL,
        )
        image_match = re.search(
            r'<img src="(.*?)"[^>]*?(?:data-fallback-src="(.*?)")?[^>]*>',
            article_html,
            flags=re.DOTALL,
        )

        if not (slug_match and index_match and eyebrow_match and title_match and meta_match and image_match):
            continue

        image_src = image_match.group(1) or ""
        fallback_value = image_match.group(2) or image_src or ""
        clean_summary = clean_text(summary_match.group(1) if summary_match else "")
        items.append(
            {
                "index": int(index_match.group(1)),
                "slug": clean_text(slug_match.group(1)),
                "eyebrow": clean_text(eyebrow_match.group(1)),
                "source_name": clean_text(meta_match.group(1)),
                "source_url": "",
                "title": clean_text(title_match.group(2)),
                "link": unescape(title_match.group(1)),
                "summary": clean_summary,
                "published_at": None,
                "display_date": clean_text(meta_match.group(2)),
                "image_src": unescape(image_src),
                "fallback_src": unescape(fallback_value),
            }
        )

    if not items:
        raise ValueError("No briefing items found in archived homepage.")

    return snapshot_date, refreshed_label, items


def resolve_archived_refreshed_at(snapshot_date: str, refreshed_label: str | None) -> str:
    if not refreshed_label:
        return f"{snapshot_date}T08:30:00+08:00"
    match = re.match(
        r"([A-Za-z]+ \d{1,2}, \d{4}) at (\d{2}:\d{2}) \(UTC([+\-]\d{2}:\d{2})\)",
        refreshed_label,
    )
    if not match:
        return f"{snapshot_date}T08:30:00+08:00"
    day_label, time_label, offset = match.groups()
    parsed_day = datetime.strptime(day_label, "%B %d, %Y").date().isoformat()
    return f"{parsed_day}T{time_label}:00{offset}"


def git_show_file(repo_root: Path, git_command: str, ref: str, path: str) -> str:
    result = subprocess.run(
        [git_command, "show", f"{ref}:{path}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"git show failed for {ref}:{path}")
    return result.stdout


def git_show_file_bytes(repo_root: Path, git_command: str, ref: str, path: str) -> bytes:
    result = subprocess.run(
        [git_command, "show", f"{ref}:{path}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip() or f"git show failed for {ref}:{path}")
    return result.stdout


def restore_history_assets_from_commit(
    repo_root: Path,
    git_command: str,
    commit_ref: str,
    items: list[dict[str, object]],
    force: bool = False,
) -> list[str]:
    restored_paths: list[str] = []
    for item in items:
        image_src = item.get("image_src")
        if not isinstance(image_src, str) or not image_src.startswith("/assets/images/home-briefing/"):
            continue
        relative_path = image_src.lstrip("/")
        target_path = repo_root / relative_path
        if target_path.exists() and not force:
            continue
        try:
            payload = git_show_file_bytes(repo_root, git_command, commit_ref, relative_path)
        except ValueError:
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(payload)
        restored_paths.append(relative_path)
    return restored_paths


def backfill_history_from_git(repo_root: Path, force: bool = False) -> tuple[int, list[str]]:
    git_command = resolve_git_command()
    history_dir = repo_root / BRIEF_HISTORY_REL
    history_dir.mkdir(parents=True, exist_ok=True)

    log_result = run_git_command(
        repo_root,
        git_command,
        ["log", "--all", "--format=%H", "--", HOME_INDEX_REL.as_posix()],
    )
    commit_refs = [line.strip() for line in log_result.stdout.splitlines() if line.strip()]

    created = 0
    touched_paths: list[str] = []
    seen_dates: set[str] = set()

    for commit_ref in commit_refs:
        try:
            index_html = git_show_file(repo_root, git_command, commit_ref, HOME_INDEX_REL.as_posix())
            snapshot_date, refreshed_at, items = parse_archived_brief_snapshot(index_html)
        except ValueError:
            continue

        if snapshot_date in seen_dates:
            continue
        seen_dates.add(snapshot_date)

        snapshot_rel = BRIEF_HISTORY_REL / f"{snapshot_date}.json"
        snapshot_path = repo_root / snapshot_rel
        if snapshot_path.exists() and not force:
            continue

        payload = {
            "date": snapshot_date,
            "refreshed_at": resolve_archived_refreshed_at(snapshot_date, refreshed_at),
            "item_count": len(items),
            "items": items,
        }
        snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        touched_paths.append(snapshot_rel.as_posix())
        touched_paths.extend(restore_history_assets_from_commit(repo_root, git_command, commit_ref, items, force=force))
        created += 1

    manifest_rel = update_history_manifest(repo_root)
    touched_paths.append(manifest_rel)
    return created, list(dict.fromkeys(touched_paths))


def update_homepage_lastmod(sitemap_path: Path, target_day: date) -> bool:
    ET.register_namespace("", SITEMAP_NS["sm"])
    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    changed = False

    for node in root.findall("sm:url", SITEMAP_NS):
        loc = node.find("sm:loc", SITEMAP_NS)
        if loc is None or loc.text != f"{SITE_URL}/":
            continue
        lastmod = node.find("sm:lastmod", SITEMAP_NS)
        if lastmod is None:
            lastmod = ET.SubElement(node, f"{{{SITEMAP_NS['sm']}}}lastmod")
        iso_value = target_day.isoformat()
        if lastmod.text != iso_value:
            lastmod.text = iso_value
            changed = True
        break

    if not changed:
        return False

    ET.indent(tree, space="  ")
    tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)
    return True


def cleanup_old_brief_images(repo_root: Path, target_day: date, keep_days: int = BRIEF_HISTORY_KEEP_DAYS) -> bool:
    images_root = repo_root / BRIEF_IMAGES_REL
    if not images_root.exists():
        return False

    oldest_kept_day = target_day - timedelta(days=max(keep_days - 1, 0))
    changed = False

    for child in images_root.iterdir():
        if not child.is_dir():
            continue
        try:
            child_day = date.fromisoformat(child.name)
        except ValueError:
            continue
        if child_day >= oldest_kept_day:
            continue
        shutil.rmtree(child, ignore_errors=True)
        changed = True

    return changed


def resolve_log_dir(repo_root: Path, log_dir: Path | None) -> Path | None:
    if log_dir is None:
        return repo_root / DEFAULT_LOG_DIR_REL
    return log_dir if log_dir.is_absolute() else repo_root / log_dir


def write_log(log_dir: Path | None, message: str) -> None:
    if log_dir is None:
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    log_path = log_dir / f"{now.date().isoformat()}.log"
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S %z")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def extract_home_brief_date(index_path: Path) -> date | None:
    html = index_path.read_text(encoding="utf-8")
    match = re.search(
        r'va-briefing-stamp">Updated daily 08:30 <span aria-hidden="true">\|</span> ([A-Za-z]+ \d{1,2}, \d{4}) at',
        html,
    )
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%B %d, %Y").date()
    except ValueError:
        return None


def count_home_brief_items(index_path: Path) -> int:
    html = index_path.read_text(encoding="utf-8")
    return len(re.findall(r'<article class="va-brief-item ', html))


def count_same_day_home_brief_items(index_path: Path, target_day: date) -> int:
    html = index_path.read_text(encoding="utf-8")
    stamp = target_day.strftime("%b %d").upper()
    return len(re.findall(rf'<span aria-hidden="true">\|</span> {re.escape(stamp)}</p>', html))


def publish_homepage_to_git(repo_root: Path, remote: str, branch: str, push: bool, extra_paths: list[str] | None = None) -> str:
    git_command = resolve_git_command()
    tracked_paths = [HOME_INDEX_REL.as_posix(), SITEMAP_REL.as_posix(), BRIEF_IMAGES_REL.as_posix(), *(extra_paths or [])]
    tracked_paths = list(dict.fromkeys(tracked_paths))
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d")

    if not push:
        run_git_command(repo_root, git_command, ["add", "-A", "--", *tracked_paths])
        staged = run_git_command(repo_root, git_command, ["diff", "--cached", "--name-only", "--", *tracked_paths])
        if not staged.stdout.strip():
            return "unchanged"
        run_git_command(
            repo_root,
            git_command,
            ["commit", "-m", f"Refresh homepage briefing: {stamp}", "--only", "--", *tracked_paths],
        )
        return "committed"

    temp_branch = f"codex/home-brief-publish-{datetime.now().astimezone().strftime('%Y%m%d%H%M%S')}"

    with tempfile.TemporaryDirectory(prefix="home-brief-publish-") as temp_dir:
        worktree_path = Path(temp_dir) / "repo"
        run_git_command(repo_root, git_command, ["fetch", remote, branch])
        run_git_command(repo_root, git_command, ["worktree", "add", "-b", temp_branch, str(worktree_path), f"{remote}/{branch}"])
        try:
            for rel_path in tracked_paths:
                source_path = repo_root / rel_path
                target_path = worktree_path / rel_path
                if source_path.is_dir():
                    if target_path.exists():
                        shutil.rmtree(target_path, ignore_errors=True)
                    shutil.copytree(source_path, target_path)
                    continue
                if source_path.exists():
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)
                    continue
                if target_path.exists():
                    if target_path.is_dir():
                        shutil.rmtree(target_path, ignore_errors=True)
                    else:
                        target_path.unlink()

            run_git_command(worktree_path, git_command, ["add", "-A", "--", *tracked_paths])
            staged = run_git_command(worktree_path, git_command, ["diff", "--cached", "--name-only", "--", *tracked_paths])
            if not staged.stdout.strip():
                return "unchanged"

            run_git_command(
                worktree_path,
                git_command,
                ["commit", "-m", f"Refresh homepage briefing: {stamp}", "--only", "--", *tracked_paths],
            )

            last_error: ValueError | None = None
            for _ in range(3):
                try:
                    run_git_command(worktree_path, git_command, ["fetch", remote, branch])
                    run_git_command(worktree_path, git_command, ["rebase", f"{remote}/{branch}"])
                    run_git_command(worktree_path, git_command, ["push", remote, f"HEAD:{branch}"])
                    return f"committed+pushed({remote}/{branch})"
                except ValueError as exc:
                    last_error = exc
                    if "rebase" in str(exc).lower():
                        run_git_command(worktree_path, git_command, ["rebase", "--abort"])
                    time.sleep(1.2)

            assert last_error is not None
            raise last_error
        finally:
            run_git_command(repo_root, git_command, ["worktree", "remove", str(worktree_path), "--force"])
            run_git_command(repo_root, git_command, ["branch", "-D", temp_branch])


def build_briefing() -> tuple[list[BriefEntry], datetime]:
    refreshed_at = datetime.now().astimezone()
    target_day = refreshed_at.date()
    source_items_map = collect_source_items(BRIEF_SOURCES)
    candidate_pool: list[CandidateEntry] = []
    extend_candidate_pool(candidate_pool, source_items_map, target_day)

    selected_entries = choose_balanced_entries(candidate_pool)
    selected_entries = enforce_min_same_day_entries(selected_entries, candidate_pool, target_day)
    same_day_selected = sum(1 for _, item in selected_entries if is_same_local_day(item.published_at, target_day))

    if same_day_selected < MIN_SAME_DAY_ITEMS:
        extra_source_items = collect_source_items(EXTRA_SAME_DAY_SOURCES)
        source_items_map.extend(extra_source_items)
        extend_candidate_pool(candidate_pool, extra_source_items, target_day)
        selected_entries = choose_balanced_entries(candidate_pool)
        selected_entries = enforce_min_same_day_entries(selected_entries, candidate_pool, target_day)

    selected_entries.sort(
        key=lambda pair: pair[1].published_at.timestamp() if pair[1].published_at else 0.0,
        reverse=True,
    )

    entries = [
        BriefEntry(index=position, source=source, item=item)
        for position, (source, item) in enumerate(selected_entries[:MIN_BRIEF_ITEMS], start=1)
    ]
    return entries[:MIN_BRIEF_ITEMS], refreshed_at


def run(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    index_path = repo_root / HOME_INDEX_REL
    sitemap_path = repo_root / SITEMAP_REL
    log_dir = resolve_log_dir(repo_root, args.log_dir)

    if args.mode == "backfill-history":
        created_count, touched_paths = backfill_history_from_git(repo_root, force=args.force_history)
        message = (
            "backfill_done "
            f"created={created_count} "
            f"manifest={BRIEF_HISTORY_MANIFEST_REL.as_posix()} "
            f"paths={len(touched_paths)}"
        )
        print(message)
        write_log(log_dir, message)
        return 0

    if not index_path.exists():
        print(f"Missing homepage file: {index_path}", file=sys.stderr)
        write_log(log_dir, f"error missing_homepage path={index_path}")
        return 1
    if not sitemap_path.exists():
        print(f"Missing sitemap file: {sitemap_path}", file=sys.stderr)
        write_log(log_dir, f"error missing_sitemap path={sitemap_path}")
        return 1

    target_day = datetime.now().astimezone().date()
    if args.mode == "check":
        homepage_day = extract_home_brief_date(index_path)
        homepage_items = count_home_brief_items(index_path)
        homepage_same_day_items = count_same_day_home_brief_items(index_path, target_day)
        if (
            homepage_day == target_day
            and homepage_items >= MIN_BRIEF_ITEMS
            and homepage_same_day_items >= MIN_SAME_DAY_ITEMS
        ):
            message = (
                "check_ok "
                f"date={homepage_day.isoformat()} items={homepage_items} same_day_items={homepage_same_day_items}"
            )
            print(message)
            write_log(log_dir, message)
            return 0
        write_log(
            log_dir,
            "check_repair_needed "
            f"date={(homepage_day.isoformat() if homepage_day else 'missing')} "
            f"items={homepage_items} "
            f"same_day_items={homepage_same_day_items}",
        )

    entries, refreshed_at = build_briefing()
    same_day_item_count = sum(1 for entry in entries if is_same_local_day(entry.item.published_at, refreshed_at.date()))
    rendered_entries: list[RenderEntry] = []
    asset_paths: list[str] = []

    if not args.dry_run:
        rendered_entries, asset_paths = prepare_render_entries(repo_root, entries, refreshed_at.date())
        cleanup_old_brief_images(repo_root, refreshed_at.date(), keep_days=BRIEF_HISTORY_KEEP_DAYS)
    else:
        rendered_entries = [
            RenderEntry(
                entry=entry,
                image_src=pick_fallback_image(repo_root, entry.item, entry.source),
                fallback_src=pick_fallback_image(repo_root, entry.item, entry.source),
            )
            for entry in entries
        ]

    section_html = build_section_html(rendered_entries, refreshed_at)

    if args.dry_run:
        message = (
            "dry_run "
            f"index={index_path} "
            f"sitemap={sitemap_path} "
            f"items={len(entries)} "
            f"same_day_items={same_day_item_count}"
        )
        print(message)
        write_log(log_dir, message)
        return 0

    index_changed = update_homepage(index_path, section_html)
    sitemap_changed = update_homepage_lastmod(sitemap_path, refreshed_at.date())
    history_paths = write_brief_history_snapshot(repo_root, rendered_entries, refreshed_at)
    git_state = "skipped"

    if args.git_commit or args.git_push:
        git_state = publish_homepage_to_git(
            repo_root,
            remote=args.git_remote,
            branch=args.git_branch,
            push=args.git_push,
            extra_paths=[*asset_paths, *history_paths],
        )

    message = (
        "done "
        f"index={'updated' if index_changed else 'unchanged'} "
        f"sitemap={'updated' if sitemap_changed else 'unchanged'} "
        f"git={git_state} "
        f"items={len(entries)} "
        f"same_day_items={same_day_item_count}"
    )
    print(message)
    write_log(log_dir, message)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh the homepage briefing section with live news.")
    parser.add_argument("mode", nargs="?", default="run", choices=("run", "check", "backfill-history"), help="Execution mode.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing files.")
    parser.add_argument("--log-dir", type=Path, help="Optional log directory for task runs.")
    parser.add_argument("--force-history", action="store_true", help="Overwrite existing Product Pulse history snapshots during backfill.")
    return add_git_publish_args(parser)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
