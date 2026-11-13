from langchain_core.tools import tool
from common.config import Env as RetrievalEnv
from retrieval.settings import load_all
from retrieval.index import make_client
from retrieval.embedding import build_embedder
from retrieval.search.hybrid import HybridSearcher

_settings = load_all(RetrievalEnv())
_client = make_client(_settings.env)
_embedder = build_embedder(_settings.embed)
_searcher = HybridSearcher(_client, _settings.collection, _settings.retrieve.search,
                           payload_fields=["chunk_id", "uid", "doc_id", "start", "end", "p_start", "p_end", "text", "ctx"])

@tool
def medical_retrieval_tool(query: str) -> str:
    """Tìm kiếm trong kho tài liệu y tế (đa ngôn ngữ) các đoạn văn bản liên quan nhất tới câu hỏi.
    Dùng tool này khi câu hỏi của người dùng cần thông tin y khoa (triệu chứng, bệnh, thuốc, điều trị, ...)
    mà câu trả lời nên dựa trên tài liệu tham khảo thay vì chỉ dựa vào kiến thức có sẵn của mô hình."""
    enc = _embedder.encode_queries([query])
    vectors = [(enc.dense[0].tolist(), enc.sparse[0] if enc.sparse else None)]
    candidates = _searcher.search(vectors)
    if not candidates:
        return "Không tìm thấy tài liệu liên quan trong corpus."
    # ctx = "tiêu đề bài | mục"; tiêu đề là thứ người dùng hiểu được khi dẫn nguồn, doc_id thì không
    return "\n\n".join(f"[{i}] Nguồn: {(c.ctx or '').split(' | ')[0].strip() or c.doc_id}\n{(c.text or '')[:500]}"
                       for i, c in enumerate(candidates[:5], 1))