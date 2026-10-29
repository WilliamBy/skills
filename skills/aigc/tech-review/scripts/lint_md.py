#!/usr/bin/env python3
"""Markdown 结构自检器（零第三方依赖）。

检查项：
  E101 代码围栏未闭合            E102 表格列数与表头不一致
  E103 空链接 [x]()              E104 文档缺少一级标题
  E105 代码围栏语言标注缺失      E106 表格分隔行与表头列数不一致
  W201 标题层级跳跃              W202 多个一级标题
  W203 表格/列表前缺少空行       W204 连续多个空行
  W205 标题末尾带标点            W206 重复标题
  W207 内部锚点链接无法解析      W208 行尾多余空格
  W209 加粗标记未成对            W210 全角空格或零宽字符

用法：
  python lint_md.py <file.md>
  python lint_md.py a.md b.md --quiet
退出码：0 = 无错误（可能有警告），1 = 存在错误，2 = 文件不可读。
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]*)\)")
LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s+")

issues: list[tuple[int, str, str, str]] = []


def add(line: int, level: str, code: str, message: str) -> None:
    issues.append((line, level, code, message))


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells: list[str] = []
    buf = ""
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            buf += "|"
            i += 2
            continue
        if ch == "|":
            cells.append(buf)
            buf = ""
        else:
            buf += ch
        i += 1
    cells.append(buf)
    return [c.strip() for c in cells]


def slugify(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[*_~]", "", t)
    out: list[str] = []
    for ch in t:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch.isspace():
            out.append("-")
    slug = "".join(out)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


def collect(path: Path) -> list[tuple[int, str, str, str]]:
    global issues
    issues = []
    lines = path.read_text(encoding="utf-8").splitlines()

    in_fence = False
    fence_open_line = 0
    fence_char = ""
    fence_len = 0
    blank_run = 0
    headings: list[tuple[int, int, str]] = []
    table: dict | None = None  # {"header": line_no, "cols": n}

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        fm = FENCE_RE.match(line)
        if fm:
            marker = fm.group(2)
            same_kind = marker[0] == fence_char and len(marker) >= fence_len
            if not in_fence:
                in_fence = True
                fence_open_line = idx
                fence_char, fence_len = marker[0], len(marker)
                info = fm.group(3).strip()
                if not info:
                    add(idx, "E", "E105", "代码块缺少语言标注（```bash / ```yaml / ```mermaid）")
                blank_run = 0
                table = None
                continue
            if same_kind and fm.group(3).strip() == "":
                in_fence = False
                blank_run = 0
                table = None
                continue
            # 不同种类/更短的围栏在块内视为普通内容
            continue

        if in_fence:
            continue

        if stripped == "":
            blank_run += 1
            if blank_run >= 2:
                add(idx, "W", "W204", "连续多个空行")
            table = None
            continue
        blank_run = 0

        if "\u3000" in line:
            add(idx, "W", "W210", "含全角空格 U+3000，建议改半角")
        if "\u200b" in line or "\ufeff" in line:
            add(idx, "W", "W210", "含零宽字符/BOM，渲染可能异常")
        if line != line.rstrip():
            add(idx, "W", "W208", "行尾存在多余空格")

        hm = HEADING_RE.match(line)
        if hm:
            table = None
            level = len(hm.group(1))
            text = hm.group(2)
            headings.append((idx, level, text))
            if text and text[-1] in "，。；：、,.;:":
                add(idx, "W", "W205", f"标题末尾带标点：{text}")
            continue

        # 表格：当前行是表头（下一行是分隔行）
        if "|" in line and idx < len(lines) and SEP_RE.match(lines[idx]):
            cols = len(split_row(line))
            sep_cols = len(split_row(lines[idx]))
            if cols != sep_cols:
                add(idx, "E", "E106", f"表头 {cols} 列，分隔行 {sep_cols} 列")
            if idx > 1 and lines[idx - 2].strip() != "":
                add(idx, "W", "W203", "表格前缺少空行，部分渲染器不识别")
            table = {"header": idx, "cols": cols}
            continue

        if table is not None:
            if "|" in line:
                body_cols = len(split_row(line))
                if body_cols != table["cols"]:
                    add(idx, "E", "E102", f"表格行列数 {body_cols} 与表头 {table['cols']} 不一致")
                continue
            table = None

        if LIST_RE.match(line):
            if idx > 1 and lines[idx - 2].strip() != "" and not LIST_RE.match(lines[idx - 2]):
                add(idx, "W", "W203", "列表前缺少空行")
            continue

        for href in LINK_RE.findall(line):
            if href.strip() == "":
                add(idx, "E", "E103", "存在空链接 ()")
            elif href.startswith("#"):
                anchor = href[1:].strip().lower()
                slugs = {slugify(h[2]) for h in headings}
                if anchor and anchor not in slugs:
                    add(idx, "W", "W207", f"内部锚点可能失效：#{anchor}")
        if line.count("**") % 2 == 1:
            add(idx, "W", "W209", "加粗标记 ** 未成对")

    if in_fence:
        add(fence_open_line, "E", "E101", f"代码围栏未闭合（第 {fence_open_line} 行开始）")

    h1 = [h for h in headings if h[1] == 1]
    if not h1:
        add(1, "E", "E104", "文档缺少一级标题（# 标题）")
    elif len(h1) > 1:
        for line_no, _, text in h1[1:]:
            add(line_no, "W", "W202", f"存在多个一级标题：{text}")

    prev = 0
    for line_no, level, text in headings:
        if prev and level > prev + 1:
            add(line_no, "W", "W201", f"标题层级跳跃：H{prev} → H{level}（{text}）")
        prev = level

    seen: dict[tuple[int, str], int] = {}
    for line_no, level, text in headings:
        key = (level, text.strip())
        if key in seen:
            add(line_no, "W", "W206", f"重复标题：{text}（首次在第 {seen[key]} 行）")
        else:
            seen[key] = line_no

    return issues


def report(path: Path, found: list[tuple[int, str, str, str]]) -> int:
    errors = [i for i in found if i[1] == "E"]
    warnings = [i for i in found if i[1] == "W"]
    if not found:
        print(f"OK  {path.name}  —  Markdown 结构检查通过")
        return 0
    for line_no, level, code, message in sorted(found, key=lambda x: (x[0], x[2])):
        flag = "[ERROR]" if level == "E" else "[WARN ]"
        print(f"{flag} {path.name}:{line_no}  {code}  {message}")
    print(f"合计：{len(errors)} 错误 / {len(warnings)} 警告")
    return 1 if errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Markdown 结构自检（零依赖）")
    ap.add_argument("files", nargs="+", help="待检查的 .md 文件")
    ap.add_argument("--quiet", action="store_true", help="仅输出汇总行")
    args = ap.parse_args()
    rc = 0
    for f in args.files:
        p = Path(f)
        if not p.exists():
            print(f"文件不存在：{p}", file=sys.stderr)
            rc = 2
            continue
        found = collect(p)
        if args.quiet:
            errs = sum(1 for i in found if i[1] == "E")
            print(f"{p.name}: {errs} 错误 / {len(found) - errs} 警告")
            rc = max(rc, 1 if errs else 0)
        else:
            rc = max(rc, report(p, found))
    return rc


if __name__ == "__main__":
    sys.exit(main())
