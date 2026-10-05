# mona-vi-prose-qc

A command-line tool that measures sentence and paragraph rhythm in Vietnamese text and flags patterns common in machine-generated prose, for editors reviewing content before publishing.

[![test](https://github.com/mona-software/mona-vi-prose-qc/actions/workflows/test.yml/badge.svg)](https://github.com/mona-software/mona-vi-prose-qc/actions/workflows/test.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

The tool targets Vietnamese content; its cliché list and patterns are Vietnamese. It only analyzes text statistically: it does not edit the text and does not call any AI model. It runs offline unless you pass a URL.

## Install

Requires Python 3.10+. No third-party runtime dependencies.

```bash
git clone https://github.com/mona-software/mona-vi-prose-qc
cd mona-vi-prose-qc
pip install -e .
```

## Usage

```bash
mona-vi-prose-qc article.txt
mona-vi-prose-qc article.html
mona-vi-prose-qc article.md
mona-vi-prose-qc https://example.com/some-article
mona-vi-prose-qc article.txt --json
mona-vi-prose-qc article.txt --custom-cliches my-phrases.txt
```

`.html`/`.htm` and `.md`/`.markdown` files are converted to plain text first. A URL is downloaded and its HTML stripped (`script`, `style`, `head`, `nav` and `footer` are skipped). Any other file is read as plain text.

| Option | Description |
| --- | --- |
| `source` | File path (`.txt`, `.html`, `.md`) or URL |
| `--json` | Print the report as JSON |
| `--custom-cliches PATH` | Text file with extra phrases to flag, one per line; matching is case-insensitive and lines starting with `#` are ignored |
| `--fail-on-warning` | Exit with code 1 when there are warnings, not only failures |

Exit codes: `0` no failures, `1` at least one failure (or a warning with `--fail-on-warning`), `2` the input or custom phrase file could not be read.

### Example

`sample.txt`:

```
Đây là một hành trình đầy hứa hẹn trong kỷ nguyên số, khi mọi doanh nghiệp đều muốn bứt phá.

Đã sửa lỗi đăng nhập, báo cáo đang chờ duyệt, hệ thống thanh toán còn lỗi, tài liệu thì chưa xong.

Buổi sáng hôm ấy trời se lạnh, và Lan vẫn ra khỏi nhà từ rất sớm để kịp chuyến xe buýt đầu tiên đến trường vì cô sợ trễ giờ kiểm tra môn toán. Cô ngồi cạnh cửa sổ nhìn phố xá dần đông người qua lại, mùi cà phê từ quán quen thoảng theo gió khiến cô tỉnh táo hẳn sau một đêm gần như thức trắng để ôn bài.

Dự án bị kẹt máy chủ, kẹt cơ sở dữ liệu, kẹt tên miền. Đội kỹ thuật đang xử lý từng phần một cách cẩn trọng và có kế hoạch rõ ràng cho từng đầu việc còn lại.
```

```bash
mona-vi-prose-qc sample.txt
```

Output (messages are in Vietnamese):

```
=== mona-vi-prose-qc — sample.txt ===
Kết quả tổng: FAIL

-- Số liệu --
  total_paragraphs: 4
  total_sentences: 6
  two_sentence_paragraph_ratio: 0.5
  deep_paragraph_ratio: 0.0
  sentence_length_stdev: 8.04
  long_sentence_ratio: 0.333
  short_sentence_ratio: 0.0
  comma_stuffed_sentence_count: 1
  rhetorical_question_count: 0
  cliche_count: 3

-- Lỗi (fail): 3 --
  [FAIL] two_sentence_paragraph_ratio: 50% số đoạn đúng 2 câu (ngưỡng tối đa 35%) — nhịp đều tay kiểu văn AI.
  [FAIL] sentence_length_stdev: Độ lệch chuẩn độ dài câu = 8.0 (khuyến nghị tối thiểu 9.0) — câu dài/ngắn không so le, nhịp đều đều.
  [FAIL] comma_stuffed_sentence: Câu nhồi nhiều ý bằng dấu phẩy kiểu điện tín báo cáo tiến độ.
          → "Đã sửa lỗi đăng nhập, báo cáo đang chờ duyệt, hệ thống thanh toán còn lỗi, tài liệu thì chưa xong."

-- Cảnh báo (warning): 5 --
  [WARN] deep_paragraph_ratio: Chỉ 0% số đoạn có từ 4 câu trở lên (khuyến nghị tối thiểu 20%) — bài có thể thiếu đoạn đào sâu ý.
  [WARN] short_sentence_ratio: Chỉ 0% câu ngắn (<= 7 từ) — có thể thiếu điểm nhấn ngắn gọn.
  [WARN] cliche_phrase: Cụm sáo rỗng kiểu văn AI: "hành trình"
          → "hành trình"
  [WARN] cliche_phrase: Cụm sáo rỗng kiểu văn AI: "đầy hứa hẹn"
          → "đầy hứa hẹn"
  [WARN] cliche_phrase: Cụm sáo rỗng kiểu văn AI: "kỷ nguyên"
          → "kỷ nguyên"
```

The comma-separated status-report sentence in paragraph 2 is flagged, while the parallel list with a repeated word in paragraph 4 ("kẹt… kẹt… kẹt…") is not.

With `--json`, the report is an object with `pass` (boolean), `stats` (the metrics above) and `findings` (a list of `{rule, level, message, detail}`, where `level` is `fail` or `warning`).

## Checks

1. Share of paragraphs with exactly two sentences (fail above 35%).
2. Share of paragraphs with four or more sentences (warn below 20%).
3. Standard deviation of sentence length in words (fail below 9.0).
4. Share of long sentences (28+ words) and short sentences (7 words or fewer).
5. Runs of consecutive short sentences within a paragraph.
6. Runs of consecutive paragraphs with the same sentence count.
7. Sentences that pack several short clauses separated by commas, excluding parallel lists with a repeated word.
8. Rhetorical questions of the "Bạn có biết…?" type.
9. Vietnamese cliché phrases and patterns, plus any phrases from `--custom-cliches`.

Thresholds are defined in the `Config` dataclass in `src/mona_vi_prose_qc/metrics.py`.

## Library use

```python
from mona_vi_prose_qc.metrics import analyze, Config

report = analyze(article_text, cfg=Config(min_sentence_length_std=8))
print(report.to_dict())
```

`analyze()` also accepts `custom_cliches=[...]`.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT, see [LICENSE](LICENSE).

**`mona-vi-prose-qc` is a product of MONA Software, a member of The MONA Group.**
