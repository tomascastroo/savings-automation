from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
import aiofiles
from ..dependencies import get_db, get_current_user
from ..models.bill import Bill
from ..models.payment import Service
from ..services.ocr import TesseractOcrEngine
from ..services.parser import parse_bill_text
from ..schemas.bill import BillRead
from ..config import settings

router = APIRouter(prefix="/bills", tags=["bills"])

@router.post("")
async def upload_bill(service_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    # Verify service belongs to user
    svc = await db.scalar(select(Service).where(Service.id == service_id, Service.user_id == user.id))
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    storage = Path(settings.storage_dir)
    storage.mkdir(parents=True, exist_ok=True)
    dest = storage / f"user{user.id}_svc{service_id}_{file.filename}"
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            await out.write(chunk)

    # OCR + parse
    await file.seek(0)
    content = await file.read()
    ocr = await TesseractOcrEngine().extract_text(content)
    parsed = parse_bill_text(ocr.text, "Proveedor")
    period = parsed.period_month or "2025-01"
    amount = parsed.amount_due or 1.0

    bill = Bill(service_id=service_id, period_month=period, amount_due=amount, currency="ARS",
                source_file_url=str(dest), ocr_json={"text": ocr.text, "pages": ocr.pages, "parsed": parsed.raw})
    db.add(bill)
    await db.commit()
    await db.refresh(bill)
    return {"id": bill.id, "period_month": bill.period_month, "amount_due": bill.amount_due}
    
@router.get("/{bill_id}", response_model=BillRead)
async def get_bill(bill_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    bill = await db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Not found")
    # Optionally validate ownership via service->user
    return bill
