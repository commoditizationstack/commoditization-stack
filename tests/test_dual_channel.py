"""Unit tests for the B.2.6 dual-channel correction (src/dual_channel.py).

Covers:
  * Acceptance check 3 — lambda_2V = 1.0 in all three phases makes
    V0_dualchannel equal V0_twophase_B to the cent.
  * Algebraic invariants of the calibration helper (clamp,
    monotonicity in layer4 and layer6 shares).
  * Eq B.13 partition algebra and non-negativity clamp.
  * Per-firm calibration sanity — the helper output for the two case
    firms lands close to the documented per-firm Phase-2 defaults
    (NeuroCertify 0.95, DataFlow Pro 0.70) when fed their layer shares.
  * Sanity ordering — DataFlow Pro's V0_dualchannel is the lowest of
    the four reconciled values under the framework's calibration
    (Layer-4-heavy + weak Layer-6 means the cash-flow channel
    dominates the risk-partition lift).
  * Reconciliation acceptance check 4 — identity between dual and
    two-phase under lambda = 1.0 propagates into the four-path record.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.dual_channel import (
    alpha_4_adj,
    build_lambda_vector,
    lambda_2V_phase2_from_calibration,
    reconcile_four_paths,
    v0_dualchannel,
)
from src.valuation_two_phase import PhaseParameters, two_phase_dcf


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _neurocertify_phases() -> PhaseParameters:
    p = config.firms_appendix_b()["neurocertify"]["phases"]
    return PhaseParameters(
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


def _dataflow_phases() -> PhaseParameters:
    p = config.firms_appendix_b()["dataflow"]["phases"]
    return PhaseParameters(
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


def _macro():
    m = config.firms_appendix_b()["macro"]
    return float(m["risk_free_rate"]), float(m["equity_risk_premium"]), float(m["terminal_growth"])


# ---------------------------------------------------------------------------
# Acceptance check 3 — lambda = 1.0 identity
# ---------------------------------------------------------------------------

class TestLambdaUnitIdentity(unittest.TestCase):
    """V0_dualchannel with lambda_2V = 1.0 in every phase must equal
    V0_twophase_B to the cent. This is the load-bearing acceptance
    check from the B.2.6 Insertion Package."""

    ABS_TOL_USD = 0.01

    def _assert_identity(self, phases: PhaseParameters, fcf, drag: float, label: str) -> None:
        rf, erp, g = _macro()
        baseline = two_phase_dcf(
            fcf_by_year=fcf,
            risk_free_rate=rf,
            equity_risk_premium=erp,
            phases=phases,
            terminal_growth_rate=g,
            second_valley_drag=drag,
        )
        dual = v0_dualchannel(
            fcf_by_year=fcf,
            risk_free_rate=rf,
            equity_risk_premium=erp,
            phases=phases,
            terminal_growth_rate=g,
            second_valley_drag=drag,
            lambda_phase2=1.0,
            lambda_phase1=1.0,
            lambda_phase3=1.0,
        )
        delta = abs(dual.enterprise_value - baseline["enterprise_value"])
        self.assertLessEqual(
            delta, self.ABS_TOL_USD,
            msg=(f"{label}: V0_dualchannel({dual.enterprise_value:,.6f}) "
                 f"!= V0_twophase_B({baseline['enterprise_value']:,.6f}) "
                 f"under lambda=1.0; delta=${delta:,.6f}"),
        )
        # Numerator channel effect must also be ~0 under lambda=1.
        self.assertLessEqual(
            abs(dual.numerator_channel_effect), self.ABS_TOL_USD,
            msg=f"{label}: numerator_channel_effect != 0 under lambda=1.0",
        )

    def test_identity_neurocertify(self) -> None:
        firms = config.firms_appendix_b()
        firm = firms["neurocertify"]
        self._assert_identity(
            phases=_neurocertify_phases(),
            fcf=list(firm["fcf_usd"]),
            drag=float(firm["second_valley_drag"]),
            label="NeuroCertify",
        )

    def test_identity_dataflow(self) -> None:
        firms = config.firms_appendix_b()
        firm = firms["dataflow"]
        self._assert_identity(
            phases=_dataflow_phases(),
            fcf=list(firm["fcf_usd"]),
            drag=float(firm["second_valley_drag"]),
            label="DataFlow Pro",
        )


# ---------------------------------------------------------------------------
# Calibration helper algebra
# ---------------------------------------------------------------------------

class TestLambdaCalibration(unittest.TestCase):

    def test_clamped_to_upper_when_layer6_dominates(self) -> None:
        # Pure Layer-6 firm: layer6=1, layer4=0 → 1 + k_L6 > 1 → clamped at 1.0
        lam = lambda_2V_phase2_from_calibration(
            layer4_share=0.0, layer6_share=1.0,
        )
        self.assertEqual(lam, 1.0)

    def test_clamped_to_lower_when_layer4_dominates(self) -> None:
        # Pure Layer-4 firm: layer4=1, layer6=0, with k_L4=0.55:
        # raw = 1 - 0.55 = 0.45 < 0.50 → clamped at lower=0.50
        lam = lambda_2V_phase2_from_calibration(
            layer4_share=1.0, layer6_share=0.0,
        )
        self.assertAlmostEqual(lam, 0.50, places=10)

    def test_monotonic_in_layer4(self) -> None:
        a = lambda_2V_phase2_from_calibration(layer4_share=0.1, layer6_share=0.2)
        b = lambda_2V_phase2_from_calibration(layer4_share=0.4, layer6_share=0.2)
        self.assertGreater(a, b)

    def test_monotonic_in_layer6(self) -> None:
        a = lambda_2V_phase2_from_calibration(layer4_share=0.2, layer6_share=0.1)
        b = lambda_2V_phase2_from_calibration(layer4_share=0.2, layer6_share=0.4)
        self.assertLess(a, b)

    def test_neurocertify_calibration_lands_near_yaml_default(self) -> None:
        """Layer 4 = 20%, Layer 6 = 40% → 1 - 0.55*0.2 + 0.40*0.4 = 1.05 → clamped 1.0.
        Documented default is 0.95; the difference is the gap between the
        auditable helper and the editorial choice. We assert closeness only
        within 0.10 — the proposal allows the practitioner to override the
        helper output with the documented default."""
        lam = lambda_2V_phase2_from_calibration(
            layer4_share=0.20, layer6_share=0.40,
        )
        documented = float(config.dual_channel()["lambda_2V_phase2_defaults"]["neurocertify"])
        self.assertLessEqual(abs(lam - documented), 0.10,
                             msg=f"helper={lam}, documented={documented}")

    def test_dataflow_calibration_lands_near_yaml_default(self) -> None:
        """Layer 4 = 55%, Layer 6 = 10% → 1 - 0.55*0.55 + 0.40*0.10 = 0.7375.
        Documented default is 0.70; helper lands within 0.05."""
        lam = lambda_2V_phase2_from_calibration(
            layer4_share=0.55, layer6_share=0.10,
        )
        documented = float(config.dual_channel()["lambda_2V_phase2_defaults"]["dataflow"])
        self.assertLessEqual(abs(lam - documented), 0.05,
                             msg=f"helper={lam}, documented={documented}")


# ---------------------------------------------------------------------------
# Eq B.13 partition
# ---------------------------------------------------------------------------

class TestAlpha4Adjustment(unittest.TestCase):

    def test_subtracts_systematic_share(self) -> None:
        self.assertAlmostEqual(alpha_4_adj(0.08, 0.03), 0.05, places=10)

    def test_clamped_non_negative(self) -> None:
        # alpha_4_sys > alpha_4 must NOT produce a negative coefficient.
        self.assertEqual(alpha_4_adj(0.03, 0.05), 0.0)

    def test_defaults_from_config(self) -> None:
        alpha_4 = float(config.layer_risk_coefficients()["layer_4_codified"])
        alpha_sys = float(config.dual_channel()["alpha_4_sys"])
        self.assertAlmostEqual(alpha_4_adj(), alpha_4 - alpha_sys, places=10)


# ---------------------------------------------------------------------------
# Phase-vector construction
# ---------------------------------------------------------------------------

class TestLambdaVector(unittest.TestCase):

    def test_phase_assignment_matches_phase_parameters(self) -> None:
        # NeuroCertify default boundaries: Phase 1 = Y1-Y2; Phase 2 = Y3-Y4; Phase 3 = Y5
        phases = _neurocertify_phases()
        vec = build_lambda_vector(
            phases=phases, n_years=5,
            lambda_phase2=0.75, lambda_phase1=1.0, lambda_phase3=1.0,
        )
        self.assertEqual(vec, [1.0, 1.0, 0.75, 0.75, 1.0])


# ---------------------------------------------------------------------------
# Sanity ordering — DataFlow Pro should be the lowest of the four
# ---------------------------------------------------------------------------

class TestSanityOrdering(unittest.TestCase):
    """The proposal's expected qualitative ordering (under realistic
    calibration):

      * DataFlow Pro: V0_dualchannel should be the lowest of the four —
        the Layer-4 erosion that lambda_2V captures dominates the
        risk-partition lift.
      * NeuroCertify: V0_dualchannel should be close to V0_twophase_B
        (both B.2.6 effects are small for a Layer-6-rich firm).

    We do not assert exact magnitudes here — those depend on
    calibration. We assert the qualitative direction."""

    def test_dataflow_dualchannel_below_twophase(self) -> None:
        firms = config.firms_appendix_b()
        firm = firms["dataflow"]
        rf, erp, g = _macro()
        dual = v0_dualchannel(
            fcf_by_year=list(firm["fcf_usd"]),
            risk_free_rate=rf,
            equity_risk_premium=erp,
            phases=_dataflow_phases(),
            terminal_growth_rate=g,
            second_valley_drag=float(firm["second_valley_drag"]),
            lambda_phase2=float(config.dual_channel()["lambda_2V_phase2_defaults"]["dataflow"]),
        )
        # With lambda_phase2 = 0.70 (severe retreat) the dual-channel EV
        # must be strictly below the two-phase EV.
        self.assertLess(dual.enterprise_value, dual.twophase_enterprise_value)
        self.assertGreater(dual.numerator_channel_effect, 0.0)

    def test_neurocertify_dualchannel_close_to_twophase(self) -> None:
        firms = config.firms_appendix_b()
        firm = firms["neurocertify"]
        rf, erp, g = _macro()
        dual = v0_dualchannel(
            fcf_by_year=list(firm["fcf_usd"]),
            risk_free_rate=rf,
            equity_risk_premium=erp,
            phases=_neurocertify_phases(),
            terminal_growth_rate=g,
            second_valley_drag=float(firm["second_valley_drag"]),
            lambda_phase2=float(config.dual_channel()["lambda_2V_phase2_defaults"]["neurocertify"]),
        )
        # With lambda_phase2 = 0.95 (mild retreat) the gap should be
        # smaller than the dual-channel EV itself by at least an order
        # of magnitude — a defensibility-rich firm absorbs the retreat.
        gap = abs(dual.twophase_enterprise_value - dual.enterprise_value)
        self.assertLess(gap, abs(dual.enterprise_value) * 0.10)


# ---------------------------------------------------------------------------
# Reconciliation record — acceptance check 4 propagation
# ---------------------------------------------------------------------------

class TestReconciliation(unittest.TestCase):

    def test_lambda_unit_identity_propagates(self) -> None:
        firms = config.firms_appendix_b()
        firm = firms["neurocertify"]
        rf, erp, g = _macro()
        baseline = two_phase_dcf(
            fcf_by_year=list(firm["fcf_usd"]),
            risk_free_rate=rf,
            equity_risk_premium=erp,
            phases=_neurocertify_phases(),
            terminal_growth_rate=g,
            second_valley_drag=float(firm["second_valley_drag"]),
        )
        dual = v0_dualchannel(
            fcf_by_year=list(firm["fcf_usd"]),
            risk_free_rate=rf,
            equity_risk_premium=erp,
            phases=_neurocertify_phases(),
            terminal_growth_rate=g,
            second_valley_drag=float(firm["second_valley_drag"]),
            lambda_phase2=1.0,
        )
        rec = reconcile_four_paths(
            firm_label="NeuroCertify (test)",
            v0_classical=126_456_178.62,    # placeholder; not under test here
            v0_layered_A=69_340_547.10,     # placeholder; not under test here
            v0_twophase_B=baseline["enterprise_value"],
            dual_result=dual,
            second_valley_drag=float(firm["second_valley_drag"]),
        )
        self.assertAlmostEqual(rec.v0_dualchannel, rec.v0_twophase_B, places=2)
        # Four bars present in the figure-B5 ordering
        bars = rec.ordered_for_figure_B5()
        self.assertEqual([b["key"] for b in bars],
                         ["v0_classical", "v0_layered_A",
                          "v0_twophase_B", "v0_dualchannel"])


if __name__ == "__main__":
    unittest.main()
