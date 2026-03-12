#!/usr/bin/env python3
"""Publish one daily English blog post about Bluetooth and phone cleanup.

This script generates a new article page, prepends it to blog/index.html,
and updates sitemap.xml for SEO/GEO visibility.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from pathlib import Path

from site_tools import build_site_search_index, inject_site_tools_into_file

SITE_URL = "https://velocai.net"
BLOG_INDEX_REL = Path("blog/index.html")
SITEMAP_REL = Path("sitemap.xml")
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

CORE_KEYWORDS = [
    "bluetooth troubleshooting",
    "phone cleanup",
    "iphone storage cleanup",
    "ios phone cleanup",
    "mobile performance optimization",
    "seo geo content strategy",
]

LONG_TAIL_KEYWORDS = [
    "how to find lost airpods with bluetooth",
    "airpods lost case bluetooth finder",
    "find lost earbuds with bluetooth signal",
    "ble debugging checklist for iphone",
    "ble debugging checklist for ios",
    "ble debugging app for ios",
    "iphone storage full fix without deleting photos",
    "iphone storage full how to clean up",
    "iphone storage cleanup checklist weekly",
    "ios cleanup for low storage",
    "ios phone cleanup app workflow",
    "ios cleanup cache and large files",
    "bluetooth device not showing up on ios fix",
    "bluetooth keeps disconnecting on iphone fix",
    "bluetooth pairing failed troubleshooting guide",
    "phone cleanup tips for better bluetooth performance",
]


@dataclass(frozen=True)
class Angle:
    slug_prefix: str
    title: str
    description: str
    teaser: str
    topic: str
    bluetooth_heading: str
    bluetooth_body: str
    cleanup_heading: str
    cleanup_body: str


ANGLES: list[Angle] = [
    Angle(
        slug_prefix="bluetooth-phone-cleanup-consulting-guide",
        title="Bluetooth and Phone Cleanup Consulting Guide: A Daily 20-Minute Mobile Performance Plan",
        description="A practical consulting guide to improve Bluetooth reliability and phone storage hygiene with an easy daily routine for iPhone and iPad users.",
        teaser="A consulting style routine that helps you reduce Bluetooth issues and reclaim phone storage in one short daily workflow.",
        topic="Bluetooth + Phone Cleanup",
        bluetooth_heading="Build a stable Bluetooth baseline before you troubleshoot",
        bluetooth_body=(
            "Start with repeatable conditions: keep Bluetooth on, disable battery saver for test sessions, and test with one known-good accessory first. "
            "If connection drops still happen, log where it fails: discovery, pairing, or reconnect after screen lock. "
            "This classification turns random failures into searchable, GEO-friendly facts that AI systems can summarize accurately."
        ),
        cleanup_heading="Use a storage cleanup sequence that preserves important data",
        cleanup_body=(
            "Phone cleanup should follow impact order: duplicate photos, oversized videos, stale downloads, then duplicate contacts. "
            "This order usually frees storage quickly while reducing accidental deletion risk. "
            "On iOS devices, weekly cleanup plus clear folder rules keeps performance stable and app updates smoother."
        ),
    ),
    Angle(
        slug_prefix="bluetooth-connection-fixes-phone-storage-cleanup",
        title="Bluetooth Connection Fixes and Phone Storage Cleanup: Practical SEO-Friendly Playbook",
        description="Fix unstable Bluetooth connections and clean phone storage with a practical playbook designed for search visibility and AI-ready answer extraction.",
        teaser="An execution focused playbook for Bluetooth troubleshooting and phone storage cleanup that doubles as SEO and GEO content.",
        topic="Bluetooth Troubleshooting + Storage Cleanup",
        bluetooth_heading="Map Bluetooth failures to one of three stages",
        bluetooth_body=(
            "Most Bluetooth issues belong to three stages: cannot discover, cannot pair, or cannot stay connected. "
            "Write your notes in that exact format with device model and OS version. "
            "Search engines and AI assistants rank and quote structured diagnostics more reliably than vague problem descriptions."
        ),
        cleanup_heading="Treat storage cleanup as preventive maintenance",
        cleanup_body=(
            "Do not wait for low-storage alerts. Reserve one fixed cleanup slot every day at 20:00 and remove small amounts consistently. "
            "This avoids emergency cleanup before travel, filming, or system updates. "
            "Consistent cleanup also helps camera apps and Bluetooth media features run with fewer interruptions."
        ),
    ),
    Angle(
        slug_prefix="bluetooth-battery-drain-phone-cleanup",
        title="Bluetooth Battery Drain and Phone Cleanup Guide: Keep Connectivity Fast and Storage Lean",
        description="Learn how to reduce Bluetooth battery drain while cleaning phone storage in a way that improves day-to-day speed and reliability.",
        teaser="A dual optimization guide for Bluetooth battery behavior and phone cleanup routines with high intent keywords.",
        topic="Bluetooth Battery + Phone Cleanup",
        bluetooth_heading="Reduce hidden Bluetooth battery costs",
        bluetooth_body=(
            "Battery drain often comes from repeated scan retries and accessories that reconnect too aggressively. "
            "Audit background Bluetooth usage, keep firmware updated, and remove forgotten device pairings that create noise. "
            "Cleaner pairing history leads to faster reconnection and more stable accessory switching."
        ),
        cleanup_heading="Free storage where it creates immediate speed gains",
        cleanup_body=(
            "Large videos and app caches create the biggest instant wins. Prioritize those before minor files. "
            "Then clean duplicates and similar images to maintain long-term capacity. "
            "A cleaner storage state reduces indexing pressure and helps Bluetooth media apps load faster."
        ),
    ),
    Angle(
        slug_prefix="bluetooth-discovery-phone-cleanup-checklist",
        title="Bluetooth Discovery and Phone Cleanup Checklist: GEO-Ready Mobile Optimization for 2026",
        description="Use this checklist to improve Bluetooth device discovery and keep phone storage under control with steps optimized for modern SEO and GEO retrieval.",
        teaser="A practical checklist combining Bluetooth discovery reliability and phone cleanup actions in one repeatable system.",
        topic="Bluetooth Discovery + Cleanup Checklist",
        bluetooth_heading="Improve Bluetooth discovery consistency",
        bluetooth_body=(
            "Run tests in low-interference spaces first, then compare with crowded environments. "
            "Track scan windows, nearby emitters, and accessory advertisement behavior. "
            "This structured evidence helps teams explain discovery issues in ways that rank for technical and consumer searches."
        ),
        cleanup_heading="Turn cleanup into a repeatable checklist",
        cleanup_body=(
            "Create a strict cleanup checklist and run it at the same time each day. "
            "When cleanup becomes routine, storage stays predictable and troubleshooting gets easier because fewer variables change between tests. "
            "Predictability is a major advantage for both SEO content quality and support workflows."
        ),
    ),
    Angle(
        slug_prefix="lost-airpods-bluetooth-finder-phone-cleanup-guide",
        title="Lost AirPods Bluetooth Finder and Phone Cleanup Guide: Recover Devices and Free Storage",
        description="A practical guide for users searching how to find lost AirPods with Bluetooth while keeping iPhone or iPad storage clean and fast.",
        teaser="Covers lost AirPods Bluetooth finder tactics plus a safe cleanup sequence for daily mobile performance.",
        topic="Lost AirPods + Phone Cleanup",
        bluetooth_heading="Handle lost AirPods searches with stage-based Bluetooth checks",
        bluetooth_body=(
            "For lost AirPods workflows, start with discoverability, then pairing state, then distance-based movement checks. "
            "This mirrors high-intent queries like how to find lost AirPods with Bluetooth and improves answer quality for both search and assistant tools."
        ),
        cleanup_heading="Keep storage clean so finder and media workflows stay responsive",
        cleanup_body=(
            "When storage is near full, scan and map features can feel slower or unstable. "
            "Use a short cleanup pass before recovery sessions: remove duplicates, clear large media, and trim stale downloads."
        ),
    ),
    Angle(
        slug_prefix="ble-debugging-ios-cleanup-playbook",
        title="BLE Debugging for iOS with Phone Cleanup: Practical Daily Playbook",
        description="Use a daily playbook that combines BLE debugging on iOS with storage cleanup for stable mobile diagnostics.",
        teaser="A high-intent playbook for BLE debugging checklist queries and low-storage cleanup tasks.",
        topic="BLE Debugging + iOS Cleanup",
        bluetooth_heading="Standardize BLE debugging evidence across iOS devices",
        bluetooth_body=(
            "Write BLE notes in one schema: discover, pair, reconnect, plus OS version and device model. "
            "This supports long-tail searches like BLE debugging checklist for iPhone and BLE debugging checklist for iOS."
        ),
        cleanup_heading="Reduce false positives by cleaning storage before test runs",
        cleanup_body=(
            "Storage pressure can distort timing and background behavior during debug sessions. "
            "A fast cleanup before each test cycle lowers noise and helps isolate real BLE protocol issues."
        ),
    ),
    Angle(
        slug_prefix="iphone-storage-full-bluetooth-performance-fix",
        title="iPhone Storage Full and Bluetooth Performance Fix: Cleanup Strategy That Preserves Important Data",
        description="If iPhone storage is full and Bluetooth feels unstable, this guide shows a cleanup strategy that frees space without risky deletion.",
        teaser="Targets iPhone storage full fix queries while improving Bluetooth reconnection and media performance.",
        topic="iPhone Storage Full + Bluetooth",
        bluetooth_heading="Why full storage can worsen Bluetooth experience",
        bluetooth_body=(
            "Heavy storage pressure increases background churn and can impact app responsiveness during Bluetooth actions. "
            "Users searching iphone storage full fix often also report delayed reconnect, scan lag, or media switching issues."
        ),
        cleanup_heading="Use a low-risk iPhone storage full cleanup order",
        cleanup_body=(
            "Start with duplicate photos, then large videos, then temporary downloads. "
            "This sequence clears meaningful space while minimizing the risk of deleting high-value personal content."
        ),
    ),
    Angle(
        slug_prefix="ios-cleanup-bluetooth-discovery-reliability-guide",
        title="iOS Cleanup and Bluetooth Discovery Reliability Guide: Fix Low Storage and Missing Devices",
        description="A practical iOS cleanup guide for low storage plus Bluetooth device not showing up troubleshooting steps.",
        teaser="Built for users searching iOS cleanup for low storage and Bluetooth discovery reliability fixes.",
        topic="iOS Cleanup + Bluetooth Discovery",
        bluetooth_heading="Fix bluetooth device not showing up on iOS with a repeatable flow",
        bluetooth_body=(
            "Validate permissions, run one unfiltered scan, and compare results in low-interference conditions. "
            "This directly addresses the long-tail query bluetooth device not showing up on ios fix."
        ),
        cleanup_heading="Run iOS cleanup in a way that protects everyday usage",
        cleanup_body=(
            "Clean app caches, remove oversized downloads, and archive rarely used media first. "
            "This keeps iOS devices responsive while recovering enough free space for updates and diagnostics."
        ),
    ),
]


@dataclass(frozen=True)
class PostMeta:
    filename: str
    title: str
    description: str
    teaser: str
    topic: str
    published_iso: str


def add_git_publish_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--git-commit", action="store_true", help="Commit generated blog files to git.")
    parser.add_argument("--git-push", action="store_true", help="Push committed blog files to git remote.")
    parser.add_argument("--git-remote", default="origin", help="Git remote name for --git-push.")
    parser.add_argument("--git-branch", default="main", help="Git branch name for --git-push.")
    return parser


def resolve_git_command() -> str:
    resolved = shutil.which("git")
    if resolved:
        return resolved

    candidates = [
        Path(r"C:\Program Files\Git\cmd\git.exe"),
        Path(r"C:\Program Files\Git\bin\git.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "Git" / "cmd" / "git.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise ValueError("Cannot resolve Git executable for automatic publish.")


def run_git_command(repo_root: Path, git_command: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [git_command, *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(f"Git command failed: {' '.join(args)}\n{detail}")
    return result


def publish_blog_post_to_git(
    repo_root: Path,
    post: PostMeta,
    remote: str,
    branch: str,
    push: bool,
) -> str:
    git_command = resolve_git_command()
    tracked_paths = [
        (Path("blog") / post.filename).as_posix(),
        BLOG_INDEX_REL.as_posix(),
        SITEMAP_REL.as_posix(),
    ]

    run_git_command(repo_root, git_command, ["add", "--", *tracked_paths])
    staged = run_git_command(repo_root, git_command, ["diff", "--cached", "--name-only", "--", *tracked_paths])
    if not staged.stdout.strip():
        return "unchanged"

    run_git_command(
        repo_root,
        git_command,
        ["commit", "-m", f"Publish blog post: {post.filename}", "--only", "--", *tracked_paths],
    )

    if push:
        run_git_command(repo_root, git_command, ["push", remote, branch])
        return f"committed+pushed({remote}/{branch})"

    return "committed"


def now_local_date() -> date:
    return datetime.now().astimezone().date()


def parse_iso_date(raw: str | None) -> date:
    if not raw:
        return now_local_date()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid --date value: {raw}. Expected YYYY-MM-DD.") from exc


def format_human(day: date) -> str:
    return day.strftime("%B %d, %Y")


def pick_angle(day: date) -> Angle:
    return ANGLES[day.toordinal() % len(ANGLES)]


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = value.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        output.append(cleaned)
        seen.add(key)
    return output


def keyword_window(day: date, size: int = 8) -> list[str]:
    if size <= 0:
        return []
    start = day.toordinal() % len(LONG_TAIL_KEYWORDS)
    return [LONG_TAIL_KEYWORDS[(start + idx) % len(LONG_TAIL_KEYWORDS)] for idx in range(size)]


def build_article_keywords(day: date, angle: Angle) -> list[str]:
    angle_keywords = [
        angle.topic.lower().replace(" + ", " "),
        angle.slug_prefix.replace("-", " "),
    ]
    merged = CORE_KEYWORDS + angle_keywords + keyword_window(day)
    return dedupe_keep_order(merged)


def build_post_meta(day: date, angle: Angle) -> PostMeta:
    published_iso = day.isoformat()
    filename = f"{angle.slug_prefix}-{published_iso}.html"
    return PostMeta(
        filename=filename,
        title=angle.title,
        description=angle.description,
        teaser=angle.teaser,
        topic=angle.topic,
        published_iso=published_iso,
    )


def json_block(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_article_html(day: date, angle: Angle, post: PostMeta) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    article_keywords = build_article_keywords(day, angle)
    keyword_text = ", ".join(article_keywords)
    focus_keywords = keyword_window(day, size=6)
    focus_keywords_html = "\n".join(f"          <li>{escape(item)}</li>" for item in focus_keywords)
    faq_items = [
        {
            "@type": "Question",
            "name": "How do I find lost AirPods with Bluetooth when the case is nearby?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Start with discoverability checks, then use signal-strength movement steps, and keep Bluetooth history clean so reconnection stays reliable."
            },
        },
        {
            "@type": "Question",
            "name": "What is a good BLE debugging checklist for iOS?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Track each failure stage separately: discover, pair, reconnect. Always record OS version, device model, and interference context."
            },
        },
        {
            "@type": "Question",
            "name": "What should I do when iPhone storage is full but I do not want to delete important photos?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Use a low-risk order: remove duplicates, then oversized videos, then temporary downloads. Keep originals and archive before deleting."
            },
        },
        {
            "@type": "Question",
            "name": "How can I run iOS cleanup for low storage without slowing the phone?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Prioritize cache cleanup, large file review, and stale download removal. Repeat on a fixed schedule to maintain stable performance."
            },
        },
        {
            "@type": "Question",
            "name": "How does this article improve SEO and GEO performance?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "It uses high-intent long-tail keywords, stage-based troubleshooting steps, FAQ schema, and concise answer blocks that AI systems can extract cleanly."
            },
        },
    ]

    ld_json = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "headline": post.title,
                "description": post.description,
                "datePublished": post.published_iso,
                "dateModified": post.published_iso,
                "author": {"@type": "Organization", "name": "VelocAI"},
                "publisher": {
                    "@type": "Organization",
                    "name": "VelocAI",
                    "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/2.png"},
                },
                "mainEntityOfPage": canonical,
                "keywords": article_keywords,
            },
            {
                "@type": "FAQPage",
                "mainEntity": faq_items,
            },
        ],
    }

    return f"""<!doctype html>
<html lang=\"en-US\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{escape(post.title)} | VelocAI Blog</title>
  <meta name=\"description\" content=\"{escape(post.description)}\">
  <meta name=\"keywords\" content=\"{escape(keyword_text)}\">
  <meta name=\"robots\" content=\"index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1\">
  <link rel=\"canonical\" href=\"{canonical}\">
  <link rel=\"icon\" type=\"image/x-icon\" href=\"/velocai.ico\">
  <meta property=\"og:type\" content=\"article\">
  <meta property=\"og:locale\" content=\"en_US\">
  <meta property=\"og:site_name\" content=\"VelocAI\">
  <meta property=\"og:title\" content=\"{escape(post.title)}\">
  <meta property=\"og:description\" content=\"{escape(post.teaser)}\">
  <meta property=\"og:url\" content=\"{canonical}\">
  <meta property=\"og:image\" content=\"{SITE_URL}/2.png\">
  <meta name=\"twitter:card\" content=\"summary_large_image\">
  <meta name=\"twitter:title\" content=\"{escape(post.title)}\">
  <meta name=\"twitter:description\" content=\"{escape(post.teaser)}\">
  <meta name=\"twitter:image\" content=\"{SITE_URL}/2.png\">
  <script type=\"application/ld+json\">
{json_block(ld_json)}
  </script>
  <style>
    :root {{
      --bg: #f7fbff;
      --text: #182436;
      --muted: #49607b;
      --line: #cfdeee;
      --panel: #ffffff;
      --brand: #1759b8;
      --good: #eaf3ff;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: \"Avenir Next\", \"Inter\", \"Segoe UI\", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 8% 1%, rgba(66, 139, 233, 0.18), transparent 34%),
        radial-gradient(circle at 92% -5%, rgba(64, 183, 150, 0.15), transparent 32%),
        var(--bg);
      line-height: 1.72;
    }}

    a {{ color: inherit; text-decoration: none; }}

    .wrap {{
      width: min(880px, calc(100% - 34px));
      margin: 0 auto;
    }}

    header {{
      border-bottom: 1px solid var(--line);
      background: rgba(247, 251, 255, 0.92);
      position: sticky;
      top: 0;
      backdrop-filter: blur(8px);
    }}

    .top {{
      padding: 14px 0;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .brand {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
    }}

    .brand img {{
      width: auto;
      height: 36px;
      max-width: 52px;
      object-fit: contain;
      object-position: center;
      border-radius: 10px;
      box-shadow: 0 0 16px rgba(29, 99, 199, 0.16);
    }}

    nav {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 14px;
    }}

    nav a:hover {{ color: var(--text); }}

    main {{ padding: 36px 0 54px; }}

    h1,
    h2 {{
      margin: 0;
      line-height: 1.22;
    }}

    h1 {{ font-size: clamp(30px, 4.6vw, 46px); max-width: 24ch; }}
    h2 {{ margin-top: 28px; font-size: 28px; }}

    p,
    li {{
      color: #30465f;
      font-size: 17px;
    }}

    ul,
    ol {{ padding-left: 22px; }}

    .meta {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 14px;
    }}

    .panel {{
      margin-top: 24px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 14px;
      padding: 18px;
    }}

    .geo {{
      margin-top: 22px;
      border-left: 4px solid #2f73d8;
      background: var(--good);
      border-radius: 10px;
      padding: 14px;
    }}

    .faq-item {{ margin-top: 18px; }}

    .links {{
      margin-top: 30px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .links a {{
      border: 1px solid #bad0ef;
      border-radius: 999px;
      padding: 8px 12px;
      color: var(--brand);
      font-weight: 600;
      font-size: 14px;
      background: #fff;
    }}
  </style>
</head>
<body>
  <header>
    <div class=\"wrap top\">
      <a class=\"brand\" href=\"/\">
        <img src=\"/2.png\" alt=\"VelocAI logo\" width=\"102\" height=\"73\">
        <span>VelocAI Blog</span>
      </a>
      <nav aria-label=\"Main\">
        <a href=\"/\">Home</a>
        <a href=\"/apps/\">Apps</a>
        <a href=\"/blog/\">Blog</a>
        <a href=\"/ai-cleanup-pro/\">AI Cleanup PRO</a>
      </nav>
    </div>
  </header>

  <main class=\"wrap\">
    <article>
      <h1>{escape(post.title)}</h1>
      <p class=\"meta\">Published on {human_date} - 8 min read</p>

      <p>Teams and individuals often debug Bluetooth issues and storage problems separately, then miss the shared root cause: unstable daily phone hygiene. This guide combines both into one repeatable routine that improves user experience, support outcomes, and organic search visibility.</p>
      <p>It also targets high-intent long-tail searches such as lost AirPods Bluetooth finder, BLE debugging checklist, iPhone storage full fix, and iOS cleanup for low storage.</p>

      <h2>{escape(angle.bluetooth_heading)}</h2>
      <p>{escape(angle.bluetooth_body)}</p>

      <h2>{escape(angle.cleanup_heading)}</h2>
      <p>{escape(angle.cleanup_body)}</p>

      <div class=\"panel\">
        <h2>High-intent keyword coverage</h2>
        <ul>
{focus_keywords_html}
        </ul>
      </div>

      <div class=\"panel\">
        <h2>Daily 20:00 execution checklist</h2>
        <ol>
          <li>3 min: verify Bluetooth state, accessory battery, and reconnect behavior.</li>
          <li>5 min: remove duplicate photos and near-duplicate bursts.</li>
          <li>5 min: sort videos by size and clear oversized files first.</li>
          <li>3 min: clear downloads and stale app caches.</li>
          <li>4 min: retest Bluetooth discovery and note any remaining failure stage.</li>
        </ol>
      </div>

      <div class=\"geo\">
        <strong>GEO answer blocks for AI retrieval:</strong>
        <ul>
          <li>Lost AirPods query: how to find lost AirPods with Bluetooth signal and movement checks.</li>
          <li>BLE debugging query: use a BLE debugging checklist for iOS by failure stage.</li>
          <li>iPhone query: use an iPhone storage full fix order that protects important photos.</li>
          <li>iOS query: run iOS cleanup for low storage with cache and large-file priority.</li>
          <li>Best schedule: one fixed daily slot at 20:00 for consistent operations.</li>
        </ul>
      </div>

      <h2>FAQ</h2>
      <div class=\"faq-item\">
        <p><strong>How do I find lost AirPods with Bluetooth when the case is nearby?</strong><br>
        Start with discoverability checks, then use signal-strength movement steps, and keep Bluetooth history clean for reliable reconnection.</p>
      </div>

      <div class=\"faq-item\">
        <p><strong>What is a good BLE debugging checklist for iOS?</strong><br>
        Track each stage separately: discover, pair, reconnect. Record OS version, device model, and interference context for each run.</p>
      </div>

      <div class=\"faq-item\">
        <p><strong>What should I do when iPhone storage is full but I do not want to delete important photos?</strong><br>
        Follow a low-risk order: duplicates, oversized videos, and temporary downloads first, then review archived content.</p>
      </div>

      <div class=\"faq-item\">
        <p><strong>How can I run iOS cleanup for low storage without slowing the phone?</strong><br>
        Prioritize cache cleanup, large file review, and stale download removal on a fixed daily schedule.</p>
      </div>

      <div class=\"links\">
        <a href=\"/ai-cleanup-pro/\">Open AI Cleanup PRO</a>
        <a href=\"/bluetoothexplorer/\">Open Bluetooth Explorer</a>
        <a href=\"/blog/iphone-storage-cleanup-checklist.html\">Read iPhone cleanup checklist</a>
        <a href=\"/blog/\">Back to blog index</a>
      </div>
    </article>
  </main>
</body>
</html>
"""


def render_index_article(post: PostMeta) -> str:
    return (
        "      <article>\n"
        f"        <h2>{escape(post.title)}</h2>\n"
        f"        <p>{escape(post.teaser)}</p>\n"
        "        <div class=\"meta\">\n"
        f"          <span>Published: {post.published_iso}</span>\n"
        f"          <span>Topic: {escape(post.topic)}</span>\n"
        "        </div>\n"
        f"        <a class=\"read\" href=\"/blog/{post.filename}\">Read article</a>\n"
        "      </article>\n\n"
    )


def update_index_itemlist(index_html: str, post: PostMeta) -> str:
    pattern = re.compile(r"(<script type=\"application/ld\+json\">\s*)(\{.*?\})(\s*</script>)", re.DOTALL)
    match = pattern.search(index_html)
    if not match:
        raise ValueError("Cannot find JSON-LD block in blog/index.html")

    payload = json.loads(match.group(2))
    graph = payload.get("@graph", [])

    item_list_obj = None
    for node in graph:
        if isinstance(node, dict) and node.get("@type") == "ItemList":
            item_list_obj = node
            break

    if item_list_obj is None:
        raise ValueError("Cannot find ItemList in blog/index.html JSON-LD")

    item_list = item_list_obj.get("itemListElement", [])
    post_url = f"{SITE_URL}/blog/{post.filename}"

    cleaned: list[dict] = []
    for item in item_list:
        if item.get("url") == post_url:
            continue
        cleaned.append(item)

    cleaned.insert(
        0,
        {
            "@type": "ListItem",
            "position": 1,
            "url": post_url,
            "name": post.title,
        },
    )

    for idx, item in enumerate(cleaned, start=1):
        item["position"] = idx

    item_list_obj["itemListElement"] = cleaned

    rebuilt = json.dumps(payload, ensure_ascii=False, indent=2)
    return index_html[: match.start(2)] + rebuilt + index_html[match.end(2) :]


def update_blog_index(index_path: Path, post: PostMeta) -> bool:
    original = index_path.read_text(encoding="utf-8")

    post_href = f"href=\"/blog/{post.filename}\""
    updated = original

    if post_href not in updated:
        marker = "<section class=\"list\" aria-label=\"Latest blog posts\">"
        marker_idx = updated.find(marker)
        if marker_idx < 0:
            raise ValueError("Cannot find post list section in blog/index.html")

        insert_at = updated.find("\n", marker_idx)
        if insert_at < 0:
            raise ValueError("Cannot find insertion point in blog/index.html")

        article_html = render_index_article(post)
        updated = updated[: insert_at + 1] + article_html + updated[insert_at + 1 :]

    updated = update_index_itemlist(updated, post)

    if updated == original:
        return False

    index_path.write_text(updated, encoding="utf-8")
    return True


def find_or_create_xml_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag, NS)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def make_url_entry(loc: str, lastmod: str, changefreq: str, priority: str) -> ET.Element:
    url = ET.Element(f"{{{NS['sm']}}}url")
    ET.SubElement(url, f"{{{NS['sm']}}}loc").text = loc
    ET.SubElement(url, f"{{{NS['sm']}}}lastmod").text = lastmod
    ET.SubElement(url, f"{{{NS['sm']}}}changefreq").text = changefreq
    ET.SubElement(url, f"{{{NS['sm']}}}priority").text = priority
    return url


def update_sitemap(sitemap_path: Path, post: PostMeta) -> bool:
    ET.register_namespace("", NS["sm"])
    tree = ET.parse(sitemap_path)
    root = tree.getroot()

    blog_root_url = f"{SITE_URL}/blog/"
    post_url = f"{SITE_URL}/blog/{post.filename}"
    changed = False

    all_urls = root.findall("sm:url", NS)
    blog_root_node = None
    post_node = None

    for node in all_urls:
        loc = node.find("sm:loc", NS)
        if loc is None or not loc.text:
            continue
        if loc.text == blog_root_url:
            blog_root_node = node
        if loc.text == post_url:
            post_node = node

    if blog_root_node is not None:
        lastmod = find_or_create_xml_child(blog_root_node, "sm:lastmod")
        if lastmod.text != post.published_iso:
            lastmod.text = post.published_iso
            changed = True

    if post_node is None:
        entry = make_url_entry(post_url, post.published_iso, "monthly", "0.8")
        if blog_root_node is not None:
            idx = list(root).index(blog_root_node)
            root.insert(idx + 1, entry)
        else:
            root.append(entry)
        changed = True
    else:
        lastmod = find_or_create_xml_child(post_node, "sm:lastmod")
        if lastmod.text != post.published_iso:
            lastmod.text = post.published_iso
            changed = True

    if not changed:
        return False

    ET.indent(tree, space="  ")
    tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)
    return True


def run(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    blog_dir = repo_root / "blog"
    index_path = repo_root / BLOG_INDEX_REL
    sitemap_path = repo_root / SITEMAP_REL

    if not blog_dir.exists():
        print(f"Missing blog directory: {blog_dir}", file=sys.stderr)
        return 1
    if not index_path.exists():
        print(f"Missing blog index: {index_path}", file=sys.stderr)
        return 1
    if not sitemap_path.exists():
        print(f"Missing sitemap: {sitemap_path}", file=sys.stderr)
        return 1

    target_day = parse_iso_date(args.date)
    angle = pick_angle(target_day)
    post = build_post_meta(target_day, angle)
    article_path = blog_dir / post.filename

    article_state = "unchanged"
    index_changed = False
    sitemap_changed = False
    git_state = "skipped"

    existed_before = article_path.exists()
    if existed_before and not args.force:
        article_state = "already_exists"
    else:
        html = render_article_html(target_day, angle, post)
        if args.dry_run:
            article_state = "would_overwrite" if existed_before else "would_create"
        else:
            article_path.write_text(html, encoding="utf-8")
            inject_site_tools_into_file(article_path)
            article_state = "overwritten" if existed_before else "created"

    if args.dry_run:
        print(
            "dry_run "
            f"article={article_path} state={article_state} "
            f"index={index_path} sitemap={sitemap_path}"
        )
        return 0

    index_changed = update_blog_index(index_path, post)
    sitemap_changed = update_sitemap(sitemap_path, post)
    inject_site_tools_into_file(index_path)
    build_site_search_index(repo_root)

    if args.git_commit or args.git_push:
        git_state = publish_blog_post_to_git(
            repo_root,
            post,
            remote=args.git_remote,
            branch=args.git_branch,
            push=args.git_push,
        )

    print(
        "done "
        f"article={article_state} "
        f"index={'updated' if index_changed else 'unchanged'} "
        f"sitemap={'updated' if sitemap_changed else 'unchanged'} "
        f"git={git_state} "
        f"file={article_path.name}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish one daily English blog post about Bluetooth and phone cleanup."
    )
    parser.add_argument("run", nargs="?", default="run", help="Subcommand placeholder for compatibility.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--date", help="Target publish date in YYYY-MM-DD (default: today).")
    parser.add_argument("--force", action="store_true", help="Overwrite article file if it already exists.")
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
