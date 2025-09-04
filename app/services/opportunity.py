from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.payment import Service
from app.models.bill import Bill
from app.models.provider_plan import ProviderPlan

@dataclass
class Opportunity:
    strategy: str  # 'switch_plan' or 'retention'
    potential_saving: float
    target_plan_id: int | None = None
    details: str = ""

async def find_opportunities(db: AsyncSession, service: Service, bill: Bill) -> list[Opportunity]:
    """
    Analyzes a bill against available provider plans to find savings opportunities.
    """
    opportunities = []

    # 1. Opportunity to switch to a cheaper plan from the same provider
    query = select(ProviderPlan).where(
        ProviderPlan.provider_id == service.provider_id,
        ProviderPlan.category == service.category,
        ProviderPlan.active == True,
        ProviderPlan.price < bill.amount_due
    ).order_by(ProviderPlan.price.asc())

    cheaper_plans = (await db.execute(query)).scalars().all()

    for plan in cheaper_plans:
        potential_saving = bill.amount_due - plan.price
        opportunities.append(Opportunity(
            strategy="switch",
            potential_saving=potential_saving,
            target_plan_id=plan.id,
            details=f"Switch to plan '{plan.name}' for ${plan.price} and save ${potential_saving:.2f}/month."
        ))

    # 2. Fallback: Opportunity to ask for a retention discount (if no better plan is found)
    if not opportunities:
        potential_saving = bill.amount_due * 0.20  # Default 20% retention goal
        opportunities.append(Opportunity(
            strategy="retention",
            potential_saving=potential_saving,
            details=f"No cheaper plans found. Attempting to negotiate a 20% retention discount."
        ))

    return opportunities
