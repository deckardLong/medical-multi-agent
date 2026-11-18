"""Đọc chuỗi message LangChain mà chat service trả về (send_message_traced)."""
import re
from dataclasses import dataclass, field
from langchain_core.messages import AIMessage, ToolMessage

_SOURCE_BLOCK = re.compile(r"^\[\d+\] Nguồn: ", re.MULTILINE)
RETRIEVAL_TOOLS = ("medical_retrieval_tool", "web_search_tool")


@dataclass
class Trace:
    tools_called: list[str] = field(default_factory=list)
    tool_outputs: dict[str, list[str]] = field(default_factory=dict)
    raw_answer: str = ""                      # câu trả lời của model TRƯỚC khi chat service lọc nguồn / gắn cảnh báo

    @property
    def contexts(self) -> list[str]:
        """Từng đoạn tài liệu mà tool truy xuất trả về — ngữ cảnh để Ragas chấm faithfulness."""
        out = []
        for name in RETRIEVAL_TOOLS:
            for text in self.tool_outputs.get(name, []):
                out += [b.strip() for b in _SOURCE_BLOCK.split(text) if b.strip()]
        return out


def read_trace(messages: list) -> Trace:
    t = Trace()
    for m in messages:
        if isinstance(m, AIMessage):
            t.tools_called += [c["name"] for c in (m.tool_calls or [])]
            if not m.tool_calls and m.content:
                t.raw_answer = m.content
        elif isinstance(m, ToolMessage):
            t.tool_outputs.setdefault(m.name or "", []).append(str(m.content))
    return t
