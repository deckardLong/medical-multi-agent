from datetime import datetime, timedelta
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from product.db.session import SessionLocal
from product.db.models import CalendarEvent, EventSource, EventType
from product.apps.api.calendar.recurrence import TZ, localize, occurrences_between, validate_rule
from .context import member_id_from

# List incoming events
@tool
async def list_upcoming_events(config: RunnableConfig, days: int = 7) -> str:
    """Liệt kê lịch khám, nhắc uống thuốc, tái khám ĐÃ XÁC NHẬN trong `days` ngày tới."""
    now = datetime.now(TZ)
    async with SessionLocal() as s:
        hits = await occurrences_between(s, member_id_from(config), now, now + timedelta(days=max(1, min(days, 366))))
    if not hits:
        return f"Không có lịch nào trong {days} ngày tới."
    return "\n".join(f"- {t.astimezone(TZ):%d/%m %H:%M} | {ev.type.value} | {ev.title}" for t, ev in hits)

# Propose calendar event
@tool
async def propose_calendar_event(title: str, event_type: EventType, starts_at: str, config: RunnableConfig,
                                 recurrence_rule: str | None = None) -> str:
    """Tạo ĐỀ XUẤT lịch (lịch khám, nhắc uống thuốc, tái khám) — chưa có hiệu lực cho tới khi người dùng xác nhận.
    starts_at theo ISO 8601 (vd 2026-11-20T08:00); recurrence_rule theo chuẩn RRULE (vd FREQ=DAILY;COUNT=7)."""
    try:
        start = localize(datetime.fromisoformat(starts_at))
    except ValueError:
        return "starts_at không đúng định dạng ISO 8601, hãy hỏi lại người dùng ngày giờ cụ thể."
    if start < datetime.now(TZ):
        return "Thời điểm này đã qua, hãy hỏi lại người dùng."
    if recurrence_rule:
        try:
            validate_rule(recurrence_rule, start)
        except ValueError as e:
            return str(e)
    async with SessionLocal() as s:
        ev = CalendarEvent(member_id=member_id_from(config), type=event_type, title=title, starts_at=start,
                           recurrence_rule=recurrence_rule, source=EventSource.AGENT, confirmed_at=None)
        s.add(ev)
        await s.commit()
        await s.refresh(ev)
    return (f"Đã tạo đề xuất lịch: {title} lúc {start:%d/%m/%Y %H:%M}"
            f"{' (lặp: ' + recurrence_rule + ')' if recurrence_rule else ''}. CHƯA có hiệu lực: nhắc người dùng bấm "
            "\"Xác nhận\" ở mục Lịch chờ duyệt. Không hỏi lại trong chat có muốn lưu không.")
