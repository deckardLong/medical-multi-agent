from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import FamilyMember
from product.db.session import get_session
from product.apps.api.members.deps import readable_member, writable_member
from . import jobs, service
from .schemas import ChatJobOut, ChatMessageOut, SendMessageIn

router = APIRouter(prefix="/members/{member_id}/chat", tags=["chat"])

@router.post("", response_model=ChatMessageOut)
async def send(data: SendMessageIn, member: FamilyMember = Depends(writable_member),
               session: AsyncSession = Depends(get_session)):
    try:
        return await service.send_message(session, member.id, data.content, data.document_ids)
    except ValueError as e:                     # document_ids không thuộc member
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.get("", response_model=list[ChatMessageOut])
async def history(member: FamilyMember = Depends(readable_member), session: AsyncSession = Depends(get_session)):
    return await service.get_history(session, member.id)


# ---------- Chạy nền + hỏi kết quả (dùng khi đi qua proxy cắt request dài, vd Cloudflare Tunnel ~100 giây) ----------
@router.post("/jobs", response_model=ChatJobOut, status_code=status.HTTP_202_ACCEPTED)
async def start_job(data: SendMessageIn, member: FamilyMember = Depends(writable_member),
                    session: AsyncSession = Depends(get_session)):
    """Trả ngay job_id; câu trả lời lấy ở GET .../chat/jobs/{job_id}."""
    try:
        await service._load_attachments(session, member.id, data.document_ids)   # sai document_ids → 400 ngay
        return jobs.start(member.id, data.content, data.document_ids)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except jobs.Busy as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))


@router.get("/jobs/{job_id}", response_model=ChatJobOut)
async def get_job(job_id: str, member: FamilyMember = Depends(readable_member)):
    job = jobs.get(member.id, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy yêu cầu (máy chủ có thể vừa khởi động lại)")
    return job
