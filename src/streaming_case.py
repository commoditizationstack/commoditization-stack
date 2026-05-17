"""Streaming case under jurisdictional substitution (Appendix D).

Reference firm: global streamer at scale of segment leader, May 2026 calibration.
Models the price decomposition under three substitution scenarios (40/60/78%)
and the cross-jurisdictional price-competition geometry (Fig D.2, D.3).

The case is parameterised in `streaming_case` section of parameters.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from . import config


@dataclass
class PriceDecomposition:
    """Per-subscription cost decomposition (USD/month)."""
    content_licensing: float
    engineering: float
    support: float
    cloud: float
    marketing: float
    g_and_a: float
    margin: float
    total: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "content_licensing": self.content_licensing,
            "engineering": self.engineering,
            "support": self.support,
            "cloud": self.cloud,
            "marketing": self.marketing,
            "g_and_a": self.g_and_a,
            "margin": self.margin,
            "total": self.total,
        }


@dataclass
class StreamingScenarioResult:
    """Result of a streaming-substitution scenario."""
    scenario_label: str
    substitution_pct: float
    incumbent: PriceDecomposition
    entrant: PriceDecomposition
    price_reduction_pct: float           # entrant price as % below incumbent
    annual_revenue_usd: float
    n_engineers: int
    n_support: int


def incumbent_price_decomposition() -> PriceDecomposition:
    """Decompose the incumbent's subscription price into cost components."""
    sc = config.load_parameters()["streaming_case"]
    price = float(sc["standard_plan_price_usd_monthly"])
    decomp = sc["cost_decomposition_pct"]
    return PriceDecomposition(
        content_licensing=price * float(decomp["content_licensing_production"]),
        engineering=price * float(decomp["engineering_technology"]),
        support=price * float(decomp["customer_support"]),
        cloud=price * float(decomp["cloud_cdn_infrastructure"]),
        marketing=price * float(decomp["marketing"]),
        g_and_a=price * float(decomp["general_administrative"]),
        margin=price * float(decomp["operating_margin"]),
        total=price,
    )


def entrant_price_decomposition(substitution_pct: float) -> PriceDecomposition:
    """AI-native entrant price decomposition under given substitution rate.

    The substitution applies to engineering and customer-support lines only;
    all other lines (content, cloud, marketing, G&A, margin) are unchanged.
    The price is reduced by the absolute savings in the two affected lines.
    """
    inc = incumbent_price_decomposition()
    sub = float(substitution_pct)
    new_eng = inc.engineering * (1.0 - sub * 0.95)        # ~95% of L4 work substitutable
    new_support = inc.support * (1.0 - sub * 0.85)        # ~85% of L4 work substitutable
    total_saving = (inc.engineering - new_eng) + (inc.support - new_support)
    new_total = inc.total - total_saving
    # Margin is held at the same fraction, so it also reduces in absolute terms
    new_margin = inc.margin * (new_total / inc.total)
    new_total = (inc.content_licensing + new_eng + new_support + inc.cloud
                 + inc.marketing + inc.g_and_a + new_margin)
    return PriceDecomposition(
        content_licensing=inc.content_licensing,
        engineering=new_eng,
        support=new_support,
        cloud=inc.cloud,
        marketing=inc.marketing,
        g_and_a=inc.g_and_a,
        margin=new_margin,
        total=new_total,
    )


def run_three_scenarios() -> List[StreamingScenarioResult]:
    """Run the three substitution scenarios (conservative/moderate/aggressive)."""
    sc = config.load_parameters()["streaming_case"]
    scenarios = sc["substitution_scenarios"]
    incumbent = incumbent_price_decomposition()
    results = []
    for label, sub_key in [
        ("conservative", "conservative_pct"),
        ("moderate", "moderate_pct"),
        ("aggressive", "aggressive_pct"),
    ]:
        sub = float(scenarios[sub_key])
        entrant = entrant_price_decomposition(sub)
        reduction = (incumbent.total - entrant.total) / incumbent.total
        results.append(StreamingScenarioResult(
            scenario_label=label,
            substitution_pct=sub,
            incumbent=incumbent,
            entrant=entrant,
            price_reduction_pct=reduction,
            annual_revenue_usd=float(sc["annual_revenue_usd"]),
            n_engineers=int(sc["engineers_count"]),
            n_support=int(sc["support_agents_count"]),
        ))
    return results


def cross_jurisdictional_price(target_jurisdiction: str,
                                acquirer_jurisdiction: str,
                                substitution_pct: float) -> float:
    """Compute the entrant's minimum viable price under cross-jurisdictional attack.

    When target and acquirer are in different blocs, cross-bloc friction
    (default 30%) reduces the effective substitution rate.

    Returns the entrant's monthly subscription price in USD.
    """
    sc = config.load_parameters()["streaming_case"]
    friction = float(sc["cross_bloc_friction_pct"])

    # Determine if cross-bloc (any pair not equal == cross-bloc)
    effective_sub = substitution_pct
    if target_jurisdiction != acquirer_jurisdiction:
        effective_sub = substitution_pct * (1.0 - friction)

    # The entrant's price depends on its labor cost basis. Since labor costs
    # vary by acquirer jurisdiction, we scale the saving by the ratio of
    # acquirer SWE cost to US baseline.
    md = config.load_parameters()["migration_dynamics"]
    us_cost = float(md["loaded_mid_engineer_usd_year"]["united_states"])
    acquirer_cost = float(md["loaded_mid_engineer_usd_year"][acquirer_jurisdiction])
    cost_ratio = acquirer_cost / us_cost  # smaller for cheaper jurisdictions

    # Smaller cost ratio (cheaper engineers) → smaller absolute saving →
    # smaller price reduction. The entrant's price = incumbent - (saving * cost_ratio)
    entrant = entrant_price_decomposition(effective_sub)
    incumbent = incumbent_price_decomposition()
    nominal_saving = incumbent.total - entrant.total
    adjusted_saving = nominal_saving * cost_ratio
    return float(incumbent.total - adjusted_saving)
