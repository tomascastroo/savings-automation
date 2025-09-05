# app/services/auth.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.user import User
from ..utils.security import hash_password, verify_password, create_access_token
from ..config import settings  # 👈 añadimos settings
import os

def _admin_set() -> set[str]:
    """
    Devuelve el conjunto de emails admin en minúsculas.
    Soporta:
      - settings.admin_emails (property que retorna set)
      - settings.admin_emails_raw (string crudo)
      - variable de entorno ADMIN_EMAILS
    """
    # 1) property preparada (preferida)
    prop = getattr(settings, "admin_emails", None)
    if isinstance(prop, (set, list, tuple)):
        return {str(x).strip().lower() for x in prop}

    # 2) string crudo desde settings o env
    raw = getattr(settings, "admin_emails_raw", None)
    if not raw:
        raw = os.getenv("ADMIN_EMAILS", "")

    return {e.strip().lower() for e in raw.split(",") if e.strip()}

class AuthService:
    async def signup(self, db: AsyncSession, email: str, password: str) -> User:
        email_norm = email.strip().lower()  # 👈 normalizamos
        existing = await db.scalar(select(User).where(User.email == email_norm))
        if existing:
            raise ValueError("Email already registered")
        user = User(email=email_norm, password_hash=hash_password(password))
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def login(self, db: AsyncSession, email: str, password: str) -> str:
        email_norm = email.strip().lower()  # 👈 normalizamos
        user = await db.scalar(select(User).where(User.email == email_norm))
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")

        admins = _admin_set()
        role = "admin" if email_norm in admins else "user"  # 👈 asignamos rol
        token = create_access_token({"sub": str(user.id), "email": user.email, "role": role})
        return token