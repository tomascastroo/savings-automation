from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime

from ..dependencies import get_db, get_current_user, get_llm_client, require_admin
from ..models.bill import Bill
from ..models.payment import Service, NegotiationStatus, NegotiationStrategy, PaymentStatus, Saving, Fee
from ..models.negotiation import Negotiation
from ..models.provider import Provider
from ..schemas.negotiation import (
    NegotiateRequest,
    NegotiationRead,
    ConfirmRequest,
    NegotiationMessageRead,
    RegenerateLlmMessageRequest
)
from ..services.llm import LlmClient
from ..services.opportunity import find_opportunities
from ..services.rate_limit import enforce_rate_limit
from ..services.payment import idempotent_charge
from ..config import settings

router = APIRouter(prefix="", tags=["negotiations"])

@router.post(
    "/services/{service_id}/negotiate",
    response_model=NegotiationRead,
    status_code=status.HTTP_201_CREATED
)
async def negotiate(
    service_id: int,
    request: NegotiateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    llm_client: LlmClient = Depends(get_llm_client),
):
    svc = await db.scalar(select(Service).where(Service.id == service_id, Service.user_id == user.id))
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    provider = await db.scalar(select(Provider).where(Provider.id == svc.provider_id))
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found for service")


    # Rate-limit per provider account
    key = f"neg_init:prov:{svc.provider_id}:acct:{svc.provider_acct}:user:{user.id}"
    await enforce_rate_limit(key, ttl_seconds=60 * 60 * 24 * settings.negotiation_rate_limit_days)

    # Get latest bill
    bill = await db.scalar(select(Bill).where(Bill.service_id == service_id).order_by(Bill.created_at.desc()))
    if not bill:
        raise HTTPException(status_code=400, detail="No bills for this service")

    # --- LLM Integration ---
    # 1. Determine target_pct
    opportunities = await find_opportunities(db, svc, bill)
    target_pct = request.target_pct
    if opportunities:
        best_opp = opportunities[0]
        # Adjust target_pct to be more realistic based on the best available plan
        target_pct = min(0.35, max(0.10, (bill.amount_due - best_opp.price) / bill.amount_due))

    # 2. Call LLM
    llm_message = await llm_client.generate_negotiation_message(
        provider=provider.name,
        amount=bill.amount_due,
        period=bill.period_month,
        user_id=user.id,
        target_pct=target_pct,
        channel="email", # Default channel
        context={"opportunities": [o.details for o in opportunities]} if opportunities else None,
    )

    # 3. Create Negotiation record
    neg = Negotiation(
        bill_id=bill.id,
        strategy=NegotiationStrategy[llm_message.strategy],
        status=NegotiationStatus.proposed,
        initial_amount=bill.amount_due,
        # --- LLM Fields ---
        llm_provider=llm_message.meta.get("provider"),
        llm_model=llm_message.meta.get("model"),
        llm_channel=llm_message.channel,
        llm_subject=llm_message.subject,
        llm_message=llm_message.message,
        llm_new_amount=llm_message.new_amount_suggestion,
        llm_target_pct=llm_message.target_pct,
        llm_confidence=llm_message.confidence,
        llm_risks=llm_message.risks,
        llm_meta=llm_message.meta,
    )
    db.add(neg)
    await db.commit()
    await db.refresh(neg)

    # Add preview field for response schema
    neg.llm_message_preview = neg.llm_message[:160] if neg.llm_message else None
    neg.llm_new_amount_suggestion = neg.llm_new_amount

    return neg

@router.get("/negotiations/{neg_id}/llm-message", response_model=NegotiationMessageRead)
async def get_llm_message(neg_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    neg = await db.get(Negotiation, neg_id)
    # TODO: Proper ownership check
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    return NegotiationMessageRead(
        channel=neg.llm_channel,
        subject=neg.llm_subject,
        message=neg.llm_message,
        strategy=neg.strategy.value,
        new_amount_suggestion=neg.llm_new_amount,
        target_pct=neg.llm_target_pct,
        confidence=neg.llm_confidence,
        risks=neg.llm_risks,
    )

@router.post("/negotiations/{neg_id}/llm-regenerate", response_model=NegotiationMessageRead)
async def regenerate_llm_message(
    neg_id: int,
    request: RegenerateLlmMessageRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
    llm_client: LlmClient = Depends(get_llm_client),
):
    neg = await db.get(Negotiation, neg_id)
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    bill = await db.get(Bill, neg.bill_id)
    service = await db.get(Service, bill.service_id)
    provider = await db.get(Provider, service.provider_id)

    # Call LLM with new params
    llm_message = await llm_client.generate_negotiation_message(
        provider=provider.name,
        amount=bill.amount_due,
        period=bill.period_month,
        user_id=admin.id,
        target_pct=request.target_pct or neg.llm_target_pct,
        channel=request.channel or neg.llm_channel,
        context=request.context,
    )

    # Update negotiation with new data
    neg.llm_provider = llm_message.meta.get("provider")
    neg.llm_model = llm_message.meta.get("model")
    neg.llm_channel = llm_message.channel
    neg.llm_subject = llm_message.subject
    neg.llm_message = llm_message.message
    neg.llm_new_amount = llm_message.new_amount_suggestion
    neg.llm_target_pct = llm_message.target_pct
    neg.llm_confidence = llm_message.confidence
    neg.llm_risks = llm_message.risks
    neg.llm_meta = llm_message.meta

    await db.commit()
    await db.refresh(neg)

    return NegotiationMessageRead.model_validate(neg)


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
