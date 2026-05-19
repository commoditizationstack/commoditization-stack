"""Unit tests for the unified Monte Carlo over the four valuation paths
(src/dual_channel_mc.py).

Covers:
  * Reproducibility — same seed gives byte-identical bands across runs.
  * The new triangular samplers (lambda_2V_phase2, alpha_4_sys) honour
    their clamp bounds.
  * lambda_2V_phase2 perturbation moves V0_dualchannel (DataFlow Pro)
    — the path's headline sensitivity is non-trivial.
  * alpha_4_sys does NOT move V0_dualchannel in the basic B.2.6 path
    — explicit contract documented in dual_channel_mc.py and enforced
    here.
  * Bands bracket the point estimate when half-widths and shocks are
    small (sanity).
  * attach_bands() populates the four-path reconciliation record.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.dual_channel import (
    reconcile_four_paths,
    v0_dualchannel,
)
from src.dual_channel_mc import (
    MonteCarloSpec,
    _sample_triangular_clamped,
    attach_bands,
    compute_bands,
    run_monte_carlo,
)
from src.valuation_layered import (
    LayerExposure,
    LayeredDiscountRateInputs,
    TRLTrajectory,
    compute_layered_discount_rate,
)
from src.valuation_two_phase import PhaseParameters


# ---------------------------------------------------------------------------
# Fixture builder — assembles all the inputs run_monte_carlo expects
# ---------------------------------------------------------------------------

import yaml


def _load_scenario(slug: str) -> dict:
    path = PROJECT_ROOT / "config" / "scenarios" / f"{slug}.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _build_layered_inputs(scn: dict) -> LayeredDiscountRateInputs:
    le = scn["layer_exposure"]
    exposure = LayerExposure(
        layer_1_infra=le["layer_1_infra"],
        layer_2_foundation=le["layer_2_foundation"],
        layer_3_capability=le["layer_3_capability"],
        layer_4_codified=le["layer_4_codified"],
        layer_5_judgment=le["layer_5_judgment"],
        layer_6_institutional=le["layer_6_institutional"],
        layer_7_crossborder=le["layer_7_crossborder"],
    )
    di = scn["damodaran_industry"]
    dri = scn["discount_rate_inputs"]
    return LayeredDiscountRateInputs(
        risk_free_rate=dri["risk_free_rate"],
        equity_risk_premium=dri["equity_risk_premium"],
        industry_unlevered_beta=di["unlevered_beta"],
        de_ratio=di["market_de_ratio"],
        effective_tax_rate=di["effective_tax_rate"],
        trl=scn["trl_trajectory"]["trl_by_year"][0],
        layer_exposure=exposure,
        K7=scn["K7"],
        layer4_substitution_potential=scn["layer4_substitution_potential"],
        sector_label=di["industry_name"],
    )


def _classical_rate_for(scn: dict) -> float:
    """Reproduce the TRL-9 / equal-weight trick used by run_appendix_a.py."""
    di = scn["damodaran_industry"]
    dri = scn["discount_rate_inputs"]
    eq = LayerExposure(
        layer_1_infra=1 / 7, layer_2_foundation=1 / 7,
        layer_3_capability=1 / 7, layer_4_codified=1 / 7,
        layer_5_judgment=1 / 7, layer_6_institutional=1 / 7,
        layer_7_crossborder=1 / 7,
    )
    inputs = LayeredDiscountRateInputs(
        risk_free_rate=dri["risk_free_rate"],
        equity_risk_premium=dri["equity_risk_premium"],
        industry_unlevered_beta=di["unlevered_beta"],
        de_ratio=di["market_de_ratio"],
        effective_tax_rate=di["effective_tax_rate"],
        trl=9, layer_exposure=eq, K7=1.0,
        layer4_substitution_potential=0.0,
        sector_label=di["industry_name"],
    )
    return float(compute_layered_discount_rate(inputs).base_capm)


def _build_run_kwargs(scenario_slug: str, firm_slug: str) -> dict:
    scn = _load_scenario(scenario_slug)
    firms = config.firms_appendix_b()
    firm = firms[firm_slug]
    macro = firms["macro"]
    p = firm["phases"]
    phases = PhaseParameters(
        phase_1_end_year=int(p["phase_1_end_year"]),
        phase_2_end_year=int(p["phase_2_end_year"]),
        beta_unlevered_phase_1=float(p["beta_unlevered_phase_1"]),
        beta_unlevered_phase_2=float(p["beta_unlevered_phase_2"]),
        beta_unlevered_phase_3=float(p["beta_unlevered_phase_3"]),
        de_ratio_phase_1=float(p["de_ratio_phase_1"]),
        de_ratio_phase_2=float(p["de_ratio_phase_2"]),
        de_ratio_phase_3=float(p["de_ratio_phase_3"]),
        kd_spread_phase_1=float(p["kd_spread_phase_1"]),
        kd_spread_phase_2=float(p["kd_spread_phase_2"]),
        kd_spread_phase_3=float(p["kd_spread_phase_3"]),
        effective_tax_rate=float(p["effective_tax_rate"]),
    )
    lambda_center = float(
        config.dual_channel()["lambda_2V_phase2_defaults"][firm_slug]
    )
    return dict(
        scenario=scn,
        phases=phases,
        fcf_two_phase=list(firm["fcf_usd"]),
        risk_free_rate_b=float(macro["risk_free_rate"]),
        equity_risk_premium_b=float(macro["equity_risk_premium"]),
        second_valley_drag_b=float(firm["second_valley_drag"]),
        classical_rate=_classical_rate_for(scn),
        layered_inputs=_build_layered_inputs(scn),
        trl_traj=TRLTrajectory(
            year_labels=scn["trl_trajectory"]["year_labels"],
            trl_by_year=scn["trl_trajectory"]["trl_by_year"],
        ),
        lambda_phase2_center=lambda_center,
    )


# ---------------------------------------------------------------------------
# Triangular sampler invariants
# ---------------------------------------------------------------------------

class TestTriangularSampler(unittest.TestCase):

    def test_clamps_above_upper(self) -> None:
        rng = np.random.default_rng(seed=1)
        # Center above the upper clamp — every draw should clamp.
        for _ in range(200):
            v = _sample_triangular_clamped(
                rng, center=1.5, half_width=0.10,
                clamp_lower=0.50, clamp_upper=1.00,
            )
            self.assertLessEqual(v, 1.00)

    def test_clamps_below_lower(self) -> None:
        rng = np.random.default_rng(seed=2)
        for _ in range(200):
            v = _sample_triangular_clamped(
                rng, center=0.0, half_width=0.05,
                clamp_lower=0.50, clamp_upper=1.00,
            )
            self.assertGreaterEqual(v, 0.50)

    def test_centered_draws_stay_in_band(self) -> None:
        rng = np.random.default_rng(seed=3)
        draws = [
            _sample_triangular_clamped(
                rng, center=0.70, half_width=0.10,
                clamp_lower=0.50, clamp_upper=1.00,
            )
            for _ in range(1000)
        ]
        self.assertGreaterEqual(min(draws), 0.50)
        self.assertLessEqual(max(draws), 1.00)
        # Mean of a symmetric triangular equals its mode.
        self.assertAlmostEqual(float(np.mean(draws)), 0.70, places=1)


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

class TestReproducibility(unittest.TestCase):

    def test_same_seed_same_bands(self) -> None:
        kwargs = _build_run_kwargs("dataflow_pro", "dataflow")
        spec = MonteCarloSpec(n_runs=500, seed=42)
        r1 = run_monte_carlo(spec=spec, **kwargs)
        r2 = run_monte_carlo(spec=spec, **kwargs)
        for path_key in ("v0_classical", "v0_layered_A",
                         "v0_twophase_B", "v0_dualchannel"):
            for band_key in ("p10", "p50", "p90", "mean"):
                self.assertEqual(
                    r1.bands[path_key][band_key],
                    r2.bands[path_key][band_key],
                    msg=f"{path_key}.{band_key} differs across runs at seed=42",
                )

    def test_different_seed_different_bands(self) -> None:
        kwargs = _build_run_kwargs("dataflow_pro", "dataflow")
        spec_a = MonteCarloSpec(n_runs=500, seed=42)
        spec_b = MonteCarloSpec(n_runs=500, seed=43)
        r_a = run_monte_carlo(spec=spec_a, **kwargs)
        r_b = run_monte_carlo(spec=spec_b, **kwargs)
        # At least one band on at least one path must differ.
        all_equal = all(
            r_a.bands[p][b] == r_b.bands[p][b]
            for p in ("v0_classical", "v0_layered_A",
                      "v0_twophase_B", "v0_dualchannel")
            for b in ("p10", "p50", "p90", "mean")
        )
        self.assertFalse(all_equal, "Different seeds produced identical bands")


# ---------------------------------------------------------------------------
# lambda_2V_phase2 propagation — it moves V0_dualchannel
# ---------------------------------------------------------------------------

class TestLambdaPropagation(unittest.TestCase):

    def test_lambda_perturbation_moves_dualchannel_for_dataflow(self) -> None:
        """With cf_shocks turned off and growth fixed, lambda is the
        only stochastic driver of V0_dualchannel that the dual-channel
        path consumes (beyond the macro factors that also move the
        classical and two-phase paths). We assert that the dual-channel
        std-dev > the two-phase std-dev when only lambda varies — the
        excess sensitivity is exactly the cash-flow channel."""
        kwargs = _build_run_kwargs("dataflow_pro", "dataflow")
        spec = MonteCarloSpec(
            n_runs=1000, seed=42,
            # Switch off the dimensions that hit both paths equally.
            K7_normal_std=0.0,
            sub_pot_normal_std=0.0,
            growth_normal_std=0.0,
            cf_shock_lognormal_sigma=0.0,
            # Keep the alpha_4_sys perturbation off so it doesn't pollute.
            alpha_4_sys_half_width=0.0,
            # Keep lambda perturbation on.
            lambda_2V_phase2_half_width=0.10,
        )
        result = run_monte_carlo(spec=spec, **kwargs)
        sd_tp = float(np.std(result.ev_twophase_B))
        sd_dc = float(np.std(result.ev_dualchannel))
        # Two-phase EV should be (numerically) constant — all of its
        # MC inputs are switched off.
        self.assertLess(sd_tp, 1.0, msg=f"Expected two-phase std~0, got {sd_tp}")
        # Dual-channel EV must vary because lambda is still sampled.
        self.assertGreater(sd_dc, 100.0,
                           msg=f"Expected dual-channel std>>0, got {sd_dc}")


# ---------------------------------------------------------------------------
# alpha_4_sys non-propagation — explicit contract
# ---------------------------------------------------------------------------

class TestAlphaSysNonPropagation(unittest.TestCase):
    """The basic V0_dualchannel of Eq B.15 does NOT consume alpha_4_sys.
    This test documents and enforces that contract: with everything else
    switched off and only alpha_4_sys varying, every EV must be
    identical across runs."""

    def test_alpha_4_sys_does_not_move_dualchannel_yet(self) -> None:
        kwargs = _build_run_kwargs("dataflow_pro", "dataflow")
        spec = MonteCarloSpec(
            n_runs=200, seed=42,
            K7_normal_std=0.0, sub_pot_normal_std=0.0,
            growth_normal_std=0.0, cf_shock_lognormal_sigma=0.0,
            lambda_2V_phase2_half_width=0.0,        # turn off lambda too
            alpha_4_sys_half_width=0.015,           # only alpha_4_sys varies
        )
        result = run_monte_carlo(spec=spec, **kwargs)
        for path_key, arr in (
            ("v0_classical",   result.ev_classical),
            ("v0_layered_A",   result.ev_layered_A),
            ("v0_twophase_B",  result.ev_twophase_B),
            ("v0_dualchannel", result.ev_dualchannel),
        ):
            sd = float(np.std(arr))
            self.assertLess(
                sd, 1e-6,
                msg=(f"{path_key}: alpha_4_sys perturbation moved EV "
                     f"(std={sd}); the basic B.2.6 path must not consume it."),
            )


# ---------------------------------------------------------------------------
# Bands bracket the point estimate
# ---------------------------------------------------------------------------

class TestBandsSanity(unittest.TestCase):

    def test_bands_ordered_p10_p50_p90(self) -> None:
        kwargs = _build_run_kwargs("neurocertify", "neurocertify")
        spec = MonteCarloSpec(n_runs=500, seed=42)
        result = run_monte_carlo(spec=spec, **kwargs)
        for path_key, bands in result.bands.items():
            self.assertLessEqual(bands["p10"], bands["p50"], msg=path_key)
            self.assertLessEqual(bands["p50"], bands["p90"], msg=path_key)


# ---------------------------------------------------------------------------
# compute_bands shape
# ---------------------------------------------------------------------------

class TestComputeBands(unittest.TestCase):

    def test_returns_four_keys(self) -> None:
        arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        b = compute_bands(arr)
        self.assertEqual(set(b.keys()), {"p10", "p50", "p90", "mean"})
        self.assertAlmostEqual(b["p50"], 5.5, places=6)


# ---------------------------------------------------------------------------
# attach_bands populates the FourPathReconciliation record
# ---------------------------------------------------------------------------

class TestAttachBands(unittest.TestCase):

    def test_bands_appear_on_reconciliation_record(self) -> None:
        kwargs = _build_run_kwargs("neurocertify", "neurocertify")
        spec = MonteCarloSpec(n_runs=200, seed=42)
        mc = run_monte_carlo(spec=spec, **kwargs)

        firms = config.firms_appendix_b()
        firm = firms["neurocertify"]
        macro = firms["macro"]
        dual = v0_dualchannel(
            fcf_by_year=list(firm["fcf_usd"]),
            risk_free_rate=float(macro["risk_free_rate"]),
            equity_risk_premium=float(macro["equity_risk_premium"]),
            phases=kwargs["phases"],
            terminal_growth_rate=float(macro["terminal_growth"]),
            second_valley_drag=float(firm["second_valley_drag"]),
            lambda_phase2=kwargs["lambda_phase2_center"],
        )
        rec = reconcile_four_paths(
            firm_label="NeuroCertify (test)",
            v0_classical=126_456_178.62,
            v0_layered_A=69_340_547.10,
            v0_twophase_B=dual.twophase_enterprise_value,
            dual_result=dual,
            second_valley_drag=float(firm["second_valley_drag"]),
        )
        self.assertEqual(rec.bands, {})
        attach_bands(rec, mc)
        for k in ("v0_classical", "v0_layered_A",
                  "v0_twophase_B", "v0_dualchannel"):
            self.assertIn(k, rec.bands)
            self.assertIn("p10", rec.bands[k])
            self.assertIn("p50", rec.bands[k])
            self.assertIn("p90", rec.bands[k])


if __name__ == "__main__":
    unittest.main()
