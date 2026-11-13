import threading
from octochains import Agent
from product.apps.agent.llm import get_llm
from ..prompts import STRUCTURE_FROM_TEXT
from ..schema import parse_extract, to_report

_ocr = None
_lock = threading.Lock()

def _ocr_lines(path: str) -> list[str]:
    global _ocr
    with _lock:
        if _ocr is None:
            from paddleocr import PaddleOCR
            # Paddle 3.x + oneDNN trên CPU Windows lỗi "ConvertPirAttribute2RuntimeAttribute not support"
            _ocr = PaddleOCR(lang="vi", enable_mkldnn=False)
        return [line for res in _ocr.predict(path) for line in res["rec_texts"]]

class OcrThenLlm(Agent):
    """Agent 2: OCR for split word, structured by LLM"""
    def __init__(self):
        super().__init__(role="ocr_then_llm", goal="Đọc đơn thuốc bằng OCR rồi cấu trúc hoá từ văn bản")

    def execute(self, data: str) -> str:
        try:
            text = "\n".join(_ocr_lines(data))
            reply = get_llm().invoke(STRUCTURE_FROM_TEXT.format(text=text))
            return to_report(parse_extract(reply.content), "ocr_then_llm")
        except Exception as e:                       # noqa: BLE001
            return to_report(None, f"ocr_then_llm lỗi: {e}")