---
name: "browser-research"
description: "Use when the user asks to open a real browser to search, browse, compare, or extract information from websites/pages, especially requests like `打开浏览器`, `去网页上查`, `到网站搜一下`, or when dynamic page interaction is required. Prefer `playwright` for one-off browser automation and `playwright-interactive` for longer iterative sessions."
---

# Browser Research

Use this skill when the request is about opening a real browser and getting information from live pages, rather than only answering from memory.

## When to trigger

Trigger this skill when the user asks to:

- open a browser and search for information
- visit a specific website and extract details
- compare information across multiple pages
- inspect content that depends on JavaScript rendering or user interaction
- navigate a UI flow before extracting facts, links, screenshots, or notes

Typical phrases include:

- “打开浏览器查一下”
- “去官网看看”
- “到网页上搜一下”
- “帮我从这个网站提取信息”

## Tool choice

Choose the lightest tool that still satisfies the request:

1. If the user explicitly wants a real browser, or the page requires interaction, use `playwright`.
2. If the task becomes a long iterative debugging or inspection session, switch to `playwright-interactive`.
3. If the task only needs up-to-date facts and does not actually need a browser UI, a direct web lookup is acceptable, but say so instead of claiming browser automation.

When `playwright` or `playwright-interactive` are used, open their `SKILL.md` and follow their prerequisite checks and workflows.

## Bundled wrapper

This skill now includes a Windows wrapper script:

- `skills/browser-research/scripts/browser_research.cmd`
- `skills/browser-research/scripts/browser_research.ps1`

Use the wrapper when you want a quick browser-research entrypoint without retyping the underlying `npx --package @playwright/cli playwright-cli ...` command.

### Prerequisite check

Before using the wrapper, confirm `npx` is available:

```powershell
node --version
npm.cmd --version
npx.cmd --version
```

If `npx` is missing, install Node.js/npm first.

### Quick start

```powershell
# Search the web in a real browser, then snapshot automatically
.\skills\browser-research\scripts\browser_research.cmd search "Bluetooth Mesh provisioning"

# Open a page, wait a bit, then snapshot automatically
.\skills\browser-research\scripts\browser_research.cmd open https://playwright.dev --session demo --wait-ms 1200

# Reuse the same browser session for follow-up interactions
.\skills\browser-research\scripts\browser_research.cmd --session demo snapshot
.\skills\browser-research\scripts\browser_research.cmd --session demo click e12
```

### Wrapper behavior

- `search` builds a search URL using `bing`, `google`, `duckduckgo`, or `baidu`
- `open` normalizes URLs and opens them in Playwright
- `search` and `open` use `--headed` by default so the browser is visible
- `search` and `open` snapshot automatically unless `--no-snapshot` is passed
- if no session is provided, the wrapper creates one and prints it for reuse
- on Windows, the wrapper prefers `npx.cmd` to avoid PowerShell execution-policy issues
- the wrapper also uses skill-local npm and Playwright cache folders to avoid user-profile permission problems
- any other arguments are passed through directly to `playwright-cli`

## Standard workflow

1. Identify the target site, query, or likely source; if the user is vague, make a reasonable default choice.
2. Open the page in a real browser.
3. Snapshot before using element refs.
4. Search or navigate to the relevant result or section.
5. Re-snapshot after navigation or significant UI changes.
6. Extract only the facts the user asked for: names, prices, dates, specs, summaries, links, or screenshots.
7. Cross-check important or time-sensitive claims against the page itself, and against a second source when the stakes are high.
8. Return a concise answer in the user's language with source links.

## Extraction rules

- Prefer official or primary sources when available.
- Capture page title, URL, and any visible date when they matter.
- Separate observed facts from your own inference.
- Quote sparingly; short snippets only when needed.
- If content is blocked by login, paywall, captcha, or geo restrictions, say that plainly and continue with the best accessible source.

## Playwright reminders

- Always snapshot before referring to ids like `e12`.
- Re-snapshot when refs go stale.
- Use `--headed` when visual confirmation matters or the user explicitly asked to “打开浏览器”.
- Prefer targeted interactions over generic code execution.
- Save browser artifacts under `output/playwright/` if you need screenshots or traces in this repo.

## Output contract

Your answer should usually include:

- a direct answer first
- a short list of key findings
- source links to the pages you used
- a brief note about uncertainty, blocked content, or assumptions if relevant

## Fallbacks

- If browser automation tooling is unavailable, say so briefly and fall back to direct web lookup or local inspection.
- If the user needs repeated interactive inspection, prefer `playwright-interactive` instead of restarting one-off browser sessions.
