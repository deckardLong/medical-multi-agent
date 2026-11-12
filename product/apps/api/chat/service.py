from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import ChatSession, ChatMessage, MessageRole, Family, FamilyMember, User
from product.apps.api.members.permissions import can_write_member
from product.apps.agent.graph import agent

async def authorize_member(session: AsyncSession, member_id: UUID, user: User) -> FamilyMember:
    """Chỉ chủ gia đình (với thành viên không có tài khoản) hoặc chính người dùng được liên kết mới được chat hộ/với member_id này."""
    member = await session.get(FamilyMember, member_id)
    if member is None:
        raise ValueError("Không tìm thấy thành viên")
    family = await session.get(Family, member.family_id)
    if family is None or not can_write_member(member, family, user):
        raise PermissionError("Bạn không có quyền truy cập đoạn chat của thành viên này")
    return member

async def get_or_create_session(session: AsyncSession, member_id: UUID) -> ChatSession:
    chat = await session.scalar(select(ChatSession).where(ChatSession.member_id == member_id))

    # If chat's not exist => Create new
    if chat is None:
        chat = ChatSession(member_id=member_id)
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
    return chat

async def send_message(session: AsyncSession, member_id: UUID, content: str, user: User) -> ChatMessage:
    await authorize_member(session, member_id, user)
    chat = await get_or_create_session(session, member_id)
    session.add(ChatMessage(session_id=chat.id, role=MessageRole.USER, content=content))
    await session.commit()

    # Get history saved for agent => Context
    history = await session.scalars(
        select(ChatMessage).where(ChatMessage.session_id == chat.id).order_by(ChatMessage.created_at))
    messages = [(m.role.value, m.content) for m in history]         

    result = agent.invoke({"messages": messages})
    reply_text = result["messages"][-1].content

    # Reply from assistant
    reply = ChatMessage(session_id=chat.id, role=MessageRole.ASSISTANT, content=reply_text)
    session.add(reply)
    await session.commit()
    await session.refresh(reply)
    return reply

async def get_history(session: AsyncSession, member_id: UUID, user: User) -> list[ChatMessage]:
    await authorize_member(session, member_id, user)
    chat = await session.scalar(select(ChatSession).where(ChatSession.member_id == member_id))
    if chat is None: 
        return []
    rows = await session.scalars(
        select(ChatMessage).where(ChatMessage.session_id == chat.id).order_by(ChatMessage.created_at)
    )
    return list(rows)