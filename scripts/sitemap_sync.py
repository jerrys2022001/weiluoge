#!/usr/bin/env python3
"""Synchronize sitemap.xml with the site's public HTML pages."""

from __future__ import annotations

import io
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping

SITE_URL = "https://velocai.net"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
LASTMOD_FIELDS = ("lastmod", "changefreq", "priority")
DATE_SUFFIX_RE = re.compile(r"-(\d{4}-\d{2}-\d{2})\.html$")
EXCLUDED_ROOTS = {".git", ".github", ".tmp", ".playwright-npm-cache", "assets", "docs", "scripts", "skills"}


@dataclass(frozen=True)
class SitemapEntry:
    loc: str
    lastmod: str
    changefreq: str
    priority: str


@dataclass(frozen=True)
class SitemapSyncResult:
    changed: bool
    url_count: int
    added: tuple[str, ...]
    removed: tuple[str, ...]


def page_is_noindex(path: Path) -> bool:
    html = path.read_text(encoding="utf-8", errors="ignore")
    return '<meta name="robots" content="noindex' in html.lower()


def iter_public_html_files(site_root: Path) -> list[Path]:
    html_files: list[Path] = []
    for path in site_root.rglob("*.html"):
        if any(part in EXCLUDED_ROOTS for part in path.relative_to(site_root).parts):
            continue
        if page_is_noindex(path):
            continue
        html_files.append(path)
    return html_files


def file_path_to_url(site_root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(site_root)
    if rel.as_posix() == "index.html":
        return f"{SITE_URL}/"
    if rel.name == "index.html" and len(rel.parts) == 2:
        return f"{SITE_URL}/{rel.parts[0]}/"
    return f"{SITE_URL}/{rel.as_posix()}"


def default_metadata_for_url(loc: str) -> tuple[str, str]:
    path = loc.removeprefix(SITE_URL)
    if path == "/":
        return "weekly", "1.0"
    if path in {"/apps/", "/blog/", "/ai-cleanup-pro/", "/aifind/", "/bluetoothexplorer/", "/dualshot/"}:
        return "weekly", "0.9"
    if path.startswith("/blog/"):
        return "monthly", "0.8"
    if path == "/bluetoothexplorer/document/en/index.html":
        return "monthly", "0.75"
    if path == "/bluetoothexplorer/document/en/bluetooth-gatt-service-uuid-lookup-table.html":
        return "monthly", "0.72"
    return "monthly", "0.7"


def file_lastmod(site_root: Path, file_path: Path, git_cache: dict[str, str | None]) -> str:
    date_match = DATE_SUFFIX_RE.search(file_path.name)
    if date_match:
        return date_match.group(1)

    rel = file_path.relative_to(site_root).as_posix()
    if rel not in git_cache:
        cmd = ["git", "log", "-1", "--format=%cs", "--", rel]
        completed = subprocess.run(cmd, cwd=site_root, capture_output=True, text=True, check=False)
        git_cache[rel] = completed.stdout.strip() or None
    if git_cache[rel]:
        return git_cache[rel]

    return datetime.fromtimestamp(file_path.stat().st_mtime).date().isoformat()


def read_existing_metadata(sitemap_path: Path) -> dict[str, dict[str, str]]:
    if not sitemap_path.exists():
        return {}

    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    metadata: dict[str, dict[str, str]] = {}
    prefix = f"{{{SITEMAP_NS}}}"
    for node in root.findall(f"{prefix}url"):
        loc = node.findtext(f"{prefix}loc")
        if not loc:
            continue
        metadata[loc] = {
            field: node.findtext(f"{prefix}{field}", default="") or ""
            for field in LASTMOD_FIELDS
        }
    return metadata


def sort_key(site_root: Path, file_path: Path) -> tuple[object, ...]:
    rel = file_path.relative_to(site_root).as_posix()
    if rel == "index.html":
        return (0, rel)
    if rel == "apps/index.html":
        return (1, rel)
    if rel == "blog/index.html":
        return (2, rel)
    if rel.startswith("blog/"):
        date_match = DATE_SUFFIX_RE.search(file_path.name)
        if date_match:
            year, month, day = (int(part) for part in date_match.group(1).split("-"))
            return (3, -year, -month, -day, rel)
        return (3, 0, 0, 0, rel)
    if rel == "ai-cleanup-pro/index.html":
        return (4, rel)
    if rel == "privacy-policy.html":
        return (5, rel)
    if rel == "aifind/index.html":
        return (6, rel)
    if rel == "aifind/privacy-policy.html":
        return (7, rel)
    if rel == "bluetoothexplorer/index.html":
        return (8, rel)
    if rel == "bluetoothexplorer/privacy-policy.html":
        return (9, rel)
    if rel.startswith("bluetoothexplorer/guid/"):
        return (10, rel)
    if rel == "bluetoothexplorer/document/en/index.html":
        return (11, rel)
    if rel == "bluetoothexplorer/document/en/bluetooth-gatt-service-uuid-lookup-table.html":
        return (12, rel)
    if rel.startswith("bluetoothexplorer/document/en/"):
        return (13, rel)
    if rel == "dualshot/index.html":
        return (14, rel)
    return (20, rel)


def build_entries(
    site_root: Path,
    sitemap_path: Path,
    overrides: Mapping[str, Mapping[str, str]] | None = None,
) -> list[SitemapEntry]:
    overrides = overrides or {}
    existing = read_existing_metadata(sitemap_path)
    git_cache: dict[str, str | None] = {}
    entries: list[tuple[tuple[object, ...], SitemapEntry]] = []

    for file_path in iter_public_html_files(site_root):
        loc = file_path_to_url(site_root, file_path)
        current = existing.get(loc, {})
        default_changefreq, default_priority = default_metadata_for_url(loc)
        entry_data = {
            "lastmod": current.get("lastmod") or file_lastmod(site_root, file_path, git_cache),
            "changefreq": current.get("changefreq") or default_changefreq,
            "priority": current.get("priority") or default_priority,
        }
        entry_data.update(overrides.get(loc, {}))
        entries.append(
            (
                sort_key(site_root, file_path),
                SitemapEntry(
                    loc=loc,
                    lastmod=entry_data["lastmod"],
                    changefreq=entry_data["changefreq"],
                    priority=entry_data["priority"],
                ),
            )
        )

    return [entry for _, entry in sorted(entries, key=lambda item: item[0])]


def render_sitemap(entries: list[SitemapEntry]) -> bytes:
    ET.register_namespace("", SITEMAP_NS)
    urlset = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for entry in entries:
        url = ET.SubElement(urlset, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = entry.loc
        ET.SubElement(url, f"{{{SITEMAP_NS}}}lastmod").text = entry.lastmod
        ET.SubElement(url, f"{{{SITEMAP_NS}}}changefreq").text = entry.changefreq
        ET.SubElement(url, f"{{{SITEMAP_NS}}}priority").text = entry.priority

    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    buffer = io.BytesIO()
    tree.write(buffer, encoding="utf-8", xml_declaration=True)
    return buffer.getvalue()


def sync_sitemap(
    site_root: Path,
    sitemap_path: Path | None = None,
    overrides: Mapping[str, Mapping[str, str]] | None = None,
) -> SitemapSyncResult:
    site_root = site_root.resolve()
    sitemap_path = (sitemap_path or site_root / "sitemap.xml").resolve()
    existing = read_existing_metadata(sitemap_path)
    entries = build_entries(site_root, sitemap_path, overrides=overrides)
    new_bytes = render_sitemap(entries)
    old_bytes = sitemap_path.read_bytes() if sitemap_path.exists() else b""

    new_urls = tuple(entry.loc for entry in entries)
    old_urls = tuple(existing.keys())
    added = tuple(loc for loc in new_urls if loc not in existing)
    removed = tuple(loc for loc in old_urls if loc not in {entry.loc for entry in entries})

    changed = new_bytes != old_bytes
    if changed:
        sitemap_path.write_bytes(new_bytes)

    return SitemapSyncResult(
        changed=changed,
        url_count=len(entries),
        added=added,
        removed=removed,
    )
