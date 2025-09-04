from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pathlib import Path
import aiofiles

from ..dependencies import get_db, get_current_user
from ..models.bill import Bill
from ..models.bill_item import BillItem
from ..models.payment import Service
from ..services.ocr import TesseractOcrEngine
from ..services.parser import parse_bill_text
from ..schemas.bill import BillRead
from ..config import settings

router = APIRouter(prefix="/bills", tags=["bills"])

@router.post("", response_model=BillRead)
async def upload_bill(service_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    # 1. Verify service belongs to user and eagerly load the provider relationship
    query = select(Service).where(Service.id == service_id, Service.user_id == user.id).options(selectinload(Service.provider))
    svc = (await db.execute(query)).scalar_one_or_none()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    # 2. Save file to storage
    storage = Path(settings.storage_dir)
    storage.mkdir(parents=True, exist_ok=True)
    dest = storage / f"user{user.id}_svc{service_id}_{file.filename}"
    async with aiofiles.open(dest, "wb") as out:
        content = await file.read()
        await out.write(content)

    # 3. OCR + Parse
    ocr_result = await TesseractOcrEngine().extract_text(content)
    parsed_bill = parse_bill_text(ocr_result.text, svc.provider.name if svc.provider else "default")

    # 4. Create Bill record
    period = parsed_bill.period_month or "2025-01" # Fallback period
    amount = parsed_bill.amount_due or 0.0 # Fallback amount

    bill = Bill(
        service_id=service_id,
        period_month=period,
        amount_due=amount,
        currency="ARS",
        source_file_url=str(dest),
        ocr_json={"text": ocr_result.text, "pages": ocr_result.pages, "parsed": parsed_bill.raw}
    )
    db.add(bill)
    await db.flush() # Flush to get the bill.id for the items

    # 5. Create BillItem records from parsed data
    for item in parsed_bill.items:
        bill_item = BillItem(
            bill_id=bill.id,
            description=item.description,
            amount=item.amount,
            quantity=item.quantity,
            unit_price=item.unit_price
        )
        db.add(bill_item)

    await db.commit()
    await db.refresh(bill)

    return bill
    
@router.get("/{bill_id}", response_model=BillRead)
async def get_bill(bill_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    bill = await db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Not found")
    # TODO: Validate that the user requesting the bill owns it via the service.
    return bill
