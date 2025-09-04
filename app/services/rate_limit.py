from ..utils.redis_client import get_redis
from fastapi import HTTPException, status

async def enforce_rate_limit(key: str, ttl_seconds: int) -> None:
    r = get_redis()
    # Set if not exists (1st time), else reject
    ok = await r.set(name=f"rl:{key}", value="1", ex=ttl_seconds, nx=True)
    if not ok:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded for this operation")
