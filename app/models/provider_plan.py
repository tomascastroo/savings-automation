# app/models/provider_plan.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, JSON, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime  # 👈 sin timezone
from ..database import Base
from .payment import ServiceCategory

class ProviderPlan(Base):
    __tablename__ = "provider_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider_id: Mapped[int] = mapped_column(Integer, ForeignKey("providers.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[ServiceCategory] = mapped_column(Enum(ServiceCategory), nullable=False)

    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ARS", nullable=False)

    details: Mapped[dict | None] = mapped_column(JSON)  # e.g., {"speed_mbps": 500, "data_gb": 100}

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # 👈
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 👈

    provider = relationship("Provider")