import base64
import io
import mimetypes
from pathlib import Path
from PIL import Image
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from product.config import ProductEnv

env = ProductEnv()

def vlm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(base_url=env.llm_base_url, api_key=env.llm_api_key, model=env.vlm_model, temperature=temperature)

def image_message(image_bytes: bytes, mime: str, prompt: str) -> HumanMessage:
    b64 = base64.b64encode(image_bytes).decode()
    return HumanMessage(content=[{"type": "text", "text": prompt},
                                 {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}])

def read_image(path: str) -> tuple[bytes, str]:
    return Path(path).read_bytes(), mimetypes.guess_type(path)[0] or "image/jpeg"

# Qwen2.5-VL tốn ~1 token / 28x28 px: ảnh quá lớn tràn context của Ollama và output bị cắt cụt giữa chừng
VLM_MAX_SIDE = 1600

def fit_for_vlm(raw: bytes, max_upscale: float = 1.0) -> bytes:
    """Đưa cạnh dài về VLM_MAX_SIDE: thu nhỏ ảnh lớn; phóng to ảnh nhỏ tối đa max_upscale lần."""
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    factor = min(max_upscale, VLM_MAX_SIDE / max(img.size))
    if factor != 1.0:
        img = img.resize((round(img.width * factor), round(img.height * factor)), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()