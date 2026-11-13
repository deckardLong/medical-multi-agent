from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dateutil.rrule import rrulestr
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import or_, select
from product.config import ProductEnv
from product.db.session import SessionLocal
from product.db.models import CalendarEvent, EventSource, EventType
from .context import member_id_from

TZ = ZoneInfo(ProductEnv().timezone)

# List incoming events
@tool
async def list_upcoming_events(config: RunnableConfig, days: int = 7) -> str:
    """List appointment, medication, follow up in 'days' after."""
    now = datetime.now(TZ)
    end = now + timedelta(days=days)
    async with SessionLocal() as s:
        events = await s.scalars(select(CalendarEvent).where(
            CalendarEvent.member_id == member_id_from(config),
            CalendarEvent.confirmed_at.is_not(None),
            or_(CalendarEvent.recurrence_rule.is_not(None), CalendarEvent.starts_at.between(now, end))))
        hits = []
        for ev in events:
            times = (rrulestr(ev.recurrence_rule, dtstart=ev.starts_at).between(now, end, inc=True)
                     if ev.recurrence_rule else [ev.starts_at])
            hits += [(t, ev) for t in times]
    if not hits:
        return f"Không có lịch nào trong {days} ngày tới."
    hits.sort(key=lambda x: x[0])
    return "\n".join(f"- {t.astimezone(TZ):%d/%m %H:%M} | {ev.type.value} | {ev.title}" for t, ev in hits)

# Propose calendar event
@tool
async def propose_calendar_event(title: str, event_type: EventType, starts_at: str, config: RunnableConfig,
                                 recurrence_rule: str | None = None) -> str:
    try:
        start = datetime.fromisoformat(starts_at)
    except ValueError:
        return "starts_at không đúng định dạng ISO 8601, hãy hỏi lại người dùng ngày giờ cụ thể."
    if start.tzinfo is None:
        start = start.replace(tzinfo=TZ)                      # người dùng nói "8 giờ sáng" = giờ Việt Nam
    if start < datetime.now(TZ):
        return "Thời điểm này đã qua, hãy hỏi lại người dùng."
    if recurrence_rule:
        try:
            rrulestr(recurrence_rule, dtstart=start)
        except ValueError:
            return f"recurrence_rule '{recurrence_rule}' không hợp lệ theo chuẩn RRULE."
    async with SessionLocal() as s:
        ev = CalendarEvent(member_id=member_id_from(config), type=event_type, title=title, starts_at=start,
                           recurrence_rule=recurrence_rule, source=EventSource.AGENT, confirmed_at=None)
        s.add(ev)
        await s.commit()
        await s.refresh(ev)
    return (f"Đã tạo đề xuất lịch {ev.id}: {title} lúc {start:%d/%m/%Y %H:%M}"
            f"{' (lặp: ' + recurrence_rule + ')' if recurrence_rule else ''}. CHƯA có hiệu lực, cần người dùng xác nhận.")