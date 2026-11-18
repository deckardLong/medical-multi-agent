"""Model local qua Ollama (endpoint tương thích OpenAI) cho: sinh dữ liệu, judge của Ragas, judge của DeepEval."""
import json
import re
from functools import lru_cache
from typing import Any
from langchain_openai import ChatOpenAI
from evaluation.config import env

_JSON = re.compile(r"\{.*\}", re.DOTALL)


def chat_model(model: str, temperature: float = 0.0, json_mode: bool = False) -> ChatOpenAI:
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    return ChatOpenAI(base_url=env.judge_base_url, api_key=env.judge_api_key, model=model,
                      temperature=temperature, timeout=600, max_retries=1, model_kwargs=kwargs)


def parse_json(text: str) -> dict:
    m = _JSON.search(text or "")
    if not m:
        raise ValueError(f"Không có JSON trong output: {text[:200]!r}")
    return json.loads(m.group(0))


def ask_json(model: str, prompt: str, temperature: float = 0.0, retries: int = 2) -> dict:
    """Gọi model với JSON mode; model nhỏ đôi khi trả JSON hỏng → thử lại."""
    llm = chat_model(model, temperature, json_mode=True)
    last: Exception | None = None
    for _ in range(retries + 1):
        try:
            return parse_json(llm.invoke(prompt).content)
        except (ValueError, json.JSONDecodeError) as e:
            last = e
    raise last  # type: ignore[misc]


# ---------------- Ragas ----------------
@lru_cache
def ragas_llm():
    import instructor
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    client = AsyncOpenAI(base_url=env.judge_base_url, api_key=env.judge_api_key, timeout=600)
    # Mode.JSON: Ollama không hỗ trợ tool-calling ổn định cho mọi model → yêu cầu trả JSON thuần
    return llm_factory(env.judge_model, provider="openai", client=client, mode=instructor.Mode.JSON,
                       max_tokens=4096, temperature=0.0)   # 1024 mặc định → IncompleteOutputException với câu trả lời dài


@lru_cache
def bge_m3_embedding():
    """Embedding cho Ragas (answer_relevancy) dùng lại BGE-M3 của pipeline retrieval — không cần thêm model."""
    import asyncio
    from ragas.embeddings import BaseRagasEmbedding
    from product.apps.agent.tools.medical_retrieval_tool import _embedder

    class BgeM3(BaseRagasEmbedding):
        def embed_text(self, text: str, **_: Any) -> list[float]:
            return _embedder.encode_queries([text]).dense[0].tolist()

        async def aembed_text(self, text: str, **kw: Any) -> list[float]:
            return await asyncio.to_thread(self.embed_text, text, **kw)

    return BgeM3()


# ---------------- DeepEval ----------------
def deepeval_judge():
    from deepeval.models import DeepEvalBaseLLM

    class LocalJudge(DeepEvalBaseLLM):
        """DeepEval gọi generate(prompt, schema=...) khi cần output có cấu trúc → JSON mode + validate bằng schema."""

        def __init__(self):
            self.model = chat_model(env.judge_model, json_mode=True)
            self.plain = chat_model(env.judge_model)

        def load_model(self):
            return self.model

        def _finish(self, content: str, schema):
            if schema is None:
                return content
            try:
                return schema.model_validate(parse_json(content))
            except Exception as e:
                raise ValueError(f"Judge trả JSON không khớp schema {schema.__name__}: {content[:200]!r}") from e

        def generate(self, prompt: str, schema=None, **_: Any):
            llm = self.model if schema is not None else self.plain
            out = llm.invoke(prompt).content
            try:
                return self._finish(out, schema)
            except ValueError:
                return self._finish(llm.invoke(prompt).content, schema)       # thử lại một lần

        async def a_generate(self, prompt: str, schema=None, **_: Any):
            llm = self.model if schema is not None else self.plain
            out = (await llm.ainvoke(prompt)).content
            try:
                return self._finish(out, schema)
            except ValueError:
                return self._finish((await llm.ainvoke(prompt)).content, schema)

        def get_model_name(self) -> str:
            return f"ollama:{env.judge_model}"

    return LocalJudge()


async def ragas_score(metric, retries: int = 1, **kwargs) -> tuple[float, str | None]:
    """Gọi metric Ragas, thử lại khi lỗi (judge local hay timeout/trả JSON hỏng lúc Ollama đang đổi model).
    Trả (điểm, lỗi): lỗi ghi kèm tên loại exception vì nhiều exception của instructor/openai có message rỗng."""
    err = None
    for _ in range(retries + 1):
        try:
            return float((await metric.ascore(**kwargs)).value), None
        except Exception as e:                                               # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:160]}"
    return float("nan"), err
