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
