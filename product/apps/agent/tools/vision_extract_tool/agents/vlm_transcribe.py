from octochains import Agent
from product.apps.agent.llm import get_llm
from ..prompts import STRUCTURE_FROM_TEXT, TRANSCRIBE
from ..schema import parse_extract, to_report
from .vlm_client import fit_for_vlm, image_message, read_image, vlm

class VlmTranscribe(Agent):
    """Agent 3: VLM get full image, structured by LLM."""

    def __init__(self):
        super().__init__(role="vlm_transcribe", goal="Chép nguyên văn ảnh phóng to rồi cấu trúc hoá")

    def execute(self, data: str) -> str:
        try:
            raw, _ = read_image(data)
            transcript = vlm().invoke([image_message(fit_for_vlm(raw, max_upscale=2.0), "image/png", TRANSCRIBE)]).content
            reply = get_llm().invoke(STRUCTURE_FROM_TEXT.format(text=transcript))
            return to_report(parse_extract(reply.content), "vlm_transcribe")
        except Exception as e:                       # noqa: BLE001
            return to_report(None, f"vlm_transcribe lỗi: {e}")