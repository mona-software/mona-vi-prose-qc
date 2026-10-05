# mona-vi-prose-qc

[![test](https://github.com/mona-software/mona-vi-prose-qc/actions/workflows/test.yml/badge.svg)](https://github.com/mona-software/mona-vi-prose-qc/actions/workflows/test.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Công cụ dòng lệnh (CLI) kiểm tra "nhịp văn" tiếng Việt và phát hiện những dấu hiệu cho thấy một đoạn văn bản nghe như do AI viết ra, thay vì do người viết tự nhiên.

## Vấn đề công cụ này giải quyết

Văn bản do các mô hình ngôn ngữ (ChatGPT, Gemini, Claude...) sinh ra thường có một số thói quen lặp đi lặp lại rất dễ nhận ra nếu để ý kỹ, dù từng câu đọc riêng lẻ vẫn "mượt". Ví dụ: đoạn nào cũng đúng hai câu, câu nào cũng dài xấp xỉ nhau, hay xuất hiện kiểu câu liệt kê tiến độ bằng dấu phẩy ("đã làm A, B đang chờ, C thì lỗi, D chưa xong"), thỉnh thoảng chèn một câu hỏi tu từ rồi tự trả lời ngay, và ưa dùng những cụm từ sáo rỗng kiểu dịch máy như "hành trình", "kỷ nguyên số", "mở khóa tiềm năng".

Khi biên tập viên đọc lướt một bài, tai mắt con người vẫn có thể bỏ sót những dấu hiệu này, đặc biệt với bài dài. `mona-vi-prose-qc` đọc toàn bộ văn bản, đo các chỉ số về nhịp câu/đoạn, rồi liệt kê chính xác vị trí và lý do nghi ngờ, để người biên tập quyết định sửa lại cho ra giọng người thật trước khi đăng.

## Dùng để làm gì

- Chạy QC nhanh trước khi đăng một bài viết (blog, landing page, tài liệu nội bộ) lên website.
- Tự động hoá bước kiểm tra này trong quy trình biên tập, nhờ mã thoát (exit code) 0 = đạt, 1 = có lỗi.
- Tích hợp vào các pipeline biên tập nội dung khác qua đầu ra JSON có cấu trúc.

Công cụ chỉ đọc và phân tích thống kê văn bản — không tự sửa bài, không gọi bất kỳ mô hình AI nào, chạy hoàn toàn offline (trừ trường hợp bạn đưa vào một URL để công cụ tự tải nội dung trang đó về kiểm tra).

## Cài đặt

Yêu cầu Python 3.10 trở lên. Không cần thư viện ngoài để chạy (`pytest` chỉ cần khi muốn tự chạy bộ test đi kèm repo).

```bash
git clone https://github.com/mona-software/mona-vi-prose-qc.git
cd mona-vi-prose-qc
pip install -e .
```

Sau khi cài, lệnh `mona-vi-prose-qc` sẽ có sẵn trong terminal.

## Cách dùng

```bash
mona-vi-prose-qc duong-dan-file.txt
mona-vi-prose-qc duong-dan-file.html
mona-vi-prose-qc duong-dan-file.md
mona-vi-prose-qc https://vi-du.com/mot-bai-viet
mona-vi-prose-qc duong-dan-file.txt --json
mona-vi-prose-qc duong-dan-file.txt --custom-cliches cum-tu-rieng.txt
```

File `.html` và `.md` sẽ được bóc tách về văn bản thuần trước khi phân tích (bỏ thẻ HTML, bỏ cú pháp Markdown), còn khi trỏ vào một URL thì công cụ tự tải trang về và làm điều tương tự.

### Ví dụ chạy thật

Giả sử có file `bai-mau.txt` với nội dung sau — cố tình trộn cả câu nhồi ý, cụm sáo rỗng lẫn một đoạn văn viết tự nhiên để minh hoạ:

```
Đây là một hành trình đầy hứa hẹn trong kỷ nguyên số, khi mọi doanh nghiệp đều muốn bứt phá.

Đã sửa lỗi đăng nhập, báo cáo đang chờ duyệt, hệ thống thanh toán còn lỗi, tài liệu thì chưa xong.

Buổi sáng hôm ấy trời se lạnh, và Lan vẫn ra khỏi nhà từ rất sớm để kịp chuyến xe buýt đầu tiên đến trường vì cô sợ trễ giờ kiểm tra môn toán. Cô ngồi cạnh cửa sổ nhìn phố xá dần đông người qua lại, mùi cà phê từ quán quen thoảng theo gió khiến cô tỉnh táo hẳn sau một đêm gần như thức trắng để ôn bài.

Dự án bị kẹt máy chủ, kẹt cơ sở dữ liệu, kẹt tên miền. Đội kỹ thuật đang xử lý từng phần một cách cẩn trọng và có kế hoạch rõ ràng cho từng đầu việc còn lại.
```

Chạy lệnh:

```bash
mona-vi-prose-qc bai-mau.txt
```

Kết quả in ra (đầu ra thật, chưa chỉnh sửa):

```
=== mona-vi-prose-qc — bai-mau.txt ===
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

Chú ý ba điều công cụ đã bắt đúng: (1) câu "Đã sửa lỗi đăng nhập, báo cáo đang chờ duyệt..." bị gắn cờ là câu nhồi ý bằng dấu phẩy — kiểu câu báo cáo tiến độ rất đặc trưng của văn AI; (2) ba cụm "hành trình", "đầy hứa hẹn", "kỷ nguyên" trong đoạn mở bài bị bắt là cụm sáo rỗng; (3) ngược lại, câu "Dự án bị kẹt máy chủ, kẹt cơ sở dữ liệu, kẹt tên miền" — vốn cũng có nhiều dấu phẩy — KHÔNG bị bắt nhầm, vì đây là kiểu liệt kê điệp từ hợp lệ ("kẹt... kẹt... kẹt..."), không phải nhồi ý.

Dùng `--json` khi cần đưa kết quả vào một pipeline khác:

```bash
mona-vi-prose-qc bai-mau.txt --json
```

sẽ in ra đúng cấu trúc trên nhưng ở dạng JSON, gồm `pass` (true/false), `stats` (toàn bộ số liệu đo được) và `findings` (danh sách từng lỗi/cảnh báo kèm mức độ `fail`/`warning`).

### Thêm cụm sáo rỗng của riêng bạn

Tạo một file `.txt`, mỗi dòng một cụm (không phân biệt hoa/thường, dòng bắt đầu bằng `#` sẽ bị bỏ qua):

```
đỉnh của chóp
không có đối thủ trên thị trường
```

Rồi chạy:

```bash
mona-vi-prose-qc bai-mau.txt --custom-cliches cum-tu-rieng.txt
```

### Mã thoát (exit code)

- `0`: bài đạt, không có lỗi `fail` nào.
- `1`: bài có ít nhất một lỗi `fail` (hoặc có cảnh báo, nếu chạy kèm `--fail-on-warning`).
- `2`: lỗi khi đọc file/URL đầu vào.

## Các mục được kiểm tra

1. Tỷ lệ đoạn văn đúng hai câu — quá nhiều là dấu hiệu viết đều tay kiểu máy.
2. Tỷ lệ đoạn văn đào sâu (từ bốn câu trở lên) — quá ít nghĩa là bài lướt qua ý mà không khai triển.
3. Độ lệch chuẩn độ dài câu (số từ/câu) toàn bài — văn tự nhiên có câu ngắn câu dài xen kẽ, văn máy thường đều đều.
4. Tỷ lệ câu rất dài và tỷ lệ câu rất ngắn.
5. Chuỗi từ ba câu ngắn liên tiếp trở lên trong cùng một đoạn — nhịp trống kiểu khẩu hiệu liên hoàn.
6. Chuỗi từ ba đoạn liên tiếp trở lên có cùng số câu — khuôn mẫu máy.
7. Câu nhồi nhiều ý bằng dấu phẩy kiểu điện tín báo cáo tiến độ (mục quan trọng nhất) — có loại trừ trường hợp liệt kê song song hợp lệ.
8. Câu hỏi tu từ giả tạo kiểu "Bạn có biết...?" rồi tự trả lời ngay.
9. Cụm từ và mẫu câu sáo rỗng tiếng Việt thường gặp trong văn dịch máy/AI.

Toàn bộ ngưỡng số ở trên nằm trong `src/mona_vi_prose_qc/metrics.py` (lớp `Config`) và có thể tinh chỉnh khi gọi thư viện trực tiếp bằng Python, thay vì chỉ dùng qua CLI.

## Dùng như thư viện Python

```python
from mona_vi_prose_qc.metrics import analyze, Config

report = analyze(noi_dung_bai_viet, cfg=Config(min_sentence_length_std=8))
print(report.to_dict())
```

## Chạy test

```bash
pip install -e ".[dev]"
pytest
```

## Giấy phép

MIT — xem file `LICENSE`.

---

## English (short version)

`mona-vi-prose-qc` is a Python CLI that checks the "prose rhythm" of Vietnamese text and flags patterns typical of AI-generated writing: uniform two-sentence paragraphs, low variance in sentence length, comma-spliced "status report" sentences that cram multiple unrelated actions into one sentence, fake rhetorical questions, and common Vietnamese AI-translation clichés. It accepts `.txt`/`.html`/`.md` files or a URL, and outputs a human-readable report or `--json`. Install with `pip install -e .`, run with `mona-vi-prose-qc <file-or-url>`. MIT licensed.

---
Từ MONA — https://mona.media · Các repo khác: https://github.com/mona-software · Hub mã nguồn mở: https://mona.media/mona-open/

**`mona-vi-prose-qc` là sản phẩm của MONA Software, thành viên The MONA Group.**
