"""
Các phép đo nhịp văn tiếng Việt + phát hiện dấu hiệu "văn AI".

Toàn bộ ngưỡng số ở đây là ngưỡng KHỞI ĐIỂM tổng quát, rút ra từ quan sát
thực tế trên văn bản tiếng Việt tự nhiên so với văn bản do mô hình ngôn ngữ
sinh ra. Có thể chỉnh qua tham số của Config khi gọi thư viện, hoặc để mặc
định khi dùng CLI.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

from .cliches_vi import find_cliches

# --- Từ vựng dùng cho phát hiện câu nhồi ý bằng dấu phẩy ---------------------

ACTION_MARKERS = [
    "đã", "đang", "còn", "xong", "lỗi", "sửa", "chạy", "gửi", "xoá", "xóa",
    "thêm", "đổi", "hoãn", "chờ", "duyệt", "bắt đầu", "kết thúc", "hoàn thành",
    "cập nhật", "kiểm tra", "triển khai", "huỷ", "hủy", "dừng", "tắt", "bật",
    "nộp", "ký", "duyệt", "phê duyệt", "trả", "nhận", "báo", "thông báo",
    "kẹt", "vướng", "chậm", "trễ", "thiếu", "đủ", "xong xuôi", "rớt", "treo",
]

LEADING_CONJUNCTIONS = {
    "hoặc", "thì", "nên", "mà", "nhưng", "rồi", "và", "còn", "để", "vì",
    "nếu", "khi", "do", "bởi", "tuy", "dù", "mặc", "song", "vậy", "nhằm",
}

RHETORICAL_STARTS = [
    r"^bạn có biết",
    r"^bạn có bao giờ",
    r"^có bao giờ (bạn|anh|chị)",
    r"^điều gì (làm nên|khiến|tạo nên)",
    r"^tại sao",
    r"^vì sao",
    r"^làm (thế nào|sao) để",
    r"^điều gì (sẽ )?xảy ra (nếu|khi)",
]
_RHETORICAL_RE = [re.compile(p, re.IGNORECASE) for p in RHETORICAL_STARTS]


@dataclass
class Config:
    """Ngưỡng kiểm tra — có thể tinh chỉnh cho phù hợp thể loại văn bản."""

    max_two_sentence_paragraph_ratio: float = 0.35
    min_deep_paragraph_ratio: float = 0.20  # đoạn >=4 câu
    deep_paragraph_min_sentences: int = 4
    min_sentence_length_std: float = 9.0
    min_long_sentence_ratio: float = 0.08
    long_sentence_word_count: int = 28
    short_sentence_word_count: int = 7
    min_short_sentence_ratio: float = 0.05
    max_short_sentence_ratio: float = 0.14
    max_consecutive_short_sentences: int = 3
    max_consecutive_equal_length_paragraphs: int = 3
    comma_stuffing_min_clauses: int = 3
    comma_stuffing_max_clause_words: int = 8


@dataclass
class Finding:
    rule: str
    level: str  # "fail" | "warning"
    message: str
    detail: str = ""


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def failed(self) -> bool:
        return any(f.level == "fail" for f in self.findings)

    def to_dict(self) -> dict:
        return {
            "pass": not self.failed,
            "stats": self.stats,
            "findings": [
                {"rule": f.rule, "level": f.level, "message": f.message, "detail": f.detail}
                for f in self.findings
            ],
        }


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_paragraphs(text: str) -> list[str]:
    """Tách văn bản thành đoạn theo dòng trống."""
    raw = re.split(r"\n\s*\n+", text.strip())
    return [p.strip() for p in raw if p.strip()]


def split_sentences(paragraph: str) -> list[str]:
    """Tách đoạn thành câu theo dấu . ! ?"""
    flat = re.sub(r"\s+", " ", paragraph.strip())
    if not flat:
        return []
    parts = _SENTENCE_SPLIT_RE.split(flat)
    sentences = [s.strip() for s in parts if s.strip()]
    return sentences


def word_count(sentence: str) -> int:
    words = re.findall(r"\S+", sentence)
    return len(words)


def _detect_comma_stuffing(sentence: str, cfg: Config) -> dict | None:
    parts = [p.strip() for p in re.split(r"[,;]", sentence) if p.strip()]
    if len(parts) < cfg.comma_stuffing_min_clauses:
        return None

    first_words = [p.split()[0].lower() if p.split() else "" for p in parts]
    # Liệt kê song song điệp từ đầu vế (VD "kẹt máy chủ, kẹt cơ sở dữ liệu,
    # kẹt tên miền") không phải nhồi ý — loại trừ. Chấp nhận cả trường hợp
    # vế đầu có thêm chủ ngữ (VD "Dự án bị kẹt máy chủ, kẹt CSDL, kẹt tên
    # miền") bằng cách xét từ lặp nhiều nhất trên toàn bộ các vế.
    non_empty_first_words = [w for w in first_words if w]
    if non_empty_first_words:
        most_common_count = max(non_empty_first_words.count(w) for w in set(non_empty_first_words))
        if most_common_count >= max(2, len(parts) - 1):
            return None

    qualifying = []
    for p in parts:
        words = p.split()
        if not words:
            continue
        first = words[0].lower().strip(",.;")
        has_action_marker = any(marker in p.lower() for marker in ACTION_MARKERS)
        starts_with_conjunction = first in LEADING_CONJUNCTIONS
        short_enough = len(words) <= cfg.comma_stuffing_max_clause_words
        if short_enough and has_action_marker and not starts_with_conjunction:
            qualifying.append(p)

    if len(qualifying) >= cfg.comma_stuffing_min_clauses:
        return {"sentence": sentence, "clauses": qualifying}
    return None


def _detect_rhetorical_question(sentence: str) -> bool:
    flat = sentence.strip().lower()
    if not flat.endswith("?"):
        return False
    return any(p.match(flat) for p in _RHETORICAL_RE)


def analyze(text: str, cfg: Config | None = None, custom_cliches: list[str] | None = None) -> Report:
    cfg = cfg or Config()
    report = Report()

    paragraphs = split_paragraphs(text)
    if not paragraphs:
        report.findings.append(
            Finding("empty_input", "fail", "Văn bản rỗng hoặc không tách được đoạn nào.")
        )
        return report

    per_paragraph_sentences: list[list[str]] = [split_sentences(p) for p in paragraphs]
    per_paragraph_sentence_count = [len(s) for s in per_paragraph_sentences]

    all_sentences: list[str] = [s for sents in per_paragraph_sentences for s in sents]
    all_word_counts = [word_count(s) for s in all_sentences]

    total_paragraphs = len(paragraphs)
    total_sentences = len(all_sentences)

    report.stats["total_paragraphs"] = total_paragraphs
    report.stats["total_sentences"] = total_sentences

    if total_sentences == 0:
        report.findings.append(
            Finding("empty_sentences", "fail", "Không tách được câu nào trong văn bản.")
        )
        return report

    # 1-2. Tỷ lệ đoạn đúng 2 câu / đoạn đào sâu (>=4 câu)
    two_sentence_paragraphs = sum(1 for c in per_paragraph_sentence_count if c == 2)
    deep_paragraphs = sum(1 for c in per_paragraph_sentence_count if c >= cfg.deep_paragraph_min_sentences)
    two_ratio = two_sentence_paragraphs / total_paragraphs
    deep_ratio = deep_paragraphs / total_paragraphs

    report.stats["two_sentence_paragraph_ratio"] = round(two_ratio, 3)
    report.stats["deep_paragraph_ratio"] = round(deep_ratio, 3)

    if two_ratio > cfg.max_two_sentence_paragraph_ratio:
        report.findings.append(
            Finding(
                "two_sentence_paragraph_ratio",
                "fail",
                f"{two_ratio:.0%} số đoạn đúng 2 câu (ngưỡng tối đa {cfg.max_two_sentence_paragraph_ratio:.0%}) — nhịp đều tay kiểu văn AI.",
            )
        )

    if total_paragraphs >= 3 and deep_ratio < cfg.min_deep_paragraph_ratio:
        report.findings.append(
            Finding(
                "deep_paragraph_ratio",
                "warning",
                f"Chỉ {deep_ratio:.0%} số đoạn có từ {cfg.deep_paragraph_min_sentences} câu trở lên (khuyến nghị tối thiểu {cfg.min_deep_paragraph_ratio:.0%}) — bài có thể thiếu đoạn đào sâu ý.",
            )
        )

    # 3. Độ lệch chuẩn độ dài câu
    if total_sentences >= 2:
        std_len = statistics.pstdev(all_word_counts)
    else:
        std_len = 0.0
    report.stats["sentence_length_stdev"] = round(std_len, 2)

    if std_len < cfg.min_sentence_length_std:
        report.findings.append(
            Finding(
                "sentence_length_stdev",
                "fail",
                f"Độ lệch chuẩn độ dài câu = {std_len:.1f} (khuyến nghị tối thiểu {cfg.min_sentence_length_std}) — câu dài/ngắn không so le, nhịp đều đều.",
            )
        )

    # 4. Tỷ lệ câu rất dài / rất ngắn
    long_count = sum(1 for w in all_word_counts if w >= cfg.long_sentence_word_count)
    short_count = sum(1 for w in all_word_counts if w <= cfg.short_sentence_word_count)
    long_ratio = long_count / total_sentences
    short_ratio = short_count / total_sentences

    report.stats["long_sentence_ratio"] = round(long_ratio, 3)
    report.stats["short_sentence_ratio"] = round(short_ratio, 3)

    if long_ratio < cfg.min_long_sentence_ratio:
        report.findings.append(
            Finding(
                "long_sentence_ratio",
                "warning",
                f"Chỉ {long_ratio:.0%} câu dài (>= {cfg.long_sentence_word_count} từ), khuyến nghị tối thiểu {cfg.min_long_sentence_ratio:.0%}.",
            )
        )

    if short_ratio < cfg.min_short_sentence_ratio:
        report.findings.append(
            Finding(
                "short_sentence_ratio",
                "warning",
                f"Chỉ {short_ratio:.0%} câu ngắn (<= {cfg.short_sentence_word_count} từ) — có thể thiếu điểm nhấn ngắn gọn.",
            )
        )
    elif short_ratio > cfg.max_short_sentence_ratio:
        report.findings.append(
            Finding(
                "short_sentence_ratio",
                "warning",
                f"{short_ratio:.0%} câu ngắn (<= {cfg.short_sentence_word_count} từ), vượt ngưỡng {cfg.max_short_sentence_ratio:.0%} — có thể rời rạc kiểu khẩu hiệu.",
            )
        )

    # 5. Chuỗi >=3 câu ngắn liên tiếp trong cùng 1 đoạn
    for p_idx, sentences in enumerate(per_paragraph_sentences, start=1):
        streak = 0
        for s in sentences:
            if word_count(s) <= cfg.short_sentence_word_count:
                streak += 1
                if streak >= cfg.max_consecutive_short_sentences:
                    report.findings.append(
                        Finding(
                            "consecutive_short_sentences",
                            "fail",
                            f"Đoạn {p_idx} có chuỗi >= {cfg.max_consecutive_short_sentences} câu ngắn liên tiếp — nhịp trống kiểu khẩu hiệu liên hoàn.",
                        )
                    )
                    break
            else:
                streak = 0

    # 6. Chuỗi đoạn liên tiếp có cùng số câu
    streak = 1
    for i in range(1, len(per_paragraph_sentence_count)):
        if (
            per_paragraph_sentence_count[i] == per_paragraph_sentence_count[i - 1]
            and per_paragraph_sentence_count[i] > 0
        ):
            streak += 1
        else:
            streak = 1
        if streak >= cfg.max_consecutive_equal_length_paragraphs:
            report.findings.append(
                Finding(
                    "consecutive_equal_length_paragraphs",
                    "fail",
                    f"Có >= {cfg.max_consecutive_equal_length_paragraphs} đoạn liên tiếp cùng đúng {per_paragraph_sentence_count[i]} câu (kết thúc ở đoạn {i + 1}) — khuôn mẫu máy.",
                )
            )
            streak = 1  # tránh báo trùng lặp chồng chéo

    # 7. Câu nhồi ý bằng dấu phẩy
    stuffed = []
    for s in all_sentences:
        hit = _detect_comma_stuffing(s, cfg)
        if hit:
            stuffed.append(hit)

    report.stats["comma_stuffed_sentence_count"] = len(stuffed)
    for hit in stuffed:
        report.findings.append(
            Finding(
                "comma_stuffed_sentence",
                "fail",
                "Câu nhồi nhiều ý bằng dấu phẩy kiểu điện tín báo cáo tiến độ.",
                detail=hit["sentence"],
            )
        )

    # 9. Câu hỏi tu từ giả tạo
    rhetorical_hits = [s for s in all_sentences if _detect_rhetorical_question(s)]
    report.stats["rhetorical_question_count"] = len(rhetorical_hits)
    for s in rhetorical_hits:
        report.findings.append(
            Finding(
                "rhetorical_question",
                "warning",
                "Câu hỏi tu từ giả tạo rồi tự trả lời — mòn kiểu văn AI.",
                detail=s,
            )
        )

    # 10. Cụm sáo rỗng / cliché
    cliche_hits = find_cliches(text, extra_phrases=custom_cliches)
    report.stats["cliche_count"] = len(cliche_hits)
    for hit in cliche_hits:
        report.findings.append(
            Finding(
                "cliche_phrase",
                "warning",
                f"Cụm sáo rỗng kiểu văn AI: \"{hit['match']}\"",
                detail=hit["match"],
            )
        )

    return report
