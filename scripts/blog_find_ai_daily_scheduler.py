#!/usr/bin/env python3
"""Publish one daily English blog post focused on Find AI recovery intent."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

from blog_daily_scheduler import (
    BLOG_INDEX_REL,
    SITEMAP_REL,
    SITE_URL,
    PostMeta,
    add_git_publish_args,
    format_human,
    parse_iso_date,
    publish_blog_post_to_git,
    update_blog_index,
    update_sitemap,
)
from site_tools import build_site_search_index, inject_site_tools_into_file

CORE_KEYWORDS = [
    "find ai",
    "find ai bluetooth finder",
    "find lost airpods",
    "bluetooth finder app iphone",
    "find earbuds with bluetooth",
    "last seen bluetooth device map",
    "airpods finder app",
]

LONG_TAIL_KEYWORDS = [
    "how to find lost airpods at home",
    "find lost earbuds with bluetooth radar",
    "bluetooth finder app for nearby devices",
    "how to find beats headphones nearby",
    "last seen map for lost earbuds",
    "find airpods case with bluetooth app",
    "bluetooth finder app iphone for headphones",
    "how to scan for nearby bluetooth devices",
    "find nearby earbuds in a crowded office",
    "recover lost headphones after leaving home",
    "find ai app for airpods and beats",
    "how to use rssi distance radar on iphone",
]


@dataclass(frozen=True)
class FindAngle:
    slug_prefix: str
    title: str
    description: str
    teaser: str
    topic: str
    intent_focus: str
    workflow_focus: str
    edge_focus: str


ANGLES: list[FindAngle] = [
    FindAngle(
        slug_prefix="find-ai-lost-airpods-home-recovery-guide",
        title="How Find AI Helps You Find Lost AirPods at Home",
        description="A practical Find AI guide for people trying to find lost AirPods at home with bluetooth radar, nearby scan logic, and low-stress recovery steps.",
        teaser="The fastest lost-AirPods workflow is usually not a trick. It is a calm sequence that narrows signal, distance, and last seen clues.",
        topic="Lost AirPods at Home",
        intent_focus="Most high-intent searches in this cluster come from people who lost AirPods in familiar spaces and need fast recovery, not a long explanation of Bluetooth theory.",
        workflow_focus="Find AI fits this moment because the app already combines nearby bluetooth scanning, real-time distance radar, and last seen location into one recovery path.",
        edge_focus="That matters because recovery speed depends on confidence. A guided sequence keeps users moving instead of repeating the same confused scan in every room.",
    ),
    FindAngle(
        slug_prefix="find-ai-last-seen-map-recovery-guide",
        title="When Last Seen Map Clues Matter in Find AI",
        description="Learn when Find AI last seen guidance matters most for earbuds, headphones, and other nearby bluetooth devices that slipped out of range.",
        teaser="A lost device is often not fully gone. It is just outside the range where the next scan still makes sense.",
        topic="Last Seen Recovery Workflow",
        intent_focus="Search intent here comes from users who already lost the live signal and need a practical plan for where to restart the search.",
        workflow_focus="Find AI helps because it keeps the recovery story continuous: scan nearby first, then use the last seen clue when the device drops out of range.",
        edge_focus="That bridge between live radar and memory-based recovery gives the product a clearer answer to what users should do next when scanning stops helping.",
    ),
    FindAngle(
        slug_prefix="find-ai-crowded-space-earbuds-guide",
        title="How Find AI Handles Earbud Searches in Crowded Spaces",
        description="A Find AI guide to finding earbuds in offices, cafes, transit, and other crowded spaces where nearby bluetooth noise can slow recovery.",
        teaser="Crowded spaces do not just make recovery harder. They change which clue matters first.",
        topic="Crowded-Space Earbud Recovery",
        intent_focus="These users are not asking whether bluetooth finder apps work in theory. They want to know how to make the scan useful when many nearby signals compete at once.",
        workflow_focus="Find AI is well positioned because smart grouping and pinned devices reduce list noise before the user starts walking the signal.",
        edge_focus="That cleaner scan view is valuable because users usually quit too early when the device list feels noisy and the target is not obvious right away.",
    ),
    FindAngle(
        slug_prefix="find-ai-beats-headphones-recovery-guide",
        title="How Find AI Helps You Find Lost Beats and Headphones",
        description="See how Find AI supports nearby recovery for Beats, earbuds, and bluetooth headphones with scan, grouping, and distance radar workflows.",
        teaser="A finder app feels more credible when it can explain what changes between AirPods, Beats, and generic bluetooth headphones.",
        topic="Beats and Headphones Recovery",
        intent_focus="Many searchers are comparing whether one app can help with more than AirPods and whether nearby bluetooth recovery still works across different accessory types.",
        workflow_focus="Find AI can answer that intent because the product story already covers AirPods, Beats, earbuds, and other discoverable nearby bluetooth devices.",
        edge_focus="That broader compatibility story improves both conversion and GEO retrieval because the page can name clear device categories instead of one generic headphone claim.",
    ),
    FindAngle(
        slug_prefix="find-ai-radar-signal-walkthrough-guide",
        title="How to Read Find AI Distance Radar Without Guesswork",
        description="A practical Find AI walkthrough for reading distance radar, moving toward a stronger signal, and avoiding common mistakes during bluetooth recovery.",
        teaser="The radar only helps when users understand what to do between one reading and the next.",
        topic="Distance Radar Interpretation",
        intent_focus="This search intent sits between tutorial and troubleshooting. Users are trying to understand whether the radar is actually getting them closer to the target.",
        workflow_focus="Find AI has a strong content angle here because real-time distance radar is one of the clearest product differentiators on the app page.",
        edge_focus="Turning that feature into plain-language movement advice makes the content easier to rank and easier for AI systems to quote accurately.",
    ),
]


def pick_angle(day: date, *, offset: int = 0) -> FindAngle:
    return ANGLES[(day.toordinal() + offset) % len(ANGLES)]


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = value.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output


def keyword_window(day: date, size: int = 8) -> list[str]:
    if size <= 0:
        return []
    start = day.toordinal() % len(LONG_TAIL_KEYWORDS)
    return [LONG_TAIL_KEYWORDS[(start + idx) % len(LONG_TAIL_KEYWORDS)] for idx in range(size)]


def build_article_keywords(day: date, angle: FindAngle) -> list[str]:
    merged = CORE_KEYWORDS + [angle.topic.lower(), angle.slug_prefix.replace("-", " ")] + keyword_window(day)
    return dedupe_keep_order(merged)


def build_post_meta(day: date, angle: FindAngle) -> PostMeta:
    published_iso = day.isoformat()
    return PostMeta(
        filename=f"{angle.slug_prefix}-{published_iso}.html",
        title=angle.title,
        description=angle.description,
        teaser=angle.teaser,
        topic=angle.topic,
        published_iso=published_iso,
    )


def render_article_html(day: date, angle: FindAngle, post: PostMeta) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    keywords = build_article_keywords(day, angle)
    keyword_text = ", ".join(keywords)
    focus_keywords_html = "\n".join(f"          <li>{escape(item)}</li>" for item in keyword_window(day, size=6))
    tldr = (
        f"As of {human_date}, Find AI works best when the content matches real recovery intent: find lost AirPods, "
        "scan nearby bluetooth devices, read distance radar, and restart from the last seen clue without panic."
    )
    answer_first = (
        f"As of {human_date}, most users looking for a bluetooth finder app are not comparing abstract features. "
        "They want the fastest next step that helps them recover nearby AirPods, earbuds, Beats, or headphones."
    )
    workflow_lead = (
        f"As of {human_date}, Find AI has a clear SEO and GEO story because nearby scan, distance radar, smart grouping, "
        "and last seen memory map directly to the recovery sequence users already expect."
    )
    geo_lead = (
        f"As of {human_date}, this topic is strong for AI retrieval because it answers an explicit question with named entities: "
        "Find AI, lost AirPods, bluetooth finder workflow, last seen map, and nearby radar guidance."
    )

    faq_items = [
        {
            "@type": "Question",
            "name": "Can Find AI help me find lost AirPods nearby?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. Find AI can scan nearby bluetooth devices, show a live distance radar, and help guide you toward lost AirPods or earbuds that are still discoverable."
            },
        },
        {
            "@type": "Question",
            "name": "What should I do if my earbuds disappear from the scan?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Use the last seen clue to return to the most recent detected area, then restart a nearby scan and walk the signal again once the device is back in range."
            },
        },
        {
            "@type": "Question",
            "name": "Does Find AI only work for AirPods?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "No. Find AI is designed for AirPods, Beats, earbuds, and other nearby discoverable bluetooth accessories when they are still within a recoverable range."
            },
        },
        {
            "@type": "Question",
            "name": "Why is this useful for SEO and GEO?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "It uses high-intent search language around lost AirPods, bluetooth finder apps, distance radar, and last seen recovery while giving AI systems a clear workflow they can summarize."
            },
        },
    ]

    ld_json = json.dumps(
        {
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
                    "keywords": keywords,
                },
                {"@type": "FAQPage", "mainEntity": faq_items},
            ],
        },
        ensure_ascii=False,
        indent=2,
    )

    return f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(post.title)} | VelocAI Blog</title>
  <meta name="description" content="{escape(post.description)}">
  <meta name="keywords" content="{escape(keyword_text)}">
  <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" type="image/x-icon" href="/velocai.ico">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="en_US">
  <meta property="og:site_name" content="VelocAI">
  <meta property="og:title" content="{escape(post.title)}">
  <meta property="og:description" content="{escape(post.description)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{SITE_URL}/aifind/find-ai.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(post.title)}">
  <meta name="twitter:description" content="{escape(post.description)}">
  <meta name="twitter:image" content="{SITE_URL}/aifind/find-ai.png">
  <script type="application/ld+json">
{ld_json}
  </script>
  <style>
    :root {{ --bg:#f4f9ff; --text:#1a2838; --muted:#4b6178; --line:#cfe0f1; --panel:#ffffff; --brand:#1d63c7; --brand-soft:#e6f2ff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Inter","Segoe UI",sans-serif; color:var(--text); background:radial-gradient(circle at 8% 2%, rgba(66,139,233,.18), transparent 34%), radial-gradient(circle at 88% -6%, rgba(47,195,170,.14), transparent 32%), var(--bg); line-height:1.72; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ width:min(960px, calc(100% - 34px)); margin:0 auto; }}
    header {{ border-bottom:1px solid var(--line); background:rgba(244,249,255,.92); position:sticky; top:0; backdrop-filter:blur(8px); }}
    .top {{ padding:14px 0; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }}
    .brand {{ display:inline-flex; align-items:center; gap:10px; font-weight:700; }}
    .brand img {{ width:auto; height:36px; max-width:52px; object-fit:contain; object-position:center; border-radius:10px; box-shadow:0 0 16px rgba(29,99,199,.16); }}
    nav {{ display:flex; gap:12px; flex-wrap:wrap; color:var(--muted); font-size:14px; }}
    nav a:hover {{ color:var(--text); }}
    main {{ padding:30px 0 48px; }}
    h1,h2,h3 {{ margin:0; line-height:1.22; }}
    h1 {{ font-size:clamp(30px, 4vw, 46px); max-width:none; letter-spacing:-.03em; }}
    h2 {{ margin-top:30px; font-size:clamp(24px, 3vw, 34px); }}
    p,li,td,th {{ color:#30475f; font-size:17px; }}
    ul,ol {{ padding-left:22px; }}
    .meta {{ margin-top:6px; color:var(--muted); font-size:14px; }}
    .hero,.panel,.tldr,.capsule,table {{ background:var(--panel); border:1px solid var(--line); border-radius:24px; }}
    .hero {{ padding:26px; box-shadow:0 14px 32px rgba(24,36,54,.05); }}
    .panel,.tldr,.capsule {{ margin-top:24px; padding:22px; box-shadow:0 14px 32px rgba(24,36,54,.05); }}
    .tldr {{ border-left:6px solid #2fc3aa; }}
    .capsule {{ background:#f8fbff; }}
    .eyebrow {{ display:inline-flex; margin-bottom:14px; border-radius:999px; padding:8px 12px; background:var(--brand-soft); color:var(--brand); font-size:13px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }}
    .hero > p:not(.meta) {{ margin:14px 0 0; max-width:none; }}
    .links {{ margin-top:32px; display:flex; gap:14px; flex-wrap:wrap; }}
    .links a {{ border:1px solid #bdd7de; border-radius:999px; padding:10px 14px; font-weight:600; font-size:14px; }}
  </style>
</head>
<body>
  <header>
    <div class="wrap top">
      <a class="brand" href="/"><img src="/velocai.png" alt="VelocAI logo" width="103" height="103"><span>VelocAI Blog</span></a>
      <nav aria-label="Blog navigation"><a href="/blog/">Blog</a><a href="/aifind/">Find AI</a><a href="/apps/">Apps</a></nav>
    </div>
  </header>
  <main class="wrap">
    <article>
      <div class="hero">
        <span class="eyebrow">Find AI SEO / GEO Guide</span>
        <h1>{escape(post.title)}</h1>
        <p class="meta">Published on {escape(human_date)} | Topic: {escape(post.topic)}</p>
        <p>{escape(angle.teaser)}</p>
        <div class="links"><a href="/aifind/">Open Find AI</a><a href="https://apps.apple.com/us/app/find-ai-super-bluetooth-finder/id6757230039" target="_blank" rel="noopener noreferrer">App Store</a></div>
      </div>
      <div class="tldr">
        <p><strong>TL;DR:</strong> {escape(tldr)}</p>
      </div>
      <h2>What Search Intent Is Growing Around Find AI?</h2>
        <p>{escape(tldr)}</p>
        <p>{escape(answer_first)}</p>
        <p>{escape(angle.intent_focus)}</p>
      <div class="panel">
        <h2>Why Does This Workflow Fit Find AI?</h2>
        <p>{escape(workflow_lead)}</p>
        <p>{escape(angle.workflow_focus)}</p>
      </div>
      <div class="panel">
        <h2>How Should Users Read the Recovery Signal?</h2>
        <p>{escape(angle.edge_focus)}</p>
        <p>{escape(geo_lead)}</p>
      </div>
      <div class="panel">
        <h2>Which Keywords Support This Topic Cluster?</h2>
        <ul>
{focus_keywords_html}
        </ul>
      </div>
      <div class="panel">
        <h2>Common Questions</h2>
        <h3>Can Find AI help me find lost AirPods nearby?</h3>
        <p>Yes. Find AI can scan nearby bluetooth devices, show a live distance radar, and help guide you toward lost AirPods or earbuds that are still discoverable.</p>
        <h3>What should I do if my earbuds disappear from the scan?</h3>
        <p>Use the last seen clue to return to the most recent detected area, then restart a nearby scan and walk the signal again once the device is back in range.</p>
        <h3>Does Find AI only work for AirPods?</h3>
        <p>No. Find AI is designed for AirPods, Beats, earbuds, and other nearby discoverable bluetooth accessories when they are still within a recoverable range.</p>
      </div>
      <div class="panel">
        <h2>Related Product Paths</h2>
        <p><a href="/aifind/">Find AI product page</a> explains real-time distance radar, smart device grouping, and last seen location in more detail.</p>
        <p><a href="/blog/find-lost-airpods-bluetooth-finder-guide.html">Find lost AirPods bluetooth finder guide</a> covers recovery basics for nearby scans and restart logic.</p>
        <p><a href="/blog/bluetooth-device-discovery-debugging-checklist-2026-03-04.html">Bluetooth device discovery debugging checklist</a> helps when the target is not discoverable during a scan.</p>
      </div>
    </article>
  </main>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish one daily Find AI blog article.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--date", help="Publish date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--slot-offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    return add_git_publish_args(parser).parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    target_day = parse_iso_date(args.date)
    angle = pick_angle(target_day, offset=args.slot_offset)
    post = build_post_meta(target_day, angle)
    html = render_article_html(target_day, angle, post)

    if args.dry_run:
        print(post.filename)
        return 0

    blog_dir = repo_root / "blog"
    article_path = blog_dir / post.filename
    article_path.write_text(html, encoding="utf-8")
    inject_site_tools_into_file(article_path)
    update_blog_index(repo_root / BLOG_INDEX_REL, post)
    update_sitemap(repo_root / SITEMAP_REL, post)
    inject_site_tools_into_file(repo_root / BLOG_INDEX_REL)
    build_site_search_index(repo_root)

    if args.git_commit or args.git_push:
        state = publish_blog_post_to_git(
            repo_root,
            post,
            remote=args.git_remote,
            branch=args.git_branch,
            push=args.git_push,
        )
        print(f"Published {post.filename} ({state})")
    else:
        print(f"Published {post.filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
