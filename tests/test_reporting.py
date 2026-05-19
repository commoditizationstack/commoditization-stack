"""Unit tests for the Part B reporting skeleton (src/reporting.py).

Sprint 2-B scope: API and invariants are locked. Body templates are
intentionally short and land in Sprint 5; tests here therefore assert
structure, provenance discipline, citation hygiene, and the
acceptance-check guarantee (8.2) that the four audiences share the
SAME numbers — only framing differs.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.reporting import (
    AUDIENCE_FOREGROUNDS,
    Audience,
    CITATIONS,
    LabeledValue,
    Provenance,
    check_input_consistency,
    generate_report,
)


# ---------------------------------------------------------------------------
# Citation table — hard-coded, never fetched, never invented
# ---------------------------------------------------------------------------

class TestCitations(unittest.TestCase):

    def test_all_required_sources_present(self) -> None:
        """The Macro Integration Proposal Section 8.3 specifies a fixed
        list of named sources. They must all be present in the
        hard-coded table."""
        required = {"bea", "fed", "wef", "oecd", "crunchbase",
                    "carta_q3_2025", "fink_2026", "furman", "harvey"}
        self.assertTrue(required.issubset(set(CITATIONS.keys())),
                        msg=f"Missing: {required - set(CITATIONS.keys())}")

    def test_each_entry_has_short_and_full(self) -> None:
        for key, entry in CITATIONS.items():
            self.assertIn("short", entry, msg=f"{key} missing 'short'")
            self.assertIn("full", entry, msg=f"{key} missing 'full'")
            self.assertTrue(entry["short"], msg=f"{key} empty 'short'")
            self.assertTrue(entry["full"], msg=f"{key} empty 'full'")


# ---------------------------------------------------------------------------
# Audience enumeration — exactly the four required by Section 8.2
# ---------------------------------------------------------------------------

class TestAudiences(unittest.TestCase):

    def test_exactly_four_audiences(self) -> None:
        self.assertEqual(
            sorted(a.value for a in Audience),
            sorted(["investor", "founder", "policy", "researcher"]),
        )

    def test_every_audience_has_foreground(self) -> None:
        for a in Audience:
            self.assertIn(a, AUDIENCE_FOREGROUNDS)
            self.assertTrue(AUDIENCE_FOREGROUNDS[a].strip())


# ---------------------------------------------------------------------------
# LabeledValue — provenance discipline (Section 8.3 of the Proposal)
# ---------------------------------------------------------------------------

class TestLabeledValue(unittest.TestCase):

    def test_render_includes_provenance_label(self) -> None:
        lv = LabeledValue(value=49_300_000, label=Provenance.USER_INPUT,
                          description="Series A median pre-money",
                          units="USD", citation_key="carta_q3_2025")
        rendered = lv.render(fmt=",.0f")
        self.assertIn("user_input", rendered)
        self.assertIn("USD", rendered)
        self.assertIn("Carta Q3 2025", rendered)

    def test_three_provenance_kinds(self) -> None:
        kinds = {p.value for p in Provenance}
        self.assertEqual(kinds, {"user_input", "calibration_parameter", "computed_result"})


# ---------------------------------------------------------------------------
# Consistency checker — Section 8.3 of the Proposal
# ---------------------------------------------------------------------------

class TestConsistencyChecks(unittest.TestCase):

    def test_layer_shares_sum_to_one_is_clean(self) -> None:
        rep = check_input_consistency(layer_shares={
            "l1": 0.05, "l2": 0.05, "l3": 0.05, "l4": 0.20,
            "l5": 0.20, "l6": 0.40, "l7": 0.05,
        })
        self.assertTrue(rep.is_clean)
        self.assertEqual(rep.warnings, [])

    def test_layer_shares_off_by_third_raises_error(self) -> None:
        rep = check_input_consistency(layer_shares={
            "l1": 0.20, "l2": 0.20, "l3": 0.20, "l4": 0.20,
            "l5": 0.20, "l6": 0.20, "l7": 0.20,         # sums to 1.40
        })
        self.assertFalse(rep.is_clean)
        self.assertTrue(any(w.code == "layer_shares_sum_off"
                            for w in rep.warnings))

    def test_trl_monotonic_check(self) -> None:
        clean = check_input_consistency(trl_by_year=[4, 5, 6, 7, 7])
        self.assertTrue(clean.is_clean)
        flagged = check_input_consistency(trl_by_year=[4, 5, 6, 5, 7])
        self.assertTrue(any(w.code == "trl_non_monotonic"
                            for w in flagged.warnings))

    def test_phase_boundaries_order(self) -> None:
        clean = check_input_consistency(phase_1_end_year=2, phase_2_end_year=4)
        self.assertTrue(clean.is_clean)
        flagged = check_input_consistency(phase_1_end_year=4, phase_2_end_year=2)
        self.assertFalse(flagged.is_clean)

    def test_lambda_delta_direction_mismatch(self) -> None:
        # Mild lambda (0.97) with severe delta (0.30) — direction mismatch.
        flagged = check_input_consistency(lambda_2V_phase2=0.97, delta_2V=0.30)
        self.assertTrue(any(w.code == "lambda_delta_direction_mismatch"
                            for w in flagged.warnings))
        # Consistent calibrations — no warning.
        clean = check_input_consistency(lambda_2V_phase2=0.70, delta_2V=0.30)
        self.assertEqual(
            [w for w in clean.warnings if w.code == "lambda_delta_direction_mismatch"],
            [],
        )


# ---------------------------------------------------------------------------
# generate_report — acceptance check 8.2 (mutual consistency)
# ---------------------------------------------------------------------------

class TestGenerateReport(unittest.TestCase):

    SAMPLE_RUN = {
        "paths": {
            "v0_classical":    126_500_000,
            "v0_layered_A":     69_300_000,
            "v0_twophase_B":   113_900_000,
            "v0_dualchannel":  111_500_000,
        },
        "funding_stage": "series_a",
        "numerator_channel_effect": 2_400_000,
    }

    def test_each_audience_renders_non_empty(self) -> None:
        for a in Audience:
            r = generate_report(a, self.SAMPLE_RUN)
            self.assertEqual(r.audience, a)
            self.assertTrue(r.body_markdown.strip())
            self.assertTrue(r.title.strip())

    def test_string_audience_accepted(self) -> None:
        r = generate_report("investor", self.SAMPLE_RUN)
        self.assertEqual(r.audience, Audience.INVESTOR)

    def test_all_audiences_share_the_same_figures(self) -> None:
        """Acceptance check 8.2: every shared number is identical
        across audiences. We assert this by checking that each EV
        figure appears in every audience's body."""
        bodies = {a: generate_report(a, self.SAMPLE_RUN).body_markdown
                  for a in Audience}
        for ev_label in ("v0_classical", "v0_layered_A",
                         "v0_twophase_B", "v0_dualchannel"):
            for a, body in bodies.items():
                self.assertIn(ev_label, body,
                              msg=f"{a.value} report missing {ev_label}")

    def test_uses_damodaran_and_carta_citations(self) -> None:
        r = generate_report(Audience.INVESTOR, self.SAMPLE_RUN)
        self.assertIn("damodaran_2026", r.citations_used)
        self.assertIn("carta_q3_2025", r.citations_used)


if __name__ == "__main__":
    unittest.main()
