"""Smoke tests: import every module and verify core invariants.

Run with:
    pytest tests/

Or directly:
    python -m unittest tests.test_smoke
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestImports(unittest.TestCase):
    """Every module imports without error."""

    def test_imports(self):
        from src import stack_layers, startup, investor, valuation
        from src import hype_cycle, death_valley, simulation
        self.assertTrue(hasattr(stack_layers, "KnowledgeStack"))
        self.assertTrue(hasattr(valuation, "damodaran_inverted_discount"))

    def test_streamlit_tabs_import(self):
        """Sprint 7 — the new tab_reports module and its integration in
        streamlit_app must import without error (catches signature drift
        between src.reporting and the Streamlit tab)."""
        from app.tabs import tab_reports, tab_appendix_b
        from app import streamlit_app
        self.assertTrue(hasattr(tab_reports, "render"))
        self.assertTrue(hasattr(tab_appendix_b, "render"))
        self.assertTrue(hasattr(streamlit_app, "main"))

    def test_b26_figures_in_pdf_manifest(self):
        """Sprint 7 — the three B.2.6 figures (6-bis/B.3, B.4, B.5) must
        appear in the PDF export manifest so the static PDF carries
        them alongside the existing Appendix B figures."""
        from app.shared.pdf_export import FIGURE_MANIFEST
        b26_files = {entry[1] for entry in FIGURE_MANIFEST
                      if "B.2.6" in entry[0]}
        self.assertEqual(b26_files, {
            "fig_b26_geometry.png",
            "fig_b26_risk_partition_and_lambda_fcf.png",
            "fig_b26_four_path_reconciliation.png",
        })

    def test_figure_a3_and_b1_caption_cross_reference_b5(self):
        """Sprint 9 — Figure A.3 (fig18_valuation_comparison.png) and
        Figure B.1 (fig19_two_phase_cost_of_capital.png) captions must
        each mention Figure B.5 so the reader of the single-channel
        figures is pointed at the dual-channel reconciliation. This
        is the manuscript edit prescribed in the Insertion Package
        Section 5 ("Caption note for existing figures")."""
        from app.shared.pdf_export import FIGURE_MANIFEST
        caps = {entry[1]: entry[2] for entry in FIGURE_MANIFEST}
        for fname in ("fig18_valuation_comparison.png",
                      "fig19_two_phase_cost_of_capital.png"):
            self.assertIn(fname, caps,
                          msg=f"{fname} missing from PDF manifest")
            self.assertIn("Figure B.5", caps[fname],
                          msg=f"{fname} caption does not cross-reference Figure B.5")
            self.assertIn("single-channel", caps[fname].lower(),
                          msg=f"{fname} caption does not flag itself as single-channel")


class TestInvertedDiscountInvariants(unittest.TestCase):
    """The inverted discount must reduce to classical when below threshold,
    and must invert sign under stated conditions."""

    def test_below_threshold_matches_classical(self):
        from src.valuation import damodaran_classical_discount, damodaran_inverted_discount
        ev = 100_000_000
        rate = 0.18
        classical_v, _ = damodaran_classical_discount(ev, key_person_discount_rate=rate)
        inverted_v, comp = damodaran_inverted_discount(
            ev, team_layer4_share=0.30, ai_substitution_potential_layer4=0.60,
            threshold_layer4_share=0.55, classical_discount_rate=rate,
        )
        self.assertAlmostEqual(classical_v, inverted_v, places=2)
        self.assertEqual(comp["regime"], "classical")

    def test_inverts_under_stated_conditions(self):
        from src.valuation import damodaran_inverted_discount
        ev = 100_000_000
        # high share, high substitutability -> regime should be inverted
        _, comp = damodaran_inverted_discount(
            ev, team_layer4_share=0.85, ai_substitution_potential_layer4=0.85,
            threshold_layer4_share=0.55,
        )
        self.assertEqual(comp["regime"], "inverted")
        self.assertLess(comp["effective_discount_rate"], 0.0)


class TestStackLayers(unittest.TestCase):
    def test_substitutability_bounded(self):
        from src.stack_layers import StackLayer
        layer = StackLayer("test", "Test", velocity=0.30, substitutability_2026=0.70)
        for y in [-2, 0, 2, 8, 20]:
            s = layer.substitutability_at(y)
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 1.0)

    def test_anti_commoditizing_layer_decays(self):
        from src.stack_layers import StackLayer
        layer = StackLayer("test", "Test", velocity=-0.10, substitutability_2026=0.20)
        s_now = layer.substitutability_at(0)
        s_future = layer.substitutability_at(5)
        self.assertLess(s_future, s_now)


class TestSimulationRuns(unittest.TestCase):
    def test_smoke_run(self):
        from src.simulation import load_scenario, run_single_simulation
        cfg = load_scenario(
            PROJECT_ROOT / "config" / "scenarios" / "post_genai_2026.yaml",
            PROJECT_ROOT / "config" / "parameters.yaml",
        )
        result = run_single_simulation(cfg)
        self.assertGreater(result.months_run, 0)
        self.assertIn("damodaran_inverted", result.valuations_at_exit)


# ----------------------------------------------------------------------------
# Tests for the new Phase-1 modules (migration_dynamics, streaming_case,
# fiscal_blocs, fragility, upstream_chain, distributional)
# ----------------------------------------------------------------------------

class TestPhase1NewModules(unittest.TestCase):
    """All new Phase-1 modules import and execute their primary entry points."""

    def test_migration_dynamics_imports(self):
        from src import migration_dynamics
        self.assertTrue(hasattr(migration_dynamics, "compute_migration"))
        self.assertTrue(hasattr(migration_dynamics, "reference_firm_migration"))

    def test_migration_reference_firm_us(self):
        from src.migration_dynamics import reference_firm_migration
        r = reference_firm_migration("united_states")
        self.assertEqual(r.n_substitutable + r.n_retained, 50)
        # US should break even within the 5-year horizon
        self.assertIsNotNone(r.break_even_quarter)
        self.assertGreater(r.cumulative_5y_post_t0_usd, 0)

    def test_migration_orchestrator_floor_for_small_firm(self):
        from src.migration_dynamics import compute_migration, MigrationParameters
        # Tiny firm — orchestrator floor must keep n_orchestrators >= 1 if subst > 0
        r = compute_migration(MigrationParameters(
            n_total_engineers=8, substitution_fraction=0.50,
            jurisdiction="united_states",
        ))
        self.assertGreaterEqual(r.n_orchestrators, 1)

    def test_layer_risk_alpha_overrides_take_precedence(self):
        """The optional alpha_overrides on LayeredDiscountRateInputs must
        replace the YAML-canonical Appendix-A.2 coefficients per key,
        falling back when a key is absent."""
        from src.valuation_layered import (
            LayerExposure,
            layer_decomposed_risk_premium,
            LAYER_RISK_COEFFICIENTS,
        )
        exposure = LayerExposure(
            layer_1_infra=0.10, layer_2_foundation=0.10, layer_3_capability=0.10,
            layer_4_codified=0.30, layer_5_judgment=0.20,
            layer_6_institutional=0.15, layer_7_crossborder=0.05,
        )
        base_total, _ = layer_decomposed_risk_premium(exposure)
        # Boost α_6 institutional (which is normally protective ≈ -0.06)
        # to a strongly protective -0.20 — total premium must drop.
        boosted_protective, _ = layer_decomposed_risk_premium(
            exposure, alpha_overrides={"layer_6_institutional": -0.20},
        )
        self.assertLess(boosted_protective, base_total)
        # Per-key fallback: an override for only one layer must leave the
        # others on their YAML default.
        partial, partial_breakdown = layer_decomposed_risk_premium(
            exposure, alpha_overrides={"layer_1_infra": 0.0},
        )
        self.assertEqual(partial_breakdown["layer_1_infra"], 0.0)
        # layer_3 untouched → uses paper default
        self.assertAlmostEqual(
            partial_breakdown["layer_3_capability"],
            LAYER_RISK_COEFFICIENTS["layer_3_capability"] * 0.10,
        )

    def test_migration_global_overrides_take_precedence(self):
        """The Optional override fields on MigrationParameters must take
        precedence over the YAML defaults — this is the contract the
        website's Advanced parameters lab depends on."""
        from src.migration_dynamics import compute_migration, MigrationParameters
        base = compute_migration(MigrationParameters(
            n_total_engineers=50, substitution_fraction=0.60,
            jurisdiction="united_states",
        ))
        # Override the orchestrator ratio to 1:20 (instead of YAML 1:10) —
        # halves the orchestrator headcount, so orchestrator annual cost drops.
        overridden = compute_migration(MigrationParameters(
            n_total_engineers=50, substitution_fraction=0.60,
            jurisdiction="united_states",
            orchestrator_ratio=20.0,
        ))
        self.assertLess(overridden.n_orchestrators, base.n_orchestrators)
        self.assertLess(
            overridden.annual_orchestrator_cost_usd,
            base.annual_orchestrator_cost_usd,
        )
        # Override AI tooling cost to zero — net annual saving rises.
        no_tooling = compute_migration(MigrationParameters(
            n_total_engineers=50, substitution_fraction=0.60,
            jurisdiction="united_states",
            ai_tooling_cost_per_dev_usd_year=0.0,
        ))
        self.assertGreater(
            no_tooling.annual_net_saving_usd,
            base.annual_net_saving_usd,
        )

    def test_streaming_case_decomposition(self):
        from src.streaming_case import (
            incumbent_price_decomposition, run_three_scenarios)
        inc = incumbent_price_decomposition()
        # Total must match standard plan price within float tolerance
        self.assertAlmostEqual(inc.total, 15.49, places=2)
        # Content must be 50% of price
        self.assertAlmostEqual(inc.content_licensing, 15.49 * 0.50, places=2)

        results = run_three_scenarios()
        self.assertEqual(len(results), 3)
        # Entrant prices must be strictly below incumbent in all three scenarios
        for r in results:
            self.assertLess(r.entrant.total, r.incumbent.total)
            # Aggressive scenario must produce larger reduction than conservative
        self.assertGreater(results[2].price_reduction_pct,
                           results[0].price_reduction_pct)

    def test_fiscal_blocs_projection(self):
        from src.fiscal_blocs import project_all_blocs
        blocs = project_all_blocs()
        self.assertEqual(set(blocs.keys()),
                         {"brazil", "france", "united_states"})
        # Brazil and France net impact should be positive (revenue loss);
        # US should be negative (revenue gain).
        self.assertGreater(blocs["brazil"].net_impact_usd_millions, 0)
        self.assertGreater(blocs["france"].net_impact_usd_millions, 0)
        self.assertLess(blocs["united_states"].net_impact_usd_millions, 0)

    def test_fragility_case_studies(self):
        from src.fragility import case_studies_fragility
        f = case_studies_fragility()
        # NeuroCertify must be resilient; DataFlow Pro must be fragile
        self.assertEqual(f["neurocertify"].zone, "resilient")
        self.assertEqual(f["dataflow_pro"].zone, "fragile")
        # NeuroCertify index must be negative; DataFlow positive
        self.assertLess(f["neurocertify"].fragility_index, 0)
        self.assertGreater(f["dataflow_pro"].fragility_index, 0)

    def test_upstream_chain_seven_categories(self):
        from src.upstream_chain import all_categories
        cats = all_categories()
        self.assertEqual(len(cats), 7)
        slugs = [c.slug for c in cats]
        self.assertIn("frontier_labs", slugs)
        self.assertIn("hyperscalers", slugs)

    def test_upstream_capex_sensitivity_decay(self):
        from src.upstream_chain import capex_sensitivity_curves
        t, train, infer = capex_sensitivity_curves()
        # At zero tightness both indices should be ~100
        self.assertAlmostEqual(train[0], 100.0, places=0)
        self.assertAlmostEqual(infer[0], 100.0, places=0)
        # Training capex must decay faster than inference
        self.assertLess(train[-1], infer[-1])

    def test_distributional_double_threshold(self):
        from src.distributional import compute_double_threshold
        d = compute_double_threshold()
        # Compliance threshold must be higher than economic threshold
        # (XAI infra floor > orchestrator floor alone)
        self.assertGreater(d.compliance_break_even, d.economic_break_even)

    def test_distributional_xai_gap_widens_as_k_falls(self):
        from src.distributional import compute_xai_capacity_gap
        x = compute_xai_capacity_gap()
        # Gap at K=0.45 must be larger than at K=1.0
        self.assertGreater(x.endpoint_gaps["k_0_45"],
                           x.endpoint_gaps["k_1_0"])


if __name__ == "__main__":
    unittest.main()
