from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import FamilyMember, MedicalRecord, RecordKind, User
from product.apps.api.calendar.recurrence import TZ, occurrences_between
from product.apps.api.members import service as members_service
from product.apps.api.members.permissions import can_read_member
from . import aggregates as agg
from .schemas import DashboardOut, MemberCard, Summary, TimelineItem, UpcomingItem

TIMELINE_LIMIT = 10
UPCOMING_LIMIT = 5


def _age(dob: date | None, today: date) -> int | None:
    if dob is None:
        return None
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _label(rec: MedicalRecord) -> str:
    """payload do agent hoặc người dùng tạo nên không cố định khoá; ưu tiên 'name', không có thì lấy giá trị đầu."""
    p = rec.payload or {}
    return str(p.get("name") or next(iter(p.values()), rec.kind.value))


async def build_dashboard(session: AsyncSession, user: User) -> DashboardOut:
    now = datetime.now(TZ)
    try:
        family = await members_service.get_family_for_owner(session, user)
    except ValueError as e:          # đổi sang LookupError để router không phải bắt mọi ValueError (sẽ che bug thật)
        raise LookupError(str(e)) from e
    members = await members_service.list_members(session, family.id)
    readable = [m for m in members if can_read_member(m, family, user)]
    ids = [m.id for m in readable]
    by_id: dict = {m.id: m for m in members}

    # ── summary ──
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    upcoming_all = []
    for m in readable:                           # gia đình chỉ vài người → mỗi người một truy vấn là chấp nhận được
        upcoming_all += [(t, ev, m) for t, ev in
                         await occurrences_between(session, m.id, now, now + timedelta(days=7))]
    upcoming_all.sort(key=lambda x: x[0])
    summary = Summary(
        consultations_this_month=await agg.count_user_messages_since(session, ids, month_start),
        documents_total=await agg.count_documents(session, ids),
        upcoming_7d=len(upcoming_all),
        pending_confirmations=await agg.count_pending(session, ids))

    # ── thẻ thành viên ──
    counts = await agg.confirmed_record_counts(session, ids)
    alerts = await agg.confirmed_alerts(session, ids)
    today = now.date()
    cards = []
    for m in members:
        if m.id not in ids:
            cards.append(MemberCard(id=m.id, display_name=m.display_name, member_type=m.member_type,
                                    age=_age(m.dob, today), avatar_updated_at=m.avatar_updated_at,
                                    health_visible=False))
            continue
        mine = [a for a in alerts if a.member_id == m.id]
        cards.append(MemberCard(
            id=m.id, display_name=m.display_name, member_type=m.member_type, age=_age(m.dob, today),
            avatar_updated_at=m.avatar_updated_at, health_visible=True, confirmed_records=counts.get(m.id, 0),
            allergies=[_label(a) for a in mine if a.kind == RecordKind.ALLERGY],
            conditions=[_label(a) for a in mine if a.kind == RecordKind.CONDITION]))

    # ── timeline ──
    items = [TimelineItem(at=d.created_at, member_id=d.member_id, member_name=by_id[d.member_id].display_name,
                          kind="document_uploaded", label="Tải lên tài liệu")
             for d in await agg.recent_documents(session, ids, TIMELINE_LIMIT)]
    items += [TimelineItem(at=r.confirmed_at, member_id=r.member_id, member_name=by_id[r.member_id].display_name,
                           kind="record_confirmed", label=f"{r.kind.value}: {_label(r)}")
              for r in await agg.recent_confirmed_records(session, ids, TIMELINE_LIMIT)]
    items.sort(key=lambda x: x.at, reverse=True)

    # ── lịch sắp tới ──
    upcoming = [UpcomingItem(at=t, member_id=m.id, member_name=m.display_name, title=ev.title, type=ev.type)
                for t, ev, m in upcoming_all[:UPCOMING_LIMIT]]

    return DashboardOut(summary=summary, members=cards, timeline=items[:TIMELINE_LIMIT], upcoming=upcoming)