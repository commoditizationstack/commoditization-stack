"""Four canonical valuation methods + the inverted Damodaran key-person discount.

Implements:
  - Berkus method (Berkus, 2016) - pre-revenue qualitative scoring.
  - Venture Capital method - exit projection discounted at target IRR.
  - Comparable-firm multiples - revenue multiple with AI-integration noise.
  - Damodaran narrative-and-numbers (2009, 2017, 2023) with:
      * standard key-person discount (10-25% downward adjustment)
      * INVERTED key-person discount (paper section 6.4, original contribution)

The inverted discount is the central original contribution. When the technical
team's tasks lie predominantly inside the jagged frontier (layer 4), the team
size transitions from positive signal of capability to negative signal of
legacy cost overhang. The discount can flip in sign.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
import numpy as np


@dataclass
class ValuationResult:
    method: str
    point_estimate_usd: float
    low_usd: float
    high_usd: float
    components: Dict[str, float]
    notes: str = ""

    def __repr__(self) -> str:
        return (f"ValuationResult({self.method}, "
                f"${self.point_estimate_usd:,.0f} "
                f"[${self.low_usd:,.0f}-${self.high_usd:,.0f}])")


def berkus_valuation(
    factor_scores: Dict[str, float],
    factor_cap_usd: float,
    factor_weights: Dict[str, float],
    prototype_signal_decay_2026: float = 0.55,
) -> ValuationResult:
    """Berkus (2016) method, with optional decay of the prototype factor."""
    components = {}
    for f in ["sound_idea", "prototype", "quality_team",
              "strategic_relationships", "product_rollout"]:
        score = float(factor_scores.get(f, 0.0))
        weight = float(factor_weights.get(f, 1.0))
        decay = prototype_signal_decay_2026 if f == "prototype" else 1.0
        components[f] = score * weight * decay * factor_cap_usd

    total = sum(components.values())
    return ValuationResult(
        method="berkus",
        point_estimate_usd=total,
        low_usd=total * 0.7,
        high_usd=total * 1.3,
        components=components,
        notes=f"Prototype factor decay applied: {prototype_signal_decay_2026:.2f}",
    )


def vc_method_valuation(
    projected_exit_revenue_usd: float,
    exit_multiple: float,
    target_irr: float,
    hold_period_years: float,
    expected_dilution: float,
) -> ValuationResult:
    """VC method: project exit, discount at target IRR, adjust for dilution."""
    exit_value = projected_exit_revenue_usd * exit_multiple
    discount_factor = (1.0 + target_irr) ** hold_period_years
    discounted = exit_value / discount_factor
    post_money = discounted * (1.0 - expected_dilution)

    return ValuationResult(
        method="vc_method",
        point_estimate_usd=post_money,
        low_usd=post_money * 0.6,
        high_usd=post_money * 1.4,
        components={
            "exit_value": exit_value,
            "discount_factor": discount_factor,
            "discounted_pre_dilution": discounted,
            "post_money": post_money,
        },
        notes=f"IRR={target_irr:.0%}, hold={hold_period_years}y, dilution={expected_dilution:.0%}",
    )


def comparable_multiple_valuation(
    arr_usd: float,
    revenue_multiple: float,
    multiple_volatility: float = 0.0,
    rng: Optional[np.random.Generator] = None,
) -> ValuationResult:
    """Revenue multiple with optional log-normal noise (post-2023 heterogeneity)."""
    if multiple_volatility > 0 and rng is not None:
        noise = np.exp(rng.normal(0, multiple_volatility))
        effective_multiple = revenue_multiple * noise
    else:
        effective_multiple = revenue_multiple

    valuation = arr_usd * effective_multiple

    return ValuationResult(
        method="comparable_multiples",
        point_estimate_usd=valuation,
        low_usd=arr_usd * revenue_multiple * np.exp(-multiple_volatility),
        high_usd=arr_usd * revenue_multiple * np.exp(+multiple_volatility),
        components={
            "arr_usd": arr_usd,
            "base_multiple": revenue_multiple,
            "effective_multiple": effective_multiple,
            "volatility": multiple_volatility,
        },
        notes="Multiple volatility reflects AI-integration heterogeneity in peer set.",
    )


def damodaran_classical_discount(
    enterprise_value_usd: float,
    key_person_discount_rate: float = 0.175,
) -> Tuple[float, Dict]:
    """Standard Damodaran key-person discount (2009, 2017, 2023)."""
    discount_amount = enterprise_value_usd * key_person_discount_rate
    discounted = enterprise_value_usd - discount_amount
    return discounted, {
        "enterprise_value": enterprise_value_usd,
        "discount_rate": key_person_discount_rate,
        "discount_amount": discount_amount,
        "discounted_value": discounted,
        "sign": "negative (classical)",
    }


def damodaran_inverted_discount(
    enterprise_value_usd: float,
    team_layer4_share: float,
    ai_substitution_potential_layer4: float,
    threshold_layer4_share: float = 0.55,
    classical_discount_rate: float = 0.175,
    max_premium_when_inverted: float = 0.15,
) -> Tuple[float, Dict]:
    """Inverted key-person discount (de Miranda Neto, 2026, section 6.4).

    Logic:
      1. If team_layer4_share <= threshold: classical discount applies.
      2. If team_layer4_share > threshold AND ai_substitution_potential_layer4
         is high: the discount inverts in sign. Large technical team becomes
         negative signal of legacy cost overhang.

    This is a *theoretical possibility*, not a documented empirical regularity.
    """
    above_threshold = max(0.0, team_layer4_share - threshold_layer4_share)
    threshold_excess = above_threshold / max(1e-6, 1.0 - threshold_layer4_share)

    if team_layer4_share <= threshold_layer4_share:
        discount_rate = classical_discount_rate
        sign = "negative (classical)"
        adjustment = -enterprise_value_usd * discount_rate
        regime = "classical"
    else:
        inversion_strength = threshold_excess * ai_substitution_potential_layer4
        effective_rate = (
            classical_discount_rate * (1.0 - inversion_strength)
            - max_premium_when_inverted * inversion_strength
        )
        discount_rate = effective_rate
        sign = ("inverted (toward premium for acquirer)"
                if effective_rate < 0 else "reduced (classical, near-flip)")
        adjustment = -enterprise_value_usd * discount_rate
        regime = "inverted"

    adjusted_value = enterprise_value_usd + adjustment

    return adjusted_value, {
        "enterprise_value": enterprise_value_usd,
        "team_layer4_share": team_layer4_share,
        "threshold": threshold_layer4_share,
        "ai_substitution_potential": ai_substitution_potential_layer4,
        "effective_discount_rate": discount_rate,
        "adjustment_usd": adjustment,
        "adjusted_value": adjusted_value,
        "sign": sign,
        "regime": regime,
    }


def damodaran_full_valuation(
    revenue_projection_usd: List[float],
    discount_rate: float,
    terminal_growth: float,
    terminal_multiple: float,
    team_layer4_share: float,
    ai_substitution_potential_layer4: float,
    use_inverted_discount: bool = True,
    threshold_layer4_share: float = 0.55,
    classical_discount_rate: float = 0.175,
    max_premium_when_inverted: float = 0.15,
) -> ValuationResult:
    """Full Damodaran-style DCF + key-person discount (classical or inverted)."""
    pv = 0.0
    for t, rev in enumerate(revenue_projection_usd, start=1):
        pv += rev / ((1 + discount_rate) ** t)
    terminal_revenue = revenue_projection_usd[-1] * (1 + terminal_growth)
    terminal_value = terminal_revenue * terminal_multiple
    pv_terminal = terminal_value / ((1 + discount_rate) ** len(revenue_projection_usd))

    enterprise_value = pv + pv_terminal

    if use_inverted_discount:
        adjusted, components = damodaran_inverted_discount(
            enterprise_value, team_layer4_share, ai_substitution_potential_layer4,
            threshold_layer4_share, classical_discount_rate, max_premium_when_inverted,
        )
    else:
        adjusted, components = damodaran_classical_discount(
            enterprise_value, classical_discount_rate,
        )

    components["pv_explicit"] = pv
    components["pv_terminal"] = pv_terminal

    return ValuationResult(
        method=("damodaran_inverted" if use_inverted_discount else "damodaran_classical"),
        point_estimate_usd=adjusted,
        low_usd=adjusted * 0.65,
        high_usd=adjusted * 1.35,
        components=components,
        notes=(f"Regime: {components.get('regime', 'classical')}; "
               f"sign: {components['sign']}"),
    )
