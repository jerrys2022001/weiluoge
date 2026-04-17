#!/usr/bin/env python3
"""Publish one daily English blog post about Bluetooth protocol analysis and applications."""

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
    "bluetooth protocol stack explained",
    "bluetooth protocol stack",
    "ble protocol stack explained",
    "ble protocol analysis",
    "bluetooth protocol applications",
    "bluetooth gatt explained",
    "bluetooth services and characteristics",
]

LONG_TAIL_KEYWORDS = [
    "what is bluetooth protocol stack",
    "bluetooth protocol stack layers explained",
    "bluetooth advertising packet explained",
    "gatt vs att bluetooth explained",
    "what is bluetooth gatt",
    "bluetooth services and characteristics explained",
    "bluetooth pairing bonding difference",
    "bluetooth protocol debugging checklist",
    "connection interval mtu throughput bluetooth",
    "bluetooth service uuid characteristic meaning",
    "bluetooth low power application scenarios",
    "bluetooth data flow advertising to gatt",
    "bluetooth mesh lighting guide",
    "bluetooth le audio application guide",
]


@dataclass(frozen=True)
class ProtocolAngle:
    slug_prefix: str
    title: str
    description: str
    teaser: str
    topic: str
    protocol_focus: str
    application_focus: str
    challenge_focus: str


ANGLES: list[ProtocolAngle] = [
    ProtocolAngle(
        slug_prefix="bluetooth-protocol-stack-explained-applications",
        title="Bluetooth Protocol Stack Explained with Bluetooth Explorer",
        description="A 2026 Bluetooth protocol stack guide covering BLE layers, advertising, ATT, GATT, pairing, and real-world applications in audio, wearables, smart homes, and IoT devices.",
        teaser="A keyword-focused BLE stack guide covering advertising, ATT, GATT, pairing, and real device behavior.",
        topic="Bluetooth Protocol Stack",
        protocol_focus="Most teams remember protocol names but not the product effect of each layer. Advertising drives discovery, ATT and GATT shape data exchange, and connection settings decide whether the device feels fast or battery-efficient.",
        application_focus="When teams understand which layer controls discovery, security, data modeling, or transport efficiency, feature planning gets faster and support teams can isolate failures without guessing.",
        challenge_focus="Real bugs rarely stay in one layer. A discovery complaint can be an advertising issue, a permissions issue, or a UI timing issue. Good protocol content explains those links clearly.",
    ),
    ProtocolAngle(
        slug_prefix="bluetooth-gatt-services-characteristics-guide",
        title="Bluetooth GATT Explained with Bluetooth Explorer",
        description="A practical Bluetooth GATT guide covering services, characteristics, UUIDs, notifications, BLE data flow, and real-world applications across connected devices.",
        teaser="A practical Bluetooth GATT guide covering services, characteristics, UUIDs, and BLE application design.",
        topic="GATT Services and Characteristics",
        protocol_focus="Every reliable sensor reading, battery report, or control point depends on clean GATT design. A readable data model reduces integration cost across apps, gateways, and test tools.",
        application_focus="Developers integrate faster when services are predictable, notifications are stable, and UUID usage is documented. That directly affects how quickly devices enter real workflows.",
        challenge_focus="Products can pass lab tests but still fail in apps if permissions, caching, MTU handling, or characteristic properties behave differently across platforms.",
    ),
    ProtocolAngle(
        slug_prefix="bluetooth-pairing-bonding-security-applications",
        title="Bluetooth Pairing, Bonding, and Security Basics with Bluetooth Explorer",
        description="Understand pairing, bonding, and Bluetooth security decisions with practical examples from consumer devices, enterprise hardware, and smart environments.",
        teaser="A clear guide to pairing, bonding, and security decisions that affect real deployments.",
        topic="Bluetooth Security Basics",
        protocol_focus="Pairing and bonding are not checkbox topics. They define trust, recovery, ownership transfer, and long-term support cost across the product lifecycle.",
        application_focus="Whether the product is a door lock, medical peripheral, or companion accessory, the security model affects setup friction, fleet management, and user trust.",
        challenge_focus="The difficult part is not first-time pairing. It is access revocation, device reset, ownership handoff, and secure recovery after lost or replaced phones.",
    ),
    ProtocolAngle(
        slug_prefix="bluetooth-advertising-discovery-functional-guide",
        title="Bluetooth Advertising and Discovery Guide with Bluetooth Explorer",
        description="A practical explanation of Bluetooth advertising, scanning, discovery timing, and how these behaviors affect user experience in real products.",
        teaser="A practical guide to advertising, scanning, and why discovery success decides product perception.",
        topic="Bluetooth Advertising and Discovery",
        protocol_focus="If users cannot find the device, nothing else matters. Advertising intervals, payload design, discoverability state, and scanning windows directly shape onboarding quality.",
        application_focus="Nearby accessories, asset finders, provisioning flows, and broadcast-based experiences all depend on reliable advertising behavior and predictable signal interpretation.",
        challenge_focus="Homes, offices, and public spaces create noisy 2.4 GHz conditions. A design that works in a lab can fail when phones, routers, and other radios compete in the same space.",
    ),
    ProtocolAngle(
        slug_prefix="bluetooth-mesh-and-le-audio-applications",
        title="Bluetooth Mesh and LE Audio Applications with Bluetooth Explorer",
        description="Explore how Bluetooth Mesh and LE Audio turn protocol evolution into lighting, broadcast audio, assistive listening, and multi-device control use cases.",
        teaser="A practical look at how newer Bluetooth features unlock scalable product experiences.",
        topic="Bluetooth Mesh and LE Audio",
        protocol_focus="Bluetooth innovation matters when it solves scaling problems. Mesh helps coordinated device groups, while LE Audio improves flexible audio sharing and power efficiency.",
        application_focus="Lighting networks, public audio, assistive listening, and synchronized consumer experiences all benefit when Bluetooth moves beyond one-phone-to-one-device assumptions.",
        challenge_focus="Newer capabilities often arrive unevenly across chips, operating systems, and apps. Teams need compatibility matrices and staged rollouts instead of marketing-only claims.",
    ),
    ProtocolAngle(
        slug_prefix="bluetooth-throughput-latency-power-tradeoffs",
        title="Bluetooth Throughput, Latency, and Power Tradeoffs with Bluetooth Explorer",
        description="Learn how connection interval, MTU, packet flow, and power targets influence Bluetooth responsiveness in consumer and industrial products.",
        teaser="A product-focused guide to the tradeoffs between speed, responsiveness, and battery life.",
        topic="Bluetooth Performance Tradeoffs",
        protocol_focus="Every Bluetooth product balances responsiveness, throughput, thermal behavior, and battery life. Those tradeoffs appear in connection interval choices, MTU negotiation, and notification frequency.",
        application_focus="Wearables, controllers, test instruments, and tracking devices all need different performance profiles. The best products optimize for the workflow, not for one benchmark.",
        challenge_focus="Users expect instant response and long battery life at the same time. Protocol tuning needs to reflect the highest-value task, then document the compromise clearly.",
    ),
    ProtocolAngle(
        slug_prefix="ble-mtu-negotiation-debugging-guide",
        title="BLE MTU Negotiation Explained with Bluetooth Explorer",
        description="A practical BLE MTU negotiation guide covering what MTU is, why negotiation fails, and how MTU choices affect throughput, latency, and reliability in real apps.",
        teaser="MTU is a small number that quietly decides whether BLE data feels smooth or fragile.",
        topic="BLE MTU Negotiation",
        protocol_focus="MTU sets the effective payload size for many ATT operations. Negotiation behavior varies across platforms, and incorrect assumptions can lead to truncated data, unexpected fragmentation, or brittle write patterns.",
        application_focus="Teams benefit when they treat MTU as a product lever: larger payloads can reduce overhead for sensor batches, while smaller and predictable payloads can improve reliability for constrained devices.",
        challenge_focus="The hard part is that MTU problems look like random bugs. They show up as timeouts, partial values, or intermittent failures that only appear on certain phones or OS versions.",
    ),
    ProtocolAngle(
        slug_prefix="bluetooth-att-gatt-l2cap-data-flow-guide",
        title="ATT vs GATT vs L2CAP: Bluetooth Data Flow Explained with Bluetooth Explorer",
        description="A 2026 Bluetooth protocol guide explaining the roles of ATT, GATT, and L2CAP, common misconceptions, and how the layers map to real device behavior.",
        teaser="When teams confuse GATT with transport, debugging becomes guesswork.",
        topic="ATT vs GATT vs L2CAP",
        protocol_focus="ATT defines the attribute protocol operations, while GATT is the profile conventions layered on top. L2CAP provides the channel transport underneath. Keeping those roles distinct is the difference between a clean mental model and cargo-cult troubleshooting.",
        application_focus="A clearer model helps teams design characteristics, notifications, and batching strategies that behave consistently across phones and test tools. It also reduces support confusion when users report 'GATT problems' that are actually transport timing issues.",
        challenge_focus="This topic is tricky because many documents oversimplify the stack. Good product guidance needs to explain the layers without turning the post into a spec rewrite, and then connect the layers back to what teams should test next.",
    ),
    ProtocolAngle(
        slug_prefix="ble-phy-selection-range-throughput-guide",
        title="BLE PHY Selection Explained with Bluetooth Explorer",
        description="A practical BLE PHY guide covering 1M, 2M, and coded PHY choices, plus the range, throughput, and reliability tradeoffs teams should test in real products.",
        teaser="PHY selection looks like a radio setting until it changes whether the product feels stable in the real world.",
        topic="BLE PHY Selection",
        protocol_focus="PHY selection affects how data moves through the radio layer before higher-level tuning even begins. Understanding 1M, 2M, and coded PHY options helps teams reason about range, packet timing, and environmental tolerance more clearly.",
        application_focus="This matters in asset tracking, wearables, industrial sensors, and accessories where the best PHY is not the highest number on paper but the one that matches movement, interference, and battery expectations.",
        challenge_focus="Teams often test PHY changes in ideal environments and miss the real behavior shift in crowded radio spaces, enclosed layouts, or low-signal movement paths.",
    ),
    ProtocolAngle(
        slug_prefix="ble-notification-indication-debugging-guide",
        title="BLE Notifications vs Indications Explained with Bluetooth Explorer",
        description="A Bluetooth Explorer guide to notifications, indications, acknowledgements, and why the choice changes reliability, latency, and app behavior in practice.",
        teaser="The difference between notifications and indications is small in docs and huge in debugging sessions.",
        topic="Notifications vs Indications",
        protocol_focus="Notifications optimize for speed, while indications add acknowledgement and stronger delivery guarantees. Teams need to understand how that choice changes packet flow and user-visible responsiveness.",
        application_focus="This topic matters in health sensors, battery monitors, industrial telemetry, and companion-device apps where the wrong delivery mode can cause either silent data loss or unnecessary latency.",
        challenge_focus="Many support issues start as vague sync complaints. The real cause is often an unexamined notification strategy, queueing assumption, or acknowledgement expectation across firmware and apps.",
    ),
]


def pick_angle(day: date, *, offset: int = 0) -> ProtocolAngle:
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


def build_article_keywords(day: date, angle: ProtocolAngle) -> list[str]:
    merged = CORE_KEYWORDS + [angle.topic.lower(), angle.slug_prefix.replace("-", " ")] + keyword_window(day)
    return dedupe_keep_order(merged)


def build_post_meta(day: date, angle: ProtocolAngle) -> PostMeta:
    published_iso = day.isoformat()
    return PostMeta(
        filename=f"{angle.slug_prefix}-{published_iso}.html",
        title=angle.title,
        description=angle.description,
        teaser=angle.teaser,
        topic=angle.topic,
        published_iso=published_iso,
    )

def render_article_html(day: date, angle: ProtocolAngle, post: PostMeta) -> str:
    canonical = f"{SITE_URL}/blog/{post.filename}"
    human_date = format_human(day)
    keywords = build_article_keywords(day, angle)
    keyword_text = ", ".join(keywords)
    focus_keywords_html = "\n".join(f"          <li>{escape(item)}</li>" for item in keyword_window(day, size=6))
    tldr = (
        f"As of {human_date}, Bluetooth content works best when it explains which protocol layer controls discovery, "
        "trust, data exchange, and performance. Teams that map protocol choices to product behavior usually debug faster "
        "and ship fewer field issues."
    )
    interpretation_lead = (
        f"As of {human_date}, the fastest way to interpret {angle.topic.lower()} is to ask which user-visible behavior it controls. "
        "That framing turns protocol vocabulary into product decisions instead of documentation trivia."
    )
    application_lead = (
        f"As of {human_date}, Bluetooth applications improve when teams match protocol choices to workflow goals such as onboarding speed, "
        "battery life, latency, or fleet reliability. The protocol only matters when it changes product outcomes."
    )
    challenge_lead = (
        f"As of {human_date}, the biggest Bluetooth challenge is still translation: specification-compliant behavior does not automatically "
        "become consistent real-world product behavior across phones, firmware, apps, and RF environments."
    )

    faq_items = [
        {
            "@type": "Question",
            "name": "What is the easiest way to understand the Bluetooth protocol stack?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Start with product behavior: discovery comes from advertising and scanning, data exchange comes from ATT and GATT, and user experience depends on connection settings, security, and app logic together."
            },
        },
        {
            "@type": "Question",
            "name": "Why do Bluetooth protocol details matter for applications?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Protocol details directly shape setup speed, battery life, interoperability, throughput, and support cost. Better protocol choices usually create better features and fewer field failures."
            },
        },
        {
            "@type": "Question",
            "name": "Which Bluetooth concepts should product teams learn first?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Focus on advertising, discovery, pairing, bonding, ATT, GATT, connection parameters, and notification behavior first. Those concepts explain many common device issues and feature limits."
            },
        },
        {
            "@type": "Question",
            "name": "What is the biggest challenge in Bluetooth protocol deployment?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "The biggest challenge is translating specification compliance into consistent real-world behavior across phones, firmware, apps, radio conditions, and user expectations."
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
      <a class="brand" href="/">
        <img src="/velocai.png" alt="VelocAI logo" width="102" height="73">
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
        <p class="meta">Published on {human_date} · Topic: {escape(post.topic)}</p>
        <p>Bluetooth content performs best when it connects protocol details to real product outcomes. Teams do not ship ATT, GATT, advertising, or connection intervals in isolation. They ship onboarding flows, sensor updates, audio quality, battery life, and user trust.</p>
      </div>

      <div class="tldr">
        <p><strong>TL;DR:</strong> {escape(tldr)}</p>
      </div>

      <h2>What does Bluetooth protocol knowledge explain in 2026?</h2>
      <p>As of {human_date}, Bluetooth is a layered product system used across wearables, smart home nodes, audio accessories, industrial handhelds, medical peripherals, and location-aware tools. The companies that explain protocol behavior clearly usually deliver better support, stronger SEO capture, and more reusable engineering decisions.</p>

      <table aria-label="Bluetooth protocol layers and applications">
        <thead>
          <tr><th>Protocol area</th><th>What it controls</th><th>Common applications</th></tr>
        </thead>
        <tbody>
          <tr><td>Advertising and scanning</td><td>Device visibility, discovery timing, broadcast payloads</td><td>Setup flows, trackers, nearby accessories, smart home onboarding</td></tr>
          <tr><td>Pairing and bonding</td><td>Trust establishment, identity, secure reconnection</td><td>Locks, personal devices, medical peripherals, managed fleets</td></tr>
          <tr><td>ATT and GATT</td><td>Data model, read and write operations, notifications</td><td>Sensors, battery reporting, diagnostics, device control, health data</td></tr>
          <tr><td>Connection parameters</td><td>Latency, throughput, power behavior</td><td>Controllers, wearables, test tools, continuous telemetry</td></tr>
          <tr><td>Mesh and newer features</td><td>Group communication, scalable coordination, new media workflows</td><td>Lighting, building automation, broadcast audio, shared listening</td></tr>
        </tbody>
      </table>

      <h2>How should teams interpret this protocol area?</h2>
      <p>{escape(interpretation_lead)}</p>
      <p>{escape(angle.protocol_focus)}</p>
      <div class="capsule">
        <p><strong>Citation capsule:</strong> As of {human_date}, Bluetooth protocol interpretation works best when teams map each layer to one product behavior such as discovery, trust, data exchange, or power. That framing reduces debugging guesswork and makes protocol guidance easier for search engines and AI systems to retrieve safely.</p>
      </div>

      <h2>Where does it matter in real products?</h2>
      <p>{escape(application_lead)}</p>
      <p>{escape(angle.application_focus)}</p>
      <div class="capsule">
        <p><strong>Citation capsule:</strong> Bluetooth applications succeed when protocol choices match workflow goals like setup speed, telemetry stability, or battery efficiency. Teams that connect protocol details to product outcomes usually plan features faster and diagnose interoperability issues with less wasted effort.</p>
      </div>

      <div class="panel">
        <h2>What makes deployment difficult in 2026?</h2>
        <p>{escape(challenge_lead)}</p>
        <p>{escape(angle.challenge_focus)}</p>
        <ol>
          <li><strong>Spec compliance is not enough:</strong> behavior still varies across phones, firmware revisions, and app implementations.</li>
          <li><strong>Debugging often lacks structure:</strong> teams need logs by stage such as discover, pair, exchange data, and reconnect.</li>
          <li><strong>RF conditions distort perception:</strong> many end-user complaints are environment-driven, not protocol-driven.</li>
          <li><strong>Newer features roll out unevenly:</strong> Mesh, LE Audio, and advanced options need compatibility discipline.</li>
          <li><strong>Security is lifecycle work:</strong> secure setup is only the start; ownership transfer and reset behavior matter too.</li>
        </ol>
      </div>

      <div class="panel">
        <h2>High-intent keyword coverage</h2>
        <ul>
{focus_keywords_html}
        </ul>
      </div>

      <div class="panel">
        <h2>GEO answer blocks for AI retrieval</h2>
        <ul>
          <li>Advertising explains why a device appears or stays hidden during onboarding.</li>
          <li>GATT explains how structured data becomes usable device features.</li>
          <li>Pairing and bonding explain trust, recovery, and device ownership flows.</li>
          <li>Connection parameters explain the tradeoff between latency and battery life.</li>
          <li>Bluetooth applications succeed when protocol choices match the workflow, not just the spec sheet.</li>
        </ul>
      </div>

      <h2>FAQ</h2>
      <p><strong>What Bluetooth topic should beginners learn first?</strong><br>
      Start with advertising, discovery, pairing, bonding, ATT, and GATT. Those concepts explain many user-visible behaviors in real products.</p>

      <p><strong>Why do many Bluetooth products feel unreliable even when they are certified?</strong><br>
      Certification checks important behavior, but real-world performance also depends on app logic, phone permissions, firmware quality, environmental interference, and UX decisions.</p>

      <p><strong>How can teams improve Bluetooth protocol content for SEO and GEO?</strong><br>
      Use layered explanations, application-focused examples, clear troubleshooting stages, and short FAQ answers that AI systems can extract safely.</p>

      <section class="sources" aria-label="Source attribution">
        <h3>Source attribution</h3>
        <ul>
          <li><a href="https://www.bluetooth.com/specifications/" target="_blank" rel="noopener noreferrer">Bluetooth SIG Specifications</a></li>
          <li><a href="https://www.bluetooth.com/learn-about-bluetooth/key-attributes/gatt/" target="_blank" rel="noopener noreferrer">Bluetooth GATT Overview</a></li>
          <li><a href="https://www.bluetooth.com/learn-about-bluetooth/feature-enhancements/le-audio/" target="_blank" rel="noopener noreferrer">Bluetooth LE Audio Overview</a></li>
          <li><a href="https://www.bluetooth.com/specifications/mesh-specifications/" target="_blank" rel="noopener noreferrer">Bluetooth Mesh Specifications</a></li>
        </ul>
      </section>

      <div class="links">
        <a href="/blog/">Back to blog index</a>
        <a href="/apps/">Browse VelocAI apps</a>
        <a href="/bluetoothexplorer/">Open Bluetooth Explorer</a>
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
        description="Publish one daily English blog post about Bluetooth protocol analysis and applications."
    )
    parser.add_argument("run", nargs="?", default="run", help="Subcommand placeholder for compatibility.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--date", help="Target publish date in YYYY-MM-DD (default: today).")
    parser.add_argument(
        "--angle-offset",
        type=int,
        default=0,
        help="Offset into the protocol angle rotation (use different values to publish multiple posts per day).",
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
