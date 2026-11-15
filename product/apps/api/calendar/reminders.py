import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from product.config import ProductEnv
from product.db.models import CalendarEvent, Family, FamilyMember, ReminderLog
from product.db.session import SessionLocal
from .notify import recipient_email, send_reminder_email
from .recurrence import TZ, occurrences

log = logging.getLogger(__name__)
env = ProductEnv()


@dataclass(frozen=True)
class _Due:
    event_id: UUID
    occurs_at: datetime
    title: str
    member_name: str
    to: str


async def _collect(now: datetime, window_end: datetime) -> list[_Due]:
    """Đọc hết dữ liệu cần gửi thành giá trị thuần rồi đóng session: rollback giữa vòng lặp sẽ làm mọi ORM object
    hết hạn, và truy cập lại chúng trong async (lazy load) là lỗi MissingGreenlet."""
    due = []
    async with SessionLocal() as session:
        events = await session.scalars(select(CalendarEvent).where(
            CalendarEvent.confirmed_at.is_not(None),
            # Lịch lặp: không biết trước lần kế tiếp nên lấy hết; lịch một lần: chỉ những cái rơi vào khoảng quét
            or_(CalendarEvent.recurrence_rule.is_not(None), CalendarEvent.starts_at.between(now, window_end))))
        for event in events:
            times = occurrences(event, now, window_end)
            if not times:
                continue
            member = await session.get(FamilyMember, event.member_id)
            to = await recipient_email(session, member, await session.get(Family, member.family_id))
            if to:
                due += [_Due(event.id, t, event.title, member.display_name, to) for t in times]
    return due


async def _send_once(item: _Due, now: datetime) -> bool:
    """Ghi log trước rồi mới gửi, cùng một transaction: unique (event_id, occurs_at) đảm bảo mỗi lần xảy ra chỉ
    được nhắc một lần kể cả khi chạy nhiều worker; gửi lỗi thì rollback để lượt quét sau thử lại."""
    async with SessionLocal() as session:
        claimed = await session.scalar(
            pg_insert(ReminderLog).values(event_id=item.event_id, occurs_at=item.occurs_at, sent_at=now)
            .on_conflict_do_nothing(constraint="uq_reminder_event_occurrence").returning(ReminderLog.id))
        if claimed is None:
            return False                                  # đã gửi ở lượt trước hoặc worker khác đang gửi
        try:
            await send_reminder_email(item.to, item.member_name, item.title, item.occurs_at)
        except Exception:
            log.exception("Gửi mail nhắc lịch thất bại, event_id=%s", item.event_id)
            await session.rollback()
            return False
        await session.commit()
        return True


async def scan_and_send() -> int:
    if not env.smtp_host:
        log.warning("Chưa cấu hình SMTP (PRODUCT_SMTP_HOST) — bỏ qua lượt quét nhắc lịch.")
        return 0
    now = datetime.now(TZ)
    sent = 0
    for item in await _collect(now, now + timedelta(minutes=env.reminder_lead_minutes)):
        sent += await _send_once(item, now)
    if sent:
        log.info("Đã gửi %d email nhắc lịch", sent)
    return sent
