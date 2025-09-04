from dataclasses import dataclass
from typing import Protocol
from ..config import settings
from ..utils.redis_client import get_redis
from ..models.payment import Fee

@dataclass
class ChargeResult:
    success: bool
    reference: str | None = None
    error: str | None = None

@dataclass
class RefundResult:
    success: bool
    reference: str | None = None
    error: str | None = None

class PaymentGateway(Protocol):
    async def authorize_method(self, pm_token: str) -> bool: ...
    async def charge(self, amount: float, idempotency_key: str) -> ChargeResult: ...
    async def refund(self, original_charge_ref: str, reason: str) -> RefundResult: ...

class StripeGateway:
    async def authorize_method(self, pm_token: str) -> bool:
        return True
    async def charge(self, amount: float, idempotency_key: str) -> ChargeResult:
        return ChargeResult(success=True, reference=f"stripe_charge_{idempotency_key}")
    async def refund(self, original_charge_ref: str, reason: str) -> RefundResult:
        # In a real scenario, this would call the Stripe API to refund the charge.
        return RefundResult(success=True, reference=f"stripe_refund_{original_charge_ref}")

class MercadoPagoGateway:
    async def authorize_method(self, pm_token: str) -> bool:
        return True
    async def charge(self, amount: float, idempotency_key: str) -> ChargeResult:
        return ChargeResult(success=True, reference=f"mp_charge_{idempotency_key}")
    async def refund(self, original_charge_ref: str, reason: str) -> RefundResult:
        return RefundResult(success=True, reference=f"mp_refund_{original_charge_ref}")

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

async def refund_charge(fee: Fee, reason: str) -> RefundResult:
    """
    Processes a refund for a given fee.
    """
    if not fee.payment_ref:
        return RefundResult(success=False, error="No original charge reference found for this fee.")

    gw = get_gateway()
    refund_res = await gw.refund(original_charge_ref=fee.payment_ref, reason=reason)
    return refund_res
