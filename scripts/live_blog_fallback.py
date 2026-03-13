#!/usr/bin/env python3
"""Generate SEO/GEO-friendly blog fallback candidates from live news feeds."""

from __future__ import annotations

import json
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

LANE_ALLOWED_SOURCES = {
    "cleanup": {"Apple Newsroom", "MacRumors", "AppleInsider"},
    "protocol": {"Bluetooth SIG"},
    "updates": {"Bluetooth SIG", "Apple Newsroom", "MacRumors", "AppleInsider", "MacStories", "9to5Mac", "OpenAI News", "Tom's Hardware"},
}

APP_FUNCTION_KEYWORDS = {
    "cleanup": (
        "files",
        "storage",
        "backup",
        "back up",
        "icloud",
        "nas",
        "drive",
        "system data",
        "storage full",
        "free up storage",
    ),
    "find": (
        "airpods",
        "find my",
        "nearby",
        "lost",
        "location",
        "tracking",
        "recover",
        "bluetooth device",
        "device finding",
        "find nearby",
        "lost device",
    ),
    "bluetooth": (
        "bluetooth",
        "ble",
        "gatt",
        "auracast",
        "mesh",
        "device discovery",
        "bluetooth pairing",
        "rssi",
        "bluetooth signal",
    ),
}

CLEANUP_TITLE_REQUIRED = (
    "storage",
    "backup",
    "back up",
    "icloud",
    "files",
    "nas",
    "drive",
    "system data",
)

UPDATES_TITLE_REQUIRED = APP_FUNCTION_KEYWORDS["cleanup"] + APP_FUNCTION_KEYWORDS["find"] + APP_FUNCTION_KEYWORDS["bluetooth"]


def matches_keyword(text: str, keyword: str) -> bool:
    lowered = text.lower()
    term = keyword.lower()
    if " " in term:
        return term in lowered
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lowered) is not None


def json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


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


def teaser_for_source_slug(source_slug: str) -> str:
    if source_slug == "apple":
        return "A search-focused Apple commentary on new product features, performance tradeoffs, and upgrade relevance."
    if source_slug == "ai":
        return "A forward-looking AI commentary focused on model capability, workflow impact, and what changes next."
    return "A latest-info Bluetooth commentary focused on standards, applications, and practical deployment impact."


def keywords_for_source_slug(source_slug: str) -> list[str]:
    if source_slug == "apple":
        return [
            "find apple product changes",
            "cleanup iphone upgrade checklist",
            "bluetooth accessory compatibility iphone",
            "find iphone feature differences",
            "cleanup iphone storage before upgrade",
            "find mac performance changes",
        ]
    if source_slug == "ai":
        return [
            "find ai workflow changes",
            "find ai product updates",
            "cleanup ai automation workflow",
            "find ai model impact",
            "cleanup ai operations checklist",
            "find ai capability shifts",
        ]
    return [
        "bluetooth latest update",
        "bluetooth standards commentary",
        "bluetooth application analysis",
        "bluetooth industry outlook",
        "bluetooth feature update",
        "bluetooth product implications",
    ]


def strip_suffix(title: str, suffix: str) -> str:
    if title.endswith(suffix):
        return title[: -len(suffix)].rstrip(" :|-")
    return title


def rewritten_story_focus(source_slug: str, item: FeedItem) -> tuple[str, str]:
    raw = clean_text(item.title)
    lowered = raw.lower()
    if source_slug == "apple":
        if any(keyword in lowered for keyword in ("storage", "1tb", "128gb", "icloud", "backup", "files", "nas", "drive")):
            if "iphone" in lowered:
                return (
                    "iPhone storage planning: what AI Cleanup PRO users should notice",
                    "A rewritten Apple storage commentary that connects the update to cleanup planning, backup pressure, and real device storage workflows.",
                )
            if "mac" in lowered or "macbook" in lowered:
                return (
                    "Mac storage and backup planning: what AI Cleanup PRO users should notice",
                    "A rewritten Apple storage commentary that connects the update to file management, backup planning, and cleanup decisions on Mac.",
                )
            return (
                "Apple storage changes: what AI Cleanup PRO users should notice",
                "A rewritten Apple storage commentary focused on file growth, capacity planning, and cleanup implications.",
            )
        if any(keyword in lowered for keyword in ("airpods", "find my", "tracking", "location", "lost")):
            return (
                "Apple device-finding changes: what Find AI users should notice",
                "A rewritten Apple commentary focused on nearby finding, last-seen workflows, and recovery signals relevant to Find AI users.",
            )
        return (
            "Apple ecosystem changes: what Find AI users should notice",
            "A rewritten Apple commentary that connects the update to practical device-finding, accessory, or ecosystem workflows.",
        )
    if source_slug == "ai":
        if any(keyword in lowered for keyword in ("storage", "files", "nas", "drive", "backup")):
            return (
                "AI for file and storage workflows: what AI Cleanup PRO users should notice",
                "A rewritten AI commentary focused on how new models or tools affect cleanup, file handling, and storage-related workflows.",
            )
        if any(keyword in lowered for keyword in ("agent", "agents", "evals", "model", "chatgpt", "gpt", "reasoning")):
            return (
                "AI workflow changes: what Find AI users should notice",
                "A rewritten AI commentary that explains capability changes in terms of real automation, assistant, and user workflow impact.",
            )
        return (
            "AI workflow update: what Find AI users should notice",
            "A rewritten AI commentary focused on practical workflow change rather than headline-only release notes.",
        )
    if any(keyword in lowered for keyword in ("auracast", "broadcast audio")):
        return (
            "Bluetooth protocol for broadcast audio: what Bluetooth Explorer users should notice",
            "A rewritten Bluetooth protocol commentary focused on broadcast audio behavior, interoperability, and deployment value.",
        )
    if any(keyword in lowered for keyword in ("tracking", "monitoring", "industrial", "supply")):
        return (
            "Bluetooth protocol for tracking and monitoring: what Bluetooth Explorer users should notice",
            "A rewritten Bluetooth protocol commentary focused on discovery, telemetry, and industrial deployment workflows.",
        )
    if any(keyword in lowered for keyword in ("connection interval", "shorter connection intervals")):
        return (
            "Bluetooth protocol and shorter connection intervals: what Bluetooth Explorer users should notice",
            "A rewritten Bluetooth protocol commentary focused on latency, timing, and practical implementation impact.",
        )
    return (
        "Bluetooth protocol update: what Bluetooth Explorer users should notice",
        "A rewritten Bluetooth protocol commentary focused on practical implementation, debugging, and product impact.",
    )


def title_for_item(source_slug: str, item: FeedItem) -> str:
    return rewritten_story_focus(source_slug, item)[0]


def looks_garbled(value: str) -> bool:
    return any(ord(ch) > 127 for ch in value)


def clean_summary(source_slug: str, source_name: str, item: FeedItem) -> str:
    cleaned = clean_text(item.summary)
    if cleaned and not looks_garbled(cleaned):
        lowered = cleaned.lower()
        for marker in ("subscribe to", "discuss this article", "related roundup", "buyer's guide", "related forum", "this article,"):
            marker_index = lowered.find(marker)
            if marker_index > 0:
                cleaned = cleaned[:marker_index].strip()
                lowered = cleaned.lower()
        cleaned = cleaned.encode("ascii", "ignore").decode().strip()
        if cleaned:
            return clip_text(cleaned, limit=210)
    fallback = {
        "apple": f"Latest Apple product commentary from {source_name} focused on feature changes, performance impact, pricing position, and upgrade relevance.",
        "ai": f"Latest AI technology commentary from {source_name} focused on capability changes, product impact, and what teams should watch next.",
        "bluetooth": f"Latest Bluetooth commentary from {source_name} focused on standards changes, application impact, and what product teams should watch next.",
    }[source_slug]
    return fallback


def current_status_heading(source_slug: str) -> str:
    return {
        "apple": "Current Status: Apple Product Commentary Needs Feature and Performance Context",
        "ai": "Current Status: AI Release Analysis Needs Capability and Workflow Context",
        "bluetooth": "Current Status: Bluetooth Update Coverage Needs Standards and Application Context",
    }[source_slug]


def current_status_body(source_slug: str, source_name: str, source_published: str) -> str:
    return {
        "apple": f"As of {source_published}, Apple product coverage performs best when it explains feature changes, performance tradeoffs, repairability, pricing position, and ecosystem impact instead of repeating launch headlines. Source monitoring from {source_name} is most useful when it turns a new release into clear buyer and developer context.",
        "ai": f"As of {source_published}, AI release coverage performs best when it explains capability shifts, deployment implications, workflow impact, pricing or access changes, and what teams should test next. Source monitoring from {source_name} becomes more useful when it translates fast-moving AI news into practical product decisions.",
        "bluetooth": f"As of {source_published}, Bluetooth update coverage performs best when it explains what changed in standards, interoperability, applications, and deployment tradeoffs instead of repeating vendor claims. Source monitoring from {source_name} matters when it turns technical announcements into implementation context.",
    }[source_slug]


def opening_intro_for(source_slug: str, title: str, summary: str) -> str:
    return {
        "apple": f"This Apple feature and performance commentary examines {title} through the lens of product positioning, feature relevance, repairability, and real-world upgrade value. Instead of repeating a launch headline, the goal is to connect the update to practical buyer intent, developer implications, and the Apple ecosystem signals that matter most in 2026. {summary}",
        "ai": f"This AI technology outlook examines {title} through the lens of model capability, workflow impact, deployment relevance, and product strategy. Instead of repeating an announcement, the goal is to explain what changed, why it matters for builders and teams, and how the update fits the broader direction of AI products in 2026. {summary}",
        "bluetooth": f"This Bluetooth standards and application commentary examines {title} through the lens of interoperability, deployment impact, and product-level relevance. Instead of repeating a standards headline, the goal is to translate the update into practical Bluetooth implementation context for teams and readers in 2026. {summary}",
    }[source_slug]


def table_rows_for(source_slug: str) -> list[tuple[str, str, str]]:
    return {
        "apple": [
            ("Feature changes", "What Apple added, removed, or repositioned", "Helps readers understand the real scope of the update"),
            ("Performance angle", "Speed, battery, thermals, repairability, or component shifts", "Turns launch news into measurable product commentary"),
            ("Lineup fit", "Where the product sits against iPhone, iPad, Mac, or accessory tiers", "Improves upgrade and buying relevance"),
            ("Ecosystem impact", "Effect on developers, accessories, workflows, or services", "Adds practical value for SEO/GEO readers"),
        ],
        "ai": [
            ("Capability shift", "What changed in models, tools, or agent behavior", "Helps readers separate real progress from headline noise"),
            ("Workflow impact", "How the update affects coding, research, automation, or enterprise use", "Connects AI news to practical usage"),
            ("Access and deployment", "Availability, retirement, pricing, or rollout changes", "Improves decision quality for teams evaluating adoption"),
            ("Strategic outlook", "What this means for product roadmaps and competitive positioning", "Makes the article more useful than a news summary"),
        ],
        "bluetooth": [
            ("Standards update", "What changed in Bluetooth specs or ecosystem guidance", "Clarifies whether the update affects shipping products"),
            ("Application impact", "Where the change matters in discovery, audio, mesh, or telemetry", "Connects standards language to real deployments"),
            ("Compatibility risk", "What teams should test across firmware, chips, OS, and apps", "Improves technical usefulness"),
            ("Adoption outlook", "How quickly the change may influence products or infrastructure", "Adds planning value for readers"),
        ],
    }[source_slug]


def interpretation_heading_for(source_slug: str) -> str:
    return {
        "apple": "Feature Commentary",
        "ai": "Capability Commentary",
        "bluetooth": "Standards Commentary",
    }[source_slug]


def application_heading_for(source_slug: str) -> str:
    return {
        "apple": "Performance and Product Positioning",
        "ai": "Workflow and Product Implications",
        "bluetooth": "Application and Deployment Implications",
    }[source_slug]


def interpretation_body_for(source_slug: str, item: FeedItem, summary: str) -> str:
    title = clean_text(item.title)
    return {
        "apple": f"{title} should be read as more than a launch note. The real value comes from understanding which Apple product behaviors changed, what stayed the same, and whether the feature update improves everyday usage, serviceability, accessory fit, or long-term upgrade value. {summary} The strongest Apple feature analysis also asks whether the change improves camera, battery, thermals, portability, or the ecosystem fit that often decides whether an upgrade is worth it.",
        "ai": f"{title} should be read as more than an announcement. The key question is whether the update changes model capability, developer workflow, agent reliability, deployment planning, or the economics of using AI in production. {summary} The strongest AI model commentary also explains whether the release changes what teams can automate, what tradeoffs they inherit, and whether product quality or operating cost shifts in a meaningful way.",
        "bluetooth": f"{title} should be read in terms of standards meaning, interoperability, and application consequences. The main value comes from mapping the update to device discovery, audio, telemetry, power, or rollout decisions. {summary}",
    }[source_slug]


def application_body_for(source_slug: str) -> str:
    return {
        "apple": "Readers, buyers, and developers care most about where the new feature or performance change fits in the lineup. The strongest Apple commentary explains upgrade relevance, tradeoffs versus nearby products, and whether the change improves real workflows rather than only spec-sheet perception. It should also clarify who does not need the update, which compromises still remain, and whether the product changes the buying logic inside the current Apple range.",
        "ai": "Teams care most about what the release changes in real usage. The strongest AI commentary explains whether a new model, retirement, or capability shift changes product quality, automation design, safety posture, or cost decisions for actual teams. It should also clarify whether the update changes evaluation criteria, tool choice, model routing, or the practical balance between speed, quality, and operating cost.",
        "bluetooth": "Teams care most about where a standards or ecosystem update changes implementation reality. The strongest Bluetooth commentary explains whether the change affects reliability, compatibility, deployment timing, or product experience in a measurable way.",
    }[source_slug]


def next_heading_for(source_slug: str) -> str:
    return {
        "apple": "What To Watch Next",
        "ai": "What To Watch Next",
        "bluetooth": "What To Watch Next",
    }[source_slug]


def next_body_for(source_slug: str) -> str:
    return {
        "apple": "The next question is whether independent testing, teardowns, benchmarks, and real user feedback support the first wave of Apple product claims. Good Apple product commentary should track whether the feature or performance story remains compelling after launch-day attention fades, and whether accessories, developers, and the broader lineup reinforce or weaken the case for the update.",
        "ai": "The next question is whether this AI update changes evaluation baselines, pricing logic, deployment planning, or model choice in real products. Good AI technology outlook content should track how the release affects practical workloads, whether the capability gain holds up under real usage, and whether access, safety, or product integration changes what teams do next.",
        "bluetooth": "The next question is whether the update moves from standards language into practical implementation value. Good Bluetooth commentary should track vendor adoption, compatibility signals, firmware support, and whether the update changes deployment planning, interoperability, or product-level user experience.",
    }[source_slug]


def search_intent_heading_for(source_slug: str) -> str:
    return {
        "apple": "Search Intent and Upgrade Questions",
        "ai": "Search Intent and Adoption Questions",
        "bluetooth": "Search Intent and Deployment Questions",
    }[source_slug]


def search_intent_body_for(source_slug: str) -> str:
    return {
        "apple": "The highest-intent Apple searches usually ask whether a new device is worth buying, which features actually changed, how performance compares to nearby models, and whether the update changes the practical value of the product. That is why Apple feature commentary should answer upgrade questions directly, compare lineup position clearly, and translate hardware or software changes into everyday usage. Articles that do this well are easier for both search engines and AI systems to retrieve because they map user intent to explicit product answers instead of leaving readers with launch language alone.",
        "ai": "The highest-intent AI searches usually ask what changed in model capability, whether the release changes workflow quality, how pricing or access shifts affect adoption, and what teams should test next. That is why AI technology outlook content should answer capability questions directly, connect the release to real product usage, and explain whether the update changes development, automation, or enterprise decision-making. Articles that do this well are easier for both search engines and AI systems to retrieve because they convert technical release notes into clear next-step guidance.",
        "bluetooth": "The highest-intent Bluetooth searches usually ask what changed in the standard, where the update matters in applications, how interoperability is affected, and whether deployment plans should change. That is why Bluetooth commentary should answer implementation questions directly, show the application impact clearly, and explain what teams should validate next. Articles that do this well are easier for both search engines and AI systems to retrieve because they turn technical announcements into deployable, searchable guidance.",
    }[source_slug]


def checklist_items_for(source_slug: str) -> list[str]:
    return {
        "apple": [
            "Check which feature changed and whether it affects daily use or only positioning.",
            "Compare the update against the nearest Apple product tier before judging upgrade value.",
            "Look at repairability, battery, accessory, and software fit alongside performance.",
            "Separate headline launch excitement from long-term ownership impact.",
            "Use direct upgrade and comparison language so SEO/GEO readers get immediate answers.",
        ],
        "ai": [
            "Check whether the release changes real workflow quality or only expands model options.",
            "Compare pricing, access, and rollout details before assuming broad availability.",
            "Look at safety, reliability, and integration tradeoffs alongside capability claims.",
            "Separate benchmark headlines from deployment impact on real teams.",
            "Use direct adoption and next-step language so SEO/GEO readers get practical answers.",
        ],
        "bluetooth": [
            "Check whether the update changes standards language, implementation reality, or both.",
            "Compare application impact across discovery, audio, mesh, telemetry, and compatibility.",
            "Look at rollout timing and firmware support before assuming adoption.",
            "Separate feature headlines from deployment value in real products.",
            "Use direct implementation language so SEO/GEO readers get usable answers quickly.",
        ],
    }[source_slug]


def retrieval_fit_body_for(source_slug: str) -> str:
    return {
        "apple": "From an SEO and GEO perspective, Apple commentary works best when it contains the core product keyword in the title, repeats that intent naturally in the opening paragraph, and uses comparison-ready language throughout the article. Readers often search for feature reviews, performance analysis, and upgrade value at the same time, so the page should answer all three directly. That makes the article more retrievable for both traditional search and AI-assisted summary systems.",
        "ai": "From an SEO and GEO perspective, AI outlook articles work best when they state the model or release name clearly, explain the practical capability shift early, and repeat workflow-oriented long-tail phrases naturally through the article. Readers often search for capability analysis, deployment implications, and next-step guidance together, so the page should answer all three directly. That makes the article more retrievable for both traditional search and AI-assisted summary systems.",
        "bluetooth": "From an SEO and GEO perspective, Bluetooth commentary works best when it names the update clearly, explains the standards or application impact early, and repeats implementation-oriented long-tail phrases naturally through the article. Readers often search for standards meaning, interoperability implications, and deployment guidance together, so the page should answer all three directly. That makes the article more retrievable for both traditional search and AI-assisted summary systems.",
    }[source_slug]


def challenge_intro_for(source_slug: str) -> str:
    return {
        "apple": "Apple product coverage gets weak when it stays too close to launch marketing and fails to explain how the update changes buying logic or long-term usability.",
        "ai": "AI release coverage gets weak when it repeats headline capability claims and skips deployment tradeoffs, operational constraints, or workflow relevance.",
        "bluetooth": "Bluetooth update coverage gets weak when it repeats standards language without explaining what changes for product teams, users, or deployment planning.",
    }[source_slug]


def challenge_items_for(source_slug: str) -> list[str]:
    return {
        "apple": [
            "Launch headlines rarely explain lineup overlap clearly.",
            "Performance claims need workflow context, not just benchmark framing.",
            "Repairability, battery, and accessory impact are often underexplained.",
            "Naming and tiering can confuse users comparing adjacent Apple products.",
            "SEO/GEO value improves when commentary answers upgrade and buying questions directly.",
        ],
        "ai": [
            "Headline capability claims can overstate practical workflow impact.",
            "Model retirement or rollout changes often affect teams more than demos do.",
            "Access, pricing, and deployment details are easy to miss in fast AI coverage.",
            "Safety and reliability tradeoffs need to be stated directly for readers.",
            "SEO/GEO value improves when commentary answers what changes next for real users and builders.",
        ],
        "bluetooth": [
            "Standards language can hide what actually changes for shipping products.",
            "Compatibility and rollout risks are often more important than feature headlines.",
            "Application examples need to connect clearly to real device workflows.",
            "Teams need implementation context across chips, OS versions, and firmware.",
            "SEO/GEO value improves when commentary answers what the update changes in practice.",
        ],
    }[source_slug]


def geo_answers_for(source_slug: str) -> list[str]:
    return {
        "apple": [
            "Apple feature commentary should explain what changed, what stayed the same, and who should care.",
            "Apple performance analysis is strongest when it maps specs to real workflow impact.",
            "Apple lineup commentary should help readers compare nearby product tiers clearly.",
            "Repairability and accessory compatibility are practical parts of Apple product value.",
            "SEO/GEO coverage improves when Apple commentary answers buying and upgrade questions directly.",
        ],
        "ai": [
            "AI commentary should explain capability change, workflow impact, and deployment relevance together.",
            "Model retirement and rollout updates can matter more than benchmark headlines.",
            "AI product analysis is strongest when it connects releases to actual team decisions.",
            "Readers need clear explanation of pricing, access, safety, and integration tradeoffs.",
            "SEO/GEO coverage improves when AI articles answer what changed and what teams should do next.",
        ],
        "bluetooth": [
            "Bluetooth commentary should explain what changed in standards and what that means for applications.",
            "Application impact matters more than repeating technical labels without context.",
            "Deployment risk depends on compatibility across chips, firmware, apps, and operating systems.",
            "Readers need standards updates translated into product-level implications.",
            "SEO/GEO coverage improves when Bluetooth articles answer how the update affects real implementations.",
        ],
    }[source_slug]


def faq_items_for(source_slug: str) -> list[tuple[str, str]]:
    return {
        "apple": [
            ("How should readers evaluate a new Apple feature or performance claim?", "Compare the change against prior Apple products, then focus on real workflow impact such as speed, battery life, repairability, accessory fit, or software usefulness."),
            ("What makes Apple product commentary useful for SEO and GEO?", "Useful Apple commentary answers upgrade, comparison, and feature-impact questions directly, rather than repeating launch marketing language."),
            ("Why does product positioning matter in Apple coverage?", "Apple updates are easiest to evaluate when readers can see where the new feature or performance change fits across nearby iPhone, iPad, Mac, or accessory tiers."),
        ],
        "ai": [
            ("How should readers evaluate a new AI release or capability claim?", "Start with the primary source, then ask what changed in model behavior, workflow value, access, pricing, and deployment tradeoffs for real users or teams."),
            ("What makes AI technology outlook articles useful for SEO and GEO?", "Strong AI outlook articles answer capability, workflow, pricing, and adoption questions in clear language that search engines and AI systems can retrieve safely."),
            ("Why do AI launch notes need extra commentary?", "Because raw announcements rarely explain how the update affects product planning, automation design, or whether teams should change what they use next."),
        ],
        "bluetooth": [
            ("How should readers evaluate a new Bluetooth update or standards claim?", "Check the primary source, then focus on what changed in interoperability, applications, rollout timing, and compatibility risk for real products."),
            ("What makes Bluetooth commentary useful for SEO and GEO?", "Strong Bluetooth commentary translates technical updates into deployment, application, and troubleshooting context that search engines and AI systems can quote safely."),
            ("Why is application context important in Bluetooth coverage?", "Because standards updates only become useful when readers understand how they affect discovery, audio, mesh, telemetry, power, or product planning."),
        ],
    }[source_slug]


def render_live_article(day: date, source_slug: str, source_name: str, item: FeedItem, post: PostMeta) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    source_published = item.published_at.astimezone().strftime("%B %d, %Y") if item.published_at else human_date
    summary = clean_summary(source_slug, source_name, item)
    opening_intro = opening_intro_for(source_slug, clean_text(item.title), summary)
    keyword_coverage = keywords_for_source_slug(source_slug) + [slugify(item.title).replace("-", " ")]
    faq_items = faq_items_for(source_slug)
    challenge_items = challenge_items_for(source_slug)
    geo_answers = geo_answers_for(source_slug)
    table_rows = table_rows_for(source_slug)
    checklist_items = checklist_items_for(source_slug)

    table_html = "\n".join(
        f"          <tr><td>{escape(col1)}</td><td>{escape(col2)}</td><td>{escape(col3)}</td></tr>"
        for col1, col2, col3 in table_rows
    )
    keyword_html = "\n".join(f"          <li>{escape(item)}</li>" for item in keyword_coverage[:6])
    geo_html = "\n".join(f"          <li>{escape(item)}</li>" for item in geo_answers)
    challenge_html = "\n".join(f"          <li>{escape(item)}</li>" for item in challenge_items)
    checklist_html = "\n".join(f"          <li>{escape(item)}</li>" for item in checklist_items)
    faq_html = "\n".join(
        f"      <p><strong>{escape(question)}</strong><br>\n      {escape(answer)}</p>\n"
        for question, answer in faq_items
    )
    keywords = ", ".join(keyword_coverage)

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
      "mainEntityOfPage": {json_string(canonical)},
      "keywords": {json.dumps(keyword_coverage[:8], ensure_ascii=False)}
    }},
    {{
      "@type": "FAQPage",
      "mainEntity": [
        {json.dumps([{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_items], ensure_ascii=False)[1:-1]}
      ]
    }}
  ]
}}
  </script>
  <style>
    :root {{ --bg:#f4f9ff; --text:#1a2838; --muted:#4b6178; --line:#cfe0f1; --panel:#ffffff; --brand:#1d63c7; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Inter","Segoe UI",sans-serif; color:var(--text); background:radial-gradient(circle at 8% 2%, rgba(66,139,233,.18), transparent 34%), radial-gradient(circle at 88% -6%, rgba(47,195,170,.14), transparent 32%), var(--bg); line-height:1.72; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ width:min(920px, calc(100% - 34px)); margin:0 auto; }}
    header {{ border-bottom:1px solid var(--line); background:rgba(244,249,255,.92); }}
    .top {{ padding:14px 0; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }}
    nav {{ display:flex; gap:12px; flex-wrap:wrap; color:var(--muted); font-size:14px; }}
    nav a:hover {{ color:var(--text); }}
    main {{ padding:36px 0 56px; }}
    h1,h2,h3 {{ margin:0; line-height:1.22; }}
    h1 {{ font-size:clamp(30px, 4.2vw, 48px); max-width:24ch; }}
    h2 {{ margin-top:30px; font-size:clamp(24px, 3vw, 34px); }}
    p,li,td,th {{ color:#30475f; font-size:17px; }}
    ul,ol {{ padding-left:22px; }}
    .meta {{ margin-top:10px; color:var(--muted); font-size:14px; }}
    .hero, .panel, table {{ background:var(--panel); border:1px solid var(--line); border-radius:24px; }}
    .hero {{ padding:26px; box-shadow:0 14px 32px rgba(24,36,54,.05); }}
    .panel {{ margin-top:24px; padding:22px; box-shadow:0 14px 32px rgba(24,36,54,.05); }}
    table {{ width:100%; margin-top:24px; border-collapse:separate; border-spacing:0; overflow:hidden; }}
    th,td {{ padding:16px 18px; border-bottom:1px solid var(--line); text-align:left; }}
    tr:last-child td {{ border-bottom:none; }}
    th {{ color:var(--text); font-weight:700; background:rgba(29,99,199,.08); }}
    .links {{ margin-top:32px; display:flex; gap:14px; flex-wrap:wrap; color:var(--brand); font-weight:600; }}
  </style>
  <link rel="stylesheet" href="/assets/css/site-tools.css">
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
        <a href="/bluetoothexplorer/">Bluetooth Explorer</a>
      </nav>
    </div>
  </header>

  <main class="wrap">
    <article>
      <div class="hero">
        <h1>{escape(post.title)}</h1>
        <p class="meta">Published on {escape(human_date)} | Topic: {escape(post.topic)} | Source: {escape(source_name)}</p>
        <p>{escape(opening_intro)}</p>
      </div>

      <h2>{escape(current_status_heading(source_slug))}</h2>
      <p>{escape(current_status_body(source_slug, source_name, source_published))}</p>

      <table aria-label="{escape(post.topic)} commentary coverage">
        <thead>
          <tr><th>Commentary area</th><th>What it covers</th><th>Why it matters</th></tr>
        </thead>
        <tbody>
{table_html}
        </tbody>
      </table>

      <h2>{escape(interpretation_heading_for(source_slug))}</h2>
      <p>{escape(interpretation_body_for(source_slug, item, summary))}</p>

      <h2>{escape(application_heading_for(source_slug))}</h2>
      <p>{escape(application_body_for(source_slug))}</p>

      <h2>{escape(next_heading_for(source_slug))}</h2>
      <p>{escape(next_body_for(source_slug))}</p>

      <h2>{escape(search_intent_heading_for(source_slug))}</h2>
      <p>{escape(search_intent_body_for(source_slug))}</p>

      <div class="panel">
        <h2>Challenges in 2026</h2>
        <p>{escape(challenge_intro_for(source_slug))}</p>
        <ol>
{challenge_html}
        </ol>
      </div>

      <div class="panel">
        <h2>Practical Decision Checklist</h2>
        <ul>
{checklist_html}
        </ul>
      </div>

      <div class="panel">
        <h2>SEO and GEO Retrieval Fit</h2>
        <p>{escape(retrieval_fit_body_for(source_slug))}</p>
      </div>

      <div class="panel">
        <h2>High-intent keyword coverage</h2>
        <ul>
{keyword_html}
        </ul>
      </div>

      <div class="panel">
        <h2>GEO answer blocks for AI retrieval</h2>
        <ul>
{geo_html}
        </ul>
      </div>

      <h2>FAQ</h2>
{faq_html}
      <section class="sources" aria-label="Source attribution">
        <h2>Source attribution</h2>
        <ul>
          <li><a href="{escape(item.link)}" target="_blank" rel="noopener noreferrer">{escape(source_name)}: {escape(clean_text(item.title))}</a></li>
        </ul>
      </section>

      <div class="links">
        <a href="/blog/">Back to blog index</a>
        <a href="/apps/">Browse VelocAI apps</a>
      </div>
    </article>
  </main>
  <script src="/assets/js/site-tools.js" defer></script>
</body>
</html>
"""


def build_candidate_from_item(
    target_day: date,
    source_slug: str,
    source_name: str,
    item: FeedItem,
    *,
    filename: str | None = None,
) -> LiveBlogCandidate:
    resolved_filename = filename or f"{article_prefix_for_source_slug(source_slug)}-{slugify(item.title)}-{target_day.isoformat()}.html"
    title, rewritten_summary = rewritten_story_focus(source_slug, item)
    summary = rewritten_summary if rewritten_summary else clean_summary(source_slug, source_name, item)
    opening_intro = opening_intro_for(source_slug, clean_text(item.title), summary)
    post = PostMeta(
        filename=resolved_filename,
        title=title,
        description=summary,
        teaser=clip_text(opening_intro, limit=160),
        topic=topic_for_source_slug(source_slug),
        published_iso=target_day.isoformat(),
    )
    html = render_live_article(target_day, source_slug, source_name, item, post)
    return LiveBlogCandidate(post=post, html=html, link=item.link, source_name=source_name)


def unique_feed_items_for_lane(lane: str) -> list[tuple[str, str, FeedItem]]:
    preferred_slugs = {
        "cleanup": ("apple",),
        "protocol": ("bluetooth",),
        "updates": ("apple", "ai", "bluetooth"),
    }[lane]
    collected: list[tuple[str, str, FeedItem]] = []
    seen_links: set[str] = set()
    for slug in preferred_slugs:
        sources = [
            source
            for source in BRIEF_SOURCES
            if source.slug == slug and source.source_name in LANE_ALLOWED_SOURCES[lane]
        ]
        for source in sources:
            try:
                items = parse_feed_items(fetch_bytes(source.feed_url))
            except Exception:
                continue
            for item in items:
                haystack = clean_text(item.title).lower()
                if lane == "cleanup":
                    required = CLEANUP_TITLE_REQUIRED
                elif lane == "updates":
                    required = UPDATES_TITLE_REQUIRED
                else:
                    required = APP_FUNCTION_KEYWORDS["bluetooth"] + APP_FUNCTION_KEYWORDS["find"]
                if not any(matches_keyword(haystack, keyword) for keyword in required):
                    continue
                padded_title = f" {clean_text(item.title).lower()} "
                if any(pattern in padded_title for pattern in NOISE_PATTERNS):
                    continue
                if score_item(item, source.keywords) <= 0:
                    continue
                if not item.link or item.link in seen_links:
                    continue
                seen_links.add(item.link)
                collected.append((slug, source.source_name, item))
    collected.sort(key=lambda entry: entry[2].published_at.timestamp() if entry[2].published_at else 0.0, reverse=True)
    return collected


def build_live_candidates(target_day: date, lane: str) -> list[LiveBlogCandidate]:
    return [
        build_candidate_from_item(target_day, source_slug, source_name, item)
        for source_slug, source_name, item in unique_feed_items_for_lane(lane)
    ]
