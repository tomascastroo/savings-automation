from dataclasses import dataclass

@dataclass
class OpportunityResult:
    strategy: str  # 'retention' or 'switch'
    target_pct: float

def find_opportunities(service, bill, parsed) -> OpportunityResult:
    # MVP: always retention with target 20%
    return OpportunityResult(strategy="retention", target_pct=0.2)
