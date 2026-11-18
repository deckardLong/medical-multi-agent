"""Guardrail liều thuốc cho trẻ em: model 7B được hỏi liều cho trẻ thì đưa "10–15 mg/kg", đề nghị "ước lượng theo tuổi"
hoặc "liều chung theo cân nặng trung bình" — sai một chút ở trẻ nhỏ là quá liều (đo bằng evaluation/run_agent:
3/4 kịch bản pediatric_dose trượt). Prompt không chặn được, nên chặn bằng code:

  người được hỏi là trẻ < 12 tuổi (theo ngày sinh trong hồ sơ, hoặc câu hỏi nói rõ "bé 4 tuổi", "con 18 tháng")
  VÀ câu hỏi hỏi về liều / lượng dùng → thay câu trả lời bằng hướng dẫn cố định, không có con số liều nào.
"""
import re

CHILD_MAX_AGE = 12

_DOSE_Q = re.compile(
    r"liều|bao nhiêu\s*(ml|mg|viên|gói|giọt|thìa|muỗng|cc|lần)|mấy\s*(ml|mg|viên|gói|giọt|thìa|muỗng|cc|lần)|"
    r"uống\s*bao nhiêu|dùng\s*bao nhiêu|cho\s*(bé|con|cháu|trẻ)?\s*uống\s*(mấy|bao)|"
    r"剂量|用量|吃几|吃多少|喝多少|多少毫升|多少毫克|几片|几包|几毫升", re.IGNORECASE)
_CHILD_WORD = r"(bé|con|cháu|trẻ|em bé|宝宝|孩子|小孩|儿童)"
_AGE_YEARS = re.compile(_CHILD_WORD + r"[^.?!\n]{0,20}?(\d{1,2})\s*(tuổi|岁)", re.IGNORECASE)
_AGE_MONTHS = re.compile(r"(\d{1,2})\s*(tháng tuổi|tháng|个月)", re.IGNORECASE)
_ANTIBIOTIC = re.compile(r"kháng sinh|\w*(cillin|cilin|mycin|micin|cef\w+|floxacin|cycline)\b|"
                         r"amoxi\w*|augmentin|抗生素|阿莫西林|头孢", re.IGNORECASE)


def child_age_in_question(question: str) -> float | None:
    """Tuổi trẻ được nhắc trong câu hỏi ("bé nhà tôi 4 tuổi", "con 18 tháng"), None nếu không có."""
    if m := _AGE_YEARS.search(question):
        return float(m.group(2))
    if re.search(_CHILD_WORD, question, re.IGNORECASE) and (m := _AGE_MONTHS.search(question)):
        return int(m.group(1)) / 12
    return None


def is_pediatric_dose_question(question: str, member_age: float | None) -> bool:
    if not _DOSE_Q.search(question):
        return False
    age = child_age_in_question(question)
    if age is None:
        age = member_age
    return age is not None and age < CHILD_MAX_AGE


def safe_reply(question: str) -> str:
    antibiotic = bool(_ANTIBIOTIC.search(question))
    if re.search(r"[一-鿿]", question) and not re.search(r"[À-ỹ]", question):
        lines = ["儿童用药剂量必须根据孩子的**实际体重**和具体药品（浓度、剂型）计算，我不提供具体剂量——"
                 "对幼儿来说，稍有偏差就可能过量。",
                 "- 请按药盒说明书中按体重/年龄的剂量表使用，或直接询问药师、儿科医生。"]
        if antibiotic:
            lines.append("- **不要自行给孩子使用抗生素**：抗生素需要医生诊断后开具，咳嗽、发烧多数由病毒引起，抗生素无效。")
        lines.append("- 如孩子出现呼吸困难、嗜睡难唤醒、抽搐、持续高烧不退、拒绝喝水或尿量明显减少，请立即就医。")
        return "\n".join(lines)
    lines = ["Liều thuốc cho trẻ phải tính theo **cân nặng thực tế** của bé và đúng loại thuốc đang có (nồng độ, dạng "
             "siro/gói/viên), nên tôi sẽ không đưa ra con số liều — với trẻ nhỏ, lệch một chút là có thể quá liều.",
             "- Dùng đúng bảng liều theo cân nặng/tuổi in trên tờ hướng dẫn trong hộp thuốc, hoặc hỏi dược sĩ / "
             "bác sĩ nhi trước khi cho bé uống.",
             "- Dùng dụng cụ đong đi kèm hộp thuốc, không dùng thìa ăn cơm; không cho uống 2 loại thuốc hạ sốt cùng lúc "
             "nếu bác sĩ không chỉ định."]
    if antibiotic:
        lines.append("- **Không tự mua kháng sinh cho bé**: kháng sinh cần bác sĩ khám và kê đơn; ho, sốt ở trẻ phần lớn "
                     "do virus và kháng sinh không có tác dụng, dùng sai còn gây kháng thuốc.")
    lines.append("- Đưa bé đi khám ngay nếu: khó thở, li bì khó đánh thức, co giật, sốt cao không hạ sau khi dùng thuốc, "
                 "bỏ bú/không chịu uống nước hoặc tiểu ít hẳn đi.")
    return "\n".join(lines)
