#!/usr/bin/env python3
"""Post a tweet through a logged-in Chrome profile via Playwright."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from post_to_x import load_dotenv

DEFAULT_OUTPUT_DIR = Path("output") / "playwright"
DEFAULT_PROFILE_DIRECTORY = "Default"


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def load_env() -> None:
    env_files = [repo_root() / ".env"]
    cwd_env = Path.cwd() / ".env"
    if cwd_env != env_files[0]:
        env_files.append(cwd_env)
    for env_file in env_files:
        load_dotenv(env_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post a tweet via Playwright + logged-in Chrome.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Tweet content.")
    source.add_argument("--file", type=Path, help="Read tweet content from a UTF-8 text file.")
    parser.add_argument("--reply-to", help="Reply target tweet id.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without sending.")
    parser.add_argument("--chrome-path", type=Path, help="Override Chrome executable path.")
    parser.add_argument("--user-data-dir", type=Path, help="Override Chrome user data directory.")
    parser.add_argument(
        "--profile-directory",
        default=os.getenv("X_PLAYWRIGHT_PROFILE_DIRECTORY", DEFAULT_PROFILE_DIRECTORY),
        help=f"Chrome profile directory name (default: {DEFAULT_PROFILE_DIRECTORY}).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root() / DEFAULT_OUTPUT_DIR,
        help=f"Artifact output directory (default: {repo_root() / DEFAULT_OUTPUT_DIR}).",
    )
    return parser.parse_args()


def get_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        content = args.text.strip()
    else:
        content = args.file.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError("Tweet text is empty.")
    return content


def resolve_node_command() -> str:
    for candidate in ["node.exe", "node"]:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError("Node.js is required for Playwright posting, but `node` was not found.")


def resolve_npx_command() -> str:
    for candidate in ["npx.cmd", "npx.exe", "npx"]:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError("Node.js/npm is required for Playwright posting, but `npx` was not found.")


def get_local_app_data_dir() -> Path | None:
    if os.name != "nt":
        return None
    try:
        buffer = ctypes.create_unicode_buffer(260)
        result = ctypes.windll.shell32.SHGetFolderPathW(None, 28, None, 0, buffer)
    except AttributeError:
        return None
    if result != 0 or not buffer.value:
        return None
    return Path(buffer.value)


def find_existing_user_paths(*parts: str) -> list[Path]:
    users_root = Path(r"C:\Users")
    if not users_root.exists():
        return []
    matches: list[Path] = []
    pattern = "/".join(parts)
    for candidate in users_root.glob(f"*/{pattern}"):
        if candidate.exists():
            matches.append(candidate)
    matches.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return matches


def resolve_chrome_path(explicit: Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)

    env_path = os.getenv("X_PLAYWRIGHT_CHROME_PATH")
    if env_path:
        candidates.append(Path(env_path))

    local_app_data = get_local_app_data_dir()
    if local_app_data is None and os.getenv("LOCALAPPDATA"):
        local_app_data = Path(os.getenv("LOCALAPPDATA", ""))
    if local_app_data:
        candidates.append(local_app_data / "Google" / "Chrome" / "Application" / "chrome.exe")
    candidates.extend(find_existing_user_paths("AppData", "Local", "Google", "Chrome", "Application", "chrome.exe"))

    candidates.extend(
        [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Chrome executable not found. Set X_PLAYWRIGHT_CHROME_PATH if needed.")


def resolve_user_data_dir(explicit: Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)

    env_path = os.getenv("X_PLAYWRIGHT_USER_DATA_DIR")
    if env_path:
        candidates.append(Path(env_path))

    dedicated_profile = repo_root() / ".x-playwright-profile"
    candidates.append(dedicated_profile)

    local_app_data = get_local_app_data_dir()
    if local_app_data is None and os.getenv("LOCALAPPDATA"):
        local_app_data = Path(os.getenv("LOCALAPPDATA", ""))
    if local_app_data:
        candidates.append(local_app_data / "Google" / "Chrome" / "User Data")
    candidates.extend(find_existing_user_paths("AppData", "Local", "Google", "Chrome", "User Data"))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Chrome user data directory not found. Set X_PLAYWRIGHT_USER_DATA_DIR if needed.")


def find_playwright_node_modules(cache_dir: Path) -> Path | None:
    npx_root = cache_dir / "_npx"
    if not npx_root.exists():
        return None
    candidates = []
    for package_dir in npx_root.glob("*/node_modules/playwright"):
        if package_dir.is_dir():
            candidates.append(package_dir.parent)
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[0]


def ensure_playwright_node_modules(cache_dir: Path, npx_command: str) -> Path:
    existing = find_playwright_node_modules(cache_dir)
    if existing is not None:
        return existing

    env = os.environ.copy()
    env["NPM_CONFIG_CACHE"] = str(cache_dir)
    subprocess.run(
        [npx_command, "--yes", "playwright", "--version"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(repo_root()),
        env=env,
    )

    installed = find_playwright_node_modules(cache_dir)
    if installed is None:
        raise RuntimeError("Playwright bootstrap succeeded but its node_modules path was not found.")
    return installed


def send_tweet_playwright(
    *,
    text: str,
    reply_to: str | None = None,
    dry_run: bool = False,
    chrome_path: Path | None = None,
    user_data_dir: Path | None = None,
    profile_directory: str | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    root = repo_root()
    driver = script_dir() / "post_to_x_playwright_driver.js"
    if not driver.exists():
        raise FileNotFoundError(f"Missing Playwright driver: {driver}")

    node_command = resolve_node_command()
    npx_command = resolve_npx_command()
    resolved_chrome_path = resolve_chrome_path(chrome_path)
    resolved_user_data_dir = resolve_user_data_dir(user_data_dir)
    resolved_profile_directory = profile_directory or os.getenv(
        "X_PLAYWRIGHT_PROFILE_DIRECTORY",
        DEFAULT_PROFILE_DIRECTORY,
    )

    resolved_output_dir = output_dir or (root / DEFAULT_OUTPUT_DIR)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    temp_dir = root / ".tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = Path(os.getenv("X_PLAYWRIGHT_NPM_CACHE") or (root / ".playwright-npm-cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    node_modules_path = ensure_playwright_node_modules(cache_dir, npx_command)

    browsers_dir = Path(os.getenv("PLAYWRIGHT_BROWSERS_PATH") or (root / ".playwright-browsers"))
    browsers_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "text": text,
        "replyTo": reply_to,
        "dryRun": dry_run,
        "chromePath": str(resolved_chrome_path),
        "userDataDir": str(resolved_user_data_dir),
        "profileDirectory": resolved_profile_directory,
        "outputDir": str(resolved_output_dir),
    }

    fd, config_path_str = tempfile.mkstemp(
        prefix="x-playwright-",
        suffix=".json",
        dir=str(temp_dir),
        text=True,
    )
    config_path = Path(config_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2)

        env = os.environ.copy()
        env["NODE_PATH"] = str(node_modules_path)
        env["NPM_CONFIG_CACHE"] = str(cache_dir)
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_dir)
        env["TEMP"] = str(temp_dir)
        env["TMP"] = str(temp_dir)

        completed = subprocess.run(
            [node_command, str(driver), "--config", str(config_path)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(root),
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(details or "Playwright posting failed.") from exc
    finally:
        config_path.unlink(missing_ok=True)

    payload = json.loads(completed.stdout)
    return payload


def main() -> int:
    load_env()
    args = parse_args()

    try:
        text = get_text(args)
        result = send_tweet_playwright(
            text=text,
            reply_to=args.reply_to,
            dry_run=args.dry_run,
            chrome_path=args.chrome_path,
            user_data_dir=args.user_data_dir,
            profile_directory=args.profile_directory,
            output_dir=args.output_dir,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if result.get("dryRun"):
        print("Dry run only. No tweet sent.")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    tweet_id = str(result.get("tweetId") or "").strip()
    tweet_url = str(result.get("tweetUrl") or "").strip()
    if tweet_id:
        if tweet_url:
            print(f"Tweet posted successfully. id={tweet_id} url={tweet_url}")
        else:
            print(f"Tweet posted successfully. id={tweet_id}")
        return 0

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
