from langchain_core.tools import tool
from tavily import AsyncTavilyClient
from product.config import ProductEnv
from .web_sources import TRUSTED_DOMAINS

_client = AsyncTavilyClient(api_key=ProductEnv().tavily_api_key)

@tool
async def web_search_tool(query: str) -> str:
    """Cite URLs when answer"""
    res = await _client.search(query=query, max_results=5, include_domains=TRUSTED_DOMAINS)
    results = res.get("results", [])
    if not results:
        return "Không tìm thấy kết quả từ các nguồn uy tín."
    return "\n\n".join(f"{r['title']} — {r['url']}\n{r['content'][:500]}" for r in results)