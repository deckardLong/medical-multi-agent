from langchain.agents import create_agent
from .llm import get_llm
from .tools.medical_retrieval_tool import medical_retrieval_tool

SYSTEM_PROMPT = """Bạn là trợ lý y tế. Với MỌI câu hỏi liên quan tới y khoa (triệu chứng, bệnh, thuốc, \
điều trị, chẩn đoán, ...), bạn BẮT BUỘC phải gọi tool `medical_retrieval_tool` với câu hỏi của người dùng \
trước khi trả lời — không được tự trả lời chỉ bằng kiến thức có sẵn, kể cả khi bạn nghĩ mình đã biết câu trả lời.
Chỉ trả lời dựa trên nội dung tool trả về; nếu tool không tìm thấy thông tin liên quan, hãy nói rõ là không \
tìm thấy trong kho tài liệu thay vì bịa câu trả lời.
Không hỏi ngược người dùng các thông tin nội bộ như chunk_id, uid, start, end — đó là chi tiết triển khai, \
người dùng không biết và không cần cung cấp."""

agent = create_agent(get_llm(), tools=[medical_retrieval_tool], system_prompt=SYSTEM_PROMPT)