#!/usr/bin/env python3
"""Lightweight SEO audit for generated blog HTML pages."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SITE_TITLE_SUFFIX = " | VelocAI Blog"
RECOMMENDED_TITLE_MIN = 40
RECOMMENDED_TITLE_MAX = 60
RECOMMENDED_DESCRIPTION_MIN = 150
RECOMMENDED_DESCRIPTION_MAX = 160
RECOMMENDED_H2_MIN = 6
RECOMMENDED_H2_MAX = 8
RECOMMENDED_QUESTION_RATIO_MIN = 0.60
RECOMMENDED_QUESTION_RATIO_MAX = 0.70
RECOMMENDED_INTERNAL_LINKS_MIN = 3
RECOMMENDED_INTERNAL_LINKS_MAX = 10
RECOMMENDED_EXTERNAL_LINKS_MIN = 3


@dataclass(frozen=True)
class SeoCheck:
    name: str
    status: str
    details: str


@dataclass(frozen=True)
class SeoAuditReport:
    checks: list[SeoCheck]

    @property
    def failed(self) -> list[SeoCheck]:
        return [item for item in self.checks if item.status == "FAIL"]

    @property
    def warned(self) -> list[SeoCheck]:
        return [item for item in self.checks if item.status == "WARN"]

    @property
    def passed(self) -> list[SeoCheck]:
        return [item for item in self.checks if item.status == "PASS"]

    def summary(self) -> str:
        return (
            f"passed={len(self.passed)} "
            f"warned={len(self.warned)} "
            f"failed={len(self.failed)}"
        )


def extract_tag(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_meta_content(text: str, *, name: str | None = None, prop: str | None = None) -> str:
    pattern = None
    if name is not None:
        pattern = rf'<meta\s+name="{re.escape(name)}"\s+content="(.*?)"\s*/?>'
    elif prop is not None:
        pattern = rf'<meta\s+property="{re.escape(prop)}"\s+content="(.*?)"\s*/?>'
    if not pattern:
        return ""
    return extract_tag(text, pattern)


def effective_title(title: str) -> str:
    if title.endswith(SITE_TITLE_SUFFIX):
        return title[: -len(SITE_TITLE_SUFFIX)].strip()
    return title.strip()


def extract_headings(html: str, level: int) -> list[str]:
    return re.findall(rf"<h{level}[^>]*>(.*?)</h{level}>", html, re.IGNORECASE | re.DOTALL)


def clean_heading_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_links(html: str) -> tuple[list[str], list[str]]:
    hrefs = re.findall(r'href="([^"]+)"', html, re.IGNORECASE)
    internal = [href for href in hrefs if href.startswith("/") and not href.startswith("//")]
    external = [href for href in hrefs if href.startswith("https://")]
    return internal, external


def add_check(checks: list[SeoCheck], name: str, status: str, details: str) -> None:
    checks.append(SeoCheck(name=name, status=status, details=details))


def validate_generated_article(html: str, *, expected_canonical: str) -> SeoAuditReport:
    checks: list[SeoCheck] = []

    raw_title = extract_tag(html, r"<title>(.*?)</title>")
    page_title = effective_title(raw_title)
    description = extract_meta_content(html, name="description")
    canonical = extract_tag(html, r'<link\s+rel="canonical"\s+href="(.*?)"\s*/?>')
    h1s = [clean_heading_text(value) for value in extract_headings(html, 1)]
    h2s = [clean_heading_text(value) for value in extract_headings(html, 2)]
    h3s = [clean_heading_text(value) for value in extract_headings(html, 3)]
    internal_links, external_links = extract_links(html)

    if page_title:
        add_check(checks, "Title present", "PASS", page_title)
    else:
        add_check(checks, "Title present", "FAIL", "Missing <title> tag")

    if page_title:
        title_len = len(page_title)
        if RECOMMENDED_TITLE_MIN <= title_len <= RECOMMENDED_TITLE_MAX:
            add_check(checks, "Title length", "PASS", f"{title_len} chars")
        else:
            add_check(
                checks,
                "Title length",
                "WARN",
                f"{title_len} chars; recommended {RECOMMENDED_TITLE_MIN}-{RECOMMENDED_TITLE_MAX}",
            )

    if description:
        add_check(checks, "Meta description present", "PASS", description)
        desc_len = len(description)
        if RECOMMENDED_DESCRIPTION_MIN <= desc_len <= RECOMMENDED_DESCRIPTION_MAX:
            add_check(checks, "Meta description length", "PASS", f"{desc_len} chars")
        else:
            add_check(
                checks,
                "Meta description length",
                "WARN",
                f"{desc_len} chars; recommended {RECOMMENDED_DESCRIPTION_MIN}-{RECOMMENDED_DESCRIPTION_MAX}",
            )
    else:
        add_check(checks, "Meta description present", "FAIL", "Missing meta description")

    if len(h1s) == 1:
        add_check(checks, "Single H1", "PASS", h1s[0])
    else:
        add_check(checks, "Single H1", "FAIL", f"Found {len(h1s)} H1 tags")

    h2_count = len(h2s)
    if RECOMMENDED_H2_MIN <= h2_count <= RECOMMENDED_H2_MAX:
        add_check(checks, "H2 count", "PASS", f"{h2_count} H2 headings")
    else:
        add_check(
            checks,
            "H2 count",
            "WARN",
            f"{h2_count} H2 headings; recommended {RECOMMENDED_H2_MIN}-{RECOMMENDED_H2_MAX}",
        )

    if h2s:
        question_ratio = sum(1 for heading in h2s if "?" in heading) / len(h2s)
        if RECOMMENDED_QUESTION_RATIO_MIN <= question_ratio <= RECOMMENDED_QUESTION_RATIO_MAX:
            add_check(checks, "Question heading ratio", "PASS", f"{question_ratio:.2%}")
        else:
            add_check(
                checks,
                "Question heading ratio",
                "WARN",
                f"{question_ratio:.2%}; recommended {RECOMMENDED_QUESTION_RATIO_MIN:.0%}-{RECOMMENDED_QUESTION_RATIO_MAX:.0%}",
            )

    long_headings = [heading for heading in [*h2s, *h3s] if len(heading) > 70]
    if long_headings:
        add_check(checks, "Heading length", "WARN", f"{len(long_headings)} headings over 70 chars")
    else:
        add_check(checks, "Heading length", "PASS", "All H2/H3 headings are under 70 chars")

    if canonical:
        if canonical == expected_canonical:
            add_check(checks, "Canonical URL", "PASS", canonical)
        else:
            add_check(
                checks,
                "Canonical URL",
                "FAIL",
                f"Expected {expected_canonical} but found {canonical}",
            )
    else:
        add_check(checks, "Canonical URL", "FAIL", "Missing canonical link")

    required_og = {
        "og:title": extract_meta_content(html, prop="og:title"),
        "og:description": extract_meta_content(html, prop="og:description"),
        "og:image": extract_meta_content(html, prop="og:image"),
        "og:url": extract_meta_content(html, prop="og:url"),
        "og:site_name": extract_meta_content(html, prop="og:site_name"),
    }
    missing_og = [key for key, value in required_og.items() if not value]
    og_type = extract_meta_content(html, prop="og:type")
    if missing_og:
        add_check(checks, "OG tags", "FAIL", "Missing " + ", ".join(missing_og))
    elif og_type != "article":
        add_check(checks, "OG tags", "FAIL", f'Expected og:type "article" but found "{og_type or "missing"}"')
    else:
        add_check(checks, "OG tags", "PASS", "Required OG tags present")

    required_twitter = {
        "twitter:card": extract_meta_content(html, name="twitter:card"),
        "twitter:title": extract_meta_content(html, name="twitter:title"),
        "twitter:description": extract_meta_content(html, name="twitter:description"),
        "twitter:image": extract_meta_content(html, name="twitter:image"),
    }
    missing_twitter = [key for key, value in required_twitter.items() if not value]
    if missing_twitter:
        add_check(checks, "Twitter card tags", "FAIL", "Missing " + ", ".join(missing_twitter))
    elif required_twitter["twitter:card"] != "summary_large_image":
        add_check(
            checks,
            "Twitter card tags",
            "FAIL",
            f'Expected twitter:card "summary_large_image" but found "{required_twitter["twitter:card"]}"',
        )
    else:
        add_check(checks, "Twitter card tags", "PASS", "Required Twitter tags present")

    internal_count = len(internal_links)
    if RECOMMENDED_INTERNAL_LINKS_MIN <= internal_count <= RECOMMENDED_INTERNAL_LINKS_MAX:
        add_check(checks, "Internal links", "PASS", f"{internal_count} internal links")
    else:
        add_check(
            checks,
            "Internal links",
            "WARN",
            f"{internal_count} internal links; recommended {RECOMMENDED_INTERNAL_LINKS_MIN}-{RECOMMENDED_INTERNAL_LINKS_MAX}",
        )

    external_count = len(external_links)
    if external_count >= RECOMMENDED_EXTERNAL_LINKS_MIN:
        add_check(checks, "External links", "PASS", f"{external_count} external links")
    else:
        add_check(
            checks,
            "External links",
            "WARN",
            f"{external_count} external links; recommended at least {RECOMMENDED_EXTERNAL_LINKS_MIN}",
        )

    if re.search(r'"@type"\s*:\s*"FAQPage"', html):
        add_check(checks, "FAQ schema", "PASS", "FAQPage schema present")
    else:
        add_check(checks, "FAQ schema", "WARN", "FAQPage schema not found")

    return SeoAuditReport(checks=checks)


def print_report(report: SeoAuditReport) -> None:
    print("SEO audit:", report.summary())
    for item in report.checks:
        print(f"- {item.status}: {item.name} - {item.details}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a generated blog article for SEO basics.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected-canonical", required=True)
    args = parser.parse_args()

    html = args.path.read_text(encoding="utf-8")
    report = validate_generated_article(html, expected_canonical=args.expected_canonical)
    print_report(report)
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
