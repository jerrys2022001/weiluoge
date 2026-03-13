#!/usr/bin/env python3
"""Generate blog fallback candidates from live news feeds."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from html import escape

from blog_daily_scheduler import PostMeta, SITE_URL, format_human
from home_brief_daily_scheduler import (
    BRIEF_SOURCES,
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


def slugify(value: str, limit: int = 72) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:limit].strip("-") or "update"


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


def title_for_item(source_slug: str, item: FeedItem) -> str:
    if source_slug == "apple":
        return f"{item.title}: Apple Feature and Performance Commentary"
    if source_slug == "ai":
        return f"{item.title}: AI Technology Outlook"
    return f"{item.title}: Bluetooth Standards and Application Commentary"


def teaser_for_source_slug(source_slug: str) -> str:
    if source_slug == "apple":
        return "A search-focused Apple commentary on product features, performance, and why the update matters."
    if source_slug == "ai":
        return "A forward-looking AI commentary that turns a fresh update into practical product and strategy context."
    return "A latest-info Bluetooth commentary focused on standards, features, and real-world applications."


def looks_garbled(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in ("鈥", "鈦", "�", "\ufffd"))


def clean_summary(source_slug: str, source_name: str, item: FeedItem) -> str:
    cleaned = clean_text(item.summary)
    if cleaned and not looks_garbled(cleaned):
        return clip_text(cleaned, limit=210)
    fallback = {
        "apple": f"Latest Apple product commentary from {source_name} focused on feature changes, performance impact, and what the update means for buyers and developers.",
        "ai": f"Latest AI technology commentary from {source_name} focused on capability changes, product impact, and what teams should watch next.",
        "bluetooth": f"Latest Bluetooth commentary from {source_name} focused on standards changes, application impact, and what product teams should watch next.",
    }[source_slug]
    return fallback


def keywords_for_source_slug(source_slug: str) -> list[str]:
    if source_slug == "apple":
        return [
            "apple new product review",
            "apple feature commentary",
            "apple performance commentary",
            "iphone feature analysis",
            "mac performance review",
        ]
    if source_slug == "ai":
        return [
            "ai technology outlook",
            "latest ai developments",
            "ai product analysis",
            "ai model commentary",
            "future of ai applications",
        ]
    return [
        "bluetooth latest update",
        "bluetooth standards commentary",
        "bluetooth application analysis",
        "latest bluetooth features",
        "bluetooth industry outlook",
    ]


def render_live_article(day: date, source_slug: str, source_name: str, item: FeedItem, post: PostMeta) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    source_published = item.published_at.astimezone().strftime("%B %d, %Y") if item.published_at else human_date
    source_summary = escape(clean_summary(source_slug, source_name, item))
    keywords = ", ".join(keywords_for_source_slug(source_slug) + [post.topic.lower(), slugify(item.title).replace("-", " ")])
    what_changed_heading = "What Happened"
    why_it_matters_heading = "Why It Matters"
    outlook_heading = "What To Watch Next"
    impact_text = {
        "apple": "This update matters because Apple feature changes and performance shifts quickly affect buyer expectations, upgrade timing, and the way app experiences are perceived across iPhone, iPad, Mac, and accessory ecosystems.",
        "ai": "This update matters because AI releases can quickly change product roadmaps, model capability expectations, enterprise adoption plans, and the pace at which practical AI workflows become mainstream.",
        "bluetooth": "This update matters because Bluetooth changes influence interoperability, product planning, standards adoption, and the real-world reliability of devices across audio, wearables, discovery, and industrial workflows.",
    }[source_slug]
    outlook_text = {
        "apple": "Watch for how Apple positions this change across product tiers, whether independent testing confirms the performance story, and how developers or accessory vendors adjust around the new feature set.",
        "ai": "Watch for follow-up launches, benchmark validation, pricing or deployment changes, and whether the update shifts how teams choose between foundation models, agents, and productized AI workflows.",
        "bluetooth": "Watch for standards follow-through, vendor adoption, ecosystem support, and whether this update creates practical gains in discovery, power, compatibility, or device-level application design.",
    }[source_slug]
    faq_question = {
        "apple": "How should readers evaluate a new Apple feature or performance claim?",
        "ai": "How should readers evaluate a new AI release or capability claim?",
        "bluetooth": "How should readers evaluate a new Bluetooth update or standards claim?",
    }[source_slug]
    faq_answer = {
        "apple": "Check the official announcement, compare the change against prior Apple products, then look for real workflow impact such as speed, battery life, camera output, or software integration.",
        "ai": "Check the primary source, compare it to previous model or platform capabilities, and focus on measurable workflow impact instead of headline-level claims alone.",
        "bluetooth": "Check the primary standards or vendor source, compare it against current deployment constraints, and focus on whether it changes interoperability, power, latency, or application design.",
    }[source_slug]
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
      "mainEntityOfPage": {json_string(canonical)}
    }},
    {{
      "@type": "FAQPage",
      "mainEntity": [
        {{
          "@type": "Question",
          "name": {json_string(faq_question)},
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": {json_string(faq_answer)}
          }}
        }}
      ]
    }}
  ]
}}
  </script>
  <style>
    :root {{ --bg:#f5f9fd; --text:#182436; --muted:#5b6c80; --line:#d6e1ec; --panel:#ffffff; --brand:#1759b8; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Segoe UI",sans-serif; color:var(--text); background:var(--bg); line-height:1.72; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ width:min(920px, calc(100% - 34px)); margin:0 auto; }}
    header {{ border-bottom:1px solid var(--line); background:rgba(245,249,253,.92); }}
    .top {{ padding:14px 0; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }}
    nav {{ display:flex; gap:12px; flex-wrap:wrap; color:var(--muted); font-size:14px; }}
    main {{ padding:36px 0 56px; }}
    h1,h2 {{ margin:0; line-height:1.22; }}
    h1 {{ font-size:clamp(30px, 4.2vw, 48px); max-width:24ch; }}
    h2 {{ margin-top:30px; font-size:clamp(24px, 3vw, 34px); }}
    p,li {{ color:#30475f; font-size:17px; }}
    .meta {{ margin-top:10px; color:var(--muted); font-size:14px; }}
    .hero, .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:24px; padding:26px; box-shadow:0 14px 32px rgba(24,36,54,.05); }}
    .panel {{ margin-top:24px; }}
    .links {{ margin-top:32px; display:flex; gap:14px; flex-wrap:wrap; color:var(--brand); font-weight:600; }}
  </style>
</head>
<body>
  <header>
    <div class="wrap top">
      <a class="brand" href="/">
        <img src="/2.png" alt="VelocAI logo" width="102" height="73">
        <span>VelocAI</span>
      </a>
      <nav>
        <a href="/apps/">Apps Hub</a>
        <a href="/blog/">Blog</a>
        <a href="/bluetoothexplorer/">Bluetooth Explorer</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <article class="hero">
      <h1>{escape(post.title)}</h1>
      <p class="meta">Published on {escape(human_date)} · Topic: {escape(post.topic)} · Source: {escape(source_name)}</p>
      <p>{escape(post.description)}</p>
    </article>

    <section class="panel">
      <h2>{what_changed_heading}</h2>
      <p>{source_summary}</p>
      <p>This commentary is based on the latest source item published on {escape(source_published)}.</p>
    </section>

    <section class="panel">
      <h2>{why_it_matters_heading}</h2>
      <p>{escape(impact_text)}</p>
    </section>

    <section class="panel">
      <h2>{outlook_heading}</h2>
      <p>{escape(outlook_text)}</p>
    </section>

    <section class="panel">
      <h2>Source Attribution</h2>
      <p><a href="{escape(item.link)}" target="_blank" rel="noopener noreferrer">{escape(source_name)}: {escape(item.title)}</a></p>
    </section>

    <div class="links">
      <a href="/blog/">Back to blog index</a>
      <a href="/apps/">Browse apps</a>
    </div>
  </main>
</body>
</html>
"""


def json_string(value: str) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def unique_feed_items_for_lane(lane: str) -> list[tuple[str, str, FeedItem]]:
    preferred_slugs = {
        "cleanup": ("apple", "ai"),
        "protocol": ("bluetooth", "ai", "apple"),
    }[lane]
    allowed_sources = {
        "cleanup": {"Apple Newsroom", "MacRumors", "OpenAI News", "Tom's Hardware"},
        "protocol": {"Bluetooth SIG", "OpenAI News", "Apple Newsroom", "MacRumors"},
    }[lane]
    required_title_keywords = {
        "apple": ("apple", "iphone", "ipad", "mac", "macbook", "airpods", "watch", "vision", "ios"),
        "ai": ("ai", "openai", "gpt", "model", "agent", "reasoning", "anthropic", "gemini", "llm"),
        "bluetooth": ("bluetooth", "le audio", "auracast", "mesh", "gatt", "pairing", "discovery", "wireless"),
    }
    collected: list[tuple[str, str, FeedItem]] = []
    seen_links: set[str] = set()
    for slug in preferred_slugs:
        sources = [source for source in BRIEF_SOURCES if source.slug == slug and source.source_name in allowed_sources]
        for source in sources:
            try:
                items = parse_feed_items(fetch_bytes(source.feed_url))
            except Exception:
                continue
            for item in items:
                lowered_title = item.title.lower()
                if not any(keyword in lowered_title for keyword in required_title_keywords[slug]):
                    continue
                padded_title = f" {lowered_title} "
                if any(pattern in padded_title for pattern in NOISE_PATTERNS):
                    continue
                if score_item(item, source.keywords) <= 0:
                    continue
                if not item.link or item.link in seen_links:
                    continue
                seen_links.add(item.link)
                collected.append((slug, source.source_name, item))
    collected.sort(key=lambda item: item[2].published_at.timestamp() if item[2].published_at else 0.0, reverse=True)
    return collected


def build_live_candidates(target_day: date, lane: str) -> list[LiveBlogCandidate]:
    candidates: list[LiveBlogCandidate] = []
    for source_slug, source_name, item in unique_feed_items_for_lane(lane):
        prefix = article_prefix_for_source_slug(source_slug)
        item_slug = slugify(item.title)
        filename = f"{prefix}-{item_slug}-{target_day.isoformat()}.html"
        title = title_for_item(source_slug, item)
        description = clean_summary(source_slug, source_name, item)
        post = PostMeta(
            filename=filename,
            title=title,
            description=description,
            teaser=teaser_for_source_slug(source_slug),
            topic=topic_for_source_slug(source_slug),
            published_iso=target_day.isoformat(),
        )
        html = render_live_article(target_day, source_slug, source_name, item, post)
        candidates.append(LiveBlogCandidate(post=post, html=html, link=item.link, source_name=source_name))
    return candidates
