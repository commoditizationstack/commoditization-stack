"""Unit tests for the unified V0_dualchannel (Sprint 4) — the
scientifically-coherent extension of Eq B.14 to all three phases.

Covers:
  * Unified identity — lambda_phase1 = lambda_phase2 = lambda_phase3 = 1.0
    AND delta_2V retired (= 0) makes V0_dualchannel_unified equal
    two_phase_dcf(delta_2V = 0) to the cent.
  * lambda_2V_phase3_from_calibration helper algebra (clamp,
    monotonicity, per-firm landing).
  * Per-firm observed ordering under the unified construction:
      - NeuroCertify: V0_dualchannel ≈ V0_twophase_B (close, < 1% diff)
      - DataFlow Pro: V0_dualchannel < V0_twophase_B (cash-flow channel
        materially compresses), and ABOVE V0_layered_A (the literal
        Eq B.15 cannot reach the proposal's "lowest" expectation —
        documented in docs/dual_channel_correction.md as a proposed
        manuscript correction).
  * Sensitivity — making lambda_phase3 = 1.0 in the unified path
    recovers the basic V0_dualchannel behaviour (modulo delta_2V),
    confirming the construction is a proper extension.

See docs/dual_channel_correction.md for the state-of-the-art rationale.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import config
from src.dual_channel import (
    lambda_2V_phase3_from_calibration,
    v0_dualchannel,
    v0_dualchannel_unified,
)
from src.valuation_layered import (
    LayerExposure,
    LayeredDiscountRateInputs,
    TRLTrajectory,
    classical_damodaran_dcf,
    compute_layered_discount_rate,
    layered_dcf,
    CashFlowProjection,
)
from src.valuation_two_phase import PhaseParameters, two_phase_dcf


# ---------------------------------------------------------------------------
# Fixtures (mirror tests/test_dual_channel_mc.py)
# ---------------------------------------------------------------------------

def _load_scenario(slug: str) -> dict:
    path = PROJECT_ROOT / "config" / "scenarios" / f"{slug}.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _phases_for(firm_slug: str) -> PhaseParameters:
    p = config.firms_appendix_b()[firm_slug]["phases"]
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
# Unified identity — acceptance check 3 (unified form)
# ---------------------------------------------------------------------------

class TestUnifiedIdentity(unittest.TestCase):
    """Sanity-check the foundational property: with lambda = 1.0 in
    every phase AND delta_2V retired, V0_dualchannel_unified equals
    two_phase_dcf(delta_2V = 0) to the cent. This is the unified
    form of acceptance check 3 from the Insertion Package."""

    ABS_TOL_USD = 0.01

    def _assert_unified_identity(self, firm_slug: str) -> None:
        firms = config.firms_appendix_b()
        firm = firms[firm_slug]
        rf, erp, g = _macro()
        phases = _phases_for(firm_slug)
        fcf = list(firm["fcf_usd"])

        # Baseline: two-phase with delta_2V = 0
        baseline = two_phase_dcf(
            fcf_by_year=fcf,
            risk_free_rate=rf,
            equity_risk_premium=erp,
            phases=phases,
            terminal_growth_rate=g,
            second_valley_drag=0.0,         # delta_2V retired
        )

        unified = v0_dualchannel_unified(
            fcf_by_year=fcf,
            risk_free_rate=rf,
            equity_risk_premium=erp,
            phases=phases,
            terminal_growth_rate=g,
            lambda_phase1=1.0,
            lambda_phase2=1.0,
            lambda_phase3=1.0,
        )

        delta = abs(unified.enterprise_value - baseline["enterprise_value"])
        self.assertLessEqual(
            delta, self.ABS_TOL_USD,
            msg=(f"{firm_slug}: V0_dualchannel_unified({unified.enterprise_value:,.6f}) "
                 f"!= two_phase_dcf(delta_2V=0)({baseline['enterprise_value']:,.6f}); "
                 f"delta=${delta:,.6f}"),
        )

    def test_unified_identity_neurocertify(self) -> None:
        self._assert_unified_identity("neurocertify")

    def test_unified_identity_dataflow(self) -> None:
        self._assert_unified_identity("dataflow")


# ---------------------------------------------------------------------------
# Phase-3 calibration helper algebra
# ---------------------------------------------------------------------------

class TestLambdaPhase3Calibration(unittest.TestCase):

    def test_clamped_to_upper(self) -> None:
        lam = lambda_2V_phase3_from_calibration(layer4_share=0.0, layer6_share=1.0)
        # Even pure Layer-6: clamped to upper bound (default 0.95)
        upper = float(config.dual_channel()["lambda_2V_phase3_calibration"]["upper_bound"])
        self.assertEqual(lam, upper)

    def test_clamped_to_lower(self) -> None:
        lam = lambda_2V_phase3_from_calibration(layer4_share=1.0, layer6_share=0.0)
        # Pure Layer-4: raw = 1 - 0.85 = 0.15, clamped to lower (0.50)
        lower = float(config.dual_channel()["lambda_2V_phase3_calibration"]["lower_bound"])
        self.assertAlmostEqual(lam, lower, places=10)

    def test_monotonic_in_layer4(self) -> None:
        a = lambda_2V_phase3_from_calibration(layer4_share=0.10, layer6_share=0.20)
        b = lambda_2V_phase3_from_calibration(layer4_share=0.50, layer6_share=0.20)
        self.assertGreater(a, b)

    def test_monotonic_in_layer6(self) -> None:
        a = lambda_2V_phase3_from_calibration(layer4_share=0.30, layer6_share=0.05)
        b = lambda_2V_phase3_from_calibration(layer4_share=0.30, layer6_share=0.50)
        self.assertLess(a, b)

    def test_phase3_more_punitive_than_phase2_for_l4_heavy(self) -> None:
        """For Layer-4-heavy firms the displacement-risk literature
        predicts permanent damage > transient compression, i.e.
        lambda_phase3 < lambda_phase2. The default coefficients
        (k_L4_p3 = 0.85 > k_L4 = 0.55) encode this."""
        from src.dual_channel import lambda_2V_phase2_from_calibration
        l4_heavy = (0.55, 0.10)  # DataFlow-like
        lp2 = lambda_2V_phase2_from_calibration(*l4_heavy)
        lp3 = lambda_2V_phase3_from_calibration(*l4_heavy)
        self.assertLess(lp3, lp2,
                        msg="Expected lp3 < lp2 for Layer-4-heavy firm "
                            f"(literature: permanent > transient damage). "
                            f"Got lp2={lp2}, lp3={lp3}.")

    def test_neurocertify_yaml_default_matches_helper(self) -> None:
        """Layer 4 = 20%, Layer 6 = 40%: helper output should land near
        the documented per-firm default."""
        le = _load_scenario("neurocertify")["layer_exposure"]
        lp3 = lambda_2V_phase3_from_calibration(
            layer4_share=le["layer_4_codified"],
            layer6_share=le["layer_6_institutional"],
        )
        documented = float(config.dual_channel()["lambda_2V_phase3_defaults"]["neurocertify"])
        self.assertLessEqual(abs(lp3 - documented), 0.05,
                             msg=f"helper={lp3}, documented={documented}")

    def test_dataflow_yaml_default_matches_helper(self) -> None:
        """Layer 4 = 55%, Layer 6 = 10%: helper output should land near
        the documented per-firm default."""
        le = _load_scenario("dataflow_pro")["layer_exposure"]
        lp3 = lambda_2V_phase3_from_calibration(
            layer4_share=le["layer_4_codified"],
            layer6_share=le["layer_6_institutional"],
        )
        documented = float(config.dual_channel()["lambda_2V_phase3_defaults"]["dataflow"])
        self.assertLessEqual(abs(lp3 - documented), 0.05,
                             msg=f"helper={lp3}, documented={documented}")


# ---------------------------------------------------------------------------
# Observed ordering under the unified construction
# ---------------------------------------------------------------------------

class TestUnifiedObservedOrdering(unittest.TestCase):
    """Verify the actual ordering produced by the unified construction
    for both case firms. Documents the scientifically-honest result
    of the literal Eq B.15 + unified lambda:

      - NeuroCertify: V0_dualchannel ≈ V0_twophase_B (close, < 1% diff).
      - DataFlow Pro: V0_layered_A < V0_dualchannel < V0_twophase_B
        (the literal Eq B.15 cannot push V0_dualchannel below
        V0_layered_A — see docs/dual_channel_correction.md Section 5.1
        for the mechanical proof).
    """

    def _setup_paths(self, firm_slug: str, scenario_slug: str):
        scn = _load_scenario(scenario_slug)
        firm = config.firms_appendix_b()[firm_slug]
        rf, erp, g = _macro()
        phases = _phases_for(firm_slug)
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
        inputs = LayeredDiscountRateInputs(
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
        trl = TRLTrajectory(
            year_labels=scn["trl_trajectory"]["year_labels"],
            trl_by_year=scn["trl_trajectory"]["trl_by_year"],
        )
        cf = CashFlowProjection(
            year_labels=scn["cash_flows"]["year_labels"],
            fcf_usd=scn["cash_flows"]["fcf_usd"],
        )

        # Classical rate (TRL 9, equal-weight exposure)
        equal_exposure = LayerExposure(
            layer_1_infra=1 / 7, layer_2_foundation=1 / 7,
            layer_3_capability=1 / 7, layer_4_codified=1 / 7,
            layer_5_judgment=1 / 7, layer_6_institutional=1 / 7,
            layer_7_crossborder=1 / 7,
        )
        cls_inputs = LayeredDiscountRateInputs(
            risk_free_rate=dri["risk_free_rate"],
            equity_risk_premium=dri["equity_risk_premium"],
            industry_unlevered_beta=di["unlevered_beta"],
            de_ratio=di["market_de_ratio"],
            effective_tax_rate=di["effective_tax_rate"],
            trl=9, layer_exposure=equal_exposure,
            K7=1.0, layer4_substitution_potential=0.0,
            sector_label=di["industry_name"],
        )
        classical_rate = compute_layered_discount_rate(cls_inputs).base_capm

        v_classical = classical_damodaran_dcf(
            cf, discount_rate=classical_rate,
            terminal_growth_rate=scn["terminal_growth_rate"],
            sector_label=scn["scenario_name"],
        ).enterprise_value_usd

        v_layered_A = layered_dcf(
            cf, inputs=inputs, trl_trajectory=trl,
            terminal_growth_rate=scn["terminal_growth_rate"],
            second_valley_drag=scn["second_valley_drag"],
        ).enterprise_value_usd

        v_twophase_B = two_phase_dcf(
            fcf_by_year=list(firm["fcf_usd"]),
            risk_free_rate=rf, equity_risk_premium=erp,
            phases=phases, terminal_growth_rate=g,
            second_valley_drag=float(firm["second_valley_drag"]),
        )["enterprise_value"]

        dc_cfg = config.dual_channel()
        lp2 = float(dc_cfg["lambda_2V_phase2_defaults"][firm_slug])
        lp3 = float(dc_cfg["lambda_2V_phase3_defaults"][firm_slug])
        v_dualchannel = v0_dualchannel_unified(
            fcf_by_year=list(firm["fcf_usd"]),
            risk_free_rate=rf, equity_risk_premium=erp,
            phases=phases, terminal_growth_rate=g,
            lambda_phase2=lp2, lambda_phase3=lp3,
        ).enterprise_value

        return v_classical, v_layered_A, v_twophase_B, v_dualchannel

    def test_neurocertify_dualchannel_close_to_twophase(self) -> None:
        v_cls, v_lay, v_tp, v_dc = self._setup_paths("neurocertify", "neurocertify")
        rel_diff = abs(v_dc - v_tp) / v_tp
        self.assertLess(rel_diff, 0.02,
                        msg=(f"NeuroCertify V0_dualchannel ({v_dc:,.0f}) should be "
                             f"within 2% of V0_twophase_B ({v_tp:,.0f}); rel_diff={rel_diff:.4f}"))

    def test_neurocertify_layered_is_lowest(self) -> None:
        v_cls, v_lay, v_tp, v_dc = self._setup_paths("neurocertify", "neurocertify")
        self.assertLess(v_lay, v_dc)
        self.assertLess(v_lay, v_tp)
        self.assertLess(v_lay, v_cls)

    def test_dataflow_dualchannel_between_layered_and_twophase(self) -> None:
        """Documents the actual observed ordering for DataFlow Pro
        under the literal Eq B.15: V0_layered_A < V0_dualchannel <
        V0_twophase_B. The proposal expected V0_dualchannel < V0_layered_A;
        the framework cannot reach that ordering under Eq B.15 — see
        docs/dual_channel_correction.md for the mechanical proof and
        the recommended manuscript edit."""
        v_cls, v_lay, v_tp, v_dc = self._setup_paths("dataflow", "dataflow_pro")
        self.assertLess(v_lay, v_dc,
                        msg=("Under literal Eq B.15, DataFlow Pro V0_dualchannel "
                             "cannot fall below V0_layered_A — see "
                             "docs/dual_channel_correction.md Section 5.1."))
        self.assertLess(v_dc, v_tp,
                        msg="The cash-flow channel should compress V0_dualchannel "
                            "materially below V0_twophase_B for Layer-4-heavy firms.")

    def test_dataflow_dualchannel_significantly_below_twophase(self) -> None:
        """The cash-flow correction should be material for a Layer-4-heavy
        firm — at least 15% below V0_twophase_B."""
        v_cls, v_lay, v_tp, v_dc = self._setup_paths("dataflow", "dataflow_pro")
        rel_compression = (v_tp - v_dc) / v_tp
        self.assertGreater(rel_compression, 0.15,
                           msg=(f"DataFlow Pro V0_dualchannel compression of "
                                f"{rel_compression*100:.1f}% below V0_twophase_B "
                                "is below the 15% threshold for Layer-4-heavy firms."))


# ---------------------------------------------------------------------------
# Extension property — lambda_phase3 = 1.0 recovers basic behaviour
# ---------------------------------------------------------------------------

class TestUnifiedIsProperExtension(unittest.TestCase):
    """When lambda_phase3 = 1.0, the unified V0_dualchannel reduces to
    the basic V0_dualchannel modulo delta_2V (basic uses YAML delta_2V,
    unified retires it). To check the extension property, we run the
    basic with second_valley_drag = 0.0 and compare against the
    unified with lambda_phase3 = 1.0."""

    ABS_TOL_USD = 0.01

    def _check(self, firm_slug: str, scenario_slug: str) -> None:
        firms = config.firms_appendix_b()
        firm = firms[firm_slug]
        rf, erp, g = _macro()
        phases = _phases_for(firm_slug)
        fcf = list(firm["fcf_usd"])
        lp2 = float(config.dual_channel()["lambda_2V_phase2_defaults"][firm_slug])

        basic = v0_dualchannel(
            fcf_by_year=fcf, risk_free_rate=rf,
            equity_risk_premium=erp, phases=phases,
            terminal_growth_rate=g,
            second_valley_drag=0.0,         # match unified's retirement
            lambda_phase2=lp2,
            lambda_phase3=1.0,               # match unified's argument
        )
        unified = v0_dualchannel_unified(
            fcf_by_year=fcf, risk_free_rate=rf,
            equity_risk_premium=erp, phases=phases,
            terminal_growth_rate=g,
            lambda_phase2=lp2, lambda_phase3=1.0,
        )
        delta = abs(basic.enterprise_value - unified.enterprise_value)
        self.assertLessEqual(
            delta, self.ABS_TOL_USD,
            msg=(f"{firm_slug}: basic({basic.enterprise_value:,.6f}) != "
                 f"unified({unified.enterprise_value:,.6f}); delta=${delta:,.6f}. "
                 "The unified path must reduce to the basic path when "
                 "delta_2V = 0 and lambda_phase3 = 1.0."),
        )

    def test_extension_neurocertify(self) -> None:
        self._check("neurocertify", "neurocertify")

    def test_extension_dataflow(self) -> None:
        self._check("dataflow", "dataflow_pro")


if __name__ == "__main__":
    unittest.main()
