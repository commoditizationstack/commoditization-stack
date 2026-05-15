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

from typing import Dict, Tuple
import numpy as np


def classical_cash_trajectory(
    n_months: int = 36,
    initial_cash_usd: float = 2_000_000,
    monthly_burn_usd: float = 150_000,
    valley_start_month: int = 6,
    valley_end_month: int = 18,
    revenue_ramp_start_month: int = 12,
    peak_revenue_usd_per_month: float = 220_000,
    revenue_growth: float = 0.10,
) -> np.ndarray:
    """Single-valley classical cash curve."""
    cash = np.zeros(n_months + 1)
    cash[0] = initial_cash_usd
    revenue = 0.0
    for m in range(1, n_months + 1):
        if m >= revenue_ramp_start_month:
            revenue = revenue * (1 + revenue_growth) + 5000
            revenue = min(revenue, peak_revenue_usd_per_month)
        cash[m] = cash[m - 1] + revenue - monthly_burn_usd
    return cash


def post_genai_double_valley_cash_trajectory(
    n_months: int = 48,
    initial_cash_usd: float = 1_400_000,
    monthly_burn_usd_initial: float = 110_000,
    classical_valley_start_month: int = 4,
    classical_valley_end_month: int = 10,
    commoditization_valley_start_month: int = 22,
    commoditization_valley_end_month: int = 36,
    revenue_ramp_start_month: int = 8,
    peak_revenue_usd_per_month: float = 280_000,
    revenue_growth: float = 0.14,
    margin_compression_factor: float = 0.30,
    refinancing_event_month: int = 14,
    refinancing_amount_usd: float = 3_000_000,
    burn_growth_after_funding: float = 0.06,
) -> np.ndarray:
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
            revenue = revenue * (1 + revenue_growth) + 6000
            revenue = min(revenue, peak_revenue_usd_per_month)

        # refinancing event (Series A) - team also scales up burn
        funding = refinancing_amount_usd if m == refinancing_event_month else 0.0
        if m == refinancing_event_month:
            burn = monthly_burn_usd_initial * 2.5  # team scales up post-Series A

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
    A 'valley' is a region where cash is at least 15% below its prior local maximum.
    """
    n = len(cash_trajectory)
    valleys = []
    in_valley = False
    valley_start = 0
    running_max = cash_trajectory[0]

    for i in range(1, n):
        running_max = max(running_max, cash_trajectory[i])
        threshold = running_max * 0.85
        if cash_trajectory[i] < threshold and not in_valley:
            in_valley = True
            valley_start = i
        elif cash_trajectory[i] >= threshold and in_valley:
            in_valley = False
            valleys.append((valley_start, i - 1))

    if in_valley:
        valleys.append((valley_start, n - 1))

    return valleys
