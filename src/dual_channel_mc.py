"""Monte Carlo for the four-path reconciliation of subsection B.2.6.

Extends the legacy single-path Monte Carlo of ``scripts/run_appendix_a.py``
into a unified sampler that drives all four paths from the SAME random
draw. This keeps the P10/P50/P90 bands coherent across paths — every
band corresponds to the same underlying set of realizations.

The sampler perturbs the following stochastic inputs:

  * ``K7``                          ~ Normal(scenario K7, 0.10)  clip [0.30, 1.00]
  * ``layer4_substitution_potential`` ~ Normal(scenario, 0.10)   clip [0.10, 0.95]
  * ``terminal_growth_rate``        ~ Normal(scenario growth, 0.01) clip [0, 0.06]
  * ``cash flow shock``             ~ Lognormal(0, 0.20) per explicit year
  * ``lambda_2V_phase2``            ~ Triangular(c - h, c, c + h)  clip [0.50, 1.00]      (new)
  * ``alpha_4_sys``                 ~ Triangular(c - h, c, c + h)  clip [0, 0.08]         (new)

The five existing dimensions match the calibration adopted by
``scripts/run_appendix_a.py::monte_carlo_layered`` so the layered-path
bands here reproduce the bands reported in Figure A.3 of the paper.

Notes on consumption of the new dimensions
------------------------------------------
* ``lambda_2V_phase2`` propagates into ``v0_dualchannel`` via the
  Phase-2 cash-flow multiplier (Eq B.14).
* ``alpha_4_sys`` is sampled but, in the basic V0_dualchannel of
  Eq B.15, does NOT propagate into any of the four EVs — V0_dualchannel
  uses the two-phase WACC + lambda only, not a hybrid layered premium
  with ``alpha_4_adj``. The sample is recorded for future hybrid
  paths and for sensitivity diagnostics; the test
  ``test_alpha_4_sys_does_not_move_dualchannel_yet`` documents this
  contract explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from . import config
from .dual_channel import v0_dualchannel
from .valuation_layered import (
    CashFlowProjection,
    LayerExposure,
    LayeredDiscountRateInputs,
    TRLTrajectory,
    classical_damodaran_dcf,
    compute_layered_discount_rate,
    layered_dcf,
)
from .valuation_two_phase import PhaseParameters, two_phase_dcf


# ---------------------------------------------------------------------------
# Spec & draw records
# ---------------------------------------------------------------------------

@dataclass
class MonteCarloSpec:
    """Distribution parameters for the unified MC sampler.

    Defaults reproduce the legacy ``monte_carlo_layered`` calibration
    so existing bands are preserved. The two new dimensions
    (``lambda_2V_phase2`` and ``alpha_4_sys``) read their distribution
    parameters from ``config.dual_channel().monte_carlo``.
    """
    n_runs: int = 5000
    seed: int = 42

    # Legacy MC dimensions
    K7_normal_std: float = 0.10
    K7_clip_lower: float = 0.30
    K7_clip_upper: float = 1.00
    sub_pot_normal_std: float = 0.10
    sub_pot_clip_lower: float = 0.10
    sub_pot_clip_upper: float = 0.95
    growth_normal_std: float = 0.01
    growth_clip_lower: float = 0.0
    growth_clip_upper: float = 0.06
    cf_shock_lognormal_sigma: float = 0.20

    # New B.2.6 dimensions (defaults loaded from YAML if left as None)
    lambda_2V_phase2_half_width: Optional[float] = None
    lambda_2V_phase2_clamp_lower: Optional[float] = None
    lambda_2V_phase2_clamp_upper: Optional[float] = None
    alpha_4_sys_half_width: Optional[float] = None
    alpha_4_sys_clamp_lower: Optional[float] = None
    alpha_4_sys_clamp_upper: Optional[float] = None

    def __post_init__(self) -> None:
        dc_mc = config.dual_channel()["monte_carlo"]
        if self.lambda_2V_phase2_half_width is None:
            self.lambda_2V_phase2_half_width = float(dc_mc["lambda_2V_phase2_half_width"])
        if self.lambda_2V_phase2_clamp_lower is None:
            self.lambda_2V_phase2_clamp_lower = float(dc_mc["lambda_2V_phase2_clamp_lower"])
        if self.lambda_2V_phase2_clamp_upper is None:
            self.lambda_2V_phase2_clamp_upper = float(dc_mc["lambda_2V_phase2_clamp_upper"])
        if self.alpha_4_sys_half_width is None:
            self.alpha_4_sys_half_width = float(dc_mc["alpha_4_sys_half_width"])
        if self.alpha_4_sys_clamp_lower is None:
            self.alpha_4_sys_clamp_lower = float(dc_mc["alpha_4_sys_clamp_lower"])
        if self.alpha_4_sys_clamp_upper is None:
            self.alpha_4_sys_clamp_upper = float(dc_mc["alpha_4_sys_clamp_upper"])


@dataclass(frozen=True)
class MonteCarloDraw:
    """Single realization of all stochastic inputs in one MC iteration."""
    K7: float
    sub_pot: float
    growth: float
    cf_shocks: List[float]
    lambda_2V_phase2: float
    alpha_4_sys: float


@dataclass
class MonteCarloResult:
    """Output of a unified Monte Carlo run.

    Arrays have shape ``(n_runs,)``. Bands are computed as P10/P50/P90
    by :func:`compute_bands`.
    """
    n_runs: int
    seed: int
    ev_classical: np.ndarray
    ev_layered_A: np.ndarray
    ev_twophase_B: np.ndarray
    ev_dualchannel: np.ndarray
    draws: List[MonteCarloDraw] = field(default_factory=list)
    bands: Dict[str, Dict[str, float]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Sampling helpers
# ---------------------------------------------------------------------------

def _sample_triangular_clamped(
    rng: np.random.Generator,
    center: float,
    half_width: float,
    clamp_lower: float,
    clamp_upper: float,
) -> float:
    """Draw from a triangular distribution centred on ``center`` with
    half-width ``half_width``, then clamp to ``[clamp_lower, clamp_upper]``.

    The triangular call uses ``(left, mode, right) = (c - h, c, c + h)``
    which is the canonical specification of a symmetric triangular.

    Degenerate case (``half_width == 0``): the distribution collapses
    to a delta at ``center``. We short-circuit because
    ``np.random.Generator.triangular`` rejects ``left == right``. This
    branch is load-bearing for the contract tests that switch off one
    dimension at a time to isolate sensitivity.
    """
    if half_width <= 0.0:
        return float(max(clamp_lower, min(clamp_upper, center)))
    left = center - half_width
    right = center + half_width
    raw = float(rng.triangular(left, center, right))
    return float(max(clamp_lower, min(clamp_upper, raw)))


def _sample_draw(
    rng: np.random.Generator,
    scenario: Dict[str, Any],
    n_explicit_years: int,
    lambda_phase2_center: float,
    alpha_4_sys_center: float,
    spec: MonteCarloSpec,
) -> MonteCarloDraw:
    K7 = float(np.clip(
        rng.normal(scenario["K7"], spec.K7_normal_std),
        spec.K7_clip_lower, spec.K7_clip_upper,
    ))
    sub_pot = float(np.clip(
        rng.normal(scenario["layer4_substitution_potential"], spec.sub_pot_normal_std),
        spec.sub_pot_clip_lower, spec.sub_pot_clip_upper,
    ))
    growth = float(np.clip(
        rng.normal(scenario["terminal_growth_rate"], spec.growth_normal_std),
        spec.growth_clip_lower, spec.growth_clip_upper,
    ))
    cf_shocks = [float(s) for s in rng.lognormal(
        0.0, spec.cf_shock_lognormal_sigma, size=n_explicit_years,
    )]
    lambda_2V = _sample_triangular_clamped(
        rng, lambda_phase2_center,
        spec.lambda_2V_phase2_half_width,
        spec.lambda_2V_phase2_clamp_lower,
        spec.lambda_2V_phase2_clamp_upper,
    )
    alpha_4_sys = _sample_triangular_clamped(
        rng, alpha_4_sys_center,
        spec.alpha_4_sys_half_width,
        spec.alpha_4_sys_clamp_lower,
        spec.alpha_4_sys_clamp_upper,
    )
    return MonteCarloDraw(
        K7=K7, sub_pot=sub_pot, growth=growth, cf_shocks=cf_shocks,
        lambda_2V_phase2=lambda_2V, alpha_4_sys=alpha_4_sys,
    )


# ---------------------------------------------------------------------------
# Path evaluators under a single draw
# ---------------------------------------------------------------------------

def _ev_classical_under_draw(
    scenario: Dict[str, Any],
    draw: MonteCarloDraw,
    classical_rate: float,
) -> float:
    cf_perturbed = CashFlowProjection(
        year_labels=scenario["cash_flows"]["year_labels"],
        fcf_usd=[float(c) * s for c, s in zip(scenario["cash_flows"]["fcf_usd"],
                                              draw.cf_shocks)],
    )
    result = classical_damodaran_dcf(
        cf_perturbed,
        discount_rate=classical_rate,
        terminal_growth_rate=draw.growth,
        sector_label=scenario.get("scenario_name", "classical"),
    )
    return float(result.enterprise_value_usd)


def _ev_layered_under_draw(
    scenario: Dict[str, Any],
    inputs: LayeredDiscountRateInputs,
    trl_traj: TRLTrajectory,
    draw: MonteCarloDraw,
) -> float:
    cf_perturbed = CashFlowProjection(
        year_labels=scenario["cash_flows"]["year_labels"],
        fcf_usd=[float(c) * s for c, s in zip(scenario["cash_flows"]["fcf_usd"],
                                              draw.cf_shocks)],
    )
    new_inputs = LayeredDiscountRateInputs(
        risk_free_rate=inputs.risk_free_rate,
        equity_risk_premium=inputs.equity_risk_premium,
        industry_unlevered_beta=inputs.industry_unlevered_beta,
        de_ratio=inputs.de_ratio,
        effective_tax_rate=inputs.effective_tax_rate,
        trl=trl_traj.trl_by_year[0],
        layer_exposure=inputs.layer_exposure,
        K7=draw.K7,
        layer4_substitution_potential=draw.sub_pot,
        sector_label=inputs.sector_label,
    )
    result = layered_dcf(
        cf_perturbed, inputs=new_inputs, trl_trajectory=trl_traj,
        terminal_growth_rate=draw.growth,
        second_valley_drag=scenario["second_valley_drag"],
    )
    return float(result.enterprise_value_usd)


def _ev_twophase_under_draw(
    fcf_by_year: List[float],
    phases: PhaseParameters,
    risk_free_rate: float,
    equity_risk_premium: float,
    second_valley_drag: float,
    draw: MonteCarloDraw,
) -> float:
    fcf_perturbed = [float(c) * s for c, s in zip(fcf_by_year, draw.cf_shocks)]
    result = two_phase_dcf(
        fcf_by_year=fcf_perturbed,
        risk_free_rate=risk_free_rate,
        equity_risk_premium=equity_risk_premium,
        phases=phases,
        terminal_growth_rate=draw.growth,
        second_valley_drag=second_valley_drag,
    )
    return float(result["enterprise_value"])


def _ev_dualchannel_under_draw(
    fcf_by_year: List[float],
    phases: PhaseParameters,
    risk_free_rate: float,
    equity_risk_premium: float,
    second_valley_drag: float,
    draw: MonteCarloDraw,
) -> float:
    fcf_perturbed = [float(c) * s for c, s in zip(fcf_by_year, draw.cf_shocks)]
    result = v0_dualchannel(
        fcf_by_year=fcf_perturbed,
        risk_free_rate=risk_free_rate,
        equity_risk_premium=equity_risk_premium,
        phases=phases,
        terminal_growth_rate=draw.growth,
        second_valley_drag=second_valley_drag,
        lambda_phase2=draw.lambda_2V_phase2,
    )
    return float(result.enterprise_value)


# ---------------------------------------------------------------------------
# Bands helper
# ---------------------------------------------------------------------------

def compute_bands(ev_array: np.ndarray) -> Dict[str, float]:
    """P10 / P50 / P90 percentile bands."""
    return {
        "p10": float(np.percentile(ev_array, 10)),
        "p50": float(np.percentile(ev_array, 50)),
        "p90": float(np.percentile(ev_array, 90)),
        "mean": float(np.mean(ev_array)),
    }


# ---------------------------------------------------------------------------
# Unified Monte Carlo over the four paths
# ---------------------------------------------------------------------------

def run_monte_carlo(
    scenario: Dict[str, Any],
    phases: PhaseParameters,
    fcf_two_phase: List[float],
    risk_free_rate_b: float,
    equity_risk_premium_b: float,
    second_valley_drag_b: float,
    classical_rate: float,
    layered_inputs: LayeredDiscountRateInputs,
    trl_traj: TRLTrajectory,
    lambda_phase2_center: float,
    alpha_4_sys_center: Optional[float] = None,
    spec: Optional[MonteCarloSpec] = None,
    keep_draws: bool = False,
) -> MonteCarloResult:
    """Run the unified Monte Carlo across the four valuation paths.

    All four paths share the SAME draw on each iteration so that the
    P10/P50/P90 bands are coherent — every band corresponds to the
    same underlying set of realizations.

    Parameters
    ----------
    scenario : dict
        The layered-path scenario (Appendix A YAML loaded as dict),
        used by the classical and layered evaluators. Provides K7,
        layer4_substitution_potential, terminal_growth_rate,
        cash_flows, second_valley_drag, and scenario_name.
    phases, fcf_two_phase, risk_free_rate_b, equity_risk_premium_b,
    second_valley_drag_b
        Appendix B fixture for the two-phase and dual-channel
        evaluators.
    classical_rate
        Pre-computed classical Damodaran single rate (the rate that
        scripts/run_appendix_a.py derives via the TRL-9 zero-premium
        trick). The MC perturbs cash flows and terminal growth but
        not this rate.
    layered_inputs, trl_traj
        Inputs to the layered DCF.
    lambda_phase2_center : float
        Per-firm Phase-2 lambda calibration center (NeuroCertify 0.95,
        DataFlow 0.70 by documented default).
    alpha_4_sys_center : float, optional
        Center for the alpha_4_sys partition. Defaults to the value
        registered under ``config.dual_channel().alpha_4_sys``.
    spec : MonteCarloSpec, optional
        Distribution parameters. Defaults to the spec assembled from
        ``config/parameters.yaml``.
    keep_draws : bool
        When True, each MonteCarloDraw is retained in ``result.draws``.
        Useful for diagnostics but consumes memory proportional to
        ``spec.n_runs``.
    """
    if spec is None:
        spec = MonteCarloSpec()
    if alpha_4_sys_center is None:
        alpha_4_sys_center = float(config.dual_channel()["alpha_4_sys"])

    rng = np.random.default_rng(seed=spec.seed)
    n = spec.n_runs

    ev_cls = np.empty(n)
    ev_lay = np.empty(n)
    ev_tp = np.empty(n)
    ev_dc = np.empty(n)
    draws: List[MonteCarloDraw] = []

    n_explicit_years = len(scenario["cash_flows"]["fcf_usd"])
    if len(fcf_two_phase) != n_explicit_years:
        raise ValueError(
            f"scenario cash_flows length {n_explicit_years} != "
            f"two-phase fcf length {len(fcf_two_phase)}; "
            "the unified MC requires matching horizons across paths."
        )

    for i in range(n):
        draw = _sample_draw(
            rng=rng, scenario=scenario, n_explicit_years=n_explicit_years,
            lambda_phase2_center=lambda_phase2_center,
            alpha_4_sys_center=alpha_4_sys_center,
            spec=spec,
        )

        ev_cls[i] = _ev_classical_under_draw(scenario, draw, classical_rate)
        ev_lay[i] = _ev_layered_under_draw(scenario, layered_inputs, trl_traj, draw)
        ev_tp[i] = _ev_twophase_under_draw(
            fcf_two_phase, phases,
            risk_free_rate_b, equity_risk_premium_b, second_valley_drag_b,
            draw,
        )
        ev_dc[i] = _ev_dualchannel_under_draw(
            fcf_two_phase, phases,
            risk_free_rate_b, equity_risk_premium_b, second_valley_drag_b,
            draw,
        )

        if keep_draws:
            draws.append(draw)

    return MonteCarloResult(
        n_runs=n,
        seed=spec.seed,
        ev_classical=ev_cls,
        ev_layered_A=ev_lay,
        ev_twophase_B=ev_tp,
        ev_dualchannel=ev_dc,
        draws=draws,
        bands={
            "v0_classical":   compute_bands(ev_cls),
            "v0_layered_A":   compute_bands(ev_lay),
            "v0_twophase_B":  compute_bands(ev_tp),
            "v0_dualchannel": compute_bands(ev_dc),
        },
    )


# ---------------------------------------------------------------------------
# Attach bands to FourPathReconciliation
# ---------------------------------------------------------------------------

def attach_bands(reconciliation, mc_result: MonteCarloResult) -> None:
    """Copy the four-path bands from a MonteCarloResult into a
    FourPathReconciliation record in place. The record's ``bands``
    field is structured as ``{path_key: {p10, p50, p90, mean}}``.
    """
    reconciliation.bands = {k: dict(v) for k, v in mc_result.bands.items()}
