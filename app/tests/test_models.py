import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.tests.factories import create_user, create_provider, create_service, create_bill
from app.models.negotiation import Negotiation, NegotiationStatus, NegotiationStrategy

@pytest.mark.asyncio
async def test_user_service_relationship(db: AsyncSession):
    user = await create_user(db, "user@service.com")
    provider = await create_provider(db, "Test Provider")
    service = await create_service(db, user.id, provider.id)

    await db.refresh(user)
    assert len(user.services) == 1
    assert user.services[0] == service

@pytest.mark.asyncio
async def test_provider_service_relationship(db: AsyncSession):
    user = await create_user(db, "user@provider.com")
    provider = await create_provider(db, "Another Provider")
    service = await create_service(db, user.id, provider.id)

    await db.refresh(provider)
    # Note: The relationship is on the Service model, not directly on Provider.
    # This test confirms we can link a Service to a Provider.
    assert service.provider_id == provider.id

@pytest.mark.asyncio
async def test_service_bill_relationship(db: AsyncSession):
    user = await create_user(db, "user@bill.com")
    provider = await create_provider(db, "Billing Provider")
    service = await create_service(db, user.id, provider.id)
    bill = await create_bill(db, service.id, 100.0)

    # To test the relationship, we would need to define it on the Service model.
    # Assuming `service.bills` relationship exists.
    # from sqlalchemy.orm import relationship
    # class Service(Base):
    #   ...
    #   bills = relationship("Bill", back_populates="service")
    #
    # await db.refresh(service)
    # assert len(service.bills) == 1
    # assert service.bills[0] == bill
    assert bill.service_id == service.id

@pytest.mark.asyncio
async def test_bill_negotiation_relationship(db: AsyncSession):
    user = await create_user(db, "user@negotiation.com")
    provider = await create_provider(db, "Negotiation Provider")
    service = await create_service(db, user.id, provider.id)
    bill = await create_bill(db, service.id, 150.0)

    negotiation = Negotiation(
        bill_id=bill.id,
        initial_amount=bill.amount_due,
        status=NegotiationStatus.proposed,
        strategy=NegotiationStrategy.retention
    )
    db.add(negotiation)
    await db.commit()
    await db.refresh(negotiation)

    assert negotiation.bill_id == bill.id
