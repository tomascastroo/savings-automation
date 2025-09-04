from dataclasses import dataclass
from typing import Protocol
from ..config import settings
from ..utils.redis_client import get_redis

@dataclass
class ChargeResult:
    success: bool
    reference: str | None = None
    error: str | None = None

class PaymentGateway(Protocol):
    async def authorize_method(self, pm_token: str) -> bool: ...
    async def charge(self, amount: float, idempotency_key: str) -> ChargeResult: ...

class StripeGateway:
    async def authorize_method(self, pm_token: str) -> bool:
        # TODO: integrate stripe SetupIntent
        return True
    async def charge(self, amount: float, idempotency_key: str) -> ChargeResult:
        # TODO: integrate stripe PaymentIntent with idempotency key
        return ChargeResult(success=True, reference=f"stripe_{idempotency_key}")

class MercadoPagoGateway:
    async def authorize_method(self, pm_token: str) -> bool:
        # TODO: integrate MercadoPago
        return True
    async def charge(self, amount: float, idempotency_key: str) -> ChargeResult:
        return ChargeResult(success=True, reference=f"mp_{idempotency_key}")

def get_gateway() -> PaymentGateway:
    return StripeGateway() if settings.payment_gateway == "stripe" else MercadoPagoGateway()

async def idempotent_charge(amount: float, key: str) -> ChargeResult:
    r = get_redis()
    already = await r.get(f"idem:{key}")
    if already:
        return ChargeResult(success=True, reference=already)
    gw = get_gateway()
    res = await gw.charge(amount, idempotency_key=key)
    if res.success and res.reference:
        await r.set(f"idem:{key}", res.reference, ex=60*60*24)
    return res
