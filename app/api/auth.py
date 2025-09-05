from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db, get_current_user
from ..services.auth import AuthService
from ..schemas.payment import PaymentSetupRequest
from ..models.payment import PaymentMethod, PaymentAuthorization
from fastapi import APIRouter, Depends
from ..dependencies import get_current_user
from ..models.user import User


router = APIRouter(prefix="/auth", tags=["auth"])

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

auth_service = AuthService()


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}

@router.post("/signup")
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.signup(db, body.email, body.password)
        return {"id": user.id, "email": user.email}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        token = await auth_service.login(db, body.email, body.password)
        return {"access_token": token, "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/payments/setup")
async def setup_payment(body: PaymentSetupRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    pm = PaymentMethod(user_id=user.id, provider=body.provider, pm_token=body.pm_token, status="active")
    db.add(pm)
    await db.flush()
    pa = PaymentAuthorization(user_id=user.id, payment_method_id=pm.id, scope="success_fee", status="authorized")
    db.add(pa)
    await db.commit()
    await db.refresh(pm)
    await db.refresh(pa)
    return {"payment_method_id": pm.id, "authorization_id": pa.id, "status": pa.status}
