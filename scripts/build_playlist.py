#!/usr/bin/env python3
"""Generate a plain M3U playlist for clients that do not support JS spiders."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.json"
OUTPUT = ROOT / "data" / "open-media.m3u"


def m3u_text(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"[\r\n]+", " ", text)
    return text.replace('"', "'").strip()


def build() -> str:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    category_names = {
        entry["id"]: entry["name"] for entry in catalog.get("categories", [])
    }
    lines = ["#EXTM3U"]
    for item in catalog.get("items", []):
        item_id = m3u_text(item.get("id"))
        name = m3u_text(item.get("name"))
        logo = m3u_text(item.get("pic"))
        group = m3u_text(category_names.get(item.get("category"), "开放影视"))
        source = m3u_text(item.get("source"))
        lines.append(
            f'#EXTINF:-1 tvg-id="{item_id}" tvg-name="{name}" '
            f'tvg-logo="{logo}" group-title="{group}",{name} · {source}'
        )
        lines.append(str(item["play_url"]))
    return "\n".join(lines) + "\n"


def main() -> None:
    content = build()
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    count = sum(1 for line in content.splitlines() if line.startswith("#EXTINF:"))
    print(f"wrote {count} channels to {OUTPUT}")


if __name__ == "__main__":
    main()
