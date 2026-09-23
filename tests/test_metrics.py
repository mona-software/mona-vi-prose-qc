from mona_vi_prose_qc.metrics import Config, analyze, split_paragraphs, split_sentences, word_count


def rule_hit(report, rule_name: str) -> bool:
    return any(f.rule == rule_name for f in report.findings)


def test_split_paragraphs_basic():
    text = "Đoạn một.\n\nĐoạn hai có hai câu. Vẫn đoạn hai."
    paragraphs = split_paragraphs(text)
    assert len(paragraphs) == 2


def test_split_sentences_basic():
    sentences = split_sentences("Câu một. Câu hai! Câu ba?")
    assert sentences == ["Câu một.", "Câu hai!", "Câu ba?"]


def test_word_count():
    assert word_count("Đây là một câu năm từ") == 6


def test_comma_stuffed_sentence_is_caught():
    text = (
        "Đã sửa lỗi đăng nhập, báo cáo đang chờ duyệt, hệ thống thanh toán còn lỗi, "
        "tài liệu thì chưa xong.\n\n"
        "Hôm nay trời đẹp."
    )
    report = analyze(text)
    assert rule_hit(report, "comma_stuffed_sentence")
    assert report.failed


def test_parallel_repetition_not_flagged_as_stuffing():
    text = (
        "Dự án bị kẹt máy chủ, kẹt cơ sở dữ liệu, kẹt tên miền.\n\n"
        "Đội kỹ thuật đang tìm cách xử lý từng phần một cách cẩn trọng và có kế hoạch rõ ràng."
    )
    report = analyze(text)
    assert not rule_hit(report, "comma_stuffed_sentence")


def test_uniform_short_paragraphs_flagged_as_ai_like():
    text = "\n\n".join(
        [f"Câu số {i} rất ngắn. Câu tiếp theo cũng ngắn." for i in range(1, 8)]
    )
    report = analyze(text)
    assert rule_hit(report, "two_sentence_paragraph_ratio")
    assert report.failed


def test_natural_varied_prose_passes():
    text = (
        "Buổi sáng hôm ấy trời se lạnh, và Lan vẫn ra khỏi nhà từ rất sớm để kịp chuyến "
        "xe buýt đầu tiên đến trường vì cô sợ trễ giờ kiểm tra môn toán.\n\n"
        "Cô ngồi cạnh cửa sổ. Ngoài kia phố xá dần đông người qua lại. Một vài quán ăn sáng "
        "đã bắt đầu dọn hàng, mùi cà phê thoảng theo gió khiến cô tỉnh táo hẳn sau một đêm "
        "gần như thức trắng để ôn bài cho kịp.\n\n"
        "Đến trường, Lan gặp Minh đang đứng đợi ở cổng. Hai người cùng nhau bước vào lớp, "
        "trò chuyện về đề cương ôn tập mà thầy giáo đã phát hôm trước, một bản đề cương dài "
        "đến mức khiến cả lớp phải thức khuya vài hôm liền mới đọc hết nổi."
    )
    report = analyze(text)
    assert not rule_hit(report, "comma_stuffed_sentence")
    assert not rule_hit(report, "two_sentence_paragraph_ratio")


def test_cliche_phrase_detected():
    text = (
        "Đây là một hành trình đầy hứa hẹn cho mọi doanh nghiệp muốn bứt phá trong kỷ nguyên số.\n\n"
        "Chúng tôi tin rằng mỗi bước đi đều cần một chiến lược rõ ràng và một đội ngũ đủ mạnh."
    )
    report = analyze(text)
    assert rule_hit(report, "cliche_phrase")


def test_custom_cliche_list():
    text = "Sản phẩm này thật sự đỉnh của chóp và không có đối thủ trên thị trường hiện nay.\n\nCòn nhiều việc phải làm."
    report_without = analyze(text)
    assert not rule_hit(report_without, "cliche_phrase")

    report_with = analyze(text, custom_cliches=["đỉnh của chóp"])
    assert rule_hit(report_with, "cliche_phrase")


def test_rhetorical_question_flagged():
    text = (
        "Bạn có biết vì sao doanh nghiệp của bạn chưa tăng trưởng như mong đợi?\n\n"
        "Câu trả lời nằm ở cách vận hành đội ngũ bán hàng mỗi ngày."
    )
    report = analyze(text)
    assert rule_hit(report, "rhetorical_question")


def test_consecutive_equal_length_paragraphs_flagged():
    text = "\n\n".join(
        [
            "Câu một dài hơn bình thường một chút để không trùng nhịp. Câu hai tiếp nối ý đó. Câu ba khép lại đoạn.",
            "Đoạn tiếp theo cũng có ba câu đúng như vậy để thử nghiệm. Câu giữa bổ sung chi tiết. Câu cuối chốt đoạn.",
            "Đoạn thứ ba lại tiếp tục giữ nguyên cấu trúc ba câu này. Câu giữa vẫn vậy. Câu cuối vẫn vậy.",
        ]
    )
    report = analyze(text)
    assert rule_hit(report, "consecutive_equal_length_paragraphs")


def test_config_thresholds_are_adjustable():
    cfg = Config(min_sentence_length_std=0.0)
    text = "Câu ngắn đều. Câu ngắn đều. Câu ngắn đều nữa.\n\nĐoạn hai cũng câu ngắn đều. Vẫn ngắn đều."
    report = analyze(text, cfg=cfg)
    assert not rule_hit(report, "sentence_length_stdev")
