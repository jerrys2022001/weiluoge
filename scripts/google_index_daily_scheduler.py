#!/usr/bin/env python3
"""Track new sitemap URLs and request indexing in Google Search Console."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from post_to_x import load_dotenv

DEFAULT_SITEMAP_URL = "https://velocai.net/sitemap.xml"
DEFAULT_SITE_URL = "https://velocai.net/"
DEFAULT_LOG_ROOT = Path(r"D:\Operation Log")
DEFAULT_BOT_DIR = "GoogleIndexing"
DEFAULT_PROFILE_DIRECTORY = "Default"
DEFAULT_MAX_URLS_PER_RUN = 20
DEFAULT_AUTH_TIMEOUT_SECONDS = 600
DEFAULT_RUN_TIMEOUT_SECONDS = 180
PROFILE_INCLUDE_NAMES = {
    "Bookmarks",
    "Cookies",
    "Extension Cookies",
    "Favicons",
    "History",
    "Login Data",
    "Network",
    "Preferences",
    "Secure Preferences",
    "Sessions",
    "Shortcuts",
    "Top Sites",
    "Visited Links",
    "Web Data",
}
USER_DATA_ROOT_INCLUDE_NAMES = {
    "Local State",
    "First Run",
    "Variations",
}


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    logs: Path
    output: Path
    temp: Path
    state_file: Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def default_profile_root() -> Path:
    return repo_root() / ".gsc-playwright-profile"


def default_profile_snapshot_root() -> Path:
    return repo_root() / ".gsc-playwright-profile-snapshot"


def load_env() -> None:
    env_files = [repo_root() / ".env"]
    cwd_env = Path.cwd() / ".env"
    if cwd_env != env_files[0]:
        env_files.append(cwd_env)
    for env_file in env_files:
        load_dotenv(env_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect new sitemap URLs and request indexing via Google Search Console."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(target: argparse.ArgumentParser) -> None:
        target.add_argument("--sitemap-url", default=DEFAULT_SITEMAP_URL, help="Remote sitemap URL.")
        target.add_argument("--site-url", default=DEFAULT_SITE_URL, help="Search Console property URL.")
        target.add_argument(
            "--log-root",
            type=Path,
            default=DEFAULT_LOG_ROOT,
            help=f"Log root path (default: {DEFAULT_LOG_ROOT}).",
        )
        target.add_argument(
            "--chrome-path",
            type=Path,
            help="Override Chromium executable path. Accepts either Chrome or Edge.",
        )
        target.add_argument(
            "--user-data-dir",
            type=Path,
            default=default_profile_root(),
            help="Chromium user data dir used directly when snapshot mode is off.",
        )
        target.add_argument(
            "--source-user-data-dir",
            type=Path,
            help="Logged-in Chromium user data dir to snapshot before automation.",
        )
        target.add_argument(
            "--profile-directory",
            default=os.getenv("GSC_PLAYWRIGHT_PROFILE_DIRECTORY", DEFAULT_PROFILE_DIRECTORY),
            help=f"Browser profile directory name (default: {DEFAULT_PROFILE_DIRECTORY}).",
        )
        target.add_argument(
            "--snapshot-user-data-dir",
            type=Path,
            default=default_profile_snapshot_root(),
            help="Working directory for copied browser profile snapshots.",
        )
        target.add_argument(
            "--output-dir",
            type=Path,
            default=repo_root() / "output" / "gsc-indexing",
            help="Artifacts directory for screenshots and JSON outputs.",
        )

    auth_parser = sub.add_parser("auth", help="Open Search Console and let the user log in once.")
    add_common(auth_parser)
    auth_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_AUTH_TIMEOUT_SECONDS,
        help="How long to wait for manual Google login.",
    )

    run_parser = sub.add_parser("run", help="Fetch sitemap, diff new URLs, and request indexing.")
    add_common(run_parser)
    run_parser.add_argument(
        "--max-urls-per-run",
        type=int,
        default=DEFAULT_MAX_URLS_PER_RUN,
        help="Cap request count per run to avoid large bursts.",
    )
    run_parser.add_argument(
        "--submit-existing-on-first-run",
        action="store_true",
        help="On a missing state file, submit the current sitemap URLs instead of bootstrapping only.",
    )
    run_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_RUN_TIMEOUT_SECONDS,
        help="Per-URL wait budget inside Search Console UI automation.",
    )
    run_parser.add_argument("--dry-run", action="store_true", help="Show what would be submitted without clicking.")
    return parser.parse_args()


def ensure_paths(log_root: Path, output_dir: Path) -> RuntimePaths:
    root = log_root / DEFAULT_BOT_DIR
    logs = root / "logs"
    output = output_dir
    temp = repo_root() / ".tmp"
    for path in [root, logs, output, temp]:
        path.mkdir(parents=True, exist_ok=True)
    return RuntimePaths(
        root=root,
        logs=logs,
        output=output,
        temp=temp,
        state_file=root / "state.json",
    )


def now_local() -> datetime:
    return datetime.now().astimezone()


def log_file_path(paths: RuntimePaths) -> Path:
    return paths.logs / f"{now_local().date().isoformat()}.log"


def write_log(paths: RuntimePaths, message: str) -> None:
    with log_file_path(paths).open("a", encoding="utf-8") as handle:
        handle.write(f"{now_local().isoformat()} {message}\n")


def save_json(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "known_urls": [],
            "pending_urls": [],
            "submitted_urls": {},
            "last_sitemap_url": None,
            "last_run_at": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_url_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "weiluoge-google-index-bot/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_loc_values(xml_text: str) -> tuple[str, list[str]]:
    root = ET.fromstring(xml_text)
    tag = root.tag.split("}", 1)[-1]
    if tag == "sitemapindex":
        locs = [item.text.strip() for item in root.findall(".//{*}loc") if item.text and item.text.strip()]
        return "sitemapindex", locs
    if tag == "urlset":
        locs = [item.text.strip() for item in root.findall(".//{*}loc") if item.text and item.text.strip()]
        return "urlset", locs
    raise ValueError(f"Unsupported sitemap root tag: {root.tag}")


def fetch_sitemap_urls(sitemap_url: str, visited: set[str] | None = None) -> list[str]:
    visited = visited or set()
    if sitemap_url in visited:
        return []
    visited.add(sitemap_url)

    xml_text = fetch_url_text(sitemap_url)
    kind, locs = extract_loc_values(xml_text)
    if kind == "urlset":
        return locs

    output: list[str] = []
    for child_sitemap in locs:
        output.extend(fetch_sitemap_urls(child_sitemap, visited))
    return output


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def resolve_node_command() -> str:
    for candidate in ["node.exe", "node"]:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError("Node.js is required for Search Console automation, but `node` was not found.")


def resolve_npx_command() -> str:
    for candidate in ["npx.cmd", "npx.exe", "npx"]:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError("Node.js/npm is required for Search Console automation, but `npx` was not found.")


def infer_browser_family_from_path(path: Path | None) -> str | None:
    if path is None:
        return None
    normalized = os.path.normcase(str(path)).replace("_", "-")
    if normalized.endswith("msedge.exe") or r"\microsoft\edge" in normalized or "edge-user-data" in normalized:
        return "edge"
    if normalized.endswith("chrome.exe") or r"\google\chrome" in normalized or "chrome-user-data" in normalized:
        return "chrome"
    return None


def resolve_browser_path(explicit: Path | None = None, preferred_family: str | None = None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)

    env_path = os.getenv("GSC_PLAYWRIGHT_BROWSER_PATH")
    if env_path:
        candidates.append(Path(env_path))

    local_app_data = os.getenv("LOCALAPPDATA")
    local_paths: dict[str, list[Path]] = {"chrome": [], "edge": []}
    installed_paths: dict[str, list[Path]] = {
        "chrome": [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ],
        "edge": [
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        ],
    }
    if local_app_data:
        base = Path(local_app_data)
        local_paths["chrome"].append(base / "Google" / "Chrome" / "Application" / "chrome.exe")
        local_paths["edge"].append(base / "Microsoft" / "Edge" / "Application" / "msedge.exe")

    preferred_family = preferred_family if preferred_family in {"chrome", "edge"} else None
    ordered_families = [preferred_family] if preferred_family else []
    ordered_families.extend(family for family in ["chrome", "edge"] if family not in ordered_families)
    for family in ordered_families:
        candidates.extend(local_paths[family])
        candidates.extend(installed_paths[family])

    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Chrome or Edge executable not found. Set GSC_PLAYWRIGHT_BROWSER_PATH if needed.")


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


def resolve_default_source_user_data_dir() -> Path | None:
    explicit = os.getenv("GSC_PLAYWRIGHT_SOURCE_USER_DATA_DIR", "").strip()
    if explicit:
        candidate = Path(explicit)
        if candidate.exists():
            return candidate

    candidates: list[Path] = []

    local_app_data = get_local_app_data_dir()
    if local_app_data is None and os.getenv("LOCALAPPDATA"):
        local_app_data = Path(os.getenv("LOCALAPPDATA", ""))
    if local_app_data is not None:
        candidates.extend(
            [
                local_app_data / "Google" / "Chrome" / "User Data",
                local_app_data / "Microsoft" / "Edge" / "User Data",
            ]
        )

    users_root = Path(r"C:\Users")
    if users_root.exists():
        for user_dir in users_root.iterdir():
            if not user_dir.is_dir():
                continue
            candidates.extend(
                [
                    user_dir / "AppData" / "Local" / "Google" / "Chrome" / "User Data",
                    user_dir / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data",
                ]
            )

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate))
        if key in seen or not candidate.exists():
            continue
        seen.add(key)
        deduped.append(candidate)

    if not deduped:
        return None

    def candidate_priority(candidate: Path) -> tuple[int, float]:
        normalized = os.path.normcase(str(candidate))
        current_user_rank = (
            1
            if local_app_data is not None
            and normalized.startswith(os.path.normcase(str(local_app_data)))
            else 0
        )
        try:
            modified_at = candidate.stat().st_mtime
        except OSError:
            modified_at = 0.0
        return current_user_rank, modified_at

    deduped.sort(key=candidate_priority, reverse=True)
    return deduped[0]


def safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    return cleaned or "default"


def infer_browser_process_name(source_user_data_dir: Path) -> str | None:
    browser_family = infer_browser_family_from_path(source_user_data_dir)
    if browser_family == "chrome":
        return "chrome.exe"
    if browser_family == "edge":
        return "msedge.exe"
    return None


def is_browser_process_running(process_name: str) -> bool:
    completed = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (completed.stdout or "").lower()
    return process_name.lower() in output and "no tasks are running" not in output


def should_use_source_dir_directly(source_user_data_dir: Path) -> bool:
    process_name = infer_browser_process_name(source_user_data_dir)
    if process_name is None:
        return False
    return not is_browser_process_running(process_name)


def copy_tree_filtered(source: Path, target: Path, include_names: set[str], required: bool = False) -> None:
    if not source.exists():
        if required:
            raise FileNotFoundError(f"Missing source path: {source}")
        return

    target.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        if child.name not in include_names:
            continue
        destination = target / child.name
        if child.is_dir():
            shutil.copytree(child, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(child, destination)


def resolve_source_user_data_dir_from_args(args: argparse.Namespace) -> Path | None:
    source_user_data_dir = args.source_user_data_dir
    if source_user_data_dir is None:
        env_source = os.getenv("GSC_PLAYWRIGHT_SOURCE_USER_DATA_DIR", "").strip()
        if env_source:
            source_user_data_dir = Path(env_source)
    if source_user_data_dir is None:
        source_user_data_dir = resolve_default_source_user_data_dir()
    return source_user_data_dir


def prepare_runtime_user_data_dir(args: argparse.Namespace, source_user_data_dir: Path | None = None) -> Path:
    if source_user_data_dir is None:
        source_user_data_dir = resolve_source_user_data_dir_from_args(args)
    if source_user_data_dir is None:
        args.user_data_dir.mkdir(parents=True, exist_ok=True)
        return args.user_data_dir

    if not source_user_data_dir.exists():
        raise FileNotFoundError(f"Browser source user data dir not found: {source_user_data_dir}")

    profile_name = args.profile_directory
    source_profile_dir = source_user_data_dir / profile_name
    if not source_profile_dir.exists():
        raise FileNotFoundError(
            f"Browser profile directory not found: {source_profile_dir}. "
            "Adjust --profile-directory if your logged-in browser uses another profile."
        )

    if should_use_source_dir_directly(source_user_data_dir):
        return source_user_data_dir

    snapshot_root = args.snapshot_user_data_dir
    snapshot_root.mkdir(parents=True, exist_ok=True)
    runtime_dir = snapshot_root / safe_slug(source_user_data_dir.parent.name + "-" + source_user_data_dir.name)
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    try:
        copy_tree_filtered(source_user_data_dir, runtime_dir, USER_DATA_ROOT_INCLUDE_NAMES)
        copy_tree_filtered(source_profile_dir, runtime_dir / profile_name, PROFILE_INCLUDE_NAMES, required=True)
    except (PermissionError, shutil.Error) as exc:
        raise RuntimeError(
            "Browser session copy failed because the source Chrome/Edge profile is in use. "
            "Close the source browser once and rerun, or switch back to the dedicated Playwright profile."
        ) from exc
    return runtime_dir


def find_playwright_node_modules(cache_dir: Path) -> Path | None:
    npx_root = cache_dir / "_npx"
    if not npx_root.exists():
        return None
    candidates: list[Path] = []
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


def run_driver(config: dict[str, Any], paths: RuntimePaths) -> dict[str, Any]:
    driver = script_dir() / "google_index_playwright_driver.js"
    if not driver.exists():
        raise FileNotFoundError(f"Missing Playwright driver: {driver}")

    node_command = resolve_node_command()
    npx_command = resolve_npx_command()
    cache_dir = repo_root() / ".playwright-npm-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    node_modules_path = ensure_playwright_node_modules(cache_dir, npx_command)

    browsers_dir = repo_root() / ".playwright-browsers"
    browsers_dir.mkdir(parents=True, exist_ok=True)

    fd, config_path_str = tempfile.mkstemp(
        prefix="gsc-playwright-",
        suffix=".json",
        dir=str(paths.temp),
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
        env["TEMP"] = str(paths.temp)
        env["TMP"] = str(paths.temp)

        completed = subprocess.run(
            [node_command, str(driver), "--config", str(config_path)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(repo_root()),
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(details or "Google Search Console automation failed.") from exc
    finally:
        config_path.unlink(missing_ok=True)

    return json.loads(completed.stdout)


def run_auth(args: argparse.Namespace, paths: RuntimePaths) -> int:
    source_user_data_dir = resolve_source_user_data_dir_from_args(args)
    preferred_family = infer_browser_family_from_path(source_user_data_dir) or infer_browser_family_from_path(
        args.user_data_dir
    )
    browser_path = resolve_browser_path(args.chrome_path, preferred_family=preferred_family)
    user_data_dir = args.user_data_dir
    user_data_dir.mkdir(parents=True, exist_ok=True)

    result = run_driver(
        {
            "mode": "auth",
            "siteUrl": args.site_url,
            "chromePath": str(browser_path),
            "userDataDir": str(user_data_dir),
            "profileDirectory": args.profile_directory,
            "outputDir": str(paths.output),
            "timeoutSeconds": args.timeout_seconds,
        },
        paths,
    )
    write_log(paths, f"auth_ok site_url={args.site_url} profile={user_data_dir}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def run_submit(args: argparse.Namespace, paths: RuntimePaths) -> int:
    source_user_data_dir = resolve_source_user_data_dir_from_args(args)
    preferred_family = infer_browser_family_from_path(source_user_data_dir)
    browser_path = resolve_browser_path(args.chrome_path, preferred_family=preferred_family)
    user_data_dir = prepare_runtime_user_data_dir(args, source_user_data_dir=source_user_data_dir)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    current_urls = dedupe_keep_order(fetch_sitemap_urls(args.sitemap_url))
    if not current_urls:
        raise RuntimeError(f"No URLs found in sitemap: {args.sitemap_url}")

    state = load_state(paths.state_file)
    known_urls = dedupe_keep_order(list(state.get("known_urls", [])))
    pending_urls = dedupe_keep_order(list(state.get("pending_urls", [])))

    discovered_new_urls = [url for url in current_urls if url not in set(known_urls)]
    updated_known_urls = dedupe_keep_order(known_urls + current_urls)

    first_run = not paths.state_file.exists()
    if first_run and not args.submit_existing_on_first_run:
        state["known_urls"] = updated_known_urls
        state["pending_urls"] = []
        state["last_sitemap_url"] = args.sitemap_url
        state["last_run_at"] = now_local().isoformat()
        save_json(paths.state_file, state)
        write_log(
            paths,
            f"bootstrap_only sitemap_url={args.sitemap_url} known_urls={len(updated_known_urls)}",
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "bootstrapped": True,
                    "knownUrls": len(updated_known_urls),
                    "message": "Initial baseline saved. Future new URLs will be submitted.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    pending_urls = dedupe_keep_order(pending_urls + discovered_new_urls)
    batch = pending_urls[: args.max_urls_per_run]

    if not batch:
        state["known_urls"] = updated_known_urls
        state["pending_urls"] = pending_urls
        state["last_sitemap_url"] = args.sitemap_url
        state["last_run_at"] = now_local().isoformat()
        save_json(paths.state_file, state)
        write_log(paths, f"no_new_urls sitemap_url={args.sitemap_url} known_urls={len(updated_known_urls)}")
        print(json.dumps({"ok": True, "newUrls": 0, "pendingUrls": 0}, ensure_ascii=False, indent=2))
        return 0

    if args.dry_run:
        write_log(paths, f"dry_run pending_urls={len(batch)}")
        print(json.dumps({"ok": True, "dryRun": True, "urls": batch}, ensure_ascii=False, indent=2))
        return 0

    result = run_driver(
        {
            "mode": "requestIndexing",
            "siteUrl": args.site_url,
            "urls": batch,
            "chromePath": str(browser_path),
            "userDataDir": str(user_data_dir),
            "profileDirectory": args.profile_directory,
            "outputDir": str(paths.output),
            "timeoutSeconds": args.timeout_seconds,
        },
        paths,
    )

    submitted_urls = dict(state.get("submitted_urls", {}))
    success_urls: list[str] = []
    failed_urls: list[str] = []
    for item in result.get("results", []):
        url = str(item.get("url", "")).strip()
        status = str(item.get("status", "")).strip()
        if not url:
            continue
        if status in {"requested", "clicked_request_button", "already_submitted_or_unavailable"}:
            submitted_urls[url] = {
                "submittedAt": now_local().isoformat(),
                "status": status,
                "inspectUrl": item.get("inspectUrl"),
            }
            success_urls.append(url)
        else:
            failed_urls.append(url)

    remaining_pending = [url for url in pending_urls if url not in set(success_urls)]
    state["known_urls"] = updated_known_urls
    state["pending_urls"] = dedupe_keep_order(remaining_pending)
    state["submitted_urls"] = submitted_urls
    state["last_sitemap_url"] = args.sitemap_url
    state["last_run_at"] = now_local().isoformat()
    save_json(paths.state_file, state)

    write_log(
        paths,
        "run_done "
        f"new_discovered={len(discovered_new_urls)} "
        f"submitted={len(success_urls)} failed={len(failed_urls)} pending={len(state['pending_urls'])}",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    load_env()
    args = parse_args()
    paths = ensure_paths(args.log_root, args.output_dir)

    try:
        if args.command == "auth":
            return run_auth(args, paths)
        if args.command == "run":
            return run_submit(args, paths)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Unsupported command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
