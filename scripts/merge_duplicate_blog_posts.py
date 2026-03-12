#!/usr/bin/env python3
"""Consolidate duplicate blog posts into canonical pages."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

SITE_URL = "https://velocai.net"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@dataclass(frozen=True)
class BlogPage:
    path: Path
    title: str
    description: str
    published_iso: str | None
    slug_base: str

    @property
    def relative_url(self) -> str:
        return f"/blog/{self.path.name}"

    @property
    def absolute_url(self) -> str:
        return f"{SITE_URL}{self.relative_url}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge duplicate blog posts with identical title/slug into canonical pages."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--dry-run", action="store_true", help="Report planned merges without writing files.")
    return parser.parse_args()


def extract_tag(html: str, pattern: str) -> str:
    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_published_iso(path: Path, html: str) -> str | None:
    stem_match = re.search(r"(\d{4}-\d{2}-\d{2})\.html$", path.name)
    if stem_match:
        return stem_match.group(1)
    ld_match = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', html)
    return ld_match.group(1) if ld_match else None


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def slug_base_for(path: Path) -> str:
    return re.sub(r"-\d{4}-\d{2}-\d{2}$", "", path.stem)


def load_blog_pages(blog_dir: Path) -> list[BlogPage]:
    pages: list[BlogPage] = []
    for path in sorted(blog_dir.glob("*.html")):
        if path.name == "index.html":
            continue
        html = path.read_text(encoding="utf-8")
        title = extract_tag(html, r"<title>(.*?)\s*\|")
        description = extract_tag(html, r'<meta\s+name="description"\s+content="(.*?)"\s*/?>')
        pages.append(
            BlogPage(
                path=path,
                title=title or path.stem,
                description=description,
                published_iso=parse_published_iso(path, html),
                slug_base=slug_base_for(path),
            )
        )
    return pages


def build_duplicate_groups(pages: list[BlogPage]) -> list[list[BlogPage]]:
    groups: dict[str, list[BlogPage]] = {}
    for page in pages:
        key = f"{page.slug_base}::{normalize_title(page.title)}"
        groups.setdefault(key, []).append(page)
    duplicates = [group for group in groups.values() if len(group) > 1]
    duplicates.sort(key=lambda group: tuple(item.path.name for item in group))
    return duplicates


def sort_group(group: Iterable[BlogPage]) -> list[BlogPage]:
    return sorted(
        group,
        key=lambda page: (
            page.published_iso or "",
            page.path.name,
        ),
    )


def build_merge_page(source: BlogPage, canonical: BlogPage) -> str:
    title_text = f"Merged: {source.title}"
    description = source.description or f"This article has been consolidated into {canonical.title}."
    canonical_url = canonical.absolute_url
    body_title = escape(source.title)
    canonical_title = escape(canonical.title)
    source_date = escape(source.published_iso or "earlier edition")
    canonical_date = escape(canonical.published_iso or "latest edition")
    return f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title_text)} | VelocAI Blog</title>
  <meta name="description" content="{escape(description)}">
  <meta name="robots" content="noindex,follow">
  <link rel="canonical" href="{escape(canonical_url)}">
  <meta http-equiv="refresh" content="0; url={escape(canonical_url)}">
  <link rel="icon" type="image/x-icon" href="/velocai.ico">
  <style>
    :root {{ --bg:#f5f9fd; --text:#182436; --muted:#5b6c80; --line:#d6e1ec; --panel:#ffffff; --brand:#1759b8; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Segoe UI",sans-serif; color:var(--text); background:var(--bg); line-height:1.7; }}
    main {{ width:min(760px, calc(100% - 32px)); margin:48px auto; }}
    .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:20px; padding:28px; box-shadow:0 12px 32px rgba(24,36,54,.06); }}
    h1 {{ margin:0 0 12px; font-size:clamp(28px, 4vw, 40px); line-height:1.2; }}
    p {{ margin:12px 0; color:var(--muted); font-size:17px; }}
    a {{ color:var(--brand); }}
  </style>
</head>
<body>
  <main>
    <section class="panel">
      <h1>{body_title}</h1>
      <p>This older page has been consolidated into the latest canonical article.</p>
      <p>Original edition: {source_date}<br>Canonical edition: {canonical_date}</p>
      <p><a href="{escape(canonical.relative_url)}">Open the merged article: {canonical_title}</a></p>
    </section>
  </main>
</body>
</html>
"""


def update_index(index_path: Path, merged_names: set[str]) -> bool:
    original = index_path.read_text(encoding="utf-8")
    updated = original

    script_match = re.search(
        r'(<script type="application/ld\+json">\s*)(\{.*?\})(\s*</script>)',
        updated,
        re.DOTALL,
    )
    if not script_match:
        raise ValueError("Cannot find JSON-LD block in blog/index.html")

    payload = json.loads(script_match.group(2))
    graph = payload.get("@graph", [])
    for item in graph:
        if item.get("@type") == "ItemList":
            items = item.get("itemListElement", [])
            items = [
                entry
                for entry in items
                if Path(str(entry.get("url", ""))).name not in merged_names
            ]
            for idx, entry in enumerate(items, start=1):
                entry["position"] = idx
            item["itemListElement"] = items

    replacement = script_match.group(1) + json.dumps(payload, indent=2) + script_match.group(3)
    updated = updated[: script_match.start()] + replacement + updated[script_match.end() :]

    section_match = re.search(
        r'(<section class="list" aria-label="Latest blog posts">\s*)(.*?)(\s*</section>)',
        updated,
        re.DOTALL,
    )
    if not section_match:
        raise ValueError("Cannot find article list section in blog/index.html")

    article_blocks = re.findall(r"\s*<article>.*?</article>", section_match.group(2), re.DOTALL)
    kept_blocks = [
        block
        for block in article_blocks
        if not any(f'/blog/{name}"' in block for name in merged_names)
    ]
    new_section = section_match.group(1) + "".join(kept_blocks) + section_match.group(3)
    updated = updated[: section_match.start()] + new_section + updated[section_match.end() :]

    if updated == original:
        return False
    index_path.write_text(updated, encoding="utf-8")
    return True


def update_sitemap(sitemap_path: Path, merged_names: set[str]) -> bool:
    ET.register_namespace("", NS["sm"])
    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    changed = False
    for node in list(root.findall("sm:url", NS)):
        loc = node.find("sm:loc", NS)
        if loc is None or not loc.text:
            continue
        if Path(loc.text).name in merged_names:
            root.remove(node)
            changed = True
    if not changed:
        return False
    ET.indent(tree, space="  ")
    tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)
    return True


def merge_duplicates(repo_root: Path, dry_run: bool) -> int:
    blog_dir = repo_root / "blog"
    index_path = blog_dir / "index.html"
    sitemap_path = repo_root / "sitemap.xml"
    pages = load_blog_pages(blog_dir)
    groups = build_duplicate_groups(pages)

    if not groups:
        print("No duplicate blog groups found.")
        return 0

    merged_names: set[str] = set()
    for group in groups:
        ordered = sort_group(group)
        canonical = ordered[-1]
        older = ordered[:-1]
        print(f"canonical={canonical.path.name}")
        for source in older:
            print(f"  merge={source.path.name}")
            merged_names.add(source.path.name)
            if not dry_run:
                source.path.write_text(build_merge_page(source, canonical), encoding="utf-8")

    if dry_run:
        print(f"would_remove_from_index_and_sitemap={sorted(merged_names)}")
        return 0

    update_index(index_path, merged_names)
    update_sitemap(sitemap_path, merged_names)
    return 0


def main() -> int:
    args = parse_args()
    return merge_duplicates(args.repo_root.resolve(), args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
