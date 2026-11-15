from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.session import get_session
from product.apps.api.auth.deps import get_current_user
from . import service
from .schemas import DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("", response_model=DashboardOut)
async def dashboard(user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        return await service.build_dashboard(session, user)
    except LookupError as e:                     # người dùng chưa có family — lỗi dữ liệu
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))