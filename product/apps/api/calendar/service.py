from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import CalendarEvent, EventSource
from product.apps.api.errors import ConflictError
from .recurrence import localize, occurrences_between, validate_rule, TZ
from .schemas import EventIn, OccurrenceOut

DEFAULT_WINDOW = timedelta(days=30)
MAX_WINDOW = timedelta(days=366)


async def _get(session: AsyncSession, member_id: UUID, event_id: UUID) -> CalendarEvent:
    ev = await session.get(CalendarEvent, event_id)
    if ev is None or ev.member_id != member_id:        # lịch của member khác cũng là "không tìm thấy"
        raise LookupError("Không tìm thấy lịch")
    return ev


async def list_occurrences(session: AsyncSession, member_id: UUID, start: datetime | None, end: datetime | None,
                           include_pending: bool) -> list[OccurrenceOut]:
    start = localize(start) if start else datetime.now(TZ)
    end = localize(end) if end else start + DEFAULT_WINDOW
    if end <= start:
        raise ValueError("end phải sau start")
    if end - start > MAX_WINDOW:
        raise ValueError("Khoảng thời gian tối đa là 366 ngày")
    hits = await occurrences_between(session, member_id, start, end, include_pending)
    return [OccurrenceOut(event_id=ev.id, occurs_at=t, type=ev.type, title=ev.title, recurrence_rule=ev.recurrence_rule,
                          source=ev.source, confirmed=ev.confirmed_at is not None) for t, ev in hits]


async def list_pending(session: AsyncSession, member_id: UUID) -> list[CalendarEvent]:
    return list(await session.scalars(select(CalendarEvent).where(
        CalendarEvent.member_id == member_id, CalendarEvent.confirmed_at.is_(None))
        .order_by(CalendarEvent.starts_at)))


async def create_event(session: AsyncSession, member_id: UUID, data: EventIn) -> CalendarEvent:
    """Người dùng tự tạo → xác nhận ngay."""
    start = localize(data.starts_at)
    rule = (data.recurrence_rule or "").strip() or None
    if rule:
        validate_rule(rule, start)
    ev = CalendarEvent(member_id=member_id, type=data.type, title=data.title.strip(), starts_at=start,
                       recurrence_rule=rule, source=EventSource.MANUAL, confirmed_at=datetime.now(timezone.utc))
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return ev


async def confirm_event(session: AsyncSession, member_id: UUID, event_id: UUID) -> CalendarEvent:
    ev = await _get(session, member_id, event_id)
    if ev.confirmed_at is not None:
        raise ConflictError("Lịch này đã được xác nhận")
    ev.confirmed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(ev)
    return ev


async def delete_event(session: AsyncSession, member_id: UUID, event_id: UUID) -> None:
    await session.delete(await _get(session, member_id, event_id))
    await session.commit()
