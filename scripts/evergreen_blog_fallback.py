#!/usr/bin/env python3
"""Evergreen blog fallback candidates for strict daily lane quotas."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import date

from blog_daily_scheduler import SITE_URL, PostMeta


@dataclass(frozen=True)
class EvergreenArticle:
    lane: str
    slug_prefix: str
    title: str
    description: str
    teaser: str
    topic: str
    lane_label: str
    nav_href: str
    nav_label: str
    keywords: tuple[str, ...]
    lead: str
    tldr: str
    sections: tuple[tuple[str, str], ...]
    table_label: str
    table_headers: tuple[str, str, str]
    table_rows: tuple[tuple[str, str, str], ...]
    checklist_title: str
    checklist: tuple[str, ...]
    faq: tuple[tuple[str, str], ...]
    sources: tuple[tuple[str, str], ...]
    bottom_line: str
    extra_links: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class EvergreenCandidate:
    lane: str
    identifier: str
    post: PostMeta
    html: str


def esc(value: str, *, quote: bool = False) -> str:
    return html.escape(value, quote=quote)


def render_article(article: EvergreenArticle, target_day: date) -> tuple[PostMeta, str]:
    published_iso = target_day.isoformat()
    filename = f"{article.slug_prefix}-{published_iso}.html"
    canonical = f"{SITE_URL}/blog/{filename}"
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "headline": article.title,
                "description": article.description,
                "datePublished": published_iso,
                "dateModified": published_iso,
                "author": {"@type": "Organization", "name": "VelocAI"},
                "publisher": {
                    "@type": "Organization",
                    "name": "VelocAI",
                    "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/2.png"},
                },
                "mainEntityOfPage": canonical,
                "keywords": list(article.keywords),
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": question,
                        "acceptedAnswer": {"@type": "Answer", "text": answer},
                    }
                    for question, answer in article.faq
                ],
            },
        ],
    }
    sections_html = "\n".join(
        f"      <h2>{esc(title)}</h2>\n      <p>{esc(body)}</p>"
        for title, body in article.sections
    )
    rows_html = "\n".join(
        f"          <tr><td>{esc(left)}</td><td>{esc(mid)}</td><td>{esc(right)}</td></tr>"
        for left, mid, right in article.table_rows
    )
    checklist_html = "\n".join(f"          <li>{esc(item)}</li>" for item in article.checklist)
    faq_html = "\n".join(
        f"      <p><strong>{esc(question)}</strong><br>\n      {esc(answer)}</p>"
        for question, answer in article.faq
    )
    sources_html = "\n".join(
        f'          <li><a href="{esc(url, quote=True)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a></li>'
        for label, url in article.sources
    )
    links = (
        (article.nav_label, article.nav_href),
        ("Back to blog", "/blog/"),
        ("Browse VelocAI apps", "/apps/"),
        *article.extra_links,
    )
    links_html = "".join(f'<a href="{esc(href, quote=True)}">{esc(label)}</a>' for label, href in links)
    published_label = target_day.strftime("%B %d, %Y")
    body = f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(article.title)} | VelocAI Blog</title>
  <meta name="description" content="{esc(article.description, quote=True)}">
  <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" type="image/x-icon" href="/velocai.ico">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="en_US">
  <meta property="og:site_name" content="VelocAI">
  <meta property="og:title" content="{esc(article.title, quote=True)}">
  <meta property="og:description" content="{esc(article.description, quote=True)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{SITE_URL}/2.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(article.title, quote=True)}">
  <meta name="twitter:description" content="{esc(article.description, quote=True)}">
  <meta name="twitter:image" content="{SITE_URL}/2.png">
  <script type="application/ld+json">
{json.dumps(graph, ensure_ascii=False, indent=2)}
  </script>
  <style>
    :root {{ --bg:#f8fbff; --text:#17283a; --muted:#536779; --line:#d7e3ee; --panel:#fff; --soft:#eaf4ff; --brand:#176b9a; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Inter","Segoe UI",sans-serif; color:var(--text); background:var(--bg); line-height:1.72; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ width:min(920px, calc(100% - 34px)); margin:0 auto; }}
    header {{ border-bottom:1px solid var(--line); background:rgba(248,251,255,.94); }}
    .top {{ padding:14px 0; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }}
    .brand {{ display:inline-flex; align-items:center; gap:10px; font-weight:700; }}
    .brand img {{ height:36px; width:auto; max-width:52px; border-radius:10px; }}
    nav {{ display:flex; gap:12px; flex-wrap:wrap; color:var(--muted); font-size:14px; }}
    main {{ padding:36px 0 56px; }}
    h1,h2,h3 {{ margin:0; line-height:1.22; }}
    h1 {{ font-size:clamp(30px, 4vw, 46px); max-width:25ch; }}
    h2 {{ margin-top:30px; font-size:clamp(23px, 3vw, 32px); }}
    p,li,td,th {{ color:#30475f; font-size:17px; }}
    ul,ol {{ padding-left:22px; }}
    .meta {{ margin-top:10px; color:var(--muted); font-size:14px; }}
    .lead {{ font-size:20px; color:#243b53; max-width:780px; }}
    .tldr,.note,.panel {{ margin:24px 0; padding:18px 20px; border:1px solid var(--line); background:var(--panel); border-radius:8px; }}
    table {{ width:100%; border-collapse:collapse; margin:18px 0; background:var(--panel); border:1px solid var(--line); }}
    th,td {{ padding:12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ color:#20344a; background:var(--soft); }}
    .links {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:28px; }}
    .links a {{ padding:10px 14px; border:1px solid var(--line); border-radius:8px; background:#fff; color:var(--brand); font-weight:650; }}
    footer {{ border-top:1px solid var(--line); padding:22px 0; color:var(--muted); font-size:14px; }}
  </style>
</head>
<body>
  <header><div class="wrap top"><a class="brand" href="/"><img src="/2.png" alt="VelocAI logo"><span>VelocAI Blog</span></a><nav><a href="/blog/">Blog</a><a href="{esc(article.nav_href, quote=True)}">{esc(article.nav_label)}</a><a href="/apps/">Apps</a></nav></div></header>
  <main class="wrap"><article>
    <section class="hero"><p class="meta">{esc(article.lane_label)}</p><h1>{esc(article.title)}</h1><p class="meta">Published {published_label} | Topic: {esc(article.topic)}</p><p class="lead">{esc(article.lead)}</p></section>
    <div class="tldr"><p><strong>TL;DR:</strong> {esc(article.tldr)}</p></div>
{sections_html}
    <table aria-label="{esc(article.table_label, quote=True)}"><thead><tr><th>{esc(article.table_headers[0])}</th><th>{esc(article.table_headers[1])}</th><th>{esc(article.table_headers[2])}</th></tr></thead><tbody>
{rows_html}
    </tbody></table>
    <div class="panel"><h2>{esc(article.checklist_title)}</h2><ul>
{checklist_html}
    </ul></div>
    <h2>What should users ask?</h2>
{faq_html}
    <h2>Useful references</h2><ul>
{sources_html}
    </ul>
    <div class="note"><p><strong>Bottom line:</strong> {esc(article.bottom_line)}</p></div>
    <div class="links">{links_html}</div>
  </article></main><footer><div class="wrap">&copy; 2026 VelocAI. Practical mobile workflows for real product decisions.</div></footer>
</body></html>
"""
    post = PostMeta(
        filename=filename,
        title=article.title,
        description=article.description,
        teaser=article.teaser,
        topic=article.topic,
        published_iso=published_iso,
    )
    return post, body


EVERGREEN_ARTICLES: tuple[EvergreenArticle, ...] = (
    EvergreenArticle(
        lane="protocol",
        slug_prefix="bluetooth-biginfo-broadcast-audio-debugging-guide",
        title="Bluetooth BIGInfo Broadcast Audio Debugging Guide",
        description="Use Bluetooth Explorer to debug BIGInfo broadcast audio setup with BIS indexes, presentation delay, encryption flags, and sync notes.",
        teaser="A Bluetooth Explorer workflow for checking BIGInfo before a broadcast audio issue turns into vague playback blame.",
        topic="Bluetooth Explorer BIGInfo broadcast debugging",
        lane_label="Bluetooth Explorer protocol workflow",
        nav_href="/bluetoothexplorer/",
        nav_label="Bluetooth Explorer",
        keywords=("bluetooth", "Bluetooth Explorer", "BIGInfo", "broadcast audio", "BIS index"),
        lead="Broadcast audio failures are easy to blame on the speaker or phone, but the useful clues often arrive earlier: BIGInfo timing, BIS indexes, encryption flags, presentation delay, and whether the receiver ever had enough data to join the stream.",
        tldr="Use Bluetooth Explorer to record BIGInfo fields, broadcast code expectations, BIS index mapping, periodic sync state, presentation delay, and PHY before changing playback logic.",
        sections=(
            ("Why does BIGInfo matter?", "BIGInfo tells a receiver how to understand a broadcast isochronous group. If the receiver never sees the right timing, encryption, or BIS structure, later audio debugging is mostly theater."),
            ("What should Bluetooth Explorer capture?", "Capture periodic sync state, BIGInfo presence, BIS count, BIS index, PHY, framing, encryption flag, and presentation delay. Those fields explain whether the receiver can even attempt the stream."),
            ("How should teams retest?", "Run one open broadcast, one encrypted broadcast, and one wrong-code attempt. Keep the same receiver placement so sync quality is not confused with authorization or metadata problems."),
            ("When is it not an audio bug?", "Do not blame codec or speaker output when BIGInfo is missing, the BIS index is wrong, or the broadcast code expectation does not match. The stream has to be joinable first."),
        ),
        table_label="BIGInfo broadcast audio triage",
        table_headers=("Evidence", "Likely meaning", "Next move"),
        table_rows=(
            ("Periodic sync works, BIGInfo missing", "Receiver sees the advertiser but cannot learn the broadcast group", "Check broadcaster configuration before audio code"),
            ("BIS index does not match UI choice", "The app may be joining the wrong stream", "Map BIS indexes to visible program names"),
            ("Encrypted flag differs from expected code", "Join failure may be authorization, not radio quality", "Retest open and encrypted broadcasts separately"),
        ),
        checklist_title="How do you keep the retest honest?",
        checklist=(
            "Record whether periodic sync happened before checking audio behavior.",
            "Write down BIS count, BIS index, and presentation delay.",
            "Separate open broadcast tests from encrypted broadcast tests.",
            "Keep receiver placement fixed for the first three captures.",
            "Map each visible program choice to the raw broadcast metadata.",
        ),
        faq=(
            ("What is the first BIGInfo debugging clue?", "Check whether periodic sync succeeded and whether BIGInfo is visible before blaming audio playback."),
            ("Why does the BIS index matter?", "The BIS index tells the receiver which stream inside the broadcast group it is joining."),
            ("When should teams inspect broadcaster setup?", "Inspect setup when BIGInfo is absent, encryption flags are wrong, or BIS mapping does not match the user interface."),
        ),
        sources=(
            ("Bluetooth Core specification", "https://www.bluetooth.com/specifications/specs/core-specification/"),
            ("Bluetooth GATT supplement", "https://www.bluetooth.com/specifications/specs/gatt-specification-supplement/"),
            ("Apple Core Bluetooth documentation", "https://developer.apple.com/documentation/corebluetooth"),
        ),
        bottom_line="Bluetooth Explorer turns broadcast audio debugging into concrete BIGInfo, BIS, encryption, and sync evidence before teams chase playback symptoms.",
        extra_links=(("Read periodic advertising guide", "/blog/ble-periodic-advertising-sync-debugging-bluetooth-explorer-2026-06-01.html"),),
    ),
    EvergreenArticle(
        lane="protocol",
        slug_prefix="bluetooth-isoal-sdu-framing-debugging-guide",
        title="Bluetooth ISOAL SDU Framing Debugging Guide",
        description="Use Bluetooth Explorer to debug ISOAL SDU framing with timestamp drift, packet loss, flush timeout clues, and clean receiver notes.",
        teaser="A Bluetooth Explorer checklist for isochronous framing bugs that look like random audio or sensor drops.",
        topic="Bluetooth Explorer ISOAL framing debugging",
        lane_label="Bluetooth Explorer protocol workflow",
        nav_href="/bluetoothexplorer/",
        nav_label="Bluetooth Explorer",
        keywords=("bluetooth", "Bluetooth Explorer", "ISOAL", "SDU framing", "isochronous data"),
        lead="Isochronous bugs rarely announce themselves cleanly. One receiver hears a click, another drops a sensor frame, and the first useful clue is usually not the app log. It is whether SDUs are being framed, flushed, and timed the same way on every run.",
        tldr="Use Bluetooth Explorer to record SDU interval, timestamp spacing, packet loss, flush timeout, controller role, and receiver placement before changing codec, parser, or retry logic.",
        sections=(
            ("Where does the trail start?", "Start with the SDU timing. If timestamps drift before the app sees the payload, the bug is already below the application layer."),
            ("What should Bluetooth Explorer capture?", "Capture interval, sequence gaps, flush timeout, transport role, PHY, and whether drops cluster near movement or interference. Keep the raw timing next to the user-facing symptom."),
            ("How should teams retest?", "Run one fixed-position pass, one movement pass, and one high-traffic pass. Change only one pressure at a time so timing drift does not get blamed on parsing."),
            ("When is it not a codec issue?", "Do not tune codec settings when SDUs arrive late, incomplete, or out of rhythm. A clean payload cannot fix a broken delivery shape."),
        ),
        table_label="ISOAL framing triage",
        table_headers=("Clue", "What it means", "Next move"),
        table_rows=(
            ("Timestamps drift before decode", "Timing is unstable below app logic", "Check interval and flush behavior first"),
            ("Loss clusters during movement", "Placement or coexistence may be involved", "Repeat with fixed receiver position"),
            ("Payload parses after clean timing", "Parser changes can be tested safely", "Compare raw SDU boundaries before editing code"),
        ),
        checklist_title="How do you keep timing evidence clean?",
        checklist=(
            "Record the expected SDU interval before the test.",
            "Save sequence gaps and timestamp spacing together.",
            "Keep the receiver still for the first pass.",
            "Retest movement and radio noise separately.",
            "Do not change codec and transport settings in the same run.",
        ),
        faq=(
            ("What is the first ISOAL clue to check?", "Check timestamp spacing and SDU boundaries before judging the decoded payload."),
            ("Why does flush timeout matter?", "A tight flush timeout can turn late data into missing data, which looks like a higher-level failure."),
            ("When should teams inspect controller behavior?", "Inspect controller behavior when timing gaps appear before the app receives a complete payload."),
        ),
        sources=(
            ("Bluetooth Core specification", "https://www.bluetooth.com/specifications/specs/core-specification/"),
            ("Bluetooth LE Audio overview", "https://www.bluetooth.com/learn-about-bluetooth/feature-enhancements/le-audio/"),
            ("Apple Core Bluetooth documentation", "https://developer.apple.com/documentation/corebluetooth"),
        ),
        bottom_line="Bluetooth Explorer helps teams treat isochronous drops as timing evidence first, then parser or codec evidence only after the transport shape is clean.",
        extra_links=(("Read BIGInfo guide", "/blog/bluetooth-biginfo-broadcast-audio-debugging-guide-2026-06-04.html"),),
    ),
    EvergreenArticle(
        lane="find",
        slug_prefix="find-ai-playground-bag-lost-earbud-checklist",
        title="Find AI Playground Bag Lost Earbud Checklist",
        description="Use Find AI around playground bags to recover misplaced earbuds with stroller checks, bench zones, pouch passes, and privacy-safe stop rules.",
        teaser="A Find AI recovery workflow for playground benches, stroller baskets, and small bag pockets.",
        topic="find AI playground bag recovery",
        lane_label="Find AI Practical Guide",
        nav_href="/aifind/",
        nav_label="Find AI",
        keywords=("find AI", "Find AI Practical Guide", "playground earbuds", "Bluetooth item recovery", "bag checklist"),
        lead="Playground searches become messy fast. Bags move between benches, jackets pile up under strollers, and a nearby reading can tempt someone to inspect the wrong family's stuff.",
        tldr="Use Find AI to split the area into your bench, stroller basket, jacket pile, snack bag, and exit path. Clear each owned pocket once and stop when the clue points at someone else's belongings.",
        sections=(
            ("Why does the playground distort clues?", "Metal benches, moving parents, and clustered bags can make a small Bluetooth item feel close even when it is buried in a different layer of your own gear."),
            ("What should Find AI compare?", "Compare the device name with the last owned bag, stroller basket, jacket, snack pouch, and pickup path. The useful clue is movement between zones, not a single nearby reading."),
            ("How should users clear bags?", "Move owned bags to one bench, check each pocket once, and place cleared items on one side. The search gets worse when every pouch is opened three times."),
            ("When should users stop?", "Stop when the clue points toward another family's bag, staff storage, or a locked area. The app should protect recovery without encouraging awkward guesses."),
        ),
        table_label="Find AI playground recovery decisions",
        table_headers=("Clue", "What it suggests", "Better move"),
        table_rows=(
            ("Reading follows the stroller", "Item may be in basket or jacket layer", "Clear stroller pockets and blanket folds once"),
            ("Reading stays near a shared bench", "Nearby bags may be confusing the scan", "Verify identity before touching anything"),
            ("Reading points outside owned gear", "Privacy boundary may be reached", "Stop and ask staff with a clear item note"),
        ),
        checklist_title="How do you write the recovery note?",
        checklist=(
            "Record bench area, time, item type, and case color.",
            "List cleared owned bags, stroller pockets, and jackets.",
            "Mention whether the reading changed near the exit path.",
            "Avoid opening another family's bag even when the reading feels close.",
            "Ask staff only with a specific item description and last owned zone.",
        ),
        faq=(
            ("Can Find AI identify which bag contains the earbuds?", "No. It can organize the search, but users should only inspect belongings they own or control."),
            ("What is the strongest playground clue?", "A matching device identity plus a reading that moves with an owned stroller or bag is stronger than a static nearby reading."),
            ("When should users stop searching alone?", "Stop when the clue points toward another family's belongings, staff storage, or an area users should not enter."),
        ),
        sources=(
            ("Apple Support locate a device", "https://support.apple.com/guide/iphone/locate-a-device-iph09b087eda/ios"),
            ("Bluetooth range basics", "https://www.bluetooth.com/learn-about-bluetooth/key-attributes/range/"),
            ("FTC privacy tips", "https://consumer.ftc.gov/"),
        ),
        bottom_line="Find AI works best at a playground when it turns a scattered bag search into owned zones, one clean pocket pass, and a privacy-safe stop rule.",
        extra_links=(("Read gym locker guide", "/blog/find-ai-gym-locker-earbud-sweep-playbook-2026-06-03.html"),),
    ),
    EvergreenArticle(
        lane="find",
        slug_prefix="find-ai-movie-theater-seat-earbud-checklist",
        title="Find AI Movie Theater Seat Earbud Checklist",
        description="Use Find AI after a movie to recover misplaced earbuds with seat-row checks, cupholder passes, aisle notes, and staff boundaries.",
        teaser="A Find AI recovery checklist for dark theater rows, cupholders, jackets, and seat gaps.",
        topic="find AI theater seat recovery",
        lane_label="Find AI Practical Guide",
        nav_href="/aifind/",
        nav_label="Find AI",
        keywords=("find AI", "Find AI Practical Guide", "movie theater earbuds", "seat gap recovery", "Bluetooth finder"),
        lead="Theater rows make small devices vanish in boring ways. Earbuds slide under a folding seat, the case drops into a cupholder shadow, and the room gets cleaned before anyone remembers the exact row.",
        tldr="Use Find AI before leaving the theater row: confirm the device name, check your seat, cupholder, jacket, bag, and aisle path once, then give staff a row note if the clue points beyond your reach.",
        sections=(
            ("What should happen first?", "Turn on the phone light, name the row and seat, and keep bags still. Moving everything at once makes the reading harder to trust."),
            ("What should Find AI compare?", "Compare the device name with seat, cupholder, jacket pocket, bag pocket, and aisle path. A reading that changes between those spots is more useful than one loud nearby clue."),
            ("How should users clear the row?", "Check owned items first. Then look under the seat hinge, cupholder lip, and aisle edge. Do not crawl into another row while people are still leaving."),
            ("When should staff take over?", "Ask staff when the clue points under fixed seating, into a closed row, or after cleaning starts. A row and seat note helps more than a vague lost earbud report."),
        ),
        table_label="Find AI theater recovery decisions",
        table_headers=("Clue", "What it suggests", "Better move"),
        table_rows=(
            ("Reading improves at the cupholder", "Case may be hidden in shadow or under a wrapper", "Clear the cupholder and nearby seat edge"),
            ("Reading follows the jacket", "Item may already be in clothing", "Check each pocket once and mark it clear"),
            ("Reading points under fixed seats", "Staff tools may be needed", "Give staff the row, seat, and item color"),
        ),
        checklist_title="How do you write the theater note?",
        checklist=(
            "Record auditorium, row, seat, movie time, and item color.",
            "List checked pockets, bag sections, cupholder, and floor area.",
            "Mention whether the reading changed near the aisle or seat hinge.",
            "Stop before reaching into another guest's area.",
            "Ask staff with a specific row note before the room turns over.",
        ),
        faq=(
            ("Can Find AI prove earbuds are under a theater seat?", "No. It can narrow the row and owned items, but fixed seating may still need staff help."),
            ("What is the strongest theater clue?", "A matching device identity plus a reading that changes between seat, jacket, and aisle is stronger than one nearby reading."),
            ("When should users stop searching alone?", "Stop when the clue points under fixed seating, into another row, or after staff cleaning begins."),
        ),
        sources=(
            ("Apple Support locate a device", "https://support.apple.com/guide/iphone/locate-a-device-iph09b087eda/ios"),
            ("Bluetooth range basics", "https://www.bluetooth.com/learn-about-bluetooth/key-attributes/range/"),
            ("FTC privacy tips", "https://consumer.ftc.gov/"),
        ),
        bottom_line="Find AI helps most after a movie when it turns a dark-row search into a seat note, one clean pocket pass, and a staff handoff before cleanup moves the item.",
        extra_links=(("Read playground recovery guide", "/blog/find-ai-playground-bag-lost-earbud-checklist-2026-06-04.html"),),
    ),
    EvergreenArticle(
        lane="dualshot",
        slug_prefix="dualshot-camera-garden-pest-inspection-workflow",
        title="Dual Camera Garden Pest Inspection Workflow",
        description="Use Dual Camera to record garden pest checks with leaf close-ups, plant-row context, soil moisture clues, and treatment notes.",
        teaser="A Dual Camera workflow for gardeners who need leaf detail and plant location in the same review clip.",
        topic="Dual Camera garden pest inspection",
        lane_label="Dual Camera creator workflow",
        nav_href="/dual-camera/",
        nav_label="Dual Camera",
        keywords=("Dual Camera", "garden pest inspection", "plant care video", "leaf close-up workflow"),
        lead="Plant problems are easy to misread from one camera angle. A close shot shows spots on a leaf, but not which plant row it came from; a wide shot shows the bed, but hides aphids, mildew, eggs, and dry soil crust.",
        tldr="Use Dual Camera for garden pest checks when the review needs two views at once: close leaf detail for symptoms and a wider plant view for location, watering pattern, sun exposure, and treatment notes.",
        sections=(
            ("Why use two views?", "The close view shows the symptom: eggs, webbing, holes, yellowing, powder, or curled edges. The wider view shows whether the problem sits near shade, crowding, dry soil, or one weak section of the bed."),
            ("What should the first plant show?", "Start with the plant name, row, pot, or bed corner. Then film the top leaf, underside, stem joint, soil surface, and neighboring plant so the later review can connect damage with location."),
            ("How should gardeners record?", "Move plant by plant, not symptom by symptom. Keep the wide view steady enough to show row order, and pause the close view under each leaf before naming what changed."),
            ("When is one camera enough?", "Use one camera for a quick bloom update or harvest note. Use Dual Camera when the clip may guide pruning, isolation, watering changes, or pest treatment."),
        ),
        table_label="Dual Camera garden inspection plan",
        table_headers=("Moment", "Plant view", "Leaf view"),
        table_rows=(
            ("First symptom", "Row, pot, bed corner, and neighboring plants", "Leaf spots, holes, eggs, webbing, or mildew"),
            ("Water check", "Mulch, drainage, shade, and crowding", "Soil crust, stem base, and wilted edges"),
            ("Treatment note", "Which plant was isolated or trimmed", "Exact leaf or stem area treated"),
        ),
        checklist_title="How do you make the clip useful?",
        checklist=(
            "Name the plant, row, pot, or bed corner before filming symptoms.",
            "Show the underside of at least one affected leaf.",
            "Keep the wider view steady enough to preserve plant order.",
            "Record soil moisture clues before adding water or treatment.",
            "End with one note about what to check again tomorrow.",
        ),
        faq=(
            ("What should Dual Camera show in a garden inspection clip?", "Show plant location in one view and leaf, stem, soil, or pest detail in the other."),
            ("Why is the wider plant view useful?", "It shows whether symptoms cluster near shade, crowding, dry soil, or a specific row."),
            ("Should garden inspection clips be heavily edited?", "No. Trim walking time if needed, but keep plant order and symptom close-ups together."),
        ),
        sources=(
            ("Apple record videos on iPhone", "https://support.apple.com/guide/iphone/record-videos-iph61f49e4bb/ios"),
            ("Apple camera settings", "https://support.apple.com/guide/iphone/change-advanced-camera-settings-iphb362b394e/ios"),
            ("iMovie trim clips on iPhone", "https://support.apple.com/guide/imovie-iphone/trim-arrange-videos-knac0e10e149/ios"),
        ),
        bottom_line="Dual Camera helps gardeners keep plant location and leaf-level symptoms together before a small pest issue spreads across the bed.",
        extra_links=(("Read pottery feedback guide", "/blog/dual-camera-pottery-wheel-feedback-workflow-2026-06-03.html"),),
    ),
    EvergreenArticle(
        lane="dualshot",
        slug_prefix="dual-camera-board-game-rules-capture-workflow",
        title="Dual Camera Board Game Rules Capture Workflow",
        description="Use Dual Camera to record board game rules with table state, card text, dice rolls, scoring disputes, and replay notes.",
        teaser="A Dual Camera workflow for board game nights where the table state and tiny rule text both matter.",
        topic="Dual Camera board game rules capture",
        lane_label="Dual Camera creator workflow",
        nav_href="/dual-camera/",
        nav_label="Dual Camera",
        keywords=("Dual Camera", "board game rules video", "tabletop scoring", "card text capture"),
        lead="Board game arguments usually start small. A card is read too fast, a dice roll gets nudged, or the scoring track moves before anyone remembers the previous state.",
        tldr="Use Dual Camera when a board game needs proof of two things at once: the whole table state and the small rule detail on a card, token, dice roll, or scoring marker.",
        sections=(
            ("Why use two views?", "The table view preserves player position, turn order, scoring track, and moved pieces. The detail view keeps card text, dice values, tokens, and rulebook lines readable."),
            ("What should the first turn show?", "Start with the game name, player order, score position, and active card or rule. Then hold the detail view still long enough for the text or dice result to be checked later."),
            ("How should players record?", "Keep the table view fixed above the board edge. Bring only the disputed card, tile, rulebook line, or dice tray into the close view so the clip does not become a messy table scan."),
            ("When is one camera enough?", "Use one camera for a quick victory photo. Use Dual Camera when a turn, penalty, scoring move, or house rule may need a calm replay."),
        ),
        table_label="Dual Camera board game capture plan",
        table_headers=("Moment", "Table view", "Detail view"),
        table_rows=(
            ("Setup", "Player order, score track, board zones, and discard piles", "Game title, scenario card, or rule variant"),
            ("Dispute", "Piece location before anyone moves again", "Card text, dice value, token symbol, or rulebook line"),
            ("Scoring", "Final board state and player markers", "Score sheet, bonus card, or tie-break rule"),
        ),
        checklist_title="How do you keep the replay fair?",
        checklist=(
            "Name the game, round, active player, and turn phase first.",
            "Keep the table view stable before a disputed move changes the board.",
            "Show card text or dice values close enough to read.",
            "Say the rule question out loud in one sentence.",
            "Stop recording after the ruling and score change are visible.",
        ),
        faq=(
            ("What should Dual Camera show during a board game dispute?", "Show the full table state in one view and the disputed card, dice, token, or rulebook text in the other."),
            ("Why is the table view important?", "It prevents a close-up from hiding piece location, turn order, discard piles, or score markers."),
            ("Should board game clips be edited heavily?", "No. Trim downtime if needed, but keep the disputed state, rule detail, and final ruling together."),
        ),
        sources=(
            ("Apple record videos on iPhone", "https://support.apple.com/guide/iphone/record-videos-iph61f49e4bb/ios"),
            ("Apple camera settings", "https://support.apple.com/guide/iphone/change-advanced-camera-settings-iphb362b394e/ios"),
            ("iMovie trim clips on iPhone", "https://support.apple.com/guide/imovie-iphone/trim-arrange-videos-knac0e10e149/ios"),
        ),
        bottom_line="Dual Camera keeps the table state and the tiny rule detail together, so the replay settles the move instead of restarting the argument.",
        extra_links=(("Read garden inspection guide", "/blog/dualshot-camera-garden-pest-inspection-workflow-2026-06-04.html"),),
    ),
    EvergreenArticle(
        lane="octopus",
        slug_prefix="octopus-mobile-log-review-approval-workflow",
        title="Octopus Mobile Log Review Approval Workflow",
        description="Use Octopus to review mobile log triage with error scope, changed files, retry limits, rollback notes, and desktop handoff rules.",
        teaser="An Octopus mobile workflow for approving small log triage steps without hiding the risk.",
        topic="Octopus mobile log review",
        lane_label="Octopus Practical Guide",
        nav_href="/octopus/",
        nav_label="Octopus",
        keywords=("Octopus", "mobile Codex", "log review", "approval workflow", "rollback notes"),
        lead="Log triage feels safe from a phone until the next tap turns into a broad rewrite. The useful mobile review is narrow: one error, one file group, one retry reason, and a visible stop point.",
        tldr="Use Octopus for log review when Codex has isolated the error, named the changed files, shown the command output, and made the next approval reversible.",
        sections=(
            ("When It Helps Most", "Octopus helps when the mobile task is to approve one bounded diagnostic step, not to redesign the fix from a small screen."),
            ("What should users inspect?", "Inspect the error line, command, changed files, retry reason, and whether the next action touches config, credentials, deployment, or data."),
            ("How should approval work?", "Approve one follow-up at a time: rerun a test, inspect a stack trace, revert a file, or write a summary. Stop if the task gets wider."),
            ("Limits And Failure Modes", "The phone is not enough for broad diffs, unclear ownership, credential changes, or a fix that needs architecture judgment."),
        ),
        table_label="Octopus log review decisions",
        table_headers=("Signal", "Risk reduced", "Stop point"),
        table_rows=(
            ("One error and one command", "Keeps triage narrow", "Stop if the next step changes many files"),
            ("Changed files are visible", "Prevents blind approval", "Stop if the diff cannot be reviewed"),
            ("Rollback note exists", "Makes the next tap reversible", "Stop before deploy or credential changes"),
        ),
        checklist_title="How do you keep the approval bounded?",
        checklist=(
            "Ask Codex to name the exact error and command output.",
            "Open the changed-files list before approving another step.",
            "Require a retry reason and expected result in one sentence.",
            "Write the rollback note before touching deployment or config.",
            "Move to desktop when the fix spans ownership boundaries.",
        ),
        faq=(
            ("When should Octopus users approve log triage from mobile?", "Approve when the error is narrow, files are visible, output is specific, and the next action is reversible."),
            ("What state should users inspect first?", "Inspect error line, command output, changed files, retry reason, and rollback readiness."),
            ("When is the phone or iPad flow not enough?", "It is not enough for broad diffs, credentials, deployment, data migrations, or architecture decisions."),
        ),
        sources=(
            ("GitHub pull request review docs", "https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests"),
            ("OpenSSF Scorecard project", "https://github.com/ossf/scorecard"),
            ("npm package lock documentation", "https://docs.npmjs.com/cli/v10/configuring-npm/package-lock-json"),
        ),
        bottom_line="Octopus is useful for mobile log review when the next approval is narrow, evidenced, and easy to reverse.",
        extra_links=(("Read dependency approval guide", "/blog/octopus-mobile-dependency-upgrade-approval-workflow-2026-06-02.html"),),
    ),
)


def build_evergreen_candidates(target_day: date, lane: str, slot_offset: int) -> list[EvergreenCandidate]:
    articles = [article for article in EVERGREEN_ARTICLES if article.lane == lane]
    if not articles:
        return []
    rotate = slot_offset % len(articles)
    articles = articles[rotate:] + articles[:rotate]
    candidates: list[EvergreenCandidate] = []
    for index, article in enumerate(articles):
        post, body = render_article(article, target_day)
        candidates.append(
            EvergreenCandidate(
                lane=lane,
                identifier=f"evergreen:{article.slug_prefix}:{index}",
                post=post,
                html=body,
            )
        )
    return candidates
