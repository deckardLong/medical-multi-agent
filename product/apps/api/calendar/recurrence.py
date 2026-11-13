"""Logic thời gian dùng chung cho API lịch và calendar_tool của agent — hai bên không được tự viết riêng,
nếu không agent nói "mai có lịch" trong khi màn hình lịch không có."""
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo
from dateutil.rrule import rrulestr
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from product.config import ProductEnv
from product.db.models import CalendarEvent

TZ = ZoneInfo(ProductEnv().timezone)
MAX_OCCURRENCES_PER_EVENT = 500
_TOO_FREQUENT = ("FREQ=SECONDLY", "FREQ=MINUTELY")


def localize(dt: datetime) -> datetime:
    """Giờ không kèm múi giờ = giờ địa phương (người dùng nói "8 giờ sáng" là giờ Việt Nam)."""
    return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt


def validate_rule(rule: str, start: datetime) -> None:
    """ValueError nếu không phải RRULE (RFC 5545) hợp lệ."""
    if any(f in rule.upper().replace(" ", "") for f in _TOO_FREQUENT):
        raise ValueError("Lịch lặp theo giây/phút không được hỗ trợ")
    try:
        rrulestr(rule, dtstart=localize(start))
    except (ValueError, TypeError) as e:
        raise ValueError(f"recurrence_rule không hợp lệ theo chuẩn RRULE: {e}")


def occurrences(event: CalendarEvent, start: datetime, end: datetime) -> list[datetime]:
    """Các lần xảy ra của event trong [start, end]."""
    first = localize(event.starts_at)
    if not event.recurrence_rule:
        return [first] if start <= first <= end else []
    hits = []
    for t in rrulestr(event.recurrence_rule, dtstart=first).xafter(start, inc=True):
        if t > end or len(hits) >= MAX_OCCURRENCES_PER_EVENT:
            break
        hits.append(t)
    return hits


async def occurrences_between(session: AsyncSession, member_id: UUID, start: datetime, end: datetime,
                              include_pending: bool = False) -> list[tuple[datetime, CalendarEvent]]:
    q = select(CalendarEvent).where(
        CalendarEvent.member_id == member_id,
        # Lịch lặp bắt đầu từ tháng trước vẫn có thể xảy ra trong khoảng này → lấy mọi event có recurrence_rule
        or_(CalendarEvent.recurrence_rule.is_not(None), CalendarEvent.starts_at.between(start, end)))
    if not include_pending:
        q = q.where(CalendarEvent.confirmed_at.is_not(None))
    hits = [(t, ev) for ev in await session.scalars(q) for t in occurrences(ev, start, end)]
    return sorted(hits, key=lambda x: x[0])
