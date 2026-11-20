#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify that a structured Markdown transcript preserves every cleaned sentence exactly."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {"sentence_id", "text"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("TSV 必须包含表头 sentence_id 和 text。")
    return rows


def markdown_body(path: Path) -> tuple[list[str], list[str], list[str]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    excluded: list[str] = []
    headings: list[str] = []
    body: list[str] = []
    in_frontmatter = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if index == 0 and stripped == "---":
            in_frontmatter = True
            excluded.append(line)
            continue
        if in_frontmatter:
            excluded.append(line)
            if stripped == "---":
                in_frontmatter = False
            continue
        if stripped.startswith("#"):
            headings.append(stripped)
            continue
        if not stripped or stripped.startswith(">") or stripped == "---":
            excluded.append(line)
            continue
        if re.match(r"^[-*+]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
            raise ValueError(f"正文第 {index + 1} 行出现列表；整理稿正文应为逐字保留的段落，而非摘要列表。")
        body.append(stripped)
    return body, headings, excluded


def find_sequence(haystack: str, needle: str, start: int = 0) -> int:
    return haystack.find(needle, start)


def main() -> int:
    parser = argparse.ArgumentParser(description="检查整理稿是否完整、按序、逐字包含清洗后的所有句子。")
    parser.add_argument("sentences_tsv", type=Path)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Markdown 校对报告路径")
    args = parser.parse_args()
    tsv_path = args.sentences_tsv.expanduser().resolve()
    md_path = args.transcript.expanduser().resolve()
    report_path = args.output.expanduser().resolve()

    rows = read_tsv(tsv_path)
    body, headings, excluded = markdown_body(md_path)
    body_text = "\n".join(body)
    ids = [row["sentence_id"] for row in rows]
    duplicate_ids = [key for key, count in Counter(ids).items() if count > 1]
    issues: list[str] = []
    positions: list[tuple[str, int]] = []
    for row in rows:
        sid = row["sentence_id"]
        text = row["text"]
        count = body_text.count(text)
        if count == 0:
            issues.append(f"缺失或句内字符被改动: {sid} | {text}")
            continue
        if count > 1:
            issues.append(f"同一清洗句出现 {count} 次: {sid} | {text}")
        positions.append((sid, body_text.find(text)))

    for (previous_id, previous), (current_id, current) in zip(positions, positions[1:]):
        if previous > current:
            issues.append(f"句子顺序异常: {previous_id} 位于 {current_id} 之后")

    covered = [False] * len(body_text)
    for row in rows:
        text = row["text"]
        start = 0
        while True:
            position = find_sequence(body_text, text, start)
            if position < 0:
                break
            for index in range(position, position + len(text)):
                covered[index] = True
            start = position + len(text)
    leftovers: list[str] = []
    current = ""
    for char, is_covered in zip(body_text, covered):
        if char == "\n":
            if current.strip():
                leftovers.append(current.strip())
            current = ""
        elif not is_covered:
            current += char
        elif current.strip():
            leftovers.append(current.strip())
            current = ""
    if current.strip():
        leftovers.append(current.strip())
    if leftovers:
        issues.append(f"发现 {len(leftovers)} 段不属于清洗句子的正文字符（可能为新增或改写内容）。")

    passed = not issues and not duplicate_ids
    status = "通过" if passed else "未通过"
    report = [
        "# 整理稿校对报告",
        "",
        f"- **结论：{status}**",
        f"- 清洗句子数：{len(rows)}",
        f"- 整理稿标题数：{len(headings)}",
        f"- 正文非空段落数：{len(body)}",
        f"- 缺失或改动：{sum('缺失或句内字符被改动' in issue for issue in issues)}",
        f"- 顺序异常：{sum('句子顺序异常' in issue for issue in issues)}",
        f"- 非源句正文字符片段：{len(leftovers)}",
        "",
        "## 校验口径",
        "",
        "本报告逐字检查清洗后的每个句子是否在 Markdown 正文中恰好出现、保持原序，并检查正文是否含非源句字符。标题和引用块中的固定整理说明不计入正文。该校验不证明原始字幕识别正确，也不进行事实核查。",
        "",
        "## 待处理项",
        "",
    ]
    if duplicate_ids:
        report.append("- TSV 句子编号重复：" + "、".join(duplicate_ids))
    if issues:
        report.extend(f"- {issue}" for issue in issues)
    if leftovers:
        report.extend(["", "### 非源句正文字符", ""] + [f"- `{item}`" for item in leftovers[:100]])
    if passed:
        report.append("- 无。全部清洗句均逐字保留，未发现漏句、重句、乱序或正文新增字符。")
    report.extend([
        "",
        "## 后续人工复核",
        "",
        "- 原始字幕中的专有名词、数字、英文和同音字未作订正；如需准确版本，请对照音频另行复核。",
        "- 本报告的“通过”只代表整理稿忠实于清洗结果，不代表讲者观点正确或字幕识别准确。",
        "",
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"校验{status}: {report_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(f"错误: {error}", file=sys.stderr)
        sys.exit(2)
