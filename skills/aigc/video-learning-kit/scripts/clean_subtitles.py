#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conservatively clean subtitle text without correcting terminology or meaning."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

FILLERS = ("呃", "嗯", "诶", "欸")
STANDALONE_FILLERS = FILLERS + ("啊", "哎", "哎呀")
TAG_FILLERS = ("对吧", "对不对", "是吧")
REPEATED_PHRASES = (
    "这个", "那个", "然后", "就是", "我们", "你们", "他们", "可以", "应该",
    "因为", "所以", "但是", "如果", "现在", "这么", "那么", "只是", "还是",
    "已经", "不是", "没有", "一下", "时候", "自己", "这里", "那里",
)
REPEATED_CHARS = "我你他她它这那是就都也很也还再又有们"
HARD_END = "。？！?!"
SOFT_END = "，、：；,;:"
SENTENCE_ID = "S{:04d}"


@dataclass
class Sentence:
    sid: str
    section: int
    first_line: int
    last_line: int
    text: str


def read_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    raise ValueError("无法识别文本编码；请转换为 UTF-8 后重试。")


def strip_inline_formatting(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\{\\[^}]*\}", "", text)
    return text.strip()


def is_timestamp(line: str) -> bool:
    return bool(re.match(
        r"^\s*(?:\d+\s+)?(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[,.]\d{1,3})?\s*-->\s*"
        r"(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[,.]\d{1,3})?(?:\s+.*)?$", line))


def is_header(line: str) -> bool:
    return bool(re.match(
        r"^\s*(?:WEBVTT\b.*|Kind:\s*captions|Language:\s*.*|NOTE\b.*|STYLE\b.*|REGION\b.*)$",
        line, re.I))


def is_explicit_metadata(line: str) -> bool:
    s = line.strip()
    if re.match(r"^https?://\S+$", s, re.I):
        return True
    if re.match(r"^(?:标题|视频标题|来源|链接|视频链接|原视频|上传者|UP主|发布时间|上传时间)\s*[:：]", s, re.I):
        return True
    if re.match(r"^.{1,50}\s+\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$", s):
        return True
    return False


def normalize_spacing(text: str) -> str:
    text = re.sub(r"[\t\u3000 ]+", " ", text).strip()
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"(?<=[A-Za-z0-9])(?=[\u4e00-\u9fff])", " ", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])(?=[A-Za-z0-9])", " ", text)
    return text


def clean_text(text: str) -> str:
    """Apply a fixed allow-list of surface-only cleanup rules."""
    s = text.strip()
    # These syllables carry no lexical content in Chinese subtitle transcription.
    # Apply the same rule everywhere; do not infer meaning from the surrounding topic.
    s = re.sub(r"[呃嗯诶欸]+", "", s)
    s = re.sub(r"(?<=[\u4e00-\u9fff])啊(?=[\u4e00-\u9fff，。？！?!]|$)", "", s)
    s = re.sub(r"^(?:哎呀|哎|啊)(?=[，,]|$)", "", s)
    s = re.sub(r"[，,](?:哎呀|哎|啊)(?=[，。？！?!]|$)", "", s)
    s = re.sub(r"(?:^|[，,])\s*(?:对吧|对不对|是吧)[，,]?(?=[。？！?!]|$)", "", s)

    for ch in REPEATED_CHARS:
        s = re.sub(re.escape(ch) + r"{2,}", ch, s)
    for _ in range(2):
        for phrase in REPEATED_PHRASES:
            s = re.sub("(" + re.escape(phrase) + r")\1+", r"\1", s)

    s = re.sub(r"[，,]{2,}", "，", s)
    s = re.sub(r"。{2,}", "。", s)
    s = re.sub(r"[，,]+(?=[。？！?!])", "", s)
    s = re.sub(r"(?<=[。？！?!])[，,]", "", s)
    s = re.sub(r"^[，,、。？！?!：；;:]+", "", s)
    return normalize_spacing(s)


def split_comma_stutter(sentence: str) -> str:
    """Collapse only exact repetitions of the same short comma-delimited unit."""
    result: list[tuple[str, str]] = []
    for part in re.findall(r"[^，,]+[，,]?", sentence):
        separator = part[-1] if part[-1] in "，," else ""
        text = part[:-1] if separator else part
        if result and result[-1][0] == text and len(text) <= 12:
            continue
        result.append((text, separator))
    return "".join(text + separator for text, separator in result)


def split_long_sentence(text: str, first_line: int, last_line: int, max_chars: int) -> list[tuple[str, int, int]]:
    """Split at existing commas once a unit exceeds max_chars; never change lexical text."""
    units = [part for part in re.split(r"(?<=[，。！？?!])", text) if part]
    if len(units) <= 1:
        return [(text, first_line, last_line)]
    result: list[tuple[str, int, int]] = []
    current = ""
    start_line = first_line
    for unit in units:
        if current and len(current) + len(unit) > max_chars:
            result.append((current.rstrip("，") + "。", start_line, last_line))
            current = unit
            start_line = last_line
        else:
            current += unit
    if current:
        if current[-1] not in HARD_END:
            current = current.rstrip("，") + "。"
        result.append((current, start_line, last_line))
    return result


def parse_source(lines: list[str]) -> tuple[list[str], list[tuple[int, int, str]], list[str]]:
    """Return removed metadata, (line number, section index, text), and section names."""
    has_chapters = any(line.strip().startswith("[章节]") for line in lines)
    first_chapter = next((i for i, line in enumerate(lines) if line.strip().startswith("[章节]")), 0)
    removed: list[str] = []
    body: list[tuple[int, int, str]] = []
    sections: list[str] = []
    section = -1
    pending_srt_index = False
    previous_raw = ""
    duplicate_count = 0

    for index, raw in enumerate(lines):
        number = index + 1
        stripped = raw.strip()
        if not stripped:
            pending_srt_index = False
            continue
        if has_chapters and index < first_chapter:
            if is_explicit_metadata(stripped):
                removed.append(f"L{number}: {stripped}")
            continue
        if is_header(stripped) or is_timestamp(stripped):
            removed.append(f"L{number}: {stripped}")
            pending_srt_index = True
            continue
        if pending_srt_index and re.fullmatch(r"\d+", stripped):
            removed.append(f"L{number}: {stripped}")
            pending_srt_index = False
            continue
        if re.fullmatch(r"\d+", stripped) and index + 1 < len(lines) and is_timestamp(lines[index + 1].strip()):
            removed.append(f"L{number}: {stripped}")
            continue
        pending_srt_index = False
        if stripped.startswith("[章节]"):
            title = stripped.replace("[章节]", "", 1).strip() or "未命名原始章节"
            sections.append(title)
            section += 1
            previous_raw = ""
            continue
        if is_explicit_metadata(stripped):
            removed.append(f"L{number}: {stripped}")
            continue
        text = strip_inline_formatting(stripped)
        if not text:
            continue
        if section < 0:
            section = 0
            sections.append("全文")
        if text == previous_raw:
            duplicate_count += 1
            removed.append(f"L{number}: [相邻完全重复] {text}")
            continue
        body.append((number, section, text))
        previous_raw = text

    if duplicate_count:
        removed.append(f"相邻完全重复行共移除 {duplicate_count} 行")
    return removed, body, sections


def build_sentences(body: list[tuple[int, int, str]], max_chars: int) -> list[Sentence]:
    sentences: list[Sentence] = []
    buffer = ""
    section = 0
    first_line = 0
    last_line = 0

    def flush() -> None:
        nonlocal buffer, first_line, last_line
        text = split_comma_stutter(buffer).strip()
        text = re.sub(r"^[，,、。？！?!：；;:]+", "", text)
        text = re.sub(r"[，,]+(?=[。？！?!])", "", text)
        text = normalize_spacing(text)
        if text:
            if text[-1] not in HARD_END:
                text = text.rstrip(SOFT_END + " ") + "。"
            for chunk, start, end in split_long_sentence(text, first_line, last_line, max_chars):
                sentences.append(Sentence(SENTENCE_ID.format(len(sentences) + 1), section, start, end, chunk))
        buffer = ""
        first_line = 0

    for number, current_section, raw in body:
        if current_section != section and buffer:
            flush()
        section = current_section
        text = clean_text(raw)
        if not text:
            continue
        if not buffer:
            first_line = number
        last_line = number
        tail = text[-1]
        if tail in HARD_END:
            buffer += text
            flush()
        elif tail in SOFT_END:
            buffer += text[:-1] + "，"
        else:
            buffer += text
    if buffer:
        flush()
    return sentences


def main() -> int:
    parser = argparse.ArgumentParser(description="保守清洗原始字幕，输出带稳定编号的句子供推理分段。")
    parser.add_argument("source", type=Path, help="TXT/SRT/VTT 原始字幕文件")
    parser.add_argument("--output-dir", type=Path, required=True, help="输出目录；不得是源文件本身")
    parser.add_argument("--preview-chars", type=int, default=1500, help="中间稿固定分段的最大字符数")
    parser.add_argument("--max-sentence-chars", type=int, default=180, help="超长口播句在原有逗号处断句的目标阈值，不删改文字")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    if not source.is_file():
        parser.error(f"找不到字幕文件: {source}")
    if args.preview_chars < 500:
        parser.error("--preview-chars 不得小于 500")
    if args.max_sentence_chars < 80:
        parser.error("--max-sentence-chars 不得小于 80")

    text, encoding = read_text(source)
    lines = text.splitlines()
    removed, body, sections = parse_source(lines)
    sentences = build_sentences(body, args.max_sentence_chars)
    if not sentences:
        parser.error("未提取到字幕正文；请检查文件格式，不要对原文件执行覆盖。")
    output.mkdir(parents=True, exist_ok=True)

    with (output / "cleaned_sentences.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["sentence_id", "section_index", "source_first_line", "source_last_line", "text"])
        for item in sentences:
            writer.writerow([item.sid, item.section + 1, item.first_line, item.last_line, item.text])

    doc = [
        f"# {source.stem}",
        "",
        "> 中间稿：仅机械清洗与固定长度分段，尚未进行推理章节划分；不得作为最终整理稿交付。",
        "",
    ]
    current_section = -1
    length = 0
    paragraph_open = False
    for item in sentences:
        if item.section != current_section:
            current_section = item.section
            doc.extend([f"## {sections[current_section]}", ""])
            length = 0
            paragraph_open = False
        if length and length + len(item.text) > args.preview_chars:
            doc.append("")
            length = 0
            paragraph_open = False
        if paragraph_open:
            doc[-1] += item.text
        else:
            doc.append(item.text)
            paragraph_open = True
        length += len(item.text)
    doc.append("")
    (output / "cleaned_transcript.md").write_text("\n".join(doc).rstrip() + "\n", encoding="utf-8")
    (output / "metadata.txt").write_text("\n".join(removed) + "\n", encoding="utf-8")
    (output / "review.txt").write_text(
        "本脚本不进行术语、数字、同音字或语义订正。\n"
        "请通过原音频复核可疑识别内容；复核前必须保留 cleaned_sentences.tsv 中的原词。\n",
        encoding="utf-8",
    )
    manifest = {
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "encoding": encoding,
        "source_lines": len(lines),
        "body_lines": len(body),
        "sentences": len(sentences),
        "characters": sum(len(item.text) for item in sentences),
        "sections": sections,
        "preview_chars": args.preview_chars,
        "max_sentence_chars": args.max_sentence_chars,
        "rule_version": "conservative-v3",
        "script_version": "1.2.0",
        "guarantees": [
            "no_domain_corrections",
            "no_external_knowledge",
            "no_semantic_rewriting",
            "stable_sentence_ids",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("source", "sentences", "characters", "sections")}, ensure_ascii=False))
    print(f"输出目录: {output}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(f"错误: {error}", file=sys.stderr)
        sys.exit(1)
