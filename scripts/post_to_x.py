#!/usr/bin/env python3
"""Post a tweet through X API v2 using OAuth 1.0a user context."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://api.x.com"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


def oauth_encode(value: str) -> str:
    return quote(str(value), safe="-._~")


def build_oauth_header(
    method: str,
    url: str,
    api_key: str,
    api_key_secret: str,
    access_token: str,
    access_token_secret: str,
) -> str:
    oauth_params: dict[str, str] = {
        "oauth_consumer_key": api_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }
    normalized_params = "&".join(
        f"{oauth_encode(k)}={oauth_encode(v)}" for k, v in sorted(oauth_params.items())
    )
    base_string = "&".join(
        [method.upper(), oauth_encode(url), oauth_encode(normalized_params)]
    )
    signing_key = f"{oauth_encode(api_key_secret)}&{oauth_encode(access_token_secret)}"
    signature = base64.b64encode(
        hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1).digest()
    ).decode("ascii")
    oauth_params["oauth_signature"] = signature

    auth_values = ", ".join(
        f'{oauth_encode(k)}="{oauth_encode(v)}"' for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {auth_values}"


def load_credentials() -> tuple[str, str, str, str]:
    api_key = os.getenv("X_API_KEY") or os.getenv("TWITTER_API_KEY")
    api_key_secret = os.getenv("X_API_KEY_SECRET") or os.getenv("TWITTER_API_KEY_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN") or os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv(
        "TWITTER_ACCESS_TOKEN_SECRET"
    )

    missing: list[str] = []
    if not api_key:
        missing.append("X_API_KEY")
    if not api_key_secret:
        missing.append("X_API_KEY_SECRET")
    if not access_token:
        missing.append("X_ACCESS_TOKEN")
    if not access_token_secret:
        missing.append("X_ACCESS_TOKEN_SECRET")
    if missing:
        raise ValueError(
            "Missing environment variables: "
            + ", ".join(missing)
            + ". Fill .env from .env.example first."
        )
    return api_key, api_key_secret, access_token, access_token_secret


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post a tweet via X API v2.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Tweet content.")
    source.add_argument("--file", type=Path, help="Read tweet content from a UTF-8 text file.")
    parser.add_argument("--reply-to", help="Tweet ID to reply to.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("X_API_BASE_URL", DEFAULT_BASE_URL),
        help=f"API base URL (default: {DEFAULT_BASE_URL}).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Build request without sending.")
    return parser.parse_args()


def get_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        content = args.text.strip()
    else:
        content = args.file.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError("Tweet text is empty.")
    return content


def send_tweet(
    text: str,
    reply_to: str | None,
    base_url: str,
    dry_run: bool,
    api_key: str,
    api_key_secret: str,
    access_token: str,
    access_token_secret: str,
) -> dict[str, Any] | None:
    endpoint = f"{base_url.rstrip('/')}/2/tweets"
    payload: dict[str, Any] = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    if dry_run:
        print("Dry run only. No tweet sent.")
        print(f"POST {endpoint}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return None

    auth_header = build_oauth_header(
        method="POST",
        url=endpoint,
        api_key=api_key,
        api_key_secret=api_key_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    req = Request(
        endpoint,
        data=payload_bytes,
        method="POST",
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "User-Agent": "weiluoge-x-poster/1.0",
        },
    )
    with urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    env_files = [repo_root / ".env"]
    cwd_env = Path.cwd() / ".env"
    if cwd_env != env_files[0]:
        env_files.append(cwd_env)
    for env_file in env_files:
        load_dotenv(env_file)

    args = parse_args()

    try:
        text = get_text(args)
        if args.dry_run:
            api_key = api_key_secret = access_token = access_token_secret = ""
        else:
            api_key, api_key_secret, access_token, access_token_secret = load_credentials()
        result = send_tweet(
            text=text,
            reply_to=args.reply_to,
            base_url=args.base_url,
            dry_run=args.dry_run,
            api_key=api_key,
            api_key_secret=api_key_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
    except FileNotFoundError as exc:
        print(f"File not found: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {details}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        return 1

    if result is None:
        return 0

    tweet_id = result.get("data", {}).get("id")
    if tweet_id:
        print(f"Tweet posted successfully. id={tweet_id}")
    else:
        print("Tweet request succeeded, response:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
