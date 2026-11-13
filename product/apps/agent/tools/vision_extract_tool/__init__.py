import asyncio
import json
from uuid import UUID
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from octochains import Engine
from product.db.session import SessionLocal
from product.db.models import Document
from ..context import member_id_from
from .agents.ocr_then_llm import OcrThenLlm
from .agents.vlm_direct import VlmDirect
from .agents.vlm_transcribe import VlmTranscribe
from .aggregate.aggregator import FieldConsensus
from .quality import check_image

def run_engine(path: str) -> dict:
    """Đồng bộ (Engine.run không có await trong README) → chỗ gọi async phải bọc asyncio.to_thread."""
    problem = check_image(path)
    if problem:
        return {"status": "rejected", "reason": problem}
    engine = Engine(agents=[VlmDirect(), OcrThenLlm(), VlmTranscribe()], aggregator=FieldConsensus())
    return json.loads(engine.run(path).consensus)

_FIELD_VI = {"prescriber": "Bác sĩ kê đơn", "issued_date": "Ngày kê", "facility": "Cơ sở y tế",
             "dose": "liều", "frequency": "tần suất", "duration": "thời gian dùng"}


def _val(v: dict) -> str:
    if v["status"] == "agree":
        return v["value"] if v["value"] is not None else "không ghi/không đọc được"
    opts = " | ".join(f'"{x}"' for x in v["values"]) or "không đọc được"
    return f"CẦN NGƯỜI DÙNG CHỌN: {opts}"


def render_summary(result: dict, for_user: bool = False) -> str:
    """Model nhỏ diễn giải JSON thô rồi tự chọn hộ người dùng → đưa sẵn bản tóm tắt đánh dấu rõ chỗ phải hỏi.
    for_user=True: bản hiển thị thẳng cho người dùng (không kèm hướng dẫn dành cho trợ lý)."""
    if result.get("status") == "rejected":
        return f"Ảnh không đạt chất lượng: {result['reason']}. Hãy đề nghị người dùng chụp lại."
    if result.get("status") == "insufficient":
        return "Không đọc được đơn thuốc (quá ít lần đọc thành công). Hãy đề nghị người dùng chụp lại rõ hơn."
    lines = [f"KẾT QUẢ ĐỌC ĐƠN — trạng thái: {result['status']} ({result['readers_ok']} lần đọc độc lập thành công)"]
    lines += [f"- {_FIELD_VI[k]}: {_val(v)}" for k, v in result["fields"].items()]
    sure = [m for m in result["medications"] if m["seen_by"] >= 2]
    unsure = [m for m in result["medications"] if m["seen_by"] < 2]
    for i, m in enumerate(sure, 1):
        lines.append(f"Thuốc {i}: tên {_val(m['name'])}; " +
                     "; ".join(f"{_FIELD_VI[f]} {_val(m[f])}" for f in ("dose", "frequency", "duration")))
    if unsure:
        names = ", ".join(f'"{n}"' for m in unsure
                          for n in (m["name"]["values"] if m["name"]["status"] != "agree" else [m["name"]["value"]]) if n)
        lines.append(f"CHƯA XÁC NHẬN — các lần đọc không khớp nhau, có thể đọc nhầm tên; liệt kê nguyên văn để người "
                     f"dùng đối chiếu với đơn gốc, không được coi là đã đọc đúng: {names}")
    if for_user:
        lines.append("Máy đọc chữ viết tay có thể sai: hãy đối chiếu từng dòng với đơn gốc, chọn giá trị đúng cho các "
                     "mục CẦN NGƯỜI DÙNG CHỌN, và hỏi lại bác sĩ/dược sĩ nếu không chắc.")
    else:
        lines.append("HƯỚNG DẪN CHO TRỢ LÝ: trình bày nguyên văn các giá trị trên; với mục CẦN NGƯỜI DÙNG CHỌN phải nêu "
                     "đủ các lựa chọn và hỏi người dùng, không tự chọn hay bình luận lựa chọn nào đúng; không suy diễn "
                     "cách dùng (uống, nhỏ mắt, ...) nếu đơn không ghi; nhắc người dùng đối chiếu với đơn gốc.")
    return "\n".join(lines)


@tool
async def vision_extract_tool(document_id: str, config: RunnableConfig) -> str:
    """Đọc ảnh đơn thuốc người dùng đã tải lên (theo document_id) bằng 3 lần đọc độc lập rồi đối chiếu.
    Kết quả KHÔNG tự lưu vào hồ sơ. Nếu status là needs_review: chỉ rõ cho người dùng những trường đang
    lệch và các giá trị đã đọc được, yêu cầu họ chọn hoặc tự nhập — tuyệt đối không tự chọn thay."""
    member_id = member_id_from(config)
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        return "document_id không hợp lệ."
    async with SessionLocal() as s:
        doc = await s.get(Document, doc_uuid)
        if doc is None or doc.member_id != member_id:   # không cho đọc tài liệu của thành viên khác
            return "Không tìm thấy tài liệu này trong hồ sơ của người dùng."
        result = await asyncio.to_thread(run_engine, doc.storage_path)
        doc.extracted_json = result
        await s.commit()
    return render_summary(result)