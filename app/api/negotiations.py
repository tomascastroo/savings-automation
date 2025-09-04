from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime

from ..dependencies import get_db, get_current_user
from ..models.bill import Bill
from ..models.payment import Service, NegotiationStatus, NegotiationStrategy, PaymentStatus, Saving, Fee
from ..models.negotiation import Negotiation
from ..schemas.negotiation import NegotiateRequest, NegotiationRead, ConfirmRequest
from ..services.opportunity import find_opportunities
from ..services.rate_limit import enforce_rate_limit
from ..services.payment import idempotent_charge
from ..config import settings

router = APIRouter(prefix="", tags=["negotiations"])

@router.post("/services/{service_id}/negotiate", response_model=NegotiationRead, status_code=status.HTTP_201_CREATED)
async def negotiate(service_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    svc = await db.scalar(select(Service).where(Service.id == service_id, Service.user_id == user.id))
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    # Rate-limit per provider account
    key = f"prov:{svc.provider_id}:acct:{svc.provider_acct}:user:{user.id}"
    await enforce_rate_limit(key, ttl_seconds=60*60*24*settings.negotiation_rate_limit_days)

    # Get latest bill
    bill = await db.scalar(select(Bill).where(Bill.service_id == service_id).order_by(Bill.created_at.desc()))
    if not bill:
        raise HTTPException(status_code=400, detail="No bills for this service")

    # Find opportunities
    opportunities = await find_opportunities(db, svc, bill)
    if not opportunities:
        raise HTTPException(status_code=404, detail="No savings opportunities found for this bill.")

    # For MVP, we'll just pick the first (and best) opportunity
    best_opp = opportunities[0]

    # For a real system, this would trigger a bot. For MVP, we create the negotiation record directly.
    neg = Negotiation(
        bill_id=bill.id,
        strategy=NegotiationStrategy[best_opp.strategy],
        status=NegotiationStatus.proposed,
        initial_amount=bill.amount_due,
        # For a "switch_plan" strategy, the new_amount is known. For "retention", it's unknown until confirmed.
        new_amount=bill.amount_due - best_opp.potential_saving if best_opp.strategy == "switch_plan" else None,
        discount_abs=best_opp.potential_saving,
        transcript_json={"opportunity_details": best_opp.details}
    )
    db.add(neg)
    await db.commit()
    await db.refresh(neg)

    return neg

@router.post("/negotiations/{neg_id}/confirm", status_code=status.HTTP_201_CREATED)
async def confirm(neg_id: int, body: ConfirmRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    neg = await db.get(Negotiation, neg_id)
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    # TODO: Check that the user owns this negotiation via the bill and service.
    if neg.status != NegotiationStatus.proposed:
        raise HTTPException(status_code=400, detail="Negotiation is not in a confirmable state.")

    neg.status = NegotiationStatus.accepted
    neg.new_amount = body.new_amount
    neg.discount_abs = neg.initial_amount - body.new_amount
    neg.discount_pct = (neg.discount_abs / neg.initial_amount) if neg.initial_amount else 0
    neg.valid_until = body.valid_until or (datetime.now() + timedelta(days=365))

    # Create saving & fee
    saving = Saving(negotiation_id=neg.id, user_id=user.id, saving_amount=neg.discount_abs, saving_period_m=12)
    db.add(saving)
    await db.flush()

    fee_amount = round(saving.saving_amount * settings.success_fee_percentage, 2)
    fee = Fee(saving_id=saving.id, percent=settings.success_fee_percentage, fee_amount=fee_amount)
    db.add(fee)
    await db.commit()
    await db.refresh(fee)

    # Charge idempotently
    idem_key = f"fee:{fee.id}"
    result = await idempotent_charge(amount=fee.fee_amount, key=idem_key)
    if result.success:
        fee.payment_status = PaymentStatus.paid
        fee.payment_ref = result.reference
    else:
        fee.payment_status = PaymentStatus.failed
    await db.commit()
    await db.refresh(fee)

    return {"fee_id": fee.id, "fee_amount": fee.fee_amount, "payment_status": fee.payment_status.value, "payment_ref": fee.payment_ref}
