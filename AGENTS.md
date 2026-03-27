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
- Preferred ongoing content ranges include Bluetooth protocol/application analysis, iPhone storage cleanup and system-impact analysis, Apple new-product feature/performance commentary, and AI technology outlook coverage.
- Every new or updated content page should target a clear primary search intent and include naturally written secondary keywords that support the same topic cluster.
- Core keyword phrases for blog content must include at least one app-centered term directly tied to the current app portfolio: `bluetooth`, `find AI`, `cleanup pro`, or `Translate`.
- Titles, H1s, meta descriptions, and visible section headings should use high-intent phrasing that matches likely search queries.
- Content should be structured for both search engines and AI retrieval: concise answers near the top, scannable sections, FAQ-style Q&A where appropriate, and explicit entity/topic wording.
- Prefer evergreen, factual wording and direct problem-solution framing over vague branding language.
- Add or preserve helpful internal links, canonical metadata, structured data, and sitemap/index updates when relevant.
- If a change would reduce SEO/GEO value, call it out before proceeding unless the user explicitly prioritizes another goal.
- Daily blog publishing target is 6 posts: 2 posts around `Translate`, 2 posts around `bluetooth`, 1 post around `find AI`, and 1 post around `cleanup pro`.
- For blog maintenance, treat posts as merge candidates when topic-bearing content similarity is above 30% after stripping shared boilerplate sections.
- Apply that 30% rule within the same intent cluster, using title/topic overlap to avoid merging unrelated long-tail pages that only share templates.
- For daily blog publishing, reject any new cleanup post whose topic-bearing similarity against the existing blog corpus reaches 40% or higher.
- For daily protocol and live-update publishing, reject any new post whose topic-bearing similarity against the existing blog corpus reaches 50% or higher.
- Protocol-topic daily publishing must stay within Bluetooth protocol subject matter, not generic consumer tech or generic AI news.
- If the fixed local topic pool cannot supply the required number of daily posts under that rule, fetch the latest live source items and rewrite them into new SEO/GEO blog posts instead of reusing near-duplicate templates.
