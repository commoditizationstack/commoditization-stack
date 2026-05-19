"""Smoke tests for the three B.2.6 figure generators (Sprint 5).

The figure functions are pure matplotlib (no I/O, no Streamlit state),
so the tests just verify that:
  · Each function returns a Figure that can be rendered.
  · The number of axes matches the expected layout.
  · Bar / line counts match the expected number of paths or firms.

Visual review is done by inspecting the rendered files under
``outputs/figures/`` (see ``scripts/run_b26_figures.py``).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib

# Force a non-interactive backend before matplotlib.pyplot is imported.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from app.shared.live_figures import (  # noqa: E402
    DATAFLOW_COLOR,
    NEUROCERTIFY_COLOR,
    figure_b3_dualchannel_geometry,
    figure_b4_risk_partition_and_corrected_fcf,
    figure_b5_four_path_reconciliation,
)


class TestFigureB3Geometry(unittest.TestCase):

    def test_returns_figure_with_two_axes(self) -> None:
        fig = figure_b3_dualchannel_geometry(formal_labels=True)
        try:
            self.assertEqual(len(fig.axes), 2)   # revenue + WACC panels
        finally:
            plt.close(fig)

    def test_formal_labels_flag(self) -> None:
        fig_formal = figure_b3_dualchannel_geometry(formal_labels=True)
        fig_plain = figure_b3_dualchannel_geometry(formal_labels=False)
        try:
            # Title differs between the two modes.
            self.assertNotEqual(fig_formal._suptitle.get_text(),
                                fig_plain._suptitle.get_text())
        finally:
            plt.close(fig_formal)
            plt.close(fig_plain)


class TestFigureB4RiskPartition(unittest.TestCase):

    def _sample_firms(self) -> dict:
        return {
            "neurocertify": {
                "label": "NeuroCertify (deep-tech, HIT)",
                "color": NEUROCERTIFY_COLOR,
                "layer4_share": 0.20,
                "ai_substitution_potential": 0.50,
                "alpha_4": 0.08,
                "alpha_4_sys": 0.03,
                "amp_base": 0.50,
                "fcf_proj": [-1_500_000, -800_000, 1_200_000, 5_500_000, 12_000_000],
                "lambda_vector": [1.0, 1.0, 0.95, 0.95, 0.95],
                "phase_boundaries": (2, 4),
            },
            "dataflow": {
                "label": "DataFlow Pro (Software, commoditizing)",
                "color": DATAFLOW_COLOR,
                "layer4_share": 0.55,
                "ai_substitution_potential": 0.75,
                "alpha_4": 0.08,
                "alpha_4_sys": 0.03,
                "amp_base": 0.50,
                "fcf_proj": [-1_200_000, 800_000, -200_000, 4_000_000, 9_500_000],
                "lambda_vector": [1.0, 1.0, 0.70, 0.70, 0.57],
                "phase_boundaries": (2, 4),
            },
        }

    def test_returns_figure_with_two_panels(self) -> None:
        fig = figure_b4_risk_partition_and_corrected_fcf(firms=self._sample_firms())
        try:
            self.assertEqual(len(fig.axes), 2)
        finally:
            plt.close(fig)

    def test_upper_panel_has_one_bar_per_firm(self) -> None:
        firms = self._sample_firms()
        fig = figure_b4_risk_partition_and_corrected_fcf(firms=firms)
        try:
            ax_top = fig.axes[0]
            # Stacked bars: each firm contributes 2 patches (sys + idio).
            # Total patches on the upper panel = 2 * n_firms.
            n_bars = sum(1 for p in ax_top.patches)
            self.assertEqual(n_bars, 2 * len(firms))
        finally:
            plt.close(fig)


class TestFigureB5Reconciliation(unittest.TestCase):

    def _sample_firms(self) -> dict:
        bands = {
            "v0_classical":   {"p10": 92e6,  "p50": 125e6, "p90": 177e6, "mean": 130e6},
            "v0_layered_A":   {"p10": 52e6,  "p50": 69e6,  "p90": 92e6,  "mean": 70e6},
            "v0_twophase_B":  {"p10": 95e6,  "p50": 131e6, "p90": 187e6, "mean": 135e6},
            "v0_dualchannel": {"p10": 95e6,  "p50": 131e6, "p90": 186e6, "mean": 134e6},
        }
        return {
            "neurocertify": {
                "label": "NeuroCertify (deep-tech, HIT)",
                "color": NEUROCERTIFY_COLOR,
                "v0_classical":   126.5e6,
                "v0_layered_A":   69.3e6,
                "v0_twophase_B":  113.9e6,
                "v0_dualchannel": 113.3e6,
                "bands": bands,
            },
            "dataflow": {
                "label": "DataFlow Pro (Software, commoditizing)",
                "color": DATAFLOW_COLOR,
                "v0_classical":   75.8e6,
                "v0_layered_A":   28.3e6,
                "v0_twophase_B":  55.4e6,
                "v0_dualchannel": 43.4e6,
                "bands": bands,
            },
        }

    def _funding_lines(self) -> dict:
        return {"seed": 16e6, "series_a": 49.3e6, "series_b": 118.9e6}

    def test_returns_figure_with_one_axis_per_firm(self) -> None:
        firms = self._sample_firms()
        fig = figure_b5_four_path_reconciliation(
            firms=firms, funding_stage_lines=self._funding_lines(),
        )
        try:
            self.assertEqual(len(fig.axes), len(firms))
        finally:
            plt.close(fig)

    def test_each_subplot_has_four_bars(self) -> None:
        firms = self._sample_firms()
        fig = figure_b5_four_path_reconciliation(
            firms=firms, funding_stage_lines=self._funding_lines(),
        )
        try:
            for ax in fig.axes:
                bars = [p for p in ax.patches]
                self.assertEqual(len(bars), 4,
                                 msg=f"Expected 4 bars per firm, got {len(bars)}")
        finally:
            plt.close(fig)

    def test_handles_missing_bands_gracefully(self) -> None:
        firms = self._sample_firms()
        # Drop bands from one firm — figure should still render.
        firms["neurocertify"]["bands"] = {}
        fig = figure_b5_four_path_reconciliation(
            firms=firms, funding_stage_lines=self._funding_lines(),
        )
        try:
            self.assertEqual(len(fig.axes), len(firms))
        finally:
            plt.close(fig)


if __name__ == "__main__":
    unittest.main()
