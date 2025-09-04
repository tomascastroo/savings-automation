from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.user import User
from ..utils.security import hash_password, verify_password, create_access_token

class AuthService:
    async def signup(self, db: AsyncSession, email: str, password: str) -> User:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing:
            raise ValueError("Email already registered")
        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def login(self, db: AsyncSession, email: str, password: str) -> str:
        user = await db.scalar(select(User).where(User.email == email))
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        token = create_access_token({"sub": str(user.id), "email": user.email, "role": "user"})
        return token
