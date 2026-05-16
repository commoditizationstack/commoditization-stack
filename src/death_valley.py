"""Valley of Death, classical and post-AI reformulated.

The classical valley of death is the gap between proof of concept and sustainable
revenue, in which most innovative firms run out of capital. The post-AI
reformulation (paper section 6.5) proposes that this single classical valley is
NARROWING (because building MVPs has become cheaper) but that a SECOND valley
appears post-product-market-fit: the commoditization valley, when competitors
achieve technical parity through frontier-model substitution and margins compress.

This module provides cash-trajectory templates that the simulation can use to
compare these regimes.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple
import numpy as np

from . import config


def _dv_classical() -> Dict:
    return config.load_parameters()["death_valley"]["classical"]


def _dv_post() -> Dict:
    return config.load_parameters()["death_valley"]["post_genai"]


def classical_cash_trajectory(
    n_months: Optional[int] = None,
    initial_cash_usd: Optional[float] = None,
    monthly_burn_usd: Optional[float] = None,
    valley_start_month: Optional[int] = None,
    valley_end_month: Optional[int] = None,
    revenue_ramp_start_month: Optional[int] = None,
    peak_revenue_usd_per_month: Optional[float] = None,
    revenue_growth: Optional[float] = None,
) -> np.ndarray:
    """Single-valley classical cash curve. Defaults from config/parameters.yaml."""
    c = _dv_classical()
    n_months = int(c["n_months"]) if n_months is None else n_months
    initial_cash_usd = float(c["initial_cash_usd"]) if initial_cash_usd is None else initial_cash_usd
    monthly_burn_usd = float(c["monthly_burn_usd"]) if monthly_burn_usd is None else monthly_burn_usd
    valley_start_month = int(c["valley_start_month"]) if valley_start_month is None else valley_start_month
    valley_end_month = int(c["valley_end_month"]) if valley_end_month is None else valley_end_month
    revenue_ramp_start_month = int(c["revenue_ramp_start_month"]) if revenue_ramp_start_month is None else revenue_ramp_start_month
    peak_revenue_usd_per_month = float(c["peak_revenue_usd_per_month"]) if peak_revenue_usd_per_month is None else peak_revenue_usd_per_month
    revenue_growth = float(c["revenue_growth"]) if revenue_growth is None else revenue_growth
    revenue_seed = float(c["revenue_seed_usd"])

    cash = np.zeros(n_months + 1)
    cash[0] = initial_cash_usd
    revenue = 0.0
    for m in range(1, n_months + 1):
        if m >= revenue_ramp_start_month:
            revenue = revenue * (1 + revenue_growth) + revenue_seed
            revenue = min(revenue, peak_revenue_usd_per_month)
        cash[m] = cash[m - 1] + revenue - monthly_burn_usd
    return cash


def post_genai_double_valley_cash_trajectory(
    n_months: Optional[int] = None,
    initial_cash_usd: Optional[float] = None,
    monthly_burn_usd_initial: Optional[float] = None,
    classical_valley_start_month: Optional[int] = None,
    classical_valley_end_month: Optional[int] = None,
    commoditization_valley_start_month: Optional[int] = None,
    commoditization_valley_end_month: Optional[int] = None,
    revenue_ramp_start_month: Optional[int] = None,
    peak_revenue_usd_per_month: Optional[float] = None,
    revenue_growth: Optional[float] = None,
    margin_compression_factor: Optional[float] = None,
    refinancing_event_month: Optional[int] = None,
    refinancing_amount_usd: Optional[float] = None,
    burn_growth_after_funding: Optional[float] = None,
) -> np.ndarray:
    p = _dv_post()
    n_months = int(p["n_months"]) if n_months is None else n_months
    initial_cash_usd = float(p["initial_cash_usd"]) if initial_cash_usd is None else initial_cash_usd
    monthly_burn_usd_initial = float(p["monthly_burn_usd_initial"]) if monthly_burn_usd_initial is None else monthly_burn_usd_initial
    classical_valley_start_month = int(p["classical_valley_start_month"]) if classical_valley_start_month is None else classical_valley_start_month
    classical_valley_end_month = int(p["classical_valley_end_month"]) if classical_valley_end_month is None else classical_valley_end_month
    commoditization_valley_start_month = int(p["commoditization_valley_start_month"]) if commoditization_valley_start_month is None else commoditization_valley_start_month
    commoditization_valley_end_month = int(p["commoditization_valley_end_month"]) if commoditization_valley_end_month is None else commoditization_valley_end_month
    revenue_ramp_start_month = int(p["revenue_ramp_start_month"]) if revenue_ramp_start_month is None else revenue_ramp_start_month
    peak_revenue_usd_per_month = float(p["peak_revenue_usd_per_month"]) if peak_revenue_usd_per_month is None else peak_revenue_usd_per_month
    revenue_growth = float(p["revenue_growth"]) if revenue_growth is None else revenue_growth
    margin_compression_factor = float(p["margin_compression_factor"]) if margin_compression_factor is None else margin_compression_factor
    refinancing_event_month = int(p["refinancing_event_month"]) if refinancing_event_month is None else refinancing_event_month
    refinancing_amount_usd = float(p["refinancing_amount_usd"]) if refinancing_amount_usd is None else refinancing_amount_usd
    burn_growth_after_funding = float(p["burn_growth_after_funding"]) if burn_growth_after_funding is None else burn_growth_after_funding
    revenue_seed = float(p["revenue_seed_usd"])
    post_funding_burn_mult = float(p["post_funding_burn_multiplier"])
    """Double-valley post-AI cash curve.

    Phase 1: shallower classical valley due to lower MVP build cost.
    Phase 2: revenue ramp.
    Phase 3: refinancing round (Series A) brings cash up; team grows; burn rises.
    Phase 4: COMMODITIZATION VALLEY - margin compression as competitors close
             technical gap; revenue may continue but at lower margins, while
             burn has scaled up. Cash declines visibly here.
    Phase 5: stabilization on a lower plateau (or further decline if margin
             compression is severe).
    """
    cash = np.zeros(n_months + 1)
    cash[0] = initial_cash_usd
    revenue = 0.0
    burn = monthly_burn_usd_initial

    for m in range(1, n_months + 1):
        # revenue ramp
        if m >= revenue_ramp_start_month:
            revenue = revenue * (1 + revenue_growth) + revenue_seed
            revenue = min(revenue, peak_revenue_usd_per_month)

        # refinancing event (Series A) - team also scales up burn
        funding = refinancing_amount_usd if m == refinancing_event_month else 0.0
        if m == refinancing_event_month:
            burn = monthly_burn_usd_initial * post_funding_burn_mult

        # margin compression in commoditization valley
        if (m >= commoditization_valley_start_month and
                m <= commoditization_valley_end_month):
            effective_revenue = revenue * margin_compression_factor
        else:
            effective_revenue = revenue

        cash[m] = cash[m - 1] + effective_revenue + funding - burn

    return cash


def detect_valleys(cash_trajectory: np.ndarray) -> list[Tuple[int, int]]:
    """Detect contiguous regions where cash is decreasing significantly.

    Returns list of (start_month, end_month) tuples for each valley.
    A 'valley' is a region where cash falls below
    `death_valley.detection.valley_threshold_factor` of its prior running max.
    """
    threshold_factor = float(config.load_parameters()["death_valley"]
                             ["detection"]["valley_threshold_factor"])
    n = len(cash_trajectory)
    valleys = []
    in_valley = False
    valley_start = 0
    running_max = cash_trajectory[0]

    for i in range(1, n):
        running_max = max(running_max, cash_trajectory[i])
        threshold = running_max * threshold_factor
        if cash_trajectory[i] < threshold and not in_valley:
            in_valley = True
            valley_start = i
        elif cash_trajectory[i] >= threshold and in_valley:
            in_valley = False
            valleys.append((valley_start, i - 1))

    if in_valley:
        valleys.append((valley_start, n - 1))

    return valleys
