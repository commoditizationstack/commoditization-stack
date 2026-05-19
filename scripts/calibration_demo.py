"""End-to-end synthetic calibration demo for the Sprint 8 scaffolding.

Generates 60 synthetic transactions from a known
(lambda_2V_phase2, lambda_2V_phase3) generator, runs the sequential
estimation prescribed in docs/empirical_calibration_program.md
Section 2.2, and prints the recovered values with bootstrap bands and
residual diagnostics.

This is **not** an empirical calibration. It is a demonstration that
the estimator implementation in src/calibration.py recovers known
parameters from data sampled from the SAME generator the framework
uses for valuation. When real transaction data becomes available,
the same workflow applies — only the data source changes.

Usage:
    python scripts/calibration_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from src.calibration import (
    compute_residuals,
    fit_lambda_phase2,
    fit_lambda_phase3,
    fit_alpha_4_sys,
    recover_layer4_premium,
)
from src.dual_channel import v0_dualchannel_unified
from src.valuation_layered import LayerExposure
from src.valuation_two_phase import PhaseParameters
from src.calibration import TransactionObservation


# ---------------------------------------------------------------------------
# Synthetic data generator (mirrors tests/test_calibration.py)
# ---------------------------------------------------------------------------

TRUE_LAMBDA_P2 = 0.70
TRUE_LAMBDA_P3 = 0.85
N_OBSERVATIONS = 60
NOISE_SIGMA = 0.05


def _default_phases() -> PhaseParameters:
    return PhaseParameters(
        phase_1_end_year=2, phase_2_end_year=4,
        beta_unlevered_phase_1=1.0, beta_unlevered_phase_2=1.3,
        beta_unlevered_phase_3=1.1,
        de_ratio_phase_1=0.05, de_ratio_phase_2=0.12, de_ratio_phase_3=0.10,
        kd_spread_phase_1=0.03, kd_spread_phase_2=0.06, kd_spread_phase_3=0.04,
        effective_tax_rate=0.06,
    )


def _exposure(layer4_share: float, layer6_share: float) -> LayerExposure:
    other = max(0.0, 1.0 - layer4_share - layer6_share)
    per = other / 5.0
    return LayerExposure(
        layer_1_infra=per, layer_2_foundation=per, layer_3_capability=per,
        layer_4_codified=layer4_share, layer_5_judgment=per,
        layer_6_institutional=layer6_share, layer_7_crossborder=per,
    )


def _generate_observations(n: int, seed: int = 7) -> list:
    rng = np.random.default_rng(seed=seed)
    phases = _default_phases()
    template_fcf = [-1_000_000, 500_000, 2_000_000, 5_000_000, 9_000_000]
    obs = []
    for i in range(n):
        layer4 = float(rng.uniform(0.15, 0.55))
        layer6 = float(rng.uniform(0.10, 0.30))
        scale = float(rng.uniform(0.5, 1.5))
        fcf = [c * scale for c in template_fcf]
        true_ev = v0_dualchannel_unified(
            fcf_by_year=fcf, risk_free_rate=0.0425,
            equity_risk_premium=0.055, phases=phases,
            terminal_growth_rate=0.03,
            lambda_phase2=TRUE_LAMBDA_P2,
            lambda_phase3=TRUE_LAMBDA_P3,
        ).enterprise_value
        observed = max(1e3, true_ev * float(rng.lognormal(0.0, NOISE_SIGMA)))
        obs.append(TransactionObservation(
            firm_id=f"firm_{i:03d}",
            sector="synthetic",
            transaction_date="2026-01-01",
            observed_enterprise_value_usd=observed,
            layer_exposure=_exposure(layer4, layer6),
            phases=phases,
            fcf_by_year=fcf,
            risk_free_rate=0.0425,
            equity_risk_premium=0.055,
            terminal_growth_rate=0.03,
            second_valley_drag=1.0 - TRUE_LAMBDA_P3,
            K7=0.7, layer4_substitution_potential=0.55,
        ))
    return obs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 72)
    print("Sprint 8 - Empirical calibration demo (synthetic data)")
    print("=" * 72)
    print()
    print(f"  Generator: lambda_phase2 = {TRUE_LAMBDA_P2:.2f}, "
          f"lambda_phase3 = {TRUE_LAMBDA_P3:.2f}")
    print(f"  Noise:     Lognormal(0, sigma = {NOISE_SIGMA})")
    print(f"  Sample:    n = {N_OBSERVATIONS}")
    print()
    print("Sequential estimation (per docs/empirical_calibration_program.md Section2.2):")
    print()

    obs = _generate_observations(N_OBSERVATIONS, seed=7)

    # Step 1: fit lambda_phase3 first (most identifiable).
    print("Step 1 — fit lambda_phase3 (holding lambda_phase2 = 1.0)")
    cal_lp3 = fit_lambda_phase3(
        obs, hold_lambda_phase2=1.0, n_bootstrap=100, seed=11,
    )
    print(f"  ->{cal_lp3.render()}")
    print(f"    abs error vs generator: "
          f"{abs(cal_lp3.point_estimate - TRUE_LAMBDA_P3):.4f}")
    print()

    # Step 2: fit lambda_phase2 holding lambda_phase3 at step-1 estimate.
    print(f"Step 2 — fit lambda_phase2 (holding lambda_phase3 = "
          f"{cal_lp3.point_estimate:.3f})")
    cal_lp2 = fit_lambda_phase2(
        obs, hold_lambda_phase3=cal_lp3.point_estimate,
        n_bootstrap=100, seed=13,
    )
    print(f"  ->{cal_lp2.render()}")
    print(f"    abs error vs generator: "
          f"{abs(cal_lp2.point_estimate - TRUE_LAMBDA_P2):.4f}")
    print()

    # Step 3: fit alpha_4_sys (heavier, hybrid construction).
    print("Step 3 — fit alpha_4_sys (hybrid construction)")
    cal_alpha = fit_alpha_4_sys(obs, n_bootstrap=50, seed=17)
    print(f"  ->{cal_alpha.render()}")
    print()

    # The sequential procedure above is honest about what the data
    # identifies. Lambda_phase3 is well-identified because most EV
    # sits in the perpetuity (driven by Phase-3 FCF). Lambda_phase2
    # is poorly identified once Lambda_phase3 is fixed at a
    # slightly-off step-1 estimate, because the two parameters partly
    # substitute in fitting EV. This is the identifiability caveat
    # discussed in docs/empirical_calibration_program.md Section 2.2.
    # Below: residual diagnostics show what the calibration captures
    # despite the sequential error propagation.
    print("Note: lambda_phase2 may show a larger error than lambda_phase3")
    print("      because the two parameters partly substitute in fitting EV.")
    print("      The residual diagnostics below show the actual fit quality.")
    print()

    # Diagnostics: residuals at the recovered calibration.
    residuals = compute_residuals(
        obs,
        lambda_phase2=cal_lp2.point_estimate,
        lambda_phase3=cal_lp3.point_estimate,
    )
    abs_res = [abs(r) for r in residuals if not np.isnan(r)]
    print("Residual diagnostics at the recovered calibration:")
    print(f"  Mean abs residual:     {np.mean(abs_res):.4f}")
    print(f"  Median abs residual:   {np.median(abs_res):.4f}")
    print(f"  90th percentile:       {np.percentile(abs_res, 90):.4f}")
    print(f"  Max abs residual:      {max(abs_res):.4f}")
    print()

    # Single-observation back-out on the first three firms.
    print("Single-obs Layer-4 premium back-out (first 3 firms):")
    for o in obs[:3]:
        premium = recover_layer4_premium(o)
        print(f"  {o.firm_id}: implied alpha_4 ~ {premium:.4f}")
    print()

    print("=" * 72)
    print("Done. None of these values overrode config/parameters.yaml — by")
    print("design, calibration outputs are records, not silent rewrites.")
    print("=" * 72)


if __name__ == "__main__":
    main()
