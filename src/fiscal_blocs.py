"""5-year fiscal projection across three jurisdictional blocs (Appendix D.6).

Decomposes the state-revenue impact of AI-substitution into three channels:
  - Lost employer social charges (when in-house labor is eliminated)
  - Fiscal exportation via AI tokens (revenue migrates to foreign AI provider)
  - Compensating gain from corporate tax on higher operating margin

Generates Figure D.8 of the paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from . import config


@dataclass
class FiscalBlocResult:
    """5-year fiscal projection for one jurisdiction."""
    jurisdiction: str
    lost_social_charges_usd_millions: float       # negative impact (revenue loss)
    ai_token_export_usd_millions: float           # negative impact (tax base migrates)
    compensating_tax_gain_usd_millions: float     # positive impact (higher CT)
    net_impact_usd_millions: float                # sum (positive = State loses)
    cumulative_by_year: List[float]               # year-by-year cumulative (year 1-5)


def project_bloc(jurisdiction: str) -> FiscalBlocResult:
    """Project the 5-year fiscal impact for one bloc using YAML calibration."""
    fb = config.load_parameters()["fiscal_blocs"]
    decomp = fb["decomposition_5y_usd_millions"]

    lost = float(decomp["lost_social_charges"][jurisdiction])
    export = float(decomp["ai_token_export"][jurisdiction])
    gain = float(decomp["compensating_tax_gain"][jurisdiction])
    net = lost + export - gain   # positive = State loses revenue

    # Linear year-by-year accumulation
    horizon = int(fb["horizon_years"])
    cumulative = [net * (yr / horizon) for yr in range(1, horizon + 1)]

    return FiscalBlocResult(
        jurisdiction=jurisdiction,
        lost_social_charges_usd_millions=lost,
        ai_token_export_usd_millions=export,
        compensating_tax_gain_usd_millions=gain,
        net_impact_usd_millions=net,
        cumulative_by_year=cumulative,
    )


def project_all_blocs() -> Dict[str, FiscalBlocResult]:
    """Project all three reference jurisdictions."""
    return {
        j: project_bloc(j)
        for j in ["brazil", "france", "united_states"]
    }


def headline_5y_impact_usd_millions(jurisdiction: str) -> float:
    """Headline net impact for a single jurisdiction (positive = loss)."""
    return project_bloc(jurisdiction).net_impact_usd_millions
