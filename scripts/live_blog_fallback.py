#!/usr/bin/env python3
"""Generate SEO/GEO-friendly blog fallback candidates from live news feeds."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import date, timedelta
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
MAX_SOURCE_AGE_DAYS = 365


NOISE_PATTERNS = (
    " sale ",
    " cheapest ",
    " coupon ",
    " discount ",
    " deal ",
    " buy now ",
    " clearance ",
    " giveaway ",
)

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
    return "A Bluetooth commentary focused on standards, applications, and practical deployment impact."


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
    label = story_label(item.title)
    lowered = f"{clean_text(item.title)} {clean_text(item.summary)}".lower()
    if lane == "cleanup":
        return (
            f"How Cleanup Pro Users Should Read {label}",
            f"A practical Cleanup Pro guide for deciding whether {label} changes iPhone storage cleanup order, backup checks, or safe deletion priorities.",
        )
    if lane == "translate":
        return (
            f"How Translate AI Users Should Read {label}",
            f"A practical Translate AI guide for applying {label} to speech, OCR, captions, travel, and multilingual review workflows.",
        )
    if lane == "find":
        if any(term in lowered for term in ("deal", "price", "discount", "sale", "off", "amazon", "best buy")):
            if any(term in lowered for term in ("airtag", "find my", "tracker", "tag")):
                return (
                    "How Find AI Users Should Read AirTag and Recovery Deals",
                    "A practical Find AI guide for deciding whether cheaper AirTags, spare devices, or accessory pricing changes recovery setup, scan confidence, or privacy boundaries.",
                )
            return (
                "How Find AI Users Should Read Device Deals and Recovery Gear",
                "A practical Find AI guide for deciding whether a sale on nearby hardware changes recovery setup, scan confidence, or last-seen checks.",
            )
        if any(term in lowered for term in ("airtag", "find my", "tracker", "lost", "recovery")):
            return (
                "How Find AI Users Should Read Lost-Device Recovery Signals",
                "A practical Find AI guide for applying this update to nearby scanning, last-seen context, and the line between recovery and tracking.",
            )
        if not any(term in lowered for term in ("find my", "airtag", "tracker", "lost", "recovery", "device", "bluetooth", "earbud", "headphone", "tag", "nearby")):
            return (
                "How Find AI Users Should Treat Background Apple News on Mobile",
                "A practical Find AI guide for deciding whether this background Apple story changes recovery confidence, nearby scanning, or the cost of keeping a second device ready.",
            )
        return (
            f"How find AI Users Should Read {label}",
            f"A practical find AI guide for deciding whether {label} changes Bluetooth signal checks, nearby scanning, or lost-device recovery steps.",
        )
    if lane == "dualshot":
        return (
            f"How Dual Camera Creators Should Read {label}",
            f"A practical Dual Camera guide for applying {label} to creator capture, demo recording, framing, and video repurposing decisions.",
        )
    if lane == "octopus":
        if any(term in lowered for term in ("browser", "architecture", "built", "building", "chatgpt", "openai")):
            return (
                "How Octopus Keeps AI Browser Work Moving on Mobile",
                "A practical Octopus guide for deciding whether this architecture story changes mobile approvals, thread continuity, or the point where desktop review still matters.",
            )
        if not any(term in lowered for term in ("codex", "agent", "ssh", "developer", "approval", "token", "repo", "repository", "workflow", "terminal")):
            return (
                "How Octopus Users Should Treat Background Apple News on Mobile",
                "A practical Octopus guide for deciding whether a background Apple story changes mobile approvals, thread continuity, or whether the task should stay on desktop.",
            )
        return (
            f"How Octopus Users Should Read {label}",
            f"A practical Octopus guide for applying {label} to mobile Codex approvals, thread continuity, SSH-linked work, and iPhone or iPad follow-up.",
        )
    return None


def lane_summary(lane: str, source_slug: str, source_name: str, item: FeedItem) -> str:
    base = clean_summary(source_slug, source_name, item)
    if lane not in LANE_APP_TERM:
        return base
    app_term = LANE_APP_TERM[lane]
    lowered = f"{clean_text(item.title)} {base}".lower()
    if lane == "find":
        if any(term in lowered for term in ("deal", "price", "discount", "sale", "off", "amazon", "best buy")):
            if any(term in lowered for term in ("airtag", "find my", "tracker", "tag")):
                return clip_text(
                    f"{base} For {app_term} readers, the useful question is whether cheaper AirTags or spare devices change recovery setup, scan confidence, or privacy boundaries.",
                    limit=260,
                )
            return clip_text(
                f"{base} For {app_term} readers, the useful question is whether the sale changes recovery hardware, last-seen checks, or the cost of tagging items.",
                limit=260,
            )
        if any(term in lowered for term in ("airtag", "find my", "tracker", "lost", "recovery")):
            return clip_text(
                f"{base} For {app_term} readers, the useful question is whether the clue is strong enough to follow or only worth logging.",
                limit=260,
            )
    if lane == "octopus":
        if any(term in lowered for term in ("browser", "architecture", "built", "building", "chatgpt", "openai")):
            return clip_text(
                f"{base} For {app_term} readers, the useful question is whether this changes mobile approvals, thread continuity, or the next file or command to inspect.",
                limit=260,
            )
        if not any(term in lowered for term in ("codex", "agent", "ssh", "developer", "approval", "token", "repo", "repository", "workflow", "terminal")):
            return clip_text(
                f"{base} For {app_term} readers, this is mostly background context; the real question is whether the current thread still has a clear approval boundary.",
                limit=260,
            )
    return clip_text(
        f"{base} For {app_term} readers, the useful question is whether this changes a real workflow, saves a step, reduces risk, or simply stays background context.",
        limit=260,
    )


def item_matches_lane_intent(lane: str, source_slug: str, title_text: str, haystack: str) -> bool:
    if lane == "cleanup":
        return any(
            matches_keyword(haystack, keyword)
            for keyword in (
                "photo cleanup",
                "iphone storage",
                "ios storage",
                "storage full",
                "system data",
                "icloud backup",
                "backup files",
                "backup data",
                "icloud",
                "icloud drive",
                "deleted",
                "duplicate",
                "cleanup",
                "clean up",
                "screenshots",
                "whatsapp",
                "downloads",
            )
        )
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
        return any(
            matches_keyword(haystack, keyword)
            for keyword in (
                "find my",
                "airtag",
                "lost",
                "location",
                "tracking",
                "asset tracking",
                "ble tracking",
                "bluetooth",
                "beacon",
                "nearby",
                "fast pair",
            )
        )
    if lane == "dualshot":
        return any(
            matches_keyword(haystack, keyword)
            for keyword in (
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
            )
        )
    if lane == "octopus":
        return any(
            matches_keyword(haystack, keyword)
            for keyword in (
                "codex",
                "coding agent",
                "developer tools",
                "remote coding",
                "thread",
                "approval",
                "permissions",
                "ssh",
                "server",
                "terminal",
                "repository",
                "pull request",
                "code review",
                "command approval",
                "chatgpt",
                "tool results",
                "prompt",
            )
        )
    return any(matches_keyword(haystack, keyword) for keyword in LANE_REQUIRED_KEYWORDS[lane])


def item_is_recent_for_target(item: FeedItem, target_day: date) -> bool:
    if item.published_at is None:
        return False
    item_day = item.published_at.date()
    return target_day - timedelta(days=MAX_SOURCE_AGE_DAYS) <= item_day <= target_day + timedelta(days=1)


def app_lane_profile(lane: str) -> dict[str, object]:
    return {
        "cleanup": {
            "eyebrow": "cleanup pro live storage fallback",
            "intent": "duplicate photo cleanup, iPhone storage cleanup, backup hygiene, and safe deletion order",
            "workflow": "review large files, old downloads, duplicate media, offline caches, and backup state before deleting anything important",
            "risk": "cleanup advice becomes weak when it skips backup readiness, hidden caches, or the order in which users should inspect files",
            "primary": "Open AI Cleanup PRO",
            "primary_url": "/ai-cleanup-pro/",
            "product_label": "AI Cleanup PRO product page",
            "product_url": "/ai-cleanup-pro/",
            "secondary": "iPhone storage cleanup",
        },
        "translate": {
            "eyebrow": "Translate live workflow fallback",
            "intent": "translation, OCR, captions, voice input, and multilingual review workflows",
            "workflow": "capture the source text or speech, translate it, review uncertain phrases, and keep context for follow-up conversations",
            "risk": "translation advice becomes weak when it ignores speech quality, OCR errors, idioms, or human review for high-stakes wording",
            "primary": "Open Translate AI",
            "primary_url": "/translate/",
            "product_label": "Translate AI product page",
            "product_url": "/translate/",
            "secondary": "AI translation workflow",
        },
        "find": {
            "eyebrow": "find AI live recovery fallback",
            "intent": "nearby-device discovery, Bluetooth signal reading, last-seen context, and lost-item recovery",
            "workflow": "check the device category, scan nearby signals, compare movement context, and separate a weak signal from a real recovery lead",
            "risk": "finding advice becomes weak when it treats every Bluetooth or location clue as equally trustworthy",
            "primary": "Open Find AI",
            "primary_url": "/aifind/",
            "product_label": "Find AI product page",
            "product_url": "/aifind/",
            "secondary": "device recovery workflow",
        },
        "dualshot": {
            "eyebrow": "Dual Camera live creator fallback",
            "intent": "creator recording, product demos, tutorials, camera framing, and video repurposing",
            "workflow": "plan the main shot, capture the presenter or context angle, protect audio clarity, and repurpose the recording for multiple channels",
            "risk": "creator advice becomes weak when it talks about video trends without explaining capture setup, framing, and editing consequences",
            "primary": "Open Dual Camera",
            "primary_url": "/dualshot/",
            "product_label": "Dual Camera product page",
            "product_url": "/dualshot/",
            "secondary": "creator capture workflow",
        },
        "octopus": {
            "eyebrow": "Octopus live mobile coding fallback",
            "intent": "mobile Codex continuity, approvals, SSH-linked sessions, runtime follow-up, and developer context capture",
            "workflow": "review session state, approve the next action, add voice or file context, and move the coding thread forward without reopening the full desktop setup",
            "risk": "mobile coding advice becomes weak when it promises convenience without explaining approvals, thread continuity, or how remote context gets back into the same workflow",
            "primary": "Open Octopus",
            "primary_url": "/octopus/",
            "product_label": "Octopus product page",
            "product_url": "/octopus/",
            "secondary": "mobile Codex workflow",
        },
    }[lane]


def app_lane_table_rows(lane: str, source_title: str, summary: str = "") -> list[tuple[str, str, str]]:
    signal = source_signal_type(source_title, summary)
    if lane == "octopus" and signal == "enterprise_codex":
        return [
            ("Business context", "Client, portfolio, meeting, and follow-up state", "Shows whether mobile review has enough real-world context to be useful"),
            ("Approval owner", "Who requested the action and who will rely on the output", "Prevents a phone tap from approving work for the wrong banker, client, or thread"),
            ("Traceability", "Saved notes, generated communications, and captured next actions", "Makes enterprise speed auditable instead of merely fast"),
            ("Phone boundary", source_title, "Defines when Octopus should monitor a workflow and when desktop review is required"),
        ]
    if lane == "octopus" and signal == "security_review":
        return [
            ("Security claim", "The file, boundary, invariant, or behavior being questioned", "Keeps mobile review attached to evidence instead of a vague risk label"),
            ("Validation step", "Minimal reproduction, test command, diff, or sandbox result", "Shows whether the finding is real before a human approves a fix"),
            ("Approval scope", "One read, one test, one patch, or one narrow follow-up", "Prevents security work from becoming an open-ended phone approval"),
            ("Desktop handoff", source_title, "Names the point where broad remediation needs a larger screen and fuller context"),
        ]
    return {
        "cleanup": [
            ("Data residue", "What invisible or forgotten files might remain", "Connects cleanup work to privacy, not only free space"),
            ("Delete order", "Backups, large media, downloads, app caches", "Prevents the user from deleting the easiest thing instead of the safest thing"),
            ("Proof check", "What the user can inspect before and after cleanup", "Makes Cleanup Pro feel like a verification workflow"),
            ("Skip condition", source_title, "Keeps the article from turning every privacy headline into a delete-everything panic"),
        ],
        "translate": [
            ("Use case", "Travel, support, family, study, and work messages", "Starts from the phrase the user needs to trust"),
            ("Input risk", "Voice noise, OCR mistakes, slang, names, and formality", "Explains why fluent output still needs review"),
            ("Review loop", "Original text, translation, listen-back, saved history", "Turns Translate AI into a working language notebook"),
            ("Market signal", source_title, "Shows how wider AI access changes user expectations without promising perfect translation"),
        ],
        "find": [
            ("Signal clue", "Bluetooth strength, last-seen context, movement, and device identity", "Separates a recovery lead from a coincidence"),
            ("Privacy boundary", "What should remain visible only to the owner", "Keeps device-finding advice from sounding like tracking advice"),
            ("Escalation point", "When to search, wait, ask for help, or stop", "Gives Find AI users a safer decision path"),
            ("Evidence value", source_title, "Uses the news item to discuss confidence, not drama"),
        ],
        "dualshot": [
            ("Shot purpose", "Tutorial, product demo, reaction, field note, or support clip", "Forces the creator to decide what the second camera is for"),
            ("Storage cost", "4K clips, retakes, B-roll, exported cuts, and cloud copies", "Connects device capacity to the edit plan"),
            ("Reuse plan", "Shorts, documentation, support snippets, and launch assets", "Makes Dual Camera capture useful after recording ends"),
            ("Buying signal", source_title, "Turns a hardware deal into a creator workflow question"),
        ],
        "octopus": [
            ("Cost ledger", "Tokens, runtime, retries, model choice, and tool loops", "Turns agent expense into a visible workflow signal"),
            ("Budget stop", "The point where another attempt needs a fresh yes", "Prevents a small mobile action from becoming an unattended spend loop"),
            ("Evidence trail", "Last command, reason for retry, output summary, and changed files", "Shows whether the next step is still solving the original task"),
            ("Handoff point", source_title, "Names when Octopus should pause and move the decision back to a larger review surface"),
        ],
    }[lane]


def app_lane_checklist(lane: str, source_title: str, summary: str = "") -> list[str]:
    signal = source_signal_type(source_title, summary)
    if lane == "octopus" and signal == "enterprise_codex":
        return [
            "Check the client, portfolio, or meeting context before approving a mobile follow-up.",
            "Verify which system of record or approved data source the thread is using.",
            "Approve only a bounded output: a meeting note, next-action draft, small script, or traceable summary.",
            "Save the reasoning note that explains why the output is ready for a banker or teammate to review.",
            "Move to desktop when the work changes compliance logic, reporting structure, integrations, or client-facing policy.",
        ]
    if lane == "octopus" and signal == "security_review":
        return [
            "Identify the exact file, function, boundary, or invariant behind the security claim.",
            "Ask Codex to produce one minimal validation step before approving any fix.",
            "Approve only a narrow read, test, reproduction, or single-file patch from mobile.",
            "Inspect the resulting evidence: terminal output, diff, failing case, or sandbox result.",
            "Stop and switch to desktop for broad remediation, dependency changes, auth logic, or unclear exploit paths.",
        ]
    return {
        "cleanup": [
            "Confirm backup state before deleting chat media, screenshots, exports, or app caches.",
            "Sort large files by source app so private residue is reviewed before bulk deletion.",
            "Keep one audit pass for files that look small but reveal sensitive activity.",
            "Delete in batches, reopen Photos and Files, then check whether storage pressure actually moved.",
            f"Treat {source_title} as a cleanup cue only when it changes what data you inspect before deleting.",
        ],
        "translate": [
            "Keep the original phrase beside the translated phrase until the message is sent or saved.",
            "Listen back to speech output when tone, names, or pronunciation matter.",
            "Flag idioms, legal wording, medical wording, prices, and dates for human review.",
            "Save corrected phrases into history instead of re-translating the same problem later.",
            f"Treat {source_title} as a translation cue only when it changes the words, tone, or input method you need to trust.",
        ],
        "find": [
            "Verify device identity before acting on a Bluetooth or location clue.",
            "Compare signal movement over time instead of trusting one strong reading.",
            "Use last-seen context to narrow the search area, then stop when the clue stops improving.",
            "Avoid sharing recovery details that could expose someone else's location or routine.",
            f"Treat {source_title} as useful only when it changes recovery confidence, device identity, or tagging cost.",
        ],
        "dualshot": [
            "Name the primary shot before recording the second angle.",
            "Estimate storage for raw clips, retakes, exported cuts, and cloud sync before a long session.",
            "Record one short test clip to check framing, audio, and file size.",
            "Delete failed takes only after the useful cut or transcript is safely exported.",
            f"Treat {source_title} as useful only when it changes the shot plan, reuse plan, or storage budget.",
        ],
        "octopus": [
            "Check the current spend signal before letting another agent loop run.",
            "Ask Codex to name the retry reason, expected output, and stop condition in one sentence.",
            "Approve one bounded attempt, then inspect whether the result changed the task state.",
            "Pause anything that touches billing, auth, deployment, dependencies, or broad file ranges.",
            f"Treat {source_title} as useful only when it changes the next bounded approval or the reason to keep the thread moving.",
        ],
    }[lane]


def app_lane_takeaways(lane: str, source_title: str = "", summary: str = "") -> list[str]:
    signal = source_signal_type(source_title, summary)
    if lane == "octopus" and signal == "enterprise_codex":
        return [
            "Enterprise Codex work is valuable when the handoff is traceable, narrow, and tied to a real business task.",
            "Octopus should make the current client, project, source data, and pending action visible before mobile approval.",
            "Speed is not the point by itself; the useful gain is less context hunting and more time for judgment.",
            "The phone is for continuity and checkpointing, not for approving policy-heavy workflow changes from a notification.",
        ]
    if lane == "octopus" and signal == "security_review":
        return [
            "Security review from mobile should start with evidence, not a label.",
            "Octopus is safest when it turns a finding into one inspectable validation step before a fix.",
            "A phone can approve a bounded reproduction or narrow patch; it should not bless a sweeping remediation.",
            "The useful security question is whether the invariant holds, what proved it, and what still needs desktop review.",
        ]
    return {
        "cleanup": [
            "Cleanup Pro is strongest when cleanup starts with evidence: what file, from which app, with what privacy or storage cost.",
            "The safest deletion flow is boring: backup, inspect, batch delete, verify.",
            "Storage relief and privacy relief overlap, but they are not the same job.",
            "A cleanup article should tell the reader what not to delete as clearly as what to remove.",
        ],
        "translate": [
            "Translate AI should help users preserve context, not just produce a quick fluent sentence.",
            "The hard translation cases are tone, domain wording, speech quality, and OCR errors.",
            "Saved corrections become more useful than a one-off translation when the phrase returns later.",
            "Wider AI access raises expectations, but trust still comes from reviewable wording.",
        ],
        "find": [
            "Find AI should treat every signal as a clue with confidence, not a verdict.",
            "Recovery workflows need privacy boundaries because finding tools can become tracking tools if written carelessly.",
            "Movement over time is usually more useful than one impressive signal spike.",
            "A good lost-device workflow knows when to stop and gather better evidence.",
        ],
        "dualshot": [
            "Dual Camera work starts before recording: purpose, angle, audio, storage, and reuse plan.",
            "More storage helps only when the creator also has a sane edit and deletion routine.",
            "The second camera should reduce explanation time, not create a second pile of unusable footage.",
            "Creator hardware news is useful when it changes capture decisions, not when it only changes specs.",
        ],
        "octopus": [
            "Octopus should make agent spend visible before the next tap, not after the bill is funny in hindsight.",
            "A mobile Codex session needs a cost ceiling, a retry ceiling, and a reason to continue.",
            "Runaway token use is product feedback; the workflow probably needed a smaller checkpoint.",
            "The phone is useful for budgeted continuation. It is not the right place to bless an open-ended loop.",
        ],
    }[lane]


def app_lane_faq_items(lane: str, source_title: str = "", summary: str = "") -> list[tuple[str, str]]:
    app_term = LANE_APP_TERM[lane]
    signal = source_signal_type(source_title, summary)
    if lane == "octopus" and signal == "enterprise_codex":
        return [
            (f"How should {app_term} users read an enterprise Codex story?", "Read it as a handoff design test: does the mobile session show the business context, source data, pending action, and reason for approval clearly enough to trust the next step?"),
            ("When is mobile approval useful in a banking-style workflow?", "It is useful for reviewing a meeting note, a small follow-up draft, a narrow script result, or a traceable next action after the hard context has already been loaded."),
            ("When should enterprise Codex work leave the phone?", "Move to desktop when the task changes compliance rules, reporting structure, client-facing language, integrations, or any decision that needs a full audit trail."),
        ]
    if lane == "octopus" and signal == "security_review":
        return [
            (f"How should {app_term} users read a Codex Security article?", "Read it as an evidence workflow: what behavior is being questioned, what validation step proves or disproves it, and what approval is safe from mobile?"),
            ("What should be approved from mobile during security review?", "Approve a bounded action such as reading a specific file, running one test, generating a minimal reproduction, or applying one narrow patch with visible evidence."),
            ("When is iPhone or iPad not enough for a security fix?", "It is not enough when the evidence spans a large diff, auth logic, dependency changes, unclear exploit paths, or remediation that deserves desktop review."),
        ]
    return {
        "cleanup": [
            (f"When should {app_term} users care about a privacy or storage update?", "They should care when the update changes what data can be inspected, backed up, deleted, or safely left alone."),
            ("What should be checked before deleting files?", "Check backup state, source app, file type, date, and whether the file contains account, message, location, or identity residue."),
            ("Why not delete everything large first?", "The largest file is not always the riskiest or least useful file. Safe cleanup starts with context, then deletes in batches."),
        ],
        "translate": [
            (f"When should {app_term} users care about AI distribution news?", "They should care when it changes expectations for everyday translation, voice, OCR, or saved phrase workflows."),
            ("What makes a translation workflow trustworthy?", "The user should be able to compare the original, translated wording, pronunciation, and any corrected phrase history."),
            ("When should a translation be reviewed by a person?", "Review it when the wording affects money, health, legal meaning, business tone, travel safety, or personal relationships."),
        ],
        "find": [
            (f"When should {app_term} users act on a device signal?", "Act when the device identity, signal trend, and last-seen context point in the same direction."),
            ("What makes a finding clue weak?", "A clue is weak when it comes from one scan, an uncertain device identity, stale location context, or a signal that does not improve with movement."),
            ("How does privacy fit into lost-device recovery?", "Recovery should expose enough context to help the owner find an item without turning the workflow into tracking of another person."),
        ],
        "dualshot": [
            (f"When should {app_term} users care about storage or hardware news?", "They should care when it changes recording length, retake tolerance, export quality, or how quickly a creator can move from capture to edit."),
            ("What should be planned before recording?", "Plan the main shot, second angle, audio path, estimated file size, and how the footage will be reused after the first edit."),
            ("When is a second camera angle unnecessary?", "Skip it when it does not explain, prove, compare, or humanize the subject better than one clear shot."),
        ],
        "octopus": [
            (f"When should {app_term} users continue an agent loop from mobile?", "Continue when the next attempt has a clear budget, a narrow expected output, and a visible stop condition."),
            ("What should stop a cost-heavy mobile workflow?", "Stop when retries keep growing, the model is doing exploratory work, or the action touches billing, credentials, deployment, dependencies, or broad file ranges."),
            ("Why does cost matter in mobile Codex workflows?", "Cost shows whether the agent loop is bounded. If tokens, retries, or tool calls keep growing, the workflow needs a checkpoint before another approval."),
        ],
    }[lane]


def app_lane_related_paths(lane: str) -> list[tuple[str, str]]:
    profile = app_lane_profile(lane)
    product_label = str(profile["product_label"])
    product_url = str(profile["product_url"])
    paths: list[tuple[str, str]] = [(product_label, product_url)]
    if lane != "translate":
        paths.append(("VelocAI Apps", "/apps/"))
    if lane in {"find", "octopus"}:
        paths.append(("Bluetooth Explorer", "/bluetoothexplorer/"))
    if lane == "translate":
        paths.append(("VelocAI Apps", "/apps/"))
    deduped: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for label, url in paths:
        key = (label, url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((label, url))
    return deduped


def app_lane_labels(lane: str, source_title: str = "", summary: str = "") -> dict[str, str]:
    signal = source_signal_type(source_title, summary)
    if lane == "octopus" and signal == "enterprise_codex":
        return {
            "problem": "The enterprise handoff question",
            "next": "Check the business context",
            "checklist": "Enterprise handoff checklist",
            "takeaways": "Banking workflow notes",
            "ignore": "When speed is not enough",
            "faq": "Enterprise Octopus questions",
            "related": "Developer paths",
            "sources": "Octopus sources",
        }
    if lane == "octopus" and signal == "security_review":
        return {
            "problem": "The security evidence question",
            "next": "Check the proof step",
            "checklist": "Security approval checklist",
            "takeaways": "Security review notes",
            "ignore": "When mobile review is too thin",
            "faq": "Security Octopus questions",
            "related": "Developer paths",
            "sources": "Octopus sources",
        }
    return {
        "cleanup": {
            "problem": "The storage question",
            "next": "Inspect before deleting",
            "checklist": "Privacy cleanup checklist",
            "takeaways": "Storage notes",
            "ignore": "When to leave it alone",
            "faq": "Cleanup questions",
            "related": "Cleanup paths",
            "sources": "Cleanup sources",
        },
        "translate": {
            "problem": "The language question",
            "next": "Check the trust layer",
            "checklist": "Translation trust checklist",
            "takeaways": "Language notes",
            "ignore": "When not to switch",
            "faq": "Translation questions",
            "related": "Translation paths",
            "sources": "Translation sources",
        },
        "find": {
            "problem": "The recovery question",
            "next": "Check signal confidence",
            "checklist": "Recovery signal checklist",
            "takeaways": "Finding notes",
            "ignore": "When the clue is weak",
            "faq": "Finding questions",
            "related": "Recovery paths",
            "sources": "Recovery sources",
        },
        "dualshot": {
            "problem": "The creator question",
            "next": "Check the shoot plan",
            "checklist": "Shot plan checklist",
            "takeaways": "Creator notes",
            "ignore": "When the deal is noise",
            "faq": "Creator questions",
            "related": "Creator paths",
            "sources": "Creator sources",
        },
        "octopus": {
            "problem": "The mobile coding question",
            "next": "Check the approval boundary",
            "checklist": "Mobile approval checklist",
            "takeaways": "Coding notes",
            "ignore": "When the phone is not enough",
            "faq": "Octopus questions",
            "related": "Developer paths",
            "sources": "Octopus sources",
        },
    }[lane]


def app_lane_intro_body(lane: str, source_title: str, summary: str, profile: dict[str, object]) -> str:
    signal = source_signal_type(source_title, summary)
    if lane == "octopus" and signal == "enterprise_codex":
        return (
            f"{source_title} matters for Octopus only if it changes the handoff between business context and a pending Codex action. "
            "For an enterprise user, the question is not 'can this run on a phone?' The question is whether the mobile view shows the client, source material, requested output, and approval owner clearly enough to continue without losing accountability."
        )
    if lane == "octopus" and signal == "security_review":
        return (
            f"{source_title} matters for Octopus only if it changes how a security claim becomes evidence. "
            "The user should be able to see the suspected boundary, the exact file or behavior under review, the smallest validation step, and the point where remediation becomes too large for iPhone or iPad approval."
        )
    return (
        f"{source_title} matters for {LANE_APP_TERM[lane]} only if it changes a real workflow question: {profile['intent']}. "
        "Start with the user problem, then decide whether the source gives you a better next step or just an interesting background signal."
    )


def app_lane_context_body(lane: str, source_title: str, source_name: str, post: PostMeta, profile: dict[str, object], human_date: str, summary: str) -> str:
    signal = source_signal_type(source_title, summary)
    if lane == "octopus" and signal == "enterprise_codex":
        return (
            f"As of {human_date}, {post.title.lower()} is useful when it turns {source_name} enterprise reporting into a handoff check: "
            "who needs the output, what source data supports it, what changed in the thread, and which approval should wait for a fuller workspace."
        )
    if lane == "octopus" and signal == "security_review":
        return (
            f"As of {human_date}, {post.title.lower()} is useful when it turns {source_name} security reasoning into an evidence check: "
            "what was tested, what output proved it, what patch is narrow enough, and which remediation belongs on desktop."
        )
    return (
        f"As of {human_date}, {post.title.lower()} connects recent reporting from {source_name} to {profile['secondary']}. "
        "Use it as a practical example, not as a reason to abandon a workflow that already works."
    )


def app_lane_next_body(lane: str, source_title: str, summary: str, profile: dict[str, object]) -> str:
    signal = source_signal_type(source_title, summary)
    if lane == "octopus" and signal == "enterprise_codex":
        return (
            "Before approving from mobile, inspect the business context first: client or portfolio, source data, requested output, last model result, and the person who will rely on it. "
            "Change only the handoff step that is visible in the thread; leave policy, integration, and client-facing judgment for desktop review."
        )
    if lane == "octopus" and signal == "security_review":
        return (
            "Before approving from mobile, inspect the proof step first: named file, command, failing case, sandbox output, or narrow diff. "
            "Approve evidence gathering before remediation, and stop when the work expands beyond one visible security claim."
        )
    return (
        f"{str(profile['risk']).capitalize()}. Check one visible signal first, then change one workflow variable at a time so you can tell whether the update actually helped."
    )


def app_lane_ignore_body(lane: str, source_title: str, summary: str) -> str:
    signal = source_signal_type(source_title, summary)
    if lane == "octopus" and signal == "enterprise_codex":
        return (
            "Ignore the speed story when the thread cannot show the business reason, source data, approval owner, or downstream reviewer. "
            "Enterprise work that moves fast but loses traceability is not a better mobile workflow; it is just a faster way to create cleanup work for someone else."
        )
    if lane == "octopus" and signal == "security_review":
        return (
            "Ignore the security angle when the thread cannot name the evidence, reproduce the behavior, or explain why a specific patch reduces risk. "
            "If the finding needs broad reasoning across auth, dependencies, deployment, or a long diff, Octopus should preserve context and wait for desktop review."
        )
    return (
        "Ignore it when it does not change the task you need to complete, the risk you are trying to reduce, or the result you can verify. "
        "Good app workflows do not need to chase every update; they need a clear reason to change."
    )


def source_signal_type(source_title: str, summary: str) -> str:
    haystack = f"{source_title} {summary}".lower()
    if any(term in haystack for term in ("browser", "architecture", "built", "building")) and any(term in haystack for term in ("chatgpt", "openai", "agent", "workflow", "developer")):
        return "ai_research_loop"
    if any(term in haystack for term in ("safari", "browser", "tabs", "web data")):
        return "iphone_safari"
    if any(term in haystack for term in ("signal chats", "cops", "spy", "storing data", "private data", "chat data")):
        return "data_privacy"
    if any(term in haystack for term in ("api tokens", "burned through", "openclaw", "token cost", "api cost")):
        return "api_cost"
    if any(term in haystack for term in ("sast", "security", "vulnerab", "lockdown", "risk label", "permission")):
        return "security_review"
    if any(term in haystack for term in ("deutsche telekom", "telekom", "millions across europe", "across europe")):
        return "telco_ai_distribution"
    if any(term in haystack for term in ("parameter golf", "ai-assisted research", "research")):
        return "ai_research_loop"
    if any(term in haystack for term in ("bank", "banker", "enterprise", "businesses", "portfolio", "meeting prep")):
        return "enterprise_codex"
    if any(term in haystack for term in ("supply chain", "frontline agents", "ble tracking", "asset tracking")):
        return "supply_chain_tracking"
    if any(term in haystack for term in ("crime blotter", "hijacker", "hijack", "stolen", "theft", "caught", "recovery lead")):
        return "tracker_privacy"
    if any(term in haystack for term in ("tile", "tracker", "stalking", "stalker", "airtag", "find my")):
        return "tracker_privacy"
    if any(term in haystack for term in ("doj", "emissions", "cheating", "investigation", "record user data", "lawsuit")):
        return "evidence_capture"
    if any(term in haystack for term in ("whatsapp", "media share", "share sheet", "attachment", "attachments", "disappearing messages")):
        return "message_media_cleanup"
    if any(term in haystack for term in ("storage", "ram", "ssd", "1tb", "512gb", "macbook", "backup", "icloud")):
        return "storage_pressure"
    if any(term in haystack for term in ("language learning", "translation", "conversation", "pronunciation", "speech", "caption")):
        return "language_practice"
    if any(term in haystack for term in ("battery", "indicator", "status", "android", "bluetooth")):
        return "bluetooth_status"
    if any(term in haystack for term in ("keyboard", "multi-device", "multidevice", "smartphone", "pairing")):
        return "multi_device"
    return "workflow_signal"


def app_lane_analysis_sections(lane: str, source_title: str, summary: str, source_name: str, human_date: str) -> list[tuple[str, str]]:
    profile = app_lane_profile(lane)
    app_term = LANE_APP_TERM[lane]
    signal = source_signal_type(source_title, summary)
    secondary = str(profile["secondary"])
    workflow = str(profile["workflow"])
    haystack = f"{source_title} {summary}".lower()
    dealish = any(term in haystack for term in ("deal", "price", "discount", "sale", "off", "amazon", "best buy"))

    if lane == "octopus" and signal == "security_review":
        return [
            (
                "A label is not proof",
                f"{source_title} should not be read as a fight over whether one security label is better than another. The Octopus angle is evidence: what behavior is being questioned, what file or boundary is involved, and what small validation step can run before a mobile user approves a change.",
            ),
            (
                "The phone-sized action",
                "In Octopus, a security approval should fit on one screen: inspect the named file, run one test, ask for a minimal reproduction, or approve one narrow patch. If the thread cannot name the exact evidence it needs next, the phone should pause the session instead of rewarding vague confidence.",
            ),
            (
                "Evidence before remediation",
                "A mobile security workflow should preserve the evidence trail: command, output, changed path, reason for the patch, and the result after the patch. That trail matters more than a dramatic vulnerability sentence because the user may need to review the decision later from the desktop.",
            ),
            (
                "Desktop handoff",
                f"Use {app_term} to keep security triage moving, not to compress the whole security decision into one tap. The moment the task touches authentication, dependency upgrades, broad permission changes, or a long diff, the safer next action is to save the thread state and continue from a full workspace.",
            ),
        ]

    if lane == "octopus" and signal == "enterprise_codex":
        return [
            (
                "The bank lesson",
                f"{source_title} matters because banking workflows punish fuzzy context. The Octopus reading is not that every professional should code from a phone; it is that Codex work becomes more valuable when the handoff is narrow, auditable, and attached to a real task such as a client follow-up, meeting-prep note, portfolio check, or small internal tool change.",
            ),
            (
                "Context before speed",
                "The enterprise win is not tapping faster. It is avoiding context loss between a banker, a task, a data source, and a pending Codex action. Octopus should show the project, source material, last result, and the requested next step clearly enough that the user can say yes, no, or wait without reconstructing the whole day.",
            ),
            (
                "Audit trail",
                "The risk is not only bad code. It is approving a summary, script, or follow-up against stale context after the assistant has drifted from the business request. A useful mobile flow should keep the reason for approval close to the output, so speed does not erase accountability.",
            ),
            (
                "Where Octopus fits",
                f"For {app_term}, the practical takeaway is to treat enterprise Codex stories as a design test: can the mobile session show who needs the work, what changed, which source the answer used, and what needs approval next? If the answer is no, the phone is for monitoring, not execution.",
            ),
        ]

    if lane == "octopus" and signal == "ai_research_loop":
        return [
            (
                "Research has state",
                f"{source_title} is useful for Octopus because research is not one clean prompt and one clean answer. It is a stack of guesses, tests, dead ends, partial notes, and tiny corrections. The mobile Codex angle is keeping that state alive when the user is away from the desk, without pretending the phone is the best place to inspect a whole research tree.",
            ),
            (
                "The checkpoint habit",
                "A good mobile research workflow is checkpoint-based: ask Codex to summarize the current hypothesis, name the file or note that changed, list the next experiment, and pause before broad edits. That is less glamorous than an autonomous research agent, but it is far safer when the work depends on context the user may need to challenge later.",
            ),
            (
                "What to approve",
                "Approve small research actions from mobile: collect one source, run one narrow command, compare one result, or turn a messy note into a cleaner task list. Do not approve a sweeping rewrite, a new dependency, or a broad repository search just because the thread sounds confident. Confidence is cheap; preserved context is the asset.",
            ),
            (
                "Octopus takeaway",
                "For Octopus, the real product lesson is continuity. The app should help the user keep the research loop moving in small, inspectable steps: what we know, what changed, what remains uncertain, and what action is safe to take next.",
            ),
        ]

    if lane == "octopus" and signal == "api_cost":
        return [
            (
                "Cost is a signal",
                f"{source_title} is an Octopus story because runaway API usage is not just a billing anecdote. It is a workflow signal: the agent kept doing work, the human boundary was too soft, and the loop probably needed a smaller approval step long before the bill became memorable.",
            ),
            (
                "Mobile approvals need budgets",
                "On mobile, the danger is approving a task that sounds harmless while it fans out into a long research, scraping, testing, or generation loop. Octopus should make the pending action feel bounded: what command runs, what server or project it touches, how long it might run, and what result should stop the loop.",
            ),
            (
                "The inspectable step",
                "The safe phone-sized action is not approve everything. It is approve one measurement, one log check, one diff, or one retry with a clear stop condition. If the next step cannot be explained in one screen, the desktop should take over.",
            ),
            (
                "Octopus takeaway",
                "For Octopus, the useful product lesson is that approval cards should carry cost and scope intuition, not just yes-or-no permission. A mobile coding workflow gets safer when the user can see whether the agent is about to solve the task or wander around burning budget.",
            ),
        ]

    if lane == "find" and dealish:
        return [
            (
                "Recovery gear, not shopping noise",
                f"{source_title} matters for Find AI only if it changes how cheaply a person can keep recovery gear ready. AirTag pricing can matter because tagging more items is a real recovery decision; a MacBook or iPad sale only matters if it changes the spare device you use to keep Find AI reachable.",
            ),
            (
                "What the price actually changes",
                "The useful part of the deal is not the headline number. It is whether a lower price makes it easier to tag keys, bags, cases, or travel gear, or whether it gives you a second device that can stay signed in and available when the main phone is out of reach.",
            ),
            (
                "What it does not change",
                "A discount does not improve recovery confidence by itself. You still need device identity, last-seen context, and a clear separation between a lost-item workflow and a privacy-sensitive tracker workflow.",
            ),
            (
                "The safer next step",
                f"Use {app_term} to check whether the deal changes your recovery kit, not just your shopping list. If the item you are considering would not change tagging coverage, signal confidence, or a spare-device setup, it is background noise rather than a recovery trigger.",
            ),
        ]

    if lane == "octopus" and signal == "workflow_signal":
        return [
            (
                "This is background context",
                f"{source_title} does not change Octopus by itself. The only useful question is whether it changes the current coding thread enough to justify another mobile approval, or whether it should stay a desktop read.",
            ),
            (
                "The mobile approval boundary",
                "Octopus should make the next action narrow: one command, one file group, one retry, or one note that keeps the thread moving. If the update does not change that boundary, the headline is just context around the work.",
            ),
            (
                "When the phone is enough",
                "The phone is enough for checking the current repo, the last command, and the next bounded step. It is not enough for a large diff, a vague permission change, or a job where the important evidence is still hidden in desktop-sized context.",
            ),
            (
                "What to do next",
                f"Use {app_term} to keep the thread honest: ask for the stop condition, read the changed files, and decide whether the next tap is a safe continuation or a prompt to move back to the desk.",
            ),
        ]

    if lane == "find" and signal == "tracker_privacy":
        return [
            (
                "Recovery versus privacy",
                f"{source_title} should push Find AI readers to separate two jobs that look similar but are not the same: finding something you lost and detecting a tracker that should not be near you. Both involve Bluetooth signals, but the decision rules are different. A recovery workflow rewards persistence; a privacy workflow rewards caution, logging, and not chasing every weak RSSI bounce like it is a treasure map.",
            ),
            (
                "Signal confidence",
                "The useful signal is not simply strongest equals closest. Readers should look for repeated sightings, movement that follows the user, and whether the device category matches the situation. A one-time weak signal near a cafe is noise; the same unnamed tracker appearing across locations is a very different story.",
            ),
            (
                "What Find AI should change",
                "For Find AI, the actionable shift is to make confidence visible: last seen time, signal trend, device type, and whether the scan pattern is consistent. The app should help users decide when to keep searching, when to stop, and when a privacy concern deserves a more cautious response than normal lost-earbud behavior.",
            ),
            (
                "The human rule",
                "The human rule is boring but important: do not let the app turn suspicion into panic. Use the scan to gather evidence, compare movement context, and avoid confronting anyone based on a single Bluetooth clue. Bluetooth can be useful without being a courtroom witness.",
            ),
        ]

    if lane == "find" and signal == "supply_chain_tracking":
        return [
            (
                "Industrial clues",
                f"{source_title} gives Find AI a useful industrial mirror. Supply-chain BLE tracking is not the same as finding earbuds under a couch, but it shares the same uncomfortable truth: a Bluetooth signal is only useful when it is tied to time, movement, and a known object.",
            ),
            (
                "Movement matters",
                "The practical lesson is movement history. A single scan tells the user almost nothing; repeated sightings tell a story. Find AI should help the user compare where the signal appeared, whether it is getting stronger, and whether the object is behaving like something stationary, carried, or drifting between environments.",
            ),
            (
                "Confidence before action",
                "Supply-chain systems care about false positives because bad data sends people to the wrong shelf, truck, or warehouse door. Consumer recovery has the same problem in miniature. If the scan is weak, stale, or inconsistent, the app should slow the user down instead of encouraging a frantic walk in circles.",
            ),
            (
                "Find AI takeaway",
                "For Find AI, the angle is not enterprise logistics; it is confidence design. Show the device category, last seen context, and signal trend clearly enough that a person can decide whether to keep searching, retrace steps, or stop treating the clue as reliable.",
            ),
        ]

    if lane == "dualshot" and signal == "evidence_capture":
        return [
            (
                "Video as evidence",
                f"{source_title} is a reminder that creator capture is not always about nicer footage. Sometimes the value is boring evidence: what was shown, what was said, what the screen displayed, and whether the clip can still make sense when someone watches it later without the original context.",
            ),
            (
                "Two angles matter",
                "Dual Camera has a specific edge here because a single view often loses the thing that makes a clip credible. A product demo, compliance walkthrough, or bug report is stronger when one angle captures the presenter or physical setup while the other captures the screen, device, or object under discussion.",
            ),
            (
                "Do not over-edit",
                "The wrong lesson is to polish everything until it looks like a launch video. For evidence-style recording, the better workflow is clean audio, stable framing, visible timestamps or sequence context where appropriate, and fewer cuts. Editing can clarify, but it can also strip away the boring details that make the clip trustworthy.",
            ),
            (
                "Creator takeaway",
                "For Dual Camera users, the useful next move is to treat some recordings as records, not content. Before filming, decide what a skeptical viewer would need to see later: the action, the environment, the screen state, and the spoken explanation. Capture those first; style comes second.",
            ),
        ]

    if lane == "dualshot" and signal == "storage_pressure":
        return [
            (
                "Storage is creative debt",
                f"{source_title} sounds like a hardware shopping note, but Dual Camera users should read it as a post-production warning. Creator footage turns storage into creative debt: every extra take, second angle, screen recording, and export has to be named, moved, reviewed, and eventually deleted or archived.",
            ),
            (
                "Capture less badly",
                "The better workflow is not simply buying more capacity. It is capturing with intent: decide the main angle, decide the context angle, keep audio clean, and avoid recording five redundant versions of the same explanation. Storage disappears fastest when the shot plan is vague.",
            ),
            (
                "The edit bottleneck",
                "A larger MacBook drive helps after filming, but it does not fix a messy capture session. The painful part is usually the edit: finding the right take, syncing context, trimming dead air, and exporting versions for different channels. Dual Camera content should help users reduce that mess before it lands on the Mac.",
            ),
            (
                "Dual Camera takeaway",
                "For Dual Camera, the useful lesson is to treat storage as part of the recording workflow. If a creator can leave the shoot with fewer, clearer clips, the hardware upgrade becomes headroom instead of a landfill.",
            ),
        ]

    if lane == "cleanup" and signal == "storage_pressure":
        return [
            (
                "Buying time",
                f"{source_title} is easy to read as a hardware deal or spec bump, but Cleanup Pro readers should read it as a storage-pressure story. More RAM or more SSD does not remove the cleanup problem; it just buys time before downloads, duplicate media, app caches, and old exports start behaving like sediment.",
            ),
            (
                "The cleanup order",
                "The order matters: confirm backups, inspect the largest media and downloads, remove duplicates, then handle app caches and offline files. Doing it backward feels productive for ten minutes and then turns into the classic mess where the user deletes small safe files while the real storage hogs keep sitting untouched.",
            ),
            (
                "When not to delete",
                "The smarter move is sometimes not deletion. If a file belongs to an active project, a recent export, or a device backup that has not been verified elsewhere, the safe choice is to tag it, move it, or postpone it. Cleanup should reduce risk, not create a tiny private disaster with a progress bar.",
            ),
            (
                "Practical takeaway",
                "For Cleanup Pro, the useful angle is to make capacity decisions visible before they become urgent. If a storage update changes buying behavior, it should also change cleanup behavior: run a quick audit before upgrading, before a trip, and before any large OS or app migration.",
            ),
        ]

    if lane == "cleanup" and signal == "iphone_safari":
        return [
            (
                "Safari leaves crumbs",
                f"{source_title} looks like a browser-tips article, but Cleanup Pro readers should read it through the small messes Safari leaves behind: downloads, cached pages, reading-list saves, screenshots, duplicated PDFs, and tabs that quietly turn into future clutter.",
            ),
            (
                "The tiny-file trap",
                "Safari clutter is annoying because it rarely looks large one file at a time. The trap is accumulation. A handful of downloaded receipts, saved images, web exports, and duplicate screenshots will not scare anyone today, but they become part of the storage fog that makes iPhone cleanup feel harder later.",
            ),
            (
                "What to inspect",
                "The practical cleanup pass is simple: check Downloads, review screenshots created from Safari, clear stale offline saves if they are no longer needed, and confirm that important PDFs or receipts are backed up before deletion. Do not start by nuking browser data just because the settings screen offers a big button.",
            ),
            (
                "Cleanup Pro takeaway",
                "For Cleanup Pro, the useful angle is habit design. Browser tips are only valuable if they reduce the future cleanup burden: fewer mystery files, fewer duplicate captures, and a clearer path between saving something useful and deleting the leftovers later.",
            ),
        ]

    if lane == "cleanup" and signal == "data_privacy":
        return [
            (
                "Cleanup is privacy work",
                f"{source_title} is not a normal storage story, but it is relevant to Cleanup Pro because stored data becomes risk when nobody remembers why it exists. The iPhone cleanup question is not only how much space a file uses; it is whether old app data, exports, caches, or backups reveal more than the user expects.",
            ),
            (
                "Do not delete blindly",
                "The privacy instinct says delete everything. The practical cleanup instinct says verify first. Messages, attachments, screenshots, exported chats, and app containers can include evidence the user needs, memories they want, or account data that should be backed up before removal.",
            ),
            (
                "What to inspect",
                "A useful cleanup pass should separate disposable clutter from sensitive records: duplicate screenshots, downloaded attachments, old exports, app caches, and backups. The goal is to reduce both storage pressure and accidental exposure, without turning cleanup into data loss with a tidy interface.",
            ),
            (
                "Cleanup Pro takeaway",
                "For Cleanup Pro, the point is to make hidden data visible enough for a sane decision. Delete the obvious waste, review the sensitive leftovers, and keep backup status in the same mental frame as free space.",
            ),
        ]

    if lane == "cleanup" and signal == "message_media_cleanup":
        return [
            (
                "Shared media becomes storage residue",
                f"{source_title} is relevant to Cleanup Pro because message sharing is one of the quiet ways iPhone storage grows. A cleaner share sheet can make sending easier, but it can also create duplicate photos, saved edits, forwarded clips, and attachments that users forget to remove later.",
            ),
            (
                "The cleanup point",
                "The useful habit is to inspect the media trail after a heavy chat day: original files, edited copies, downloaded attachments, forwarded videos, and screenshots made to explain the conversation. That is more concrete than clearing a whole app cache and hoping nothing important disappears.",
            ),
            (
                "What not to delete",
                "Do not delete message media just because it appears twice. Keep files that document work, travel, purchases, support cases, family records, or anything that is not backed up elsewhere. Cleanup is safest when it separates throwaway duplicates from records the user may need later.",
            ),
            (
                "Cleanup Pro takeaway",
                "For Cleanup Pro, the article should turn messaging updates into an inspection routine: sort by source app, review large media first, remove obvious duplicate exports, then verify storage moved. That gives the user a repeatable action instead of a vague privacy warning.",
            ),
        ]

    if lane == "translate" and signal == "language_practice":
        return [
            (
                "Practice beats lookup",
                f"{source_title} is useful for Translate AI only if it moves translation from one-shot lookup into practice. A phrase translated once is a receipt; a phrase heard, repeated, adjusted, and saved with context becomes something the user might actually use in a real conversation.",
            ),
            (
                "The speech loop",
                "The workflow should be short: capture the sentence, translate it, listen back, repeat the hard part, and save the version that sounds least awkward. That sounds almost too simple, but most translation apps fail here because they treat the answer as the finish line instead of the first rehearsal.",
            ),
            (
                "Where AI can mislead",
                "The risk is fluent wrongness. A smooth translation can still miss tone, politeness, domain context, or the thing a native speaker would never say that way. Translate AI should make uncertainty easy to review, especially for work messages, travel problems, medical wording, or anything with money attached.",
            ),
            (
                "Practical takeaway",
                "For Translate AI users, the next step is not to collect more translations. It is to build a small set of phrases they can trust: original, translation, pronunciation, and a note about when to use it. That is slower than tapping once, and much more useful.",
            ),
        ]

    if lane == "translate" and signal == "telco_ai_distribution":
        return [
            (
                "Distribution changes expectations",
                f"{source_title} matters for Translate AI because distribution changes what users expect from language tools. When AI features reach carrier-scale audiences, translation stops feeling like a specialist utility and starts feeling like something people assume should work inside travel, customer support, family messages, and everyday phone workflows.",
            ),
            (
                "The trust problem",
                "Scale does not solve trust. In translation, the hard part is not producing a fluent sentence; it is helping the user notice when tone, context, or formality might be wrong. A carrier partnership can make AI more available, but the app still needs review loops for the moments where being almost right is not good enough.",
            ),
            (
                "What Translate AI should emphasize",
                "Translate AI should lean into the practical phone workflow: camera text, voice input, saved history, listen-back, and quick revision. The advantage is not that the app knows every language perfectly; the advantage is that it keeps the original, translated output, and user context close enough to compare.",
            ),
            (
                "Translate AI takeaway",
                "For Translate AI, the insight is that broad AI access raises the floor, not the ceiling. The app wins when it helps a user move from raw translation to usable wording they can trust in a specific situation.",
            ),
        ]

    if signal == "bluetooth_status":
        return [
            (
                "Status is behavior",
                f"{source_title} sounds like a small Bluetooth detail, but status indicators change behavior. When battery state, connection state, or device identity is visible, users stop guessing and start making better pairing, recovery, and troubleshooting decisions.",
            ),
            (
                "What to inspect",
                "The useful check is whether the signal is stable across reconnects, sleep, range changes, and multi-device handoff. A pretty battery icon is not enough if it lies after the second reconnect or disappears when the device moves between phone, tablet, and laptop.",
            ),
            (
                "App angle",
                f"For {app_term}, the practical angle is to expose the part of the Bluetooth story the system UI hides: signal trend, device identity, service behavior, and whether the problem is pairing, power, range, or the accessory itself.",
            ),
            (
                "Practical takeaway",
                "Treat Bluetooth status as a diagnostic hint, not a verdict. The next useful action is to compare what the user interface claims against what the scan, RSSI trend, or device response actually shows.",
            ),
        ]

    if signal == "multi_device":
        return [
            (
                "Handoff friction",
                f"{source_title} matters because multi-device hardware succeeds or fails in the handoff, not in the spec sheet. The user does not care that pairing is theoretically supported; they care whether the keyboard, phone, tablet, and app state agree when the work moves.",
            ),
            (
                "The real test",
                "The real test is mundane: switch devices, type a short command, reconnect after sleep, and see whether the accessory lands on the device the user intended. Bluetooth workflows usually break in these boring seams, which is exactly why they are worth writing down.",
            ),
            (
                "App angle",
                f"For {app_term}, the useful view is to treat device switching as part of the workflow instead of a setup chore. The app should help the user see which device is active, what changed, and whether a failed action came from input focus, Bluetooth state, or the app itself.",
            ),
            (
                "Practical takeaway",
                "If the update does not reduce handoff uncertainty, it is only a gadget story. If it does, it can change how users capture, debug, translate, code, or recover devices across a mixed Apple and accessory setup.",
            ),
        ]

    return [
        (
            "The real signal",
            f"{source_title} is worth using only if it changes a concrete {secondary} decision. Read it for the operational clue: what becomes easier to inspect, what should be tested once, and what still deserves to be left alone.",
        ),
        (
            "The workflow test",
            f"For {app_term}, the test is whether the update improves this sequence: {workflow}. If it cannot change one step in that sequence, it belongs in background reading rather than the user's routine.",
        ),
        (
            "The failure mode",
            f"The failure mode is pretending that every adjacent update deserves an app workflow. It does not. A stronger article says exactly where the signal is weak, what evidence is missing, and why the user should wait before changing behavior.",
        ),
        (
            "The next move",
            f"Use {app_term} for one bounded experiment, then compare the result with the old routine. If the update does not improve time, quality, safety, or confidence, the old routine wins.",
        ),
    ]


def render_app_live_article(day: date, source_slug: str, source_name: str, item: FeedItem, post: PostMeta, lane: str) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    source_published = item.published_at.astimezone().strftime("%B %d, %Y") if item.published_at else human_date
    source_title = clean_text(item.title)
    summary = lane_summary(lane, source_slug, source_name, item)
    profile = app_lane_profile(lane)
    labels = app_lane_labels(lane, source_title, summary)
    app_term = LANE_APP_TERM[lane]
    keyword_coverage = keywords_for_lane(lane, source_slug) + [slugify(item.title).replace("-", " ")]
    table_rows = app_lane_table_rows(lane, source_title, summary)
    checklist_items = app_lane_checklist(lane, source_title, summary)
    takeaways = app_lane_takeaways(lane, source_title, summary)
    faq_items = app_lane_faq_items(lane, source_title, summary)
    related_paths = app_lane_related_paths(lane)
    analysis_sections = app_lane_analysis_sections(lane, source_title, summary, source_name, human_date)
    table_html = "\n".join(
        f"          <tr><td>{escape(col1)}</td><td>{escape(col2)}</td><td>{escape(col3)}</td></tr>"
        for col1, col2, col3 in table_rows
    )
    checklist_html = "\n".join(f"          <li>{escape(item)}</li>" for item in checklist_items)
    takeaways_html = "\n".join(f"          <li>{escape(item)}</li>" for item in takeaways)
    faq_html = "\n".join(
        f"      <p><strong>{escape(question)}</strong><br>\n      {escape(answer)}</p>\n"
        for question, answer in faq_items
    )
    related_paths_html = "\n".join(
        f'        <li><a href="{escape(url)}">{escape(label)}</a></li>'
        for label, url in related_paths
    )
    analysis_html = "\n\n".join(
        f"      <h2>{escape(heading)}</h2>\n      <p>{escape(body)}</p>"
        for heading, body in analysis_sections
    )
    source_links = [(f"{source_name}: {source_title}", item.link), *background_links_for(source_slug)]
    source_links_html = "\n".join(
        f'          <li><a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(label)}</a></li>'
        for label, url in source_links
    )
    keywords = ", ".join(keyword_coverage)
    signal = source_signal_type(source_title, summary)
    if lane == "octopus" and signal == "enterprise_codex":
        tldr = (
            f"As of {human_date}, this Octopus article reads {source_title} as an enterprise handoff lesson. "
            "The useful check is whether the mobile session shows business context, source data, approval owner, and a desktop boundary before anyone moves faster."
        )
    elif lane == "octopus" and signal == "security_review":
        tldr = (
            f"As of {human_date}, this Octopus article reads {source_title} as a security evidence lesson. "
            "The useful check is whether the phone can approve one validation step, see the proof, and stop before broad remediation needs desktop review."
        )
    else:
        tldr = (
            f"As of {human_date}, this {app_term} article uses recent reporting from {source_name}. "
            f"The useful answer is whether {source_title} changes a real {profile['secondary']} decision, which signal to inspect first, and when the phone or iPad should hand the work back to desktop review."
        )

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

      <h2>{escape(labels["problem"])}</h2>
      <p>{escape(app_lane_intro_body(lane, source_title, summary, profile))}</p>

      <table aria-label="{escape(post.topic)} source coverage">
        <thead>
          <tr><th>Coverage area</th><th>Specific angle</th><th>Reader value</th></tr>
        </thead>
        <tbody>
{table_html}
        </tbody>
      </table>

{analysis_html}

      <div class="capsule">
        <p>{escape(app_lane_context_body(lane, source_title, source_name, post, profile, human_date, summary))}</p>
      </div>

      <h2>{escape(labels["next"])}</h2>
      <p>{escape(app_lane_next_body(lane, source_title, summary, profile))}</p>

      <div class="panel">
        <h3>{escape(labels["checklist"])}</h3>
        <ul>
{checklist_html}
        </ul>
      </div>

      <div class="panel">
        <h3>{escape(labels["takeaways"])}</h3>
        <ul>
{takeaways_html}
        </ul>
      </div>

      <h2>{escape(labels["ignore"])}</h2>
      <p>{escape(app_lane_ignore_body(lane, source_title, summary))}</p>

      <h2>{escape(labels["faq"])}</h2>
{faq_html}

      <div class="panel">
        <h3>{escape(labels["related"])}</h3>
        <ul>
{related_paths_html}
        </ul>
      </div>

      <section class="sources" aria-label="Source attribution">
        <h3>{escape(labels["sources"])}</h3>
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
        return clip_text(combined, limit=158)
    suffix = {
        "apple": f" Covers upgrade relevance, storage impact, and what {source_name} signals mean for cleanup planning.",
        "ai": f" Covers workflow impact, deployment relevance, and what {source_name} signals mean for teams evaluating AI changes.",
        "bluetooth": f" Covers application impact, rollout risk, and what {source_name} signals mean for Bluetooth product teams.",
    }[source_slug]
    combined = f"{summary.rstrip('.')}." + suffix
    return clip_text(combined, limit=158)


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
        "apple": f"As of {source_published}, Apple product coverage performs best when it explains feature changes, performance tradeoffs, repairability, pricing position, and ecosystem impact instead of repeating launch headlines. Source monitoring from {source_name} is most useful when it turns a new release into clear buyer and developer context.",
        "ai": f"As of {source_published}, AI release coverage performs best when it explains capability shifts, deployment implications, workflow impact, pricing or access changes, and what teams should test next. Source monitoring from {source_name} becomes more useful when it translates fast-moving AI news into practical product decisions.",
        "bluetooth": f"As of {source_published}, Bluetooth update coverage performs best when it explains what changed in standards, interoperability, applications, and deployment tradeoffs instead of repeating vendor claims. Source monitoring from {source_name} matters when it turns technical announcements into implementation context.",
    }[source_slug]


def opening_intro_for(source_slug: str, title: str, summary: str) -> str:
    return {
        "apple": f"This Apple feature and performance commentary examines {title} through the lens of product positioning, feature relevance, repairability, and real-world upgrade value. Instead of repeating a launch headline, the goal is to connect the update to practical buyer intent, developer implications, and the Apple ecosystem signals that matter most in 2026. {summary}",
        "ai": f"This AI technology outlook examines {title} through the lens of model capability, workflow impact, deployment relevance, and product strategy. Instead of repeating an announcement, the goal is to explain what changed, why it matters for builders and teams, and how the update fits the broader direction of AI products in 2026. {summary}",
        "bluetooth": f"This Bluetooth standards and application commentary examines {title} through the lens of interoperability, deployment impact, and product-level relevance. Instead of repeating a standards headline, the goal is to translate the update into practical Bluetooth implementation context for teams and readers in 2026. {summary}",
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
        "apple": f"{title} should be read as more than a launch note. The real value comes from understanding which Apple product behaviors changed, what stayed the same, and whether the feature update improves everyday usage, serviceability, accessory fit, or long-term upgrade value. {summary} The strongest Apple feature analysis also asks whether the change improves camera, battery, thermals, portability, or the ecosystem fit that often decides whether an upgrade is worth it.",
        "ai": f"{title} should be read as more than an announcement. The key question is whether the update changes model capability, developer workflow, agent reliability, deployment planning, or the economics of using AI in production. {summary} The strongest AI model commentary also explains whether the release changes what teams can automate, what tradeoffs they inherit, and whether product quality or operating cost shifts in a meaningful way.",
        "bluetooth": f"{title} should be read in terms of standards meaning, interoperability, and application consequences. The main value comes from mapping the update to device discovery, audio, telemetry, power, or rollout decisions. {summary}",
    }[source_slug]


def application_body_for(source_slug: str) -> str:
    return {
        "apple": "Readers, buyers, and developers care most about where the new feature or performance change fits in the lineup. The strongest Apple commentary explains upgrade relevance, tradeoffs versus nearby products, and whether the change improves real workflows rather than only spec-sheet perception. It should also clarify who does not need the update, which compromises still remain, and whether the product changes the buying logic inside the current Apple range.",
        "ai": "Teams care most about what the release changes in real usage. The strongest AI commentary explains whether a new model, retirement, or capability shift changes product quality, automation design, safety posture, or cost decisions for actual teams. It should also clarify whether the update changes evaluation criteria, tool choice, model routing, or the practical balance between speed, quality, and operating cost.",
        "bluetooth": "Teams care most about where a standards or ecosystem update changes implementation reality. The strongest Bluetooth commentary explains whether the change affects reliability, compatibility, deployment timing, or product experience in a measurable way.",
    }[source_slug]


def next_heading_for(source_slug: str) -> str:
    return {
        "apple": "What To Watch Next",
        "ai": "What To Watch Next",
        "bluetooth": "What To Watch Next",
    }[source_slug]


def next_body_for(source_slug: str) -> str:
    return {
        "apple": "The next question is whether independent testing, teardowns, benchmarks, and real user feedback support the first wave of Apple product claims. Good Apple product commentary should track whether the feature or performance story remains compelling after launch-day attention fades, and whether accessories, developers, and the broader lineup reinforce or weaken the case for the update.",
        "ai": "The next question is whether this AI update changes evaluation baselines, pricing logic, deployment planning, or model choice in real products. Good AI technology outlook content should track how the release affects practical workloads, whether the capability gain holds up under real usage, and whether access, safety, or product integration changes what teams do next.",
        "bluetooth": "The next question is whether the update moves from standards language into practical implementation value. Good Bluetooth commentary should track vendor adoption, compatibility signals, firmware support, and whether the update changes deployment planning, interoperability, or product-level user experience.",
    }[source_slug]


def search_intent_heading_for(source_slug: str) -> str:
    return {
        "apple": "Upgrade Questions",
        "ai": "Adoption Questions",
        "bluetooth": "Deployment Questions",
    }[source_slug]


def search_intent_body_for(source_slug: str) -> str:
    return {
        "apple": "Readers usually need four answers before an Apple update matters: what changed, what stayed the same, how it compares with nearby models, and whether the change affects daily use. Useful commentary should separate lineup positioning from practical value, because a spec bump that looks large in a launch headline can still be irrelevant for battery life, repairability, accessory fit, or the way someone actually uses the device.",
        "ai": "Readers usually need to know what changed in capability, whether the change holds up in real workflows, how pricing or access affects adoption, and what teams should test before switching tools. Useful AI commentary should connect the release to concrete work: development, automation, review quality, latency, safety, reliability, or enterprise rollout decisions.",
        "bluetooth": "Readers usually need to know what changed in the standard, where the change matters in applications, how interoperability is affected, and whether deployment plans should change. Useful Bluetooth commentary should translate technical language into validation steps across chips, firmware, apps, operating systems, and real devices.",
    }[source_slug]


def checklist_items_for(source_slug: str) -> list[str]:
    return {
        "apple": [
            "Check which feature changed and whether it affects daily use or only positioning.",
            "Compare the update against the nearest Apple product tier before judging upgrade value.",
            "Look at repairability, battery, accessory, and software fit alongside performance.",
            "Separate headline launch excitement from long-term ownership impact.",
            "End with a clear buy, wait, or ignore recommendation for the user group being discussed.",
        ],
        "ai": [
            "Check whether the release changes real workflow quality or only expands model options.",
            "Compare pricing, access, and rollout details before assuming broad availability.",
            "Look at safety, reliability, and integration tradeoffs alongside capability claims.",
            "Separate benchmark headlines from deployment impact on real teams.",
            "End with a concrete test plan before recommending adoption.",
        ],
        "bluetooth": [
            "Check whether the update changes standards language, implementation reality, or both.",
            "Compare application impact across discovery, audio, mesh, telemetry, and compatibility.",
            "Look at rollout timing and firmware support before assuming adoption.",
            "Separate feature headlines from deployment value in real products.",
            "End with the specific interoperability checks teams should run next.",
        ],
    }[source_slug]


def retrieval_fit_body_for(source_slug: str) -> str:
    return {
        "apple": "Name the product clearly, explain the practical change early, and compare the update against nearby Apple options. Readers need feature review, performance impact, and upgrade value in one place because those decisions are connected in real buying behavior.",
        "ai": "Name the model, product, or release clearly, explain the practical capability shift early, and tie the change to a workflow someone can test. Readers need capability analysis, deployment implications, and next-step guidance together because switching AI tools without a test plan is mostly guesswork.",
        "bluetooth": "Name the standard, update, or application clearly, explain the implementation impact early, and identify the compatibility checks that matter. Readers need standards meaning, interoperability risk, and deployment guidance together because Bluetooth changes only matter after devices actually work together.",
    }[source_slug]


def challenge_intro_for(source_slug: str) -> str:
    return {
        "apple": "Apple product coverage gets weak when it stays too close to launch marketing and fails to explain how the update changes buying logic or long-term usability.",
        "ai": "AI release coverage gets weak when it repeats headline capability claims and skips deployment tradeoffs, operational constraints, or workflow relevance.",
        "bluetooth": "Bluetooth update coverage gets weak when it repeats standards language without explaining what changes for product teams, users, or deployment planning.",
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


def geo_answers_for(source_slug: str) -> list[str]:
    return {
        "apple": [
            "Apple feature commentary should explain what changed, what stayed the same, and who should care.",
            "Apple performance analysis is strongest when it maps specs to real workflow impact.",
            "Apple lineup commentary should help readers compare nearby product tiers clearly.",
            "Repairability and accessory compatibility are practical parts of Apple product value.",
            "Good Apple coverage should make the wait, upgrade, or skip decision easier.",
        ],
        "ai": [
            "AI commentary should explain capability change, workflow impact, and deployment relevance together.",
            "Model retirement and rollout updates can matter more than benchmark headlines.",
            "AI product analysis is strongest when it connects releases to actual team decisions.",
            "Readers need clear explanation of pricing, access, safety, and integration tradeoffs.",
            "Good AI coverage should name what teams should test before changing tools.",
        ],
        "bluetooth": [
            "Bluetooth commentary should explain what changed in standards and what that means for applications.",
            "Application impact matters more than repeating technical labels without context.",
            "Deployment risk depends on compatibility across chips, firmware, apps, and operating systems.",
            "Readers need standards updates translated into product-level implications.",
            "Good Bluetooth coverage should identify which implementation checks come next.",
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


def bluetooth_live_profile(
    item: FeedItem,
    summary: str,
    source_name: str,
    human_date: str,
    source_published: str,
    post: PostMeta,
) -> dict[str, object] | None:
    title = clean_text(item.title)
    haystack = f"{title} {summary}".lower()
    if any(term in haystack for term in ("beacon data set", "dataset", "data set", "zenodo", "indoor localisation", "indoor localization")):
        return {
            "opening_intro": (
                f"{title} is useful because it gives Bluetooth Explorer readers a reproducible artefact, not another vague promise about indoor positioning. "
                "The interesting question is data quality: what was labelled, what was omitted, how the home layout shapes the sample, and whether a team can repeat the experiment without quietly moving the goalposts."
            ),
            "tldr": (
                f"As of {human_date}, this BeaconZone item is best read as a dataset design story. Teams should use it to judge coverage, labels, holdout strategy, and reproducibility before building a BLE indoor localisation claim around it."
            ),
            "current_heading": "Dataset, Not Spec News",
            "current_body": (
                f"BeaconZone published the item on {source_published}. The important part is not that another Bluetooth article exists; it is that the source points to a labelled sample collected in a home-like environment. "
                "For Bluetooth Explorer users, that changes the job from admiring a positioning claim to auditing the ingredients: floor plan, reference points, capture notes, missing corners, repeated observations, and the parts of the setup a future tester would need to copy."
            ),
            "table_label": "BLE beacon dataset reading guide",
            "table_head": ("Dataset angle", "What to inspect", "Why it matters"),
            "table_rows": [
                ("Label schema", "Room names, reference points, device identifiers, and capture fields", "Decides whether another team can understand the sample without guessing"),
                ("Coverage map", "Which rooms, doors, corners, and transitional areas were included", "Shows whether the dataset represents the hard parts of the floor plan"),
                ("Holdout plan", "Points reserved for validation instead of training", "Prevents a model from merely memorising the sample"),
                ("Reproducibility notes", "Hardware, placement, timing, and environmental context", "Lets teams repeat the collection instead of treating the file as magic"),
            ],
            "interpretation_heading": "What The Data Teaches",
            "interpretation_body": (
                f"{summary} The useful reading is that a dataset is both training material and an audit trail. The file should make it possible to ask boring but decisive questions: were all rooms represented, were reference points repeated, were edge cases labelled, and can the same collection method survive a second run? "
                "A good Bluetooth Explorer workflow should treat the sample as evidence to interrogate, not as a trophy that proves the product already works."
            ),
            "context_body": (
                "The article matters when it helps a team create a test harness: load the records, split training and validation points, keep a changelog of assumptions, and write down which parts of the building the sample does not describe. "
                "That is more valuable than a polished demo that never exposes its data."
            ),
            "application_heading": "Where It Breaks",
            "application_body": (
                "The dataset is not a universal map of every office, warehouse, museum, or home. It is a controlled slice of reality. Teams should expect breaks when the floor plan changes, hardware is swapped, collection timing shifts, or a deployment space has materials the sample never saw. "
                "Bluetooth Explorer can help by showing whether a new site still resembles the evidence used to design the location logic."
            ),
            "note_body": (
                "Treat the data as a rehearsal space. If an algorithm cannot explain its mistakes on a public sample, it will not become magically reliable in a messier building."
            ),
            "next_heading": "Use It Carefully",
            "next_body": (
                "Start with a dumb baseline, then improve it only after the validation split explains what actually failed. Compare room classification, uncertain zones, repeatability, and the cost of adding more collection points. "
                "If the data teaches anything, it is that indoor BLE location needs documented evidence before it needs a prettier confidence claim."
            ),
            "risk_heading": "Dataset traps",
            "risk_intro": "A beacon dataset is helpful, but only if teams resist turning one sample into a universal truth.",
            "challenge_items": [
                "A home dataset can underrepresent office, retail, factory, and outdoor layouts.",
                "A neat file can hide missing metadata about placement, timing, hardware, or collection order.",
                "A model can look strong if validation points are too similar to training points.",
                "Room-level labels can mask weak performance near doors, hallways, and boundary areas.",
                "A dataset without field validation can produce a method that works only on the sample it learned from.",
            ],
            "checklist_heading": "Beacon dataset checklist",
            "checklist_items": [
                "Check whether the dataset includes labelled reference points, device IDs, and repeated captures per point.",
                "Draw the coverage map before judging model quality.",
                "Keep a naive baseline so later improvements have something honest to beat.",
                "Separate training points from validation points before tuning thresholds or weights.",
                "Document which rooms, materials, hardware, and collection conditions the dataset does not cover.",
            ],
            "takeaway_heading": "Reproducibility notes",
            "takeaway_intro": "For Bluetooth Explorer, the value is making dataset assumptions visible before a product turns them into a location label.",
            "geo_answers": [
                "A BLE beacon dataset helps teams test indoor localisation assumptions against labelled reference points.",
                "Dataset quality depends on coverage, metadata, validation split, and repeatability.",
                "Home-based samples are useful but should not be treated as universal building evidence.",
                "Bluetooth Explorer-style inspection is useful before a team commits to a location model.",
                "The best dataset work ends with documented limits, not a universal accuracy claim.",
            ],
            "faq_heading": "Dataset questions",
            "faq_items": [
                ("Can this dataset prove that BLE indoor location is accurate?", "No. It can help test methods and reveal failure modes, but every real deployment still needs validation in its own building and device mix."),
                ("What should Bluetooth Explorer users inspect first?", "Start with labels, reference points, repeated captures, missing areas, and the split between training and validation records."),
                ("Why does metadata matter for beacon data?", "Because hardware, placement, room layout, and collection timing decide whether another team can reproduce the experiment."),
            ],
            "sources_heading": "Dataset source",
        }
    if any(term in haystack for term in ("variation of rssi", "rssi", "received signal strength", "fluctuation")):
        return {
            "opening_intro": (
                f"{title} is a useful Bluetooth Explorer topic because RSSI is the number people want to treat as distance, and it is also the number most eager to embarrass them. "
                "The practical issue is not whether RSSI fluctuates. It does. The issue is whether the product can behave responsibly while that fluctuation is happening."
            ),
            "tldr": (
                f"As of {human_date}, this BeaconZone item is best read as an RSSI volatility guide. Teams should use Bluetooth Explorer to inspect signal spread, sampling windows, and device differences before turning RSSI into proximity or distance logic."
            ),
            "current_heading": "RSSI Is Noisy",
            "current_body": (
                f"BeaconZone published the item on {source_published}, and the core point is pleasantly unromantic: smartphones and gateways can see changing RSSI values from the same beacon even when nobody thinks the setup is changing. "
                "That does not automatically mean the beacon is broken. It usually means the measurement path is messy: antenna orientation, body blocking, reflections, scan timing, transmit power, and receiver behavior are all in the room with you, being annoying."
            ),
            "table_label": "RSSI variation debugging guide",
            "table_head": ("RSSI factor", "What to inspect", "Why it matters"),
            "table_rows": [
                ("Receiver behavior", "Phone model, gateway antenna, OS scanning policy", "Different receivers can report different signal histories"),
                ("Body and orientation", "Pocket position, hand grip, beacon rotation, user movement", "Small physical changes can look like large proximity changes"),
                ("Sampling window", "Single scan, rolling median, percentile, or timeout window", "The chosen window decides whether noise becomes a false alert"),
                ("Environment", "Walls, metal shelves, multipath, doors, and people", "The same beacon behaves differently across real spaces"),
            ],
            "interpretation_heading": "The Device Problem",
            "interpretation_body": (
                f"{summary} The mistake is assuming RSSI is an objective distance meter. It is not. It is a receiver-side observation shaped by hardware, firmware, scan cadence, and the RF path between beacon and scanner. "
                "Bluetooth Explorer users should compare readings across devices before deciding that the beacon, the phone, or the building is the villain."
            ),
            "context_body": (
                "The useful product decision is how much trust to give a jumpy signal. If a workflow only needs 'near enough to investigate,' RSSI can be helpful. If it promises exact distance, precise room choice, or automated safety behavior from one reading, the design is asking a noisy metric to do courtroom testimony."
            ),
            "application_heading": "Test The Variation",
            "application_body": (
                "A practical test is boring in exactly the right way: keep the beacon fixed, rotate the phone, change pocket position, scan for several windows, repeat with another receiver, and record the spread. "
                "Then walk the same path twice. If the signal profile changes more than the product decision can tolerate, the app needs smoothing, confidence states, or a different signal altogether."
            ),
            "note_body": (
                "Do not debug RSSI from a single screenshot. Debug it from repeated readings, device notes, and the exact physical setup that produced the surprise."
            ),
            "next_heading": "Avoid Fake Distance",
            "next_body": (
                "Teams should avoid turning one RSSI value into a polished distance label. Use ranges, confidence language, hysteresis, and fallback checks. "
                "For Bluetooth Explorer, the better next step is to show trend and variance so the person holding the phone can tell whether the signal is stable enough to act on."
            ),
            "risk_heading": "RSSI traps",
            "risk_intro": "RSSI is useful, but it punishes products that pretend the number is cleaner than the radio environment.",
            "challenge_items": [
                "A single RSSI reading can change because the user turns their body, not because the beacon moved.",
                "Phones and gateways may smooth, sample, or expose RSSI differently.",
                "Distance formulas can look precise while hiding huge indoor error bars.",
                "Short sampling windows can trigger false proximity changes.",
                "A product that hides signal uncertainty leaves support teams explaining ghosts.",
            ],
            "checklist_heading": "RSSI debug checklist",
            "checklist_items": [
                "Record repeated RSSI samples instead of judging one scan result.",
                "Test at least two receiver types before blaming the beacon.",
                "Note body position, beacon orientation, walls, doors, and nearby metal.",
                "Use median or percentile windows before making proximity decisions.",
                "Show uncertainty when the signal spread is wider than the product action can tolerate.",
            ],
            "takeaway_heading": "Bluetooth Explorer angle",
            "takeaway_intro": "For Bluetooth Explorer, the win is not making RSSI look calm. The win is showing when it is not calm enough to trust.",
            "geo_answers": [
                "RSSI variation is normal in Bluetooth beacon workflows and does not always mean hardware failure.",
                "Bluetooth Explorer-style signal inspection should compare trend, spread, receiver type, and physical setup.",
                "RSSI should guide proximity decisions only when the sampling window and confidence threshold are explicit.",
                "Exact distance from one RSSI value is fragile in indoor environments.",
                "Better Bluetooth products expose uncertainty instead of hiding noisy signal behavior.",
            ],
            "faq_heading": "RSSI questions",
            "faq_items": [
                ("Does RSSI variation mean my Bluetooth beacon is faulty?", "Not by itself. Variation can come from receiver hardware, scan timing, orientation, body blocking, and the surrounding environment."),
                ("Can RSSI be used for distance?", "Only cautiously. It can support broad proximity decisions, but exact distance from a single RSSI value is fragile indoors."),
                ("What should Bluetooth Explorer users test first?", "Hold the beacon fixed, collect repeated readings, change receiver orientation, compare devices, and inspect the spread before changing product logic."),
            ],
            "sources_heading": "RSSI source",
        }
    return None


def render_live_article(day: date, source_slug: str, source_name: str, item: FeedItem, post: PostMeta, lane: str = "updates") -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    source_published = item.published_at.astimezone().strftime("%B %d, %Y") if item.published_at else human_date
    summary = lane_summary(lane, source_slug, source_name, item)
    custom_profile = bluetooth_live_profile(item, summary, source_name, human_date, source_published, post) if source_slug == "bluetooth" else None
    opening_intro = str(custom_profile["opening_intro"]) if custom_profile else opening_intro_for(source_slug, clean_text(item.title), summary)
    keyword_coverage = keywords_for_lane(lane, source_slug) + [slugify(item.title).replace("-", " ")]
    faq_items = custom_profile["faq_items"] if custom_profile else faq_items_for(source_slug)
    challenge_items = custom_profile["challenge_items"] if custom_profile else challenge_items_for(source_slug)
    geo_answers = custom_profile["geo_answers"] if custom_profile else geo_answers_for(source_slug)
    table_rows = custom_profile["table_rows"] if custom_profile else table_rows_for(source_slug)
    checklist_items = custom_profile["checklist_items"] if custom_profile else checklist_items_for(source_slug)
    table_head = custom_profile["table_head"] if custom_profile else ("Commentary area", "What it covers", "Why it matters")
    table_label = str(custom_profile["table_label"]) if custom_profile else f"{post.topic} commentary coverage"
    current_heading = str(custom_profile["current_heading"]) if custom_profile else f"What changed in {day.strftime('%B %Y')}?"
    current_body = str(custom_profile["current_body"]) if custom_profile else current_status_body(source_slug, source_name, source_published)
    interpretation_heading = str(custom_profile["interpretation_heading"]) if custom_profile else "Why does this update matter?"
    interpretation_body = str(custom_profile["interpretation_body"]) if custom_profile else f"{interpretation_body_for(source_slug, item, summary)} {retrieval_fit_body_for(source_slug)}"
    context_body = str(custom_profile["context_body"]) if custom_profile else f"As of {human_date}, {post.title.lower()} matters because it turns recent reporting from {source_name} into practical guidance on implementation, interoperability, or workflow impact. The useful part is the decision it helps a reader make next."
    application_heading = str(custom_profile["application_heading"]) if custom_profile else "Where does it affect real products?"
    application_body = str(custom_profile["application_body"]) if custom_profile else application_body_for(source_slug)
    note_body = str(custom_profile["note_body"]) if custom_profile else "The product value of this update depends on where it changes real workflows such as deployment timing, compatibility checks, or user-facing behavior. Teams benefit most when the article maps the source update to practical validation and rollout decisions."
    next_heading = str(custom_profile["next_heading"]) if custom_profile else "What should teams watch next?"
    next_body = str(custom_profile["next_body"]) if custom_profile else f"{next_body_for(source_slug)} {search_intent_body_for(source_slug)}"
    risk_heading = str(custom_profile["risk_heading"]) if custom_profile else "What are the key risks in 2026?"
    risk_intro = str(custom_profile["risk_intro"]) if custom_profile else challenge_intro_for(source_slug)
    checklist_heading = str(custom_profile["checklist_heading"]) if custom_profile else "What should teams verify first?"
    takeaway_heading = str(custom_profile["takeaway_heading"]) if custom_profile else "What to remember"
    takeaway_intro = str(custom_profile["takeaway_intro"]) if custom_profile else teaser_for_source_slug(source_slug)
    faq_heading = str(custom_profile["faq_heading"]) if custom_profile else "FAQ"
    sources_heading = str(custom_profile["sources_heading"]) if custom_profile else "Source attribution"

    table_html = "\n".join(
        f"          <tr><td>{escape(col1)}</td><td>{escape(col2)}</td><td>{escape(col3)}</td></tr>"
        for col1, col2, col3 in table_rows
    )
    keyword_html = "\n".join(f"          <li>{escape(item)}</li>" for item in keyword_coverage[:6])
    geo_html = "\n".join(f"          <li>{escape(item)}</li>" for item in geo_answers)
    challenge_html = "\n".join(f"          <li>{escape(item)}</li>" for item in challenge_items)
    checklist_html = "\n".join(f"          <li>{escape(item)}</li>" for item in checklist_items)
    tldr = str(custom_profile["tldr"]) if custom_profile else (
        f"As of {human_date}, {post.title.lower()} matters because it turns a source update from {source_name} into deployment guidance. "
        "The practical question is what changed, where it affects products, and what teams should verify next."
    )
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

      <h2>{escape(current_heading)}</h2>
      <p>{escape(current_body)}</p>

      <table aria-label="{escape(table_label)}">
        <thead>
          <tr><th>{escape(table_head[0])}</th><th>{escape(table_head[1])}</th><th>{escape(table_head[2])}</th></tr>
        </thead>
        <tbody>
{table_html}
        </tbody>
      </table>

      <h2>{escape(interpretation_heading)}</h2>
      <p>{escape(interpretation_body)}</p>
      <div class="capsule">
        <p>{escape(context_body)}</p>
      </div>

      <h2>{escape(application_heading)}</h2>
      <p>{escape(application_body)}</p>
      <div class="capsule">
        <p>{escape(note_body)}</p>
      </div>

      <h2>{escape(next_heading)}</h2>
      <p>{escape(next_body)}</p>

      <div class="panel">
        <h2>{escape(risk_heading)}</h2>
        <p>{escape(risk_intro)}</p>
        <ol>
{challenge_html}
        </ol>
      </div>

      <div class="panel">
        <h2>{escape(checklist_heading)}</h2>
        <ul>
{checklist_html}
        </ul>
      </div>

      <div class="panel">
        <h2>{escape(takeaway_heading)}</h2>
        <p>{escape(takeaway_intro)}</p>
        <ul>
{geo_html}
        </ul>
      </div>

      <h2>{escape(faq_heading)}</h2>
{faq_html}
      <section class="sources" aria-label="Source attribution">
        <h3>{escape(sources_heading)}</h3>
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
            if not item_is_recent_for_target(item, target_day):
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
    if lane in {"protocol", "updates"}:
        for page in CURATED_PROTOCOL_PAGES:
            item = feed_item_from_curated_page(page)
            if item is None:
                continue
            haystack = clean_text(item.title).lower()
            required = LANE_REQUIRED_KEYWORDS[lane]
            if not any(matches_keyword(haystack, keyword) for keyword in required):
                continue
            if item.link in seen_links:
                continue
            seen_links.add(item.link)
            collected.append((page.source_slug, page.source_name, item))
    collected.sort(key=lambda entry: entry[2].published_at.timestamp() if entry[2].published_at else 0.0, reverse=True)
    return collected


def build_live_candidates(target_day: date, lane: str) -> list[LiveBlogCandidate]:
    return [
        build_candidate_from_item(target_day, source_slug, source_name, item, lane=lane)
        for source_slug, source_name, item in unique_feed_items_for_lane(lane, target_day)
    ]

