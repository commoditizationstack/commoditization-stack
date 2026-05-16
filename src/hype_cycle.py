"""Gartner Hype Cycle, classical and reformulated for the post-AI regime.

The classical Hype Cycle (Gartner, 1995) models technology adoption as:
  Innovation Trigger -> Peak of Inflated Expectations -> Trough of Disillusionment
  -> Slope of Enlightenment -> Plateau of Productivity.

The post-AI reformulation (paper section 6.5) proposes a *double-valley*
structure: the classical valley appears earlier and shallower; a second valley
(the "commoditization valley") appears AFTER what looks like a recovery, when
competitors achieve technical parity through frontier-model substitution and
margins compress.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np

from . import config


def classical_hype_curve(
    n_quarters: int,
    peak_quarter: int = 4,
    trough_quarter: int = 12,
    plateau_quarter: int = 24,
    peak_height: float = 100.0,
    trough_height: float = 20.0,
    plateau_height: float = 60.0,
) -> np.ndarray:
    """Classical single-valley Gartner curve.

    Built piecewise: ramp-up, peak, decline to trough, slope of enlightenment,
    plateau.
    """
    t = np.arange(n_quarters + 1)
    y = np.zeros_like(t, dtype=float)

    # ramp up to peak (exponent from config.structural)
    rise_exp = float(config.structural()["classical_hype_rise_exponent"])
    rise_mask = t <= peak_quarter
    y[rise_mask] = peak_height * (t[rise_mask] / peak_quarter) ** rise_exp

    # decline to trough
    decline_mask = (t > peak_quarter) & (t <= trough_quarter)
    decline_t = t[decline_mask]
    decline_norm = (decline_t - peak_quarter) / (trough_quarter - peak_quarter)
    y[decline_mask] = peak_height + (trough_height - peak_height) * (
        1 - np.cos(np.pi * decline_norm)) / 2

    # slope of enlightenment
    enlight_mask = (t > trough_quarter) & (t <= plateau_quarter)
    enlight_t = t[enlight_mask]
    enlight_norm = (enlight_t - trough_quarter) / (plateau_quarter - trough_quarter)
    y[enlight_mask] = trough_height + (plateau_height - trough_height) * (
        1 - np.cos(np.pi * enlight_norm)) / 2

    # plateau
    plateau_mask = t > plateau_quarter
    y[plateau_mask] = plateau_height

    return y


def post_genai_double_valley_curve(
    n_quarters: int,
    peak_quarter: int = 3,
    trough_quarter: int = 8,
    second_peak_quarter: int = 14,
    commoditization_valley_quarter: int = 18,
    plateau_quarter: int = 28,
    peak_height: float = 100.0,
    trough_height: float = 10.0,
    second_peak_height: float = 45.0,
    commoditization_valley_height: float = 25.0,
    plateau_height: float = 50.0,
) -> np.ndarray:
    """Reformulated post-AI hype curve with a double valley.

    Stages:
      1. Sharp ramp to early peak (faster than classical).
      2. Steep early trough (deeper than classical).
      3. Recovery toward a second, lower peak ("false plateau").
      4. SECOND valley - commoditization valley - as competitors close
         the technical gap via frontier-model substitution.
      5. Lower plateau than classical.
    """
    t = np.arange(n_quarters + 1)
    y = np.zeros_like(t, dtype=float)

    # phase 1: ramp to peak (exponent from config.structural)
    rise_exp = float(config.structural()["post_genai_hype_rise_exponent"])
    m1 = t <= peak_quarter
    y[m1] = peak_height * (t[m1] / peak_quarter) ** rise_exp

    # phase 2: classical valley
    m2 = (t > peak_quarter) & (t <= trough_quarter)
    nrm = (t[m2] - peak_quarter) / max(1, (trough_quarter - peak_quarter))
    y[m2] = peak_height + (trough_height - peak_height) * (1 - np.cos(np.pi * nrm)) / 2

    # phase 3: false recovery to second peak
    m3 = (t > trough_quarter) & (t <= second_peak_quarter)
    nrm = (t[m3] - trough_quarter) / max(1, (second_peak_quarter - trough_quarter))
    y[m3] = trough_height + (second_peak_height - trough_height) * (
        1 - np.cos(np.pi * nrm)) / 2

    # phase 4: COMMODITIZATION VALLEY (the new contribution)
    m4 = (t > second_peak_quarter) & (t <= commoditization_valley_quarter)
    nrm = (t[m4] - second_peak_quarter) / max(
        1, (commoditization_valley_quarter - second_peak_quarter))
    y[m4] = second_peak_height + (commoditization_valley_height - second_peak_height) * (
        1 - np.cos(np.pi * nrm)) / 2

    # phase 5: slow recovery to lower plateau
    m5 = (t > commoditization_valley_quarter) & (t <= plateau_quarter)
    nrm = (t[m5] - commoditization_valley_quarter) / max(
        1, (plateau_quarter - commoditization_valley_quarter))
    y[m5] = commoditization_valley_height + (plateau_height - commoditization_valley_height) * (
        1 - np.cos(np.pi * nrm)) / 2

    # phase 6: plateau
    m6 = t > plateau_quarter
    y[m6] = plateau_height

    return y


def annotate_phases_classical(cfg: Dict) -> Dict[str, Tuple[int, str]]:
    return {
        "Innovation Trigger": (0, "left"),
        "Peak of Inflated Expectations": (cfg["peak_quarter"], "center"),
        "Trough of Disillusionment": (cfg["trough_quarter"], "center"),
        "Slope of Enlightenment": ((cfg["trough_quarter"] + cfg["plateau_quarter"]) // 2,
                                   "center"),
        "Plateau of Productivity": (cfg["plateau_quarter"] + 2, "left"),
    }


def annotate_phases_post_genai(cfg: Dict) -> Dict[str, Tuple[int, str]]:
    return {
        "Innovation Trigger": (0, "left"),
        "Early Peak": (cfg["peak_quarter"], "center"),
        "Classical Trough": (cfg["trough_quarter"], "center"),
        "False Recovery Peak": (cfg["second_peak_quarter"], "center"),
        "Commoditization Valley (new)": (cfg["commoditization_valley_quarter"], "center"),
        "Lower Plateau": (cfg["plateau_quarter"] + 2, "left"),
    }
