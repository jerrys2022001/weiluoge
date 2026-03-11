#!/usr/bin/env python3
"""Refresh the homepage daily briefing section with product-relevant live news."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from html import escape, unescape
from pathlib import Path

from blog_daily_scheduler import add_git_publish_args, resolve_git_command, run_git_command

SITE_URL = "https://velocai.net"
HOME_INDEX_REL = Path("index.html")
SITEMAP_REL = Path("sitemap.xml")
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
        fallback_image="/assets/images/stock-2026-03/stock-09.jpg",
        item_count=3,
    ),
    BriefSource(
        slug="world",
        eyebrow="Major International Event",
        source_name="BBC World",
        source_url="https://www.bbc.com/news/world",
        feed_url="https://feeds.bbci.co.uk/news/world/rss.xml",
        keywords=("attack", "war", "iran", "ukraine", "tariff", "election", "summit", "sanction", "ceasefire"),
        fallback_image="/assets/images/stock-2026-03/stock-10.jpg",
        item_count=2,
    ),
    BriefSource(
        slug="wireless",
        eyebrow="Wireless Standards Update",
        source_name="GSMA Newsroom",
        source_url="https://www.gsma.com/newsroom/",
        feed_url="https://www.gsma.com/newsroom/feed/",
        keywords=("5g", "6g", "api", "open gateway", "satellite", "network", "wireless", "spectrum", "regulatory", "connectivity"),
        fallback_image="/assets/images/stock-2026-03/stock-07.jpg",
        item_count=3,
    ),
    BriefSource(
        slug="bluetooth",
        eyebrow="Bluetooth Innovation",
        source_name="Bluetooth SIG",
        source_url="https://www.bluetooth.com/blog/",
        feed_url="https://www.bluetooth.com/blog/feed/",
        keywords=("auracast", "industrial", "tracking", "monitoring", "predictive", "audio", "healthcare", "retail", "location", "asset"),
        fallback_image="/assets/images/stock-2026-03/stock-06.jpg",
        item_count=2,
    ),
)

MEDIA_NS = {
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


@dataclass(frozen=True)
class BriefEntry:
    index: int
    source: BriefSource
    item: FeedItem


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


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

    for child in node.findall("link"):
        rel = (child.attrib.get("rel") or "").strip().lower()
        href = (child.attrib.get("href") or "").strip()
        media_type = (child.attrib.get("type") or "").strip().lower()
        if href and rel == "enclosure" and media_type.startswith("image/"):
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
        if keyword.lower() in haystack:
            keyword_score += 1

    if ":" in item.title:
        keyword_score -= 1
    if "writes the" in haystack or "editor" in haystack or "analysis" in haystack or "opinion" in haystack:
        keyword_score -= 1

    return keyword_score


def select_item(items: list[FeedItem], keywords: tuple[str, ...]) -> FeedItem:
    if not items:
        raise ValueError("Feed returned no usable items.")
    ranked = max(enumerate(items), key=lambda pair: (score_item(pair[1], keywords), -pair[0]))
    return ranked[1]


def select_items(items: list[FeedItem], keywords: tuple[str, ...], limit: int) -> list[FeedItem]:
    if limit <= 0:
        return []
    ranked = sorted(
        enumerate(items),
        key=lambda pair: (
            score_item(pair[1], keywords),
            pair[1].published_at.timestamp() if pair[1].published_at else 0.0,
            -pair[0],
        ),
        reverse=True,
    )
    selected: list[FeedItem] = []
    seen_links: set[str] = set()
    for _, item in ranked:
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


def render_entry(entry: BriefEntry) -> str:
    source = entry.source
    item = entry.item
    image_url = item.image_url or source.fallback_image
    image_alt = f"{item.title} thumbnail"
    return f"""      <article class="va-brief-item va-brief-item-{escape(source.slug)}">
        <div class="va-brief-index" aria-hidden="true">{entry.index}</div>
        <div class="va-brief-body">
          <p class="va-brief-label">{escape(source.eyebrow)}</p>
          <h3><a href="{escape(item.link)}" target="_blank" rel="noopener noreferrer">{escape(item.title)}</a></h3>
          <p class="va-brief-meta"><span class="va-brief-source">{escape(source.source_name)}</span> <span aria-hidden="true">|</span> {escape(format_card_date(item.published_at))}</p>
        </div>
        <a class="va-brief-thumb" href="{escape(item.link)}" target="_blank" rel="noopener noreferrer" aria-label="Open story: {escape(item.title)}">
          <img src="{escape(image_url)}" alt="{escape(image_alt)}" loading="lazy" decoding="async">
        </a>
      </article>"""


def render_column(entries: list[BriefEntry]) -> str:
    return "\n".join(render_entry(entry) for entry in entries)


def build_section_html(entries: list[BriefEntry], refreshed_at: datetime) -> str:
    left_column = entries[:5]
    right_column = entries[5:10]
    return f"""
    <div class="va-briefing-head">
      <div class="va-briefing-title-wrap">
        <h2 class="va-briefing-heading"><span class="is-apple">苹果</span><span class="is-dot">·</span><span class="is-world">国际</span><span class="is-dot">·</span><span class="is-wireless">通信</span><span class="is-dot">·</span><span class="is-bluetooth">蓝牙</span></h2>
      </div>
      <p class="va-briefing-stamp">Updated daily 08:30 <span aria-hidden="true">|</span> {escape(format_refresh_time(refreshed_at))}</p>
    </div>
    <div class="va-briefing-grid">
      <div class="va-briefing-column">
{render_column(left_column)}
      </div>
      <div class="va-briefing-column">
{render_column(right_column)}
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


def publish_homepage_to_git(repo_root: Path, remote: str, branch: str, push: bool) -> str:
    git_command = resolve_git_command()
    tracked_paths = [HOME_INDEX_REL.as_posix(), SITEMAP_REL.as_posix()]

    run_git_command(repo_root, git_command, ["add", "--", *tracked_paths])
    staged = run_git_command(repo_root, git_command, ["diff", "--cached", "--name-only", "--", *tracked_paths])
    if not staged.stdout.strip():
        return "unchanged"

    stamp = datetime.now().astimezone().strftime("%Y-%m-%d")
    run_git_command(
        repo_root,
        git_command,
        ["commit", "-m", f"Refresh homepage briefing: {stamp}", "--only", "--", *tracked_paths],
    )

    if push:
        run_git_command(repo_root, git_command, ["push", remote, branch])
        return f"committed+pushed({remote}/{branch})"
    return "committed"


def build_briefing() -> tuple[list[BriefEntry], datetime]:
    entries: list[BriefEntry] = []
    next_index = 1
    for source in BRIEF_SOURCES:
        items = parse_feed_items(fetch_bytes(source.feed_url))
        selected = select_items(items, source.keywords, source.item_count)
        if not selected:
            fallback = select_item(items, source.keywords)
            selected = [fallback]
        for item in selected:
            entries.append(BriefEntry(index=next_index, source=source, item=item))
            next_index += 1
    return entries[:10], datetime.now().astimezone()


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
    section_html = build_section_html(entries, refreshed_at)

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
