#!/usr/bin/env python3
"""Build a catalog from explicitly open, first-party media APIs."""

from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "catalog.json"
USER_AGENT = "ysc-public-media/1.0 (+https://github.com/Elanlin/ysc-public-media)"
IA_LIMIT = max(1, int(os.getenv("IA_LIMIT", "12")))
NASA_LIMIT = max(1, int(os.getenv("NASA_LIMIT", "10")))
NASA_USAGE_URL = "https://www.nasa.gov/nasa-brand-center/images-and-media/"


def request_json(url: str, timeout: int = 30, attempts: int = 3) -> Any:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(1.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def clean_text(value: Any, limit: int = 1000) -> str:
    if isinstance(value, list):
        value = " / ".join(str(part) for part in value)
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def safe_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url.replace("http://", "https://", 1))
    path = urllib.parse.quote(urllib.parse.unquote(parts.path), safe="/%:@")
    return urllib.parse.urlunsplit(("https", parts.netloc, path, parts.query, ""))


def allowed_license(url: str) -> bool:
    value = (url or "").lower().replace("http://", "https://")
    return any(
        marker in value
        for marker in (
            "creativecommons.org/licenses/publicdomain/",
            "creativecommons.org/licenses/by/",
            "creativecommons.org/licenses/by-sa/",
            "creativecommons.org/licenses/zero/",
        )
    )


def license_name(url: str) -> str:
    value = (url or "").lower()
    if "publicdomain" in value:
        return "Public Domain"
    if "/zero/" in value:
        return "CC0"
    if "/by-sa/" in value:
        return "CC BY-SA"
    if "/by/" in value:
        return "CC BY"
    return "Open license"


def choose_ia_video(files: list[dict[str, Any]]) -> str | None:
    candidates: list[tuple[int, int, str]] = []
    for file in files:
        name = str(file.get("name") or "")
        lower = name.lower()
        if not lower.endswith(".mp4") or lower.startswith("__"):
            continue
        if any(word in lower for word in ("sample", "trailer", "preview")):
            continue
        try:
            size = int(file.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if size and (size < 1_000_000 or size > 1_500_000_000):
            continue
        fmt = str(file.get("format") or "").lower()
        score = 0
        if "512kb" in lower:
            score += 80
        if "h.264" in fmt or "mpeg4" in fmt:
            score += 40
        if file.get("source") == "derivative":
            score += 10
        if 5_000_000 <= size <= 400_000_000:
            score += 15
        candidates.append((score, -size, name))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def fetch_prelinger() -> list[dict[str, Any]]:
    query = "collection:prelinger AND mediatype:movies AND licenseurl:* AND format:MPEG4"
    params = [
        ("q", query),
        ("fl[]", "identifier"),
        ("fl[]", "title"),
        ("fl[]", "licenseurl"),
        ("fl[]", "creator"),
        ("fl[]", "date"),
        ("fl[]", "downloads"),
        ("sort[]", "downloads desc"),
        ("rows", str(max(IA_LIMIT * 3, 40))),
        ("page", "1"),
        ("output", "json"),
    ]
    search_url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(params)
    documents = request_json(search_url)["response"]["docs"]
    items: list[dict[str, Any]] = []

    for document in documents:
        if len(items) >= IA_LIMIT:
            break
        identifier = str(document.get("identifier") or "")
        listed_license = str(document.get("licenseurl") or "")
        if not identifier or not allowed_license(listed_license):
            continue
        metadata = request_json(
            "https://archive.org/metadata/" + urllib.parse.quote(identifier, safe=""),
            timeout=20,
            attempts=2,
        )
        item_meta = metadata.get("metadata") or {}
        license_url = str(item_meta.get("licenseurl") or listed_license)
        if not allowed_license(license_url):
            continue
        filename = choose_ia_video(metadata.get("files") or [])
        if not filename:
            continue
        date = clean_text(item_meta.get("date") or document.get("date"), 20)
        creator = clean_text(item_meta.get("creator") or document.get("creator"), 200)
        play_url = safe_url(
            "https://archive.org/download/"
            + urllib.parse.quote(identifier, safe="")
            + "/"
            + urllib.parse.quote(filename, safe="/")
        )
        items.append(
            {
                "id": "ia:" + identifier,
                "category": "prelinger",
                "name": clean_text(item_meta.get("title") or document.get("title"), 160),
                "pic": "https://archive.org/download/"
                + urllib.parse.quote(identifier, safe="")
                + "/__ia_thumb.jpg",
                "remarks": "公版 · " + (date[:4] if date else "Prelinger"),
                "year": date[:4] if re.match(r"^\d{4}", date) else "",
                "area": "",
                "director": creator,
                "actor": "",
                "content": clean_text(item_meta.get("description"), 1000),
                "source": "Internet Archive / Prelinger",
                "license": license_name(license_url),
                "license_url": safe_url(license_url),
                "detail_url": "https://archive.org/details/"
                + urllib.parse.quote(identifier, safe=""),
                "play_url": play_url,
                "mime": "video/mp4",
            }
        )
    return items


def choose_nasa_video(urls: list[str]) -> str | None:
    mp4s = [safe_url(url) for url in urls if str(url).lower().endswith(".mp4")]
    for marker in ("~medium.mp4", "~small.mp4", "~mobile.mp4", "~preview.mp4"):
        for url in mp4s:
            if url.lower().endswith(marker):
                return url
    return mp4s[0] if mp4s else None


def fetch_nasa() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in ("earth", "mars", "space station"):
        params = urllib.parse.urlencode(
            {"q": query, "media_type": "video", "page_size": max(NASA_LIMIT, 10)}
        )
        results = request_json("https://images-api.nasa.gov/search?" + params)
        for result in results.get("collection", {}).get("items", []):
            if len(items) >= NASA_LIMIT:
                return items
            data = (result.get("data") or [{}])[0]
            nasa_id = str(data.get("nasa_id") or "")
            if not nasa_id or nasa_id in seen or str(data.get("media_type")) != "video":
                continue
            try:
                assets = request_json(
                    str(result.get("href") or ""), timeout=15, attempts=1
                )
            except Exception:
                continue
            play_url = choose_nasa_video(assets if isinstance(assets, list) else [])
            if not play_url:
                continue
            links = result.get("links") or []
            picture = ""
            for link in links:
                if link.get("render") == "image" and (
                    link.get("rel") == "preview" or not picture
                ):
                    picture = safe_url(str(link.get("href") or ""))
                    if link.get("rel") == "preview":
                        break
            date = clean_text(data.get("date_created"), 20)
            creator = clean_text(data.get("secondary_creator") or data.get("center"), 200)
            items.append(
                {
                    "id": "nasa:" + nasa_id,
                    "category": "nasa",
                    "name": clean_text(data.get("title"), 160),
                    "pic": picture,
                    "remarks": "NASA · " + (date[:4] if date else "官方"),
                    "year": date[:4] if re.match(r"^\d{4}", date) else "",
                    "area": "美国",
                    "director": creator,
                    "actor": "",
                    "content": clean_text(data.get("description"), 1000),
                    "source": "NASA Image and Video Library",
                    "license": "NASA Media Usage Guidelines",
                    "license_url": NASA_USAGE_URL,
                    "detail_url": "https://images.nasa.gov/details/"
                    + urllib.parse.quote(nasa_id, safe=""),
                    "play_url": play_url,
                    "mime": "video/mp4",
                }
            )
            seen.add(nasa_id)
    return items


def previous_items(category: str) -> list[dict[str, Any]]:
    if not OUTPUT.exists():
        return []
    try:
        data = json.loads(OUTPUT.read_text(encoding="utf-8"))
        return [item for item in data.get("items", []) if item.get("category") == category]
    except (OSError, ValueError):
        return []


def build() -> dict[str, Any]:
    statuses: list[dict[str, str]] = []
    all_items: list[dict[str, Any]] = []
    for category, name, fetcher in (
        ("prelinger", "Internet Archive / Prelinger", fetch_prelinger),
        ("nasa", "NASA Image and Video Library", fetch_nasa),
    ):
        try:
            source_items = fetcher()
            if not source_items:
                raise RuntimeError("upstream returned no playable items")
            statuses.append({"name": name, "status": "ok", "items": str(len(source_items))})
        except Exception as exc:
            source_items = previous_items(category)
            statuses.append(
                {"name": name, "status": "fallback", "message": clean_text(exc, 300)}
            )
        all_items.extend(source_items)

    if len(all_items) < 4:
        raise RuntimeError("catalog has fewer than four playable items; refusing to overwrite")

    all_items.sort(key=lambda item: (item.get("category", ""), item.get("name", "")))
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "notice": "Only official open-media APIs are used. Verify each item's original license before reuse.",
        "sources": statuses,
        "categories": [
            {"id": "prelinger", "name": "公版历史影像"},
            {"id": "nasa", "name": "NASA 官方影像"},
        ],
        "items": all_items,
    }


def main() -> int:
    catalog = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(catalog['items'])} items to {OUTPUT}")
    for source in catalog["sources"]:
        print(source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
