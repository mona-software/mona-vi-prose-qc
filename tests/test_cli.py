import json
import subprocess
import sys
from pathlib import Path


def run_cli(args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "mona_vi_prose_qc.cli", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_cli_txt_file_json_output(tmp_path: Path):
    sample = tmp_path / "sample.txt"
    sample.write_text(
        "Đã sửa lỗi đăng nhập, báo cáo đang chờ duyệt, hệ thống thanh toán còn lỗi.\n\n"
        "Hôm nay trời đẹp.",
        encoding="utf-8",
    )
    result = run_cli([str(sample), "--json"])
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["pass"] is False
    assert any(f["rule"] == "comma_stuffed_sentence" for f in data["findings"])


def test_cli_html_input_is_stripped(tmp_path: Path):
    sample = tmp_path / "sample.html"
    sample.write_text(
        "<html><body><p>Buổi sáng hôm ấy trời se lạnh, và Lan vẫn ra khỏi nhà từ rất sớm "
        "để kịp chuyến xe buýt đầu tiên đến trường vì cô sợ trễ giờ.</p>"
        "<p>Cô ngồi cạnh cửa sổ. Ngoài kia phố xá dần đông người qua lại. "
        "Một vài quán ăn sáng đã bắt đầu dọn hàng, mùi cà phê thoảng theo gió khiến cô tỉnh táo hẳn.</p>"
        "</body></html>",
        encoding="utf-8",
    )
    result = run_cli([str(sample), "--json"])
    data = json.loads(result.stdout)
    assert data["stats"]["total_paragraphs"] == 2


def test_cli_exit_code_pass(tmp_path: Path):
    sample = tmp_path / "ok.txt"
    sample.write_text(
        "Buổi sáng hôm ấy trời se lạnh, và Lan vẫn ra khỏi nhà từ rất sớm để kịp chuyến "
        "xe buýt đầu tiên đến trường vì cô sợ trễ giờ kiểm tra môn toán.\n\n"
        "Cô ngồi cạnh cửa sổ. Ngoài kia phố xá dần đông người qua lại. Một vài quán ăn sáng "
        "đã bắt đầu dọn hàng, mùi cà phê thoảng theo gió khiến cô tỉnh táo hẳn sau một đêm "
        "gần như thức trắng để ôn bài cho kịp.\n\n"
        "Đến trường, Lan gặp Minh đang đứng đợi ở cổng. Hai người cùng nhau bước vào lớp, "
        "trò chuyện về đề cương ôn tập mà thầy giáo đã phát hôm trước, một bản đề cương dài "
        "đến mức khiến cả lớp phải thức khuya vài hôm liền mới đọc hết nổi.",
        encoding="utf-8",
    )
    result = run_cli([str(sample)])
    assert result.returncode == 0
    assert "PASS" in result.stdout
