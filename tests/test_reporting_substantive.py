"""Sprint 6 substantive tests for the Part B reporting layer.

Covers:
  * RunResult dataclass — round-trip to_dict produces the legacy shape
    that ``generate_report`` consumes.
  * funding_stage_placement — Carta-stage mapping under the three
    funding_environment settings (abundant / baseline / crowded).
  * macro_regime_dispersion_multiplier — symmetric around 0.5,
    baseline preserved exactly.
  * macro_sensitivity_grid — shape (5 × 3), acceptance check 8.1
    (regime never alters the four EVs), funding-stage placement shifts
    only with funding_environment.
  * Audience-specific section markers — each template foregrounds the
    sections the Macro Integration Proposal Section 8.2 specifies.
  * Markdown rendering — every rendered report is parseable as
    markdown text and contains no obvious template placeholders.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.reporting import (
    Audience,
    MacroSensitivityCell,
    RunResult,
    funding_stage_placement,
    generate_report,
    macro_regime_dispersion_multiplier,
    macro_sensitivity_grid,
    render_macro_sensitivity_table,
)


# ---------------------------------------------------------------------------
# Sample inputs shared across tests
# ---------------------------------------------------------------------------

def _sample_run_result() -> RunResult:
    """Roughly the DataFlow Pro numbers under the unified construction
    (Sprint 4) — chosen because they exercise every code path including
    a non-zero numerator-channel effect and a non-default lambda_phase3."""
    return RunResult(
        firm_label="DataFlow Pro (test)",
        sector="Software System & Application",
        v0_classical=75_780_000,
        v0_layered_A=28_270_000,
        v0_twophase_B=55_410_000,
        v0_dualchannel=43_400_000,
        bands={
            "v0_classical":   {"p10": 56e6, "p50": 75e6, "p90": 102e6, "mean": 78e6},
            "v0_layered_A":   {"p10": 21e6, "p50": 28e6, "p90": 37e6,  "mean": 29e6},
            "v0_twophase_B":  {"p10": 41e6, "p50": 55e6, "p90": 74e6,  "mean": 57e6},
            "v0_dualchannel": {"p10": 32e6, "p50": 43e6, "p90": 58e6,  "mean": 44e6},
        },
        numerator_channel_effect=12_010_000,
        layer_exposure={
            "layer_1_infra": 0.05, "layer_2_foundation": 0.05,
            "layer_3_capability": 0.10, "layer_4_codified": 0.55,
            "layer_5_judgment": 0.10, "layer_6_institutional": 0.10,
            "layer_7_crossborder": 0.05,
        },
        K7=0.7,
        layer4_substitution_potential=0.75,
        lambda_2V_phase2=0.70,
        lambda_2V_phase3=0.57,
        alpha_4_sys=0.03,
        macro_regime=0.5,
        funding_environment="baseline",
        funding_stage_placement=funding_stage_placement(43_400_000, "baseline"),
    )


# ---------------------------------------------------------------------------
# RunResult round-trip
# ---------------------------------------------------------------------------

class TestRunResultDataclass(unittest.TestCase):

    def test_to_dict_preserves_paths(self) -> None:
        rr = _sample_run_result()
        d = rr.to_dict()
        for k in ("v0_classical", "v0_layered_A",
                  "v0_twophase_B", "v0_dualchannel"):
            self.assertIn(k, d["paths"])
            self.assertEqual(d["paths"][k], getattr(rr, k))

    def test_to_dict_drops_none_paths(self) -> None:
        rr = RunResult(v0_classical=100e6)
        d = rr.to_dict()
        self.assertIn("v0_classical", d["paths"])
        self.assertNotIn("v0_dualchannel", d["paths"])

    def test_generate_report_accepts_to_dict_output(self) -> None:
        rr = _sample_run_result()
        rep = generate_report(Audience.INVESTOR, rr.to_dict())
        self.assertTrue(rep.body_markdown.strip())


# ---------------------------------------------------------------------------
# funding_stage_placement
# ---------------------------------------------------------------------------

class TestFundingStagePlacement(unittest.TestCase):

    def test_seed_threshold_baseline(self) -> None:
        # $15M (just below baseline seed median $16M) → pre_seed cleared,
        # next stage is seed with positive gap.
        p = funding_stage_placement(15_000_000, "baseline")
        self.assertEqual(p["cleared"], "pre_seed")
        self.assertEqual(p["next_stage"], "seed")
        self.assertAlmostEqual(p["gap_to_next_usd"], 1_000_000.0, places=2)

    def test_series_a_cleared(self) -> None:
        p = funding_stage_placement(60_000_000, "baseline")
        self.assertEqual(p["cleared"], "series_a")
        self.assertEqual(p["next_stage"], "series_b")
        self.assertGreater(p["gap_to_next_usd"], 0)

    def test_series_c_topmost(self) -> None:
        p = funding_stage_placement(500_000_000, "baseline")
        self.assertEqual(p["cleared"], "series_c")
        self.assertIsNone(p["next_stage"])
        self.assertIsNone(p["gap_to_next_usd"])

    def test_funding_environment_shifts_seed_only(self) -> None:
        ev = 18_000_000  # Above baseline seed ($16M), above crowded ($11M),
                        # but BELOW abundant seed ($22M).
        baseline = funding_stage_placement(ev, "baseline")
        abundant = funding_stage_placement(ev, "abundant")
        crowded = funding_stage_placement(ev, "crowded")
        self.assertEqual(baseline["cleared"], "seed")
        self.assertEqual(abundant["cleared"], "pre_seed")  # raised bar
        self.assertEqual(crowded["cleared"], "seed")
        # Other stages should be at their Carta medians regardless of env.
        for env_placement in (baseline, abundant, crowded):
            stage_amts = dict(env_placement["stages"])
            self.assertAlmostEqual(stage_amts["series_a"], 49_300_000)
            self.assertAlmostEqual(stage_amts["series_b"], 118_900_000)


# ---------------------------------------------------------------------------
# macro_regime_dispersion_multiplier
# ---------------------------------------------------------------------------

class TestMacroRegimeDispersion(unittest.TestCase):

    def test_baseline_is_exactly_one(self) -> None:
        self.assertEqual(macro_regime_dispersion_multiplier(0.5), 1.0)

    def test_symmetric_around_baseline(self) -> None:
        below = macro_regime_dispersion_multiplier(0.3)
        above = macro_regime_dispersion_multiplier(0.7)
        # Distances from 1.0 should be equal (symmetric around 0.5).
        self.assertAlmostEqual(1.0 - below, above - 1.0, places=10)

    def test_extremes_bounded(self) -> None:
        lo = macro_regime_dispersion_multiplier(0.0)
        hi = macro_regime_dispersion_multiplier(1.0)
        self.assertAlmostEqual(lo, 0.8, places=10)
        self.assertAlmostEqual(hi, 1.2, places=10)


# ---------------------------------------------------------------------------
# macro_sensitivity_grid (acceptance check 8.1 + shape)
# ---------------------------------------------------------------------------

class TestMacroSensitivityGrid(unittest.TestCase):

    def test_default_grid_shape(self) -> None:
        cells = macro_sensitivity_grid(_sample_run_result())
        # Default: 5 regimes × 3 environments = 15 cells.
        self.assertEqual(len(cells), 15)
        regimes = sorted({c.macro_regime for c in cells})
        envs = sorted({c.funding_environment for c in cells})
        self.assertEqual(regimes, [0.0, 0.25, 0.5, 0.75, 1.0])
        self.assertEqual(envs, ["abundant", "baseline", "crowded"])

    def test_acceptance_check_8_1_regime_does_not_change_evs(self) -> None:
        """Sweeping macro_regime MUST NOT alter any of the four EVs."""
        rr = _sample_run_result()
        original_evs = (rr.v0_classical, rr.v0_layered_A,
                        rr.v0_twophase_B, rr.v0_dualchannel)
        _ = macro_sensitivity_grid(rr)
        # The function does not mutate the input; the central EVs on
        # the RunResult remain unchanged.
        self.assertEqual(
            (rr.v0_classical, rr.v0_layered_A,
             rr.v0_twophase_B, rr.v0_dualchannel),
            original_evs,
        )

    def test_baseline_cell_dispersion_multiplier_is_one(self) -> None:
        cells = macro_sensitivity_grid(_sample_run_result())
        baseline_cells = [c for c in cells
                          if c.macro_regime == 0.5 and c.funding_environment == "baseline"]
        self.assertEqual(len(baseline_cells), 1)
        self.assertAlmostEqual(baseline_cells[0].dispersion_multiplier, 1.0, places=10)

    def test_funding_environment_changes_placement_but_regime_does_not(self) -> None:
        cells = macro_sensitivity_grid(_sample_run_result())
        # Filter cells at regime 0.5: only funding_environment varies.
        baseline_regime = [c for c in cells if c.macro_regime == 0.5]
        placements = {c.funding_environment: c.placement["cleared"]
                      for c in baseline_regime}
        # $43.4M is above the abundant seed line ($22M), above baseline
        # ($16M), above crowded ($11M) — all clear seed but NOT Series A.
        for env in ("abundant", "baseline", "crowded"):
            self.assertEqual(placements[env], "seed")

        # Holding funding_environment fixed at baseline, sweeping
        # macro_regime must NOT change placement (regime affects only
        # dispersion, not the EV).
        baseline_env = [c for c in cells if c.funding_environment == "baseline"]
        clearances = {c.macro_regime: c.placement["cleared"] for c in baseline_env}
        self.assertEqual(len(set(clearances.values())), 1,
                         msg=f"macro_regime altered placement: {clearances}")


# ---------------------------------------------------------------------------
# Audience-specific section markers (Macro Integration Proposal §8.2)
# ---------------------------------------------------------------------------

class TestAudienceSubstantiveSections(unittest.TestCase):

    def setUp(self) -> None:
        self.run_dict = _sample_run_result().to_dict()

    def _body(self, audience: Audience) -> str:
        return generate_report(audience, self.run_dict).body_markdown

    def test_investor_foregrounds_funding_stage_and_recommendation(self) -> None:
        body = self._body(Audience.INVESTOR)
        self.assertIn("Funding-stage placement", body)
        self.assertIn("Recommendation", body)
        self.assertIn("Numerator channel effect", body)

    def test_founder_foregrounds_layers_and_second_valley_reserve(self) -> None:
        body = self._body(Audience.FOUNDER)
        self.assertIn("Where the firm's value sits", body)
        self.assertIn("Cost gradient", body)
        self.assertIn("Second-valley reserve", body)
        # Layer-6 emphasis appears in the layer-exposure table.
        self.assertIn("Layer 6", body)

    def test_policy_foregrounds_k7_and_stewardship(self) -> None:
        body = self._body(Audience.POLICY)
        self.assertIn("Cross-border knowledge regime (K7)", body)
        self.assertIn("Stewardship", body)
        self.assertIn("Macro positioning", body)
        # Explicit "calibration parameters... not data-estimated" disclaimer.
        self.assertIn("calibration", body.lower())

    def test_researcher_foregrounds_equations_and_limits(self) -> None:
        body = self._body(Audience.RESEARCHER)
        self.assertIn("Equations consumed", body)
        self.assertIn("Eq B.14", body)
        self.assertIn("Eq B.15", body)
        self.assertIn("Assumption ledger", body)
        self.assertIn("Honest limits", body)

    def test_all_audiences_include_recommended_value_marker(self) -> None:
        """The dual-channel point estimate ($43.4M for the sample run)
        must appear in every audience body (recommended figure)."""
        for a in Audience:
            self.assertIn("$43.4M", self._body(a),
                          msg=f"{a.value} missing the dual-channel value")


# ---------------------------------------------------------------------------
# Markdown table rendering helper
# ---------------------------------------------------------------------------

class TestMacroSensitivityRendering(unittest.TestCase):

    def test_table_includes_header_and_rows(self) -> None:
        cells = macro_sensitivity_grid(_sample_run_result())
        md = render_macro_sensitivity_table(cells)
        # Header + alignment row + 15 data rows = 17 lines.
        self.assertEqual(len(md.splitlines()), 17)
        # Channel disclosure: every row carries the dispersion multiplier.
        for c in cells:
            disp_str = f"{c.dispersion_multiplier:.2f}"
            self.assertIn(disp_str, md)


if __name__ == "__main__":
    unittest.main()
