"""Distributional and epistemic-justice dimensions (Appendix G).

Two structural figures:
  - G.1 Double threshold: economic threshold (orchestrator overhead) and
    regulatory-compliance threshold (orchestrator + XAI infrastructure)
    below which AI migration is net-negative for institution-dominant firms.
  - G.2 XAI capacity gap: divergence between two reference blocs over time
    under three regimes of cross-border knowledge integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

from . import config


@dataclass
class DoubleThresholdData:
    """Data for Figure G.1: double threshold for AI migration."""
    headcount: np.ndarray
    gross_saving_usd: np.ndarray
    orchestrator_floor_usd: float
    xai_floor_usd: float
    economic_break_even: float          # headcount at which gross saving = orchestrator floor
    compliance_break_even: float        # headcount at which gross saving = orchestrator + XAI


def compute_double_threshold() -> DoubleThresholdData:
    """Compute the double-threshold curves for institution-dominant firm profile."""
    di = config.load_parameters()["distributional"]["double_threshold"]
    n = int(di["n_grid"])
    headcount = np.linspace(float(di["headcount_min"]), float(di["headcount_max"]), n)

    saving_per_eng = float(di["gross_saving_per_eng_usd_year"])
    gross_saving = headcount * saving_per_eng

    orch_floor = float(di["orchestrator_overhead_floor_usd"])
    xai_floor = float(di["xai_infrastructure_floor_usd"])

    # Break-even points (where gross saving curve crosses each floor)
    economic_be = orch_floor / saving_per_eng
    compliance_be = xai_floor / saving_per_eng

    return DoubleThresholdData(
        headcount=headcount,
        gross_saving_usd=gross_saving,
        orchestrator_floor_usd=orch_floor,
        xai_floor_usd=xai_floor,
        economic_break_even=economic_be,
        compliance_break_even=compliance_be,
    )


@dataclass
class XAICapacityGapData:
    """Data for Figure G.2: XAI capacity gap across two blocs over time."""
    years: np.ndarray
    bloc_a_k1_0: np.ndarray             # K=1.0 trajectory for Bloc A
    bloc_b_k1_0: np.ndarray
    bloc_a_k0_7: np.ndarray             # K=0.7 trajectory
    bloc_b_k0_7: np.ndarray
    bloc_a_k0_45: np.ndarray            # K=0.45 trajectory
    bloc_b_k0_45: np.ndarray
    endpoint_gaps: Dict[str, float]      # k_1_0, k_0_7, k_0_45


def compute_xai_capacity_gap() -> XAICapacityGapData:
    """Compute XAI capacity trajectories for two reference blocs under three K7 regimes."""
    xg = config.load_parameters()["distributional"]["xai_capacity_gap"]
    n = int(xg["horizon_years"]) + 1
    base_year = int(xg["base_year"])
    years = np.arange(base_year, base_year + n)
    t = np.arange(n)  # 0..N

    a_growth = xg["bloc_a_growth_factor"]
    b_growth = xg["bloc_b_growth_factor"]

    bloc_a_k1_0 = (float(a_growth["k_1_0"])) ** t
    bloc_a_k0_7 = (float(a_growth["k_0_7"])) ** t
    bloc_a_k0_45 = (float(a_growth["k_0_45"])) ** t
    bloc_b_k1_0 = (float(b_growth["k_1_0"])) ** t
    bloc_b_k0_7 = (float(b_growth["k_0_7"])) ** t
    bloc_b_k0_45 = (float(b_growth["k_0_45"])) ** t

    return XAICapacityGapData(
        years=years,
        bloc_a_k1_0=bloc_a_k1_0,
        bloc_b_k1_0=bloc_b_k1_0,
        bloc_a_k0_7=bloc_a_k0_7,
        bloc_b_k0_7=bloc_b_k0_7,
        bloc_a_k0_45=bloc_a_k0_45,
        bloc_b_k0_45=bloc_b_k0_45,
        endpoint_gaps={
            "k_1_0": float(xg["endpoint_gap_year_8"]["k_1_0"]),
            "k_0_7": float(xg["endpoint_gap_year_8"]["k_0_7"]),
            "k_0_45": float(xg["endpoint_gap_year_8"]["k_0_45"]),
        },
    )
