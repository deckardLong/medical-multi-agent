from octochains import Agent
from ..prompts import EXTRACT
from ..schema import parse_extract, to_report
from .vlm_client import fit_for_vlm, image_message, read_image, vlm

class VlmDirect(Agent):
    """Agent 1: Read original image, get structure it"""

    def __init__(self):
        super().__init__(role="vlm_direct", goal="Đọc đơn thuốc trực tiếp từ ảnh gốc")

    def execute(self, data: str) -> str:
        try:
            raw, _ = read_image(data)
            reply = vlm().invoke([image_message(fit_for_vlm(raw), "image/png", EXTRACT)])
            return to_report(parse_extract(reply.content), "vlm_direct")
        except Exception as e:                       # noqa: BLE001 — một agent lỗi không được kéo đổ cả lượt
            return to_report(None, f"vlm_direct lỗi: {e}")