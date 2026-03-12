#!/usr/bin/env python3
"""Refresh shared site tools assets and build a static search index."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

HEAD_INJECTION = '  <link rel="stylesheet" href="/assets/css/site-tools.css">\n'
SCRIPT_INJECTION = '  <script src="/assets/js/site-tools.js" defer></script>\n'
SEARCH_INDEX_REL = Path("assets/data/site-search-index.json")
EXCLUDED_DIRS = {
    ".git",
    ".github",
    ".playwright-browsers",
    ".playwright-cli",
    ".playwright-npm-cache",
    ".tmp",
    ".tmp-gcm",
    ".tmp-git",
    ".gsc-playwright-profile",
    ".gsc-playwright-profile-snapshot",
    ".x-playwright-profile",
    ".x-playwright-profile-20260307011848",
    "output",
    "scripts",
    "skills",
}
EXCLUDED_FILES = {
    "googlec013bfb5fe336f73.html",
    "superlist_home.html",
}
LANGUAGE_FOLDERS = {"en": "en-US", "cn": "zh-CN", "zh": "zh-CN"}

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
LANG_RE = re.compile(r"<html\b[^>]*\blang=(['\"])(.*?)\1", re.IGNORECASE | re.DOTALL)
META_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(['\"])(.*?)\2", re.DOTALL)
BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class SearchRecord:
    url: str
    title: str
    description: str
    heading: str
    category: str
    locale: str
    alternates: dict[str, str]
    terms: str


def clean_html_text(value: str) -> str:
    collapsed = TAG_RE.sub(" ", value or "")
    return SPACE_RE.sub(" ", unescape(collapsed)).strip()


def extract_meta_content(text: str, key: str, attr_name: str = "name") -> str:
    wanted_key = key.lower()
    wanted_attr = attr_name.lower()
    for match in META_RE.finditer(text):
        tag = match.group(0)
        attrs = {name.lower(): val for name, _, val in ATTR_RE.findall(tag)}
        if attrs.get(wanted_attr, "").lower() == wanted_key:
            return clean_html_text(attrs.get("content", ""))
    return ""


def infer_locale(text: str, relative_path: Path) -> str:
    lang_match = LANG_RE.search(text)
    if lang_match:
        lang = lang_match.group(2).strip()
        if lang:
            return lang

    for part in relative_path.parts:
        locale = LANGUAGE_FOLDERS.get(part.lower())
        if locale:
            return locale
    return "en-US"


def normalize_url(relative_path: Path) -> str:
    rel = relative_path.as_posix()
    if rel.endswith("/index.html"):
        rel = rel[:-10]
    elif rel == "index.html":
        return "/"
    return f"/{rel}"


def infer_category(relative_path: Path) -> str:
    parts = relative_path.parts
    if not parts:
        return "Site"
    if parts[0] == "blog":
        return "Blog"
    if parts[0] == "apps":
        return "Apps"
    if parts[0] == "aifind":
        return "Find AI"
    if parts[0] == "ai-cleanup-pro":
        return "AI Cleanup PRO"
    if parts[0] == "bluetoothexplorer":
        if len(parts) > 1 and parts[1] == "document":
            return "Bluetooth Docs"
        if len(parts) > 1 and parts[1] == "guid":
            return "Bluetooth Guides"
        return "Bluetooth Explorer"
    if "privacy-policy" in relative_path.name:
        return "Privacy"
    return "Site"


def build_terms(relative_path: Path, title: str, description: str, heading: str, category: str) -> str:
    slug = relative_path.stem if relative_path.stem != "index" else relative_path.parent.name or "home"
    pieces = [
        title,
        description,
        heading,
        category,
        relative_path.as_posix(),
        slug.replace("-", " "),
    ]
    return " ".join(piece for piece in pieces if piece).lower()


def extract_body_terms(text: str, max_chars: int = 4000) -> str:
    body_match = BODY_RE.search(text)
    if not body_match:
      return ""
    body_text = clean_html_text(body_match.group(1))
    if len(body_text) > max_chars:
      body_text = body_text[:max_chars]
    return body_text.lower()


def discover_site_html_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_root.rglob("*.html"):
        relative = path.relative_to(repo_root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if relative.name in EXCLUDED_FILES:
            continue
        files.append(path)
    return sorted(files)


def build_alternates(relative_path: Path, known_paths: set[Path]) -> dict[str, str]:
    parts = list(relative_path.parts)
    alternates: dict[str, str] = {}
    for index, part in enumerate(parts):
        lang = part.lower()
        if lang not in LANGUAGE_FOLDERS:
            continue
        for target_part, locale in LANGUAGE_FOLDERS.items():
            if target_part == lang:
                continue
            candidate_parts = parts.copy()
            candidate_parts[index] = target_part
            candidate_path = Path(*candidate_parts)
            if candidate_path in known_paths:
                alternates[locale] = normalize_url(candidate_path)
        break
    return alternates


def parse_search_record(repo_root: Path, path: Path, known_paths: set[Path]) -> SearchRecord:
    relative = path.relative_to(repo_root)
    text = path.read_text(encoding="utf-8")
    title_match = TITLE_RE.search(text)
    heading_match = H1_RE.search(text)
    title = clean_html_text(title_match.group(1)) if title_match else clean_html_text(relative.stem.replace("-", " "))
    heading = clean_html_text(heading_match.group(1)) if heading_match else ""
    description = extract_meta_content(text, "description")
    locale = infer_locale(text, relative)
    category = infer_category(relative)
    alternates = build_alternates(relative, known_paths)
    body_terms = extract_body_terms(text)
    return SearchRecord(
        url=normalize_url(relative),
        title=title,
        description=description,
        heading=heading,
        category=category,
        locale=locale,
        alternates=alternates,
        terms=" ".join(
            piece
            for piece in [build_terms(relative, title, description, heading, category), body_terms]
            if piece
        ),
    )


def build_site_search_index(repo_root: Path) -> int:
    html_files = discover_site_html_files(repo_root)
    known_paths = {path.relative_to(repo_root) for path in html_files}
    records = [parse_search_record(repo_root, path, known_paths) for path in html_files]

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "items": [
            {
                "url": record.url,
                "title": record.title,
                "description": record.description,
                "heading": record.heading,
                "category": record.category,
                "locale": record.locale,
                "alternates": record.alternates,
                "terms": record.terms,
            }
            for record in records
        ],
    }

    output_path = repo_root / SEARCH_INDEX_REL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(records)


def inject_snippet(text: str, snippet: str, marker: str) -> tuple[str, bool]:
    if snippet.strip() in text:
        return text, False

    newline = "\r\n" if "\r\n" in text else "\n"
    normalized = snippet.replace("\n", newline)
    marker_index = text.lower().find(marker)
    if marker_index == -1:
        return text + normalized, True
    return text[:marker_index] + normalized + text[marker_index:], True


def inject_site_tools_into_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = text
    changed = False

    if "site-tools.css" not in updated:
        updated, did_change = inject_snippet(updated, HEAD_INJECTION, "</head>")
        changed = changed or did_change
    if "site-tools.js" not in updated:
        updated, did_change = inject_snippet(updated, SCRIPT_INJECTION, "</body>")
        changed = changed or did_change

    if changed:
        path.write_text(updated, encoding="utf-8")
    return changed


def inject_site_tools_assets(repo_root: Path) -> int:
    changed_files = 0
    for path in discover_site_html_files(repo_root):
        if inject_site_tools_into_file(path):
            changed_files += 1
    return changed_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh shared VelocAI site tools assets and search data.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--skip-inject", action="store_true", help="Skip injecting shared CSS/JS tags into HTML files.")
    parser.add_argument("--skip-index", action="store_true", help="Skip rebuilding the JSON search index.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root.resolve()

    changed_files = 0
    indexed_files = 0

    if not args.skip_inject:
        changed_files = inject_site_tools_assets(repo_root)
    if not args.skip_index:
        indexed_files = build_site_search_index(repo_root)

    print(f"site_tools inject_changed={changed_files} indexed={indexed_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
