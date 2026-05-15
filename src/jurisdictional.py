"""Jurisdictional accounting model for the inverted key-person discount.

Implements the accounting-substitution problem (de Miranda Neto, 2026, section 6.5):
when a firm replaces in-house technical labor with AI-as-a-service, the substitution
crosses an accounting category boundary. The magnitude of the inverted key-person
discount therefore depends materially on the jurisdiction in which the substitution
takes place.

Three reference jurisdictions are modeled, with parameters drawn from publicly
documented sources (links in repository README):

  - Brazil (CLT regime). Employer social charges typically add 70-90% on top of
    the gross salary (FGTS, INSS empregador, 13th salary, vacation bonus + 1/3,
    PIS/PASEP, RAT/SAT, third-party contributions). Imported SaaS services from
    foreign providers (e.g., OpenAI, Anthropic) are subject to IRRF (15%), CIDE
    (10%), and PIS/COFINS-importacao (~9.25%), adding 25-40% to the nominal USD
    cost. Termination costs include rescission compensation, FGTS multa (40% of
    accumulated FGTS), and aviso previo, typically 25-30% of annual salary.

  - France (CDI regime). Charges patronales typically add 42-45% on top of the
    salaire brut (URSSAF: maladie, vieillesse, allocations familiales, chomage,
    AGIRC-ARRCO retraite complementaire, AT/MP, etc). EU-based SaaS subject to
    domestic TVA (20%) but largely deductible for B2B; imported non-EU SaaS
    subject to TVA-importation. Termination of CDI is rigid: indemnite de
    licenciement + preavis typically 30-50% of annual salary depending on
    seniority; without economic justification, additional damages possible.

  - United States (W-2 regime). Federal payroll taxes are FICA employer match
    (7.65%) + FUTA (0.6% effective with state credit) + state SUTA (~1-3%);
    workers' comp adds another 0.3-1% for office workers. Statutory total
    typically 8-10%. Healthcare and 401k match are voluntary but competitive
    practice adds another 15-20% in tech roles. SaaS purchases are domestic
    OPEX with no import friction. Termination is at-will in most states; only
    contractual severance applies, typically 5-15% of annual salary.

All multipliers are documented and editable via the jurisdiction YAML.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import numpy as np


@dataclass
class JurisdictionParameters:
    """Fiscal-accounting parameters for a single jurisdiction."""
    name: str
    # Total cost of labor as multiplier on base salary
    # Brazil ~1.80, France ~1.42, US ~1.25
    labor_cost_multiplier: float
    # Termination cost as fraction of annual base salary
    # Brazil ~0.25, France ~0.40, US ~0.10
    termination_cost_fraction: float
    # Cost overhead on imported AI services (foreign SaaS)
    # Brazil ~1.30 (IRRF + CIDE + PIS/COFINS-imp), France ~1.20 (TVA),
    # US ~1.00 (domestic for most providers)
    ai_service_overhead: float
    # Required notice period as fraction of annual base salary (additional to termination)
    notice_period_fraction: float = 0.0
    # Whether AI services qualify for full tax deduction in the year of expense
    ai_opex_deductibility: float = 1.0
    # WACC adjustment for vendor concentration risk when relying heavily on AI
    # Brazil/France with strong dependency on US frontier labs: ~+0.5 percentage points
    # US firms using domestic providers: ~+0.2 percentage points
    vendor_risk_wacc_premium: float = 0.005
    # Free-text notes for documentation
    notes: str = ""


# Reference jurisdictions — defaults are documented orders of magnitude,
# editable via YAML.
JURISDICTION_DEFAULTS: Dict[str, JurisdictionParameters] = {
    "brazil": JurisdictionParameters(
        name="Brazil (CLT)",
        labor_cost_multiplier=1.80,
        termination_cost_fraction=0.25,
        ai_service_overhead=1.30,
        notice_period_fraction=0.083,  # 1 month / 12
        ai_opex_deductibility=1.0,
        vendor_risk_wacc_premium=0.005,
        notes="CLT encargos: 70-90% on top of gross salary. Imported SaaS: "
              "IRRF 15% + CIDE 10% + PIS/COFINS-importacao 9.25%. "
              "Termination: rescissao + FGTS multa 40% + aviso previo.",
    ),
    "france": JurisdictionParameters(
        name="France (CDI)",
        labor_cost_multiplier=1.42,
        termination_cost_fraction=0.40,
        ai_service_overhead=1.20,
        notice_period_fraction=0.167,  # 2 months
        ai_opex_deductibility=1.0,
        vendor_risk_wacc_premium=0.005,
        notes="Charges patronales: 42-45% sur salaire brut. CDI termination "
              "rigide: indemnite de licenciement + preavis. Imported non-EU "
              "SaaS subject to TVA-importation 20%.",
    ),
    "united_states": JurisdictionParameters(
        name="United States (W-2)",
        labor_cost_multiplier=1.25,
        termination_cost_fraction=0.10,
        ai_service_overhead=1.00,
        notice_period_fraction=0.0,
        ai_opex_deductibility=1.0,
        vendor_risk_wacc_premium=0.002,
        notes="FICA match 7.65% + FUTA 0.6% + SUTA 1-3% + workers comp + "
              "voluntary healthcare/401k ~15-20%. At-will termination: "
              "contractual severance only.",
    ),
}


@dataclass
class AccountingSubstitutionResult:
    """Decomposition of value from substituting in-house labor with AI services."""
    jurisdiction: str
    employees_replaced: int
    avg_base_salary_usd: float
    # Costs eliminated
    annual_labor_cost_eliminated_usd: float  # incl. employer charges
    one_time_termination_cost_usd: float
    # Costs added
    annual_ai_service_cost_usd: float        # incl. import/tax overhead
    # Net effect on enterprise value (DCF-like)
    net_annual_savings_usd: float
    npv_substitution_usd: float
    # Breakdown for transparency
    components: Dict[str, float] = field(default_factory=dict)
    notes: str = ""


def compute_accounting_substitution(
    n_employees_replaced: int,
    avg_base_salary_usd: float,
    annual_ai_cost_per_replaced_employee_usd: float,
    jurisdiction: JurisdictionParameters,
    discount_rate: float = 0.12,
    horizon_years: int = 5,
) -> AccountingSubstitutionResult:
    """Compute the net present value of substituting in-house labor with AI services
    in a given jurisdiction.

    Parameters
    ----------
    n_employees_replaced : int
        Number of in-house technical employees substituted by AI tooling.
    avg_base_salary_usd : float
        Average gross/base annual salary of replaced employees, in USD.
    annual_ai_cost_per_replaced_employee_usd : float
        Nominal annual cost of AI tooling per replaced employee (e.g., subscription
        + token consumption + monitoring). Before jurisdictional overhead.
    jurisdiction : JurisdictionParameters
        Jurisdiction-specific fiscal-accounting parameters.
    discount_rate : float
        Discount rate for NPV calculation. Will be augmented by vendor risk premium.
    horizon_years : int
        Horizon over which to compute the NPV of recurring savings.
    """
    j = jurisdiction

    # Costs eliminated (annual recurring + one-time termination)
    annual_labor_cost_eliminated = (
        n_employees_replaced
        * avg_base_salary_usd
        * j.labor_cost_multiplier
    )
    one_time_termination = (
        n_employees_replaced
        * avg_base_salary_usd
        * (j.termination_cost_fraction + j.notice_period_fraction)
    )

    # Costs added (annual recurring AI services with jurisdictional overhead)
    annual_ai_cost = (
        n_employees_replaced
        * annual_ai_cost_per_replaced_employee_usd
        * j.ai_service_overhead
    )

    # Net annual recurring savings
    net_annual_savings = annual_labor_cost_eliminated - annual_ai_cost

    # NPV of recurring savings minus one-time termination cost
    # Augment WACC with vendor risk premium
    effective_rate = discount_rate + j.vendor_risk_wacc_premium
    npv_recurring = sum(
        net_annual_savings / ((1 + effective_rate) ** t)
        for t in range(1, horizon_years + 1)
    )
    npv_substitution = npv_recurring - one_time_termination

    components = {
        "labor_cost_multiplier": j.labor_cost_multiplier,
        "ai_service_overhead": j.ai_service_overhead,
        "termination_cost_fraction": j.termination_cost_fraction
                                     + j.notice_period_fraction,
        "annual_labor_eliminated": annual_labor_cost_eliminated,
        "annual_ai_added": annual_ai_cost,
        "net_annual_savings": net_annual_savings,
        "npv_recurring": npv_recurring,
        "termination_one_time": one_time_termination,
        "effective_discount_rate": effective_rate,
        "vendor_risk_premium": j.vendor_risk_wacc_premium,
    }

    return AccountingSubstitutionResult(
        jurisdiction=j.name,
        employees_replaced=n_employees_replaced,
        avg_base_salary_usd=avg_base_salary_usd,
        annual_labor_cost_eliminated_usd=annual_labor_cost_eliminated,
        one_time_termination_cost_usd=one_time_termination,
        annual_ai_service_cost_usd=annual_ai_cost,
        net_annual_savings_usd=net_annual_savings,
        npv_substitution_usd=npv_substitution,
        components=components,
        notes=j.notes,
    )


def jurisdictional_inverted_discount(
    enterprise_value_usd: float,
    team_layer4_share: float,
    ai_substitution_potential_layer4: float,
    n_employees: int,
    avg_base_salary_usd: float,
    annual_ai_cost_per_replaced_employee_usd: float,
    jurisdiction: JurisdictionParameters,
    threshold_layer4_share: float = 0.55,
    classical_discount_rate: float = 0.175,
    discount_rate: float = 0.12,
    horizon_years: int = 5,
) -> Tuple[float, Dict]:
    """Jurisdictionally-aware inverted key-person discount (de Miranda Neto, 2026,
    section 6.5).

    Generalizes the basic inverted discount of section 6.4 by computing the
    inversion premium from the ground up, using jurisdiction-specific fiscal
    parameters, rather than as a fixed maximum.

    Logic:
      1. Below threshold or low substitution potential: classical discount.
      2. Above threshold: compute the actual NPV of the substitution that
         the acquirer can execute post-deal, given the jurisdictional cost
         of labor, the cost of AI services, and the cost of termination.
         Express this NPV as a fraction of the enterprise value to get the
         effective inversion premium.

    The inversion thus emerges from accounting fundamentals rather than from
    a stipulated upper bound.
    """
    above_threshold = max(0.0, team_layer4_share - threshold_layer4_share)
    threshold_excess = above_threshold / max(1e-6, 1.0 - threshold_layer4_share)
    inversion_intensity = threshold_excess * ai_substitution_potential_layer4

    if team_layer4_share <= threshold_layer4_share or ai_substitution_potential_layer4 < 0.3:
        # Classical regime: standard downward discount.
        adjustment = -enterprise_value_usd * classical_discount_rate
        adjusted = enterprise_value_usd + adjustment
        return adjusted, {
            "enterprise_value": enterprise_value_usd,
            "regime": "classical",
            "jurisdiction": jurisdiction.name,
            "effective_discount_rate": classical_discount_rate,
            "adjustment_usd": adjustment,
            "adjusted_value": adjusted,
            "inversion_premium_usd": 0.0,
            "sign": "negative (classical)",
        }

    # Inverted regime: compute substitution NPV from accounting fundamentals.
    # Acquirer can replace a fraction of the employees corresponding to the
    # team's Layer-4 share above threshold.
    n_replaceable = int(round(n_employees * inversion_intensity))

    if n_replaceable == 0:
        adjustment = -enterprise_value_usd * classical_discount_rate
        adjusted = enterprise_value_usd + adjustment
        return adjusted, {
            "enterprise_value": enterprise_value_usd,
            "regime": "classical (inversion conditions met but n_replaceable=0)",
            "jurisdiction": jurisdiction.name,
            "effective_discount_rate": classical_discount_rate,
            "adjustment_usd": adjustment,
            "adjusted_value": adjusted,
            "inversion_premium_usd": 0.0,
            "sign": "negative (classical)",
        }

    substitution = compute_accounting_substitution(
        n_employees_replaced=n_replaceable,
        avg_base_salary_usd=avg_base_salary_usd,
        annual_ai_cost_per_replaced_employee_usd=annual_ai_cost_per_replaced_employee_usd,
        jurisdiction=jurisdiction,
        discount_rate=discount_rate,
        horizon_years=horizon_years,
    )

    # Inversion premium is the substitution NPV (positive = good for acquirer).
    # The classical discount is partially attenuated by the inversion intensity.
    classical_adjustment = -enterprise_value_usd * classical_discount_rate
    classical_attenuation = 1.0 - inversion_intensity
    attenuated_classical = classical_adjustment * classical_attenuation

    # Total adjustment = attenuated classical penalty + substitution NPV (positive)
    total_adjustment = attenuated_classical + substitution.npv_substitution_usd
    adjusted_value = enterprise_value_usd + total_adjustment

    effective_rate = -total_adjustment / enterprise_value_usd if enterprise_value_usd > 0 else 0.0
    sign = ("inverted (premium for acquirer)"
            if total_adjustment > 0 else "reduced (classical, near-flip)")

    return adjusted_value, {
        "enterprise_value": enterprise_value_usd,
        "regime": "inverted",
        "jurisdiction": jurisdiction.name,
        "team_layer4_share": team_layer4_share,
        "threshold": threshold_layer4_share,
        "ai_substitution_potential": ai_substitution_potential_layer4,
        "inversion_intensity": inversion_intensity,
        "n_employees_replaceable": n_replaceable,
        "substitution_npv_usd": substitution.npv_substitution_usd,
        "annual_savings_usd": substitution.net_annual_savings_usd,
        "termination_one_time_usd": substitution.one_time_termination_cost_usd,
        "labor_cost_multiplier": jurisdiction.labor_cost_multiplier,
        "ai_service_overhead": jurisdiction.ai_service_overhead,
        "effective_discount_rate": effective_rate,
        "adjustment_usd": total_adjustment,
        "adjusted_value": adjusted_value,
        "inversion_premium_usd": substitution.npv_substitution_usd,
        "sign": sign,
    }
