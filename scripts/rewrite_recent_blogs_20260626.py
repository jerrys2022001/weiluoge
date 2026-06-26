#!/usr/bin/env python3
"""Rewrite and publish recent daily blog posts with stronger differentiation."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from blog_daily_scheduler import BLOG_INDEX_REL, SITEMAP_REL, PostMeta, update_blog_index, update_sitemap
from blog_seo_audit import validate_generated_article
from blog_similarity import load_blog_pages, max_similarity_against_existing
from site_tools import build_site_search_index, inject_site_tools_into_file

SITE_URL = "https://velocai.net"
THRESHOLD = 0.40


@dataclass(frozen=True)
class ArticleSpec:
    day: date
    filename: str
    title: str
    description: str
    topic: str
    product: str
    product_url: str
    image: str
    audience: str
    opener: str
    thesis: str
    sections: tuple[tuple[str, tuple[str, ...]], ...]
    checklist_title: str
    checklist_items: tuple[str, ...]
    stop_rule: str
    links: tuple[tuple[str, str], ...]
    sources: tuple[tuple[str, str], ...]
    faq: tuple[tuple[str, str], ...]
    keywords: tuple[str, ...]


def slug_date(value: str, day: date) -> str:
    return f"{value}-{day.isoformat()}.html"


def paragraph_block(paragraphs: tuple[str, ...]) -> str:
    return "\n".join(f"        <p>{paragraph}</p>" for paragraph in paragraphs)


def list_block(items: tuple[str, ...]) -> str:
    return "\n".join(f"          <li>{item}</li>" for item in items)


def render_article(spec: ArticleSpec) -> str:
    canonical = f"{SITE_URL}/blog/{spec.filename}"
    internal_links = "\n".join(
        f'        <a href="{href}">{escape(label)}</a>' for label, href in spec.links
    )
    source_links = "\n".join(
        f'          <li><a href="{href}" target="_blank" rel="noopener noreferrer">{escape(label)}</a></li>'
        for label, href in spec.sources
    )
    sections = "\n".join(
        f"""      <section>
        <h2>{heading}</h2>
{paragraph_block(paragraphs)}
      </section>"""
        for heading, paragraphs in spec.sections
    )
    faq_entities = [
        {
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {"@type": "Answer", "text": answer},
        }
        for question, answer in spec.faq
    ]
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "headline": spec.title,
                "description": spec.description,
                "datePublished": spec.day.isoformat(),
                "dateModified": spec.day.isoformat(),
                "author": {"@type": "Organization", "name": "VelocAI"},
                "publisher": {
                    "@type": "Organization",
                    "name": "VelocAI",
                    "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/velocai.png"},
                },
                "mainEntityOfPage": canonical,
                "keywords": list(spec.keywords),
            },
            {"@type": "FAQPage", "mainEntity": faq_entities},
        ],
    }
    keyword_text = ", ".join(spec.keywords)
    return f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(spec.title)} | VelocAI Blog</title>
  <meta name="description" content="{escape(spec.description)}">
  <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" type="image/x-icon" href="/velocai.ico">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="en_US">
  <meta property="og:site_name" content="VelocAI">
  <meta property="og:title" content="{escape(spec.title)}">
  <meta property="og:description" content="{escape(spec.description)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{SITE_URL}{spec.image}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(spec.title)}">
  <meta name="twitter:description" content="{escape(spec.description)}">
  <meta name="twitter:image" content="{SITE_URL}{spec.image}">
  <script type="application/ld+json">
{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}
  </script>
  <style>
    :root {{ --bg:#f7faf8; --text:#17221f; --muted:#53645e; --line:#d8e4df; --panel:#ffffff; --accent:#176b5f; --soft:#eaf5f1; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Avenir Next","Inter","Segoe UI",sans-serif; color:var(--text); background:var(--bg); line-height:1.72; }}
    a {{ color:inherit; text-decoration:none; }}
    .wrap {{ width:min(930px, calc(100% - 34px)); margin:0 auto; }}
    header {{ border-bottom:1px solid var(--line); background:rgba(247,250,248,.94); }}
    .top {{ padding:14px 0; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }}
    .brand {{ display:inline-flex; align-items:center; gap:10px; font-weight:700; }}
    .brand img {{ width:auto; height:36px; max-width:52px; object-fit:contain; object-position:center; border-radius:10px; box-shadow:0 0 16px rgba(23,107,95,.16); }}
    nav {{ display:flex; gap:12px; flex-wrap:wrap; color:var(--muted); font-size:14px; }}
    main {{ padding:36px 0 58px; }}
    article {{ display:grid; gap:22px; }}
    .hero {{ border-bottom:1px solid var(--line); padding-bottom:20px; }}
    h1,h2 {{ margin:0; line-height:1.2; letter-spacing:0; }}
    h1 {{ font-size:clamp(30px, 4vw, 48px); max-width:25ch; }}
    h2 {{ margin-top:6px; font-size:clamp(22px, 2.8vw, 31px); }}
    p,li {{ color:#30463f; font-size:17px; }}
    ul {{ padding-left:22px; }}
    section {{ padding:18px 0; border-bottom:1px solid var(--line); }}
    .meta {{ margin-top:10px; color:var(--muted); font-size:14px; }}
    .answer {{ margin-top:18px; padding:18px 20px; border-left:5px solid var(--accent); background:var(--soft); }}
    .check {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:20px; box-shadow:0 12px 28px rgba(18,38,32,.05); }}
    .links {{ display:flex; gap:12px; flex-wrap:wrap; }}
    .links a {{ border:1px solid #bfd4ce; border-radius:999px; padding:10px 14px; font-weight:700; font-size:14px; color:var(--accent); background:#fff; }}
  </style>
  <link rel="stylesheet" href="/assets/css/site-tools.css">
</head>
<body>
  <header>
    <div class="wrap top">
      <a class="brand" href="/"><img src="/velocai.png" alt="VelocAI logo" width="103" height="103"><span>VelocAI Blog</span></a>
      <nav aria-label="Main">
        <a href="/">Home</a>
        <a href="/apps/">Apps</a>
        <a href="/blog/">Blog</a>
        <a href="{spec.product_url}">{escape(spec.product)}</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <article>
      <div class="hero">
        <h1>{escape(spec.title)}</h1>
        <p class="meta">Published on {spec.day.strftime("%B %-d, %Y") if sys.platform != "win32" else spec.day.strftime("%B %#d, %Y")} | Topic: {escape(spec.topic)} | For {escape(spec.audience)}</p>
        <p>{spec.opener}</p>`n        <p class="meta">{escape(spec.product)} Practical Guide</p>
      </div>
      <div class="answer">
        <p>{spec.thesis}</p>
      </div>
{sections}
      <section class="check">
        <h2>{escape(spec.checklist_title)}</h2>
        <ul>
{list_block(spec.checklist_items)}
        </ul>
        <p><strong>Stop rule:</strong> {spec.stop_rule}</p>
      </section>
      <section>
        <h2>What should you read next?</h2>
        <p>Use the app page when you need the tool, then use the related guide only if the next decision is still unclear. The point is to shorten the work, not decorate the tab bar.</p>
        <div class="links">
{internal_links}
        </div>
      </section>
      <section>
        <h2>Which sources shaped the advice?</h2>
        <p>The outside links below are here for technical context and platform behavior. The workflow above is deliberately narrower than the news cycle.</p>
        <ul>
{source_links}
        </ul>
      </section>
      <section>
        <h2>What is the takeaway?</h2>
        <p>{escape(spec.product)} is most useful when the operator makes one specific decision before opening the app: what evidence, signal, or file state would actually change the next action. Everything else is just screen activity with a nicer icon.</p>
        <p class="meta">Keywords: {escape(keyword_text)}</p>
      </section>
    </article>
  </main>
  <script src="/assets/js/site-tools.js" defer></script>
</body>
</html>
"""


def specs() -> list[ArticleSpec]:
    d24 = date(2026, 6, 24)
    d25 = date(2026, 6, 25)
    d26 = date(2026, 6, 26)
    return [
        ArticleSpec(
            day=d24,
            filename=slug_date("dual-camera-warranty-unboxing-proof-guide", d24),
            title="Dual Camera Warranty Unboxing Proof Guide",
            description="Use Dual Camera to record package condition, serial labels, and first-power-on behavior when a warranty dispute may depend on clean visual proof.",
            topic="Warranty Unboxing Evidence",
            product="Dual Camera",
            product_url="/dualshot/",
            image="/dualshot/dualshot-camera-icon.png",
            audience="buyers documenting expensive electronics",
            opener="A warranty video fails when it looks like a product demo. The boring parts, tape seams, shipping dents, serial labels, and the first boot, are exactly the parts you need later.",
            thesis="Record one wide view for chain-of-custody context and one close view for defects or labels. Stop trying to make the clip pretty; make it hard to argue with.",
            sections=(
                ("What must the clip prove?", ("The useful record shows the package before you touch it, the product as it leaves the box, and the first moment the issue appears. A single tight shot usually misses one of those three pieces.", "Dual Camera helps because the wide frame keeps your hands and the box in view while the close frame catches label text or damage detail.")),
                ("Where do disputes usually start?", ("Disputes start in the gap between a receipt and a defect claim. If the video only shows the broken corner after the box is open, the seller can still ask whether the damage happened during setup.", "Keep the shipping label, seal, and device serial in the same timeline. Not because everyone is out to reject claims, but because support queues reward clean evidence.")),
                ("How should you apply it?", ("Put the iPhone on a stable surface at a slight angle above the table. Do a five-second audio note naming the order number or product model, then do not pause until the first inspection is complete.", "If the close camera cannot read the serial label, move the item instead of moving the phone. Camera shake makes the whole record feel improvised.")),
                ("What tradeoff is worth accepting?", ("The clip may be longer than a normal social video. That is fine. Trimmed highlight reels look better, but continuous clips are stronger when the question is what happened before the defect was visible.",)),
            ),
            checklist_title="The five-minute warranty pass",
            checklist_items=("Show sealed package sides before cutting tape.", "Keep serial labels readable for at least three seconds.", "Capture the first-power-on screen or failed boot behavior.", "Say the date and product model once at the start.", "Save the original file before sending a compressed copy."),
            stop_rule="If the issue involves electric smell, heat, swelling, or broken glass, stop recording and follow the manufacturer safety instructions first.",
            links=(("Open Dual Camera", "/dualshot/"), ("Compare field evidence tips", "/blog/dual-camera-safety-briefing-recording-guide-2026-06-16.html"), ("Browse VelocAI apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("Apple Support: service and repair", "https://support.apple.com/repair"), ("FTC: warranties", "https://consumer.ftc.gov/articles/warranties"), ("Apple Support: back up iPhone", "https://support.apple.com/iphone/backup")),
            faq=(("Should I record the whole unboxing for a warranty claim?", "Yes, when the item is expensive or fragile. Continuous context usually matters more than a polished close-up."), ("Can Dual Camera replace official repair documentation?", "No. It helps preserve visual proof, but manufacturer instructions and service records still come first."), ("What should be visible in a warranty video?", "The sealed package, serial label, product condition, and first failure should be visible in the same timeline.")),
            keywords=("Dual Camera", "warranty unboxing video", "iPhone product evidence", "serial label recording"),
        ),
        ArticleSpec(
            day=d24,
            filename=slug_date("bluetooth-explorer-warehouse-rssi-walk-test-guide", d24),
            title="Bluetooth Explorer Warehouse RSSI Walk Test",
            description="Use Bluetooth Explorer during a warehouse walk test to separate weak beacon placement, aisle shadowing, and scanner mistakes before moving hardware.",
            topic="Warehouse RSSI Walk Test",
            product="Bluetooth Explorer",
            product_url="/bluetoothexplorer/",
            image="/apps/bluetooth-explorer-icon.png",
            audience="ops teams checking beacon coverage",
            opener="Warehouse Bluetooth problems often get blamed on the nearest beacon, which is convenient and frequently wrong. Shelving, forklifts, body blocking, and scan cadence can all make a good beacon look guilty.",
            thesis="Use Bluetooth Explorer as a repeatable walk-test notebook: same path, same phone position, same scan window, then compare RSSI movement against the physical aisle map.",
            sections=(
                ("What are you trying to isolate?", ("You are not looking for one magic RSSI number. You are looking for repeatable drop zones where the same beacon fades in the same physical place.", "That distinction matters. A random dip says little; a dip that appears at the end of aisle 7 every pass is a placement or obstruction problem.")),
                ("Where should the walk begin?", ("Start outside the dense rack area and record a baseline for thirty seconds. Then walk the planned route at normal worker speed without waving the phone around.", "Phone gymnastics make the data entertaining and useless. Keep the device in the same hand position you expect during real work.")),
                ("How do you read noisy RSSI?", ("RSSI is allowed to be ugly. Look for bands, not single readings: strong near the anchor, unstable near metal corners, and missing where goods or walls cut the path.", "If two passes disagree completely, inspect the scan setup before moving tags. The test may be measuring operator behavior instead of radio behavior.")),
                ("When is hardware movement justified?", ("Move hardware only after the same weak zone appears across at least two passes and one control phone. Otherwise you may be rearranging the warehouse around a flaky test.",)),
            ),
            checklist_title="Walk-test discipline",
            checklist_items=("Use one route map and mark timestamps at aisle turns.", "Keep the phone height and orientation consistent.", "Run at least two passes before changing beacon placement.", "Compare one known-good beacon against the suspect beacon.", "Write down nearby metal doors, chargers, and dense inventory."),
            stop_rule="If workers depend on the beacon for safety or compliance, do not rely on a phone walk test alone; schedule a proper RF survey.",
            links=(("Open Bluetooth Explorer", "/bluetoothexplorer/"), ("Read RSSI variation guide", "/blog/bluetooth-industry-update-why-is-there-variation-of-rssi-2026-05-19.html"), ("Browse apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("Bluetooth SIG: Bluetooth technology overview", "https://www.bluetooth.com/learn-about-bluetooth/tech-overview/"), ("Apple Developer: Core Bluetooth", "https://developer.apple.com/bluetooth/"), ("BeaconZone: RSSI variation", "https://www.beaconzone.co.uk/blog/why-is-there-variation-of-rssi/")),
            faq=(("Is one RSSI reading enough for beacon placement?", "No. Placement decisions need repeated readings across the same path and phone position."), ("Why does RSSI change in a warehouse?", "Metal racks, moving people, inventory density, and scanner orientation can all change the observed signal."), ("Can Bluetooth Explorer replace an RF survey?", "No. It is useful for early field checks, but high-risk deployments need professional measurement.")),
            keywords=("bluetooth", "Bluetooth Explorer", "warehouse RSSI", "BLE beacon walk test"),
        ),
        ArticleSpec(
            day=d24,
            filename=slug_date("find-ai-gym-locker-signal-recovery-guide", d24),
            title="Find AI Gym Locker Signal Recovery Guide",
            description="Use find AI after a gym or studio visit to narrow a missing tracker search by locker row, signal fade, movement history, and practical stop rules.",
            topic="Gym Locker Recovery",
            product="find AI",
            product_url="/aifind/",
            image="/aifind/find-ai-icon.png",
            audience="people searching crowded lockers",
            opener="Locker rooms are terrible search environments because everything is close, reflective, and moving. Your missing earbuds may be three feet away and still feel like a ghost signal.",
            thesis="Treat find AI as a narrowing tool, not a metal detector. Confirm the device category, walk the locker rows slowly, and stop when the signal pattern stops improving.",
            sections=(
                ("What makes gyms different?", ("A gym packs phones, watches, earbuds, padlocks, and wet walls into a small area. That creates more false confidence than distance.", "The right move is not to chase every spike. Walk one row, pause, turn around, and see whether the same area remains stronger.")),
                ("How should you scan the lockers?", ("Start at the entrance to establish a weak baseline. Then move row by row with the phone held low enough to match locker height.", "If the signal improves near one bank, do a second pass from the opposite direction. Real leads tend to survive the direction change; reflections often do not.")),
                ("What should you ask staff?", ("Ask whether a lost-property sweep has already happened and whether cleaners moved bags from the locker area. That one question can save twenty minutes of scanning the wrong room.", "Do not ask staff to interpret RSSI. Ask them about movement: what got cleared, when, and where it was placed.")),
                ("When is the search over?", ("The search is over when two full passes show no stronger area and staff confirm the room was cleared. At that point, switch to account-level lost-device steps instead of pacing the same row again.",)),
            ),
            checklist_title="Locker-room search order",
            checklist_items=("Confirm the missing item can still advertise a Bluetooth signal.", "Scan from the room entrance before touching lockers.", "Walk each row twice from opposite directions.", "Ask staff about cleaning carts and lost-property bins.", "Write down the last strong area before leaving."),
            stop_rule="If the item may be inside another person's locker or bag, stop and involve staff instead of trying to verify it yourself.",
            links=(("Open find AI", "/aifind/"), ("Use the school bag recovery guide", "/blog/find-ai-school-bag-backpack-recovery-guide-2026-06-16.html"), ("Read Bluetooth discovery checklist", "/blog/bluetooth-device-discovery-debugging-checklist-2026-03-04.html"), ("Back to blog index", "/blog/")),
            sources=(("Apple Support: Find My", "https://support.apple.com/find-my"), ("Bluetooth SIG: Bluetooth location services", "https://www.bluetooth.com/learn-about-bluetooth/feature-enhancements/location-services/"), ("Apple Support: AirPods service", "https://support.apple.com/airpods")),
            faq=(("Can find AI identify the exact locker?", "No. It can help narrow the strongest area, but walls, bags, and metal doors can distort the signal."), ("How many passes should I do in a locker room?", "Two slow passes from opposite directions are usually enough before asking staff about moved items."), ("What if the signal is strong but access is private?", "Stop and ask staff to handle the situation. Do not open or pressure anyone's locker.")),
            keywords=("find AI", "Bluetooth locker search", "lost earbuds gym", "signal recovery"),
        ),
        ArticleSpec(
            day=d24,
            filename=slug_date("octopus-hotfix-diff-review-phone-guide", d24),
            title="Octopus Hotfix Diff Review From a Phone",
            description="Use Octopus for a phone-based hotfix review by checking changed files, failure signals, risk boundaries, and when to hand the work back to a laptop.",
            topic="Mobile Hotfix Review",
            product="Octopus",
            product_url="/octopus/",
            image="/octopus/octopus-icon.png",
            audience="developers reviewing urgent patches away from a desk",
            opener="A phone is fine for approving a tiny hotfix and bad for pretending you reviewed a system rewrite. The difference is not screen size; it is whether you can inspect the risk surface without guessing.",
            thesis="Use Octopus when the diff is narrow, the tests are explicit, and the rollback story is boring. If any of those are missing, the phone flow has reached its limit.",
            sections=(
                ("What counts as phone-sized?", ("A phone-sized hotfix changes one behavior path, one config value, or one isolated copy error. It does not touch migrations, auth, billing, or shared state without a second reviewer at a real keyboard.", "The practical threshold is simple: if you cannot explain every changed file in one breath, do not approve from the phone.")),
                ("Which state should you inspect?", ("Start with the file list, then the exact diff, then the failing signal that motivated the patch. A hotfix with no failure signal is just a rushed change wearing a pager badge.", "Octopus is useful because you can keep the thread, diff, and notes together while you decide whether the patch actually addresses the symptom.")),
                ("What risk does the step reduce?", ("The review reduces accidental scope creep. You are checking whether the fix stayed inside the blast radius promised by the incident note.", "If the patch also cleans up nearby code, politely reject that part. Cleanup can wait. Production is already having a day.")),
                ("When is the iPad still not enough?", ("Move to a laptop when you need to run a full local reproduction, inspect generated artifacts, compare screenshots, or resolve conflicts. Bigger glass helps, but only if the environment can prove the change.",)),
            ),
            checklist_title="Phone approval gate",
            checklist_items=("Name the incident signal before reading the diff.", "Confirm every changed file belongs to the same fix.", "Check that tests or monitoring cover the failed path.", "Write the rollback command or owner in the thread.", "Reject opportunistic refactors bundled into the hotfix."),
            stop_rule="If the change touches credentials, payment flow, migrations, or permission checks, stop and require a full workstation review.",
            links=(("Open Octopus", "/octopus/"), ("Read runtime status workflow", "/blog/octopus-runtime-status-live-activity-guide-2026-06-16.html"), ("Browse apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("GitHub Docs: reviewing changes in pull requests", "https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests"), ("GitHub Docs: reverting a pull request", "https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reverting-a-pull-request"), ("OpenAI Codex", "https://openai.com/codex/")),
            faq=(("Can Octopus be used for hotfix review on a phone?", "Yes, when the diff is narrow, tests are visible, and rollback ownership is clear."), ("What should not be approved from a phone?", "Auth, billing, migrations, broad refactors, and changes without a clear failure signal should wait for a full workstation."), ("What is the main risk in mobile hotfix approval?", "The main risk is approving hidden scope because the reviewer did not inspect every changed file and test signal.")),
            keywords=("Octopus", "mobile coding workflow", "hotfix review", "phone diff review"),
        ),
        ArticleSpec(
            day=d25,
            filename=slug_date("dual-camera-cooking-class-overhead-demo-guide", d25),
            title="Dual Camera Cooking Class Overhead Demo",
            description="Use Dual Camera for cooking classes when one view must show hand technique and another must show pan timing, texture, and heat cues.",
            topic="Cooking Class Demo Capture",
            product="Dual Camera",
            product_url="/dualshot/",
            image="/dualshot/dualshot-camera-icon.png",
            audience="instructors recording practical cooking lessons",
            opener="Cooking videos fail when the camera admires the finished plate and misses the thirty seconds where the sauce actually changed. Students need the boring middle, not only the pretty ending.",
            thesis="Use one lens above the hands and one lens near the pan or bowl. The point is to capture timing, texture, and tool angle in the same take.",
            sections=(
                ("What should be captured before erasing?", ("Capture the final board, the discarded option that nearly won, and the owner for the next step. Most teams only save the board, then spend the next day reconstructing the argument in chat.", "Dual Camera helps because the board can stay visible while the speaker points to the tradeoff that made the decision stick.")),
                ("Who should narrate the handoff?", ("Pick the person who can explain what changed during the meeting, not the person with the loudest calendar invite. The narration should name the decision, the rejected path, and the next review date.", "If nobody can say that in one minute, the meeting did not produce a decision. Congratulations, you recorded a mural.")),
                ("Where does this beat a normal photo?", ("A photo stores state. The short narration stores intent. That matters when the remote teammate asks why the team chose a narrower launch, a different metric, or an ugly interim workaround.", "Keep the clip under two minutes. Long recordings become homework, and homework disguised as alignment usually rots unread.")),
                ("When should the phone stay away?", ("Do not record sensitive customer data, credentials, hiring notes, or private personnel topics on a shared planning clip. Rewrite the board first or use a controlled document.",)),
            ),
            checklist_title="Cooking demo pass",
            checklist_items=("Lock the phone before heat or knives are active.", "Keep one view on hands and one on the pan or bowl.", "Name the texture cue before it appears.", "Hold the close view through the irreversible step.", "Stop the clip when the technique is complete."),
            stop_rule="If the recording position changes safe knife handling or hot-pan movement, stop and move the phone before continuing.",
            links=(("Open Dual Camera", "/dualshot/"), ("Read small-team shoot guide", "/blog/dualshot-camera-small-team-shoot-efficiency-guide-2026-06-15.html"), ("Browse apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("Apple Support: record videos", "https://support.apple.com/guide/iphone/record-videos-iph61f49e4bb/ios"), ("USDA: safe minimum internal temperatures", "https://www.foodsafety.gov/food-safety-charts/safe-minimum-internal-temperatures"), ("FDA: food safety in your kitchen", "https://www.fda.gov/food/buy-store-serve-safe-food/food-safety-your-kitchen")),
            faq=(("Why use two camera views for cooking instruction?", "One view can show hand technique while the other shows pan texture, heat response, or bowl consistency."), ("How long should a cooking demo clip be?", "Keep it to one technique or irreversible step so learners can replay the useful part quickly."), ("What should stop a cooking recording?", "Unsafe phone placement around knives, hot oil, or heavy cookware should stop the recording until the station is reset.")),
            keywords=("Dual Camera", "cooking class video", "overhead demo", "iPhone tutorial recording"),
        ),
        ArticleSpec(
            day=d25,
            filename=slug_date("bluetooth-explorer-auracast-room-readiness-guide", d25),
            title="Bluetooth Explorer Auracast Room Readiness",
            description="Use Bluetooth Explorer to prepare an Auracast-style room check by mapping discoverable broadcasts, receiver expectations, and interference risks.",
            topic="Auracast Room Readiness",
            product="Bluetooth Explorer",
            product_url="/bluetoothexplorer/",
            image="/apps/bluetooth-explorer-icon.png",
            audience="venue teams planning shared audio",
            opener="A shared-audio room can look ready because the speakers sound fine. That says almost nothing about whether people can discover the right broadcast from the seats that matter.",
            thesis="Use Bluetooth Explorer before the event to map what a listener device can see, which names are confusing, and where the room makes discovery unreliable.",
            sections=(
                ("What does readiness mean?", ("Readiness means a visitor can identify the intended broadcast quickly and keep it visible from normal seating areas. It is not just whether the transmitter powers on.", "The room name, broadcast label, and staff script should match. If the phone sees three similar names, the setup is already hostile.")),
                ("Where should scans happen?", ("Scan at the entrance, the front row, the back row, and one obstructed seat. These four positions catch most obvious surprises without turning prep into a lab project.", "If the broadcast disappears only behind a pillar or metal partition, mark that seat area and adjust signage or equipment placement.")),
                ("What should staff rehearse?", ("Staff should know the exact broadcast name and the fallback plan. Bluetooth Explorer can show whether the name visible on test devices matches what staff plan to say.", "That tiny naming check prevents a lot of shoulder-tapping during the first ten minutes of an event.")),
                ("When is a deeper test needed?", ("Do a deeper test when the room is large, accessibility-critical, or has multiple simultaneous broadcasts. Casual checks are not enough when people depend on the audio feed.",)),
            ),
            checklist_title="Room readiness pass",
            checklist_items=("Confirm the visible broadcast name from visitor seating.", "Check entrance, front, back, and obstructed seats.", "Remove stale or confusing broadcast labels.", "Write a one-sentence staff fallback script.", "Repeat the scan after the room fills if possible."),
            stop_rule="If the feed supports accessibility accommodations, do not call the room ready until real receiver devices have been tested.",
            links=(("Open Bluetooth Explorer", "/bluetoothexplorer/"), ("Read Auracast background", "/blog/bluetooth-industry-update-the-story-of-auracast-tm-broadcast-audio-2026-03-19.html"), ("Browse apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("Bluetooth SIG: Auracast broadcast audio", "https://www.bluetooth.com/auracast/"), ("Bluetooth SIG: location services", "https://www.bluetooth.com/learn-about-bluetooth/feature-enhancements/location-services/"), ("Apple Developer: Core Bluetooth", "https://developer.apple.com/bluetooth/")),
            faq=(("Can Bluetooth Explorer test every Auracast receiver feature?", "No. It helps inspect discoverability and nearby Bluetooth signals, but final acceptance needs real receiver devices."), ("Where should I scan a shared-audio room?", "Scan the entrance, front row, back row, and one obstructed seat before the room fills."), ("Why do broadcast names matter?", "Visitors need to pick the right feed quickly, so confusing or duplicate names create support work.")),
            keywords=("bluetooth", "Bluetooth Explorer", "Auracast", "broadcast audio room"),
        ),
        ArticleSpec(
            day=d25,
            filename=slug_date("find-ai-airport-security-bin-recovery-guide", d25),
            title="Find AI Airport Security Bin Recovery",
            description="Use find AI after airport security to narrow a missing-item search by checkpoint lane, tray movement, Bluetooth visibility, and staff handoff timing.",
            topic="Airport Security Recovery",
            product="find AI",
            product_url="/aifind/",
            image="/aifind/find-ai-icon.png",
            audience="travelers who lost small devices at screening",
            opener="Airport security creates a special kind of panic: your bag moved, the tray moved, you moved, and now the signal looks close but the item is behind a process you do not control.",
            thesis="Use find AI to narrow the checkpoint zone, then switch from searching to asking precise staff questions. Wandering near secure equipment is not a recovery strategy.",
            sections=(
                ("What should you confirm first?", ("Confirm whether the missing item is still advertising and whether you last saw it before or after the tray entered the scanner.", "That timeline decides whether you ask about a bin, a secondary inspection table, or a lost-property handoff.")),
                ("How do you scan without getting in the way?", ("Stand in public waiting space and scan from stable positions. If the signal strengthens near the belt exit, do not crowd the lane; tell staff the lane number and item type.", "The useful observation is location trend, not exact inches. Security areas are not the place for experimental pacing.")),
                ("What should you ask staff?", ("Ask when bins from that lane were cleared and where small electronics are held. Give a color, case shape, and last-seen tray detail.", "A precise question beats a dramatic one. Staff can act on lane, time, and object description.")),
                ("When should you stop scanning?", ("Stop when staff have checked the lane and the signal no longer improves from public areas. Continue with airline or airport lost-property reporting instead of orbiting the checkpoint.",)),
            ),
            checklist_title="Checkpoint recovery order",
            checklist_items=("Note checkpoint lane and approximate time.", "Scan only from public or allowed waiting areas.", "Compare signal near belt exit and seating area.", "Give staff a concise object description.", "File lost-property details before boarding if time is short."),
            stop_rule="If the item appears to be inside a restricted area, stop scanning and hand the details to airport staff.",
            links=(("Open find AI", "/aifind/"), ("Use gym locker recovery", "/blog/find-ai-gym-locker-signal-recovery-guide-2026-06-24.html"), ("Browse apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("TSA: lost and found", "https://www.tsa.gov/contact/lost-and-found"), ("Apple Support: Find My", "https://support.apple.com/find-my"), ("Bluetooth SIG: Bluetooth overview", "https://www.bluetooth.com/learn-about-bluetooth/tech-overview/")),
            faq=(("Can find AI recover an item inside airport security?", "It can help narrow the area, but staff must handle restricted spaces and screening equipment."), ("What information helps airport staff most?", "Checkpoint lane, approximate time, tray detail, item color, and case shape are more useful than vague signal claims."), ("Should I keep scanning if boarding is close?", "File the airport lost-property report before boarding if staff cannot resolve it quickly.")),
            keywords=("find AI", "airport lost item", "Bluetooth tracker recovery", "security bin"),
        ),
        ArticleSpec(
            day=d25,
            filename=slug_date("octopus-release-note-approval-mobile-guide", d25),
            title="Octopus Release Note Approval on Mobile",
            description="Use Octopus to approve release notes from a phone by checking user-visible change scope, screenshots, risk language, and launch blockers.",
            topic="Mobile Release Approval",
            product="Octopus",
            product_url="/octopus/",
            image="/octopus/octopus-icon.png",
            audience="founders and PMs reviewing launches while mobile",
            opener="Release notes written on a deadline tend to lie by omission. Not maliciously, just in the normal way teams say fixed when they really mean reduced a very specific failure.",
            thesis="Use Octopus for mobile approval only when you can inspect the changed user path, the exact release note, and the known limitation in the same thread.",
            sections=(
                ("What are you approving?", ("You are approving a public claim, not a feeling that the build is probably fine. The release note should name the user-visible change and avoid promising more than the code shipped.", "If the note says faster, ask for the number or remove the adjective. Vague speed claims age badly.")),
                ("Which artifacts matter?", ("Check the diff, screenshot or screen recording, test result, and final text. If one of those is missing, approval from a phone becomes vibes with notifications.", "Octopus works well here because the approval thread can keep all four artifacts together instead of scattering them through chat.")),
                ("Where does mobile review fail?", ("Mobile review fails when a tiny screen hides copy overflow, localization problems, or an empty state. Ask for the failure-state screenshot, not only the happy path.", "This is the part people skip because the release is almost done. That is exactly why it catches real issues.")),
                ("When should approval wait?", ("Wait when the note changes pricing expectations, privacy language, migration steps, or support obligations. Those deserve a proper desk review and probably another person.",)),
            ),
            checklist_title="Release-note approval gate",
            checklist_items=("Compare final wording against the actual changed path.", "Request one screenshot or recording of the feature state.", "Remove adjectives that lack evidence.", "Check whether support needs a warning or macro update.", "Leave a clear approve or block comment in the thread."),
            stop_rule="If the release note mentions privacy, pricing, data migration, or security, stop and route it through the normal review owner.",
            links=(("Open Octopus", "/octopus/"), ("Read hotfix review guide", "/blog/octopus-hotfix-diff-review-phone-guide-2026-06-24.html"), ("Browse apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("GitHub Docs: release notes", "https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes"), ("Apple Developer: App Store Review Guidelines", "https://developer.apple.com/app-store/review/guidelines/"), ("OpenAI Codex", "https://openai.com/codex/")),
            faq=(("Can release notes be approved from a phone?", "Yes, if the reviewer can inspect the changed path, evidence, final wording, and limitation in one place."), ("What should block mobile release-note approval?", "Privacy, pricing, security, migration, and support-impact changes should wait for the normal review path."), ("Why are screenshots important for release notes?", "They expose copy overflow, empty states, and mismatches between the shipped feature and the public claim.")),
            keywords=("Octopus", "mobile coding workflow", "release note approval", "phone review"),
        ),
        ArticleSpec(
            day=d26,
            filename=slug_date("dual-camera-repair-counter-evidence-guide", d26),
            title="Dual Camera Repair Counter Evidence Guide",
            description="Use Dual Camera at a repair counter to capture device condition, intake notes, visible defects, and pickup proof without turning the visit into a fight.",
            topic="Repair Counter Evidence",
            product="Dual Camera",
            product_url="/dualshot/",
            image="/dualshot/dualshot-camera-icon.png",
            audience="customers documenting device repair handoff",
            opener="Repair handoffs are awkward because nobody wants to imply distrust. Still, a thirty-second condition record is kinder than a two-week argument about when a scratch appeared.",
            thesis="Use Dual Camera to document the device before intake and after pickup: one frame for counter context, one frame for serials, cracks, ports, and screen state.",
            sections=(
                ("What problem does this help solve?", ("Record the device powered on if possible, then show the exterior, ports, screen, camera glass, and any existing damage. Keep the counter or paperwork visible in the wide frame.", "The close frame should linger on the problem area and serial label. If the label is private, record enough context for yourself and avoid sharing that clip publicly.")),
                ("How should you apply it?", ("Say what you are doing plainly: I am recording the condition before I leave it. Then keep the clip short.", "Most awkwardness comes from filming people, not objects. Aim at the device and paperwork, not employee faces.")),
                ("What matters at pickup?", ("Repeat the same pass before leaving. Check the repaired feature, the screen, ports, and any accessories returned with the device.", "If something looks wrong, raise it at the counter while the handoff is still fresh. Parking-lot discoveries are harder to resolve.")),
                ("What should you check next?", ("If a shop forbids recording, ask for written condition notes and photos in the intake record. The goal is documentation, not confrontation.",)),
            ),
            checklist_title="Repair handoff record",
            checklist_items=("Capture powered-on state when possible.", "Show existing scratches or cracks before intake.", "Keep paperwork or counter context in the wide frame.", "Repeat the same pass at pickup.", "Store the original clip until the warranty window closes."),
            stop_rule="If recording violates shop policy or local rules, stop and ask for written condition notes instead.",
            links=(("Open Dual Camera", "/dualshot/"), ("Read warranty unboxing proof", "/blog/dual-camera-warranty-unboxing-proof-guide-2026-06-24.html"), ("Browse apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("Apple Support: prepare for service", "https://support.apple.com/iphone/repair"), ("FTC: warranties", "https://consumer.ftc.gov/articles/warranties"), ("Apple Support: back up iPhone", "https://support.apple.com/iphone/backup")),
            faq=(("Should I record a repair handoff?", "A short device-condition record can help, especially for expensive devices or visible damage."), ("Should repair staff be filmed?", "Avoid filming faces. Focus on the device, paperwork, and visible condition."), ("What if recording is not allowed?", "Ask for written condition notes or official intake photos instead.")),
            keywords=("Dual Camera", "repair counter video", "device handoff proof", "iPhone repair evidence"),
        ),
        ArticleSpec(
            day=d26,
            filename=slug_date("bluetooth-explorer-device-name-collision-guide", d26),
            title="Bluetooth Explorer Device Name Collision",
            description="Use Bluetooth Explorer to diagnose duplicate Bluetooth names, mislabeled accessories, and support mistakes before resetting every device in the room.",
            topic="Device Name Collision",
            product="Bluetooth Explorer",
            product_url="/bluetoothexplorer/",
            image="/apps/bluetooth-explorer-icon.png",
            audience="support teams sorting crowded device lists",
            opener="Duplicate Bluetooth names are a support trap. Everyone says connect to the speaker, then three identical speakers appear and the wrong one gets blamed for the failure.",
            thesis="Use Bluetooth Explorer to separate human-readable names from underlying signal identity. Rename, label, or retire devices only after you know which collision is real.",
            sections=(
                ("What is actually colliding?", ("A visible name collision is not always a device collision. Two accessories can share a friendly name while advertising different identifiers, service data, or signal patterns.", "That is why resetting everything is lazy. It may work, but it destroys evidence before you understand the room.")),
                ("How should support triage it?", ("Stand near the expected device and watch which signal strengthens. Then move toward the second candidate and compare. The wrong device often reveals itself by staying strong in the wrong place.", "Write down the physical label, friendly name, and approximate location. Support tickets need those three fields, not a screenshot of chaos.")),
                ("Where do naming policies help?", ("Room names, asset tags, and accessory labels should match. If the sticker says Studio A but the Bluetooth name says Speaker, the system is asking users to fail.", "Rename only after confirming the device, then record the new convention so the next replacement does not recreate the mess.")),
                ("When should you reset?", ("Reset after identity is confirmed and the device still refuses the correct pairing path. Resetting first is a satisfying button press and a poor diagnostic habit.",)),
            ),
            checklist_title="Name-collision triage",
            checklist_items=("List every duplicate visible name before touching settings.", "Move near each physical candidate and compare signal change.", "Match friendly name to room label or asset tag.", "Rename one device at a time and retest.", "Document the final naming rule for replacements."),
            stop_rule="If the device belongs to medical, access-control, or safety equipment, stop and follow the vendor's managed-device process.",
            links=(("Open Bluetooth Explorer", "/bluetoothexplorer/"), ("Use warehouse RSSI walk test", "/blog/bluetooth-explorer-warehouse-rssi-walk-test-guide-2026-06-24.html"), ("Browse apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("Apple Support: pair Bluetooth accessories", "https://support.apple.com/en-us/HT204091"), ("Bluetooth SIG: assigned numbers", "https://www.bluetooth.com/specifications/assigned-numbers/"), ("Apple Developer: Core Bluetooth", "https://developer.apple.com/bluetooth/")),
            faq=(("Why do multiple Bluetooth devices show the same name?", "Manufacturers often ship the same friendly name across devices, and teams may forget to rename replacements."), ("Should I reset duplicate Bluetooth devices first?", "No. Identify the physical device and signal pattern first, then reset only if pairing still fails."), ("How can teams prevent name collisions?", "Use room names or asset tags in the visible device name and document the naming rule.")),
            keywords=("bluetooth", "Bluetooth Explorer", "duplicate device names", "Bluetooth support"),
        ),
        ArticleSpec(
            day=d26,
            filename=slug_date("find-ai-hotel-room-checkout-sweep-guide", d26),
            title="Find AI Hotel Checkout Room Sweep Guide",
            description="Use find AI before hotel checkout to scan for earbuds, trackers, and small Bluetooth devices while the room is still accessible.",
            topic="Hotel Checkout Sweep",
            product="find AI",
            product_url="/aifind/",
            image="/aifind/find-ai-icon.png",
            audience="travelers doing final room checks",
            opener="The cheapest time to find lost earbuds is before the elevator doors close. After checkout, every missing item becomes a front-desk workflow with a queue and a housekeeping cart.",
            thesis="Use find AI as a final sweep: scan from the doorway, bed, desk, and bathroom, then inspect the places where the signal changes instead of dumping every bag again.",
            sections=(
                ("Where should the sweep start?", ("Start at the doorway with bags still open. That gives you a baseline before you walk into the strongest part of the room.", "Then scan near the bed, desk, outlets, sofa, and bathroom counter. These are the zones where small devices hide because people charge, change clothes, or empty pockets there.")),
                ("How do you avoid false panic?", ("A nearby room can produce a confusing signal. If the reading is stronger near the shared wall but never improves inside your room, do not tear apart the suitcase.", "Instead, check your own high-probability surfaces first: sheets, bedside gaps, chair cushions, and cable pouches.")),
                ("What should happen before checkout?", ("If the signal points to bedding or laundry, call the front desk before leaving and ask them to note the room number and item description.", "Housekeeping moves fast. A note made before checkout has a better chance than a memory sent six hours later.")),
                ("When do you file a report?", ("File a report when the item is not recovered after the sweep but the last known location is still the hotel. Include room number, checkout time, item color, and case description.",)),
            ),
            checklist_title="Checkout sweep path",
            checklist_items=("Keep bags open until the first scan is complete.", "Scan doorway, bed, desk, outlets, sofa, and bathroom.", "Check bedding and chair gaps before luggage.", "Tell the front desk before leaving if signal points to laundry.", "Save room number and checkout time in the report."),
            stop_rule="If the signal appears to come from another occupied room, stop and ask hotel staff to handle the next step.",
            links=(("Open find AI", "/aifind/"), ("Read airport bin recovery", "/blog/find-ai-airport-security-bin-recovery-guide-2026-06-25.html"), ("Browse apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("Apple Support: Find My", "https://support.apple.com/find-my"), ("Bluetooth SIG: location services", "https://www.bluetooth.com/learn-about-bluetooth/feature-enhancements/location-services/"), ("FTC: travel tips", "https://consumer.ftc.gov/consumer-alerts/2024/05/planning-trip-avoid-travel-scams")),
            faq=(("When should I scan a hotel room for lost earbuds?", "Scan before checkout while the room is still accessible and bags are open."), ("Can a signal come from another hotel room?", "Yes. Shared walls and nearby devices can confuse proximity, so staff should handle cross-room checks."), ("What should I include in a hotel lost-item report?", "Include room number, checkout time, item color, case description, and where the signal was strongest.")),
            keywords=("find AI", "hotel lost earbuds", "Bluetooth room sweep", "checkout checklist"),
        ),
        ArticleSpec(
            day=d26,
            filename=slug_date("octopus-mobile-test-failure-triage-guide", d26),
            title="Octopus Mobile Test Failure Triage",
            description="Use Octopus from a phone or iPad to triage failed tests by reading the failing assertion, recent diff, artifact state, and escalation boundary.",
            topic="Mobile Test Failure Triage",
            product="Octopus",
            product_url="/octopus/",
            image="/octopus/octopus-icon.png",
            audience="developers checking CI while away from the laptop",
            opener="A red CI badge on your phone is not a command to start guessing. It is a request to decide whether the failure is obvious, owned, and small enough to handle mobile.",
            thesis="Use Octopus to inspect the failed assertion, changed files, and artifact state. Fix from mobile only when the cause is narrow; otherwise leave a useful handoff.",
            sections=(
                ("What signal comes first?", ("Read the failing assertion before reading chat. Chat will happily give you five theories and no stack trace.", "The assertion tells you whether this is a snapshot drift, timeout, missing fixture, environment problem, or real behavior break.")),
                ("How do you compare against the diff?", ("Match the failure to the changed files. If the failing test is outside the touched area, slow down. It may still be related, but the phone is no place for heroic dependency archaeology.", "Octopus helps by keeping the thread and diff close enough that you can write a clean triage note without reopening half the project.")),
                ("Which artifacts matter?", ("Screenshots, logs, coverage changes, and build metadata matter more than the red badge itself. A screenshot diff can justify a mobile copy fix; a flaky timeout usually cannot.", "If artifacts are expired or missing, your next action is to rerun or hand off, not invent a diagnosis.")),
                ("When is mobile enough?", ("Mobile is enough for typo fixes, fixture path corrections, obvious expectation updates, or a clear revert. It is not enough for cross-service behavior or race conditions.",)),
            ),
            checklist_title="CI triage from mobile",
            checklist_items=("Read the exact failing assertion first.", "Map the failed test to changed files.", "Open screenshots or logs before proposing a fix.", "Decide fix, rerun, revert, or handoff in one comment.", "Mention what you did not verify."),
            stop_rule="If the failure involves timing, data races, migrations, or shared auth state, stop and hand it to a workstation session.",
            links=(("Open Octopus", "/octopus/"), ("Read hotfix review guide", "/blog/octopus-hotfix-diff-review-phone-guide-2026-06-24.html"), ("Browse apps", "/apps/"), ("Back to blog index", "/blog/")),
            sources=(("GitHub Docs: viewing workflow runs", "https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/viewing-workflow-run-history"), ("GitHub Docs: workflow artifacts", "https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts"), ("OpenAI Codex", "https://openai.com/codex/")),
            faq=(("Can I fix CI failures from a phone?", "Yes, but only for narrow failures with clear assertions and artifacts."), ("What should I read before chat theories?", "Read the failing assertion, changed files, and logs or screenshots first."), ("When should mobile CI triage stop?", "Stop when the failure involves timing, shared state, migrations, or missing artifacts.")),
            keywords=("Octopus", "mobile coding workflow", "CI triage", "test failure review"),
        ),
    ]


def publish(repo_root: Path, dry_run: bool) -> int:
    blog_dir = repo_root / "blog"
    index_path = repo_root / BLOG_INDEX_REL
    sitemap_path = repo_root / SITEMAP_REL
    existing_pages = load_blog_pages(blog_dir)
    pending: list[tuple[ArticleSpec, str, float, PostMeta]] = []

    for spec in specs():
        html = render_article(spec)
        expected = f"{SITE_URL}/blog/{spec.filename}"
        seo = validate_generated_article(html, expected_canonical=expected)
        if seo.failed:
            print(f"SEO failed for {spec.filename}: {seo.summary()}", file=sys.stderr)
            for item in seo.failed:
                print(f"- {item.name}: {item.details}", file=sys.stderr)
            return 1
        similarity = max_similarity_against_existing(html, existing_pages)
        if similarity >= THRESHOLD:
            print(f"Similarity failed for {spec.filename}: {similarity:.3f}", file=sys.stderr)
            return 1
        post = PostMeta(
            filename=spec.filename,
            title=spec.title,
            description=spec.description,
            teaser=spec.opener,
            topic=spec.topic,
            published_iso=spec.day.isoformat(),
        )
        pending.append((spec, html, similarity, post))
        if dry_run:
            temp_path = blog_dir / spec.filename
            existing_pages.append(
                load_blog_pages_from_html(temp_path, html)
            )

    if dry_run:
        for spec, _, similarity, _ in pending:
            print(f"would_publish {spec.filename} similarity={similarity:.3f}")
        return 0

    for spec, html, similarity, post in pending:
        path = blog_dir / spec.filename
        path.write_text(html, encoding="utf-8")
        inject_site_tools_into_file(path)
        update_blog_index(index_path, post)
        update_sitemap(sitemap_path, post)
        print(f"published {spec.filename} similarity={similarity:.3f}")

    inject_site_tools_into_file(index_path)
    build_site_search_index(repo_root)
    return 0


def load_blog_pages_from_html(path: Path, html: str):
    temp_dir = path.parent / ".tmp-recent-blog-validate"
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / path.name
    temp_path.write_text(html, encoding="utf-8")
    try:
        return load_blog_pages(temp_dir)[0]
    finally:
        try:
            temp_path.unlink()
            temp_dir.rmdir()
        except OSError:
            pass


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    repo_root = Path(__file__).resolve().parent.parent
    return publish(repo_root, dry_run=dry_run)


if __name__ == "__main__":
    raise SystemExit(main())


