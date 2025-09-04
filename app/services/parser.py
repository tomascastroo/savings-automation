from dataclasses import dataclass
from typing import Any, Optional
import re
from datetime import datetime

@dataclass
class ParsedBill:
    period_month: str | None
    amount_due: float | None
    raw: dict

def parse_bill_text(text: str, provider_hint: str | None = None) -> ParsedBill:
    # naive extraction
    m_period = re.search(r"(20\d{2})[\-/ ]?(0[1-9]|1[0-2])", text)
    period = f"{m_period.group(1)}-{m_period.group(2)}" if m_period else None
    amounts = [float(x.replace(',', '.')) for x in re.findall(r"\b(\d+[\.,]\d{2})\b", text)]
    amount = max(amounts) if amounts else None
    return ParsedBill(period_month=period, amount_due=amount, raw={"provider_hint": provider_hint})
