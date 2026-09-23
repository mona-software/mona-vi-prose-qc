"""
Danh sách cụm sáo rỗng / cliché tiếng Việt kiểu "văn dịch từ AI" và các
mẫu regex hai-vế thường gặp trong văn bản do mô hình ngôn ngữ tạo ra.

Người dùng có thể bổ sung cụm riêng bằng cờ --custom-cliches (mỗi dòng 1 cụm,
so khớp không phân biệt hoa/thường, không dùng regex).
"""

from __future__ import annotations

import re

# Cụm cố định — so khớp dạng chuỗi con, không phân biệt hoa thường.
CLICHE_PHRASES: list[str] = [
    "hành trình",
    "bức tranh toàn cảnh",
    "chìa khóa thành công",
    "đòn bẩy",
    "tối ưu hóa trải nghiệm",
    "hãy cùng nhau",
    "trong thời đại số",
    "kỷ nguyên",
    "vô vàn",
    "đầy hứa hẹn",
    "một cách đáng kể",
    "nói không ngoa",
    "mở khóa tiềm năng",
    "điều hướng sự phức tạp",
    "tác động có ý nghĩa",
    "ở cấp độ cốt lõi",
    "trải nghiệm liền mạch",
    "thông qua việc",
    "tiến hành thực hiện",
    "đưa ra sự hỗ trợ",
    "cung cấp sự hỗ trợ",
    "không có nước lã",
    "không phải dạng vừa",
    "đáng gờm",
]

# Mẫu regex 2 vế cách nhau — case-insensitive, đặc trưng cho câu văn AI dịch.
CLICHE_PATTERNS: list[str] = [
    r"không chỉ[^.!?\n]{0,100}mà còn",
    r"(không những|không chỉ)[^.!?\n]{0,60}nhưng còn",
    r"đóng vai trò[^.!?\n]{0,35}trong việc",
    r"trong bối cảnh[^.!?\n]{0,60}(không ngừng|ngày càng) phát triển",
    r"(các chuyên gia|nhiều nghiên cứu|giới quan sát|nhiều nguồn) (cho rằng|chỉ ra|nhận định)",
    r"bởi vì[^.!?\n]{0,60}cho nên",
    r"\b(đồng thời|qua đó|từ đó)\b[^.!?\n]{0,80}\b(đồng thời|qua đó|từ đó)\b",
    r"(không|chẳng|đâu) (phải|nằm ở|ở)[^.!?\n]{0,90}(mà|thì) (là|ở|nằm|chính)",
    r"(chuyện|cái|thứ) mới (không phải|là)[^.!?\n]{0,60}(mà|—|-)",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in CLICHE_PATTERNS]


def load_custom_phrases(path: str) -> list[str]:
    """Đọc file cụm cliché tuỳ chỉnh, mỗi dòng 1 cụm, bỏ dòng trống/comment (#)."""
    phrases: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            phrases.append(line)
    return phrases


def find_cliches(text: str, extra_phrases: list[str] | None = None) -> list[dict]:
    """Trả về danh sách cliché tìm thấy trong văn bản: {"match", "kind", "start"}."""
    findings: list[dict] = []
    lowered = text.lower()

    all_phrases = list(CLICHE_PHRASES)
    if extra_phrases:
        all_phrases = all_phrases + list(extra_phrases)

    for phrase in all_phrases:
        needle = phrase.lower()
        start = 0
        while True:
            idx = lowered.find(needle, start)
            if idx == -1:
                break
            findings.append({"match": text[idx : idx + len(phrase)], "kind": "phrase", "start": idx})
            start = idx + len(needle)

    for pattern in _COMPILED_PATTERNS:
        for m in pattern.finditer(text):
            findings.append({"match": m.group(0), "kind": "pattern", "start": m.start()})

    findings.sort(key=lambda x: x["start"])
    return findings
