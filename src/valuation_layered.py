"""Layered DCF valuation: extending Damodaran's narrative-and-numbers
to deep-tech firms under the seven-layer commoditization framework.

This module is the operational appendix to Section 9 of the paper
"The Cost Gradient of the Build" (de Miranda Neto, 2026). It extends
the canonical four-method valuation toolkit (`valuation.py`) by
introducing three innovations grounded in the state of the art:

1. TRL-modulated discount rate (replacing Damodaran's single rate).
   Calibration follows the Equidam methodology update of June 2025
   and the Hectelion published numerical schedule (TRL 4 ~ 18%,
   TRL 7 ~ 13%). See:
   - Equidam (2025). Deep Tech Valuation: Using Technology Readiness
     Levels. June 25, 2025.
   - Hectelion (2025). TRL as a quantifiable value-creation lever.

2. Layer-decomposed risk premium. Each of the seven layers contributes
   a separate risk premium component, with sign and magnitude that
   reflect whether the layer commoditizes (positive contribution to
   risk) or anti-commoditizes (negative contribution = protection).
   The total risk premium is therefore not a scalar but a vector
   that can be inspected and audited.

3. Double-valley perpetuity correction. Section 6.5 of the paper
   shows that post-AI deep-tech and commoditizing-tech firms exhibit
   a second valley of disillusionment around month 24-36. The
   classical Gordon perpetuity assumption (single steady state) is
   incompatible with this dynamic. We replace the single-rate
   perpetuity with a two-stage perpetuity that captures the second
   valley before convergence to terminal growth.

Damodaran's own warning in his 2009 working paper "Valuing Young,
Start-up and Growth Companies" (SSRN 1418687) is that the venture
capital approach to valuation "is flawed and should be replaced",
and that squeezing failure risk into the discount rate is a
mistake because the discount rate is "a blunt instrument that was
never intended to include failure risk" (Damodaran at the CFA
Alpha Summit, 2022). The framework of this paper takes Damodaran's
own diagnosis seriously by separating the discount-rate work
(macro + sector beta + TRL adjustment) from the failure-risk work
(handled by Monte Carlo over the layer-7 K7 coefficient and over
the AI substitutability potential of Layer 4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import numpy as np

from . import config


# ---------------------------------------------------------------------------
# TRL → discount-rate adjustment schedule
# ---------------------------------------------------------------------------
# Calibration grounded in Equidam (2025) and Hectelion (2025). The schedule
# (TRL 1..9 → premium) lives in config/parameters.yaml under
# valuation_layered.trl_discount_premium. Editing the YAML is the canonical
# way to retune.

TRL_DISCOUNT_PREMIUM: Dict[int, float] = {
    int(k): float(v)
    for k, v in config.load_parameters()["valuation_layered"]
    ["trl_discount_premium"].items()
}


def trl_premium(trl: int) -> float:
    """Return the technology-readiness premium added on top of base CAPM.

    Calibrated to Equidam (2025) and Hectelion (2025): TRL 4 ~ +10 pp,
    TRL 7 ~ +4 pp. The progression from TRL 4 to TRL 7 thus reduces
    the discount rate by approximately 6 percentage points, consistent
    with Hectelion's reported 18% → 13% trajectory under their
    Swiss medtech case.
    """
    return config.trl_discount_premium(trl)


# ---------------------------------------------------------------------------
# Layer-decomposed risk premium
# ---------------------------------------------------------------------------
# Each of the seven layers of the framework contributes a signed
# component to the firm-specific risk premium. Layers that commoditize
# rapidly contribute a positive premium (more risk because product
# differentiation erodes). Layers that anti-commoditize contribute a
# negative premium (protection: institutional embedding, judgment).
# The base coefficients here are illustrative and editable; the
# qualitative pattern (Layer 4 erodes value, Layer 6 protects) is
# the substantive content.

_DEFAULT_EXPOSURE = config.default_layer_exposure()
_EXPOSURE_TOLERANCE = float(
    config.load_parameters()["valuation_layered"]["layer_exposure_sum_tolerance"])


@dataclass
class LayerExposure:
    """Fraction of firm value exposed to each layer of the framework.

    Defaults come from config/parameters.yaml under
    valuation_layered.default_layer_exposure. Sum is validated to 1.0
    within `layer_exposure_sum_tolerance` (also configured in YAML).
    """
    layer_1_infra: float = _DEFAULT_EXPOSURE["layer_1_infra"]
    layer_2_foundation: float = _DEFAULT_EXPOSURE["layer_2_foundation"]
    layer_3_capability: float = _DEFAULT_EXPOSURE["layer_3_capability"]
    layer_4_codified: float = _DEFAULT_EXPOSURE["layer_4_codified"]
    layer_5_judgment: float = _DEFAULT_EXPOSURE["layer_5_judgment"]
    layer_6_institutional: float = _DEFAULT_EXPOSURE["layer_6_institutional"]
    layer_7_crossborder: float = _DEFAULT_EXPOSURE["layer_7_crossborder"]

    def __post_init__(self) -> None:
        s = (self.layer_1_infra + self.layer_2_foundation + self.layer_3_capability +
             self.layer_4_codified + self.layer_5_judgment + self.layer_6_institutional +
             self.layer_7_crossborder)
        if not (1.0 - _EXPOSURE_TOLERANCE <= s <= 1.0 + _EXPOSURE_TOLERANCE):
            raise ValueError(f"LayerExposure must sum to 1.0; got {s:.3f}")


# Signed per-layer risk-premium coefficients. Source of truth:
# config/parameters.yaml under valuation_layered.layer_risk_coefficients.
LAYER_RISK_COEFFICIENTS = config.layer_risk_coefficients()


def layer_decomposed_risk_premium(
    exposure: LayerExposure,
    K7: float = 1.0,
    layer4_substitution_potential: float = 0.55,
    alpha_overrides: Optional[Dict[str, float]] = None,
) -> Tuple[float, Dict[str, float]]:
    """Compute the firm-specific risk premium as a sum of per-layer
    contributions, returning both the total and the breakdown.

    The Layer 4 contribution is amplified by the AI substitution
    potential because higher substitutability means faster erosion.
    The Layer 7 contribution is modulated by K7: K7 < 1 (fragmented
    cross-border knowledge regime) creates a small positive premium
    representing the marginal vendor-concentration risk that the
    paper's section 8.4 introduces.

    ``alpha_overrides`` lets a caller substitute the paper-canonical
    α coefficients (Appendix A.2) with their own values for sensitivity
    analysis. Keys must match the YAML schema
    (``layer_1_infra``, ``layer_2_foundation``, …, ``layer_7_crossborder``);
    any subset is accepted, with missing keys falling back to the
    YAML default. The website's Advanced parameters lab uses this.
    """
    vl = config.load_parameters()["valuation_layered"]
    amp_base = float(vl["layer4_substitution_amplifier_base"])
    k7_premium_per_unit = float(vl["layer7_k_premium_per_unit"])

    def alpha(key: str) -> float:
        if alpha_overrides is not None and key in alpha_overrides:
            override = alpha_overrides[key]
            if override is not None:
                return float(override)
        return float(LAYER_RISK_COEFFICIENTS[key])

    breakdown: Dict[str, float] = {}
    breakdown["layer_1_infra"] = alpha("layer_1_infra") * exposure.layer_1_infra
    breakdown["layer_2_foundation"] = alpha("layer_2_foundation") * exposure.layer_2_foundation
    breakdown["layer_3_capability"] = alpha("layer_3_capability") * exposure.layer_3_capability
    # Layer 4: amplified by AI substitution potential
    breakdown["layer_4_codified"] = (
        alpha("layer_4_codified")
        * exposure.layer_4_codified
        * (amp_base + layer4_substitution_potential)
    )
    breakdown["layer_5_judgment"] = alpha("layer_5_judgment") * exposure.layer_5_judgment
    breakdown["layer_6_institutional"] = alpha("layer_6_institutional") * exposure.layer_6_institutional
    # Layer 7: K7-modulated. The override here REPLACES the K7 modulation
    # (advanced users who want to disable the K7 channel can set
    # `layer_7_crossborder` directly). When no override, the canonical
    # K7-modulated premium per unit applies.
    if alpha_overrides is not None and alpha_overrides.get("layer_7_crossborder") is not None:
        breakdown["layer_7_crossborder"] = (
            float(alpha_overrides["layer_7_crossborder"]) * exposure.layer_7_crossborder
        )
    else:
        layer7_k_premium = (1.0 - K7) * k7_premium_per_unit
        breakdown["layer_7_crossborder"] = layer7_k_premium * exposure.layer_7_crossborder
    total = sum(breakdown.values())
    return total, breakdown


# ---------------------------------------------------------------------------
# Layered discount rate
# ---------------------------------------------------------------------------

@dataclass
class LayeredDiscountRateInputs:
    """Inputs for the layered discount-rate calculation."""
    risk_free_rate: float                  # e.g. 0.0425 for 4.25% (US 10y as of 2026)
    equity_risk_premium: float             # e.g. 0.055 for the US (Damodaran ERP, 2026)
    industry_unlevered_beta: float         # from Damodaran (2026): e.g. 0.99 (HIT) or 1.23 (Software)
    de_ratio: float                        # market D/E ratio (industry, Damodaran)
    effective_tax_rate: float              # industry effective tax (Damodaran)
    trl: int                               # current TRL (1-9)
    layer_exposure: LayerExposure
    K7: float = 1.0                         # cross-border knowledge regime
    layer4_substitution_potential: float = 0.55
    sector_label: str = "unspecified"
    # Optional override of the signed per-layer α coefficients
    # (Appendix A.2 of the paper). Keys must match the YAML schema.
    # See ``layer_decomposed_risk_premium`` for behaviour.
    alpha_overrides: Optional[Dict[str, float]] = None


@dataclass
class LayeredDiscountRateResult:
    sector_label: str
    base_capm: float
    levered_beta: float
    trl_premium_pp: float
    layer_premium_pp: float
    layer_breakdown: Dict[str, float]
    total_discount_rate: float
    classical_damodaran_rate: float        # for direct comparison with the textbook
    delta_vs_classical_pp: float


def compute_layered_discount_rate(inputs: LayeredDiscountRateInputs) -> LayeredDiscountRateResult:
    """Compute the discount rate under both classical Damodaran and the
    layered extension introduced in the paper. The two are returned
    side by side so that the delta is auditable.

    The classical rate is the textbook adjusted CAPM as taught in the
    course (relevered industry beta + ERP * beta) without TRL or
    layer adjustments. The layered rate adds the TRL premium
    (Equidam-Hectelion calibration) and the layer-decomposed
    firm-specific premium.
    """
    # Step 1: relever industry unlevered beta to firm's de_ratio
    levered_beta = inputs.industry_unlevered_beta * (
        1.0 + (1.0 - inputs.effective_tax_rate) * inputs.de_ratio
    )
    # Step 2: classical CAPM (Damodaran textbook)
    base_capm = inputs.risk_free_rate + levered_beta * inputs.equity_risk_premium
    # Step 3: TRL premium (Equidam-Hectelion 2025 calibration)
    trl_pp = trl_premium(inputs.trl)
    # Step 4: layer-decomposed firm-specific risk premium
    layer_total_pp, layer_breakdown = layer_decomposed_risk_premium(
        inputs.layer_exposure,
        K7=inputs.K7,
        layer4_substitution_potential=inputs.layer4_substitution_potential,
        alpha_overrides=inputs.alpha_overrides,
    )
    total = base_capm + trl_pp + layer_total_pp
    classical = base_capm  # the textbook stops here
    return LayeredDiscountRateResult(
        sector_label=inputs.sector_label,
        base_capm=base_capm,
        levered_beta=levered_beta,
        trl_premium_pp=trl_pp,
        layer_premium_pp=layer_total_pp,
        layer_breakdown=layer_breakdown,
        total_discount_rate=total,
        classical_damodaran_rate=classical,
        delta_vs_classical_pp=total - classical,
    )


# ---------------------------------------------------------------------------
# DCF with TRL trajectory (replacing single-rate perpetuity)
# ---------------------------------------------------------------------------

@dataclass
class CashFlowProjection:
    """Projected free cash flows by year (Y1...YN), in USD."""
    year_labels: List[str]
    fcf_usd: List[float]


@dataclass
class TRLTrajectory:
    """TRL-by-year trajectory for a deep-tech firm. Allows the discount
    rate to vary across years as TRL rises. Values are clipped to [1, 9]."""
    year_labels: List[str]
    trl_by_year: List[int]


@dataclass
class LayeredDCFResult:
    sector_label: str
    method: str
    enterprise_value_usd: float
    discount_rate_used: float | List[float]
    trl_trajectory: Optional[List[int]]
    pv_explicit_period_usd: float
    pv_terminal_usd: float
    components: Dict[str, float] = field(default_factory=dict)
    notes: str = ""


def classical_damodaran_dcf(
    cf: CashFlowProjection,
    discount_rate: float,
    terminal_growth_rate: float,
    sector_label: str = "classical_damodaran",
) -> LayeredDCFResult:
    """Single-rate Gordon-perpetuity DCF as taught in the canonical
    course material (Valuation_IV.xlsx). Used as the comparison
    baseline against the layered method.
    """
    pv_explicit = 0.0
    for t, fcf in enumerate(cf.fcf_usd, start=1):
        pv_explicit += fcf / (1.0 + discount_rate) ** t
    last_fcf = cf.fcf_usd[-1]
    if discount_rate <= terminal_growth_rate:
        terminal = 0.0
    else:
        terminal_value_at_T = last_fcf * (1.0 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        terminal = terminal_value_at_T / (1.0 + discount_rate) ** len(cf.fcf_usd)
    ev = pv_explicit + terminal
    return LayeredDCFResult(
        sector_label=sector_label,
        method="classical_damodaran_single_rate",
        enterprise_value_usd=ev,
        discount_rate_used=discount_rate,
        trl_trajectory=None,
        pv_explicit_period_usd=pv_explicit,
        pv_terminal_usd=terminal,
        components={"pv_explicit": pv_explicit, "pv_terminal": terminal},
        notes="Single discount rate, Gordon perpetuity. The textbook approach.",
    )


def layered_dcf(
    cf: CashFlowProjection,
    inputs: LayeredDiscountRateInputs,
    trl_trajectory: TRLTrajectory,
    terminal_growth_rate: float,
    second_valley_drag: float = 0.0,
) -> LayeredDCFResult:
    """Layered DCF: discount rate varies year-by-year as TRL rises,
    layer-decomposed firm-specific premium applies to each year, and
    the perpetuity value is reduced by `second_valley_drag` (a 0..0.5
    factor) to capture the post-AI second-valley risk introduced in
    the paper's section 6.5.

    The year-specific discount rate is obtained by overriding the
    `trl` field of `inputs` with the year's TRL. The other fields
    (industry beta, layer exposure, K7, layer-4 substitution) are held
    constant in this baseline implementation; they are user-editable
    for richer scenarios via the YAML interface.
    """
    n_years = len(cf.fcf_usd)
    if len(trl_trajectory.trl_by_year) != n_years:
        raise ValueError(
            f"TRL trajectory has {len(trl_trajectory.trl_by_year)} years; "
            f"cash flow has {n_years}."
        )
    pv_explicit = 0.0
    discount_rates: List[float] = []
    for t, fcf in enumerate(cf.fcf_usd, start=1):
        # update inputs to this year's TRL
        year_inputs = LayeredDiscountRateInputs(
            risk_free_rate=inputs.risk_free_rate,
            equity_risk_premium=inputs.equity_risk_premium,
            industry_unlevered_beta=inputs.industry_unlevered_beta,
            de_ratio=inputs.de_ratio,
            effective_tax_rate=inputs.effective_tax_rate,
            trl=trl_trajectory.trl_by_year[t - 1],
            layer_exposure=inputs.layer_exposure,
            K7=inputs.K7,
            layer4_substitution_potential=inputs.layer4_substitution_potential,
            sector_label=inputs.sector_label,
            alpha_overrides=inputs.alpha_overrides,
        )
        rate_result = compute_layered_discount_rate(year_inputs)
        rate_t = rate_result.total_discount_rate
        discount_rates.append(rate_t)
        # cumulative discount factor (so year-t cash flow is discounted
        # by the geometric mean of all rates seen up to t)
        cum_factor = 1.0
        for r in discount_rates:
            cum_factor *= (1.0 + r)
        pv_explicit += fcf / cum_factor

    # Terminal value at year-N TRL, with second-valley drag adjustment
    final_inputs = LayeredDiscountRateInputs(
        risk_free_rate=inputs.risk_free_rate,
        equity_risk_premium=inputs.equity_risk_premium,
        industry_unlevered_beta=inputs.industry_unlevered_beta,
        de_ratio=inputs.de_ratio,
        effective_tax_rate=inputs.effective_tax_rate,
        trl=trl_trajectory.trl_by_year[-1],
        layer_exposure=inputs.layer_exposure,
        K7=inputs.K7,
        layer4_substitution_potential=inputs.layer4_substitution_potential,
        sector_label=inputs.sector_label,
        alpha_overrides=inputs.alpha_overrides,
    )
    terminal_rate = compute_layered_discount_rate(final_inputs).total_discount_rate
    last_fcf = cf.fcf_usd[-1]
    if terminal_rate <= terminal_growth_rate:
        terminal_pv = 0.0
    else:
        terminal_value = last_fcf * (1.0 + terminal_growth_rate) / (terminal_rate - terminal_growth_rate)
        # Apply the second-valley drag (0..0.5 reduces terminal value)
        terminal_value *= (1.0 - second_valley_drag)
        cum_factor = 1.0
        for r in discount_rates:
            cum_factor *= (1.0 + r)
        terminal_pv = terminal_value / cum_factor

    ev = pv_explicit + terminal_pv
    return LayeredDCFResult(
        sector_label=inputs.sector_label,
        method="layered_seven_layer_dcf",
        enterprise_value_usd=ev,
        discount_rate_used=discount_rates,
        trl_trajectory=trl_trajectory.trl_by_year,
        pv_explicit_period_usd=pv_explicit,
        pv_terminal_usd=terminal_pv,
        components={
            "pv_explicit": pv_explicit,
            "pv_terminal": terminal_pv,
            "terminal_rate": terminal_rate,
            "second_valley_drag": second_valley_drag,
        },
        notes=(
            "Layered DCF: year-specific discount rate from TRL trajectory + "
            "layer-decomposed risk premium + second-valley drag on the "
            "terminal value. See paper section 9 (Appendix A)."
        ),
    )


# ---------------------------------------------------------------------------
# Funding-stage benchmarks (US, calibrated to Carta Q3 2025)
# ---------------------------------------------------------------------------
# These are reference benchmarks used by the appendix to discuss how
# valuation outcomes interact with VC funding-round expectations.
# Source: Carta State of Private Markets Q3 2025; SaaStr (Dec 2025).

US_FUNDING_STAGE_BENCHMARKS = config.us_funding_stage_benchmarks()


def stage_for_valuation(enterprise_value_usd: float) -> str:
    """Map an enterprise value to its expected funding stage band.

    Thresholds in config/parameters.yaml under
    valuation_layered.stage_thresholds_usd.
    """
    t = config.stage_thresholds_usd()
    if enterprise_value_usd < float(t["pre_seed_upper"]):
        return "pre_seed"
    if enterprise_value_usd < float(t["seed_upper"]):
        return "seed"
    if enterprise_value_usd < float(t["series_a_upper"]):
        return "series_a"
    if enterprise_value_usd < float(t["series_b_upper"]):
        return "series_b"
    return "series_c"
