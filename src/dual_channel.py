"""Dual-channel correction (subsection B.2.6) of the post-AI valuation
framework.

The two-phase reformulation of Appendix B (Eqs B.3-B.11) corrects the
DENOMINATOR of the DCF — the cost of capital — for the post-AI double-
valley dynamic. This module adds the missing correction to the
NUMERATOR: during the Phase-2 window, the projected free cash flow is
multiplied by a phase-conditional ``lambda_2V`` factor that compresses
revenue as the firm loses pricing power while its technical advantage
commoditizes.

The module is purely additive. It does not modify any of the three
existing valuation paths (classical Damodaran, Appendix A layered DCF,
Appendix B two-phase DCF). It introduces a fourth, complementary path
``V0_dualchannel`` (Eq B.15) and a reconciliation routine that places
the four side-by-side.

Equations
---------
* Eq B.12 — Partition of the second-valley risk effect:

      pi_2V = pi_2V_sys + pi_2V_idio

  The systematic component is already carried by the Phase-2 jump of
  the unlevered beta in Eq B.3 / two_phase_dcf. The idiosyncratic
  component lives in the firm-specific layer-decomposed premium.

* Eq B.13 — Adjusted Layer-4 coefficient (to avoid double-counting):

      alpha_4_adj = alpha_4 - alpha_4_sys

  Used ONLY in hybrid models that combine the layered firm-specific
  premium (Appendix A / Eq C.1) with the two-phase WACC (Appendix B).
  The basic ``V0_dualchannel`` of Eq B.15 does not need this adjustment
  because it does not add a layered premium on top of the two-phase
  WACC — the helper is registered here for use by future extensions.

* Eq B.14 — Phase-conditional revenue-retreat factor applied to FCF:

      FCF_2V(t) = FCF_proj(t) * lambda_2V(phi(t))

* Eq B.15 — Dual-channel enterprise value:

      V0_dualchannel = sum_t [ FCF_proj(t) * lambda_2V(phi(t))
                                / prod_{s<=t} (1 + WACC(s)) ] + TV

  where WACC(s) is the existing Eq B.6 phase-conditional WACC,
  prod (1 + WACC(s)) is the existing Eq B.10 compounded discount
  factor, and TV is the existing Eq B.9 phase-conditional terminal
  value (with delta_2V drag). In other words: V0_dualchannel IS the
  existing two-phase DCF with the FCF replaced by FCF * lambda.

  Identity (acceptance check 3): when lambda_2V = 1.0 in all three
  phases, V0_dualchannel equals V0_twophase_B to the cent. The unit
  test in tests/test_dual_channel.py guards this invariant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import config
from .valuation_two_phase import (
    PhaseParameters,
    two_phase_dcf,
)


# ---------------------------------------------------------------------------
# Helper 1 — auditable calibration of lambda_2V_phase2 from layer shares
# ---------------------------------------------------------------------------

def lambda_2V_phase2_from_calibration(
    layer4_share: float,
    layer6_share: float,
    k_L4: Optional[float] = None,
    k_L6: Optional[float] = None,
    lower_bound: Optional[float] = None,
    upper_bound: Optional[float] = None,
) -> float:
    """Auditable derivation of the Phase-2 revenue-retreat factor from a
    firm's layer composition.

    Formula (mirrors the structure of delta_2V from Appendix B)::

        lambda_2V_phase2 = clamp(
            1.0 - k_L4 * layer4_share + k_L6 * layer6_share,
            lower_bound, upper_bound,
        )

    Reasoning: a Layer-4-heavy firm sees its pricing power compressed
    during the Phase-2 commoditization window — lambda falls below 1.
    A Layer-6-rich firm carries regulatory and institutional moats that
    insulate revenue during the same window — lambda is pushed back
    toward 1. The clamp keeps the result in a defensible band.

    Parameters left at ``None`` are loaded from
    ``config/parameters.yaml`` section 26 (``dual_channel.lambda_2V_calibration``).
    The per-firm Phase-2 defaults documented under
    ``dual_channel.lambda_2V_phase2_defaults`` (NeuroCertify 0.95,
    DataFlow 0.70) should land close to the output of this helper when
    the layer shares of the corresponding firms are passed in. They
    are not hard-coded; the helper is the source.
    """
    dc = config.dual_channel()["lambda_2V_calibration"]
    if k_L4 is None:
        k_L4 = float(dc["k_L4"])
    if k_L6 is None:
        k_L6 = float(dc["k_L6"])
    if lower_bound is None:
        lower_bound = float(dc["lower_bound"])
    if upper_bound is None:
        upper_bound = float(dc["upper_bound"])

    raw = 1.0 - k_L4 * layer4_share + k_L6 * layer6_share
    return float(max(lower_bound, min(upper_bound, raw)))


# ---------------------------------------------------------------------------
# Helper 2 — Eq B.13 risk partition (documented for future hybrid models)
# ---------------------------------------------------------------------------

def alpha_4_adj(
    alpha_4: Optional[float] = None,
    alpha_4_sys: Optional[float] = None,
) -> float:
    """Adjusted Layer-4 coefficient, net of the systematic share that is
    already represented in the Phase-2 beta jump (Eq B.13).

    Returns ``alpha_4 - alpha_4_sys`` clamped to be non-negative.

    The basic ``v0_dualchannel`` (Eq B.15) does not consume this helper
    because it does not add a layered firm-specific premium on top of
    the two-phase WACC. The helper is registered for use by HYBRID
    models that DO combine the two — the partition removes the
    double-counting that would otherwise inflate the total risk
    premium.

    Defaults:
        alpha_4     -> config/parameters.yaml
                       valuation_layered.layer_risk_coefficients.layer_4_codified
                       (typically 0.08).
        alpha_4_sys -> config/parameters.yaml
                       dual_channel.alpha_4_sys (typically 0.03).
    """
    if alpha_4 is None:
        alpha_4 = float(config.layer_risk_coefficients()["layer_4_codified"])
    if alpha_4_sys is None:
        alpha_4_sys = float(config.dual_channel()["alpha_4_sys"])
    return max(0.0, float(alpha_4) - float(alpha_4_sys))


# ---------------------------------------------------------------------------
# Helper 3 — build the phase-conditional lambda vector
# ---------------------------------------------------------------------------

def build_lambda_vector(
    phases: PhaseParameters,
    n_years: int,
    lambda_phase2: float,
    lambda_phase1: float = 1.0,
    lambda_phase3: float = 1.0,
) -> List[float]:
    """Construct the per-year ``lambda_2V`` multiplier vector used by Eq B.15.

    Walks years 1..n_years, asks the supplied ``PhaseParameters`` which
    phase each year sits in, and returns the corresponding lambda. The
    Phase-1 and Phase-3 defaults are 1.0 (no retreat outside the
    valley), in line with the normative case stated in the Insertion
    Package for B.2.6.
    """
    out: List[float] = []
    for year in range(1, n_years + 1):
        phase = phases.phase_for_year(year)
        if phase == "phase_1_growth":
            out.append(float(lambda_phase1))
        elif phase == "phase_2_second_valley":
            out.append(float(lambda_phase2))
        elif phase == "phase_3_terminal":
            out.append(float(lambda_phase3))
        else:
            raise ValueError(f"Unknown phase label: {phase!r}")
    return out


# ---------------------------------------------------------------------------
# Eq B.15 — dual-channel enterprise value
# ---------------------------------------------------------------------------

@dataclass
class DualChannelResult:
    """Output of the dual-channel correction (Eq B.15)."""
    enterprise_value: float
    pv_explicit: float
    pv_terminal: float
    yearly_wacc: List[float]
    phase_3_wacc: float
    lambda_vector: List[float]
    twophase_enterprise_value: float
    numerator_channel_effect: float  # = V0_twophase_B - V0_dualchannel
    notes: str = ""


def v0_dualchannel(
    fcf_by_year: List[float],
    risk_free_rate: float,
    equity_risk_premium: float,
    phases: PhaseParameters,
    terminal_growth_rate: float,
    second_valley_drag: float,
    lambda_phase2: float,
    lambda_phase1: float = 1.0,
    lambda_phase3: float = 1.0,
) -> DualChannelResult:
    """Dual-channel enterprise value (Eq B.15).

    This is the existing two-phase DCF (``two_phase_dcf``) with the
    explicit-period free cash flow multiplied by a phase-conditional
    ``lambda_2V`` factor. Everything else — the phase-conditional WACC
    of Eq B.6, the compounded discount factor of Eq B.10, the
    phase-conditional terminal value of Eq B.9 with ``delta_2V`` — is
    delegated unchanged to ``two_phase_dcf``.

    Also computes the *numerator channel effect*:

        numerator_channel_effect = V0_twophase_B - V0_dualchannel

    which isolates, in monetary terms, the contribution of the
    cash-flow channel — the amount that a rate-only correction
    (two-phase WACC alone) leaves unmeasured. Feeds the reconciliation
    figure (Figure B.5) and the B.2.6 text.
    """
    lambda_vec = build_lambda_vector(
        phases=phases,
        n_years=len(fcf_by_year),
        lambda_phase2=lambda_phase2,
        lambda_phase1=lambda_phase1,
        lambda_phase3=lambda_phase3,
    )

    # Baseline two-phase EV (lambda = 1 everywhere) — used to compute
    # the numerator channel effect and to validate the identity stated
    # in acceptance check 3.
    twophase = two_phase_dcf(
        fcf_by_year=fcf_by_year,
        risk_free_rate=risk_free_rate,
        equity_risk_premium=equity_risk_premium,
        phases=phases,
        terminal_growth_rate=terminal_growth_rate,
        second_valley_drag=second_valley_drag,
        cash_flow_multipliers=None,        # explicit: default behaviour
    )

    dual = two_phase_dcf(
        fcf_by_year=fcf_by_year,
        risk_free_rate=risk_free_rate,
        equity_risk_premium=equity_risk_premium,
        phases=phases,
        terminal_growth_rate=terminal_growth_rate,
        second_valley_drag=second_valley_drag,
        cash_flow_multipliers=lambda_vec,
    )

    return DualChannelResult(
        enterprise_value=dual["enterprise_value"],
        pv_explicit=dual["pv_explicit"],
        pv_terminal=dual["pv_terminal"],
        yearly_wacc=list(dual["yearly_wacc"]),
        phase_3_wacc=dual["phase_3_wacc"],
        lambda_vector=lambda_vec,
        twophase_enterprise_value=twophase["enterprise_value"],
        numerator_channel_effect=(
            twophase["enterprise_value"] - dual["enterprise_value"]
        ),
        notes=(
            "V0_dualchannel = two-phase DCF (Eq B.11) with FCF replaced by "
            "FCF * lambda_2V (Eq B.14). When lambda_2V = 1.0 in all phases "
            "this reduces to V0_twophase_B to the cent (acceptance check 3)."
        ),
    )


# ---------------------------------------------------------------------------
# Reconciliation: the four valuations side-by-side
# ---------------------------------------------------------------------------

@dataclass
class FourPathReconciliation:
    """Record holding the four valuation paths for a given firm.

    Keys ``v0_classical``, ``v0_layered_A``, ``v0_twophase_B``,
    ``v0_dualchannel`` hold the point-estimate enterprise values (USD).
    ``numerator_channel_effect`` and ``lambda_vector`` come from the
    dual-channel path; the rest are pulled from the existing paths
    unchanged. Monte Carlo bands (P10/P50/P90) are attached by the
    caller in Sprint 3 and are intentionally empty here.
    """
    firm_label: str
    v0_classical: float
    v0_layered_A: float
    v0_twophase_B: float
    v0_dualchannel: float
    numerator_channel_effect: float
    lambda_vector: List[float]
    second_valley_drag: float
    bands: Dict[str, Dict[str, float]] = field(default_factory=dict)
    notes: str = ""

    def ordered_for_figure_B5(self) -> List[Dict[str, float]]:
        """Four-bar ordering used by Figure B.5 of the paper."""
        return [
            {"key": "v0_classical",   "value_usd": self.v0_classical},
            {"key": "v0_layered_A",   "value_usd": self.v0_layered_A},
            {"key": "v0_twophase_B",  "value_usd": self.v0_twophase_B},
            {"key": "v0_dualchannel", "value_usd": self.v0_dualchannel},
        ]


def reconcile_four_paths(
    firm_label: str,
    v0_classical: float,
    v0_layered_A: float,
    v0_twophase_B: float,
    dual_result: DualChannelResult,
    second_valley_drag: float,
    notes: str = "",
) -> FourPathReconciliation:
    """Assemble the four valuations into a single record.

    The three existing paths are passed in as numerical values to keep
    this module decoupled from the upstream callers — the caller is
    responsible for running ``classical_damodaran_dcf``, ``layered_dcf``,
    and reading the two-phase EV from ``dual_result.twophase_enterprise_value``.

    Acceptance check 4: when ``lambda_2V = 1.0`` in the dual result, this
    record satisfies ``v0_dualchannel == v0_twophase_B`` to the cent.
    """
    return FourPathReconciliation(
        firm_label=firm_label,
        v0_classical=float(v0_classical),
        v0_layered_A=float(v0_layered_A),
        v0_twophase_B=float(v0_twophase_B),
        v0_dualchannel=float(dual_result.enterprise_value),
        numerator_channel_effect=float(dual_result.numerator_channel_effect),
        lambda_vector=list(dual_result.lambda_vector),
        second_valley_drag=float(second_valley_drag),
        notes=notes,
    )
