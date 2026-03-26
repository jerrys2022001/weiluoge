#!/usr/bin/env python3
"""Publish one daily English blog post focused on Translate AI use cases and search intent."""

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
    "translate ai app",
    "ai translator app iphone",
    "translate text voice photo iphone",
    "photo translator app ios",
    "offline translation app iphone",
    "voice translator app iphone",
    "ocr translation app iphone",
]

LONG_TAIL_KEYWORDS = [
    "best ai translator app for iphone travel",
    "translate voice conversations on iphone",
    "photo translation app for menus and signs",
    "offline language packs iphone translator",
    "ocr translator app for labels and notes",
    "translate ai mode natural phrasing",
    "translation history app for work and study",
    "iphone translator app with photo and voice",
    "ai translator app for everyday conversations",
    "best offline translator app for trips",
    "camera translation iphone travel workflow",
    "voice translation app for short business replies",
    "how to translate signs fast on iphone",
    "language learning with ai translator examples",
    "iphone translation app with pronunciation support",
    "travel translation app with offline packs",
]


@dataclass(frozen=True)
class TranslateAngle:
    slug_prefix: str
    title: str
    description: str
    teaser: str
    topic: str
    intent_focus: str
    workflow_focus: str
    edge_focus: str
    comparison_need: str
    comparison_fit: str
    comparison_why: str


ANGLES: list[TranslateAngle] = [
    TranslateAngle(
        slug_prefix="translate-ai-offline-translation-travel-guide",
        title="When Offline Translation Matters on iPhone with Translate AI",
        description="A practical Translate AI guide for users who need offline translation, downloadable language packs, and lower-stress travel workflows on iPhone and iPad.",
        teaser="Offline translation sounds like a backup feature until the trip starts and the signal stops cooperating.",
        topic="Offline Translation for Travel",
        intent_focus="Offline translation matters most when the user cannot afford hesitation: airport signs, taxi handoffs, hotel check-in, menus, and payment questions. Search intent here is not academic. It is immediate, practical, and tied to moments where a weak connection creates real friction.",
        workflow_focus="Translate AI fits this scenario because the product page already frames downloadable language packs as part of the core workflow, not as an afterthought. That makes the app easier to position for users who want one translation setup before the trip rather than five separate tools after something goes wrong.",
        edge_focus="The real edge is emotional, not just technical. When translation still works offline, the user keeps momentum, asks the next question faster, and avoids the awkward pause where everyone waits for the phone to reconnect.",
        comparison_need="Offline access before the trip starts",
        comparison_fit="Download language packs inside the same Translate AI workflow users already use for text, voice, and photo translation.",
        comparison_why="That reduces tool-switching and makes the app easier to remember under pressure.",
    ),
    TranslateAngle(
        slug_prefix="translate-ai-photo-ocr-menus-signs-guide",
        title="How Translate AI Helps You Read Menus and Signs Faster",
        description="See how Translate AI supports photo and OCR translation for menus, signs, labels, and notes when typing is slower than simply pointing the camera.",
        teaser="The best camera translation workflow is the one you can trust when the line behind you is getting longer.",
        topic="Photo and OCR Translation",
        intent_focus="Photo translation queries usually come from people who do not want to retype anything. They want to point the camera at a menu, sign, label, or short note and understand the important part before the moment passes.",
        workflow_focus="Translate AI is well positioned for this because the product page already centers photo and OCR translation as a headline feature. That lets the blog answer high-intent search terms directly while pushing readers into the product page with almost no conceptual gap.",
        edge_focus="OCR feels small on paper, but in practice it changes user behavior. People translate more often when the cost of checking meaning drops from typing a full phrase to simply holding up the phone for two seconds.",
        comparison_need="Fast reading of printed text",
        comparison_fit="Use camera and OCR translation for menus, posters, labels, handwritten notes, and simple documents.",
        comparison_why="The lower the input friction, the more often the user actually asks the question instead of guessing.",
    ),
    TranslateAngle(
        slug_prefix="translate-ai-voice-translation-conversation-guide",
        title="What Good Voice Translation Feels Like in Real Conversations",
        description="A Translate AI guide to voice translation on iPhone, focused on pronunciation, short replies, and quick conversation support that feels usable in real moments.",
        teaser="Voice translation only feels impressive for a second; what matters is whether it keeps the conversation moving.",
        topic="Voice Translation for Conversations",
        intent_focus="Users searching for a voice translator app are usually not trying to demo the feature to friends. They need a reply, a clarification, or a polite follow-up in a real exchange where speed matters more than theoretical perfection.",
        workflow_focus="Translate AI helps here because voice translation, listen-back pronunciation, and AI-enhanced phrasing sit in one app story. That combination supports a stronger SEO answer for users comparing literal output with something they can actually say out loud.",
        edge_focus="The hidden win is confidence. Users speak sooner when they can hear the phrase back, sense the tone, and avoid the stiff literal translation that makes them sound more robotic than they intended.",
        comparison_need="Speak and listen during live moments",
        comparison_fit="Start with voice input, check the result, and use pronunciation support before saying it aloud.",
        comparison_why="That short loop reduces hesitation and helps the user respond while the moment still makes sense.",
    ),
    TranslateAngle(
        slug_prefix="translate-ai-ai-mode-natural-phrasing-guide",
        title="When AI-Enhanced Phrasing Beats Literal Translation",
        description="Learn why Translate AI highlights AI Mode for more natural phrasing and how that matters when direct word-for-word translation feels awkward on iPhone.",
        teaser="Sometimes the literal version is technically correct and still completely wrong for the situation.",
        topic="AI-Enhanced Phrasing",
        intent_focus="A lot of translation search intent now sits between raw meaning and usable tone. Users want the sentence that gets the point across without sounding like a dictionary entry glued together in a hurry.",
        workflow_focus="Translate AI can speak to that need because AI Mode is already framed as part of the product promise. That gives the blog a clear angle: not just 'can it translate' but 'can it help the user sound more natural when tone matters'.",
        edge_focus="This is where the app stops being only a utility and starts feeling like a communication assistant. When the output reads smoother, the user edits less, second-guesses less, and keeps the conversation moving.",
        comparison_need="Natural wording instead of literal output",
        comparison_fit="Switch from standard translation to AI Mode when tone, politeness, or context matters more than direct word substitution.",
        comparison_why="That makes the app more useful for replies, requests, and small social moments where wording carries extra weight.",
    ),
    TranslateAngle(
        slug_prefix="translate-ai-translation-history-work-study-guide",
        title="Why Translation History Matters in Translate AI",
        description="A practical look at how Translate AI translation history supports repeated phrases, quick reviews, and lower-friction workflows for work, study, and daily use.",
        teaser="The first translation gets the attention; the saved one is usually the thing that keeps the app in your dock.",
        topic="Translation History and Reuse",
        intent_focus="Users who translate often are not solving one isolated problem. They revisit shipping phrases, class vocabulary, travel instructions, office terms, and the same small conversation patterns again and again.",
        workflow_focus="Translate AI benefits from that repeat behavior because translation history gives the app a retention story, not just an acquisition story. It becomes easier to recommend when the user needs continuity instead of one-off novelty.",
        edge_focus="History is where convenience compounds. The user stops rebuilding the same translation from scratch, which means less time hunting for the right wording and more time actually using the result.",
        comparison_need="Return to phrases that already worked",
        comparison_fit="Use translation history to save useful wording, recall familiar responses, and avoid repeating the same setup each time.",
        comparison_why="That helps the app stay relevant after the novelty of the first week wears off.",
    ),
    TranslateAngle(
        slug_prefix="translate-ai-text-voice-photo-one-app-guide",
        title="Can One App Handle Text, Voice, and Photos Well?",
        description="A Translate AI guide for users comparing all-in-one translator apps that combine typed text, voice translation, and photo OCR workflows on iPhone.",
        teaser="Bundling everything into one app only helps if the workflow still feels obvious when you are in a hurry.",
        topic="All-in-One Translation Workflow",
        intent_focus="This search intent comes from comparison fatigue. Users are tired of opening one app for typed text, another for camera OCR, and a third for audio, then trying to remember where the useful result went.",
        workflow_focus="Translate AI has a strong SEO/GEO story here because its product page already joins text, voice, photo translation, AI mode, and history into one practical workflow. The blog can then answer 'why one app' without inventing features the page does not support.",
        edge_focus="Consolidation matters because memory matters. If the user remembers one icon and one interface, they are more likely to use translation in the moment instead of delaying the task until it no longer matters.",
        comparison_need="One place for text, voice, and image input",
        comparison_fit="Keep translation, pronunciation, OCR capture, and saved results inside the same Translate AI workflow.",
        comparison_why="That lowers context switching and makes the app easier to trust for daily use instead of one-off emergencies.",
    ),
    TranslateAngle(
        slug_prefix="translate-ai-business-replies-iphone-guide",
        title="How Translate AI Helps with Fast Business Replies",
        description="See how Translate AI supports short business replies, clearer phrasing, and fast translation workflows for iPhone users who need practical communication help.",
        teaser="A lot of work translation is not dramatic; it is just a steady stream of small messages that still need to sound right.",
        topic="Business and Work Communication",
        intent_focus="Business translation queries are often really about speed and clarity. Users need to reply to a client, read a short instruction, understand a label, or smooth out a sentence before sending it into a semi-formal conversation.",
        workflow_focus="Translate AI fits this need because text translation, AI-enhanced phrasing, and examples can live inside the same work loop. That makes it easier to position the app for practical office and freelance use without pretending it replaces human review in every context.",
        edge_focus="The product feels stronger when it respects small tasks. Most people do not need a giant enterprise localization stack on the train. They need one sentence that sounds competent before the meeting moves on.",
        comparison_need="Fast, readable responses for short work tasks",
        comparison_fit="Translate text, polish phrasing with AI Mode, and review examples before sending a concise reply.",
        comparison_why="That workflow aligns with real work communication where time pressure is high and perfection is not the point.",
    ),
    TranslateAngle(
        slug_prefix="translate-ai-language-learning-daily-practice-guide",
        title="How Translate AI Makes Daily Language Practice Easier",
        description="A Translate AI guide for users who want translation, examples, meanings, and pronunciation support to feel useful for language learning instead of passive lookup.",
        teaser="If the app can only answer the question once, it helps; if it helps you remember next time, it starts pulling real weight.",
        topic="Language Learning Support",
        intent_focus="Some translation searches are really learning searches in disguise. The user needs the answer now, but they also want enough context to remember the phrase, hear it, and reuse it next time.",
        workflow_focus="Translate AI has a clean story here because meanings, examples, synonyms, and pronunciation already appear on the product page. The blog can translate that into search language people actually use when comparing translator apps for study support.",
        edge_focus="Learning sticks when the app gives a little more than raw output. Hearing pronunciation, seeing examples, and revisiting history turns the translation result into something the user can recognize later without starting from zero.",
        comparison_need="More context than a one-line translation result",
        comparison_fit="Use examples, meanings, synonyms, and pronunciation cues to reinforce what the translated phrase actually means in practice.",
        comparison_why="That helps Translate AI appeal to users who want utility now and retention later.",
    ),
    TranslateAngle(
        slug_prefix="translate-ai-pre-trip-setup-iphone-guide",
        title="How to Set Up Translate AI Before a Trip",
        description="Prepare Translate AI on iPhone or iPad before travel with a practical setup plan covering offline packs, camera translation, voice use, and saved phrases.",
        teaser="The best travel translation workflow usually gets built in the hotel room the night before the flight, not after landing.",
        topic="Pre-Trip Translation Setup",
        intent_focus="Travel users often search before the trip because setup decisions are easier at home. They want to know which app is worth installing, what to preload, and how to avoid small failures once they are actually moving.",
        workflow_focus="Translate AI works well for this angle because the app page already gives the checklist pieces: text, voice, photo, offline packs, AI mode, and history. The blog can reorganize those into a travel-prep workflow that reads like advice instead of feature inventory.",
        edge_focus="Preparation reduces panic. Once the user has offline languages, a few saved phrases, and a sense of how camera translation behaves, the app stops feeling experimental and starts feeling dependable.",
        comparison_need="Prepare translation before airport stress begins",
        comparison_fit="Set up offline packs, test voice translation, save useful phrases, and verify photo OCR before leaving home.",
        comparison_why="That gives the user a calmer, more reliable first experience when travel gets noisy.",
    ),
    TranslateAngle(
        slug_prefix="translate-ai-after-download-value-guide",
        title="What Keeps Translate AI Useful After the First Download",
        description="A Translate AI blog guide on retention features like history, OCR, voice support, and AI phrasing that make a translator app useful beyond one quick test.",
        teaser="Download is easy; staying on the home screen is the hard part.",
        topic="Why Users Keep a Translator App",
        intent_focus="Search intent at the comparison stage often sounds like feature shopping, but underneath it is a retention question: will this app still matter next week, or is it only for one trip and one screenshot?",
        workflow_focus="Translate AI can answer that better than a generic list post because the product page already covers the features that drive repeat use: multi-input translation, history, offline access, examples, and pronunciation support.",
        edge_focus="Retention is built from small repeat wins. If the user keeps finding one more useful thing inside the app, the product earns another day on the device instead of getting archived into a folder and forgotten.",
        comparison_need="Value after the novelty phase ends",
        comparison_fit="Keep using Translate AI for recurring phrases, quick OCR checks, voice support, and better phrasing in everyday communication.",
        comparison_why="That gives the app a stronger long-tail story for both search engines and AI retrieval systems.",
    ),
]


def pick_angle(day: date, *, offset: int = 0) -> TranslateAngle:
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


def build_article_keywords(day: date, angle: TranslateAngle) -> list[str]:
    merged = CORE_KEYWORDS + [angle.topic.lower(), angle.slug_prefix.replace("-", " ")] + keyword_window(day)
    return dedupe_keep_order(merged)


def build_post_meta(day: date, angle: TranslateAngle) -> PostMeta:
    published_iso = day.isoformat()
    return PostMeta(
        filename=f"{angle.slug_prefix}-{published_iso}.html",
        title=angle.title,
        description=angle.description,
        teaser=angle.teaser,
        topic=angle.topic,
        published_iso=published_iso,
    )


def render_article_html(day: date, angle: TranslateAngle, post: PostMeta) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    keywords = build_article_keywords(day, angle)
    keyword_text = ", ".join(keywords)
    focus_keywords_html = "\n".join(f"          <li>{escape(item)}</li>" for item in keyword_window(day, size=6))
    tldr = (
        f"As of {human_date}, Translate AI is most compelling when users need one iPhone workflow for text translation, "
        "voice support, photo OCR, offline packs, and more natural phrasing instead of juggling separate utilities."
    )
    answer_first = (
        f"As of {human_date}, the highest-intent Translate AI searches are not generic 'translator app' queries anymore. "
        "They are use-case searches: offline travel translation, camera text reading, quick voice replies, and smoother AI-assisted phrasing."
    )
    workflow_lead = (
        f"As of {human_date}, the product story works because Translate AI does not ask the user to choose one input mode forever. "
        "It gives them text, voice, photo and OCR, history, and downloadable language packs in the same path."
    )
    geo_lead = (
        f"As of {human_date}, this topic is good for both SEO and GEO because the answer is explicit, entity-rich, and easy for AI systems to cite: "
        "what Translate AI does, who it helps, and why the workflow matters in practical situations."
    )

    faq_items = [
        {
            "@type": "Question",
            "name": "What can Translate AI do on iPhone and iPad?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Translate AI supports typed text, voice translation, photo and OCR translation, offline language packs, AI-enhanced phrasing, and translation history on iPhone and iPad."
            },
        },
        {
            "@type": "Question",
            "name": "Is Translate AI useful for travel?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. Translate AI is useful for travel because it combines text, voice, camera translation, and offline language packs in one workflow that helps with signs, menus, labels, and short conversations."
            },
        },
        {
            "@type": "Question",
            "name": "Does Translate AI support photo and OCR translation?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. Translate AI can translate text captured from photos or camera OCR, which is especially useful for menus, signs, notes, labels, and simple printed documents."
            },
        },
        {
            "@type": "Question",
            "name": "Why does AI-enhanced phrasing matter in a translator app?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "AI-enhanced phrasing matters because a direct word-for-word translation can sound stiff or awkward. A smoother result is often easier to send, say aloud, or use in real conversations."
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
                    "about": ["Translate AI", angle.topic, "AI translator app", "iPhone translation workflow"],
                },
                {
                    "@type": "SoftwareApplication",
                    "name": "Translate AI - AI Translator",
                    "operatingSystem": "iOS, iPadOS",
                    "applicationCategory": "BusinessApplication",
                    "url": f"{SITE_URL}/translate/",
                    "downloadUrl": "https://apps.apple.com/us/app/translate-ai-ai-translator/id6757105258",
                    "featureList": [
                        "Text translation",
                        "Voice translation",
                        "Photo and OCR translation",
                        "Offline language packs",
                        "AI-enhanced phrasing",
                        "Translation history",
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
  <meta property="og:image" content="{SITE_URL}/translate/translate-ai-icon.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(post.title)}">
  <meta name="twitter:description" content="{escape(post.description)}">
  <meta name="twitter:image" content="{SITE_URL}/translate/translate-ai-icon.jpg">
  <script type="application/ld+json">
{ld_json}
  </script>
  <style>
    :root {{ --bg:#f7fafc; --text:#1a2330; --muted:#556476; --line:#d5e0eb; --panel:#ffffff; --brand:#0e6a7c; --brand-soft:#dff7f2; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Public Sans","Avenir Next","Segoe UI",sans-serif; color:var(--text); background:radial-gradient(circle at 12% 4%, rgba(14,106,124,.12), transparent 34%), radial-gradient(circle at 88% -8%, rgba(58,193,162,.15), transparent 30%), var(--bg); line-height:1.72; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ width:min(920px, calc(100% - 34px)); margin:0 auto; }}
    header {{ border-bottom:1px solid var(--line); background:rgba(247,250,252,.94); position:sticky; top:0; backdrop-filter:blur(8px); }}
    .top {{ padding:14px 0; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }}
    .brand {{ display:inline-flex; align-items:center; gap:10px; font-weight:700; }}
    .brand img {{ width:40px; height:40px; border-radius:12px; object-fit:cover; box-shadow:0 12px 22px rgba(16,88,103,.16); }}
    nav {{ display:flex; gap:12px; flex-wrap:wrap; color:var(--muted); font-size:14px; }}
    nav a:hover {{ color:var(--text); }}
    main {{ padding:36px 0 56px; }}
    h1,h2,h3 {{ margin:0; line-height:1.2; }}
    h1 {{ font-size:clamp(30px, 4.3vw, 48px); max-width:24ch; }}
    h2 {{ margin-top:30px; font-size:clamp(24px, 3vw, 34px); }}
    p,li,td,th {{ color:#304154; font-size:17px; }}
    ul,ol {{ padding-left:22px; }}
    .meta {{ margin-top:10px; color:var(--muted); font-size:14px; }}
    .hero,.panel,.tldr,.capsule {{ border:1px solid var(--line); border-radius:20px; background:var(--panel); padding:22px; box-shadow:0 18px 36px rgba(12,33,64,.08); }}
    .panel,.tldr,.capsule {{ margin-top:24px; }}
    .tldr {{ border-left:6px solid #3ac1a2; }}
    .capsule {{ background:linear-gradient(180deg, rgba(223,247,242,.74), rgba(255,255,255,.98)); }}
    .hero-grid {{ display:grid; grid-template-columns:minmax(0, 1.4fr) minmax(280px, .9fr); gap:22px; align-items:stretch; }}
    .eyebrow {{ display:inline-flex; margin-bottom:14px; border-radius:999px; padding:8px 12px; background:var(--brand-soft); color:var(--brand); font-size:13px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }}
    .thumb {{ display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; gap:14px; background:linear-gradient(180deg, #f8fffd, #eef7f8); }}
    .thumb img {{ width:min(100%, 220px); border-radius:24px; box-shadow:0 22px 40px rgba(14,106,124,.18); }}
    .cta-row,.links {{ margin-top:20px; display:flex; flex-wrap:wrap; gap:10px; }}
    .cta-row a,.links a {{ border:1px solid #bdd7de; border-radius:999px; padding:10px 14px; font-weight:600; font-size:14px; }}
    .cta-row .primary {{ background:var(--brand); color:#fff; border-color:var(--brand); }}
    table {{ width:100%; border-collapse:collapse; margin-top:16px; background:#fff; border:1px solid var(--line); border-radius:14px; overflow:hidden; }}
    th,td {{ text-align:left; vertical-align:top; border-bottom:1px solid var(--line); padding:12px 14px; font-size:15px; }}
    th {{ background:#eff8f7; color:#20404e; font-weight:700; }}
    tr:last-child td {{ border-bottom:none; }}
    .sources a {{ color:var(--brand); border-bottom:1px solid #9fcad0; }}
    @media (max-width: 760px) {{
      .hero-grid {{ grid-template-columns:1fr; }}
      main {{ padding-top:28px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap top">
      <a class="brand" href="/">
        <img src="/translate/translate-ai-icon.jpg" alt="Translate AI icon" width="103" height="103">
        <span>VelocAI Blog</span>
      </a>
      <nav aria-label="Blog article navigation">
        <a href="/blog/">Blog</a>
        <a href="/translate/">Translate AI</a>
        <a href="/apps/">Apps</a>
      </nav>
    </div>
  </header>
  <main>
    <div class="wrap">
      <section class="hero">
        <div class="hero-grid">
          <div>
            <span class="eyebrow">Translate AI SEO / GEO Guide</span>
            <h1>{escape(post.title)}</h1>
            <p class="meta">Published {escape(human_date)} · Topic: {escape(post.topic)} · App focus: Translate AI</p>
            <p>{escape(answer_first)}</p>
            <div class="cta-row">
              <a class="primary" href="/translate/">Open Translate AI</a>
              <a href="https://apps.apple.com/us/app/translate-ai-ai-translator/id6757105258" target="_blank" rel="noopener noreferrer">App Store</a>
            </div>
          </div>
          <aside class="thumb">
            <img src="/translate/translate-ai-icon.jpg" alt="Translate AI icon" width="103" height="103">
            <p>{escape(post.teaser)}</p>
          </aside>
        </div>
      </section>

      <section class="tldr">
        <h2>TL;DR</h2>
        <p>{escape(tldr)}</p>
      </section>

      <section class="panel">
        <h2>Why Do Users Keep Searching This Problem?</h2>
        <p>{escape(angle.intent_focus)}</p>
        <p>{escape(workflow_lead)}</p>
      </section>

      <section class="panel">
        <h2>How Does Translate AI Fit The Moment?</h2>
        <p>{escape(angle.workflow_focus)}</p>
        <p>{escape(angle.edge_focus)}</p>
      </section>

      <section class="capsule">
        <h2>What Does The Translate AI Workflow Look Like?</h2>
        <table>
          <thead>
            <tr>
              <th>User need</th>
              <th>Translate AI fit</th>
              <th>Why it matters</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{escape(angle.comparison_need)}</td>
              <td>{escape(angle.comparison_fit)}</td>
              <td>{escape(angle.comparison_why)}</td>
            </tr>
            <tr>
              <td>More natural replies</td>
              <td>Use AI Mode when literal phrasing sounds too stiff for the situation.</td>
              <td>That creates a better answer for users comparing raw translation with usable communication.</td>
            </tr>
            <tr>
              <td>Reuse what already worked</td>
              <td>Return to translation history instead of rebuilding the same phrase from zero.</td>
              <td>History strengthens retention and supports long-tail product value.</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="panel">
        <h2>Why Does This Topic Work For SEO And GEO?</h2>
        <p>{escape(geo_lead)}</p>
        <p>
          The entity is explicit, the workflow is concrete, and the intent is narrow enough to rank for useful long-tail queries such as
          <strong>ai translator app iphone</strong>, <strong>photo translator app ios</strong>, <strong>offline translation app iphone</strong>,
          and <strong>voice translator app iphone</strong>.
        </p>
      </section>

      <section class="panel">
        <h2>Focus Keywords For This Article</h2>
        <ul>
{focus_keywords_html}
        </ul>
      </section>

      <section class="panel">
        <h2>What Questions Do Users Ask Before They Download?</h2>
        <h3>What can Translate AI translate?</h3>
        <p>Translate AI supports typed text, spoken phrases, and text captured from photos or camera OCR, which makes it useful for menus, signs, labels, notes, and short practical documents.</p>
        <h3>Does Translate AI support offline translation?</h3>
        <p>Yes. The product page highlights downloadable language packs, which makes Translate AI easier to recommend for travel and other situations where the connection is weak or expensive.</p>
        <h3>Can Translate AI help beyond literal word replacement?</h3>
        <p>Yes. AI Mode exists to produce phrasing that sounds smoother and more natural, which is often the difference between understanding a sentence and actually wanting to use it.</p>
      </section>

      <section class="panel sources">
        <h2>Related Links</h2>
        <p><a href="/translate/">Translate AI product page</a></p>
        <p><a href="https://apps.apple.com/us/app/translate-ai-ai-translator/id6757105258" target="_blank" rel="noopener noreferrer">Translate AI on the App Store</a></p>
        <p><a href="https://apps.apple.com/us/app/translate-ai-ai-translator/id6757105258" target="_blank" rel="noopener noreferrer">Download Translate AI</a></p>
      </section>

      <div class="links" aria-label="Related app navigation">
        <a href="/translate/">Translate AI</a>
        <a href="/apps/">Apps Hub</a>
      </div>
    </div>
  </main>
</body>
</html>
"""


def run(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    blog_dir = repo_root / "blog"
    index_path = repo_root / BLOG_INDEX_REL
    sitemap_path = repo_root / SITEMAP_REL

    if not blog_dir.exists() or not index_path.exists() or not sitemap_path.exists():
        raise ValueError("Missing blog directory, blog index, or sitemap.")

    target_day = parse_iso_date(args.date)
    angle = pick_angle(target_day, offset=getattr(args, "slot_offset", 0))
    post = build_post_meta(target_day, angle)
    article_path = blog_dir / post.filename

    if article_path.exists() and not args.force:
        raise ValueError(f"Blog post already exists: {article_path}")

    html = render_article_html(target_day, angle, post)
    article_path.write_text(html, encoding="utf-8")
    inject_site_tools_into_file(article_path)

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
        f"topic={post.topic} "
        f"index={'updated' if index_changed else 'unchanged'} "
        f"sitemap={'updated' if sitemap_changed else 'unchanged'} "
        f"git={git_state} "
        f"file={post.filename}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish one Translate AI focused blog post.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--date", help="Target publish date in YYYY-MM-DD (default: today).")
    parser.add_argument("--slot-offset", type=int, default=0, help="Preferred topic offset for this slot.")
    parser.add_argument("--force", action="store_true", help="Overwrite article file if it already exists.")
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
