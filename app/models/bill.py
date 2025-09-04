from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from ..database import Base

class Bill(Base):
    __tablename__ = "bills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("services.id"))
    period_month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    amount_due: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="ARS")
    source_file_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ocr_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
