# Main Site Security Headers

This repository currently deploys the main site on GitHub Pages, which means classic response headers such as `Content-Security-Policy`, `X-Content-Type-Options`, `Referrer-Policy`, and `Permissions-Policy` cannot be set directly from repo files alone.

## What ships today

The HTML entry pages use an early `<meta http-equiv="Content-Security-Policy">` fallback plus `<meta name="referrer">` so the browser still gets baseline protection on GitHub Pages.

Meta CSP limitations:

- It does not support `frame-ancestors`, `sandbox`, or reporting directives.
- It should appear before executable scripts.
- It is weaker than a real response header and should be treated as an interim layer.

## Recommended response headers

When the site moves behind Cloudflare, Netlify, Vercel, Nginx, or another edge that can inject headers, use this baseline:

```http
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https: data:; font-src 'self' https://framerusercontent.com https://fonts.gstatic.com data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; manifest-src 'self'; media-src 'self' https: data:; frame-ancestors 'none'; upgrade-insecure-requests
Referrer-Policy: strict-origin-when-cross-origin
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()
Cross-Origin-Opener-Policy: same-origin
```

## Notes

- `frame-ancestors 'none'` is preferred over `X-Frame-Options`, but keeping both is fine for older clients.
- If any page later embeds trusted third-party video or maps, update `frame-src` explicitly instead of weakening `default-src`.
- If analytics, chat widgets, or remote APIs are added later, update `script-src` and `connect-src` intentionally and re-test.
