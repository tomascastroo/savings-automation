from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Enum, Text, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from .payment import NegotiationStatus, NegotiationStrategy
from ..database import Base

class Negotiation(Base):
    __tablename__ = "negotiations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bill_id: Mapped[int] = mapped_column(Integer, ForeignKey("bills.id"))
    strategy: Mapped[NegotiationStrategy] = mapped_column(Enum(NegotiationStrategy), default=NegotiationStrategy.retention)
    status: Mapped[NegotiationStatus] = mapped_column(Enum(NegotiationStatus), default=NegotiationStatus.proposed)
    initial_amount: Mapped[float] = mapped_column(Float, nullable=False)
    new_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_abs: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    transcript_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # --- LLM Generated Fields ---
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    llm_subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_new_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    llm_target_pct: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    llm_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    llm_risks: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    llm_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
