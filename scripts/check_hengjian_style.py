#!/usr/bin/env python3
"""Check common Hengjian-style problems in a Chinese Markdown or text article."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


HARD_PATTERNS = {
    "破折号": re.compile(r"[—–]"),
    "翻案腔": re.compile(
        r"(?:不是.{0,30}而是|并非.{0,30}而是|不在于.{0,30}而在于|"
        r"与其说.{0,30}不如说|看似.{0,30}实则|你以为.{0,30}其实)"
    ),
}

MODEL_PHRASES = (
    "赋能",
    "抓手",
    "降本增效",
    "底层逻辑",
    "顶层设计",
    "认知跃迁",
    "价值闭环",
    "全链路",
    "组合拳",
    "打开想象空间",
)

ABSOLUTE_WORDS = (
    "必然",
    "完全取代",
    "全部取代",
    "一定会",
    "所有公司",
    "所有岗位",
)

SLANG_WORDS = (
    "做掉",
    "干掉",
    "吊打",
    "杀疯了",
)


def strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"https?://\S+", "", text)
    return text


def content_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block or block.startswith("#") or block.startswith("|"):
            continue
        if re.match(r"^(?:[-*+] |\d+[.、]\s*)", block):
            continue
        paragraphs.append(block)
    return paragraphs


def sentence_count(paragraph: str) -> int:
    clean = re.sub(r"\[[^]]+\]\([^)]+\)", "", paragraph)
    return len(re.findall(r"[。！？?!]", clean)) or 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("article", type=Path, help="UTF-8 Markdown or text file")
    args = parser.parse_args()

    try:
        text = args.article.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR 无法读取文件: {exc}")
        return 2

    failures: list[str] = []
    warnings: list[str] = []
    scan_text = strip_markdown(text)

    for label, pattern in HARD_PATTERNS.items():
        matches = pattern.findall(scan_text)
        if matches:
            failures.append(f"{label} {len(matches)} 处")

    for phrase in MODEL_PHRASES:
        count = scan_text.count(phrase)
        if count:
            failures.append(f"模型或商业黑话“{phrase}” {count} 处")

    for word in ABSOLUTE_WORDS:
        count = scan_text.count(word)
        if count:
            warnings.append(f"绝对化表达“{word}” {count} 处，请核对证据边界")

    for word in SLANG_WORDS:
        count = scan_text.count(word)
        if count:
            warnings.append(f"过度口语化表达“{word}” {count} 处")

    colon_count = len(re.findall(r"[：:]", scan_text))
    if colon_count:
        warnings.append(
            f"冒号 {colon_count} 处，只保留引出人物直接原话的用法"
        )

    headings = re.findall(r"^#{1,6}\s+(.+)$", text, flags=re.M)
    for heading in headings:
        plain = re.sub(r"[*_`\[\]()]", "", heading).strip()
        if len(plain) > 24:
            warnings.append(f"小标题偏长“{plain}”")

    paragraphs = content_paragraphs(text)
    if paragraphs:
        single = sum(sentence_count(p) == 1 for p in paragraphs)
        ratio = single / len(paragraphs)
        if len(paragraphs) >= 8 and ratio > 0.55:
            warnings.append(
                f"单句段落占比 {ratio:.0%}，可能接近口播稿，建议合并普通段落"
            )

    bold_blocks = re.findall(r"\*\*[^*\n]{4,}\*\*", text)
    han_count = len(re.findall(r"[\u4e00-\u9fff]", scan_text))
    recommended_bold = max(4, han_count // 400 + 2)
    if len(bold_blocks) > recommended_bold:
        warnings.append(
            f"重点加粗 {len(bold_blocks)} 处，文章约 {han_count} 个汉字，重点可能过密"
        )

    numeric_claims = re.findall(r"\d+(?:\.\d+)?%|\d{3,4}年", scan_text)
    has_references = bool(re.search(r"^#{1,6}\s*参考资料", text, flags=re.M))
    if numeric_claims and not has_references:
        warnings.append("正文包含年份或百分比，但没有“参考资料”部分")

    print(f"汉字数 {han_count}")
    if failures:
        print("失败项")
        for item in failures:
            print(f"- {item}")
    if warnings:
        print("警告项")
        for item in warnings:
            print(f"- {item}")
    if not failures and not warnings:
        print("未发现规则覆盖的问题")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
