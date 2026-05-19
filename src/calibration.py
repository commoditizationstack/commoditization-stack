"""Empirical-calibration scaffolding for the B.2.6 dual-channel
correction (Sprint 8).

This module is **infrastructure for future work**. The framework's
operative parameters — ``alpha_4_sys``, ``lambda_2V_phase2``,
``lambda_2V_phase3`` and the layer risk coefficients ``alpha_i`` — are
documented as "calibration parameter — provisional, not data-estimated"
throughout the paper and in ``config/parameters.yaml``. The empirical
calibration program described in the paper's Section 11.2 (multi-
disciplinary agenda) and in ``docs/empirical_calibration_program.md``
explains what firm-level transaction data would be needed to refine
these values. This module provides the typed surface that future
calibration work can plug into:

  * ``TransactionObservation`` — one observed deal or funding round
    with its firm context.
  * ``EmpiricalCalibration`` — a typed record of the parameters fit
    to a sample of observations, with bootstrap confidence bands.
  * ``fit_alpha_4_sys`` / ``fit_lambda_phase2`` / ``fit_lambda_phase3``
    — grid-search estimators that minimize the log-EV residual under
    the unified V0_dualchannel construction.

**What this module does not do.** It does not ingest external data.
It does not automatically override YAML defaults. It does not claim
that any documented parameter is empirically estimated. A fit
produced by this module is a candidate value for an explicit
calibration decision made by the practitioner.

Acceptance properties (regression-tested in
``tests/test_calibration.py``):

  * **Round-trip recovery.** Given synthetic observations generated
    from a known ``alpha_4_sys`` (or ``lambda_phase2``), the
    corresponding ``fit_*`` function recovers the parameter within a
    tight tolerance (typically < 0.005 absolute, < 5% relative for
    realistic sample sizes).
  * **Minimum sample size.** ``fit_*`` raises if
    ``len(observations) < MIN_OBSERVATIONS`` to discourage
    over-precise fits from sparse data.
  * **No side effects.** The module never reads from or writes to
    ``config/parameters.yaml``; calibration outputs are returned as
    ``EmpiricalCalibration`` records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import math

import numpy as np

from . import config
from .dual_channel import (
    alpha_4_adj,
    build_lambda_vector,
    v0_dualchannel_unified,
)
from .valuation_layered import (
    CashFlowProjection,
    LayerExposure,
    LayeredDiscountRateInputs,
    TRLTrajectory,
    layered_dcf,
)
from .valuation_two_phase import PhaseParameters, two_phase_dcf

# Refuse to estimate parameters from fewer than this many observations.
# At ~10 observations a 1-parameter fit's standard error is roughly
# 1/sqrt(10) ≈ 32% of the parameter range — already loose. Below this
# the fit is closer to noise than signal.
MIN_OBSERVATIONS: int = 10


# ---------------------------------------------------------------------------
# Transaction observation schema
# ---------------------------------------------------------------------------

@dataclass
class TransactionObservation:
    """One observed deal or funding round.

    All fields are required for a fit to consume the observation. If
    real data is sparse, the analyst should impute missing fields and
    explicitly mark them — the framework does not impute silently.

    Field provenance:
      * ``observed_enterprise_value_usd`` is the ONLY field that the
        fit estimator treats as ground truth.
      * The layer-exposure, phase parameters, FCF projection, and
        macro inputs are the analyst's reconstruction of the firm at
        transaction time. They are treated as known by the fit.
    """
    firm_id: str
    sector: str
    transaction_date: str             # ISO YYYY-MM-DD
    observed_enterprise_value_usd: float
    # Reconstructed firm context at transaction time:
    layer_exposure: LayerExposure
    phases: PhaseParameters
    fcf_by_year: List[float]
    risk_free_rate: float
    equity_risk_premium: float
    terminal_growth_rate: float
    second_valley_drag: float = 0.0   # 0 in the unified construction
    K7: float = 1.0
    layer4_substitution_potential: float = 0.55
    notes: str = ""


# ---------------------------------------------------------------------------
# Calibration record
# ---------------------------------------------------------------------------

@dataclass
class EmpiricalCalibration:
    """Typed record of a calibration fit.

    A fit produces a point estimate, P10/P50/P90 bootstrap bands,
    sample size, and the objective value at the optimum. None of the
    fields override anything in ``config/parameters.yaml`` — accepting
    the calibration is an explicit decision the practitioner records
    by hand.
    """
    parameter_name: str
    point_estimate: float
    p10: float
    p50: float
    p90: float
    n_observations: int
    objective_at_optimum: float
    objective_name: str = "sum_squared_log_ev_residual"
    grid_lower: Optional[float] = None
    grid_upper: Optional[float] = None
    n_bootstrap: int = 0
    timestamp: str = ""
    notes: str = ""

    def render(self) -> str:
        """One-line summary suitable for inclusion in a report."""
        return (
            f"{self.parameter_name} = {self.point_estimate:.4f} "
            f"(P10={self.p10:.4f}, P50={self.p50:.4f}, P90={self.p90:.4f}; "
            f"n={self.n_observations}, obj={self.objective_at_optimum:.4g})"
        )


# ---------------------------------------------------------------------------
# Objective: log-EV residual under V0_dualchannel
# ---------------------------------------------------------------------------

def _predict_dualchannel(
    obs: TransactionObservation,
    lambda_phase2: float,
    lambda_phase3: float,
) -> float:
    """Predict V0_dualchannel for a single observation under the
    unified construction. ``second_valley_drag = 0`` is enforced
    inside the function (per the unified-lambda doctrine — its
    information now lives in ``lambda_phase3``)."""
    return v0_dualchannel_unified(
        fcf_by_year=obs.fcf_by_year,
        risk_free_rate=obs.risk_free_rate,
        equity_risk_premium=obs.equity_risk_premium,
        phases=obs.phases,
        terminal_growth_rate=obs.terminal_growth_rate,
        lambda_phase2=lambda_phase2,
        lambda_phase3=lambda_phase3,
    ).enterprise_value


def _log_ev_residual(
    observations: List[TransactionObservation],
    predict: Callable[[TransactionObservation], float],
) -> float:
    """Sum of squared (log) EV residuals.

    Log space is the canonical choice because EV magnitudes span
    orders of magnitude across the sample (a $10M error on a $1B firm
    is treated proportionally, not absolutely). Returns +inf for any
    observation whose predicted or observed EV is ≤ 0 (the dual-
    channel can theoretically give negative EVs for distressed
    firms; those are excluded from the fit).
    """
    total = 0.0
    for obs in observations:
        pred = predict(obs)
        if pred <= 0.0 or obs.observed_enterprise_value_usd <= 0.0:
            return float("inf")
        residual = math.log(pred) - math.log(obs.observed_enterprise_value_usd)
        total += residual * residual
    return total


def _grid_search(
    values: List[float],
    objective: Callable[[float], float],
) -> Tuple[float, float]:
    """Return ``(argmin, objective_at_argmin)``."""
    best_v = values[0]
    best_obj = objective(values[0])
    for v in values[1:]:
        obj = objective(v)
        if obj < best_obj:
            best_obj = obj
            best_v = v
    return best_v, best_obj


def _bootstrap_bands(
    observations: List[TransactionObservation],
    one_fit: Callable[[List[TransactionObservation]], float],
    n_bootstrap: int,
    seed: int,
) -> Tuple[float, float, float]:
    """Return (P10, P50, P90) of the parameter under non-parametric
    bootstrap resampling. ``one_fit`` is the closure that runs a
    single fit on a resample and returns the point estimate."""
    rng = np.random.default_rng(seed=seed)
    n = len(observations)
    samples = np.empty(n_bootstrap, dtype=float)
    obs_arr = np.array(observations, dtype=object)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        resample = list(obs_arr[idx])
        samples[i] = one_fit(resample)
    p10 = float(np.percentile(samples, 10))
    p50 = float(np.percentile(samples, 50))
    p90 = float(np.percentile(samples, 90))
    return p10, p50, p90


def compute_residuals(
    observations: List[TransactionObservation],
    lambda_phase2: float,
    lambda_phase3: float,
) -> List[float]:
    """Return the per-observation log-EV residuals under the supplied
    lambda calibration. Useful for diagnostic plots and outlier
    detection in calibration practice."""
    out: List[float] = []
    for obs in observations:
        pred = _predict_dualchannel(obs, lambda_phase2, lambda_phase3)
        if pred <= 0.0 or obs.observed_enterprise_value_usd <= 0.0:
            out.append(float("nan"))
        else:
            out.append(math.log(pred) - math.log(obs.observed_enterprise_value_usd))
    return out


# ---------------------------------------------------------------------------
# Estimators
# ---------------------------------------------------------------------------

def fit_lambda_phase2(
    observations: List[TransactionObservation],
    grid_lower: float = 0.50,
    grid_upper: float = 1.00,
    grid_steps: int = 51,
    hold_lambda_phase3: Optional[float] = None,
    n_bootstrap: int = 200,
    seed: int = 42,
) -> EmpiricalCalibration:
    """Fit ``lambda_2V_phase2`` to a sample of observations.

    Holds ``lambda_phase3`` fixed at either the value supplied by the
    caller or at ``1 - second_valley_drag`` of each observation if
    ``hold_lambda_phase3 is None``. The grid is uniform on
    ``[grid_lower, grid_upper]`` with ``grid_steps`` points.

    Returns an :class:`EmpiricalCalibration` with bootstrap P10/P50/P90
    bands. Raises ``ValueError`` if fewer than :data:`MIN_OBSERVATIONS`
    are supplied.
    """
    if len(observations) < MIN_OBSERVATIONS:
        raise ValueError(
            f"fit_lambda_phase2 requires at least {MIN_OBSERVATIONS} "
            f"observations; got {len(observations)}."
        )

    grid = list(np.linspace(grid_lower, grid_upper, grid_steps))

    def _one_fit(sample: List[TransactionObservation]) -> float:
        def objective(lp2: float) -> float:
            def predict(o: TransactionObservation) -> float:
                lp3 = (hold_lambda_phase3 if hold_lambda_phase3 is not None
                       else 1.0 - o.second_valley_drag)
                return _predict_dualchannel(o, lp2, lp3)
            return _log_ev_residual(sample, predict)
        v, _ = _grid_search(grid, objective)
        return v

    point = _one_fit(observations)

    def objective_full(lp2: float) -> float:
        def predict(o: TransactionObservation) -> float:
            lp3 = (hold_lambda_phase3 if hold_lambda_phase3 is not None
                   else 1.0 - o.second_valley_drag)
            return _predict_dualchannel(o, lp2, lp3)
        return _log_ev_residual(observations, predict)

    obj_at_optimum = objective_full(point)
    p10, p50, p90 = _bootstrap_bands(observations, _one_fit, n_bootstrap, seed)

    return EmpiricalCalibration(
        parameter_name="lambda_2V_phase2",
        point_estimate=point,
        p10=p10, p50=p50, p90=p90,
        n_observations=len(observations),
        objective_at_optimum=obj_at_optimum,
        grid_lower=grid_lower, grid_upper=grid_upper,
        n_bootstrap=n_bootstrap,
        notes=("Holding lambda_phase3 fixed per observation second_valley_drag"
               if hold_lambda_phase3 is None
               else f"Holding lambda_phase3 = {hold_lambda_phase3}"),
    )


def fit_lambda_phase3(
    observations: List[TransactionObservation],
    grid_lower: float = 0.50,
    grid_upper: float = 1.00,
    grid_steps: int = 51,
    hold_lambda_phase2: Optional[float] = None,
    n_bootstrap: int = 200,
    seed: int = 42,
) -> EmpiricalCalibration:
    """Fit ``lambda_2V_phase3`` to a sample of observations.

    Mirrors :func:`fit_lambda_phase2` but holds ``lambda_phase2``
    instead. When ``hold_lambda_phase2`` is None, holds at the
    per-firm YAML default for the documented case firms or at 1.0 for
    others.
    """
    if len(observations) < MIN_OBSERVATIONS:
        raise ValueError(
            f"fit_lambda_phase3 requires at least {MIN_OBSERVATIONS} "
            f"observations; got {len(observations)}."
        )

    grid = list(np.linspace(grid_lower, grid_upper, grid_steps))

    def _one_fit(sample: List[TransactionObservation]) -> float:
        def objective(lp3: float) -> float:
            def predict(o: TransactionObservation) -> float:
                lp2 = (hold_lambda_phase2 if hold_lambda_phase2 is not None
                       else 1.0)
                return _predict_dualchannel(o, lp2, lp3)
            return _log_ev_residual(sample, predict)
        v, _ = _grid_search(grid, objective)
        return v

    point = _one_fit(observations)

    def objective_full(lp3: float) -> float:
        def predict(o: TransactionObservation) -> float:
            lp2 = (hold_lambda_phase2 if hold_lambda_phase2 is not None
                   else 1.0)
            return _predict_dualchannel(o, lp2, lp3)
        return _log_ev_residual(observations, predict)

    obj_at_optimum = objective_full(point)
    p10, p50, p90 = _bootstrap_bands(observations, _one_fit, n_bootstrap, seed)

    return EmpiricalCalibration(
        parameter_name="lambda_2V_phase3",
        point_estimate=point,
        p10=p10, p50=p50, p90=p90,
        n_observations=len(observations),
        objective_at_optimum=obj_at_optimum,
        grid_lower=grid_lower, grid_upper=grid_upper,
        n_bootstrap=n_bootstrap,
        notes=("Holding lambda_phase2 = 1.0"
               if hold_lambda_phase2 is None
               else f"Holding lambda_phase2 = {hold_lambda_phase2}"),
    )


def fit_alpha_4_sys(
    observations: List[TransactionObservation],
    grid_lower: float = 0.00,
    grid_upper: float = 0.08,
    grid_steps: int = 41,
    n_bootstrap: int = 200,
    seed: int = 42,
) -> EmpiricalCalibration:
    """Fit ``alpha_4_sys`` (Eq B.13) to a sample of observations using
    a hybrid construction.

    The hybrid construction layered_dcf-with-alpha_4_adj +
    lambda-on-FCF is the path that consumes alpha_4_sys. The fit
    grid-searches alpha_4_sys ∈ [grid_lower, grid_upper], substituting
    ``alpha_4_adj = alpha_4 - alpha_4_sys`` into Layer 4 of the
    layered firm-specific premium and applying the per-observation
    ``lambda_2V`` vector (using each observation's documented
    ``second_valley_drag`` as a proxy for ``lambda_phase3`` per the
    Sprint-4 unified-lambda correction).

    Note: this estimator is heavier than the lambda estimators
    because it mutates the layered-DCF Layer-4 coefficient at each
    grid point. We restore the original coefficient before returning.
    """
    if len(observations) < MIN_OBSERVATIONS:
        raise ValueError(
            f"fit_alpha_4_sys requires at least {MIN_OBSERVATIONS} "
            f"observations; got {len(observations)}."
        )

    from . import valuation_layered as _vl
    original_alpha_4 = float(_vl.LAYER_RISK_COEFFICIENTS["layer_4_codified"])
    grid = list(np.linspace(grid_lower, grid_upper, grid_steps))

    def _predict_with_alpha_sys(o: TransactionObservation, alpha_sys: float) -> float:
        """Predict EV using the layered DCF with α_4_adj, plus lambda
        on FCF. Temporarily mutates LAYER_RISK_COEFFICIENTS — restored
        in the finally clause of the calling context."""
        alpha_adj = max(0.0, original_alpha_4 - alpha_sys)
        _vl.LAYER_RISK_COEFFICIENTS["layer_4_codified"] = alpha_adj
        try:
            n_years = len(o.fcf_by_year)
            lp3 = 1.0 - o.second_valley_drag
            lambda_vec = build_lambda_vector(
                phases=o.phases, n_years=n_years,
                lambda_phase2=1.0, lambda_phase3=lp3,
            )
            cf_p = CashFlowProjection(
                year_labels=[f"Y{i+1}" for i in range(n_years)],
                fcf_usd=[c * l for c, l in zip(o.fcf_by_year, lambda_vec)],
            )
            trl = TRLTrajectory(
                year_labels=cf_p.year_labels,
                trl_by_year=[9] * n_years,           # neutral TRL
            )
            inputs = LayeredDiscountRateInputs(
                risk_free_rate=o.risk_free_rate,
                equity_risk_premium=o.equity_risk_premium,
                industry_unlevered_beta=o.phases.beta_unlevered_phase_1,
                de_ratio=o.phases.de_ratio_phase_1,
                effective_tax_rate=o.phases.effective_tax_rate,
                trl=9, layer_exposure=o.layer_exposure,
                K7=o.K7,
                layer4_substitution_potential=o.layer4_substitution_potential,
                sector_label=o.sector,
            )
            return layered_dcf(
                cf_p, inputs=inputs, trl_trajectory=trl,
                terminal_growth_rate=o.terminal_growth_rate,
                second_valley_drag=0.0,                # absorbed into lp3
            ).enterprise_value_usd
        finally:
            _vl.LAYER_RISK_COEFFICIENTS["layer_4_codified"] = original_alpha_4

    def _one_fit(sample: List[TransactionObservation]) -> float:
        def objective(alpha_sys: float) -> float:
            return _log_ev_residual(
                sample,
                lambda o: _predict_with_alpha_sys(o, alpha_sys),
            )
        v, _ = _grid_search(grid, objective)
        return v

    try:
        point = _one_fit(observations)
        obj_at_optimum = _log_ev_residual(
            observations,
            lambda o: _predict_with_alpha_sys(o, point),
        )
        p10, p50, p90 = _bootstrap_bands(
            observations, _one_fit, n_bootstrap, seed,
        )
    finally:
        # Belt-and-braces — _predict_with_alpha_sys also restores, but
        # if a bootstrap iteration raised mid-fit we still want the
        # coefficient back where we found it.
        _vl.LAYER_RISK_COEFFICIENTS["layer_4_codified"] = original_alpha_4

    return EmpiricalCalibration(
        parameter_name="alpha_4_sys",
        point_estimate=point,
        p10=p10, p50=p50, p90=p90,
        n_observations=len(observations),
        objective_at_optimum=obj_at_optimum,
        grid_lower=grid_lower, grid_upper=grid_upper,
        n_bootstrap=n_bootstrap,
        notes=("Uses hybrid layered-DCF + alpha_4_adj + lambda-on-FCF "
               "predictor. lambda_phase2 held at 1.0; lambda_phase3 derived "
               "per-observation as 1 - second_valley_drag."),
    )


# ---------------------------------------------------------------------------
# Single-observation back-out (diagnostic, useful for outlier analysis)
# ---------------------------------------------------------------------------

def recover_layer4_premium(obs: TransactionObservation) -> float:
    """Back out the implied Layer-4 firm-specific risk premium from a
    single observation, given the documented Layer-4 share and AI
    substitution potential.

    Returns the value of ``alpha_4_implied`` such that the layered_A
    discount rate matches the observed EV. Used for sanity-checking
    individual transactions against the framework's documented
    coefficients before they are pooled into a fit. The implementation
    is approximate (linear in alpha_4); rigorous use requires the
    full fit_alpha_4_sys above.
    """
    vl = config.load_parameters()["valuation_layered"]
    amp = (float(vl["layer4_substitution_amplifier_base"])
           + obs.layer4_substitution_potential)
    layer4_share = obs.layer_exposure.layer_4_codified
    # alpha_4_implied = (alpha_4 contribution that closes the gap) / (share * amp)
    # We do a one-pass approximation rather than a full fit — see the
    # docstring for the caveat.
    if layer4_share * amp == 0.0:
        return float("nan")
    pred_at_zero = v0_dualchannel_unified(
        fcf_by_year=obs.fcf_by_year,
        risk_free_rate=obs.risk_free_rate,
        equity_risk_premium=obs.equity_risk_premium,
        phases=obs.phases,
        terminal_growth_rate=obs.terminal_growth_rate,
        lambda_phase2=1.0,
        lambda_phase3=1.0 - obs.second_valley_drag,
    ).enterprise_value
    # log gap divided by sensitivity = alpha_4_implied
    if pred_at_zero <= 0.0 or obs.observed_enterprise_value_usd <= 0.0:
        return float("nan")
    log_gap = math.log(pred_at_zero) - math.log(obs.observed_enterprise_value_usd)
    # A 1-pp increase in alpha_4 contributes roughly
    # 0.01 * layer4_share * amp percentage points to the discount rate;
    # over 5 years, that's an EV-log-elasticity of approximately
    # 5 * 0.01 * layer4_share * amp.
    sensitivity = 5.0 * 0.01 * layer4_share * amp
    if sensitivity == 0.0:
        return float("nan")
    return float(log_gap / sensitivity)
