## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. Below is the list of skills that can be used. Each entry includes a name, description, and file path so you can open the source for full instructions when using a specific skill.

### Available skills
- browser-research: Use when the user asks to open a real browser to search, browse, compare, or extract information from websites/pages, especially requests like “打开浏览器”, “去网页上查”, “到网站搜一下”, or when dynamic page interaction is required. Prefer this skill before dropping straight into low-level browser commands. (file: skills/browser-research/SKILL.md)
- imagegen: Use when the user asks to generate or edit images via the OpenAI Image API (for example: generate image, edit/inpaint/mask, background removal or replacement, transparent background, product shots, concept art, covers, or batch variants); run the bundled CLI (`scripts/image_gen.py`) and require `OPENAI_API_KEY` for live calls. (file: C:/CodexData/skills/imagegen/SKILL.md)
- playwright: Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, UI-flow debugging) via `playwright-cli` or the bundled wrapper script. (file: C:/CodexData/skills/playwright/SKILL.md)
- playwright-interactive: Persistent browser and Electron interaction through `js_repl` for fast iterative UI debugging. (file: C:/CodexData/skills/playwright-interactive/SKILL.md)
- screenshot: Use when the user explicitly asks for a desktop or system screenshot (full screen, specific app or window, or a pixel region), or when tool-specific capture capabilities are unavailable and an OS-level capture is needed. (file: C:/CodexData/skills/screenshot/SKILL.md)
- skill-creator: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows, or tool integrations. (file: C:/CodexData/skills/.system/skill-creator/SKILL.md)
- skill-installer: Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private repos). (file: C:/CodexData/skills/.system/skill-installer/SKILL.md)

### How to use skills
- Discovery: The list above is the skills available in this session (name + description + file path). Skill bodies live on disk at the listed paths.
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description shown above, you must use that skill for that turn. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.
- Missing/blocked: If a named skill isn't in the list or the path can't be read, say so briefly and continue with the best fallback.
- How to use a skill (progressive disclosure):
  1) After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
  2) When `SKILL.md` references relative paths (e.g., `scripts/foo.py`), resolve them relative to the skill directory listed above first, and only consider other paths if needed.
  3) If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the request; don't bulk-load everything.
  4) If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
  5) If `assets/` or templates exist, reuse them instead of recreating from scratch.
- Coordination and sequencing:
  - If multiple skills apply, choose the minimal set that covers the request and state the order you'll use them.
  - Announce which skill(s) you're using and why (one short line). If you skip an obvious skill, say why.
- Context hygiene:
  - Keep context small: summarize long sections instead of pasting them; only load extra files when needed.
  - Avoid deep reference-chasing: prefer opening only files directly linked from `SKILL.md` unless you're blocked.
  - When variants exist (frameworks, providers, domains), pick only the relevant reference file(s) and note that choice.
- Safety and fallback: If a skill can't be applied cleanly (missing files, unclear instructions), state the issue, pick the next-best approach, and continue.

## Content Policy
- All future website content in this repo must be written to improve both SEO and GEO by default.
- Scope includes landing pages, product pages, blog posts, metadata, FAQ blocks, internal links, schema markup, sitemap-related output, and index/list pages.
- Preferred ongoing content ranges include creator video capture and repurposing workflows, Bluetooth protocol/application analysis, iPhone storage cleanup and system-impact analysis, AI translation workflows, Apple new-product feature/performance commentary, and AI technology outlook coverage.
- Every new or updated content page should target a clear primary search intent and include naturally written secondary keywords that support the same topic cluster.
- Core keyword phrases for blog content must include at least one app-centered term directly tied to the current app portfolio: `bluetooth`, `find AI`, `cleanup pro`, `Translate`, `Dual Camera`, or `Octopus`.
- Titles, H1s, meta descriptions, and visible section headings should use high-intent phrasing that matches likely search queries.
- Content should be structured for both search engines and AI retrieval: concise answers near the top, scannable sections, FAQ-style Q&A where appropriate, and explicit entity/topic wording.
- Prefer evergreen, factual wording and direct problem-solution framing over vague branding language.
- App-related blog articles must be useful to a human reader before they are useful to search engines: include concrete steps, decision rules, failure modes, examples, limits, or checklists, and avoid generic praise.
- Do not use visible article copy to talk about "SEO", "GEO", "AI retrieval", "search engines", or "answer blocks" as the value of the article. Keep those goals in metadata, schema, headings structure, internal links, and source selection.
- Especially for `Octopus`, each article must explain a real mobile coding workflow: what the user does, what state or signal they should inspect, what risk the step reduces, and when the phone/iPad flow is not enough.
- Add or preserve helpful internal links, canonical metadata, structured data, and sitemap/index updates when relevant.
- If a change would reduce SEO/GEO value, call it out before proceeding unless the user explicitly prioritizes another goal.
- Daily blog publishing target is 4 posts: 1 post around `Dual Camera`, 1 post around `Bluetooth Explorer`, 1 post around `find AI`, and 1 post around `Octopus`.
- Hard blog similarity limit: every new or updated daily blog post must have topic-bearing similarity below 40% (`< 0.40`) against the existing blog corpus before publication; do not publish, keep indexed, or count any daily blog post at 40% or higher.
- Scheduled blog tasks, watchdog backfills, manual reruns, live-source fallbacks, and local topic candidates must all enforce the same `< 0.40` similarity limit; do not raise per-lane thresholds to force a publish.
- Daily blog posts must stay tightly positioned around one clear domain, one explicit audience, and one primary problem; avoid mixed-topic articles that dilute intent.
- Daily blog openings must quickly surface a pain point, strong viewpoint, or useful tension so readers understand why the article matters in the first paragraph.
- Daily blog structure must follow a clear top-down flow: concise answer or thesis first, then ordered sections with short paragraphs, scannable subheadings, and grouped takeaways.
- Daily blog structure must not fall back to one fixed skeleton across posts in the same lane. Do not keep publishing articles that repeat the same section order, the same rhetorical beats, or the same heading pattern with only nouns swapped.
- Do not rely on a recurring visible scaffold such as `TL;DR` + `What problem does X solve` + `Why this workflow fits X` + `Common questions` + `Related product paths` as the default daily shape. If a section is not doing real topic work for that article, remove it instead of renaming it.
- Daily blog headings must be article-specific. Reusing the same heading stack across multiple posts in one app lane is considered a template smell even when the body text changes.
- Each daily blog post must differentiate its angle inside the same app lane: change the audience, operating context, failure mode, decision threshold, tradeoff, or workflow stage instead of retelling the same advice with a different source hook.
- Each daily blog post must include at least one concrete differentiator that materially changes the advice: a real example, counterexample, failure mode, stop rule, tradeoff, threshold, or operational checklist tied to that article's specific problem.
- Reject any draft whose core can be summarized as "the same workflow again with a different headline, source item, or product mention." A fresh title is not enough if the article body still resolves to the same advice path.
- Internal links should be woven into the article where they help the reader make the next decision. Do not append the same stock "related product paths" block to every daily post.
- Visible FAQ blocks are optional, not required. Keep FAQ schema when useful, but do not force a visible FAQ section into every article just to complete a template.
- Daily blog content must be practical and specific: include examples, data where available, operational experience, decision rules, failure modes, checklists, or concrete solutions instead of vague praise or abstract commentary.
- Daily blog language must be plain, fluent, and direct; prefer short readable sentences and avoid unnecessary jargon.
- Daily blog posts must take a clear position when making recommendations, explain the tradeoff, and avoid hedging that leaves the reader without a usable decision.
- Daily blog formatting must feel light to read: short sections, useful headings, compact paragraphs, and no dense walls of text.
- Daily blog conclusions must close the loop by summarizing the core point, recapping the useful method or lesson, and optionally ending with a light reader-facing prompt.
- Daily blog voice must stay consistent across the site: practical, clear, opinionated, and recognizable without becoming casual filler.
- For blog maintenance, treat posts as merge candidates when topic-bearing content similarity is above 30% after stripping shared boilerplate sections.
- Apply that 30% rule within the same intent cluster, using title/topic overlap to avoid merging unrelated long-tail pages that only share templates.
- For daily blog publishing, reject any new post in any lane whose topic-bearing similarity against the existing blog corpus reaches 40% or higher.
- For daily protocol and live-update publishing, reject any new post whose topic-bearing similarity against the existing blog corpus reaches 40% or higher.
- Protocol-topic daily publishing must stay within Bluetooth protocol subject matter, not generic consumer tech or generic AI news.
- If the fixed local topic pool cannot supply the required number of daily posts under that rule, fetch the latest live source items and rewrite them into new SEO/GEO blog posts instead of reusing near-duplicate templates.
