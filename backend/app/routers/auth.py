from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, hash_password, verify_password
from app.db import get_db
from app.models import Clinic, User
from app.schemas import AuthResponse, LoginRequest, SignupRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _to_response(user: User, db: AsyncSession) -> AuthResponse:
    await db.commit()
    return AuthResponse(token=create_access_token(user), user=UserOut.model_validate(user))


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.phone == body.phone))
    if existing:
        raise HTTPException(status_code=409, detail="Phone already registered")
    clinic = Clinic(name=body.clinic_name)
    db.add(clinic)
    await db.flush()
    user = User(
        clinic_id=clinic.id,
        name=body.name,
        role="doctor",
        phone=body.phone,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    return await _to_response(user, db)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.phone == body.phone))
    if not user or not verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=401, detail="Invalid phone or password")
    return await _to_response(user, db)
