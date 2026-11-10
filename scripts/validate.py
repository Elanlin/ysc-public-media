#!/usr/bin/env python3
"""Validate generated files before publishing them."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require_https(url: str, field: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc:
        raise ValueError(f"{field} must be a public HTTPS URL: {url!r}")


def validate_catalog() -> None:
    catalog = load_json(ROOT / "data" / "catalog.json")
    categories = {entry["id"] for entry in catalog["categories"]}
    items = catalog.get("items") or []
    if len(items) < 4:
        raise ValueError("catalog must contain at least four items")

    seen = set()
    for index, item in enumerate(items):
        prefix = f"items[{index}]"
        for field in (
            "id",
            "category",
            "name",
            "source",
            "license",
            "license_url",
            "detail_url",
            "play_url",
        ):
            if not item.get(field):
                raise ValueError(f"{prefix}.{field} is required")
        if item["id"] in seen:
            raise ValueError(f"duplicate id: {item['id']}")
        seen.add(item["id"])
        if item["category"] not in categories:
            raise ValueError(f"unknown category: {item['category']}")
        if item.get("mime") != "video/mp4":
            raise ValueError(f"unsupported media type in {prefix}")
        require_https(item["license_url"], prefix + ".license_url")
        require_https(item["detail_url"], prefix + ".detail_url")
        require_https(item["play_url"], prefix + ".play_url")


def validate_config() -> None:
    config = load_json(ROOT / "config.json")
    site = config["sites"][0]
    if site.get("type") != 3 or not str(site.get("api", "")).endswith(".js"):
        raise ValueError("config must point to a type-3 JS spider")
    require_https(site["api"], "sites[0].api")
    require_https(site["ext"], "sites[0].ext")

    warehouse = load_json(ROOT / "warehouse.json")
    if not warehouse.get("urls"):
        raise ValueError("warehouse must contain at least one config URL")
    require_https(warehouse["urls"][0]["url"], "warehouse.urls[0].url")


def validate_playlist() -> None:
    lines = (ROOT / "data" / "open-media.m3u").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "#EXTM3U":
        raise ValueError("playlist must start with #EXTM3U")
    entries = [line for line in lines if line.startswith("#EXTINF:")]
    urls = [line for line in lines if line.startswith("https://")]
    if len(entries) < 4 or len(entries) != len(urls):
        raise ValueError("playlist entries and URLs must match")


def main() -> None:
    validate_catalog()
    validate_config()
    validate_playlist()
    print("catalog, playlist, and configuration are valid")


if __name__ == "__main__":
    main()
