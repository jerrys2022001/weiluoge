#!/usr/bin/env python3
"""Rebuild sitemap.xml from the site's current public HTML files."""

from __future__ import annotations

import argparse
from pathlib import Path

from sitemap_sync import sync_sitemap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild sitemap.xml from public HTML files.")
    parser.add_argument(
        "--site-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Site root containing sitemap.xml and public HTML files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    site_root = args.site_root.resolve()
    result = sync_sitemap(site_root)
    print(
        f"sitemap={'updated' if result.changed else 'unchanged'} "
        f"url_count={result.url_count} added={len(result.added)} removed={len(result.removed)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
