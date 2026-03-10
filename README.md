# weiluoge

## X API Auto Posting

1. Create an app in X Developer Portal and set permission to `Read and write`.
2. Collect these credentials:
`X_API_KEY`
`X_API_KEY_SECRET`
`X_ACCESS_TOKEN`
`X_ACCESS_TOKEN_SECRET`
3. Copy `.env.example` to `.env` and fill in real values.
4. Run a no-send check:
`python scripts/post_to_x.py --text "Hello from API" --dry-run`
5. Post a tweet:
`python scripts/post_to_x.py --text "Free App Picks (2026)..." `
6. Post from a file:
`python scripts/post_to_x.py --file tweet.txt`
7. Reply to a tweet:
`python scripts/post_to_x.py --text "Thanks!" --reply-to 1890000000000000000`

### Common Errors

- `HTTP 401`: Key/token mismatch, or access token was not created under this app.
- `HTTP 403`: App permission is not `Read and write`, or app/project linkage is wrong.
- `HTTP 429`: Rate limit reached, retry later.

## X Playwright Posting

- Dry run the Playwright sender:
`python scripts/post_to_x_playwright.py --text "Hello from Playwright" --dry-run`
- Send through logged-in Chrome:
`python scripts/post_to_x_playwright.py --text "Hello from Playwright"`
- Optional environment overrides:
`X_PLAYWRIGHT_CHROME_PATH`, `X_PLAYWRIGHT_USER_DATA_DIR`, `X_PLAYWRIGHT_PROFILE_DIRECTORY`

## Daily Random Product Stories (>=10/day)

1. Ensure Chrome is already logged into X. API credentials stay optional if you use `playwright`-only mode.
2. Dry run once:
`python scripts/x_story_scheduler.py run --dry-run --log-root "D:\Operation Log" --min-posts 5 --max-posts 10 --post-mode playwright-first`
3. Install Windows scheduled tasks:
`powershell -ExecutionPolicy Bypass -File scripts/install_x_story_tasks.ps1 -LogRoot "D:\Operation Log" -MinPosts 5 -MaxPosts 10 -PostMode playwright-first`

Installed task:
- `WeiLuoGe-XStory-Plan`: runs every 1 hour, auto-creates daily plan if missing, and posts due items.
- Default post order is now `playwright-first` with API fallback.

Runtime files:
- Plans: `D:\Operation Log\TwitterStoryBot\plans\YYYY-MM-DD.json`
- Logs: `D:\Operation Log\TwitterStoryBot\logs\YYYY-MM-DD.log`

### Example: 4 posts between 20:00 and 22:00

This uses the `velocai-mix` content mode, which rotates across:
- celebrity humor
- VelocAI app use cases
- VelocAI update-style posts
- popular Apple product commentary

Each scheduled post now appends exactly one most-relevant App Store link from:
- `Cleanup Pro`
- `Find AI`
- `Bluetooth Explorer`

Optional: add your own update-note ideas with:
`--update-topics-file "D:\GitHub\weiluoge\scripts\x_story_update_topics.example.txt"`

Dry run a plan:
`python scripts/x_story_scheduler.py plan --force --date 2026-03-08 --log-root "D:\Operation Log" --min-posts 4 --max-posts 4 --day-start 20:00 --day-end 22:00 --content-mode velocai-mix --post-mode playwright-first --update-topics-file "scripts/x_story_update_topics.example.txt"`

Install the scheduled task with a 5-minute worker interval:
`powershell -ExecutionPolicy Bypass -File scripts/install_x_story_tasks.ps1 -LogRoot "D:\Operation Log" -MinPosts 4 -MaxPosts 4 -DayStart 20:00 -DayEnd 22:00 -ContentMode velocai-mix -PostMode playwright-first -UpdateTopicsFile "D:\GitHub\weiluoge\scripts\x_story_update_topics.example.txt" -WorkerEveryMinutes 5`

## Daily Blog Auto Publishing (20:00)

This task publishes one English blog post per day about Bluetooth + phone cleanup,
updates `blog/index.html`, and updates `sitemap.xml` for SEO/GEO visibility.

1. Dry run once:
`python scripts/blog_daily_scheduler.py run --dry-run`
2. Publish immediately (manual run):
`python scripts/blog_daily_scheduler.py run`
3. Install the daily Windows scheduled task (default: 20:00):
`powershell -ExecutionPolicy Bypass -File scripts/install_blog_daily_task.ps1`

Optional:
- Change schedule time: `-PublishAt "20:00"`
- Force overwrite for a date: `python scripts/blog_daily_scheduler.py run --date 2026-03-05 --force`

## Bluetooth Protocol Blog (09:30~10:00, 2/day)

This publishes 2 English posts each morning focused on Bluetooth protocol interpretation and applications.
It installs 2 scheduled tasks (default: 09:30 and 09:45) and uses `--angle-offset` to avoid duplicates.

Install:
`powershell -ExecutionPolicy Bypass -File scripts/install_protocol_blog_morning_tasks.ps1 -WindowStart 09:30 -WindowEnd 10:00 -PostsPerDay 2`

## Google Index Request Task (10:30)

Google does not offer an official API to click `Request indexing` for normal web pages.
This repo uses a supported sitemap diff plus a Playwright browser flow for the final Search Console click.

1. Initialize a dedicated logged-in Search Console browser profile once:
`py -3 scripts/google_index_daily_scheduler.py auth --site-url "https://velocai.net/"`
2. First run bootstrap only, so existing sitemap URLs are recorded and only future new URLs will be submitted:
`py -3 scripts/google_index_daily_scheduler.py run --site-url "https://velocai.net/" --sitemap-url "https://velocai.net/sitemap.xml"`
3. Install the daily Windows task at `10:30`:
`powershell -ExecutionPolicy Bypass -File scripts/install_google_index_task.ps1 -RunAt "10:30"`

Default runtime behavior:
- The scheduled `run` command now tries to auto-detect a local Chrome/Edge user data directory first, then falls back to the dedicated Playwright profile if no local browser session is found.
- When an Edge profile is selected, the automation now prefers the matching Edge executable instead of accidentally opening Chrome against that profile.
- If the source Chrome/Edge profile is currently open, Windows may lock the cookies database. In that case, close the source browser once and rerun, or keep using the dedicated Playwright profile.
- You can still force a specific logged-in Chrome/Edge profile with `-SourceUserDataDir` and `-ProfileDirectory` when installing the task.

Installed task:
- `WeiLuoGe-Google-Index-Daily-10-30`: checks `https://velocai.net/sitemap.xml`, finds new URLs, opens Search Console URL inspection, and requests indexing.

Runtime files:
- State: `D:\Operation Log\GoogleIndexing\state.json`
- Logs: `D:\Operation Log\GoogleIndexing\logs\YYYY-MM-DD.log`
