"""Two-phase reformulation of CAPM, WACC, EVA, ROI, and Gordon perpetuity
under the post-AI double-valley dynamic introduced in Section 6.5 of the
paper "The Cost Gradient of the Build" (de Miranda Neto, 2026), and
formally developed in Appendix B.

This module is the operational counterpart of Appendix B. It complements
Appendix A's `valuation_layered.py` (which extends Damodaran's narrative-
and-numbers with TRL-modulated discount rates and layer-decomposed risk
premia) by addressing a different question: how do the canonical
formulas of corporate finance (CAPM, WACC, EVA, Gordon perpetuity)
adapt mathematically to a firm whose risk profile undergoes a
discrete phase transition rather than evolving smoothly?

The literature already provides the building blocks. Damodaran himself
has explicitly written that "the D cannot change over time in a DCF" is
a myth: discount rates can vary by year, and the proper discounting
under time-varying rates uses compounded rather than per-year factors
(Damodaran, 2016, blog post "Myth 4.3"). The conditional CAPM literature
(Jagannathan and Wang, 1996; Lewellen and Nagel, 2006; Engle, 2016)
has formalised time-varying betas. Miller (2009) and Frank and Shen
(2016) have shown that the standard perpetuity-formula WACC is
incorrect for finite-life or dynamic firms. What this module
contributes is a calibration of these established time-varying
techniques to the specific phase structure that the paper's Section 6.5
introduces: a Phase 1 (initial growth, single valley resolved by
Series A capital), a Phase 2 (commoditization second valley, when
Layer-4 substitutability erodes the competitive moat), and a Phase 3
(post-second-valley terminal trajectory).

Three formal extensions are implemented:

1. Two-phase CAPM with phase-conditional beta. Beta is allowed to
   take different values in each of the three phases; the model
   reduces to classical CAPM when all three are equal.

2. Two-phase WACC with phase-conditional weights and rates. The
   capital structure (D/E) and the costs of debt and equity can shift
   across phases, reflecting the empirical observation that firms in
   the second valley raise more equity at higher cost.

3. Two-phase Gordon perpetuity. The terminal value is computed not
   from a single steady-state assumption but from the post-Phase-3
   convergent rate, with the second-valley drag (introduced in
   Appendix A) applied as a multiplicative correction.

The module also implements a phase-conditional EVA and ROI, both of
which are taught in the user's classroom material (Valuation_IV.pptx)
under their classical (single-rate) form.

References cited in the docstrings of this module:
- Damodaran, A. (2016). Myth 4.3: The D cannot change (over time) in
  a DCF. Musings on Markets blog post, November 4, 2016.
- Jagannathan, R., and Wang, Z. (1996). The conditional CAPM and the
  cross-section of expected returns. Journal of Finance, 51(1), 3-53.
- Lewellen, J., and Nagel, S. (2006). The conditional CAPM does not
  explain asset-pricing anomalies. Journal of Financial Economics,
  82(2), 289-314. (NBER Working Paper 9974, 2003.)
- Engle, R. F. (2016). Dynamic conditional beta. Journal of Financial
  Econometrics, 14(4), 643-667.
- Miller, R. A. (2009). The weighted average cost of capital is not
  quite right. Quarterly Review of Economics and Finance, 49(1), 128-138.
- Frank, M. Z., and Shen, T. (2016). Investment and the weighted average
  cost of capital. Journal of Financial Economics, 119(2), 300-315.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from . import config


# ---------------------------------------------------------------------------
# Phase enumeration
# ---------------------------------------------------------------------------
# Phase 1: initial growth and first valley (months 0-18 typical).
# Phase 2: commoditization second valley (months 18-42 typical).
# Phase 3: post-second-valley terminal trajectory (month 42+).
# Generic phase boundaries and defaults live in config/parameters.yaml
# under valuation_two_phase.* — firm-specific calibrations are under
# firms_appendix_b.*.

PHASE_1 = "phase_1_growth"
PHASE_2 = "phase_2_second_valley"
PHASE_3 = "phase_3_terminal"


def _vtp() -> Dict:
    return config.load_parameters()["valuation_two_phase"]


# ---------------------------------------------------------------------------
# Phase parameters
# ---------------------------------------------------------------------------

@dataclass
class PhaseParameters:
    """Parameters that may shift across phases of the firm's lifecycle.

    The classical (single-phase) CAPM/WACC arises as the special case
    where phase_1, phase_2, and phase_3 are identical. Defaults come from
    config/parameters.yaml under valuation_two_phase.
    """
    # Phase boundaries (year indices). Year 1 = first projected year.
    phase_1_end_year: int = int(_vtp()["default_phase_boundaries"]["phase_1_end_year"])
    phase_2_end_year: int = int(_vtp()["default_phase_boundaries"]["phase_2_end_year"])

    # Phase-conditional unlevered betas
    beta_unlevered_phase_1: float = float(_vtp()["default_betas"]["phase_1"])
    beta_unlevered_phase_2: float = float(_vtp()["default_betas"]["phase_2"])
    beta_unlevered_phase_3: float = float(_vtp()["default_betas"]["phase_3"])

    # Phase-conditional D/E ratios (capital structure may shift)
    de_ratio_phase_1: float = float(_vtp()["default_de_ratios"]["phase_1"])
    de_ratio_phase_2: float = float(_vtp()["default_de_ratios"]["phase_2"])
    de_ratio_phase_3: float = float(_vtp()["default_de_ratios"]["phase_3"])

    # Phase-conditional cost-of-debt premium above risk-free
    kd_spread_phase_1: float = float(_vtp()["default_kd_spreads"]["phase_1"])
    kd_spread_phase_2: float = float(_vtp()["default_kd_spreads"]["phase_2"])
    kd_spread_phase_3: float = float(_vtp()["default_kd_spreads"]["phase_3"])

    # Effective tax rate (typically constant across phases)
    effective_tax_rate: float = float(_vtp()["default_effective_tax_rate"])

    def beta_for_year(self, year: int) -> float:
        if year <= self.phase_1_end_year:
            return self.beta_unlevered_phase_1
        elif year <= self.phase_2_end_year:
            return self.beta_unlevered_phase_2
        else:
            return self.beta_unlevered_phase_3

    def de_ratio_for_year(self, year: int) -> float:
        if year <= self.phase_1_end_year:
            return self.de_ratio_phase_1
        elif year <= self.phase_2_end_year:
            return self.de_ratio_phase_2
        else:
            return self.de_ratio_phase_3

    def kd_for_year(self, year: int, risk_free_rate: float) -> float:
        if year <= self.phase_1_end_year:
            return risk_free_rate + self.kd_spread_phase_1
        elif year <= self.phase_2_end_year:
            return risk_free_rate + self.kd_spread_phase_2
        else:
            return risk_free_rate + self.kd_spread_phase_3

    def phase_for_year(self, year: int) -> str:
        if year <= self.phase_1_end_year:
            return PHASE_1
        elif year <= self.phase_2_end_year:
            return PHASE_2
        else:
            return PHASE_3


# ---------------------------------------------------------------------------
# Two-phase CAPM
# ---------------------------------------------------------------------------

def two_phase_capm(
    year: int,
    risk_free_rate: float,
    equity_risk_premium: float,
    phases: PhaseParameters,
) -> float:
    """Cost of equity Ke for a given year, under phase-conditional beta.

    Ke_t = Rf + beta_levered(t) * ERP

    where beta_levered(t) = beta_unlevered(phase(t)) * [1 + (1 - tau) * (D/E)(phase(t))]

    Reduces to the classical Damodaran adjusted-CAPM when betas, D/E, and
    spreads are equal across phases. The literature on conditional CAPM
    (Jagannathan and Wang, 1996; Lewellen and Nagel, 2006; Engle, 2016)
    establishes the legitimacy of time-varying betas; the contribution
    here is the calibration of beta jumps to the framework's phase
    structure rather than to consumption-to-wealth ratios or to GARCH
    volatility filters.
    """
    beta_u = phases.beta_for_year(year)
    de = phases.de_ratio_for_year(year)
    beta_l = beta_u * (1.0 + (1.0 - phases.effective_tax_rate) * de)
    ke = risk_free_rate + beta_l * equity_risk_premium
    return ke


# ---------------------------------------------------------------------------
# Two-phase WACC
# ---------------------------------------------------------------------------

def two_phase_wacc(
    year: int,
    risk_free_rate: float,
    equity_risk_premium: float,
    phases: PhaseParameters,
) -> Dict[str, float]:
    """Phase-conditional WACC for a given year.

    WACC_t = (E/V)_t * Ke_t + (D/V)_t * Kd_t * (1 - tau)

    where (E/V), (D/V), Ke, and Kd are all phase-conditional.

    The literature recognises that "moving WACC" is conceptually more
    accurate than constant WACC for any firm whose capital structure or
    risk profile shifts (Miller, 2009; Frank and Shen, 2016). The
    contribution here is the calibration of these shifts to the
    Phase 1 / Phase 2 / Phase 3 structure of the post-AI double valley.

    Returns a dict with the components for inspection.
    """
    de = phases.de_ratio_for_year(year)
    # Convert D/E to E/V and D/V
    # If D/E = x, then D/V = x / (1 + x), E/V = 1 / (1 + x)
    d_over_v = de / (1.0 + de)
    e_over_v = 1.0 / (1.0 + de)
    ke = two_phase_capm(year, risk_free_rate, equity_risk_premium, phases)
    kd = phases.kd_for_year(year, risk_free_rate)
    after_tax_kd = kd * (1.0 - phases.effective_tax_rate)
    wacc = e_over_v * ke + d_over_v * after_tax_kd
    return {
        "wacc": wacc,
        "ke": ke,
        "kd": kd,
        "after_tax_kd": after_tax_kd,
        "e_over_v": e_over_v,
        "d_over_v": d_over_v,
        "phase": phases.phase_for_year(year),
    }


# ---------------------------------------------------------------------------
# Two-phase DCF with compounded discount factors
# ---------------------------------------------------------------------------

def two_phase_dcf(
    fcf_by_year: List[float],
    risk_free_rate: float,
    equity_risk_premium: float,
    phases: PhaseParameters,
    terminal_growth_rate: float,
    second_valley_drag: float = 0.0,
    cash_flow_multipliers: Optional[List[float]] = None,
) -> Dict[str, float]:
    """Two-phase DCF with compounded discount factors, as Damodaran (2016)
    explicitly recommends for time-varying rates.

    The present value of year-t cash flow uses the compounded factor
    prod_{s=1..t} (1 + r_s) rather than (1 + r)^t, exactly as
    Damodaran's "Musings on Markets" blog post specifies. The terminal
    value is computed with the Phase-3 WACC and reduced by the
    second-valley drag.

    Parameters
    ----------
    cash_flow_multipliers : list of float, optional
        Year-by-year multiplier applied to ``fcf_by_year`` before
        discounting. Defaults to all-ones, in which case the function
        produces exactly the legacy behaviour (regression-tested by
        tests/test_regression_baseline.py).

        This hook supports the dual-channel correction of subsection
        B.2.6 (Eq B.14–B.15 of the Insertion Package): the caller passes
        a phase-conditional ``lambda_2V`` vector that compresses
        projected free cash flow during the Phase-2 window. Outside
        Phase 2 the multiplier should equal 1.0 — see
        ``v0_dualchannel`` for the canonical construction. The terminal
        value uses the multiplied last FCF as its perpetuity base; with
        ``lambda_2V(phase_3) = 1.0`` (the normative case) this is
        identical to the unmultiplied last FCF.
    """
    n_years = len(fcf_by_year)
    if cash_flow_multipliers is None:
        multipliers = [1.0] * n_years
    else:
        if len(cash_flow_multipliers) != n_years:
            raise ValueError(
                f"cash_flow_multipliers has length {len(cash_flow_multipliers)}; "
                f"expected {n_years} to match fcf_by_year."
            )
        multipliers = [float(m) for m in cash_flow_multipliers]

    yearly_wacc = []
    for year in range(1, n_years + 1):
        w = two_phase_wacc(year, risk_free_rate, equity_risk_premium, phases)
        yearly_wacc.append(w["wacc"])

    # PV of explicit period using compounded discount factors
    adjusted_fcf = [f * m for f, m in zip(fcf_by_year, multipliers)]
    pv_explicit = 0.0
    cum_factor = 1.0
    for t, (fcf, r_t) in enumerate(zip(adjusted_fcf, yearly_wacc), start=1):
        cum_factor *= (1.0 + r_t)
        pv_explicit += fcf / cum_factor

    # Terminal value using Phase-3 WACC. The perpetuity base uses the
    # multiplied last FCF so that the formula is internally consistent
    # under any lambda trajectory the caller may supply. When
    # multipliers[-1] == 1.0 (the normative case for Phase 3) this
    # reduces to the unmultiplied last FCF and the legacy behaviour is
    # preserved.
    phase_3_wacc = yearly_wacc[-1]
    last_fcf = adjusted_fcf[-1]
    if phase_3_wacc <= terminal_growth_rate:
        tv_pv = 0.0
    else:
        tv_at_T = last_fcf * (1.0 + terminal_growth_rate) / (phase_3_wacc - terminal_growth_rate)
        # Apply second-valley drag to terminal value
        tv_at_T *= (1.0 - second_valley_drag)
        # Discount back to present using the same compounded factor
        tv_pv = tv_at_T / cum_factor

    return {
        "enterprise_value": pv_explicit + tv_pv,
        "pv_explicit": pv_explicit,
        "pv_terminal": tv_pv,
        "yearly_wacc": yearly_wacc,
        "phase_3_wacc": phase_3_wacc,
        "compounded_discount_factor_T": cum_factor,
        "cash_flow_multipliers": multipliers,
    }


# ---------------------------------------------------------------------------
# Phase-conditional EVA and ROI
# ---------------------------------------------------------------------------

def two_phase_eva(
    nopat: float,
    invested_capital: float,
    year: int,
    risk_free_rate: float,
    equity_risk_premium: float,
    phases: PhaseParameters,
) -> Dict[str, float]:
    """Phase-conditional Economic Value Added.

    EVA_t = NOPAT_t - WACC_t * IC_t

    The EVA formulation taught in the user's course material (Valuation_IV.pptx)
    uses a single WACC. Here the WACC is phase-conditional, so a project
    or firm can have positive EVA in Phase 1 (when WACC is low because
    beta is low and D/E is low) and negative EVA in Phase 2 (when WACC
    rises because beta jumps and D/E rises). This is the formal
    statement of the second-valley risk in EVA terms.
    """
    wacc_components = two_phase_wacc(year, risk_free_rate, equity_risk_premium, phases)
    wacc = wacc_components["wacc"]
    capital_charge = wacc * invested_capital
    eva = nopat - capital_charge
    return {
        "eva": eva,
        "nopat": nopat,
        "wacc": wacc,
        "invested_capital": invested_capital,
        "capital_charge": capital_charge,
        "phase": wacc_components["phase"],
    }


def two_phase_roi(
    nopat: float,
    invested_capital: float,
    year: int,
    risk_free_rate: float,
    equity_risk_premium: float,
    phases: PhaseParameters,
) -> Dict[str, float]:
    """Phase-conditional ROI vs WACC test.

    ROI_t = NOPAT_t / IC_t
    Decision: ROI_t > WACC_t in this phase => firm creates value;
              ROI_t < WACC_t => firm destroys value.

    Under classical Damodaran with single WACC, a firm with stable ROI
    above WACC creates value indefinitely. Under the phase-conditional
    version, the firm may create value in Phase 1, destroy value in
    Phase 2 (WACC jumps above ROI), and recover in Phase 3. This is
    the EVA-equivalent statement of the second-valley dynamic.
    """
    roi = nopat / invested_capital if invested_capital > 0 else 0.0
    wacc_components = two_phase_wacc(year, risk_free_rate, equity_risk_premium, phases)
    wacc = wacc_components["wacc"]
    return {
        "roi": roi,
        "wacc": wacc,
        "spread": roi - wacc,
        "creates_value": roi > wacc,
        "phase": wacc_components["phase"],
    }


# ---------------------------------------------------------------------------
# Comparison helpers: classical (single-rate) vs two-phase
# ---------------------------------------------------------------------------

def classical_capm(
    risk_free_rate: float,
    equity_risk_premium: float,
    beta_unlevered: float,
    de_ratio: float,
    effective_tax_rate: float,
) -> float:
    """Classical adjusted-CAPM as taught in Valuation_IV.pptx (single rate)."""
    beta_l = beta_unlevered * (1.0 + (1.0 - effective_tax_rate) * de_ratio)
    return risk_free_rate + beta_l * equity_risk_premium


def classical_wacc(
    risk_free_rate: float,
    equity_risk_premium: float,
    beta_unlevered: float,
    de_ratio: float,
    effective_tax_rate: float,
    kd_spread: float,
) -> float:
    """Classical single-rate WACC as taught in Valuation_IV.pptx."""
    ke = classical_capm(
        risk_free_rate, equity_risk_premium, beta_unlevered, de_ratio, effective_tax_rate
    )
    kd = risk_free_rate + kd_spread
    d_over_v = de_ratio / (1.0 + de_ratio)
    e_over_v = 1.0 / (1.0 + de_ratio)
    return e_over_v * ke + d_over_v * kd * (1.0 - effective_tax_rate)
