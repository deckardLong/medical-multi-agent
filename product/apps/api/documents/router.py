from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.session import get_session
from product.apps.api.auth.deps import get_current_user
from . import service
from .schemas import DocumentOut

router = APIRouter(prefix="/members/{member_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload(member_id: UUID, file: UploadFile = File(...), user=Depends(get_current_user),
                 session: AsyncSession = Depends(get_session)):
    """Tải ảnh đơn thuốc lên; dùng `id` trả về trong `document_ids` khi gửi tin nhắn chat."""
    try:
        return await service.save_upload(session, member_id, user, file)
    except service.InvalidUpload as e:
        code = status.HTTP_413_CONTENT_TOO_LARGE if e.too_large else status.HTTP_400_BAD_REQUEST
        raise HTTPException(code, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))


@router.get("", response_model=list[DocumentOut])
async def list_documents(member_id: UUID, user=Depends(get_current_user),
                         session: AsyncSession = Depends(get_session)):
    try:
        return await service.list_documents(session, member_id, user)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
