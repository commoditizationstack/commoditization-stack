"""Upstream AI value-chain mapping and structural sensitivities (Appendix F).

Maps seven categories of upstream firms (foundry, training silicon, inference
silicon, memory, hyperscalers, frontier labs, AI-tooling platforms) onto the
seven-layer framework. Articulates three structural sensitivities the
framework illuminates without forecasting their realisation.

Generates Figures F.1 (scope), F.2 (mapping table), F.3 (sensitivities).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

from . import config


@dataclass
class UpstreamCategory:
    """One upstream firm category with its layer exposure profile."""
    slug: str
    label: str
    exposure: Dict[str, int]                 # L1_train, L1_infer, L2..L6 → 0..3
    structural_sensitivity: str


def all_categories() -> List[UpstreamCategory]:
    """Return the seven upstream firm categories from YAML."""
    uc = config.load_parameters()["upstream_chain"]["categories"]
    return [
        UpstreamCategory(
            slug=slug,
            label=str(v["label"]),
            exposure=dict(v["exposure"]),
            structural_sensitivity=str(v["structural_sensitivity"]),
        )
        for slug, v in uc.items()
    ]


def capex_sensitivity_curves() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute Layer-1 training vs inference capex decay under financing tightness.

    Returns (tightness_grid, training_capex_index, inference_capex_index).
    Capex indices normalised to 100 at zero tightness.
    """
    cs = config.load_parameters()["upstream_chain"]["capex_sensitivity"]
    n = int(cs["n_grid"])
    t = np.linspace(float(cs["tightness_min"]), float(cs["tightness_max"]), n)
    train_decay = float(cs["training_decay_exponent"])
    infer_decay = float(cs["inference_decay_exponent"])
    # Polynomial decay: training falls steeper than inference
    train_idx = 100.0 * (1.0 - t ** train_decay * 0.65)
    infer_idx = 100.0 * (1.0 - t ** infer_decay * 0.20)
    return t, train_idx, infer_idx


def adoption_threshold_curves() -> Dict[str, np.ndarray]:
    """Compute gross-saving curves vs engineering headcount for two firm profiles.

    Returns a dict with 'headcount', 'l4_heavy_saving', 'l6_rich_saving',
    'orchestrator_floor', 'xai_floor' (all USD thousands).
    """
    md = config.load_parameters()["migration_dynamics"]
    di = config.load_parameters()["distributional"]["double_threshold"]
    n = int(di["n_grid"])
    headcount = np.linspace(float(di["headcount_min"]), float(di["headcount_max"]), n)

    # L4-heavy firm (DataFlow-like): high substitutable subset per engineer
    l4_heavy_saving_per_eng = (
        float(md["loaded_mid_engineer_usd_year"]["united_states"]) * 0.55 * 0.75
    )
    # L6-rich firm (NeuroCertify-like): small substitutable subset per engineer
    l6_rich_saving_per_eng = float(di["gross_saving_per_eng_usd_year"])

    return {
        "headcount": headcount,
        "l4_heavy_saving_usd": headcount * l4_heavy_saving_per_eng,
        "l6_rich_saving_usd": headcount * l6_rich_saving_per_eng,
        "orchestrator_floor_usd": np.full_like(
            headcount, float(di["orchestrator_overhead_floor_usd"])
        ),
        "xai_floor_usd": np.full_like(
            headcount, float(di["xai_infrastructure_floor_usd"])
        ),
    }


def k7_sensitivity_per_jurisdiction() -> Dict[str, np.ndarray]:
    """Inversion-premium sensitivity to K7 across the three jurisdictions.

    Reuses the layer7_k_grid from config.sweeps and computes premium as
    a function of K7 for each jurisdiction, with collapse threshold at K7≈0.45.
    """
    sw = config.sweeps()["layer7_k_grid"]
    k_grid = np.linspace(float(sw["k_min"]), float(sw["k_max"]), int(sw["k_n"]))

    # Baseline premiums at K7=1.0 (per Section 7.3, K7=1.0 reference)
    baseline_premium = {
        "brazil": 0.010,
        "france": 0.017,
        "united_states": 0.039,
    }
    collapse_threshold = 0.45
    cross_bloc_threshold = 0.65

    result = {"k_grid": k_grid}
    for j, base in baseline_premium.items():
        premium = np.where(
            k_grid < collapse_threshold,
            0.0,
            base * ((k_grid - collapse_threshold) / (1.0 - collapse_threshold))
        )
        result[f"{j}_same_bloc"] = premium

    # Cross-bloc (US acquirer of target in different bloc)
    cross_bloc_base = baseline_premium["united_states"] * 0.62  # 38% contraction
    cross_bloc_premium = np.where(
        k_grid < cross_bloc_threshold,
        0.0,
        cross_bloc_base * ((k_grid - cross_bloc_threshold) / (1.0 - cross_bloc_threshold))
    )
    result["united_states_cross_bloc"] = cross_bloc_premium

    return result
