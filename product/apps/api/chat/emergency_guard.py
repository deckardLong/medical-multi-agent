"""Guardrail cấp cứu: prompt yêu cầu khuyên gọi 115 "trước mọi thông tin khác" nhưng model 7B không ổn định — gặp tài
liệu tra cứu lạc đề (sởi, vắc xin) thì chỉ khuyên "đưa bé đến cơ sở y tế gần nhất" cho một bé đang tím môi, thở rít
(evaluation/run_agent: emerg-child-breath). Dấu hiệu đe doạ tính mạng → code gắn khối cảnh báo lên ĐẦU câu trả lời,
model viết gì thì vẫn có; và không tra cứu trước (prefetch) để model không bị tài liệu lạc đề kéo đi, trả lời nhanh hơn.
"""
import re

_PHYSICAL = re.compile(
    r"tím (môi|tái)|môi tím|thở rít|khó thở (dữ dội|nặng|nhiều)|không thở được|ngừng thở|ngạt thở|hóc|"
    r"đau (thắt )?ngực (dữ dội|lan)|đau thắt ngực|méo miệng|nói ngọng|yếu (nửa người|liệt)|liệt nửa người|"
    r"co giật|bất tỉnh|ngất|hôn mê|li bì|lơ mơ|khó đánh thức|"
    r"(máu|chảy máu)[^.?!\n]{0,20}(không cầm|nhiều|ồ ạt)|nôn ra máu|đi ngoài ra máu|"
    r"uống nhầm|(bị|nghi|đang) ngộ độc|bỏng (nặng|rộng)|điện giật|đuối nước|sốc phản vệ|phù (môi|họng|mặt)|"
    r"呼吸困难|嘴唇发紫|胸痛|昏迷|抽搐|大出血|中毒|口角歪斜", re.IGNORECASE)
_SELF_HARM = re.compile(r"tự tử|tự sát|tự hại|muốn chết|không muốn sống|sống không còn ý nghĩa|kết liễu|"
                        r"tự làm đau bản thân|rạch tay|自杀|不想活|轻生", re.IGNORECASE)


def emergency_kind(question: str) -> str | None:
    if _SELF_HARM.search(question):
        return "self_harm"
    if _PHYSICAL.search(question):
        return "physical"
    return None


def banner(kind: str, question: str) -> str:
    zh = bool(re.search(r"[一-鿿]", question)) and not re.search(r"[À-ỹ]", question)
    if kind == "self_harm":
        if zh:
            return ("**你并不孤单。** 如果你此刻有伤害自己的念头，请立即告诉身边信任的人，或前往最近的医院急诊；"
                    "若有紧急危险，请拨打急救电话 115。心理医生和专业人士可以帮助你度过这段时间。")
        return ("**Bạn không một mình.** Nếu lúc này bạn đang có ý định làm hại bản thân, hãy nói ngay với một người thân "
                "hoặc người bạn tin tưởng đang ở gần, hoặc tới khoa cấp cứu của bệnh viện gần nhất; nếu đang nguy hiểm, "
                "gọi **115**. Bác sĩ và chuyên gia tâm lý có thể giúp bạn vượt qua giai đoạn này.")
    if zh:
        return ("**⚠ 这可能是危及生命的紧急情况：请立即拨打 115 或马上前往最近的医院急诊，不要在家观察等待。**")
    return ("**⚠ Đây có thể là tình huống CẤP CỨU: gọi 115 hoặc đưa tới khoa cấp cứu gần nhất NGAY, "
            "không tự theo dõi ở nhà.** Thông tin dưới đây chỉ để xử trí trong lúc chờ.")


def with_banner(reply: str, kind: str | None, question: str) -> str:
    if kind is None:
        return reply
    return f"{banner(kind, question)}\n\n{reply}"
