from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.provider import Provider
from app.models.payment import Service, ServiceCategory
from app.models.bill import Bill
from app.utils.security import hash_password

async def create_user(db: AsyncSession, email: str, password: str = "password", is_admin: bool = False) -> User:
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def create_provider(db: AsyncSession, name: str) -> Provider:
    provider = Provider(name=name)
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider

async def create_service(db: AsyncSession, user_id: int, provider_id: int, category: ServiceCategory = ServiceCategory.mobile, provider_acct: str = "12345") -> Service:
    service = Service(user_id=user_id, provider_id=provider_id, category=category, provider_acct=provider_acct)
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service

async def create_bill(db: AsyncSession, service_id: int, amount_due: float, period_month: str = "2024-01") -> Bill:
    bill = Bill(service_id=service_id, amount_due=amount_due, period_month=period_month)
    db.add(bill)
    await db.commit()
    await db.refresh(bill)
    return bill
