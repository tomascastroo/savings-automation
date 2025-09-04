from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, Float, UniqueConstraint, JSON, Numeric
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
import enum
from ..database import Base

class ServiceCategory(str, enum.Enum):
    mobile = "mobile"
    internet = "internet"
    tv = "tv"
    energy = "energy"
    water = "water"
    gas = "gas"

class NegotiationStatus(str, enum.Enum):
    proposed = "proposed"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"

class NegotiationStrategy(str, enum.Enum):
    retention = "retention"
    switch = "switch"

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"

class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    provider_id: Mapped[int] = mapped_column(Integer, ForeignKey("providers.id"))
    category: Mapped[ServiceCategory] = mapped_column(Enum(ServiceCategory), nullable=False)
    provider_acct: Mapped[str] = mapped_column(String(128), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="services")
    provider = relationship("Provider")

class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # stripe|mp
    pm_token: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="payment_methods")

class PaymentAuthorization(Base):
    __tablename__ = "payment_authorizations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    payment_method_id: Mapped[int] = mapped_column(Integer, ForeignKey("payment_methods.id"))
    scope: Mapped[str] = mapped_column(String(64))  # e.g., "success_fee"
    status: Mapped[str] = mapped_column(String(32), default="authorized")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Saving(Base):
    __tablename__ = "savings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    negotiation_id: Mapped[int] = mapped_column(Integer, ForeignKey("negotiations.id"), unique=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    saving_amount: Mapped[float] = mapped_column(Float, nullable=False)
    saving_period_m: Mapped[int] = mapped_column(Integer, default=12)
    confirmed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class Fee(Base):
    __tablename__ = "fees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    saving_id: Mapped[int] = mapped_column(Integer, ForeignKey("savings.id"), unique=True)
    percent: Mapped[float] = mapped_column(Float, default=0.2)
    fee_amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending)
    payment_ref: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(64))
    data_before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    data_after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
