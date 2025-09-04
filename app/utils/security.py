from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import re
import jwt
from passlib.hash import bcrypt
from ..config import settings

def hash_password(password: str) -> str:
    return bcrypt.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.verify(password, password_hash)

def create_access_token(subject: dict[str, Any], expires_minutes: int | None = None) -> str:
    to_encode = subject.copy()
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

def mask_account(value: str) -> str:
    if not value:
        return value
    clean = re.sub(r"\D", "", value)
    if len(clean) <= 4:
        return "*" * len(clean)
    return "*" * (len(clean)-4) + clean[-4:]
