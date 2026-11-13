from langchain_core.tools import tool
from tavily import AsyncTavilyClient
from product.config import ProductEnv
from .web_sources import TRUSTED_DOMAINS

_api_key = ProductEnv().tavily_api_key
_client = AsyncTavilyClient(api_key=_api_key) if _api_key else None

@tool
async def web_search_tool(query: str) -> str:
    """Tìm trên web, chỉ trong các nguồn y tế uy tín (WHO, CDC, NIH, Bộ Y tế, ...). Chỉ dùng khi
    medical_retrieval_tool không có kết quả phù hợp. Khi trả lời phải dẫn kèm URL nguồn."""
    if _client is None:
        return "Tìm kiếm web chưa được cấu hình (thiếu PRODUCT_TAVILY_API_KEY)."
    res = await _client.search(query=query, max_results=5, include_domains=TRUSTED_DOMAINS)
    results = res.get("results", [])
    if not results:
        return "Không tìm thấy kết quả từ các nguồn uy tín."
    return "\n\n".join(f"{r['title']} — {r['url']}\n{r['content'][:500]}" for r in results)