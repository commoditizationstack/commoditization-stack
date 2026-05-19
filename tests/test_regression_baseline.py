"""Regression baseline for the three existing valuation paths.

This test guards the byte-identical (to the cent) numerical output of:

  1. Classical Damodaran single-rate DCF              (Appendix A comparator)
  2. Appendix A layered DCF                           (TRL-modulated + layer-decomposed)
  3. Appendix B two-phase DCF                         (phase-conditional WACC + drag)

against the snapshots produced by ``scripts/freeze_regression_baseline.py``.

Subsequent additive work (e.g. the dual-channel correction of subsection
B.2.6, which introduces a fourth path V0_dualchannel) MUST NOT alter the
numerical output of any of the three existing paths. This test is the
mechanical guarantor of that contract.

If a legitimate calibration change is intended, regenerate the baseline
explicitly via ``python scripts/freeze_regression_baseline.py`` and commit
the new JSON alongside the change.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Reuse the snapshot helpers so the test computes the *same* values the
# freezer wrote — anything else would defeat the purpose.
from scripts.freeze_regression_baseline import (
    _load_scenario,
    _snapshot_appendix_a,
    _snapshot_appendix_b,
)


BASELINE_DIR = PROJECT_ROOT / "tests" / "baselines"

# Tolerance: floating-point reproducibility on the same platform is exact
# for these deterministic computations, but allow 1 cent of slack to keep
# the test robust against future Python/NumPy releases that may reorder
# arithmetic at the 16th decimal.
ABS_TOL_USD = 0.01           # one cent
REL_TOL_RATE = 1e-12         # rates are exact


def _assert_close_usd(test: unittest.TestCase, label: str,
                      actual: float, expected: float) -> None:
    delta = abs(actual - expected)
    test.assertLessEqual(
        delta, ABS_TOL_USD,
        msg=(f"{label}: {actual:,.6f} vs baseline {expected:,.6f} "
             f"(delta ${delta:,.6f}, tol ${ABS_TOL_USD}). "
             "If this change is intentional, regenerate the baseline "
             "via scripts/freeze_regression_baseline.py."),
    )


def _assert_close_rate(test: unittest.TestCase, label: str,
                       actual: float, expected: float) -> None:
    if expected == 0.0:
        test.assertAlmostEqual(actual, 0.0, places=12, msg=label)
        return
    rel = abs((actual - expected) / expected)
    test.assertLessEqual(
        rel, REL_TOL_RATE,
        msg=(f"{label}: {actual!r} vs baseline {expected!r} (rel {rel}). "
             "If this change is intentional, regenerate the baseline "
             "via scripts/freeze_regression_baseline.py."),
    )


class _BaselineMixin:
    firm_slug: str
    scenario_slug: str
    baseline_filename: str

    def _load_baseline(self) -> dict:
        with open(BASELINE_DIR / self.baseline_filename) as f:
            return json.load(f)

    def _live_snapshot(self) -> dict:
        scn = _load_scenario(self.scenario_slug)
        snap = {}
        snap.update(_snapshot_appendix_a(scn))
        snap.update(_snapshot_appendix_b(self.firm_slug))
        return snap

    def _compare_classical(self, live: dict, baseline: dict) -> None:
        prefix = f"{self.firm_slug}.path_1_classical_damodaran"
        _assert_close_usd(
            self, f"{prefix}.enterprise_value_usd",
            live["path_1_classical_damodaran"]["enterprise_value_usd"],
            baseline["path_1_classical_damodaran"]["enterprise_value_usd"],
        )
        _assert_close_usd(
            self, f"{prefix}.pv_explicit_period_usd",
            live["path_1_classical_damodaran"]["pv_explicit_period_usd"],
            baseline["path_1_classical_damodaran"]["pv_explicit_period_usd"],
        )
        _assert_close_usd(
            self, f"{prefix}.pv_terminal_usd",
            live["path_1_classical_damodaran"]["pv_terminal_usd"],
            baseline["path_1_classical_damodaran"]["pv_terminal_usd"],
        )
        _assert_close_rate(
            self, f"{prefix}.discount_rate",
            live["path_1_classical_damodaran"]["discount_rate"],
            baseline["path_1_classical_damodaran"]["discount_rate"],
        )

    def _compare_layered(self, live: dict, baseline: dict) -> None:
        prefix = f"{self.firm_slug}.path_2_layered_dcf"
        _assert_close_usd(
            self, f"{prefix}.enterprise_value_usd",
            live["path_2_layered_dcf"]["enterprise_value_usd"],
            baseline["path_2_layered_dcf"]["enterprise_value_usd"],
        )
        _assert_close_usd(
            self, f"{prefix}.pv_explicit_period_usd",
            live["path_2_layered_dcf"]["pv_explicit_period_usd"],
            baseline["path_2_layered_dcf"]["pv_explicit_period_usd"],
        )
        _assert_close_usd(
            self, f"{prefix}.pv_terminal_usd",
            live["path_2_layered_dcf"]["pv_terminal_usd"],
            baseline["path_2_layered_dcf"]["pv_terminal_usd"],
        )
        live_rates = live["path_2_layered_dcf"]["discount_rates_by_year"]
        base_rates = baseline["path_2_layered_dcf"]["discount_rates_by_year"]
        self.assertEqual(len(live_rates), len(base_rates), msg=prefix)
        for i, (lv, bv) in enumerate(zip(live_rates, base_rates)):
            _assert_close_rate(self, f"{prefix}.discount_rates_by_year[{i}]", lv, bv)

    def _compare_two_phase(self, live: dict, baseline: dict) -> None:
        prefix = f"{self.firm_slug}.path_3_two_phase_dcf"
        _assert_close_usd(
            self, f"{prefix}.enterprise_value_usd",
            live["path_3_two_phase_dcf"]["enterprise_value_usd"],
            baseline["path_3_two_phase_dcf"]["enterprise_value_usd"],
        )
        _assert_close_usd(
            self, f"{prefix}.pv_explicit_usd",
            live["path_3_two_phase_dcf"]["pv_explicit_usd"],
            baseline["path_3_two_phase_dcf"]["pv_explicit_usd"],
        )
        _assert_close_usd(
            self, f"{prefix}.pv_terminal_usd",
            live["path_3_two_phase_dcf"]["pv_terminal_usd"],
            baseline["path_3_two_phase_dcf"]["pv_terminal_usd"],
        )
        _assert_close_rate(
            self, f"{prefix}.phase_3_wacc",
            live["path_3_two_phase_dcf"]["phase_3_wacc"],
            baseline["path_3_two_phase_dcf"]["phase_3_wacc"],
        )
        live_yearly = live["path_3_two_phase_dcf"]["yearly"]
        base_yearly = baseline["path_3_two_phase_dcf"]["yearly"]
        self.assertEqual(len(live_yearly), len(base_yearly), msg=prefix)
        for ly, by in zip(live_yearly, base_yearly):
            year = ly["year"]
            self.assertEqual(ly["year"], by["year"])
            self.assertEqual(ly["phase"], by["phase"],
                             msg=f"{prefix}.yearly[year={year}].phase")
            _assert_close_rate(self, f"{prefix}.yearly[year={year}].wacc",
                               ly["wacc"], by["wacc"])
            _assert_close_rate(self, f"{prefix}.yearly[year={year}].ke",
                               ly["ke"], by["ke"])
            _assert_close_rate(self, f"{prefix}.yearly[year={year}].kd",
                               ly["kd"], by["kd"])

    def test_classical_damodaran_path(self) -> None:
        self._compare_classical(self._live_snapshot(), self._load_baseline())

    def test_appendix_a_layered_path(self) -> None:
        self._compare_layered(self._live_snapshot(), self._load_baseline())

    def test_appendix_b_two_phase_path(self) -> None:
        self._compare_two_phase(self._live_snapshot(), self._load_baseline())


class TestNeuroCertifyBaseline(_BaselineMixin, unittest.TestCase):
    firm_slug = "neurocertify"
    scenario_slug = "neurocertify"
    baseline_filename = "neurocertify.json"


class TestDataFlowProBaseline(_BaselineMixin, unittest.TestCase):
    firm_slug = "dataflow"
    scenario_slug = "dataflow_pro"
    baseline_filename = "dataflow_pro.json"


if __name__ == "__main__":
    unittest.main()
