from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import select
from product.db.session import SessionLocal
from product.db.models import FamilyMember, MedicalRecord, RecordKind
from .context import member_id_from

# Get member profile => Context for LLM suggest
@tool
async def get_member_profile(config: RunnableConfig) -> str:
    member_id = member_id_from(config)
    async with SessionLocal() as s:
        member = await s.get(FamilyMember, member_id)
        records = await s.scalars(select(MedicalRecord).where(
            MedicalRecord.member_id == member_id,
            MedicalRecord.confirmed_at.is_not(None)
        ))
        lines = [f"Tên: {member.display_name} | Quan hệ: {member.member_type.value} | Ngày sinh: {member.dob or 'chưa rõ'}"]
        lines += [f"- {r.kind.value}: {r.payload}" for r in records]
    return "\n".join(lines) if len(lines) > 1 else lines[0] + "\nChưa có mục y tế nào được xác nhận."

# Propose medical record
@tool
async def propose_medical_record(kind: RecordKind, details: dict[str, str], config: RunnableConfig) -> str:
    """Only write if user accept medical record suggested"""
    async with SessionLocal() as s:
        rec = MedicalRecord(member_id=member_id_from(config), kind=kind, payload=details, confirmed_at=None)
        s.add(rec)
        await s.commit()
        await s.refresh(rec)
    return (f"Đã tạo đề xuất {rec.id} ({kind.value}: {details}). CHƯA lưu chính thức. "
            "Hãy nói người dùng kiểm tra lại và bấm xác nhận; không được nói là đã lưu.")