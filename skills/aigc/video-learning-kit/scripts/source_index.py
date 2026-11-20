#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Index a structured Markdown transcript by chapter and paragraph for study aids."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="为整理稿建立章节/段落只读定位索引。")
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.transcript.expanduser().resolve()
    destination = args.output.expanduser().resolve()
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    chapters: list[dict] = []
    current: dict | None = None
    title = source.stem
    in_frontmatter = False
    for number, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if number == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if stripped.startswith("# "):
            title = stripped[2:].strip()
        match = re.match(r"^(#{2,6})\s+(.+)$", stripped)
        if match:
            current = {
                "heading": match.group(2).strip(),
                "level": len(match.group(1)),
                "line": number,
                "paragraphs": [],
            }
            chapters.append(current)
            continue
        if not stripped or stripped.startswith("#") or stripped.startswith(">") or stripped == "---":
            continue
        if current is None:
            current = {"heading": "开篇", "level": 2, "line": number, "paragraphs": []}
            chapters.append(current)
        current["paragraphs"].append({
            "ref": f"{current['heading']} · 段{len(current['paragraphs']) + 1}",
            "line": number,
            "text": stripped,
        })
    if not chapters:
        raise ValueError("未找到正文；请先完成字幕整理与章节划分。")
    for chapter in chapters:
        chapter["id"] = f"ch{chapters.index(chapter) + 1:02d}"
        for index, paragraph in enumerate(chapter["paragraphs"], 1):
            paragraph["id"] = f"{chapter['id']}-p{index:02d}"
            paragraph["ref"] = f"{chapter['heading']} · 段{index}"
    data = {"source": str(source), "title": title, "chapters": chapters}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chapters": len(chapters), "paragraphs": sum(len(c["paragraphs"]) for c in chapters)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(f"错误: {error}", file=sys.stderr)
        sys.exit(1)
