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

## Daily Random Product Stories (>=10/day)

1. Ensure `.env` already has valid X credentials (`X_API_KEY`, `X_API_KEY_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`).
2. Dry run once:
`python scripts/x_story_scheduler.py run --dry-run --log-root "D:\Operation Log" --min-posts 5 --max-posts 10`
3. Install Windows scheduled tasks:
`powershell -ExecutionPolicy Bypass -File scripts/install_x_story_tasks.ps1 -LogRoot "D:\Operation Log" -MinPosts 5 -MaxPosts 10`

Installed task:
- `WeiLuoGe-XStory-Plan`: runs every 1 hour, auto-creates daily plan if missing, and posts due items.

Runtime files:
- Plans: `D:\Operation Log\TwitterStoryBot\plans\YYYY-MM-DD.json`
- Logs: `D:\Operation Log\TwitterStoryBot\logs\YYYY-MM-DD.log`

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
