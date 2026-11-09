from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from .deps import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.session import get_session
from .schemas import RegisterIn, TokenOut, UserOut
from . import service

router = APIRouter(prefix="/auth", tags=["auth"])

# Register
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, session: AsyncSession = Depends(get_session)):
    try:
        user = await service.register(session, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return user

# Login
@router.post("/login", response_model=TokenOut)
async def login(form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    from .schemas import LoginIn
    try:
        token = await service.login(session, LoginIn(email=form.username, password=form.password))
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
    return TokenOut(access_token=token)

# Get me
@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return user