from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from product.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from product.apps.api.auth.deps import get_current_user
from .schemas import FamilyMemberIn, FamilyOut, FamilyMemberOut, ConnectionOut, ConnectionRequestIn, AttachConnectionIn
from . import service
from .permissions import can_write_member


router = APIRouter(tags=["members"])

# Get user's family
@router.get("/families/me", response_model=FamilyOut)
async def my_family(user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        return await service.get_family_for_owner(session, user)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))

# Get user's family's members
@router.get("/families/me/members", response_model=list[FamilyMemberOut])
async def my_members(user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    family = await service.get_family_for_owner(session, user)
    return await service.list_members(session, family.id)

# Post user's family's member
@router.post("/families/me/members", response_model=FamilyMemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(data: FamilyMemberIn, user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    family = await service.get_family_for_owner(session, user)
    return await service.add_managed_member(session, family, data)

# Post connection
@router.post("/connections", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
async def request_connection(data: ConnectionRequestIn, user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        return await service.send_connection_request(session, user, data.target_email)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

# Respond connection
@router.post("/connections/{connection_id}/respond", response_model=ConnectionOut)
async def respond(connection_id: UUID, accept: bool, user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        return await service.respond_connection(session, connection_id, user, accept)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))

# Attach member
@router.post("/families/me/members/attach", response_model=FamilyMemberOut, status_code=status.HTTP_201_CREATED)
async def attach(data: AttachConnectionIn, user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    family = await service.get_family_for_owner(session, user)
    try:
        return await service.attach_connection_as_member(session, family, user, data.connection_id, data.member_type)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

# Incoming members
@router.post("/connections/incoming", response_model=list[ConnectionOut])
async def incoming_connections(user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await service.list_incoming_connections(session, user)