from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .database import get_async_session
from .utils.security import decode_token
from .models.user import User
from .services.llm import LlmClient, OpenAiClient
import httpx

async def get_llm_client() -> LlmClient:
    async with httpx.AsyncClient() as client:
        yield OpenAiClient(http_client=client)

async def get_db() -> AsyncSession:
    async for s in get_async_session():
        yield s

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")
    token = auth.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = int(payload.get("sub"))
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    # MVP: user id 1 is admin
    if user.id != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


