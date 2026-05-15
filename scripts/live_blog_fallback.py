#!/usr/bin/env python3
"""Generate SEO/GEO-friendly blog fallback candidates from live news feeds."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

from blog_daily_scheduler import PostMeta, SITE_URL, format_human
from home_brief_daily_scheduler import (
    BRIEF_SOURCES,
    EXTRA_SAME_DAY_SOURCES,
    FeedItem,
    clean_text,
    clip_text,
    fetch_bytes,
    parse_feed_items,
    score_item,
)


@dataclass(frozen=True)
class LiveBlogCandidate:
    post: PostMeta
    html: str
    link: str
    source_name: str


@dataclass(frozen=True)
class CuratedPage:
    source_slug: str
    source_name: str
    url: str


CACHE_ROOT = Path(tempfile.gettempdir()) / "weiluoge-live-cache"
CACHE_TTL_SECONDS = 6 * 60 * 60
MAX_NEWS_SOURCE_AGE_DAYS = 365


NOISE_PATTERNS = (
    " sale ",
    " cheapest ",
    " coupon ",
    " discount ",
    " deal ",
    " deals ",
    " today in apple history ",
    " buy now ",
    " best price ",
    " record low ",
    " clearance ",
    " giveaway ",
    " ransomware ",
    " stock market ",
    " f1 streaming ",
    " netflix ",
)

LANE_DISALLOWED_PATTERNS = {
    "cleanup": (
        "ransomware",
        "stolen",
        "hacker",
        "hackers",
        "spy",
        "supreme court",
        "app store commission",
        "marketshare",
        "sales",
        "ai phone",
        "save up",
        "coupon",
        "coupons",
        "deal",
    ),
    "dualshot": (
        "history",
        "downloads from netflix",
        "recycled material",
        "macbook pro",
        "ssd",
        "amd",
        "settlement",
        "siri",
        "spotify",
        "podcast",
    ),
    "find": (
        "ransomware",
        "foxconn",
        "marketshare",
        "smartphone sales",
        "apple history",
    ),
    "octopus": (
        "3d printing",
        "recycled glass",
        "iphone sales",
        "smartphone market",
    ),
}

CURATED_PROTOCOL_PAGES = (
    CuratedPage("bluetooth", "Bluetooth SIG", "https://www.bluetooth.com/specifications/specs/core-specification-6-2/"),
    CuratedPage("bluetooth", "Bluetooth SIG", "https://www.bluetooth.com/learn-about-bluetooth/key-attributes/gatt/"),
    CuratedPage("bluetooth", "Bluetooth SIG", "https://www.bluetooth.com/learn-about-bluetooth/feature-enhancements/le-audio/"),
    CuratedPage("bluetooth", "Bluetooth SIG", "https://www.bluetooth.com/specifications/mesh-specifications/"),
    CuratedPage("bluetooth", "Bluetooth SIG", "https://www.bluetooth.com/blog/bluetooth-shorter-connection-intervals-paving-the-way-for-bluetooth-innovation/"),
    CuratedPage("bluetooth", "Bluetooth SIG", "https://www.bluetooth.com/blog/bluetooth-core-specifications-now-scheduled-for-bi-annual-release/"),
)

LANE_ALLOWED_SOURCES = {
    "protocol": {
        "Bluetooth SIG",
        "Nordic News",
        "Nordic GetConnected",
        "Silicon Labs Bluetooth",
        "Blecon",
        "BeaconZone",
        "SoundGuys Bluetooth",
        "Android Authority Bluetooth",
        "9to5Google Bluetooth",
    },
    "updates": {"Bluetooth SIG", "Nordic News", "Nordic GetConnected", "Apple Newsroom", "MacRumors", "AppleInsider", "MacStories", "9to5Mac", "OpenAI News", "Tom's Hardware"},
}

LANE_APP_ALLOWED_SOURCES = {
    "cleanup": {"9to5Mac", "MacRumors", "AppleInsider", "Ars Technica Apple", "MacStories"},
    "translate": {"OpenAI News", "Cult of Mac"},
    "find": {"9to5Mac", "AppleInsider", "Android Authority Bluetooth", "BeaconZone", "Blecon"},
    "dualshot": {"OpenAI News", "9to5Mac", "AppleInsider", "MacRumors"},
    "octopus": {"OpenAI News", "MacRumors", "AppleInsider"},
}

APP_FUNCTION_KEYWORDS = {
    "cleanup": (
        "files",
        "storage",
        "icloud backup",
        "backup files",
        "backup data",
        "back up your mac",
        "icloud",
        "nas",
        "icloud drive",
        "database",
        "cloud",
        "system data",
        "storage full",
        "free up storage",
    ),
    "find": (
        "airpods",
        "find my",
        "nearby",
        "lost",
        "location",
        "tracking",
        "recover",
        "bluetooth device",
        "device finding",
        "find nearby",
        "lost device",
    ),
    "bluetooth": (
        "bluetooth",
        "ble",
        "gatt",
        "auracast",
        "mesh",
        "device discovery",
        "bluetooth pairing",
        "rssi",
        "bluetooth signal",
    ),
    "translate": (
        "translate",
        "translation",
        "translator",
        "live translation",
        "speech translation",
        "language translation",
        "multilingual",
        "caption",
        "subtitle",
        "ocr",
        "text recognition",
        "transcription",
    ),
    "dualshot": (
        "camera",
        "video",
        "record",
        "recording",
        "creator",
        "demo",
        "tutorial",
        "vlog",
        "youtube",
        "short-form",
        "livestream",
    ),
    "octopus": (
        "codex",
        "agent",
        "coding agent",
        "developer tools",
        "remote coding",
        "thread",
        "approval",
        "approvals",
        "permissions",
        "ssh",
        "server",
        "automation",
        "voice",
        "files",
        "project",
    ),
}

CLEANUP_TITLE_REQUIRED = (
    "storage",
    "icloud backup",
    "backup files",
    "backup data",
    "back up your mac",
    "icloud",
    "files",
    "nas",
    "icloud drive",
    "database",
    "cloud",
    "system data",
)

UPDATES_TITLE_REQUIRED = APP_FUNCTION_KEYWORDS["cleanup"] + APP_FUNCTION_KEYWORDS["find"] + APP_FUNCTION_KEYWORDS["bluetooth"]

LANE_SOURCE_SLUGS = {
    "cleanup": ("apple",),
    "translate": ("ai", "apple"),
    "find": ("apple", "bluetooth"),
    "dualshot": ("apple", "ai"),
    "octopus": ("ai", "apple"),
    "protocol": ("bluetooth",),
    "updates": ("apple", "ai", "bluetooth"),
}

LANE_REQUIRED_KEYWORDS = {
    "cleanup": APP_FUNCTION_KEYWORDS["cleanup"],
    "translate": APP_FUNCTION_KEYWORDS["translate"],
    "find": APP_FUNCTION_KEYWORDS["find"] + APP_FUNCTION_KEYWORDS["bluetooth"],
    "dualshot": APP_FUNCTION_KEYWORDS["dualshot"],
    "octopus": APP_FUNCTION_KEYWORDS["octopus"],
    "protocol": APP_FUNCTION_KEYWORDS["bluetooth"],
    "updates": UPDATES_TITLE_REQUIRED,
}

LANE_FALLBACK_PREFIX = {
    "cleanup": "iphone-storage-full-cleanup-five-step-order-live-source-update",
    "translate": "translate-ai-live-translation-workflow-update",
    "find": "find-ai-live-device-finding-update",
    "dualshot": "dualshot-camera-product-demo-tutorial-guide-live-source-update",
    "octopus": "octopus-mobile-codex-workflow-live-source-update",
}

LANE_TOPIC = {
    "cleanup": "cleanup pro Storage Cleanup",
    "translate": "Translate AI Translation Workflow",
    "find": "find AI Device Recovery",
    "dualshot": "Dual Camera Creator Workflow",
    "octopus": "Octopus Mobile Codex Workflow",
}

LANE_APP_TERM = {
    "cleanup": "cleanup pro",
    "translate": "Translate",
    "find": "find AI",
    "dualshot": "Dual Camera",
    "octopus": "Octopus",
}


def matches_keyword(text: str, keyword: str) -> bool:
    lowered = text.lower()
    term = keyword.lower()
    if " " in term:
        return term in lowered
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lowered) is not None


def json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def news_source_age_days(item: FeedItem, target_day: date) -> int | None:
    if item.published_at is None:
        return None
    return (target_day - item.published_at.astimezone().date()).days


def is_recent_news_source(item: FeedItem, target_day: date) -> bool:
    age = news_source_age_days(item, target_day)
    return age is not None and 0 <= age <= MAX_NEWS_SOURCE_AGE_DAYS


def require_recent_news_source(item: FeedItem, target_day: date) -> None:
    age = news_source_age_days(item, target_day)
    if age is None:
        raise ValueError("Live blog news sources must include a publish date.")
    if age < 0:
        raise ValueError("Live blog news sources cannot be dated after the article date.")
    if age > MAX_NEWS_SOURCE_AGE_DAYS:
        raise ValueError(
            f"Live blog news source is {age} days old; maximum allowed age is {MAX_NEWS_SOURCE_AGE_DAYS} days."
        )


def cache_paths_for_url(url: str) -> tuple[Path, Path]:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    cache_dir = CACHE_ROOT
    return cache_dir / f"{key}.bin", cache_dir / f"{key}.json"


def cached_fetch_bytes(url: str) -> bytes:
    payload_path, meta_path = cache_paths_for_url(url)
    now = time.time()
    if payload_path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            fetched_at = float(meta.get("fetched_at", 0.0))
            if now - fetched_at <= CACHE_TTL_SECONDS:
                return payload_path.read_bytes()
        except Exception:
            pass

    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    payload = fetch_bytes(url)
    payload_path.write_bytes(payload)
    meta_path.write_text(json.dumps({"url": url, "fetched_at": now}, ensure_ascii=False), encoding="utf-8")
    return payload


def slugify(value: str, limit: int = 72) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:limit].strip("-") or "update"


def source_pool_for_lane(lane: str):
    preferred_slugs = LANE_SOURCE_SLUGS.get(lane, ())
    seen: set[tuple[str, str, str]] = set()
    for source in (*BRIEF_SOURCES, *EXTRA_SAME_DAY_SOURCES):
        key = (source.slug, source.source_name, source.feed_url)
        if key in seen or source.slug not in preferred_slugs:
            continue
        seen.add(key)
        if lane in LANE_ALLOWED_SOURCES and source.source_name not in LANE_ALLOWED_SOURCES[lane]:
            continue
        if lane in LANE_APP_ALLOWED_SOURCES and source.source_name not in LANE_APP_ALLOWED_SOURCES[lane]:
            continue
        yield source


def render_source_slug_for_lane(lane: str, source_slug: str) -> str:
    if source_slug in {"apple", "ai", "bluetooth"}:
        return source_slug
    if lane == "translate":
        return "ai"
    if lane == "octopus":
        return "ai"
    if lane in {"cleanup", "find", "dualshot"}:
        return "apple"
    return "bluetooth"


def article_prefix_for_lane(lane: str, source_slug: str) -> str:
    return LANE_FALLBACK_PREFIX.get(lane, article_prefix_for_source_slug(source_slug))


def article_prefix_for_source_slug(source_slug: str) -> str:
    if source_slug == "apple":
        return "apple-feature-performance-commentary"
    if source_slug == "ai":
        return "ai-technology-outlook"
    return "bluetooth-industry-update"


def topic_for_source_slug(source_slug: str) -> str:
    if source_slug == "apple":
        return "Apple Product Commentary"
    if source_slug == "ai":
        return "AI Technology Outlook"
    return "Bluetooth Industry Update"


def topic_for_lane(lane: str, source_slug: str) -> str:
    return LANE_TOPIC.get(lane, topic_for_source_slug(source_slug))


def teaser_for_source_slug(source_slug: str) -> str:
    if source_slug == "apple":
        return "A search-focused Apple commentary on new product features, performance tradeoffs, and upgrade relevance."
    if source_slug == "ai":
        return "A forward-looking AI commentary focused on model capability, workflow impact, and what changes next."
    return "A latest-info Bluetooth commentary focused on standards, applications, and practical deployment impact."


def source_home_url(source_slug: str) -> str:
    if source_slug == "apple":
        return "https://www.apple.com/newsroom/"
    if source_slug == "ai":
        return "https://openai.com/news/"
    return "https://www.bluetooth.com/specifications/"


def background_links_for(source_slug: str) -> list[tuple[str, str]]:
    if source_slug == "apple":
        return [
            ("Apple Newsroom", "https://www.apple.com/newsroom/"),
            ("Apple Support", "https://support.apple.com/"),
        ]
    if source_slug == "ai":
        return [
            ("OpenAI News", "https://openai.com/news/"),
            ("OpenAI API", "https://openai.com/api/"),
        ]
    return [
        ("Bluetooth SIG Specifications", "https://www.bluetooth.com/specifications/"),
        ("Bluetooth SIG Features", "https://www.bluetooth.com/learn-about-bluetooth/"),
    ]


def keywords_for_source_slug(source_slug: str) -> list[str]:
    if source_slug == "apple":
        return [
            "find apple product changes",
            "cleanup iphone upgrade checklist",
            "bluetooth accessory compatibility iphone",
            "find iphone feature differences",
            "cleanup iphone storage before upgrade",
            "find mac performance changes",
        ]
    if source_slug == "ai":
        return [
            "find ai workflow changes",
            "find ai product updates",
            "cleanup ai automation workflow",
            "find ai model impact",
            "cleanup ai operations checklist",
            "find ai capability shifts",
        ]
    return [
        "bluetooth latest update",
        "bluetooth standards commentary",
        "bluetooth application analysis",
        "bluetooth industry outlook",
        "bluetooth feature update",
        "bluetooth product implications",
    ]


def keywords_for_lane(lane: str, source_slug: str) -> list[str]:
    if lane not in LANE_APP_TERM:
        return keywords_for_source_slug(source_slug)
    app_term = LANE_APP_TERM[lane]
    lane_keywords = [app_term, *APP_FUNCTION_KEYWORDS[lane]]
    source_keywords = keywords_for_source_slug(source_slug)
    return list(dict.fromkeys([*lane_keywords, *source_keywords]))


def story_label(value: str, limit: int = 34) -> str:
    cleaned = clean_text(value)
    cleaned = re.sub(r"\s*[-|]\s*(MacRumors|AppleInsider|9to5Mac|TechCrunch|OpenAI|Bluetooth.*)$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^A-Za-z0-9+ ]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= limit:
        return cleaned or "Live Source Update"
    clipped = cleaned[:limit].rsplit(" ", 1)[0].strip()
    return clipped or cleaned[:limit].strip()


def lane_story_focus(lane: str, source_slug: str, item: FeedItem) -> tuple[str, str] | None:
    if lane not in LANE_APP_TERM:
        return None
    label_limit = 28 if lane == "find" else 24
    label = story_label(item.title, limit=label_limit)
    if lane == "cleanup":
        return (
            f"Cleanup Pro Storage Lessons from {label}",
            f"Cleanup pro storage update on {label}, focused on storage pressure, file growth, backup hygiene, and safe iPhone cleanup decisions.",
        )
    if lane == "translate":
        return (
            f"Translate AI Workflow Lessons from {label}",
            f"Translate workflow update on {label}, focused on translation, speech, OCR, captions, and multilingual workflow decisions.",
        )
    if lane == "find":
        return (
            f"find AI Recovery Lessons from {label}",
            f"find AI recovery update on {label}, focused on device discovery, Bluetooth signals, nearby recovery, and lost-item workflows.",
        )
    if lane == "dualshot":
        return (
            f"Dual Camera Creator Lessons from {label}",
            f"Dual Camera creator update on {label}, focused on camera capture, demo recording, creator workflow, and video repurposing.",
        )
    if lane == "octopus":
        return (
            f"Octopus Mobile Coding Lessons from {label}",
            f"Octopus mobile coding update on {label}, focused on mobile coding approvals, thread continuity, automation follow-up, SSH-linked workflow, and developer context from iPhone or iPad.",
        )
    return None


def lane_summary(lane: str, source_slug: str, source_name: str, item: FeedItem) -> str:
    base = clean_summary(source_slug, source_name, item)
    if lane not in LANE_APP_TERM:
        return base
    app_term = LANE_APP_TERM[lane]
    return clip_text(
        f"{base} For {app_term} readers, the useful question is how this source changes a real workflow decision, what to verify next, and where the app fits.",
        limit=260,
    )


def item_matches_lane_intent(lane: str, source_slug: str, title_text: str, haystack: str) -> bool:
    disallowed = LANE_DISALLOWED_PATTERNS.get(lane, ())
    if any(pattern in haystack for pattern in disallowed):
        return False
    if lane == "cleanup":
        cleanup_title_terms = (
            "storage",
            "file storage",
            "files",
            "icloud",
            "icloud backup",
            "icloud drive",
            "backup",
            "pcloud",
            "macbook notch",
            "512gb",
            "256gb",
        )
        return any(matches_keyword(title_text, keyword) for keyword in cleanup_title_terms)
    if lane == "translate":
        title_terms = (
            "translate",
            "translation",
            "translator",
            "live translation",
            "speech translation",
            "language translation",
            "caption",
            "subtitle",
            "ocr",
            "text recognition",
            "transcription",
        )
        if any(matches_keyword(title_text, keyword) for keyword in title_terms):
            return True

        voice_terms = (
            "audio model",
            "audio models",
            "dubbing",
            "language learning",
            "voice ai",
            "voice feature",
            "voice features",
            "voice engine",
            "real-time voice",
            "realtime voice",
            "realtime api",
            "speech",
            "spoken",
            "language gap",
            "language gaps",
            "multilingual",
            "caption",
            "subtitle",
            "transcription",
        )
        return source_slug == "ai" and any(matches_keyword(haystack, keyword) for keyword in voice_terms)
    if lane == "find":
        strict_find_terms = (
            "find my",
            "airtag",
            "tracker",
            "trackers",
            "luggage tracker",
            "lost",
            "stolen",
            "location",
            "asset tracking",
            "ble tracking",
            "smart labels",
            "beacon",
            "beacons",
            "indoor navigation",
            "spatial signal",
            "nearby finding",
        )
        return any(matches_keyword(title_text, keyword) for keyword in strict_find_terms) or any(
            matches_keyword(haystack, keyword)
            for keyword in strict_find_terms
            if keyword not in {"lost", "location"}
        )
    if lane == "dualshot":
        title_terms = (
            "camera",
            "video",
            "recording",
            "record",
            "creator",
            "demo",
            "tutorial",
            "vlog",
            "youtube",
            "short-form",
            "livestream",
            "sora",
            "cinematic",
            "iphone short",
            "short films",
            "video app",
        )
        return any(matches_keyword(title_text, keyword) for keyword in title_terms)
    if lane == "octopus":
        title_terms = (
            "codex",
            "coding agent",
            "agent apps",
            "ai agent",
            "ai agents",
            "developer tools",
            "remote coding",
            "sandbox",
            "nvidia engineers",
            "finance teams use codex",
        )
        support_terms = (
            "thread",
            "approval",
            "permissions",
            "ssh",
            "server",
            "automation",
            "tool results",
            "prompt",
            "workflow",
        )
        return any(matches_keyword(title_text, keyword) for keyword in title_terms) or any(
            matches_keyword(haystack, keyword) for keyword in support_terms
        )
    if lane == "protocol":
        protocol_terms = (
            "bluetooth sig",
            "core",
            "specification",
            "standard",
            "standards",
            "auracast",
            "le audio",
            "channel sounding",
            "mesh",
            "gatt",
            "beacon",
            "beacons",
            "asset tracking",
            "industrial",
            "iot",
            "manufacturing",
            "healthcare",
            "connection interval",
            "connection intervals",
            "interoperability",
            "chipset",
            "chipsets",
            "device vendors",
            "broadcast audio",
            "ada compliant",
        )
        return any(matches_keyword(haystack, keyword) for keyword in protocol_terms)
    return any(matches_keyword(haystack, keyword) for keyword in LANE_REQUIRED_KEYWORDS[lane])


def app_lane_profile(lane: str) -> dict[str, object]:
    return {
        "cleanup": {
            "eyebrow": "cleanup pro live storage update",
            "intent": "storage cleanup, backup hygiene, file growth, and safe deletion order",
            "workflow": "review large files, old downloads, duplicate media, offline caches, and backup state before deleting anything important",
            "risk": "storage advice becomes weak when it skips backup readiness, hidden caches, or the order in which users should inspect files",
            "primary": "Open Cleanup Pro",
            "primary_url": "/apps/",
            "secondary": "iPhone storage cleanup",
        },
        "translate": {
            "eyebrow": "Translate live workflow update",
            "intent": "translation, OCR, captions, voice input, and multilingual review workflows",
            "workflow": "capture the source text or speech, translate it, review uncertain phrases, and keep context for follow-up conversations",
            "risk": "translation advice becomes weak when it ignores speech quality, OCR errors, idioms, or human review for high-stakes wording",
            "primary": "Open Translate",
            "primary_url": "/translate/",
            "secondary": "AI translation workflow",
        },
        "find": {
            "eyebrow": "find AI live recovery update",
            "intent": "nearby-device discovery, Bluetooth signal reading, last-seen context, and lost-item recovery",
            "workflow": "check the device category, scan nearby signals, compare movement context, and separate a weak signal from a real recovery lead",
            "risk": "finding advice becomes weak when it treats every Bluetooth or location clue as equally trustworthy",
            "primary": "Open find AI",
            "primary_url": "/apps/",
            "secondary": "device recovery workflow",
        },
        "dualshot": {
            "eyebrow": "Dual Camera live creator update",
            "intent": "creator recording, product demos, tutorials, camera framing, and video repurposing",
            "workflow": "plan the main shot, capture the presenter or context angle, protect audio clarity, and repurpose the recording for multiple channels",
            "risk": "creator advice becomes weak when it talks about video trends without explaining capture setup, framing, and editing consequences",
            "primary": "Open Dual Camera",
            "primary_url": "/apps/",
            "secondary": "creator capture workflow",
        },
        "octopus": {
            "eyebrow": "Octopus live mobile coding update",
            "intent": "mobile Codex continuity, approvals, SSH-linked sessions, runtime follow-up, and developer context capture",
            "workflow": "review session state, approve the next action, add voice or file context, and move the coding thread forward without reopening the full desktop setup",
            "risk": "mobile coding advice becomes weak when it promises convenience without explaining approvals, thread continuity, or how remote context gets back into the same workflow",
            "primary": "Open Octopus",
            "primary_url": "/octopus/",
            "secondary": "mobile Codex workflow",
        },
    }[lane]


def app_lane_table_rows(lane: str, source_title: str) -> list[tuple[str, str, str]]:
    profile = app_lane_profile(lane)
    return [
        ("Fresh evidence", source_title, f"Connects the new item to {profile['secondary']} decisions"),
        ("User problem", str(profile["intent"]), "Shows which app decision the update affects"),
        ("Workflow check", str(profile["workflow"]), "Turns the update into an actionable sequence"),
        ("Reader check", "Compare the current source detail with the workflow before changing behavior", "Keeps the advice grounded in a real action"),
    ]


def app_lane_faq_items(lane: str) -> list[tuple[str, str]]:
    profile = app_lane_profile(lane)
    app_term = LANE_APP_TERM[lane]
    return [
        (
            f"Why does this source matter for {app_term}?",
            f"It gives readers a current example to compare against {profile['intent']}, so the next step stays tied to a real workflow rather than a generic feature list.",
        ),
        (
            "How should readers use this update?",
            f"Start with the source fact, map it to {profile['workflow']}, then verify the risk before changing the routine.",
        ),
        (
            f"What makes this {app_term} workflow useful?",
            f"It ties the live source item to {profile['workflow']}, so readers can decide what to inspect, what to try next, and what to avoid.",
        ),
    ]


def render_app_live_article(day: date, source_slug: str, source_name: str, item: FeedItem, post: PostMeta, lane: str) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    source_published = item.published_at.astimezone().strftime("%B %d, %Y") if item.published_at else human_date
    source_title = clean_text(item.title)
    summary = lane_summary(lane, source_slug, source_name, item)
    profile = app_lane_profile(lane)
    app_term = LANE_APP_TERM[lane]
    keyword_coverage = keywords_for_lane(lane, source_slug) + [slugify(item.title).replace("-", " ")]
    table_rows = app_lane_table_rows(lane, source_title)
    faq_items = app_lane_faq_items(lane)
    table_html = "\n".join(
        f"          <tr><td>{escape(col1)}</td><td>{escape(col2)}</td><td>{escape(col3)}</td></tr>"
        for col1, col2, col3 in table_rows
    )
    faq_html = "\n".join(
        f"      <p><strong>{escape(question)}</strong><br>\n      {escape(answer)}</p>\n"
        for question, answer in faq_items
    )
    source_links = [(f"{source_name}: {source_title}", item.link), *background_links_for(source_slug)]
    source_links_html = "\n".join(
        f'          <li><a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(label)}</a></li>'
        for label, url in source_links
    )
    keywords = ", ".join(keyword_coverage)
    tldr = (
        f"As of {human_date}, {source_title} gives {app_term} readers a concrete signal to test against {profile['secondary']}. "
        f"The useful answer is what to inspect next, what risk to reduce, and when the source should stay as background context."
    )
    action_checks = [
        f"Identify the exact fact in {source_name} that changes the {app_term} workflow.",
        f"Compare that fact with the current step where users handle {profile['secondary']}.",
        "Decide whether the next action is a setup change, a review step, a recovery attempt, or no change at all.",
        "Keep the original source open when the change affects compatibility, privacy, permissions, storage, capture quality, or device behavior.",
    ]
    action_checks_html = "\n".join(f"          <li>{escape(check)}</li>" for check in action_checks)
    ignore_checks = [
        "The source is about a distant platform change that does not affect the user's current device or workflow.",
        "The update describes a product announcement but gives no behavior, limit, compatibility, or rollout detail to test.",
        "The next step would require risky changes before the user can verify the source detail in their own setup.",
        f"The reader only needs background context and does not need to change how they use {app_term} today.",
    ]
    ignore_checks_html = "\n".join(f"          <li>{escape(check)}</li>" for check in ignore_checks)

    return f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(post.title)} | VelocAI Blog</title>
  <meta name="description" content="{escape(post.description)}">
  <meta name="keywords" content="{escape(keywords)}">
  <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
  <link rel="canonical" href="{escape(canonical)}">
  <link rel="icon" type="image/x-icon" href="/velocai.ico">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="en_US">
  <meta property="og:site_name" content="VelocAI">
  <meta property="og:title" content="{escape(post.title)}">
  <meta property="og:description" content="{escape(post.description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:image" content="https://velocai.net/2.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(post.title)}">
  <meta name="twitter:description" content="{escape(post.description)}">
  <meta name="twitter:image" content="https://velocai.net/2.png">
  <script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "BlogPosting",
      "headline": {json_string(post.title)},
      "description": {json_string(post.description)},
      "datePublished": {json_string(post.published_iso)},
      "dateModified": {json_string(post.published_iso)},
      "author": {{"@type": "Organization", "name": "VelocAI"}},
      "publisher": {{
        "@type": "Organization",
        "name": "VelocAI",
        "logo": {{"@type": "ImageObject", "url": "https://velocai.net/2.png"}}
      }},
      "mainEntityOfPage": {json_string(canonical)},
      "keywords": {json.dumps(keyword_coverage[:8], ensure_ascii=False)}
    }},
    {{
      "@type": "FAQPage",
      "mainEntity": [
        {json.dumps([{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_items], ensure_ascii=False)[1:-1]}
      ]
    }}
  ]
}}
  </script>
  <style>
    :root {{ --bg:#f7faf8; --text:#18241f; --muted:#52645c; --line:#cfdcd4; --panel:#ffffff; --brand:#176b54; --brand-soft:#e7f5ee; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Inter","Segoe UI",sans-serif; color:var(--text); background:var(--bg); line-height:1.72; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ width:min(920px, calc(100% - 34px)); margin:0 auto; }}
    header {{ border-bottom:1px solid var(--line); background:rgba(247,250,248,.94); }}
    .top {{ padding:14px 0; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }}
    .brand {{ display:inline-flex; align-items:center; gap:10px; font-weight:700; }}
    .brand img {{ width:auto; height:36px; max-width:52px; object-fit:contain; object-position:center; border-radius:10px; }}
    nav {{ display:flex; gap:12px; flex-wrap:wrap; color:var(--muted); font-size:14px; }}
    nav a:hover {{ color:var(--text); }}
    main {{ padding:36px 0 56px; }}
    h1,h2,h3 {{ margin:0; line-height:1.22; }}
    h1 {{ font-size:clamp(30px, 4.2vw, 48px); max-width:25ch; }}
    h2 {{ margin-top:30px; font-size:clamp(24px, 3vw, 34px); }}
    p,li,td,th {{ color:#31443b; font-size:17px; }}
    ul,ol {{ padding-left:22px; }}
    .meta {{ margin-top:10px; color:var(--muted); font-size:14px; }}
    .hero, .panel, .tldr, .capsule, table {{ background:var(--panel); border:1px solid var(--line); border-radius:18px; }}
    .hero {{ padding:26px; box-shadow:0 12px 28px rgba(28,44,36,.05); }}
    .panel, .tldr, .capsule {{ margin-top:24px; padding:22px; box-shadow:0 12px 28px rgba(28,44,36,.05); }}
    .tldr {{ border-left:6px solid #2a9d74; }}
    .capsule {{ background:#fbfdfb; }}
    .eyebrow {{ display:inline-flex; margin-bottom:14px; border-radius:999px; padding:8px 12px; background:var(--brand-soft); color:var(--brand); font-size:13px; font-weight:700; text-transform:uppercase; }}
    .hero > p:not(.meta) {{ margin:14px 0 0; max-width:none; }}
    .links {{ margin-top:32px; display:flex; gap:14px; flex-wrap:wrap; }}
    .links a {{ border:1px solid #b9d5ca; border-radius:999px; padding:10px 14px; font-weight:600; font-size:14px; color:var(--brand); background:#fff; }}
    table {{ width:100%; margin-top:24px; border-collapse:separate; border-spacing:0; overflow:hidden; }}
    th,td {{ padding:16px 18px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    tr:last-child td {{ border-bottom:none; }}
    th {{ color:var(--text); font-weight:700; background:rgba(23,107,84,.08); }}
    .sources a {{ color:var(--brand); border-bottom:1px solid #9fc7b7; }}
  </style>
  <link rel="stylesheet" href="/assets/css/site-tools.css">
</head>
<body>
  <header>
    <div class="wrap top">
      <a class="brand" href="/">
        <img src="/velocai.png" alt="VelocAI logo" width="102" height="73">
        <span>VelocAI Blog</span>
      </a>
      <nav aria-label="Main">
        <a href="/">Home</a>
        <a href="/apps/">Apps</a>
        <a href="/blog/">Blog</a>
        <a href="/bluetoothexplorer/">Bluetooth Explorer</a>
      </nav>
    </div>
  </header>

  <main class="wrap">
    <article>
      <div class="hero">
        <span class="eyebrow">{escape(str(profile["eyebrow"]))}</span>
        <h1>{escape(post.title)}</h1>
        <p class="meta">Published on {escape(human_date)} | Topic: {escape(post.topic)} | Source: {escape(source_name)} | Source date: {escape(source_published)}</p>
        <p>{escape(summary)}</p>
      </div>

      <div class="tldr">
        <p><strong>TL;DR:</strong> {escape(tldr)}</p>
      </div>

      <h2>What changed in {escape(day.strftime("%B %Y"))}?</h2>
      <p>{escape(source_title)} matters for {escape(app_term)} when it changes a real workflow question: {escape(str(profile["intent"]))}. The useful check is to identify the new fact, choose the next action, and verify whether the workflow actually changes.</p>

      <table aria-label="{escape(post.topic)} live source coverage">
        <thead>
          <tr><th>Coverage area</th><th>Specific angle</th><th>Reader value</th></tr>
        </thead>
        <tbody>
{table_html}
        </tbody>
      </table>

      <h2>Why does this matter for {escape(app_term)}?</h2>
      <p>The source item matters when it changes how a reader thinks about {escape(str(profile["secondary"]))}. The practical answer is to connect {escape(source_title)} with {escape(str(profile["workflow"]))}, then decide what to inspect, what to try next, and what risk to avoid.</p>

      <h2>Applying The Signal</h2>
      <p>Users can apply the signal when they compare a current workflow against the source detail. For {escape(app_term)}, the useful next step is to pair the action with a verification step and a clear reason the detail changes a real decision.</p>

      <div class="capsule">
        <p><strong>Reader note:</strong> As of {human_date}, {escape(post.title.lower())} connects a fresh {escape(source_name)} detail to {escape(str(profile["secondary"]))}. Keep it practical: change the workflow only when the source points to a step the user can inspect, repeat, or verify.</p>
      </div>

      <h2>What should the workflow check next?</h2>
      <p>{escape(str(profile["risk"]).capitalize())}. Readers should keep the source-specific facts visible, especially when the update changes a setup, review step, recovery signal, or approval path.</p>

      <h2>Action Steps For This Signal</h2>
      <p>The safest way to use the update is to turn it into one small decision. For {escape(app_term)}, that means connecting the source detail to a step the user can inspect, repeat, or undo without guessing.</p>
      <ol>
{action_checks_html}
      </ol>

      <h2>What should readers verify next?</h2>
      <p>Check the source detail against the current workflow, confirm which step changes, and look for one risk that the update reduces or introduces. If the update does not change a real action, treat it as context rather than a reason to change the routine.</p>

      <h2>When should users ignore the update?</h2>
      <p>Not every live item deserves a workflow change. The update should stay in the background when it does not create a clearer action, a measurable risk reduction, or a better way to complete the task.</p>
      <ul>
{ignore_checks_html}
      </ul>

      <h2>FAQ</h2>
{faq_html}
      <section class="sources" aria-label="Source attribution">
        <h3>Source attribution</h3>
        <ul>
{source_links_html}
        </ul>
      </section>

      <div class="links">
        <a href="/blog/">Back to blog index</a>
        <a href="/apps/">Browse VelocAI apps</a>
        <a href="{escape(str(profile["primary_url"]))}">{escape(str(profile["primary"]))}</a>
      </div>
    </article>
  </main>
  <script src="/assets/js/site-tools.js" defer></script>
</body>
</html>
"""


def build_live_description(source_slug: str, source_name: str, summary: str, lane: str = "updates") -> str:
    if lane in LANE_APP_TERM:
        app_term = LANE_APP_TERM[lane]
        combined = (
            f"{summary.rstrip('.')}."
            f" Covers what {source_name} signals mean for {app_term} workflows, with practical checks and next steps."
        )
        description = clip_text(combined, limit=158)
        if len(description) < 150:
            description = clip_text(f"{description.rstrip('.')} with source-backed workflow guidance.", limit=158)
        if len(description) > 160:
            description = (
                f"{source_name} update for {app_term} workflows, with practical checks, source context, "
                "and next steps readers can verify today."
            )
        if len(description) > 160:
            description = description[:157].rstrip(" ,.;") + "..."
        description = description.replace("'", "")
        return description
    suffix = {
        "apple": f" Covers upgrade relevance, storage impact, and what {source_name} signals mean for cleanup planning.",
        "ai": f" Covers workflow impact, deployment relevance, and what {source_name} signals mean for teams evaluating AI changes.",
        "bluetooth": f" Covers application impact, rollout risk, and what {source_name} signals mean for Bluetooth product teams.",
    }[source_slug]
    combined = f"{summary.rstrip('.')}." + suffix
    description = clip_text(combined, limit=158)
    if len(description) < 150:
        description = clip_text(f"{description.rstrip('.')} with practical checks for readers.", limit=158)
    return description


def strip_suffix(title: str, suffix: str) -> str:
    if title.endswith(suffix):
        return title[: -len(suffix)].rstrip(" :|-")
    return title


def rewritten_story_focus(source_slug: str, item: FeedItem) -> tuple[str, str]:
    raw = clean_text(item.title)
    lowered = raw.lower()
    if source_slug == "apple":
        if any(keyword in lowered for keyword in ("storage", "1tb", "128gb", "icloud", "backup", "files", "nas", "drive")):
            if "iphone" in lowered:
                if "fold" in lowered and any(keyword in lowered for keyword in ("ram", "storage", "pricing")):
                    return (
                        "iPhone Fold Storage Rumors for Cleanup-Minded Buyers",
                        "March 2026 Apple commentary on iPhone Fold RAM, storage, and pricing signals that matter for cleanup-minded buyers weighing long-term capacity pressure.",
                    )
                if "fold" in lowered and any(keyword in lowered for keyword in ("1tb", "price", "money")):
                    return (
                        "iPhone Fold 1TB Price Rumor: What Cleanup Users Should Know",
                        "March 2026 Apple commentary on the iPhone Fold 1TB price rumor, storage planning, and what cleanup-conscious users should weigh before buying.",
                    )
                return (
                    "iPhone storage planning: what cleanup users should notice",
                    "March 2026 Apple commentary on storage planning, backup pressure, and the cleanup decisions that matter before capacity pain becomes a daily problem.",
                )
            if "mac" in lowered or "macbook" in lowered:
                if "back up" in lowered or "backup" in lowered or "macos tahoe" in lowered:
                    return (
                        "How to Back Up Your Mac Without a Storage Mess",
                        "March 2026 Apple commentary on backing up a Mac under macOS Tahoe while avoiding the storage mistakes that make cleanup harder later.",
                    )
                return (
                    "Mac backup planning: what cleanup users should notice",
                    "March 2026 Apple commentary on backup planning, file growth, and the cleanup decisions Mac users should make before storage becomes a workflow bottleneck.",
                )
            return (
                "Apple storage changes: what cleanup users should notice",
                "March 2026 Apple commentary focused on file growth, capacity planning, and cleanup implications for users managing storage across devices.",
            )
        if any(keyword in lowered for keyword in ("airpods", "find my", "tracking", "location", "lost")):
            if "spigen" in lowered and "wallet" in lowered:
                return (
                    "Spigen's Retro MagSafe Wallet Is a Fun Find My Throwback",
                    "March 2026 Apple commentary on Spigen's retro MagSafe wallet, Find My appeal, and why finder-minded accessory buyers may actually click on this one.",
                )
            if "airpods max" in lowered and any(keyword in lowered for keyword in ("launch date", "reveal", "ios 26.4")):
                return (
                    "AirPods Max 2 Launch Date: Why Find Users Will Care",
                    "March 2026 Apple commentary on the AirPods Max 2 launch timeline, nearby-device habits, and why Find-focused users should care about the rollout.",
                )
            if "wallet" in lowered and "find my" in lowered:
                return (
                    "FineWoven Wallet Review: Is Find My Tracking Worth It?",
                    "March 2026 Apple commentary on FineWoven Wallet tracking, Find My usefulness, and whether the accessory improves real finder workflows enough to matter.",
                )
            if "airpods max" in lowered and any(keyword in lowered for keyword in ("audio", "improvements", "upgrades")):
                return (
                    "AirPods Max 2 Audio Upgrades for Bluetooth Users",
                    "March 2026 Apple commentary on AirPods Max 2 audio upgrades and the Bluetooth details most likely to shape listener interest and accessory expectations.",
                )
            return (
                "Apple finding changes: what Find users should notice",
                "March 2026 Apple commentary focused on nearby finding, last-seen workflows, and recovery signals that shape real device-finding experiences.",
            )
        return (
            "Apple ecosystem changes: what Find users should notice",
            "March 2026 Apple commentary connecting the update to practical device-finding, accessory behavior, and ecosystem workflow changes.",
        )
    if source_slug == "ai":
        if any(keyword in lowered for keyword in ("storage", "files", "nas", "drive", "backup")):
            return (
                "AI for storage workflows: what cleanup users should notice",
                "March 2026 AI commentary focused on how new models or tools affect cleanup, file handling, and storage-heavy workflows.",
            )
        if any(keyword in lowered for keyword in ("agent", "agents", "evals", "model", "chatgpt", "gpt", "reasoning")):
            return (
                "AI workflow changes: what users should notice",
                "March 2026 AI commentary explaining capability changes in terms of real automation, assistant quality, and user workflow impact.",
            )
        return (
            "AI workflow update: what users should notice",
            "March 2026 AI commentary focused on practical workflow change rather than headline-only release notes.",
        )
    if any(keyword in lowered for keyword in ("auracast", "broadcast audio")):
        if "frankfurt airport" in lowered or "airport" in lowered:
            return (
                "Auracast at Frankfurt Airport: Why Broadcast Audio Matters",
                "March 2026 Bluetooth commentary on Auracast at Frankfurt Airport, broadcast audio rollout, and why Bluetooth teams should watch real public deployment closely.",
            )
        if "story of auracast" in lowered:
            return (
                "Auracast Broadcast Audio Is Starting to Feel Real",
                "March 2026 Bluetooth commentary on Auracast broadcast audio, rollout momentum, and why Bluetooth teams are starting to treat it like a real deployment story, not just a spec promise.",
            )
        return (
            "Auracast Broadcast Audio: Why Bluetooth Teams Still Care",
            "March 2026 Bluetooth commentary on Auracast broadcast audio, rollout momentum, and why Bluetooth teams keep paying attention to real deployment signals.",
        )
    if any(keyword in lowered for keyword in ("tracking", "monitoring", "industrial", "supply")):
        if "wiliot" in lowered:
            return (
                "How Wiliot Shows Bluetooth Tracking at Industrial Scale",
                "March 2026 Bluetooth commentary on the Wiliot case study and how Bluetooth tracking is proving its value at industrial scale.",
            )
        if "industrial spaces" in lowered:
            return (
                "Why Bluetooth Monitoring Is Catching On in Industrial Spaces",
                "March 2026 Bluetooth commentary on why industrial monitoring, tracking, and predictive maintenance are making Bluetooth more relevant in physical operations.",
            )
        if "supply" in lowered:
            return (
                "How Bluetooth Tracking Is Turning into Real Industrial ROI",
                "March 2026 Bluetooth commentary on an industrial supply-chain case study that shows where Bluetooth tracking is delivering measurable operational value.",
            )
        return (
            "Bluetooth in Industrial Monitoring: Why Tracking Matters",
            "March 2026 Bluetooth commentary on industrial monitoring, tracking, and predictive maintenance, with a focus on why Bluetooth deployments are gaining practical momentum.",
        )
    if any(keyword in lowered for keyword in ("connection interval", "shorter connection intervals")):
        return (
            "Bluetooth shorter connection intervals: why they matter",
            "March 2026 Bluetooth commentary on latency, timing, and implementation tradeoffs behind shorter connection intervals and faster product response.",
        )
    if any(keyword in lowered for keyword in ("indoor", "navigation", "position")):
        return (
            "Bluetooth indoor navigation: what changed",
            "March 2026 Bluetooth commentary on indoor navigation, positioning potential, and the deployment questions product teams should validate next.",
        )
    label = story_label(raw, limit=30)
    return (
        f"Bluetooth Protocol: {label}",
        f"May 2026 Bluetooth protocol commentary on {label}, focused on pairing behavior, device discovery, interoperability, signal reliability, and what product teams should test before rollout.",
    )


def title_for_item(source_slug: str, item: FeedItem) -> str:
    return rewritten_story_focus(source_slug, item)[0]


def looks_garbled(value: str) -> bool:
    return any(ord(ch) > 127 for ch in value)


def clean_summary(source_slug: str, source_name: str, item: FeedItem) -> str:
    cleaned = clean_text(item.summary)
    if cleaned and not looks_garbled(cleaned):
        lowered = cleaned.lower()
        for marker in ("subscribe to", "discuss this article", "related roundup", "buyer's guide", "related forum", "this article,"):
            marker_index = lowered.find(marker)
            if marker_index > 0:
                cleaned = cleaned[:marker_index].strip()
                lowered = cleaned.lower()
        cleaned = cleaned.encode("ascii", "ignore").decode().strip()
        if cleaned:
            return clip_text(cleaned, limit=210)
    fallback = {
        "apple": f"Latest Apple product commentary from {source_name} focused on feature changes, performance impact, pricing position, and upgrade relevance.",
        "ai": f"Latest AI technology commentary from {source_name} focused on capability changes, product impact, and what teams should watch next.",
        "bluetooth": f"Latest Bluetooth commentary from {source_name} focused on standards changes, application impact, and what product teams should watch next.",
    }[source_slug]
    return fallback


def feed_item_from_curated_page(page: CuratedPage) -> FeedItem | None:
    try:
        html = cached_fetch_bytes(page.url).decode("utf-8", errors="ignore")
    except Exception:
        return None
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = clean_text(title_match.group(1)) if title_match else ""
    title = re.sub(r"\s*\|\s*Bluetooth.*$", "", title, flags=re.IGNORECASE).strip()
    desc_match = re.search(r'<meta\s+name="description"\s+content="(.*?)"\s*/?>', html, re.IGNORECASE | re.DOTALL)
    description = clean_text(desc_match.group(1)) if desc_match else ""
    if not title:
        return None
    return FeedItem(title=title, link=page.url, summary=description, published_at=None, image_url="")


def current_status_heading(source_slug: str) -> str:
    return {
        "apple": "Current Status: Apple Product Commentary Needs Feature and Performance Context",
        "ai": "Current Status: AI Release Analysis Needs Capability and Workflow Context",
        "bluetooth": "Current Status: Bluetooth Update Coverage Needs Standards and Application Context",
    }[source_slug]


def current_status_body(source_slug: str, source_name: str, source_published: str) -> str:
    return {
        "apple": f"As of {source_published}, Apple product updates are most useful when readers can see feature changes, performance tradeoffs, repairability, pricing position, and ecosystem impact instead of only launch headlines. Source monitoring from {source_name} helps turn a new release into clear buyer and developer context.",
        "ai": f"As of {source_published}, AI release updates are most useful when readers can see capability shifts, deployment implications, workflow impact, pricing or access changes, and what teams should test next. Source monitoring from {source_name} helps translate fast-moving AI news into practical product decisions.",
        "bluetooth": f"As of {source_published}, Bluetooth updates are most useful when readers can see what changed in standards, interoperability, applications, and deployment tradeoffs instead of only vendor claims. Source monitoring from {source_name} matters when it turns technical announcements into implementation context.",
    }[source_slug]


def opening_intro_for(source_slug: str, title: str, summary: str) -> str:
    return {
        "apple": f"This Apple feature and performance update looks at {title} through product positioning, feature relevance, repairability, and real-world upgrade value. Instead of stopping at a launch headline, it connects the update to practical buyer intent, developer implications, and the Apple ecosystem signals that matter most in 2026. {summary}",
        "ai": f"This AI technology outlook looks at {title} through model capability, workflow impact, deployment relevance, and product strategy. Instead of stopping at an announcement, it explains what changed, why it matters for builders and teams, and how the update fits the broader direction of AI products in 2026. {summary}",
        "bluetooth": f"This Bluetooth standards and application update looks at {title} through interoperability, deployment impact, and product-level relevance. Instead of stopping at a standards headline, it translates the update into practical Bluetooth implementation context for teams and readers in 2026. {summary}",
    }[source_slug]


def table_rows_for(source_slug: str) -> list[tuple[str, str, str]]:
    return {
        "apple": [
            ("Feature changes", "What Apple added, removed, or repositioned", "Helps readers understand the real scope of the update"),
            ("Performance angle", "Speed, battery, thermals, repairability, or component shifts", "Turns launch news into measurable product commentary"),
            ("Lineup fit", "Where the product sits against iPhone, iPad, Mac, or accessory tiers", "Improves upgrade and buying relevance"),
            ("Ecosystem impact", "Effect on developers, accessories, workflows, or services", "Shows who needs to change a plan, setup, or buying decision"),
        ],
        "ai": [
            ("Capability shift", "What changed in models, tools, or agent behavior", "Helps readers separate real progress from headline noise"),
            ("Workflow impact", "How the update affects coding, research, automation, or enterprise use", "Connects AI news to practical usage"),
            ("Access and deployment", "Availability, retirement, pricing, or rollout changes", "Improves decision quality for teams evaluating adoption"),
            ("Strategic outlook", "What this means for product roadmaps and competitive positioning", "Makes the article more useful than a news summary"),
        ],
        "bluetooth": [
            ("Standards update", "What changed in Bluetooth specs or ecosystem guidance", "Clarifies whether the update affects shipping products"),
            ("Application impact", "Where the change matters in discovery, audio, mesh, or telemetry", "Connects standards language to real deployments"),
            ("Compatibility risk", "What teams should test across firmware, chips, OS, and apps", "Improves technical usefulness"),
            ("Adoption outlook", "How quickly the change may influence products or infrastructure", "Adds planning value for readers"),
        ],
    }[source_slug]


def interpretation_heading_for(source_slug: str) -> str:
    return {
        "apple": "Feature Commentary",
        "ai": "Capability Commentary",
        "bluetooth": "Standards Commentary",
    }[source_slug]


def application_heading_for(source_slug: str) -> str:
    return {
        "apple": "Performance and Product Positioning",
        "ai": "Workflow and Product Implications",
        "bluetooth": "Application and Deployment Implications",
    }[source_slug]


def interpretation_body_for(source_slug: str, item: FeedItem, summary: str) -> str:
    title = clean_text(item.title)
    return {
        "apple": f"{title} is more than a launch note when it changes which Apple product behaviors matter, what stayed the same, and whether the feature update improves everyday usage, serviceability, accessory fit, or long-term upgrade value. {summary} A useful Apple feature read also asks whether the change improves camera, battery, thermals, portability, or the ecosystem fit that often decides whether an upgrade is worth it.",
        "ai": f"{title} is more than an announcement when it changes model capability, developer workflow, agent reliability, deployment planning, or the economics of using AI in production. {summary} A useful AI model read also explains whether the release changes what teams can automate, what tradeoffs they inherit, and whether product quality or operating cost shifts in a meaningful way.",
        "bluetooth": f"{title} is most useful when read in terms of standards meaning, interoperability, and application consequences. The main value comes from mapping the update to device discovery, audio, telemetry, power, or rollout decisions. {summary}",
    }[source_slug]


def application_body_for(source_slug: str) -> str:
    return {
        "apple": "Readers, buyers, and developers care most about where the new feature or performance change fits in the lineup. The practical value is in upgrade relevance, tradeoffs versus nearby products, and whether the change improves real workflows rather than only spec-sheet perception. It also helps clarify who does not need the update, which compromises still remain, and whether the product changes buying logic inside the current Apple range.",
        "ai": "Teams care most about what the release changes in real usage. The practical value is in whether a new model, retirement, or capability shift changes product quality, automation design, safety posture, or cost decisions for actual teams. It also helps clarify whether the update changes evaluation criteria, tool choice, model routing, or the balance between speed, quality, and operating cost.",
        "bluetooth": "Teams care most about where a standards or ecosystem update changes implementation reality. Useful Bluetooth analysis explains whether the change affects reliability, compatibility, deployment timing, or product experience in a measurable way.",
    }[source_slug]


def next_heading_for(source_slug: str) -> str:
    return {
        "apple": "What To Watch Next",
        "ai": "What To Watch Next",
        "bluetooth": "What To Watch Next",
    }[source_slug]


def next_body_for(source_slug: str) -> str:
    return {
        "apple": "The next question is whether independent testing, teardowns, benchmarks, and real user feedback support the first wave of Apple product claims. Readers should track whether the feature or performance story remains compelling after launch-day attention fades, and whether accessories, developers, and the broader lineup reinforce or weaken the case for the update.",
        "ai": "The next question is whether this AI update changes evaluation baselines, pricing logic, deployment planning, or model choice in real products. Teams should track how the release affects practical workloads, whether the capability gain holds up under real usage, and whether access, safety, or product integration changes what they do next.",
        "bluetooth": "The next question is whether the update moves from standards language into practical implementation value. Teams should track vendor adoption, compatibility signals, firmware support, and whether the update changes deployment planning, interoperability, or product-level user experience.",
    }[source_slug]


def search_intent_heading_for(source_slug: str) -> str:
    return {
        "apple": "Upgrade Questions",
        "ai": "Adoption Questions",
        "bluetooth": "Deployment Questions",
    }[source_slug]


def search_intent_body_for(source_slug: str) -> str:
    return {
        "apple": "Readers usually need four answers before an Apple update matters: what changed, what stayed the same, how it compares with nearby models, and whether the change affects daily use. Useful analysis separates lineup positioning from practical value, because a spec bump that looks large in a launch headline can still be irrelevant for battery life, repairability, accessory fit, or the way someone actually uses the device.",
        "ai": "Readers usually need to know what changed in capability, whether the change holds up in real workflows, how pricing or access affects adoption, and what teams should test before switching tools. Useful AI analysis connects the release to concrete work: development, automation, review quality, latency, safety, reliability, or enterprise rollout decisions.",
        "bluetooth": "Readers usually need to know what changed in the standard, where the change matters in applications, how interoperability is affected, and whether deployment plans should change. Useful Bluetooth analysis translates technical language into validation steps across chips, firmware, apps, operating systems, and real devices.",
    }[source_slug]


def retrieval_fit_body_for(source_slug: str) -> str:
    return {
        "apple": "Useful Apple coverage names the product clearly, explains the practical change early, and compares the update against nearby Apple options. Readers need the feature review, performance impact, and upgrade value in one place because those decisions are connected in real buying behavior.",
        "ai": "Useful AI coverage names the model, product, or release clearly, explains the practical capability shift early, and ties the change to a workflow someone can test. Readers need capability analysis, deployment implications, and next-step guidance together because switching AI tools without a test plan is mostly guesswork.",
        "bluetooth": "Useful Bluetooth coverage names the standard, update, or application clearly, explains the implementation impact early, and identifies the compatibility checks that matter. Readers need standards meaning, interoperability risk, and deployment guidance together because Bluetooth changes only matter after devices actually work together.",
    }[source_slug]


def challenge_intro_for(source_slug: str) -> str:
    return {
        "apple": "Apple product updates are hardest to judge when they stay too close to launch marketing and do not explain how the change affects buying logic or long-term usability.",
        "ai": "AI releases are hardest to judge when they repeat headline capability claims and skip deployment tradeoffs, operational constraints, or workflow relevance.",
        "bluetooth": "Bluetooth updates are hardest to judge when they repeat standards language without explaining what changes for product teams, users, or deployment planning.",
    }[source_slug]


def challenge_items_for(source_slug: str) -> list[str]:
    return {
        "apple": [
            "Launch headlines rarely explain lineup overlap clearly.",
            "Performance claims need workflow context, not just benchmark framing.",
            "Repairability, battery, and accessory impact are often underexplained.",
            "Naming and tiering can confuse users comparing adjacent Apple products.",
            "Buying advice gets weaker when it avoids a clear recommendation for who should wait.",
        ],
        "ai": [
            "Headline capability claims can overstate practical workflow impact.",
            "Model retirement or rollout changes often affect teams more than demos do.",
            "Access, pricing, and deployment details are easy to miss in fast AI coverage.",
            "Safety and reliability tradeoffs need to be stated directly for readers.",
            "Adoption advice gets weaker when it skips evaluation tasks teams can actually run.",
        ],
        "bluetooth": [
            "Standards language can hide what actually changes for shipping products.",
            "Compatibility and rollout risks are often more important than feature headlines.",
            "Application examples need to connect clearly to real device workflows.",
            "Teams need implementation context across chips, OS versions, and firmware.",
            "Deployment advice gets weaker when it skips interoperability and firmware checks.",
        ],
    }[source_slug]


def faq_items_for(source_slug: str) -> list[tuple[str, str]]:
    return {
        "apple": [
            ("How should readers evaluate a new Apple feature or performance claim?", "Compare the change against prior Apple products, then focus on real workflow impact such as speed, battery life, repairability, accessory fit, or software usefulness."),
            ("What makes Apple product commentary useful?", "Useful Apple commentary answers upgrade, comparison, and feature-impact questions directly, rather than repeating launch marketing language."),
            ("Why does product positioning matter in Apple coverage?", "Apple updates are easiest to evaluate when readers can see where the new feature or performance change fits across nearby iPhone, iPad, Mac, or accessory tiers."),
        ],
        "ai": [
            ("How should readers evaluate a new AI release or capability claim?", "Start with the primary source, then ask what changed in model behavior, workflow value, access, pricing, and deployment tradeoffs for real users or teams."),
            ("What makes AI technology outlook articles useful?", "Strong AI outlook articles answer capability, workflow, pricing, and adoption questions in clear language, then give teams a practical next test."),
            ("Why do AI launch notes need extra commentary?", "Because raw announcements rarely explain how the update affects product planning, automation design, or whether teams should change what they use next."),
        ],
        "bluetooth": [
            ("How should readers evaluate a new Bluetooth update or standards claim?", "Check the primary source, then focus on what changed in interoperability, applications, rollout timing, and compatibility risk for real products."),
            ("What makes Bluetooth commentary useful?", "Strong Bluetooth commentary translates technical updates into deployment, application, and troubleshooting context that teams can validate on real devices."),
            ("Why is application context important in Bluetooth coverage?", "Because standards updates only become useful when readers understand how they affect discovery, audio, mesh, telemetry, power, or product planning."),
        ],
    }[source_slug]


def render_live_article(day: date, source_slug: str, source_name: str, item: FeedItem, post: PostMeta, lane: str = "updates") -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    source_published = item.published_at.astimezone().strftime("%B %d, %Y") if item.published_at else human_date
    summary = lane_summary(lane, source_slug, source_name, item)
    opening_intro = opening_intro_for(source_slug, clean_text(item.title), summary)
    keyword_coverage = keywords_for_lane(lane, source_slug) + [slugify(item.title).replace("-", " ")]
    faq_items = faq_items_for(source_slug)
    challenge_items = challenge_items_for(source_slug)
    table_rows = table_rows_for(source_slug)

    table_html = "\n".join(
        f"          <tr><td>{escape(col1)}</td><td>{escape(col2)}</td><td>{escape(col3)}</td></tr>"
        for col1, col2, col3 in table_rows
    )
    keyword_html = "\n".join(f"          <li>{escape(item)}</li>" for item in keyword_coverage[:6])
    challenge_html = "\n".join(f"          <li>{escape(item)}</li>" for item in challenge_items)
    tldr = (
        f"As of {human_date}, {post.title.lower()} matters because it turns a fresh {source_name} item into deployment guidance. "
        "The practical question is what changed, where it affects products, and what teams should verify next."
    )
    validation_items = {
        "apple": [
            "Compare the claim with the device, OS version, storage tier, and accessory setup users actually have.",
            "Separate launch positioning from measurable changes such as performance, battery life, repairability, app behavior, or upgrade timing.",
            "Check whether the update creates an immediate decision or only informs a future purchase, rollout, or support note.",
            "Avoid changing recommendations until the source detail is confirmed against the user's current Apple product context.",
        ],
        "ai": [
            "Map the announcement to one workflow: generation quality, latency, tool use, safety review, pricing, access, or deployment reliability.",
            "Run a small comparison task before changing model routing, automation design, or user-facing behavior.",
            "Check whether the update changes evaluation criteria or simply adds context to a tool the team already understands.",
            "Keep human review in place when the update affects high-stakes wording, privacy, permissions, or production automation.",
        ],
        "bluetooth": [
            "Test the change on real hardware instead of relying only on standards or vendor wording.",
            "Check pairing, discovery, RSSI behavior, connection intervals, audio path, firmware version, and OS compatibility where relevant.",
            "Look for edge cases across older devices, crowded radio environments, and mixed chipset deployments.",
            "Treat the source as a planning signal until interoperability tests confirm the behavior in the target product.",
        ],
    }[source_slug]
    validation_html = "\n".join(f"          <li>{escape(item)}</li>" for item in validation_items)
    no_change_items = {
        "apple": [
            "The update affects a model, market, or OS version outside the user's current upgrade window.",
            "The source does not include enough detail to change buying, support, or storage planning advice.",
            "The decision depends on hands-on performance, repair data, battery behavior, or app compatibility that is not available yet.",
        ],
        "ai": [
            "The release changes positioning but not the team's actual workflow, cost profile, access path, or quality bar.",
            "The source is too early to justify changing production automation, user promises, or compliance review.",
            "The current toolchain already handles the task reliably and the update does not improve a measurable bottleneck.",
        ],
        "bluetooth": [
            "The update does not affect the profiles, chipsets, operating systems, or environments used by the target product.",
            "The source is about a consumer deal or broad trend rather than interoperability, protocol behavior, or application design.",
            "The team cannot reproduce the behavior on real devices, so the item should stay as background context.",
        ],
    }[source_slug]
    no_change_html = "\n".join(f"          <li>{escape(item)}</li>" for item in no_change_items)
    faq_html = "\n".join(
        f"      <p><strong>{escape(question)}</strong><br>\n      {escape(answer)}</p>\n"
        for question, answer in faq_items
    )
    source_links = [(f"{source_name}: {clean_text(item.title)}", item.link), *background_links_for(source_slug)]
    source_links_html = "\n".join(
        f'          <li><a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(label)}</a></li>'
        for label, url in source_links
    )
    keywords = ", ".join(keyword_coverage)

    return f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(post.title)} | VelocAI Blog</title>
  <meta name="description" content="{escape(post.description)}">
  <meta name="keywords" content="{escape(keywords)}">
  <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
  <link rel="canonical" href="{escape(canonical)}">
  <link rel="icon" type="image/x-icon" href="/velocai.ico">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="en_US">
  <meta property="og:site_name" content="VelocAI">
  <meta property="og:title" content="{escape(post.title)}">
  <meta property="og:description" content="{escape(post.description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:image" content="https://velocai.net/2.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(post.title)}">
  <meta name="twitter:description" content="{escape(post.description)}">
  <meta name="twitter:image" content="https://velocai.net/2.png">
  <script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "BlogPosting",
      "headline": {json_string(post.title)},
      "description": {json_string(post.description)},
      "datePublished": {json_string(post.published_iso)},
      "dateModified": {json_string(post.published_iso)},
      "author": {{"@type": "Organization", "name": "VelocAI"}},
      "publisher": {{
        "@type": "Organization",
        "name": "VelocAI",
        "logo": {{"@type": "ImageObject", "url": "https://velocai.net/2.png"}}
      }},
      "mainEntityOfPage": {json_string(canonical)},
      "keywords": {json.dumps(keyword_coverage[:8], ensure_ascii=False)}
    }},
    {{
      "@type": "FAQPage",
      "mainEntity": [
        {json.dumps([{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_items], ensure_ascii=False)[1:-1]}
      ]
    }}
  ]
}}
  </script>
  <style>
    :root {{ --bg:#f4f9ff; --text:#1a2838; --muted:#4b6178; --line:#cfe0f1; --panel:#ffffff; --brand:#1d63c7; --brand-soft:#e6f2ff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Inter","Segoe UI",sans-serif; color:var(--text); background:radial-gradient(circle at 8% 2%, rgba(66,139,233,.18), transparent 34%), radial-gradient(circle at 88% -6%, rgba(47,195,170,.14), transparent 32%), var(--bg); line-height:1.72; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ width:min(920px, calc(100% - 34px)); margin:0 auto; }}
    header {{ border-bottom:1px solid var(--line); background:rgba(244,249,255,.92); }}
    .top {{ padding:14px 0; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }}
    .brand {{ display:inline-flex; align-items:center; gap:10px; font-weight:700; }}
    .brand img {{ width:auto; height:36px; max-width:52px; object-fit:contain; object-position:center; border-radius:10px; box-shadow:0 0 16px rgba(29,99,199,.16); }}
    nav {{ display:flex; gap:12px; flex-wrap:wrap; color:var(--muted); font-size:14px; }}
    nav a:hover {{ color:var(--text); }}
    main {{ padding:36px 0 56px; }}
    h1,h2,h3 {{ margin:0; line-height:1.22; }}
    h1 {{ font-size:clamp(30px, 4.2vw, 48px); max-width:24ch; }}
    h2 {{ margin-top:30px; font-size:clamp(24px, 3vw, 34px); }}
    p,li,td,th {{ color:#30475f; font-size:17px; }}
    ul,ol {{ padding-left:22px; }}
    .meta {{ margin-top:10px; color:var(--muted); font-size:14px; }}
    .hero, .panel, .tldr, .capsule, table {{ background:var(--panel); border:1px solid var(--line); border-radius:24px; }}
    .hero {{ padding:26px; box-shadow:0 14px 32px rgba(24,36,54,.05); }}
    .panel, .tldr, .capsule {{ margin-top:24px; padding:22px; box-shadow:0 14px 32px rgba(24,36,54,.05); }}
    .tldr {{ border-left:6px solid #2fc3aa; }}
    .capsule {{ background:#f8fbff; }}
    .eyebrow {{ display:inline-flex; margin-bottom:14px; border-radius:999px; padding:8px 12px; background:var(--brand-soft); color:var(--brand); font-size:13px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }}
    .hero > p:not(.meta) {{ margin:14px 0 0; max-width:none; }}
    .cta-row,.links {{ margin-top:32px; display:flex; gap:14px; flex-wrap:wrap; }}
    .cta-row a,.links a {{ border:1px solid #bdd7de; border-radius:999px; padding:10px 14px; font-weight:600; font-size:14px; color:var(--brand); background:#fff; }}
    .cta-row .primary {{ background:var(--brand); color:#fff; border-color:var(--brand); }}
    table {{ width:100%; margin-top:24px; border-collapse:separate; border-spacing:0; overflow:hidden; }}
    th,td {{ padding:16px 18px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    tr:last-child td {{ border-bottom:none; }}
    th {{ color:var(--text); font-weight:700; background:rgba(29,99,199,.08); }}
    .sources a {{ color:var(--brand); border-bottom:1px solid #9fcad0; }}
  </style>
  <link rel="stylesheet" href="/assets/css/site-tools.css">
</head>
<body>
  <header>
    <div class="wrap top">
      <a class="brand" href="/">
        <img src="/velocai.png" alt="VelocAI logo" width="102" height="73">
        <span>VelocAI Blog</span>
      </a>
      <nav aria-label="Main">
        <a href="/">Home</a>
        <a href="/apps/">Apps</a>
        <a href="/blog/">Blog</a>
        <a href="/bluetoothexplorer/">Bluetooth Explorer</a>
      </nav>
    </div>
  </header>

  <main class="wrap">
    <article>
      <div class="hero">
        <h1>{escape(post.title)}</h1>
        <p class="meta">Published on {escape(human_date)} | Topic: {escape(post.topic)} | Source: {escape(source_name)} | Source date: {escape(source_published)}</p>
        <p>{escape(opening_intro)}</p>
      </div>

      <div class="tldr">
        <p><strong>TL;DR:</strong> {escape(tldr)}</p>
      </div>

      <h2>What changed in {escape(day.strftime("%B %Y"))}?</h2>
      <p>{escape(current_status_body(source_slug, source_name, source_published))}</p>

      <table aria-label="{escape(post.topic)} commentary coverage">
        <thead>
          <tr><th>Commentary area</th><th>What it covers</th><th>Why it matters</th></tr>
        </thead>
        <tbody>
{table_html}
        </tbody>
      </table>

      <h2>Why does this update matter?</h2>
      <p>{escape(interpretation_body_for(source_slug, item, summary))} {escape(retrieval_fit_body_for(source_slug))}</p>
      <div class="capsule">
        <p><strong>Reader note:</strong> As of {human_date}, {escape(post.title.lower())} is useful only if it changes implementation, interoperability, workflow impact, or the next validation step. The useful part is the decision it helps a reader make next.</p>
      </div>

      <h2>Product Impact Areas</h2>
      <p>{escape(application_body_for(source_slug))}</p>
      <div class="capsule">
        <p><strong>Practical note:</strong> The product value of this item depends on where it changes real workflows such as deployment timing, compatibility checks, or user-facing behavior. Teams benefit most when they map the source detail to practical validation and rollout decisions.</p>
      </div>

      <h2>What should teams watch next?</h2>
      <p>{escape(next_body_for(source_slug))} {escape(search_intent_body_for(source_slug))}</p>

      <h2>Validation Before Acting</h2>
      <p>A fresh source is most useful when it becomes a small validation plan. Teams should keep the test narrow enough to run quickly and specific enough to change a real product or workflow decision.</p>
      <ol>
{validation_html}
      </ol>

      <div class="panel">
        <h2>What are the key risks in 2026?</h2>
        <p>{escape(challenge_intro_for(source_slug))}</p>
        <ol>
{challenge_html}
        </ol>
      </div>

      <h2>When does the update not matter?</h2>
      <p>The item should not drive a roadmap, rollout, or recommendation unless it changes a concrete user outcome. It is reasonable to log it as context when the following limits apply.</p>
      <ul>
{no_change_html}
      </ul>

      <h2>FAQ</h2>
{faq_html}
      <section class="sources" aria-label="Source attribution">
        <h3>Source attribution</h3>
        <ul>
{source_links_html}
        </ul>
      </section>

      <div class="links">
        <a href="/blog/">Back to blog index</a>
        <a href="/apps/">Browse VelocAI apps</a>
      </div>
    </article>
  </main>
  <script src="/assets/js/site-tools.js" defer></script>
</body>
</html>
"""


def build_candidate_from_item(
    target_day: date,
    source_slug: str,
    source_name: str,
    item: FeedItem,
    *,
    lane: str = "updates",
    filename: str | None = None,
) -> LiveBlogCandidate:
    require_recent_news_source(item, target_day)
    resolved_filename = filename or f"{article_prefix_for_lane(lane, source_slug)}-{slugify(item.title)}-{target_day.isoformat()}.html"
    lane_focus = lane_story_focus(lane, source_slug, item)
    title, rewritten_summary = lane_focus if lane_focus is not None else rewritten_story_focus(source_slug, item)
    summary = rewritten_summary if rewritten_summary else lane_summary(lane, source_slug, source_name, item)
    if lane in LANE_APP_TERM:
        opening_intro = lane_summary(lane, source_slug, source_name, item)
    else:
        opening_intro = opening_intro_for(source_slug, clean_text(item.title), summary)
    description = build_live_description(source_slug, source_name, summary, lane)
    post = PostMeta(
        filename=resolved_filename,
        title=title,
        description=description,
        teaser=clip_text(opening_intro, limit=160),
        topic=topic_for_lane(lane, source_slug),
        published_iso=target_day.isoformat(),
    )
    if lane in LANE_APP_TERM:
        html = render_app_live_article(target_day, source_slug, source_name, item, post, lane)
    else:
        html = render_live_article(target_day, source_slug, source_name, item, post, lane)
    return LiveBlogCandidate(post=post, html=html, link=item.link, source_name=source_name)


def unique_feed_items_for_lane(lane: str, target_day: date) -> list[tuple[str, str, FeedItem]]:
    if lane not in LANE_SOURCE_SLUGS:
        return []
    collected: list[tuple[str, str, FeedItem]] = []
    seen_links: set[str] = set()
    for source in source_pool_for_lane(lane):
        try:
            items = parse_feed_items(cached_fetch_bytes(source.feed_url))
        except Exception:
            continue
        for item in items:
            if not is_recent_news_source(item, target_day):
                continue
            title_text = clean_text(item.title).lower()
            haystack = f"{title_text} {clean_text(item.summary)}".lower()
            required = LANE_REQUIRED_KEYWORDS[lane]
            if not item_matches_lane_intent(lane, source.slug, title_text, haystack):
                continue
            padded_title = f" {clean_text(item.title).lower()} "
            if any(pattern in padded_title for pattern in NOISE_PATTERNS):
                continue
            if score_item(item, source.keywords) <= 0 and not any(matches_keyword(haystack, keyword) for keyword in required[:4]):
                continue
            if not item.link or item.link in seen_links:
                continue
            seen_links.add(item.link)
            collected.append((render_source_slug_for_lane(lane, source.slug), source.source_name, item))
    collected.sort(key=lambda entry: entry[2].published_at.timestamp() if entry[2].published_at else 0.0, reverse=True)
    return collected


def build_live_candidates(target_day: date, lane: str) -> list[LiveBlogCandidate]:
    return [
        build_candidate_from_item(target_day, source_slug, source_name, item, lane=lane)
        for source_slug, source_name, item in unique_feed_items_for_lane(lane, target_day)
    ]
