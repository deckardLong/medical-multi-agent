import asyncio
import re
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import ToolMessage
from product.db.models import ChatSession, ChatMessage, Document, MessageRole
from product.apps.api.records.service import UNRESOLVED, propose_from_extraction
from product.apps.agent.graph import agent
from product.apps.agent.tools.member_profile_tool import member_allergies, member_profile_text
from product.apps.agent.tools.vision_extract_tool import render_summary, run_engine

_SOURCE_TOOLS = {"medical_retrieval_tool", "web_search_tool"}
_MEDICAL_TOOLS = _SOURCE_TOOLS | {"vision_extract_tool"}
_SOURCE_LINE = re.compile(r"^\[\d+\] Nguồn: (.+)$", re.MULTILINE)
_DRUG_WORDS = ("thuốc", "kháng sinh", "liều", "mg", "viên", "đơn")
# Gốc/hậu tố tên hoạt chất (INN) phổ biến: câu chỉ nêu tên thuốc ("Amoxicillin ...") vẫn phải kích hoạt cảnh báo
_DRUG_STEMS = re.compile(r"\w*(cillin|mycin|micin|cycline|floxacin|cef\w+|sulfa\w*|prazole|statin|olol|pril|sartan|"
                         r"profen|fenac|coxib|azole|vir|mab|parin|xaban|gliptin|formin|cort\w*|sone|lone|"
                         r"paracetamol|acetaminophen|aspirin|ibuprofen|codein\w*|tramadol|insulin)\b", re.IGNORECASE)
# Lịch sử dài khiến model 7B chép lại câu trả lời cũ thay vì gọi tool; cũng làm mỗi lượt chậm hơn trên CPU
HISTORY_LIMIT = 12


async def get_or_create_session(session: AsyncSession, member_id: UUID) -> ChatSession:
    chat = await session.scalar(select(ChatSession).where(ChatSession.member_id == member_id))

    # If chat's not exist => Create new
    if chat is None:
        chat = ChatSession(member_id=member_id)
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
    return chat


async def _load_attachments(session: AsyncSession, member_id: UUID, document_ids: list[UUID]) -> list[Document]:
    if not document_ids:
        return []
    docs = {d.id: d for d in await session.scalars(select(Document).where(
        Document.id.in_(document_ids), Document.member_id == member_id))}
    if missing := [d for d in document_ids if d not in docs]:
        raise ValueError(f"Không tìm thấy tài liệu: {', '.join(map(str, missing))}")
    return [docs[d] for d in document_ids]


async def _read_attachments(session: AsyncSession, docs: list[Document]) -> tuple[str, str]:
    """Đọc ảnh ngay tại service: để model tự quyết thì nó có thể lặp lại kết quả cũ trong lịch sử mà không đọc ảnh mới.
    Mỗi thuốc đọc được thành một đề xuất hồ sơ chờ xác nhận. Trả về (bản cho model, bản hiển thị cho người dùng)."""
    for_model, for_user = [], []
    for doc in docs:
        result = await asyncio.to_thread(run_engine, doc.storage_path)
        doc.extracted_json = result
        proposals = await propose_from_extraction(session, doc, result)
        note = ""
        if proposals:
            flagged = sum(1 for p in proposals if UNRESOLVED in str(p.payload))
            note = (f"\nĐã tạo {len(proposals)} đề xuất thuốc trong mục Hồ sơ chờ xác nhận"
                    + (f" ({flagged} mục có trường {UNRESOLVED}: phải sửa đúng giá trị trước khi xác nhận)" if flagged
                       else "") + ". Hồ sơ chỉ có hiệu lực sau khi bạn bấm \"Xác nhận\".")
        for_model.append(f"Tài liệu {doc.id}:\n{render_summary(result)}{note}")
        for_user.append(render_summary(result, for_user=True) + note)
    await session.commit()
    return "\n\n".join(for_model), "\n\n".join(for_user)


def _for_agent(m: ChatMessage) -> tuple[str, str]:
    note = "".join(f"\n[Người dùng đính kèm tài liệu, document_id: {d}]" for d in m.attachments or [])
    return m.role.value, m.content + note


_URL = re.compile(r"https?://[^\s)\]>*]+")
_SOURCE_CLAIM = re.compile(r"^[\s*_-]*nguồn[\s*_]*:(.*)$", re.IGNORECASE)


def _strip_unverified_sources(reply: str, tool_text: str) -> str:
    """Bỏ dòng "Nguồn: ..." mà URL/tiêu đề không có trong kết quả tool của CHÍNH lượt này (model 7B hay bịa link,
    hoặc chép link từ câu trả lời cũ trong lịch sử)."""
    kept = []
    for line in reply.splitlines():
        m = _SOURCE_CLAIM.match(line)
        if m:
            claim = m.group(1).strip(" *_")
            urls = [u.rstrip(".,;") for u in _URL.findall(claim)]
            ok = all(u in tool_text for u in urls) if urls else bool(claim) and claim.split(" — ")[0] in tool_text
            if not ok:
                continue
        kept.append(line)
    return "\n".join(kept).rstrip()


def _with_sources(reply: str, messages: list) -> str:
    """Model nhỏ hay quên hoặc bịa nguồn dù prompt yêu cầu → chỉ giữ nguồn có thật, thiếu thì tự liệt kê."""
    tool_text = "\n".join(str(m.content) for m in messages if isinstance(m, ToolMessage))
    reply = _strip_unverified_sources(reply, tool_text)
    if any(_SOURCE_CLAIM.match(line) for line in reply.splitlines()):
        return reply
    sources = []
    for m in messages:
        if isinstance(m, ToolMessage) and m.name in _SOURCE_TOOLS:
            sources += [s.strip() for s in _SOURCE_LINE.findall(str(m.content)) if s.strip() not in sources]
    if not sources:
        return reply
    return reply + "\n\nTài liệu đã tra cứu:\n" + "\n".join(f"- {s}" for s in sources[:3])


def _with_allergy_warning(reply: str, messages: list, allergies: list[str], had_attachments: bool) -> str:
    """An toàn dị ứng không được phụ thuộc vào việc model 7B có nhớ đọc hồ sơ / có gọi tool hay không."""
    if not allergies:
        return reply
    text = reply.lower()
    about_drugs = (had_attachments
                   or any(isinstance(m, ToolMessage) and m.name in _MEDICAL_TOOLS for m in messages)
                   or any(w in text for w in _DRUG_WORDS)
                   or _DRUG_STEMS.search(reply) is not None
                   or any(a.lower() in text for a in allergies))
    warning = (f"Lưu ý an toàn: hồ sơ ghi nhận bạn DỊ ỨNG với {', '.join(allergies)}. "
               "Hãy báo bác sĩ/dược sĩ điều này trước khi dùng bất kỳ thuốc nào được nhắc tới ở trên.")
    # Model có thể chép nguyên câu cảnh báo từ lượt trước trong lịch sử → không gắn lặp
    if not about_drugs or warning in reply:
        return reply
    return f"{reply}\n\n{warning}"


async def send_message(session: AsyncSession, member_id: UUID, content: str,
                       document_ids: list[UUID] | None = None) -> ChatMessage:
    """member_id đã được router kiểm tra quyền (members.deps.writable_member)."""
    docs = await _load_attachments(session, member_id, document_ids or [])
    chat = await get_or_create_session(session, member_id)
    session.add(ChatMessage(session_id=chat.id, role=MessageRole.USER, content=content,
                            attachments=[str(d.id) for d in docs] or None))
    await session.commit()
    attachments_text, attachments_for_user = await _read_attachments(session, docs)

    # Get history saved for agent => Context
    history = list(await session.scalars(
        select(ChatMessage).where(ChatMessage.session_id == chat.id)
        .order_by(ChatMessage.created_at.desc()).limit(HISTORY_LIMIT)))[::-1]
    # Nạp hồ sơ sẵn thay vì trông vào model tự gọi get_member_profile (model 7B thường bỏ qua bước này)
    profile = await member_profile_text(member_id)
    messages = [("system", f"Hồ sơ của người đang được tư vấn:\n{profile}")]
    if attachments_text:
        messages.append(("system", "Tài liệu người dùng vừa đính kèm ĐÃ được đọc xong và kết quả dưới đây ĐÃ được "
                                   "hiển thị nguyên văn cho người dùng. KHÔNG liệt kê lại danh sách thuốc; chỉ trả lời "
                                   "phần câu hỏi còn lại (nếu có) hoặc nhắc người dùng xác nhận các mục cần chọn, "
                                   f"ngắn gọn:\n{attachments_text}"))
    # Lượt có đính kèm chỉ hỏi về tài liệu mới: bỏ lịch sử để model không chép kết quả đọc đơn cũ
    messages += [_for_agent(m) for m in (history[-1:] if docs else history)]

    result = await agent.ainvoke({"messages": messages},
                                 config={"configurable": {"member_id": str(member_id)}})
    reply_text = _with_sources(result["messages"][-1].content, result["messages"])
    if attachments_for_user:
        # Kết quả đọc đơn hiển thị nguyên văn do code tạo — model 7B diễn giải lại thì hay tự chọn/thêm "uống"
        reply_text = f"{attachments_for_user}\n\n{reply_text}"
    reply_text = _with_allergy_warning(reply_text, result["messages"], await member_allergies(member_id), bool(docs))

    # Reply from assistant
    reply = ChatMessage(session_id=chat.id, role=MessageRole.ASSISTANT, content=reply_text)
    session.add(reply)
    await session.commit()
    await session.refresh(reply)
    return reply


async def get_history(session: AsyncSession, member_id: UUID) -> list[ChatMessage]:
    chat = await session.scalar(select(ChatSession).where(ChatSession.member_id == member_id))
    if chat is None:
        return []
    rows = await session.scalars(
        select(ChatMessage).where(ChatMessage.session_id == chat.id).order_by(ChatMessage.created_at)
    )
    return list(rows)
