#!/usr/bin/env python3
"""Consolidate similar blog posts into canonical pages."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from blog_similarity import (
    BlogPage,
    cosine_similarity,
    extract_tag,
    load_blog_pages,
    normalize_title,
    title_overlap,
)
from site_tools import build_site_search_index

SITE_URL = "https://velocai.net"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge blog posts whose content similarity exceeds the configured threshold."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--dry-run", action="store_true", help="Report planned merges without writing files.")
    parser.add_argument("--similarity-threshold", type=float, default=0.30)
    parser.add_argument("--title-overlap-threshold", type=float, default=0.40)
    return parser.parse_args()


def page_sort_key(page: BlogPage) -> tuple[str, str]:
    return (page.published_iso or "", page.path.name)


def build_components(
    pages: list[BlogPage],
    similarity_threshold: float,
    title_overlap_threshold: float,
) -> list[list[BlogPage]]:
    page_by_name = {page.path.name: page for page in pages}
    graph: dict[str, set[str]] = defaultdict(set)

    for index, left in enumerate(pages):
        for right in pages[index + 1 :]:
            same_slug = left.slug_base == right.slug_base
            same_title = normalize_title(left.title) == normalize_title(right.title)
            overlap = title_overlap(left.title_tokens, right.title_tokens)
            similarity = cosine_similarity(left.body_counter, right.body_counter)
            if same_slug and same_title:
                graph[left.path.name].add(right.path.name)
                graph[right.path.name].add(left.path.name)
                continue
            if similarity >= similarity_threshold and overlap >= title_overlap_threshold:
                graph[left.path.name].add(right.path.name)
                graph[right.path.name].add(left.path.name)

    components: list[list[BlogPage]] = []
    seen: set[str] = set()
    for page in pages:
        if page.path.name in seen or page.path.name not in graph:
            continue
        stack = [page.path.name]
        seen.add(page.path.name)
        component: list[BlogPage] = []
        while stack:
            current = stack.pop()
            component.append(page_by_name[current])
            for neighbor in graph[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        if len(component) > 1:
            components.append(sorted(component, key=page_sort_key))

    components.sort(key=lambda group: tuple(item.path.name for item in group))
    return components


def choose_canonical(group: list[BlogPage]) -> BlogPage:
    scores: dict[str, tuple[int, float, str, str]] = {}
    for candidate in group:
        title_matches = 0
        similarity_sum = 0.0
        for other in group:
            if other.path == candidate.path:
                continue
            if title_overlap(candidate.title_tokens, other.title_tokens) >= 0.40:
                title_matches += 1
            similarity_sum += cosine_similarity(candidate.body_counter, other.body_counter)
        scores[candidate.path.name] = (
            title_matches,
            similarity_sum,
            candidate.published_iso or "",
            candidate.path.name,
        )
    best_name = max(scores, key=scores.get)
    return next(page for page in group if page.path.name == best_name)


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
      <p>This older page has been consolidated into the canonical article for this topic cluster.</p>
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
        r'(<section\b(?=[^>]*class="list")(?=[^>]*aria-label="Latest blog posts")[^>]*>\s*)(.*?)(\s*</section>)',
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


def merge_duplicates(
    repo_root: Path,
    dry_run: bool,
    similarity_threshold: float,
    title_overlap_threshold: float,
) -> int:
    blog_dir = repo_root / "blog"
    index_path = blog_dir / "index.html"
    sitemap_path = repo_root / "sitemap.xml"
    pages = load_blog_pages(blog_dir)
    groups = build_components(pages, similarity_threshold, title_overlap_threshold)

    if not groups:
        print("No similar blog groups found.")
        return 0

    merged_names: set[str] = set()
    for group in groups:
        canonical = choose_canonical(group)
        older = [page for page in group if page.path != canonical.path]
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
    build_site_search_index(repo_root)
    return 0


def main() -> int:
    args = parse_args()
    return merge_duplicates(
        args.repo_root.resolve(),
        args.dry_run,
        args.similarity_threshold,
        args.title_overlap_threshold,
    )


if __name__ == "__main__":
    raise SystemExit(main())
