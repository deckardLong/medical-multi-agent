from uuid import UUID
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import select
from product.db.session import SessionLocal
from product.db.models import FamilyMember, MedicalRecord, RecordKind
from .context import member_id_from

_KIND_LABEL = {
    RecordKind.ALLERGY: "DỊ ỨNG (đã xác nhận — không được khuyên dùng chất này hoặc thuốc cùng nhóm)",
    RecordKind.CONDITION: "Bệnh nền",
    RecordKind.MEDICATION: "Thuốc đang dùng",
    RecordKind.LAB_RESULT: "Kết quả xét nghiệm",
}


def _payload_text(payload: dict) -> str:
    return ", ".join(str(v) for v in payload.values() if v not in (None, ""))


async def _confirmed_records(s, member_id: UUID) -> list[MedicalRecord]:
    return list(await s.scalars(select(MedicalRecord).where(
        MedicalRecord.member_id == member_id, MedicalRecord.confirmed_at.is_not(None))))


async def member_allergies(member_id: UUID) -> list[str]:
    async with SessionLocal() as s:
        return [_payload_text(r.payload) for r in await _confirmed_records(s, member_id)
                if r.kind == RecordKind.ALLERGY]


async def member_profile_text(member_id: UUID) -> str:
    async with SessionLocal() as s:
        member = await s.get(FamilyMember, member_id)
        if member is None:
            return "Không tìm thấy hồ sơ thành viên."
        records = await _confirmed_records(s, member_id)
    lines = [f"Tên: {member.display_name} | Quan hệ: {member.member_type.value} | Ngày sinh: {member.dob or 'chưa rõ'}"]
    lines += [f"- {_KIND_LABEL[r.kind]}: {_payload_text(r.payload)}" for r in records]
    return "\n".join(lines) if len(lines) > 1 else lines[0] + "\nChưa có mục y tế nào được xác nhận."

# Get member profile => Context for LLM suggest
@tool
async def get_member_profile(config: RunnableConfig) -> str:
    """Lấy hồ sơ của thành viên đang được tư vấn: tên, quan hệ, ngày sinh và các mục y tế đã xác nhận
    (bệnh nền, thuốc đang dùng, dị ứng, xét nghiệm). Gọi trước khi đưa ra lời khuyên cho người này."""
    return await member_profile_text(member_id_from(config))

# Propose medical record
@tool
async def propose_medical_record(kind: RecordKind, details: dict[str, str], config: RunnableConfig) -> str:
    """Tạo ĐỀ XUẤT một mục hồ sơ (bệnh nền, thuốc, dị ứng, xét nghiệm) từ điều người dùng nói — chưa có hiệu lực cho
    tới khi người dùng bấm Xác nhận. Giá trị chưa chắc: ghi các khả năng kèm "(cần kiểm tra)"."""
    async with SessionLocal() as s:
        rec = MedicalRecord(member_id=member_id_from(config), kind=kind, payload=details, confirmed_at=None)
        s.add(rec)
        await s.commit()
        await s.refresh(rec)
    return (f"Đã tạo đề xuất ({kind.value}: {details}). CHƯA có hiệu lực: nhắc người dùng kiểm tra và bấm \"Xác nhận\" "
            "ở mục Hồ sơ chờ duyệt. Không nói là đã lưu, không hỏi lại trong chat có muốn lưu không.")