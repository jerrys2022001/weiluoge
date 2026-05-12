#!/usr/bin/env python3
"""Publish one daily English blog post focused on Octopus mobile coding workflows."""

from __future__ import annotations

import argparse
import json
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

APP_STORE_URL = "https://apps.apple.com/us/app/octopus-codex-code-app/id6763834077"
PRODUCT_URL = f"{SITE_URL}/octopus/"
PRODUCT_IMAGE = f"{SITE_URL}/octopus/octopus.png"

CORE_KEYWORDS = [
    "octopus codex code app",
    "mobile codex workflow iphone",
    "approve coding agent actions from phone",
    "resume codex threads on ipad",
    "developer tools app iphone",
    "ssh coding session iphone",
    "remote coding companion iphone",
]

LONG_TAIL_KEYWORDS = [
    "how to approve coding agent commands from iphone",
    "resume codex thread from ipad away from desk",
    "best mobile app for remote coding approvals",
    "iphone app for ssh coding session monitoring",
    "mobile codex workflow with voice notes and images",
    "how to review automation runs from phone",
    "iphone developer tools app for remote server context",
    "approve ai coding permissions remotely on ipad",
    "mobile second screen for codex sessions",
    "runtime status notifications for coding agents on iphone",
    "how to keep project and thread context organized on phone",
    "ssh host fingerprint confirmation iphone coding workflow",
    "use voice notes for mobile bug triage",
    "how to review tool results and files on iphone",
    "remote coding workflow for mac and server from ipad",
    "mobile app for codex approvals and automation history",
]


@dataclass(frozen=True)
class OctopusAngle:
    slug_prefix: str
    title: str
    description: str
    teaser: str
    topic: str
    intent_focus: str
    workflow_focus: str
    edge_focus: str
    scenario_focus: str


ANGLES: list[OctopusAngle] = [
    OctopusAngle(
        slug_prefix="octopus-remote-approvals-mobile-coding-guide",
        title="How Octopus Makes Remote Coding Approvals Faster on iPhone",
        description="A practical Octopus guide for approving agent actions, command requests, and permission decisions from iPhone or iPad without losing thread context.",
        teaser="The approval step is where mobile coding either feels useful or turns into a notification graveyard.",
        topic="Remote Coding Approvals",
        intent_focus="Users searching this problem already trust the coding agent to do work. What they need next is a mobile approval flow that keeps the project moving when they are away from the desk.",
        workflow_focus="Octopus fits this intent because the visible App Store copy centers approvals, command decisions, and permission handling as a first-class mobile workflow rather than a hidden admin screen.",
        edge_focus="That matters because approval latency compounds. A five-minute delay on every command review can turn a productive coding session into a stop-start chain that burns time on both the human side and the agent side.",
        scenario_focus="This angle serves founders, solo developers, and engineering leads who want to keep code tasks moving while commuting, walking between meetings, or stepping away from the main workstation.",
    ),
    OctopusAngle(
        slug_prefix="octopus-resume-codex-threads-away-from-desk-guide",
        title="Why Octopus Works for Resuming Codex Threads Away from the Desk",
        description="See how Octopus supports mobile Codex continuity on iPhone and iPad when you need to resume threads, review progress, and continue the same work state remotely.",
        teaser="Most remote coding friction starts when the thread context lives on one machine and the decision-maker lives somewhere else.",
        topic="Resume Codex Threads from Mobile",
        intent_focus="Search intent here comes from users who do not want a brand-new mobile workflow. They want the same Codex thread, the same recent context, and the same work history from a smaller screen.",
        workflow_focus="Octopus is a strong fit because the App Store page explicitly frames the product around carrying Codex sessions on your phone and resuming threads from iPhone or iPad.",
        edge_focus="That continuity matters because restarting a coding conversation from memory is slower than reopening the actual thread with its messages, approvals, tool results, and recent activity intact.",
        scenario_focus="This topic fits developers checking progress from lunch, product managers following a release thread from mobile, and founders reviewing agent output while away from the keyboard.",
    ),
    OctopusAngle(
        slug_prefix="octopus-voice-images-files-context-guide",
        title="Use Octopus Voice, Images, and Files to Add Better Coding Context",
        description="A practical Octopus guide to adding voice notes, screenshots, images, and files from mobile so Codex threads stay grounded in real debugging context.",
        teaser="A remote coding thread gets much better the moment mobile context stops meaning text only.",
        topic="Voice, Image, and File Context",
        intent_focus="Users searching this workflow usually hit the same limit: they can read the thread from mobile, but they also need a fast way to attach the bug screenshot, log capture, whiteboard photo, or spoken note that explains the next step.",
        workflow_focus="Octopus fits because the visible product description calls out voice, images, and files directly, which makes the app easier to position for practical debugging and handoff workflows.",
        edge_focus="The real gain is compression. A screenshot, photo, or short voice note can replace several back-and-forth messages when the issue depends on visual state, phrasing nuance, or a quick spoken explanation.",
        scenario_focus="This topic works for mobile bug triage, on-call notes, QA follow-up, device screenshots, visual regressions, and rapid explanation of failing test behavior.",
    ),
    OctopusAngle(
        slug_prefix="octopus-ssh-app-server-mobile-monitoring-guide",
        title="How Octopus Helps Monitor SSH and App-Server Coding Sessions",
        description="Learn how Octopus supports mobile monitoring for Codex app-server and SSH workflows when projects keep running on a Mac or remote server.",
        teaser="Mobile coding feels credible when it stays connected to the server and project state you already use.",
        topic="SSH and App-Server Monitoring",
        intent_focus="This search cluster comes from developers who are not looking for a toy coding app. They want a mobile surface for real server-backed work that already exists on a Mac, workstation, or remote machine.",
        workflow_focus="Octopus speaks to that need directly because the App Store feature list mentions Codex app-server and SSH connections as a visible core capability.",
        edge_focus="That changes the product story from chat access to infrastructure continuity. The phone becomes a lightweight control point for active work instead of a disconnected second system.",
        scenario_focus="This angle fits long-running refactors, server-side scripts, CI follow-up, remote dev boxes, home lab workflows, and workstation-linked coding sessions that keep running after the laptop closes.",
    ),
    OctopusAngle(
        slug_prefix="octopus-automation-runs-history-mobile-guide",
        title="When Octopus Is Best for Reviewing Automation Runs and History",
        description="A guide to using Octopus for mobile review of automation lists, run-now actions, and run history so repeated coding tasks stay visible outside the desktop session.",
        teaser="Automation only saves time if someone can still see what ran, what failed, and what needs the next push.",
        topic="Automation Runs and History",
        intent_focus="Users searching this problem usually have repeated tasks already in motion. Their question is whether mobile review can keep automation understandable without making them open the laptop every time a task finishes or stalls.",
        workflow_focus="Octopus is well matched because the App Store page explicitly lists automation lists, run-now actions, and run history as part of the mobile feature set.",
        edge_focus="That matters operationally because the hardest part of automation is not pressing run. It is keeping visibility into retries, result state, and whether the system still reflects the intent of the original task.",
        scenario_focus="This angle serves teams running recurring code quality jobs, content schedulers, release checklists, indexing flows, and repeatable publishing tasks that need lightweight mobile oversight.",
    ),
    OctopusAngle(
        slug_prefix="octopus-second-screen-developer-workflow-guide",
        title="Why Octopus Works as a Second Development Screen on iPhone",
        description="See how Octopus can act as a second development screen for Codex sessions, approvals, and runtime status when the main coding work stays on another machine.",
        teaser="A second screen is useful only when it reduces context switching instead of creating more of it.",
        topic="Second Development Screen",
        intent_focus="This query comes from developers comparing whether mobile access is merely passive or whether it can genuinely reduce the need to keep returning to the laptop for status checks and small decisions.",
        workflow_focus="Octopus has a good answer here because the App Store screenshot content includes the idea of a second development screen rather than just a generic companion app.",
        edge_focus="That is important because productive mobile tooling is usually about micro-decisions: glanceable state, quick approvals, short prompts, and targeted follow-up when the main environment is still doing the heavy work.",
        scenario_focus="This topic fits desk-plus-phone setups, iPad sidecar habits, team leads watching build progress, and solo developers who want ambient awareness of active coding sessions.",
    ),
    OctopusAngle(
        slug_prefix="octopus-runtime-status-live-activity-guide",
        title="How Octopus Runtime Status and Live Activity Support Faster Follow-Up",
        description="A practical Octopus guide to runtime status, notifications, and Live Activity deep links for developers who need quicker follow-up from mobile.",
        teaser="A useful coding notification is not the alert itself. It is the speed of getting back into the right thread with the right context.",
        topic="Runtime Status and Live Activity",
        intent_focus="Users searching this topic want to know whether mobile coding tools can reduce the gap between a status change and the next meaningful action.",
        workflow_focus="Octopus fits because the visible feature list includes runtime status, notifications, and Live Activity deep links, which aligns neatly with high-intent searches around remote follow-up and mobile oversight.",
        edge_focus="That feature cluster matters because generic notifications create awareness, but deep links plus thread continuity create action. The difference is whether the user can do the next thing immediately.",
        scenario_focus="This angle serves developers following long-running tasks, approval queues, release-time checks, or background automation that changes state while they are away from the desk.",
    ),
    OctopusAngle(
        slug_prefix="octopus-mobile-bug-triage-test-results-guide",
        title="Use Octopus for Mobile Bug Triage and Test Result Follow-Up",
        description="A mobile Octopus workflow for triaging bugs, sharing failing test context, and sending fast follow-up notes to active Codex threads from iPhone or iPad.",
        teaser="A bug report gets much more useful when the person holding the phone can still add context to the exact thread doing the fix.",
        topic="Mobile Bug Triage",
        intent_focus="Searchers in this cluster usually need a quick bridge between observation and action: a screenshot from QA, a short spoken note, a failing test summary, or a reminder to inspect a specific regression.",
        workflow_focus="Octopus is a strong fit because voice input, image input, files, markdown messages, and thread continuity create a cleaner path from mobile observation to agent action.",
        edge_focus="That matters because bug triage is highly perishable. The longer the context sits outside the thread, the more likely the details get rewritten badly, forgotten, or split across too many tools.",
        scenario_focus="This topic fits QA feedback, staging checks, test result review, release-day issue capture, and support escalations that need to move quickly into the coding workflow.",
    ),
    OctopusAngle(
        slug_prefix="octopus-project-thread-session-management-guide",
        title="How Octopus Keeps Server, Project, and Thread Context Organized",
        description="A practical Octopus guide to managing server, project, thread, and recent session context on mobile so coding work stays understandable across devices.",
        teaser="Mobile access becomes valuable when the session list tells you where the real work lives without making you reconstruct it from memory.",
        topic="Project and Thread Organization",
        intent_focus="This search intent comes from users who already have more than one workspace, server, or thread in motion and need a mobile view that keeps those contexts distinct.",
        workflow_focus="Octopus addresses that directly because the App Store feature list highlights server, project, thread, and recent session management rather than collapsing everything into one flat message history.",
        edge_focus="That structure matters because remote coding breaks down fast when the user cannot tell which environment the next approval or follow-up belongs to.",
        scenario_focus="This angle helps teams with multiple repos, consultants switching client contexts, and solo developers keeping side projects, production work, and experiments separated on mobile.",
    ),
    OctopusAngle(
        slug_prefix="octopus-ssh-fingerprint-keychain-mobile-guide",
        title="Why Octopus SSH Fingerprint and Keychain Flow Matter on Mobile",
        description="See why Octopus host fingerprint confirmation and device Keychain storage matter for safer mobile coding access to Mac and server sessions.",
        teaser="Remote access only feels smooth after the trust step feels clear.",
        topic="SSH Fingerprint and Keychain Setup",
        intent_focus="Users searching this area are looking past the headline workflow and into the credibility question: can a mobile coding companion handle connection trust and credential storage in a way that feels sane?",
        workflow_focus="Octopus has a clear product angle because the App Store feature bullets mention SSH host fingerprint confirmation and device Keychain storage as visible parts of the setup experience.",
        edge_focus="That matters because secure connection flows are part of product adoption. A mobile developer tool is easier to recommend when trust prompts are explicit and credential handling is predictable.",
        scenario_focus="This topic serves developers onboarding a new server, reconnecting from travel, reviewing SSH prompts on iPad, or trying to keep remote access both quick and understandable.",
    ),
]


def pick_angle(day: date, *, offset: int = 0) -> OctopusAngle:
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


def build_article_keywords(day: date, angle: OctopusAngle) -> list[str]:
    merged = CORE_KEYWORDS + [angle.topic.lower(), angle.slug_prefix.replace("-", " ")] + keyword_window(day)
    return dedupe_keep_order(merged)


def build_post_meta(day: date, angle: OctopusAngle) -> PostMeta:
    published_iso = day.isoformat()
    return PostMeta(
        filename=f"{angle.slug_prefix}-{published_iso}.html",
        title=angle.title,
        description=angle.description,
        teaser=angle.teaser,
        topic=angle.topic,
        published_iso=published_iso,
    )


def render_article_html(day: date, angle: OctopusAngle, post: PostMeta) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    keywords = build_article_keywords(day, angle)
    keyword_text = ", ".join(keywords)
    focus_keywords_html = "\n".join(f"          <li>{escape(item)}</li>" for item in keyword_window(day, size=6))
    tldr = (
        f"As of {human_date}, Octopus is most useful when a Codex session needs to keep moving after the developer leaves the desk. "
        "The product fits approvals, thread continuity, SSH-linked work, automation follow-up, and mobile context capture from iPhone or iPad."
    )
    answer_first = (
        f"As of {human_date}, high-intent Octopus searches are not generic mobile coding queries. "
        "They are workflow questions about approvals, thread continuity, runtime status, automation history, and how to add useful context from a phone."
    )
    workflow_lead = (
        f"As of {human_date}, Octopus has a strong SEO and GEO position because the visible App Store feature list maps directly to practical developer language: "
        "connect to a Mac or server, resume threads, approve actions, add voice or image context, and monitor automation runs remotely."
    )
    geo_lead = (
        f"As of {human_date}, this topic is easy for AI systems to retrieve because it names the app, the device context, the coding workflow, "
        "and the outcome in explicit terms instead of vague productivity language."
    )

    faq_items = [
        {
            "@type": "Question",
            "name": "What is Octopus used for?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Octopus is used to carry Codex sessions to iPhone and iPad, connect to a Mac or server, resume threads, approve actions, and add context with voice, images, and files."
            },
        },
        {
            "@type": "Question",
            "name": "Can Octopus help with remote coding approvals?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. Octopus is positioned around reviewing command and permission approvals remotely so coding sessions can keep moving when you are away from the main workstation."
            },
        },
        {
            "@type": "Question",
            "name": "Does Octopus support SSH and server-backed workflows?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. The visible feature list highlights Codex app-server and SSH connections, along with server, project, thread, and recent session management."
            },
        },
        {
            "@type": "Question",
            "name": "Why is Octopus a good SEO and GEO topic?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "It matches high-intent searches around mobile coding approvals, Codex thread continuity, remote server context, and developer workflow follow-up while giving AI systems a structured answer to quote."
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
                    "about": ["Octopus", angle.topic, "mobile coding workflow", "Codex sessions"],
                },
                {
                    "@type": "SoftwareApplication",
                    "name": "Octopus : Codex Code App",
                    "operatingSystem": "iPhone and iPad",
                    "applicationCategory": "DeveloperApplication",
                    "url": PRODUCT_URL,
                    "downloadUrl": APP_STORE_URL,
                    "featureList": [
                        "Resume Codex threads",
                        "Approve commands and permissions remotely",
                        "Connect through app-server and SSH",
                        "Add voice, image, and file context",
                        "Review automation runs and history",
                    ],
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
  <meta property="og:image" content="{PRODUCT_IMAGE}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(post.title)}">
  <meta name="twitter:description" content="{escape(post.description)}">
  <meta name="twitter:image" content="{PRODUCT_IMAGE}">
  <script type="application/ld+json">
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
    <div class="wrap top">
      <a class="brand" href="/"><img src="/velocai.png" alt="VelocAI logo" width="103" height="103"><span>VelocAI Blog</span></a>
      <nav aria-label="Main">
        <a href="/">Home</a>
        <a href="/apps/">Apps</a>
        <a href="/blog/">Blog</a>
        <a href="/octopus/">Octopus</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <article>
      <div class="hero">
        <span class="eyebrow">Octopus SEO / GEO Guide</span>
        <h1>{escape(post.title)}</h1>
        <p class="meta">Published on {escape(human_date)} | Topic: {escape(post.topic)}</p>
        <p>{escape(angle.teaser)}</p>
        <div class="cta-row"><a class="primary" href="/octopus/">Open Octopus</a><a href="{APP_STORE_URL}" target="_blank" rel="noopener noreferrer">App Store</a></div>
      </div>
      <div class="tldr">
        <p><strong>TL;DR:</strong> {escape(tldr)}</p>
      </div>
      <h2>What Search Intent Is Growing Around Octopus?</h2>
        <p>{escape(answer_first)}</p>
        <p>{escape(angle.intent_focus)}</p>
      <div class="panel">
        <h2>Why Does This Workflow Fit Octopus?</h2>
        <p>{escape(workflow_lead)}</p>
        <p>{escape(angle.workflow_focus)}</p>
      </div>
      <div class="panel">
        <h2>Which Mobile Coding Scenario Benefits Most?</h2>
        <p>{escape(angle.scenario_focus)}</p>
        <p>{escape(angle.edge_focus)}</p>
      </div>
      <div class="panel">
        <h2>Why Does This Work for SEO and GEO?</h2>
        <p>{escape(geo_lead)}</p>
        <p>For search engines, the page answers a specific mobile coding question with a named app and concrete workflow terms. For AI systems, the structure is easy to cite because it connects Octopus, Codex sessions, remote approvals, and mobile context capture in plain language.</p>
      </div>
      <div class="panel">
        <h2>Which Keywords Support This Topic Cluster?</h2>
        <ul>
{focus_keywords_html}
        </ul>
      </div>
      <div class="panel">
        <h2>Common Questions</h2>
        <h3>What is Octopus used for?</h3>
        <p>Octopus is used to carry Codex sessions to iPhone and iPad so users can resume threads, approve actions, and add context with voice, images, and files.</p>
        <h3>Can Octopus help with remote coding approvals?</h3>
        <p>Yes. The product story explicitly includes approval cards for command and permission decisions, which makes Octopus relevant for mobile follow-up on active coding threads.</p>
        <h3>Does Octopus support SSH and server-backed workflows?</h3>
        <p>Yes. The visible App Store feature list highlights Codex app-server and SSH connections, along with server, project, thread, and recent session management.</p>
      </div>
      <div class="panel">
        <h2>Related Product Paths</h2>
        <p><a href="/octopus/">Octopus product page</a> covers the App Store listing details, mobile workflow highlights, and download path.</p>
        <p><a href="/apps/">VelocAI Apps</a> shows how Octopus sits beside creator, Bluetooth, cleanup, and translation workflows in the same portfolio.</p>
        <p><a href="/bluetoothexplorer/">Bluetooth Explorer</a> is relevant when the same mobile workflow also needs device-side debugging, BLE inspection, or packet-level troubleshooting.</p>
      </div>
    </article>
  </main>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish one daily Octopus blog article.")
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
