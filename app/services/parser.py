from dataclasses import dataclass
from typing import List, Optional
import re
from datetime import datetime

@dataclass
class ParsedItem:
    description: str
    amount: float
    quantity: Optional[float] = None
    unit_price: Optional[float] = None

@dataclass
class ParsedBill:
    period_month: Optional[str]
    amount_due: Optional[float]
    items: List[ParsedItem]
    raw: dict

def parse_bill_text(text: str, provider_hint: Optional[str] = None) -> ParsedBill:
    """
    A simple MVP parser to extract structured data from raw OCR text.
    In a real system, this would be a sophisticated NLP or rule-based engine.
    """
    # Naive extraction for period and total amount
    m_period = re.search(r"(20\d{2})[\-/ ]?(0[1-9]|1[0-2])", text)
    period = f"{m_period.group(1)}-{m_period.group(2)}" if m_period else None

    amounts = [float(x.replace(',', '.')) for x in re.findall(r"\b(\d+[\.,]\d{2})\b", text)]
    amount_due = max(amounts) if amounts else None

    # Naive extraction for line items (lines with a description and a price)
    items = []
    # This regex looks for lines that start with some text, then have a price at the end.
    # e.g., "Cargo Fijo Mensual.... $100.00"
    item_regex = re.compile(r"^(.*?)\s+\$?\s*(\d+\.\d{2})$", re.MULTILINE)
    for match in item_regex.finditer(text):
        description = match.group(1).strip()
        # Avoid capturing the total amount as a line item
        if "total" not in description.lower():
            items.append(ParsedItem(
                description=description,
                amount=float(match.group(2))
            ))

    # If no items were found but we have a total, create a single item for it
    if not items and amount_due:
        items.append(ParsedItem(description="Total", amount=amount_due))

    return ParsedBill(
        period_month=period,
        amount_due=amount_due,
        items=items,
        raw={"provider_hint": provider_hint}
    )
