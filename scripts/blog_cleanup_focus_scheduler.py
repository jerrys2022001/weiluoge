#!/usr/bin/env python3
"""Publish one daily English blog post about storage cleanup priorities."""

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
    "cleanup duplicate photos",
    "find large videos for cleanup",
    "cleanup screenshots on iphone",
    "cleanup whatsapp storage on iphone",
    "cleanup iphone storage full",
    "cleanup system storage on iphone",
    "iphone storage cleanup",
    "ios phone cleanup",
    "find cleanup wins on iphone",
]

LONG_TAIL_KEYWORDS = [
    "how to cleanup duplicate photos on iphone",
    "best cleanup way to remove duplicate photos safely",
    "find large videos taking up space on iphone",
    "how to find videos by size on ios for cleanup",
    "cleanup screenshots in bulk on iphone",
    "cleanup old screenshots without losing important images",
    "how to cleanup whatsapp storage on iphone",
    "cleanup iphone storage full after whatsapp media growth",
    "how to cleanup whatsapp photos and videos safely",
    "cleanup whatsapp storage without deleting chats",
    "cleanup system storage on iphone",
    "cleanup iphone system data too large fix",
    "daily phone cleanup checklist 20 minutes",
    "ios cleanup routine for low storage",
    "cleanup iphone storage without deleting everything",
    "best weekly iphone storage cleanup workflow",
    "whatsapp storage full cleanup guide",
    "how to find duplicate photos and large videos fast",
]


@dataclass(frozen=True)
class CleanupAngle:
    slug_prefix: str
    title: str
    description: str
    teaser: str
    topic: str
    first_focus: str
    second_focus: str
    challenge_focus: str


ANGLES: list[CleanupAngle] = [
    CleanupAngle(
        slug_prefix="delete-duplicate-photos-daily-cleanup-guide",
        title="AI Cleanup PRO: Duplicate Photos First for Faster iPhone Storage Recovery",
        description="A practical English guide to deleting duplicate photos first so you can reclaim space safely and make daily iPhone cleanup faster.",
        teaser="A safe daily cleanup routine that starts with duplicate photos and builds toward better storage hygiene.",
        topic="Delete Duplicate Photos",
        first_focus="Duplicate and near-duplicate photos are usually the safest high-impact place to start. They free space without forcing users to review system files or delete important apps, and they create fast visible progress in daily cleanup.",
        second_focus="After duplicate photos, move to large videos, screenshots, WhatsApp media, and finally system storage checks. That order keeps the easiest wins first and helps users avoid risky deletion decisions when they are rushing.",
        challenge_focus="The main challenge is consistency. People often delete random files under pressure, then stop before they reach the categories that actually keep storage stable over time.",
    ),
    CleanupAngle(
        slug_prefix="find-large-videos-storage-cleanup-playbook",
        title="AI Cleanup PRO: Find Large Videos and Reclaim Space Fast",
        description="Learn how to find large videos quickly and reclaim phone storage with a simple daily cleanup workflow built for SEO and GEO visibility.",
        teaser="A focused cleanup playbook for finding large videos first and recovering meaningful storage fast.",
        topic="Find Large Videos",
        first_focus="When users need space now, large videos often beat every other category for speed and impact. Sorting by size and reviewing only the heaviest files can free meaningful capacity in minutes.",
        second_focus="Once large videos are under control, keep momentum by deleting duplicate photos, removing screenshots, cleaning WhatsApp media, and checking system storage growth. This turns emergency cleanup into a repeatable daily habit.",
        challenge_focus="The hard part is decision fatigue. Large videos are valuable memory files, so users need a shortlist method that helps them review only the biggest, lowest-value clips first.",
    ),
    CleanupAngle(
        slug_prefix="remove-screenshots-iphone-cleanup-checklist",
        title="AI Cleanup PRO: Cleanup Screenshots in Bulk for Better Storage Hygiene",
        description="A practical guide to removing screenshots in bulk so you can keep your photo library cleaner and reclaim space without deleting valuable memories.",
        teaser="A repeatable screenshot cleanup routine that helps keep the camera roll useful and the storage graph under control.",
        topic="Remove Screenshots",
        first_focus="Screenshots accumulate silently and often deliver less long-term value than photos or videos. Clearing them in batches reduces clutter, speeds later photo reviews, and creates safer cleanup momentum.",
        second_focus="Start with duplicate photos, then large videos, then screenshots. After that, clean WhatsApp media and review system storage so you handle both visible clutter and hidden growth.",
        challenge_focus="The challenge is that screenshots feel small one by one, so people underestimate their total effect. Bulk cleanup solves that by treating them as a dedicated recurring category.",
    ),
    CleanupAngle(
        slug_prefix="clean-whatsapp-media-storage-guide",
        title="AI Cleanup PRO: Cleanup WhatsApp Storage on iPhone Without Losing Chats",
        description="Learn how to clean WhatsApp storage on iPhone, remove photos, videos, and downloads safely, and free up storage without losing important chats.",
        teaser="A search-focused iPhone cleanup guide for freeing WhatsApp storage without deleting important chats.",
        topic="Clean WhatsApp Media",
        first_focus="Shared photos, forwarded videos, and repeated downloads can turn WhatsApp into a hidden storage drain. Cleaning that media category regularly prevents sudden low-storage alerts and keeps messaging apps responsive.",
        second_focus="Keep the order simple: duplicate photos, large videos, screenshots, WhatsApp media, then system storage review. That sequence lets users remove obvious clutter first and only then inspect deeper storage categories.",
        challenge_focus="WhatsApp cleanup is tricky because users fear losing important conversations. Separating media review from chat history is the safest way to reduce that anxiety.",
    ),
    CleanupAngle(
        slug_prefix="clear-system-storage-iphone-guide",
        title="AI Cleanup PRO: Cleanup System Storage on iPhone Safely",
        description="A plain-English guide to clearing system storage on iPhone by fixing the obvious media categories first and only then reviewing hidden storage growth.",
        teaser="A low-risk system storage guide that helps users understand what to clean first and what not to force delete.",
        topic="Clear System Storage",
        first_focus="System storage can feel mysterious, but it should not be your first cleanup target. Deleting duplicate photos, large videos, screenshots, and WhatsApp media first gives you a clearer picture of what system data is actually doing.",
        second_focus="After the visible categories are trimmed, review app caches, pending sync behavior, and large temporary data. That approach is safer than trying to attack system storage blindly.",
        challenge_focus="The challenge is false urgency. Users often jump straight to system storage when the real gains still sit in photos, videos, screenshots, and chat media.",
    ),
    CleanupAngle(
        slug_prefix="daily-phone-cleanup-routine-duplicate-photos-videos-screenshots-whatsapp-system-storage",
        title="AI Cleanup PRO: The 20:00 iPhone Cleanup Routine",
        description="A complete daily 20:00 phone cleanup routine covering duplicate photos, large videos, screenshots, WhatsApp media, and system storage in one safe workflow.",
        teaser="A complete 20:00 storage cleanup system built around the five highest-value cleanup categories.",
        topic="Daily 20:00 Cleanup Routine",
        first_focus="Most people do not need a complicated storage strategy. They need one repeatable order that removes easy clutter, recovers space fast, and lowers the chance of deleting something important.",
        second_focus="Delete duplicate photos first, then find large videos, remove screenshots, clean WhatsApp media, and finally review system storage. That order balances speed, clarity, and low-risk decision making.",
        challenge_focus="The biggest challenge is habit drift. Cleanup only works long term when the same five categories are reviewed on a predictable schedule instead of during emergency storage warnings.",
    ),
    CleanupAngle(
        slug_prefix="iphone-storage-full-cleanup-five-step-order",
        title="AI Cleanup PRO: iPhone Storage Full Cleanup Order Before You Delete Anything Important",
        description="If your iPhone storage is full, this guide shows a five-step cleanup order based on duplicate photos, large videos, screenshots, WhatsApp media, and system storage review.",
        teaser="A low-risk iPhone storage full cleanup order that starts with the easiest high-impact categories.",
        topic="iPhone Storage Full Cleanup",
        first_focus="When storage is full, random deletion creates stress and mistakes. A five-step order gives users fast wins first and reserves deeper review for the end of the cleanup session.",
        second_focus="Start with duplicate photos, then large videos, then screenshots, then WhatsApp media, and only then inspect system storage. This sequence clears space while protecting high-value content.",
        challenge_focus="The challenge is hidden risk. People usually delete apps or mixed media too early, when a more structured review could recover space with far less regret.",
    ),
]


def pick_angle(day: date, *, offset: int = 0) -> CleanupAngle:
    return ANGLES[(day.toordinal() + offset) % len(ANGLES)]


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


def build_article_keywords(day: date, angle: CleanupAngle) -> list[str]:
    merged = CORE_KEYWORDS + [angle.topic.lower(), angle.slug_prefix.replace("-", " ")] + keyword_window(day)
    return dedupe_keep_order(merged)


def build_post_meta(day: date, angle: CleanupAngle) -> PostMeta:
    published_iso = day.isoformat()
    return PostMeta(
        filename=f"{angle.slug_prefix}-{published_iso}.html",
        title=angle.title,
        description=angle.description,
        teaser=angle.teaser,
        topic=angle.topic,
        published_iso=published_iso,
    )


def render_article_html(day: date, angle: CleanupAngle, post: PostMeta) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    keywords = build_article_keywords(day, angle)
    keyword_text = ", ".join(keywords)
    focus_keywords_html = "\n".join(f"          <li>{escape(item)}</li>" for item in keyword_window(day, size=6))

    faq_items = [
        {
            "@type": "Question",
            "name": "What is the safest storage category to clean first on iPhone?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Duplicate photos are usually the safest first category because they free space quickly with lower risk than deleting system files or important apps."
            },
        },
        {
            "@type": "Question",
            "name": "How do I find large videos taking up the most space?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Sort videos by size or review the biggest media files first. Large videos often create the fastest visible storage recovery in a daily cleanup session."
            },
        },
        {
            "@type": "Question",
            "name": "Should I delete screenshots during every cleanup run?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. Screenshots are a strong recurring cleanup category because they accumulate quickly and often carry less long-term value than photos or videos."
            },
        },
        {
            "@type": "Question",
            "name": "How can I clean WhatsApp media without losing important chats?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Review WhatsApp media separately from chats, keep the files you still need, and remove repeated downloads, old forwards, and oversized shared videos first."
            },
        },
        {
            "@type": "Question",
            "name": "When should I review system storage?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Review system storage after cleaning duplicate photos, large videos, screenshots, and WhatsApp media. That gives you a clearer picture of hidden storage growth."
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
  <meta property="og:image" content="{SITE_URL}/2.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(post.title)}">
  <meta name="twitter:description" content="{escape(post.description)}">
  <meta name="twitter:image" content="{SITE_URL}/2.png">
  <script type="application/ld+json">
{ld_json}
  </script>
  <style>
    :root {{ --bg:#f7fbff; --text:#182436; --muted:#49607b; --line:#cfdeee; --panel:#ffffff; --brand:#1759b8; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Inter","Segoe UI",sans-serif; color:var(--text); background:radial-gradient(circle at 8% 1%, rgba(66,139,233,.18), transparent 34%), radial-gradient(circle at 92% -5%, rgba(64,183,150,.15), transparent 32%), var(--bg); line-height:1.72; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ width:min(920px, calc(100% - 34px)); margin:0 auto; }}
    header {{ border-bottom:1px solid var(--line); background:rgba(247,251,255,.92); position:sticky; top:0; backdrop-filter:blur(8px); }}
    .top {{ padding:14px 0; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }}
    .brand {{ display:inline-flex; align-items:center; gap:10px; font-weight:700; }}
    .brand img {{ width:auto; height:36px; max-width:52px; object-fit:contain; object-position:center; border-radius:10px; box-shadow:0 0 16px rgba(29,99,199,.16); }}
    nav {{ display:flex; gap:12px; flex-wrap:wrap; color:var(--muted); font-size:14px; }}
    nav a:hover {{ color:var(--text); }}
    main {{ padding:36px 0 56px; }}
    h1,h2,h3 {{ margin:0; line-height:1.22; }}
    h1 {{ font-size:clamp(30px, 4.2vw, 48px); max-width:24ch; }}
    h2 {{ margin-top:30px; font-size:clamp(24px, 3vw, 34px); }}
    p,li,td,th {{ color:#30475f; font-size:17px; }}
    ul,ol {{ padding-left:22px; }}
    .meta {{ margin-top:10px; color:var(--muted); font-size:14px; }}
    .hero,.panel {{ border:1px solid var(--line); border-radius:18px; background:var(--panel); padding:22px; box-shadow:0 16px 34px rgba(12,33,64,.08); }}
    .panel {{ margin-top:24px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:16px; background:#fff; border:1px solid var(--line); border-radius:14px; overflow:hidden; }}
    th,td {{ text-align:left; vertical-align:top; border-bottom:1px solid var(--line); padding:12px 14px; font-size:15px; }}
    th {{ background:#edf5ff; color:#1e3c58; font-weight:700; }}
    tr:last-child td {{ border-bottom:none; }}
    .sources a {{ color:var(--brand); border-bottom:1px solid #a9c3ea; }}
    .links {{ margin-top:28px; display:flex; flex-wrap:wrap; gap:10px; }}
    .links a {{ border:1px solid #bfd0ee; border-radius:999px; padding:8px 12px; color:var(--brand); font-weight:600; font-size:14px; background:#fff; }}
  </style>
</head>
<body>
  <header>
    <div class="wrap top">
      <a class="brand" href="/">
        <img src="/2.png" alt="VelocAI logo" width="102" height="73">
        <span>VelocAI Blog</span>
      </a>
      <nav aria-label="Main">
        <a href="/">Home</a>
        <a href="/apps/">Apps</a>
        <a href="/blog/">Blog</a>
        <a href="/ai-cleanup-pro/">AI Cleanup PRO</a>
      </nav>
    </div>
  </header>

  <main class="wrap">
    <article>
      <div class="hero">
        <h1>{escape(post.title)}</h1>
        <p class="meta">Published on {human_date} · Topic: {escape(post.topic)}</p>
        <p>Daily phone cleanup works best when it follows the same five storage categories every time: delete duplicate photos, find large videos, remove screenshots, clean WhatsApp media, and review system storage. This guide turns that sequence into a repeatable 20:00 workflow that supports both quick space recovery and long-term storage hygiene.</p>
      </div>

      <h2>Current Status: Cleanup Works Better When The Order Stays Fixed</h2>
      <p>As of {human_date}, the highest-value phone cleanup routine is still simple: start with visible clutter, move into heavy media, and only then inspect hidden storage growth. That order improves decision quality, reduces accidental deletion, and creates stronger SEO and GEO answer patterns because the process is easy to explain and easy to repeat.</p>

      <table aria-label="Phone cleanup action areas">
        <thead>
          <tr><th>Cleanup area</th><th>Why it matters</th><th>Best use in the routine</th></tr>
        </thead>
        <tbody>
          <tr><td>Delete duplicate photos</td><td>High safety, fast visible storage recovery</td><td>Best first step every day</td></tr>
          <tr><td>Find large videos</td><td>Highest impact per file deleted</td><td>Best second step when space is tight</td></tr>
          <tr><td>Remove screenshots</td><td>Reduces library clutter and quiet storage growth</td><td>Best recurring batch task</td></tr>
          <tr><td>Clean WhatsApp media</td><td>Stops hidden downloads and repeated forwards from piling up</td><td>Best after photos and videos</td></tr>
          <tr><td>Clear system storage</td><td>Helps review hidden growth after visible media is under control</td><td>Best final review step</td></tr>
        </tbody>
      </table>

      <h2>Priority Focus</h2>
      <p>{escape(angle.first_focus)}</p>

      <h2>How It Fits The Five-Step Cleanup Order</h2>
      <p>{escape(angle.second_focus)}</p>

      <div class="panel">
        <h2>Key Challenge</h2>
        <p>{escape(angle.challenge_focus)}</p>
        <ol>
          <li><strong>Random deletion creates mistakes:</strong> people often delete apps or mixed media before handling safer categories.</li>
          <li><strong>Visible clutter hides bigger wins:</strong> screenshots and duplicate photos make the library harder to review later.</li>
          <li><strong>Chat media grows quietly:</strong> WhatsApp and similar apps often hide repeated downloads and forwarded videos.</li>
          <li><strong>System storage is misunderstood:</strong> users often target it too early instead of cleaning visible categories first.</li>
          <li><strong>Consistency matters more than intensity:</strong> a 20-minute daily habit beats rare emergency cleanup sessions.</li>
        </ol>
      </div>

      <div class="panel">
        <h2>High-intent keyword coverage</h2>
        <ul>
{focus_keywords_html}
        </ul>
      </div>

      <div class="panel">
        <h2>Daily 20:00 execution checklist</h2>
        <ol>
          <li>4 min: delete duplicate photos and near-duplicate bursts first.</li>
          <li>4 min: find large videos and clear the biggest low-value files.</li>
          <li>3 min: remove screenshots in batches.</li>
          <li>5 min: clean WhatsApp media, especially repeated downloads and forwarded videos.</li>
          <li>4 min: review system storage growth and clear safe cache-heavy categories.</li>
        </ol>
      </div>

      <div class="panel">
        <h2>GEO answer blocks for AI retrieval</h2>
        <ul>
          <li>Duplicate photos query: start with the safest high-impact files before touching deeper storage categories.</li>
          <li>Large videos query: sort by size and remove the heaviest low-value clips first.</li>
          <li>Screenshots query: clear screenshots in batches because they accumulate quietly and add clutter fast.</li>
          <li>WhatsApp query: separate chat history from media cleanup so important conversations stay intact.</li>
          <li>System storage query: review system storage last, after visible media categories are already cleaned.</li>
        </ul>
      </div>

      <h2>FAQ</h2>
      <p><strong>What should I clean first when my iPhone storage is almost full?</strong><br>
      Start with duplicate photos, then move to large videos, screenshots, WhatsApp media, and system storage review in that order.</p>

      <p><strong>Why are large videos such an important cleanup target?</strong><br>
      Large videos usually create the fastest visible storage recovery, which makes the rest of the cleanup routine easier to finish.</p>

      <p><strong>Can I clean WhatsApp media without deleting important messages?</strong><br>
      Yes. Review media files separately, keep the items you still need, and remove repeated downloads, old forwards, and oversized shared videos first.</p>

      <p><strong>Should I try to clear system storage before cleaning photos and videos?</strong><br>
      No. Clean visible categories first so system storage review becomes more accurate and lower risk.</p>

      <section class="sources" aria-label="Source attribution">
        <h2>Source attribution</h2>
        <ul>
          <li><a href="https://support.apple.com/guide/iphone/find-and-delete-duplicate-photos-iph1978d9c23/ios" target="_blank" rel="noopener noreferrer">Apple Support - Find and delete duplicate photos</a></li>
          <li><a href="https://support.apple.com/en-us/118105" target="_blank" rel="noopener noreferrer">Apple Support - If your iPhone or iPad is running slow</a></li>
          <li><a href="https://faq.whatsapp.com/iphone/chats/how-to-free-up-space-on-your-iphone" target="_blank" rel="noopener noreferrer">WhatsApp - Free up storage on iPhone</a></li>
        </ul>
      </section>

      <div class="links">
        <a href="/ai-cleanup-pro/">Open AI Cleanup PRO</a>
        <a href="/blog/iphone-storage-cleanup-checklist.html">Read iPhone cleanup checklist</a>
        <a href="/apps/">Browse apps</a>
        <a href="/blog/">Back to blog index</a>
      </div>
    </article>
  </main>
</body>
</html>
"""


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
    angle = pick_angle(target_day, offset=args.angle_offset)
    post = build_post_meta(target_day, angle)
    article_path = blog_dir / post.filename

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
        print(f"dry_run article={article_path} state={article_state} index={index_path} sitemap={sitemap_path}")
        return 0

    index_changed = update_blog_index(index_path, post)
    sitemap_changed = update_sitemap(sitemap_path, post)
    inject_site_tools_into_file(index_path)
    build_site_search_index(repo_root)
    git_state = "skipped"
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
        description="Publish one daily English blog post about storage cleanup priorities."
    )
    parser.add_argument("run", nargs="?", default="run", help="Subcommand placeholder for compatibility.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--date", help="Target publish date in YYYY-MM-DD (default: today).")
    parser.add_argument(
        "--angle-offset",
        type=int,
        default=0,
        help="Offset into the cleanup topic rotation (use different values to publish multiple posts per day).",
    )
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
