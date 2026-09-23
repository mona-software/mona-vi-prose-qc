"""CLI cho mona-vi-prose-qc."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser

from .cliches_vi import load_custom_phrases
from .metrics import Config, analyze

BLOCK_TAGS = {
    "p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6",
    "tr", "section", "article", "blockquote",
}
SKIP_TAGS = {"script", "style", "head", "nav", "footer"}


class _HTMLTextExtractor(HTMLParser):
    """Trích text thuần từ HTML, giữ ranh giới đoạn ở các thẻ block."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._skip_tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            self._skip_tag_stack.append(tag)
            return
        if tag in BLOCK_TAGS:
            self._chunks.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS and self._skip_tag_stack and self._skip_tag_stack[-1] == tag:
            self._skip_tag_stack.pop()
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in BLOCK_TAGS:
            self._chunks.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        self._chunks.append(data)

    def get_text(self) -> str:
        return html_lib.unescape("".join(self._chunks))


def strip_html(raw: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(raw)
    text = parser.get_text()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_markdown(raw: str) -> str:
    text = raw
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    return text.strip()


def load_input(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        req = urllib.request.Request(source, headers={"User-Agent": "mona-vi-prose-qc/0.1"})
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read().decode(charset, errors="replace")
        return strip_html(raw)

    with open(source, encoding="utf-8") as f:
        raw = f.read()

    lower = source.lower()
    if lower.endswith(".html") or lower.endswith(".htm"):
        return strip_html(raw)
    if lower.endswith(".md") or lower.endswith(".markdown"):
        return strip_markdown(raw)
    return raw


def format_text_report(report, source: str) -> str:
    lines: list[str] = []
    status = "PASS" if not report.failed else "FAIL"
    lines.append(f"=== mona-vi-prose-qc — {source} ===")
    lines.append(f"Kết quả tổng: {status}")
    lines.append("")
    lines.append("-- Số liệu --")
    for key, value in report.stats.items():
        lines.append(f"  {key}: {value}")
    lines.append("")

    fails = [f for f in report.findings if f.level == "fail"]
    warnings = [f for f in report.findings if f.level == "warning"]

    lines.append(f"-- Lỗi (fail): {len(fails)} --")
    for f in fails:
        lines.append(f"  [FAIL] {f.rule}: {f.message}")
        if f.detail:
            lines.append(f"          → \"{f.detail}\"")
    if not fails:
        lines.append("  (không có)")

    lines.append("")
    lines.append(f"-- Cảnh báo (warning): {len(warnings)} --")
    for f in warnings:
        lines.append(f"  [WARN] {f.rule}: {f.message}")
        if f.detail:
            lines.append(f"          → \"{f.detail}\"")
    if not warnings:
        lines.append("  (không có)")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mona-vi-prose-qc",
        description="Kiểm nhịp văn tiếng Việt + phát hiện dấu hiệu văn AI trong bài viết.",
    )
    parser.add_argument("source", help="Đường dẫn file (.txt/.html/.md) hoặc URL cần kiểm tra")
    parser.add_argument("--json", action="store_true", help="Xuất kết quả dạng JSON")
    parser.add_argument(
        "--custom-cliches",
        metavar="PATH",
        help="File .txt chứa cụm cliché bổ sung, mỗi dòng 1 cụm",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Coi warning cũng là fail khi tính exit code",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = load_input(args.source)
    except (OSError, ValueError) as exc:
        print(f"Lỗi đọc nguồn '{args.source}': {exc}", file=sys.stderr)
        return 2

    custom_phrases: list[str] | None = None
    if args.custom_cliches:
        try:
            custom_phrases = load_custom_phrases(args.custom_cliches)
        except OSError as exc:
            print(f"Lỗi đọc file cliché tuỳ chỉnh '{args.custom_cliches}': {exc}", file=sys.stderr)
            return 2

    report = analyze(text, cfg=Config(), custom_cliches=custom_phrases)

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_text_report(report, args.source))

    if report.failed:
        return 1
    if args.fail_on_warning and any(f.level == "warning" for f in report.findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
