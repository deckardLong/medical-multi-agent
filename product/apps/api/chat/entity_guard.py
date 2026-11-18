"""Guardrail tên lạ: model 7B gặp tên thuốc/bệnh nó không biết thì hay gán bừa vào một thứ có thật na ná tên
("Brontaxel (docetaxel)…", "Orvalin (tên khoa học là Testosterone)…") rồi đưa liều dùng cụ thể — nguy hiểm vì trông đáng
tin. Prompt không chặn được (đo bằng evaluation/run_generation: 6/8 tên hư cấu bị bịa), nên kiểm tra bằng code:

  tên riêng trong câu hỏi → phải xuất hiện NGUYÊN VĂN trong kết quả tool của lượt này / hồ sơ / đơn đính kèm,
  hoặc trong kho tài liệu (tự tra lại, không phụ thuộc model có gọi tool hay không)
  → nếu không, và câu trả lời có nói về tên đó → thay bằng câu trả lời an toàn cố định.
"""
import re
import unicodedata

# Tên Latin viết hoa (cho phép nối gạch: Kessler-Varn, Delmont-Ashby). Viết toàn hoa (HIV, COVID) là viết tắt → bỏ qua.
_LATIN_NAME = re.compile(r"(?<![\w-])([A-Z][a-z]{2,}(?:-[A-Z][a-z]+)*)(?![\w-])")
# Một âm tiết tiếng Việt gõ không dấu ("Thuoc", "Trong", "Nghieng"): không phải tên riêng cần xác minh
_VI_SYLLABLE = re.compile(r"^(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdghklmnpqrstvx])?"
                          r"[aeiouy]{1,3}(ch|ng|nh|[cmnpt])?$", re.IGNORECASE)
# Tên tiếng Trung: cụm chữ Hán đứng ngay trước hậu tố dạng bào chế / loại bệnh
_CJK_NAME = re.compile(r"([一-鿿]{2,8}?)(片|胶囊|注射液|颗粒|口服液|软膏|滴眼液|糖浆|综合征|综合症)")
# Tên riêng không phải thuốc/bệnh hay gặp trong câu hỏi
_COMMON = {"google", "facebook", "zalo", "youtube", "tiktok", "covid", "aurelia", "vitamin", "omega"}


def _plain(s: str) -> str:
    return unicodedata.normalize("NFC", s).casefold()


def candidate_names(question: str) -> list[str]:
    """Tên riêng trông như tên thuốc/bệnh/xét nghiệm trong câu hỏi (có thể rỗng)."""
    names = []
    for m in _LATIN_NAME.finditer(question):
        w = m.group(1)
        if w.casefold() in _COMMON or all(_VI_SYLLABLE.match(p) for p in w.split("-")):
            continue
        names.append(w)
    names += [m.group(1) for m in _CJK_NAME.finditer(question)]
    return list(dict.fromkeys(names))


def unverified_names(question: str, reply: str, known_text: str, corpus_mentions) -> list[str]:
    """Tên trong câu hỏi mà câu trả lời có nói tới nhưng không có nguồn nào xác nhận.
    known_text: kết quả tool + hồ sơ + đơn đính kèm của lượt này. corpus_mentions(term) -> bool: tra kho tài liệu."""
    known, answered = _plain(known_text), _plain(reply)
    out = []
    for name in candidate_names(question):
        n = _plain(name)
        if n in known or n not in answered:   # đã có nguồn, hoặc câu trả lời không nói về nó (đã tự từ chối)
            continue
        if not corpus_mentions(name):
            out.append(name)
    return out


def safe_reply(names: list[str], question: str = "") -> str:
    quoted = ", ".join(f"“{n}”" for n in names)
    if re.search(r"[一-鿿]", question) and not re.search(r"[À-ỹ]", question):   # hỏi bằng tiếng Trung
        return (f"我在医学资料库和检索结果中没有找到关于{quoted}的可靠信息，因此不会猜测其用途、剂量或特征——"
                "猜错医学信息可能造成伤害。\n\n"
                "- 请核对名称拼写，或药盒/处方上印的名称（商品名通常附有成分名）。\n"
                "- 如果是医生开的药，请在使用前咨询药师或开药的医生。\n"
                "- 您也可以发送药盒或处方的照片，我帮您识别。")
    return (f"Tôi không tìm thấy thông tin đáng tin cậy nào về {quoted} trong kho tài liệu y khoa và kết quả tra cứu, "
            "nên sẽ không đoán công dụng, liều dùng hay đặc điểm của nó — đoán sai thông tin y khoa có thể gây hại.\n\n"
            "- Bạn kiểm tra lại chính tả, hoặc tên in trên vỏ hộp / đơn thuốc (tên biệt dược thường kèm tên hoạt chất).\n"
            "- Nếu đây là thuốc được kê, hãy hỏi dược sĩ hoặc bác sĩ kê đơn trước khi dùng.\n"
            "- Bạn có thể gửi ảnh vỏ hộp hoặc đơn thuốc để tôi đọc giúp.")
