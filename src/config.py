"""Centralized parameter loader.

Single source of truth: config/parameters.yaml at the repo root. This module
loads the file lazily on first access and exposes the merged dict via
`load_parameters()` plus typed accessors for the most-used sections.

Why this module exists
----------------------
Every tunable numeric parameter in the simulation lives in parameters.yaml.
src/, scripts/ and app/ modules read from here so there is exactly one place
to look up or change any value. The dataclasses-with-defaults pattern that
used to live in src/valuation_layered.py, src/valuation_two_phase.py,
src/jurisdictional.py and src/stack_layers.py now wraps these values
instead of hardcoding them.

Usage
-----
    from src import config
    p = config.load_parameters()
    runway = p["startup"]["growth"]["runway_months_before_team_can_grow"]

For typed shortcuts:

    config.trl_discount_premium(trl=5)
    config.layer_risk_coefficients()
    config.us_funding_stage_benchmarks()
    config.jurisdiction_defaults()
    config.knowledge_regime_defaults()
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "parameters.yaml"


@lru_cache(maxsize=1)
def load_parameters() -> Dict[str, Any]:
    """Load and cache config/parameters.yaml. Always returns the same dict.

    To pick up edits during a long-running process (e.g. Streamlit hot-reload),
    call `load_parameters.cache_clear()` first.
    """
    return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))


def get(path: str, default: Any = None) -> Any:
    """Dot-path accessor: get("startup.growth.runway_months_before_team_can_grow").

    Accepts integer keys transparently: a path component that is all
    digits matches int(key) when the string form is absent (some YAML
    sections, e.g. ``trl_discount_premium``, use int keys).
    """
    cur: Any = load_parameters()
    for key in path.split("."):
        if not isinstance(cur, dict):
            return default
        if key in cur:
            cur = cur[key]
        elif key.lstrip("-").isdigit() and int(key) in cur:
            cur = cur[int(key)]
        else:
            return default
    return cur


# ---------------------------------------------------------------------------
# Typed shortcuts for the most-frequently-used sections
# ---------------------------------------------------------------------------

def trl_discount_premium(trl: int) -> float:
    """TRL → discount-rate premium in absolute (not percent) units. Clipped [1, 9]."""
    schedule = load_parameters()["valuation_layered"]["trl_discount_premium"]
    trl = max(1, min(9, int(trl)))
    return float(schedule[trl])


def layer_risk_coefficients() -> Dict[str, float]:
    return dict(load_parameters()["valuation_layered"]["layer_risk_coefficients"])


def default_layer_exposure() -> Dict[str, float]:
    return dict(load_parameters()["valuation_layered"]["default_layer_exposure"])


def us_funding_stage_benchmarks() -> Dict[str, Dict[str, float]]:
    return {
        stage: dict(values)
        for stage, values in load_parameters()["valuation_layered"]
        ["us_funding_stage_benchmarks"].items()
    }


def stage_thresholds_usd() -> Dict[str, float]:
    return dict(load_parameters()["valuation_layered"]["stage_thresholds_usd"])


def jurisdiction_defaults() -> Dict[str, Dict[str, Any]]:
    return {
        slug: dict(values)
        for slug, values in load_parameters()["jurisdictions"]["defaults"].items()
    }


def knowledge_regime_defaults() -> Dict[str, Dict[str, Any]]:
    return {
        slug: dict(values)
        for slug, values in load_parameters()["knowledge_regimes"]["regimes"].items()
    }


def cross_border_friction() -> float:
    return float(load_parameters()["knowledge_regimes"]["cross_border_friction"])


def structural() -> Dict[str, float]:
    return dict(load_parameters()["structural"])


def streamlit_ui() -> Dict[str, Any]:
    return dict(load_parameters()["streamlit_ui"])


def firms_appendix_b() -> Dict[str, Any]:
    return dict(load_parameters()["firms_appendix_b"])


def sweeps() -> Dict[str, Any]:
    return dict(load_parameters()["sweeps"])


def dual_channel() -> Dict[str, Any]:
    """Provisional B.2.6 dual-channel correction parameters.

    Source of truth: ``config/parameters.yaml`` section 26. Includes
    ``enabled`` master flag, per-firm ``lambda_2V_phase2`` defaults, the
    auditable calibration helper coefficients (``k_L4``, ``k_L6``), and
    the systematic/idiosyncratic risk-partition coefficient
    ``alpha_4_sys``. Consumed by :mod:`src.dual_channel`.
    """
    return dict(load_parameters()["dual_channel"])


def macro_context() -> Dict[str, Any]:
    """Provisional Part B macro-context parameters.

    Source of truth: ``config/parameters.yaml`` section 27. Drives
    presentation only (multi-audience reports, funding-stage reference
    lines, macro-sensitivity view). Must never alter any DCF EV — that
    invariant is regression-tested.
    """
    return dict(load_parameters()["macro_context"])
