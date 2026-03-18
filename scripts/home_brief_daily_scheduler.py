#!/usr/bin/env python3
"""Refresh the homepage daily briefing section with product-relevant live news."""

from __future__ import annotations

import argparse
import hashlib
import time
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from html import escape, unescape
from pathlib import Path

from blog_daily_scheduler import add_git_publish_args, resolve_git_command, run_git_command

SITE_URL = "https://velocai.net"
HOME_INDEX_REL = Path("index.html")
SITEMAP_REL = Path("sitemap.xml")
BRIEF_IMAGES_REL = Path("assets/images/home-briefing")
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
    ("\u2018", "'"),
    ("\u2019", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2013", "-"),
    ("\u2014", "-"),
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
        source_name="Engadget",
        source_url="https://www.engadget.com/",
        feed_url="https://www.engadget.com/rss.xml",
        keywords=(
            "apple",
            "nvidia",
            "tesla",
            "musk",
            "xai",
            "robot",
            "ai",
            "chip",
            "device",
            "laptop",
        ),
        fallback_image="/assets/images/stock-2026-03/stock-10.jpg",
        item_count=1,
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

MEDIA_NS = {
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}
FALLBACK_IMAGES = (
    "/assets/images/stock-2026-03/stock-02.jpg",
    "/assets/images/stock-2026-03/stock-04.jpg",
    "/assets/images/stock-2026-03/stock-06.jpg",
    "/assets/images/stock-2026-03/stock-07.jpg",
    "/assets/images/stock-2026-03/stock-08.jpg",
    "/assets/images/stock-2026-03/stock-10.jpg",
)
MIN_BRIEF_ITEMS = 10
RECENT_BACKFILL_DAYS = 7
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


def pick_fallback_image(item: FeedItem, source: BriefSource) -> str:
    seed = f"{source.slug}|{item.link}|{item.title}".encode("utf-8", errors="ignore")
    digest = hashlib.sha1(seed).hexdigest()
    index = int(digest[:8], 16) % len(FALLBACK_IMAGES)
    return FALLBACK_IMAGES[index]


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


def resolve_story_image_url(item: FeedItem, source: BriefSource) -> tuple[str, str]:
    fallback_image = source.fallback_image or pick_fallback_image(item, source)
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
        fallback_image = source.fallback_image or pick_fallback_image(item, source)

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
    return f"""
    <div class="va-briefing-head">
      <div class="va-briefing-title-wrap">
        <p class="va-briefing-section-label">Top Stories</p>
        <h2 class="va-briefing-heading">Product <span class="is-accent">Pulse</span></h2>
      </div>
      <p class="va-briefing-stamp">Updated daily 08:30 <span aria-hidden="true">|</span> {escape(format_refresh_time(refreshed_at))}</p>
    </div>
    <div class="va-briefing-panel">
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


def cleanup_old_brief_images(repo_root: Path, target_day: date, keep_days: int = 5) -> bool:
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
    source_items_map: list[tuple[BriefSource, list[FeedItem]]] = []
    candidate_pool: list[CandidateEntry] = []
    for source in BRIEF_SOURCES:
        try:
            items = parse_feed_items(fetch_bytes(source.feed_url))
        except Exception as exc:  # pragma: no cover - network/source variability
            print(f"skip_source source={source.source_name} error={exc}", file=sys.stderr)
            continue
        source_items_map.append((source, items))
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

    selected_entries = choose_balanced_entries(candidate_pool)
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

    if not index_path.exists():
        print(f"Missing homepage file: {index_path}", file=sys.stderr)
        return 1
    if not sitemap_path.exists():
        print(f"Missing sitemap file: {sitemap_path}", file=sys.stderr)
        return 1

    entries, refreshed_at = build_briefing()
    rendered_entries: list[RenderEntry] = []
    asset_paths: list[str] = []

    if not args.dry_run:
        rendered_entries, asset_paths = prepare_render_entries(repo_root, entries, refreshed_at.date())
        cleanup_old_brief_images(repo_root, refreshed_at.date(), keep_days=5)
    else:
        rendered_entries = [
            RenderEntry(
                entry=entry,
                image_src=entry.source.fallback_image or pick_fallback_image(entry.item, entry.source),
                fallback_src=entry.source.fallback_image or pick_fallback_image(entry.item, entry.source),
            )
            for entry in entries
        ]

    section_html = build_section_html(rendered_entries, refreshed_at)

    if args.dry_run:
        print(
            "dry_run "
            f"index={index_path} "
            f"sitemap={sitemap_path} "
            f"items={len(entries)}"
        )
        return 0

    index_changed = update_homepage(index_path, section_html)
    sitemap_changed = update_homepage_lastmod(sitemap_path, refreshed_at.date())
    git_state = "skipped"

    if args.git_commit or args.git_push:
        git_state = publish_homepage_to_git(
            repo_root,
            remote=args.git_remote,
            branch=args.git_branch,
            push=args.git_push,
            extra_paths=asset_paths,
        )

    print(
        "done "
        f"index={'updated' if index_changed else 'unchanged'} "
        f"sitemap={'updated' if sitemap_changed else 'unchanged'} "
        f"git={git_state} "
        f"items={len(entries)}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh the homepage briefing section with live news.")
    parser.add_argument("run", nargs="?", default="run", help="Subcommand placeholder for compatibility.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing files.")
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
