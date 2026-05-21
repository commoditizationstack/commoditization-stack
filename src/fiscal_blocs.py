"""5-year fiscal projection across three jurisdictional blocs (Appendix D.6).

Decomposes the state-revenue impact of AI-substitution into three channels:
  - Lost employer social charges (when in-house labor is eliminated)
  - Fiscal exportation via AI tokens (revenue migrates to foreign AI provider)
  - Compensating gain from corporate tax on higher operating margin

Generates Figure D.8 of the paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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


def _merged_config(overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Deep-merge an `overrides` dict onto the YAML fiscal_blocs config.

    Override shape mirrors the YAML — partial fields are honoured, missing
    fields fall back to the canonical value. Used by callers (the API
    layer, scenario runners) to probe sensitivities without editing the
    YAML on disk.
    """
    base = dict(config.load_parameters()["fiscal_blocs"])
    if not overrides:
        return base
    # Deep merge one level for sub-dicts (corporate_tax_rate, employer_charges_*,
    # decomposition_5y_usd_millions, cumulative_5y_impact_usd_millions).
    for key, value in overrides.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merged = dict(base[key])
            for sub_key, sub_val in value.items():
                if sub_val is None:
                    continue
                if isinstance(sub_val, dict) and isinstance(merged.get(sub_key), dict):
                    inner = dict(merged[sub_key])
                    for k2, v2 in sub_val.items():
                        if v2 is not None:
                            inner[k2] = v2
                    merged[sub_key] = inner
                else:
                    merged[sub_key] = sub_val
            base[key] = merged
        else:
            base[key] = value
    return base


def project_bloc(
    jurisdiction: str,
    overrides: Optional[Dict[str, Any]] = None,
) -> FiscalBlocResult:
    """Project the 5-year fiscal impact for one bloc using YAML calibration.

    When `overrides` is supplied, the values are deep-merged onto the
    canonical YAML config before reading any field. Useful for
    parameter sweeps and for the web app's Advanced parameters lab.
    """
    fb = _merged_config(overrides)
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


def project_all_blocs(
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, FiscalBlocResult]:
    """Project all three reference jurisdictions, with optional overrides."""
    return {
        j: project_bloc(j, overrides=overrides)
        for j in ["brazil", "france", "united_states"]
    }


def headline_5y_impact_usd_millions(jurisdiction: str) -> float:
    """Headline net impact for a single jurisdiction (positive = loss)."""
    return project_bloc(jurisdiction).net_impact_usd_millions
