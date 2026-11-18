"""Tra cứu trước cho câu hỏi y khoa: model 7B thấy câu "phổ thông" (aspirin khi sốt xuất huyết, ăn uống khi tăng huyết áp)
thì trả lời bằng trí nhớ, không gọi medical_retrieval_tool → không nguồn, không kiểm chứng được (evaluation/run_agent:
3/9 kịch bản tool_use trượt). Service tự gọi tool trước rồi đưa kết quả vào hội thoại như một lượt gọi tool thật
(AIMessage có tool_call + ToolMessage) — _with_sources, guardrail tên lạ và evaluation đọc ToolMessage nên chạy như cũ.

Mặc định LUÔN tra cứu; chỉ bỏ qua những ý định chắc chắn không cần tài liệu y khoa. (Danh sách từ khoá y khoa thì
bỏ sót quá nhiều: 53/120 câu sức khoẻ thật trong evaluation/data/retrieval_synthetic.jsonl không chứa từ khoá nào.)
"""
import re
from langchain_core.messages import AIMessage, ToolMessage

_SMALLTALK = re.compile(r"^\W*(xin chào|chào|hi|hello|alo|cảm ơn|cám ơn|thanks|thank you|ok|oke|vâng|dạ|tạm biệt|"
                        r"bye|你好|谢谢|再见)\b", re.IGNORECASE)
# Đặt lịch/nhắc, ghi hồ sơ, hỏi chính hồ sơ của mình, yêu cầu ngoài phạm vi / về id nội bộ
_NOT_LOOKUP = re.compile(r"đặt lịch|lịch hẹn|lịch khám|lịch uống|lịch nhắc|vào lịch|nhắc (tôi|mình|nhở|bà|ông|bé|con)|"
                         r"hẹn (khám|tái khám)|tái khám ngày|ghi (vào|lại)|lưu (vào|lại)|hồ sơ|bệnh nền gì|"
                         r"đang dùng thuốc gì|document_id|member_id|chunk_id|\bcode\b|python|javascript|lập trình|"
                         r"预约|提醒我|病历|档案", re.IGNORECASE)
_PREFETCH_ID = "prefetch-medical-retrieval"


def needs_lookup(question: str) -> bool:
    q = question.strip()
    if len(q) < 6 or (_SMALLTALK.match(q) and len(q.split()) <= 6):
        return False
    return not _NOT_LOOKUP.search(q)


def prefetch_messages(question: str, result: str) -> list:
    """Cặp message giả lập lượt gọi medical_retrieval_tool(query=question) với kết quả `result`."""
    return [AIMessage(content="", tool_calls=[{"name": "medical_retrieval_tool", "args": {"query": question},
                                                "id": _PREFETCH_ID, "type": "tool_call"}]),
            ToolMessage(content=result, tool_call_id=_PREFETCH_ID, name="medical_retrieval_tool")]
