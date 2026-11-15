"""Chỉ chứa truy vấn đếm/lấy dữ liệu, không ghép kết quả. Mọi hàm nhận danh sách member_id ĐÃ lọc quyền."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import (CalendarEvent, ChatMessage, ChatSession, Document, MedicalRecord,
                               MessageRole, RecordKind)


async def count_user_messages_since(session: AsyncSession, member_ids: list[UUID], since: datetime) -> int:
    q = (select(func.count(ChatMessage.id)).join(ChatSession, ChatMessage.session_id == ChatSession.id)
         .where(ChatSession.member_id.in_(member_ids), ChatMessage.role == MessageRole.USER,
                ChatMessage.created_at >= since))
    return await session.scalar(q) or 0


async def count_documents(session: AsyncSession, member_ids: list[UUID]) -> int:
    return await session.scalar(select(func.count(Document.id)).where(Document.member_id.in_(member_ids))) or 0


async def count_pending(session: AsyncSession, member_ids: list[UUID]) -> int:
    records = await session.scalar(select(func.count(MedicalRecord.id)).where(
        MedicalRecord.member_id.in_(member_ids), MedicalRecord.confirmed_at.is_(None))) or 0
    events = await session.scalar(select(func.count(CalendarEvent.id)).where(
        CalendarEvent.member_id.in_(member_ids), CalendarEvent.confirmed_at.is_(None))) or 0
    return records + events


async def confirmed_record_counts(session: AsyncSession, member_ids: list[UUID]) -> dict[UUID, int]:
    rows = await session.execute(
        select(MedicalRecord.member_id, func.count(MedicalRecord.id))
        .where(MedicalRecord.member_id.in_(member_ids), MedicalRecord.confirmed_at.is_not(None))
        .group_by(MedicalRecord.member_id))
    return dict(rows.all())


async def confirmed_alerts(session: AsyncSession, member_ids: list[UUID]) -> list[MedicalRecord]:
    """Dị ứng và bệnh nền đã xác nhận — hai loại cần thấy ngay trên thẻ thành viên."""
    return list(await session.scalars(select(MedicalRecord).where(
        MedicalRecord.member_id.in_(member_ids), MedicalRecord.confirmed_at.is_not(None),
        MedicalRecord.kind.in_([RecordKind.ALLERGY, RecordKind.CONDITION]))))


async def recent_documents(session: AsyncSession, member_ids: list[UUID], limit: int) -> list[Document]:
    return list(await session.scalars(select(Document).where(Document.member_id.in_(member_ids))
                                      .order_by(Document.created_at.desc()).limit(limit)))


async def recent_confirmed_records(session: AsyncSession, member_ids: list[UUID], limit: int) -> list[MedicalRecord]:
    return list(await session.scalars(select(MedicalRecord).where(
        MedicalRecord.member_id.in_(member_ids), MedicalRecord.confirmed_at.is_not(None))
        .order_by(MedicalRecord.confirmed_at.desc()).limit(limit)))