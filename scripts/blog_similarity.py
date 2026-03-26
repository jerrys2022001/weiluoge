#!/usr/bin/env python3
"""Shared blog similarity helpers."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

STOP_WORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "without",
    "how", "what", "why", "when", "where", "is", "are", "was", "were", "be", "been",
    "being", "this", "that", "these", "those", "your", "you", "it", "its", "as", "by",
    "from", "at", "into", "than", "then", "they", "them", "their", "can", "may", "will",
    "should", "after", "before", "first", "second", "third", "guide", "explained", "use",
    "using", "latest", "blog", "velocai", "current", "key", "practical", "reliable",
    "update", "2026",
}
SKIP_HEADERS = (
    "high-intent keyword coverage",
    "geo answer blocks for ai retrieval",
    "faq",
    "source attribution",
    "daily 20:00 execution checklist",
    "current status:",
    "practical decision checklist",
    "seo and geo retrieval fit",
    "what to watch next",
    "search intent and upgrade questions",
    "search intent and adoption questions",
    "search intent and deployment questions",
)
RESUME_MARKERS = (
    "back to blog index",
    "browse velocai apps",
    "open bluetooth explorer",
)


@dataclass(frozen=True)
class BlogPage:
    path: Path
    title: str
    description: str
    published_iso: str | None
    slug_base: str
    title_tokens: frozenset[str]
    body_counter: Counter[str]

    @property
    def relative_url(self) -> str:
        return f"/blog/{self.path.name}"

    @property
    def absolute_url(self) -> str:
        return f"https://velocai.net{self.relative_url}"


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


def title_tokens_for(title: str) -> frozenset[str]:
    return frozenset(
        token
        for token in re.findall(r"[a-z0-9]+", title.lower())
        if token not in STOP_WORDS
    )


def extract_body_counter(html: str) -> Counter[str]:
    if "Translate AI SEO / GEO Guide" in html:
        focus_parts: list[str] = []
        for pattern in (
            r"<h1>(.*?)</h1>",
            r'<section class="tldr">.*?<p>(.*?)</p>',
            r'<section class="panel">\s*<h2>Why.*?</h2>\s*<p>(.*?)</p>\s*<p>(.*?)</p>',
            r'<section class="panel">\s*<h2>How.*?</h2>\s*<p>(.*?)</p>\s*<p>(.*?)</p>',
        ):
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            focus_parts.extend(group for group in match.groups() if group)

        table_match = re.search(
            r"<tbody>\s*<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if table_match:
            focus_parts.extend(table_match.groups())

        faq_match = re.search(r'<section class="panel">\s*<h2>What Questions.*?</h2>(.*?)</section>', html, re.IGNORECASE | re.DOTALL)
        if faq_match:
            focus_parts.append(faq_match.group(1))

        focus_text = re.sub(r"<[^>]+>", " ", " ".join(focus_parts))
        focus_text = re.sub(r"\s+", " ", focus_text).lower()
        return Counter(
            token
            for token in re.findall(r"[a-z0-9]{3,}", focus_text)
            if token not in STOP_WORDS
        )

    if "<h2>What Happened</h2>" in html:
        focus_parts: list[str] = []
        title_match = re.search(r"<h1>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            focus_parts.append(title_match.group(1))
        hero_match = re.search(r'<div class="hero">.*?<p class="meta">.*?</p>\s*<p>(.*?)</p>', html, re.IGNORECASE | re.DOTALL)
        if hero_match:
            focus_parts.append(hero_match.group(1))
        happened_match = re.search(r'<h2>What Happened</h2>\s*<p>(.*?)</p>', html, re.IGNORECASE | re.DOTALL)
        if happened_match:
            focus_parts.append(happened_match.group(1))
        focus_html = " ".join(focus_parts)
        focus_text = re.sub(r"<[^>]+>", " ", focus_html)
        focus_text = re.sub(r"\s+", " ", focus_text).lower()
        return Counter(
            token
            for token in re.findall(r"[a-z0-9]{3,}", focus_text)
            if token not in STOP_WORDS
        )

    trimmed = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    trimmed = re.sub(r'<section class="sources".*?</section>', " ", trimmed, flags=re.IGNORECASE | re.DOTALL)
    trimmed = re.sub(
        r'<section class="panel">\s*<h2>(?:Why It Matters|What To Watch Next|Source Attribution)</h2>.*?</section>',
        " ",
        trimmed,
        flags=re.IGNORECASE | re.DOTALL,
    )
    trimmed = re.sub(r'<p class="meta">.*?</p>', " ", trimmed, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", "\n", trimmed)
    lines = [re.sub(r"\s+", " ", item).strip() for item in text.splitlines()]

    kept: list[str] = []
    skip_block = False
    for line in lines:
        lowered = line.lower()
        if any(header in lowered for header in SKIP_HEADERS):
            skip_block = True
            continue
        if skip_block and any(lowered.startswith(marker) for marker in RESUME_MARKERS):
            skip_block = False
            continue
        if not skip_block and line:
            kept.append(line)

    body = " ".join(kept).lower()
    return Counter(
        token
        for token in re.findall(r"[a-z0-9]{3,}", body)
        if token not in STOP_WORDS
    )


def is_merge_redirect(html: str, title: str) -> bool:
    robots = extract_tag(html, r'<meta\s+name="robots"\s+content="(.*?)"\s*/?>').lower()
    return title.lower().startswith("merged:") or "noindex" in robots


def load_blog_pages(blog_dir: Path) -> list[BlogPage]:
    pages: list[BlogPage] = []
    for path in sorted(blog_dir.glob("*.html")):
        if path.name == "index.html":
            continue
        html = path.read_text(encoding="utf-8")
        title = extract_tag(html, r"<title>(.*?)\s*\|")
        if is_merge_redirect(html, title):
            continue
        description = extract_tag(html, r'<meta\s+name="description"\s+content="(.*?)"\s*/?>')
        pages.append(
            BlogPage(
                path=path,
                title=title or path.stem,
                description=description,
                published_iso=parse_published_iso(path, html),
                slug_base=slug_base_for(path),
                title_tokens=title_tokens_for(title or path.stem),
                body_counter=extract_body_counter(html),
            )
        )
    return pages


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    shared = set(left) & set(right)
    dot = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def title_overlap(left: frozenset[str], right: frozenset[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def max_similarity_against_existing(html: str, existing_pages: list[BlogPage]) -> float:
    body_counter = extract_body_counter(html)
    if not body_counter:
        return 0.0
    return max((cosine_similarity(body_counter, page.body_counter) for page in existing_pages), default=0.0)
