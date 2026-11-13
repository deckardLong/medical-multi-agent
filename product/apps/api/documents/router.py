from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import FamilyMember
from product.db.session import get_session
from product.apps.api.members.deps import readable_member, writable_member
from . import service
from .schemas import DocumentOut

router = APIRouter(prefix="/members/{member_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload(file: UploadFile = File(...), member: FamilyMember = Depends(writable_member),
                 session: AsyncSession = Depends(get_session)):
    """Tải ảnh đơn thuốc lên; dùng `id` trả về trong `document_ids` khi gửi tin nhắn chat."""
    try:
        return await service.save_upload(session, member.id, file)
    except service.InvalidUpload as e:
        code = status.HTTP_413_CONTENT_TOO_LARGE if e.too_large else status.HTTP_400_BAD_REQUEST
        raise HTTPException(code, str(e))


@router.get("", response_model=list[DocumentOut])
async def list_documents(member: FamilyMember = Depends(readable_member), session: AsyncSession = Depends(get_session)):
    return await service.list_documents(session, member.id)
