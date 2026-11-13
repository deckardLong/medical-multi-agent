from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import Document, MedicalRecord, RecordKind
from product.apps.api.errors import ConflictError
from .schemas import StatusFilter

# Trường mà các lần đọc ảnh không thống nhất được ghi "250 mg | 25 mg (cần kiểm tra)"; system prompt dùng đúng chuỗi này
UNRESOLVED = "(cần kiểm tra)"


def has_unresolved(value: Any) -> bool:
    if isinstance(value, str):
        return UNRESOLVED in value
    if isinstance(value, dict):
        return any(has_unresolved(v) for v in value.values())
    if isinstance(value, list):
        return any(has_unresolved(v) for v in value)
    return False


async def _get(session: AsyncSession, member_id: UUID, record_id: UUID) -> MedicalRecord:
    rec = await session.get(MedicalRecord, record_id)
    if rec is None or rec.member_id != member_id:      # mục của member khác cũng là "không tìm thấy"
        raise LookupError("Không tìm thấy mục hồ sơ")
    return rec


async def list_records(session: AsyncSession, member_id: UUID, status_filter: StatusFilter) -> list[MedicalRecord]:
    q = select(MedicalRecord).where(MedicalRecord.member_id == member_id)
    if status_filter is StatusFilter.PENDING:
        q = q.where(MedicalRecord.confirmed_at.is_(None))
    elif status_filter is StatusFilter.CONFIRMED:
        q = q.where(MedicalRecord.confirmed_at.is_not(None))
    return list(await session.scalars(q.order_by(MedicalRecord.created_at.desc())))


async def create_record(session: AsyncSession, member_id: UUID, kind: RecordKind, payload: dict) -> MedicalRecord:
    """Người dùng tự nhập → chính họ là nguồn thông tin nên xác nhận ngay."""
    if has_unresolved(payload):
        raise ValueError(f"Nội dung còn chứa '{UNRESOLVED}'")
    rec = MedicalRecord(member_id=member_id, kind=kind, payload=payload, confirmed_at=datetime.now(timezone.utc))
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec


async def confirm_record(session: AsyncSession, member_id: UUID, record_id: UUID,
                         payload: dict | None) -> MedicalRecord:
    rec = await _get(session, member_id, record_id)
    if rec.confirmed_at is not None:
        raise ConflictError("Mục này đã được xác nhận")
    final = payload if payload is not None else rec.payload
    # Người dùng hay bấm "Xác nhận" cho nhanh: con số chưa rõ không được lọt vào hồ sơ dùng để tư vấn
    if has_unresolved(final):
        raise ConflictError(f"Còn trường '{UNRESOLVED}': hãy gửi payload đã chọn đúng giá trị")
    rec.payload = final
    rec.confirmed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(rec)
    return rec


async def delete_record(session: AsyncSession, member_id: UUID, record_id: UUID) -> None:
    await session.delete(await _get(session, member_id, record_id))
    await session.commit()


def _field(v: dict, single_reader: bool) -> str | None:
    if v["status"] == "agree" and not single_reader:
        return v["value"]
    values = [x for x in ([v["value"]] if v["status"] == "agree" else v["values"]) if x]
    return f"{' | '.join(values)} {UNRESOLVED}" if values else None


async def propose_from_extraction(session: AsyncSession, doc: Document, result: dict) -> list[MedicalRecord]:
    """Mỗi thuốc trong kết quả đối chiếu 3 lần đọc → một đề xuất MEDICATION (chờ xác nhận), gắn với ảnh gốc.
    Đọc lại cùng một ảnh thì thay các đề xuất cũ chưa xác nhận của ảnh đó, không tạo trùng."""
    await session.execute(delete(MedicalRecord).where(
        MedicalRecord.source_document_id == doc.id, MedicalRecord.confirmed_at.is_(None)))
    recs = []
    for med in result.get("medications", []) if result.get("status") in ("agree", "needs_review") else []:
        single = med["seen_by"] < 2            # chỉ 1 lần đọc thấy → mọi trường đều chưa được kiểm chứng
        payload = {f: _field(med[f], single) for f in ("name", "dose", "frequency", "duration")}
        payload = {k: v for k, v in payload.items() if v is not None}
        if payload.get("name"):
            recs.append(MedicalRecord(member_id=doc.member_id, kind=RecordKind.MEDICATION, payload=payload,
                                      source_document_id=doc.id, confirmed_at=None))
    session.add_all(recs)
    await session.commit()
    return recs
