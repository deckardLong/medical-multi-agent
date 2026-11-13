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
    return json.dumps(result, ensure_ascii=False)