# Security Best Practices Report

Date: 2026-03-14
Scope: `https://velocai.net/`, `https://velocai.net/privacy-policy.html`, `https://velocai.net/superlist_home.html`, and the corresponding repo files under `D:\GitHub\weiluoge`

## Executive Summary

The main VelocAI pages are simple static documents, but the deployed site currently lacks browser-enforced defense-in-depth controls such as a Content Security Policy and clickjacking protections. That gap becomes more important because the repo serves a large third-party `superlist_home.html` snapshot from the same origin, and that page pulls in many remote scripts and analytics tags that execute with `velocai.net` origin privileges.

## Medium Severity

### SEC-001: No CSP or anti-framing protection is visible on the deployed HTML pages

Impact: A future HTML/script injection bug, compromised content include, or malicious third-party script would execute without a browser-enforced CSP safety net, and the pages can currently be embedded by other sites.

- Evidence:
  - Runtime `HEAD` checks for `https://velocai.net/`, `https://velocai.net/privacy-policy.html`, and `https://velocai.net/superlist_home.html` returned `200 OK` from GitHub Pages, but did not include `Content-Security-Policy`, `X-Frame-Options`, `Referrer-Policy`, or `X-Content-Type-Options`.
  - [index.html](/D:/GitHub/weiluoge/index.html#L3) starts the `<head>` without any CSP meta tag and includes script execution points at [index.html](/D:/GitHub/weiluoge/index.html#L23), [index.html](/D:/GitHub/weiluoge/index.html#L324), and [index.html](/D:/GitHub/weiluoge/index.html#L359).
  - [privacy-policy.html](/D:/GitHub/weiluoge/privacy-policy.html#L3) likewise has no CSP meta tag before its JSON-LD script at [privacy-policy.html](/D:/GitHub/weiluoge/privacy-policy.html#L22).
  - [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L5) has no CSP meta tag and executes inline and remote scripts starting at [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L9), [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L35), and [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L402).
- Fix:
  - Add a response-header CSP at the hosting layer if possible.
  - If you must stay on static hosting only, add an early `<meta http-equiv="Content-Security-Policy" ...>` as a partial fallback and move inline scripts into external files so `script-src` can avoid `unsafe-inline`.
  - Add clickjacking protection at the edge via `Content-Security-Policy: frame-ancestors 'none'` or `X-Frame-Options: DENY`.
- Mitigation:
  - Until header control is available, keep scripts same-origin, avoid new inline handlers, and minimize third-party JS.
- False positive notes:
  - This is based on live runtime headers observed on 2026-03-14. If you terminate traffic behind another edge in production, re-check there as well.

### SEC-002: `superlist_home.html` serves a third-party site snapshot from your origin and imports many remote scripts without isolation

Impact: Any compromise of the loaded analytics/CDN providers would run arbitrary JavaScript under the `velocai.net` origin for visitors who hit this page, increasing supply-chain and phishing surface on your main domain.

- Evidence:
  - The file is tracked and publicly served as `https://velocai.net/superlist_home.html`.
  - It identifies a different brand and canonical target at [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L15) and [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L17).
  - It loads remote analytics and script bundles from multiple third parties at [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L35), [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L385), [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L402), and [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L416).
  - The page also contains large inline script blocks at [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L36), [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L412), [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L414), and [superlist_home.html](/D:/GitHub/weiluoge/superlist_home.html#L415), which makes a strict CSP harder to deploy.
- Fix:
  - Remove the file from the public site if it is not intentionally part of the VelocAI product.
  - If it must exist, move it to a separate hostname/subdomain so it does not share origin trust with the main site.
  - Reduce or self-host third-party scripts where possible, and pair them with a strict CSP.
- Mitigation:
  - At minimum, prevent indexing and linking to the page until its ownership and trust model are clear.
- False positive notes:
  - This finding assumes `superlist_home.html` is not an intentionally maintained first-party experience. If it is intentional, it still needs stricter origin separation.

## Low Severity

### SEC-003: Several external links open a new tab without explicit `rel="noopener noreferrer"`

Impact: Modern browsers often imply `noopener` for `_blank`, but relying on browser defaults is weaker than setting the relationship explicitly and consistently.

- Evidence:
  - [privacy-policy.html](/D:/GitHub/weiluoge/privacy-policy.html#L134)
  - [privacy-policy.html](/D:/GitHub/weiluoge/privacy-policy.html#L135)
  - [privacy-policy.html](/D:/GitHub/weiluoge/privacy-policy.html#L148)
- Fix:
  - Add `rel="noopener noreferrer"` to all external `target="_blank"` links.
- Mitigation:
  - If you later centralize external-link rendering, enforce the rel attributes there.
- False positive notes:
  - This is a hardening issue rather than an immediately exploitable bug on all browsers.

## Notes

- I did not find evidence of DOM XSS sinks fed by user-controlled input in `assets/js/site-tools.js`; its `innerHTML` usage is currently limited to constant markup strings.
- The root `.env` file is present locally but is not tracked by git in this repo, so I did not treat it as a committed-secret finding.

