#!/usr/bin/env python3
"""Publish one daily English blog post focused on Dual Camera creator workflows."""

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
from blog_similarity import load_blog_pages, max_similarity_against_existing
from site_tools import build_site_search_index, inject_site_tools_into_file

CORE_KEYWORDS = [
    "dual camera",
    "dual recorder app iphone",
    "record landscape and portrait video iphone",
    "creator video app iphone",
    "record vertical and horizontal video at the same time",
    "iphone multicam creator workflow",
    "dual format recording app",
]

LONG_TAIL_KEYWORDS = [
    "how to record landscape and portrait video in one take",
    "best iphone app for vertical and horizontal video together",
    "dual recorder app for youtube and reels workflow",
    "one take creator workflow iphone camera app",
    "product demo recording app for vertical and horizontal clips",
    "travel creator app for landscape and portrait capture",
    "tutorial recording app for short and long form video",
    "talking head video app with dual format output",
    "multicam recording app iphone for creators",
    "ultra wide framing app for creator video",
    "repurpose one take into reels and youtube clips",
    "how to reduce reshoots for social and long form content",
    "iphone creator workflow for behind the scenes clips",
    "video app for product walkthroughs and creator demos",
    "how to shoot once for short form and wide playback",
    "dual camera app for travel vlogs and tutorials",
]


@dataclass(frozen=True)
class DualShotAngle:
    slug_prefix: str
    title: str
    description: str
    teaser: str
    topic: str
    intent_focus: str
    workflow_focus: str
    edge_focus: str
    scenario_focus: str


ANGLES: list[DualShotAngle] = [
    DualShotAngle(
        slug_prefix="dualshot-camera-one-take-creator-workflow-guide",
        title="Why Dual Camera Fits a One-Take Creator Workflow",
        description="A practical Dual Camera guide for creators who want one iPhone take to become both landscape video and portrait content without repeating the shoot.",
        teaser="The strongest creator workflow is often not more editing. It is fewer repeated takes before editing even begins.",
        topic="One-Take Creator Workflow",
        intent_focus="Creators in this situation usually already know they need both wide and vertical output. The real question is whether one iPhone workflow can reduce repeated setup, repeated speaking, and repeated camera alignment.",
        workflow_focus="Dual Camera fits because the product promise is simple and high intent: record landscape and portrait video at the same time, then reuse the same moment across more than one publishing format.",
        edge_focus="That matters because creator fatigue usually starts before post-production. Each repeated take adds energy loss, continuity risk, and small framing differences that make the final package feel less consistent.",
        scenario_focus="This angle works well for solo creators, educators, and founders who want one clean take for tutorials, announcements, walkthroughs, and short social cutdowns.",
    ),
    DualShotAngle(
        slug_prefix="dualshot-camera-short-form-long-form-guide",
        title="How Dual Camera Helps You Shoot for Short Form and Long Form Together",
        description="See how Dual Camera supports creators who need portrait clips for social posts and landscape footage for longer playback from the same iPhone recording session.",
        teaser="Publishing to more than one format stops feeling efficient the moment every format needs its own reshoot.",
        topic="Short-Form and Long-Form Recording",
        intent_focus="This problem comes from creators balancing YouTube-style playback with vertical platforms. They need a practical way to capture for both without making the shoot twice as slow.",
        workflow_focus="Dual Camera answers that need directly by turning one recording session into two output paths: wide footage for longer edits and portrait footage for vertical distribution.",
        edge_focus="That dual-format capture is useful because platform demands are different, but the moment being recorded is often the same. Capturing both early protects timing, expression, and framing continuity.",
        scenario_focus="This topic serves vloggers, product reviewers, coaches, and social teams that publish one core idea across multiple channels.",
    ),
    DualShotAngle(
        slug_prefix="dualshot-camera-product-demo-tutorial-guide",
        title="Use Dual Camera for Product Demos and Tutorial Recording on iPhone",
        description="A Dual Camera guide for creators recording product demos, walkthroughs, and tutorials that need both landscape playback and portrait cutdowns from one take.",
        teaser="A good product demo loses momentum when the presenter has to repeat the same explanation just to fit a second aspect ratio.",
        topic="Product Demos and Tutorials",
        intent_focus="Creators in this scenario usually need faster demo production: one explanation, one gesture sequence, one setup, and multiple publishable outputs for product pages, social clips, and update posts.",
        workflow_focus="Dual Camera fits tutorial and demo work because it reduces the friction between a full explanation for long-form viewers and a compact vertical asset for discovery and promotion.",
        edge_focus="The scientific part is simple cause and effect: fewer retakes means more consistent voice, more consistent framing, and less editing work to reconcile near-duplicate clips that do not quite match.",
        scenario_focus="This is especially useful for app demos, hardware walkthroughs, tutorial segments, unboxings, and onboarding content that must explain once and publish many times.",
    ),
    DualShotAngle(
        slug_prefix="dualshot-camera-travel-vlog-repurposing-guide",
        title="When Dual Camera Makes Travel Vlog Repurposing Easier",
        description="Learn how Dual Camera helps travel creators capture one iPhone moment for wide vlog edits and portrait social clips without rebuilding the same scene twice.",
        teaser="Travel footage gets harder to repeat the second the train leaves, the light changes, or the crowd shifts.",
        topic="Travel Vlog Repurposing",
        intent_focus="Travel creators search for faster capture workflows because reshoots are often impossible. The right app needs to preserve the moment while still supporting more than one publishing format later.",
        workflow_focus="Dual Camera supports that reality by capturing the same travel moment once while keeping both long-form and short-form options open after the trip moves on.",
        edge_focus="That is valuable because travel content is time sensitive in a literal way. Lighting, motion, crowd density, and access windows change quickly, so one-take efficiency has a measurable production benefit.",
        scenario_focus="This angle fits city walks, hotel reviews, food clips, transit moments, scenic b-roll, and behind-the-scenes travel posts.",
    ),
    DualShotAngle(
        slug_prefix="dualshot-camera-talking-head-social-clips-guide",
        title="How Dual Camera Helps Talking-Head Creators Publish Faster",
        description="A practical Dual Camera guide for talking-head videos, commentary, coaching clips, and interviews that need both wide and vertical output from one session.",
        teaser="Talking-head creators usually do not need more camera theory. They need fewer reasons to repeat the same sentence.",
        topic="Talking-Head Creator Workflow",
        intent_focus="People searching this workflow are often recording themselves regularly for lessons, commentary, or brand content. Their pain point is repetitive setup and repetitive speaking, not lack of ideas.",
        workflow_focus="Dual Camera is a strong fit because a single take can feed a wide master clip plus a portrait post without forcing the speaker to reset tone, posture, and timing for a second recording pass.",
        edge_focus="This improves consistency. When the same sentence is recorded twice, subtle voice changes and hand-position changes create more edit friction than most creators expect.",
        scenario_focus="This topic serves consultants, coaches, educators, founders, interview hosts, and creator-led brands publishing daily commentary or educational clips.",
    ),
    DualShotAngle(
        slug_prefix="dualshot-camera-multicam-ultra-wide-framing-guide",
        title="Why Multicam and Ultra Wide Support Matter in Dual Camera",
        description="A Dual Camera guide to multicam and ultra wide framing choices for creators who want more usable composition before editing vertical and horizontal versions.",
        teaser="Good framing is not only about aesthetics. It decides how much room the editor has after the shoot is already over.",
        topic="Multicam and Ultra Wide Framing",
        intent_focus="Creators comparing this workflow want to know whether framing flexibility changes real output quality or is just another camera-feature checklist item.",
        workflow_focus="Dual Camera can answer that because multicam and ultra wide support give creators more room to protect both aspect ratios before the edit starts.",
        edge_focus="This matters scientifically in the workflow sense: wider and cleaner source framing lowers the risk of cropping out hands, products, or contextual details once clips are reformatted for vertical distribution.",
        scenario_focus="This topic fits product tables, desk demos, interviews, walking shots, cooking clips, and tutorial scenes where composition must survive more than one final crop.",
    ),
    DualShotAngle(
        slug_prefix="dualshot-camera-behind-the-scenes-content-guide",
        title="Use Dual Camera for Behind-the-Scenes and Creator Process Clips",
        description="See how Dual Camera helps creators capture behind-the-scenes content, process footage, and studio moments for both wide edits and vertical social posts.",
        teaser="Behind-the-scenes content works best when it feels natural, which is exactly why extra retakes can ruin it.",
        topic="Behind-the-Scenes Content",
        intent_focus="Creators using this angle usually want more publishable context from the same shoot: process clips, setup moments, quick explanations, and extra footage that keeps the audience close to the work.",
        workflow_focus="Dual Camera supports that goal because creators can keep one natural recording session and still leave with footage that works for both recap edits and portrait snippets.",
        edge_focus="The hidden benefit is retention of spontaneity. Behind-the-scenes footage loses credibility when it is obviously recreated only to fit another format.",
        scenario_focus="This topic is useful for studio diaries, maker videos, setup tours, editing process clips, rehearsal footage, and launch-week creator updates.",
    ),
    DualShotAngle(
        slug_prefix="dualshot-camera-small-team-shoot-efficiency-guide",
        title="When Dual Camera Saves Time for Small Creator Teams",
        description="A Dual Camera workflow guide for small creator teams that need faster capture, cleaner handoffs, and more reusable footage from each iPhone shoot.",
        teaser="Small teams do not usually run out of ideas first. They run out of time, attention, and reshoot patience.",
        topic="Small-Team Creator Efficiency",
        intent_focus="This problem comes from small teams handling strategy, filming, editing, and publishing in the same week. They need a camera workflow that creates more usable assets without multiplying production time.",
        workflow_focus="Dual Camera helps because one session can deliver wide and portrait material for different editors, channels, or deadlines without reassembling the crew for another pass.",
        edge_focus="That operational gain is measurable: fewer resets, fewer repeated lines, faster edit branching, and less version confusion once the footage reaches post-production.",
        scenario_focus="This angle fits startup launch teams, lean ecommerce studios, creators with one assistant, and social teams building weekly product content on iPhone.",
    ),
]


def pick_angle(day: date, *, offset: int = 0) -> DualShotAngle:
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


def build_article_keywords(day: date, angle: DualShotAngle) -> list[str]:
    merged = CORE_KEYWORDS + [angle.topic.lower(), angle.slug_prefix.replace("-", " ")] + keyword_window(day)
    return dedupe_keep_order(merged)


def build_post_meta(day: date, angle: DualShotAngle) -> PostMeta:
    published_iso = day.isoformat()
    return PostMeta(
        filename=f"{angle.slug_prefix}-{published_iso}.html",
        title=angle.title,
        description=angle.description,
        teaser=angle.teaser,
        topic=angle.topic,
        published_iso=published_iso,
    )


def structure_variant(day: date, angle: DualShotAngle) -> int:
    return (day.toordinal() + len(angle.slug_prefix)) % 3


def render_article_html(day: date, angle: DualShotAngle, post: PostMeta) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    keywords = build_article_keywords(day, angle)
    keyword_text = ", ".join(keywords)
    tldr = (
        f"As of {human_date}, Dual Camera is most useful when creators need one iPhone take to become both "
        "landscape video and portrait content. That workflow reduces reshoots, preserves timing, and creates more "
        "publishable footage for social clips, tutorials, demos, and travel posts."
    )
    answer_first = (
        f"As of {human_date}, Dual Camera solves a practical production problem: how to shoot once for short-form "
        "and long-form publishing without rebuilding the same scene twice."
    )
    workflow_lead = (
        f"As of {human_date}, Dual Camera is useful when the capture plan is specific: decide which subject must stay readable in landscape, "
        "which action must stay centered in portrait, and which parts of the scene cannot be cropped out later."
    )
    practical_lead = (
        f"As of {human_date}, the strongest one-take workflow is built before recording: lock the scene, test audio, leave safe crop room, "
        "and verify that both outputs still explain the same moment clearly."
    )
    variant = structure_variant(day, angle)
    shoot_checklist = [
        "Record a 10-second test and confirm both landscape and portrait framing before the real take.",
        "Keep faces, products, hands, labels, and screen details inside the safe area for both outputs.",
        "Check audio from the actual speaking distance, not from the setup position.",
        "Avoid fast side-to-side gestures if the vertical crop needs to preserve detail.",
        "Name the clip by scene or product before editing so the wide and vertical versions stay paired.",
    ]
    shoot_checklist_html = "\n".join(f"          <li>{escape(item)}</li>" for item in shoot_checklist)
    tradeoff_checks = [
        "If the subject barely fits in portrait, do not assume the editor can fix it later.",
        "If the product demo depends on tiny on-screen details, leave more crop room than feels necessary.",
        "If the scene changes lighting quickly, spend the extra minute on a test take instead of trusting the live setup.",
        "If the vertical cutdown is only marketing garnish, do not let it compromise the readability of the wide master shot.",
    ]
    tradeoff_checks_html = "\n".join(f"          <li>{escape(item)}</li>" for item in tradeoff_checks)
    publish_paths = [
        "Use the wide version as the main walkthrough, tutorial, or review asset.",
        "Use the portrait version for the hook, summary, or strongest visual beat.",
        "Keep both outputs tied to the same clip name so the edit handoff stays clean.",
        "Reshoot only when one of the two formats fails the actual publishing job.",
    ]
    publish_paths_html = "\n".join(f"          <li>{escape(item)}</li>" for item in publish_paths)

    faq_items = [
        {
            "@type": "Question",
            "name": "What is Dual Camera used for?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Dual Camera is used to record landscape and portrait video at the same time on iPhone so creators can publish one shoot across wide and vertical formats."
            },
        },
        {
            "@type": "Question",
            "name": "Can Dual Camera record vertical and horizontal video in one take?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. Dual Camera is designed to capture both formats during one recording session, which helps creators reuse the same moment for long-form playback and short-form posts."
            },
        },
        {
            "@type": "Question",
            "name": "Who benefits most from Dual Camera?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Creators making tutorials, product demos, talking-head videos, travel clips, behind-the-scenes footage, and social cutdowns benefit most because one session can create more than one publishable format."
            },
        },
        {
            "@type": "Question",
            "name": "What should creators check before recording?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Creators should check framing, audio, safe crop room, lighting changes, and whether the same take still works for both landscape playback and portrait social posts."
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
                        "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/velocai.png"},
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
<html lang=\"en-US\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{escape(post.title)} | VelocAI Blog</title>
  <meta name=\"description\" content=\"{escape(post.description)}\">
  <meta name=\"keywords\" content=\"{escape(keyword_text)}\">
  <meta name=\"robots\" content=\"index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1\">
  <link rel=\"canonical\" href=\"{canonical}\">
  <link rel=\"icon\" type=\"image/x-icon\" href=\"/velocai.ico\">
  <meta property=\"og:type\" content=\"article\">
  <meta property=\"og:locale\" content=\"en_US\">
  <meta property=\"og:site_name\" content=\"VelocAI\">
  <meta property=\"og:title\" content=\"{escape(post.title)}\">
  <meta property=\"og:description\" content=\"{escape(post.description)}\">
  <meta property=\"og:url\" content=\"{canonical}\">
  <meta property=\"og:image\" content=\"{SITE_URL}/dualshot/dualshot-camera-icon.png\">
  <meta name=\"twitter:card\" content=\"summary_large_image\">
  <meta name=\"twitter:title\" content=\"{escape(post.title)}\">
  <meta name=\"twitter:description\" content=\"{escape(post.description)}\">
  <meta name=\"twitter:image\" content=\"{SITE_URL}/dualshot/dualshot-camera-icon.png\">
  <script type=\"application/ld+json\">
{ld_json}
  </script>
  <style>
    :root {{ --bg:#f4f9ff; --text:#1a2838; --muted:#4b6178; --line:#cfe0f1; --panel:#ffffff; --brand:#1d63c7; --brand-soft:#e6f2ff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Inter","Segoe UI",sans-serif; color:var(--text); background:radial-gradient(circle at 8% 2%, rgba(66,139,233,.18), transparent 34%), radial-gradient(circle at 88% -6%, rgba(47,195,170,.14), transparent 32%), var(--bg); line-height:1.72; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ width:min(920px, calc(100% - 34px)); margin:0 auto; }}
    header {{ border-bottom:1px solid var(--line); background:rgba(244,249,255,.92); }}
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
    .hero, .panel, .tldr, .capsule, table {{ background:var(--panel); border:1px solid var(--line); border-radius:24px; }}
    .hero {{ padding:26px; box-shadow:0 14px 32px rgba(24,36,54,.05); }}
    .panel, .tldr, .capsule {{ margin-top:24px; padding:22px; box-shadow:0 14px 32px rgba(24,36,54,.05); }}
    .tldr {{ border-left:6px solid #2fc3aa; }}
    .capsule {{ background:#f8fbff; }}
    .eyebrow {{ display:inline-flex; margin-bottom:14px; border-radius:999px; padding:8px 12px; background:var(--brand-soft); color:var(--brand); font-size:13px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }}
    .hero > p:not(.meta) {{ margin:14px 0 0; max-width:none; }}
    .cta-row,.links {{ margin-top:32px; display:flex; gap:14px; flex-wrap:wrap; }}
    .cta-row a,.links a {{ border:1px solid #bdd7de; border-radius:999px; padding:10px 14px; font-weight:600; font-size:14px; color:var(--brand); background:#fff; }}
    .cta-row .primary {{ background:var(--brand); color:#fff; border-color:var(--brand); }}
    table {{ width:100%; margin-top:24px; border-collapse:separate; border-spacing:0; overflow:hidden; }}
    th,td {{ padding:16px 18px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    tr:last-child td {{ border-bottom:none; }}
    th {{ color:var(--text); font-weight:700; background:rgba(29,99,199,.08); }}
    .sources a {{ color:var(--brand); border-bottom:1px solid #9fcad0; }}
  </style>
</head>
<body>
  <header>
    <div class=\"wrap top\">
      <a class=\"brand\" href=\"/\"><img src=\"/velocai.png\" alt=\"VelocAI logo\" width=\"103\" height=\"103\"><span>VelocAI Blog</span></a>
      <nav aria-label="Main">
        <a href="/">Home</a>
        <a href="/apps/">Apps</a>
        <a href="/blog/">Blog</a>
        <a href="/dualshot/">Dual Camera</a>
      </nav>
    </div>
  </header>
  <main class=\"wrap\">
    <article>
      <div class=\"hero\">
        <span class=\"eyebrow\">Dual Camera Practical Guide</span>
        <h1>{escape(post.title)}</h1>
        <p class=\"meta\">Published on {escape(human_date)} | Topic: {escape(post.topic)}</p>
        <p>{escape(angle.teaser)}</p>
        <div class=\"links\"><a href=\"/dualshot/\">Open Dual Camera</a><a href=\"https://apps.apple.com/app/dualshot-camera-dual-recorder/id6761664966\" target=\"_blank\" rel=\"noopener noreferrer\">App Store</a></div>
      </div>
      <div class=\"tldr\">
        <p>{escape(tldr)}</p>
      </div>
      <div class=\"panel\">
        <h2>{escape(["The Production Problem", "Why Creators Reach for This", "What Makes the Shoot Worth Saving"][variant])}</h2>
        <p>{escape(answer_first)}</p>
        <p>{escape(angle.intent_focus)}</p>
      </div>
      <div class=\"panel\">
        <h2>{escape(["Where Dual Camera Earns Its Keep", "How the One-Take Workflow Holds Up", "Why the Format Split Matters Early"][variant])}</h2>
        <p>{escape(workflow_lead)}</p>
        <p>{escape(angle.workflow_focus)}</p>
      </div>
      <div class=\"panel\">
        <h2>{escape(["Best-Fit Scenario", "Who Gets the Most Time Back", "When the Workflow Pays Off"][variant])}</h2>
        <p>{escape(angle.scenario_focus)}</p>
        <p>{escape(angle.edge_focus)}</p>
      </div>
      <div class=\"panel\">
        <h2>{escape(["Before You Press Record", "Setup Checks That Actually Matter", "What to Lock Before the Take"][variant])}</h2>
        <p>{escape(practical_lead)}</p>
        <p>Before pressing record, check audio, lighting, subject distance, hand movement, and safe crop space. If either format hides the product, face, gesture, or key background detail, fix the setup before the take instead of repairing it in editing.</p>
      </div>
      <div class=\"panel\">
        <h2>{escape(["One-Take Setup Checklist", "Edit-Saving Checklist", "Capture Rules"][variant])}</h2>
        <ul>
{shoot_checklist_html}
        </ul>
      </div>
      <div class=\"panel\">
        <h2>{escape(["Tradeoffs to Accept Early", "What Not to Compromise", "When to Reshoot Instead"][variant])}</h2>
        <ul>
{tradeoff_checks_html if variant != 2 else publish_paths_html}
        </ul>
      </div>
      <div class=\"panel\">
        <h2>{escape(["Useful Next Read", "Workflow Follow-Up", "Related Creator Path"][variant])}</h2>
        <p><a href=\"/dualshot/\">Dual Camera product page</a> is the right next stop if you want the core capture promise, App Store path, and multicam framing context in one place.</p>
        <p><a href=\"/translate/\">Translate AI</a> becomes relevant when the same shoot also needs captions, OCR translation, or bilingual review after recording.</p>
      </div>
    </article>
  </main>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish one daily Dual Camera blog article.")
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
    similarity = max_similarity_against_existing(html, load_blog_pages(blog_dir))
    if similarity >= 0.40:
        raise ValueError(f"Refusing to publish {post.filename}: similarity {similarity:.4f} >= 0.40")
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
