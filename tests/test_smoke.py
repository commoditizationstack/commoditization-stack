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


if __name__ == "__main__":
    unittest.main()
