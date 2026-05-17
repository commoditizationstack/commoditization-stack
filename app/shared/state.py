"""Streamlit session-state + parameter override engine.

Centralises three concerns:
  1. Country selection ("brazil" / "france" / "united_states") — global,
     synced across all tabs that depend on jurisdiction.
  2. Parameter overrides — user edits applied on top of the framework
     defaults, persisted in st.session_state, and consumed by all
     simulation code through `effective_parameters()` (returns a dict
     in the same shape as the framework defaults but with the user's
     overrides applied).
  3. YAML round-trip — download/upload the current overlay as a YAML file
     so users can save/share their scenarios.

The override engine works at the dot-path level. A user editing the slider
for "valuation.damodaran_inverted_threshold_layer4_share" writes
`st.session_state["overrides"]["valuation.damodaran_inverted_threshold_layer4_share"] = 0.60`,
and `effective_parameters()` deep-merges the overlay onto the YAML defaults.
"""

from __future__ import annotations

import io
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st
import yaml

from src import config


# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

DEFAULT_COUNTRY = "united_states"
DEFAULT_COUNTRIES = ["brazil", "france", "united_states"]
COUNTRY_LABELS = {
    "brazil": "🇧🇷 Brazil",
    "france": "🇫🇷 France",
    "united_states": "🇺🇸 United States",
}


def init_session_state() -> None:
    """Set up st.session_state keys used across the app. Idempotent."""
    if "countries" not in st.session_state:
        # All three blocs active by default — comparative scenario mode.
        st.session_state["countries"] = list(DEFAULT_COUNTRIES)
    if "country" not in st.session_state:
        # Backwards-compat: the single-country anchor (first selected).
        st.session_state["country"] = st.session_state["countries"][0]
    if "overrides" not in st.session_state:
        st.session_state["overrides"] = {}
    if "recompute_counter" not in st.session_state:
        # Bumped by the "Recompute All" button to invalidate caches.
        st.session_state["recompute_counter"] = 0


# ---------------------------------------------------------------------------
# Override engine
# ---------------------------------------------------------------------------

def get_override(dot_path: str, default: Any = None) -> Any:
    """Get a parameter from overrides or fall back to YAML default."""
    if "overrides" not in st.session_state:
        init_session_state()
    if dot_path in st.session_state["overrides"]:
        return st.session_state["overrides"][dot_path]
    return config.get(dot_path, default)


def set_override(dot_path: str, value: Any) -> None:
    """Record a user override at the given dot-path."""
    if "overrides" not in st.session_state:
        init_session_state()
    st.session_state["overrides"][dot_path] = value


def clear_overrides() -> None:
    """Reset all overrides to YAML defaults."""
    if "overrides" in st.session_state:
        st.session_state["overrides"] = {}


def _deep_merge(target: dict, source: dict) -> dict:
    """Deep-merge source into target (target is mutated and returned)."""
    for k, v in source.items():
        if k in target and isinstance(target[k], dict) and isinstance(v, dict):
            _deep_merge(target[k], v)
        else:
            target[k] = v
    return target


def _coerce_key(cur: dict, raw: str) -> Any:
    """Return the actual dict key matching `raw`: prefer the string form;
    fall back to the integer form when the YAML stores integer keys
    (e.g. ``trl_discount_premium`` uses ``1..9: float``)."""
    if raw in cur:
        return raw
    if raw.lstrip("-").isdigit():
        as_int = int(raw)
        if as_int in cur:
            return as_int
    return raw  # new key — keep as string


def _apply_overrides_to_dict(base: dict, overrides: Dict[str, Any]) -> dict:
    """Apply dot-path overrides to a nested dict, returning a new dict."""
    out = deepcopy(base)
    for path, value in overrides.items():
        parts = path.split(".")
        cur = out
        for key in parts[:-1]:
            real_key = _coerce_key(cur, key) if isinstance(cur, dict) else key
            if real_key not in cur or not isinstance(cur[real_key], dict):
                cur[real_key] = {}
            cur = cur[real_key]
        leaf_key = _coerce_key(cur, parts[-1]) if isinstance(cur, dict) else parts[-1]
        cur[leaf_key] = value
    return out


def effective_parameters() -> dict:
    """Return the framework defaults with all user overrides applied.

    This is the single function that every simulation entry point should
    consume in the Streamlit context — never call config.load_parameters()
    directly from tabs, because that bypasses user edits.
    """
    if "overrides" not in st.session_state:
        init_session_state()
    base = config.load_parameters()
    if not st.session_state["overrides"]:
        return base
    return _apply_overrides_to_dict(base, st.session_state["overrides"])


# ---------------------------------------------------------------------------
# Country selection
# ---------------------------------------------------------------------------

def current_countries() -> list:
    """List of country slugs the user currently has selected for comparison.

    Always non-empty: if the user clears the multi-select we fall back to
    every available country, since downstream charts assume at least one.
    """
    if "countries" not in st.session_state:
        init_session_state()
    selected = list(st.session_state.get("countries") or [])
    if not selected:
        selected = list(DEFAULT_COUNTRIES)
    return selected


def current_country() -> str:
    """Anchor country: the first one in the active selection.

    Tabs that still need a single country (PDF cover, sample-firm view,
    migration trajectory anchor) use this. Tabs that should iterate over
    every active jurisdiction call ``current_countries()`` instead.
    """
    if "country" not in st.session_state:
        init_session_state()
    selected = current_countries()
    # Keep the legacy `country` key consistent with the active selection.
    if st.session_state.get("country") not in selected:
        st.session_state["country"] = selected[0]
    return st.session_state["country"]


def country_label(country: Optional[str] = None) -> str:
    """Pretty label for a country slug (with flag emoji)."""
    if country is None:
        country = current_country()
    return COUNTRY_LABELS.get(country, country)


def country_labels(countries: Optional[list] = None) -> list:
    """Pretty labels for a list of country slugs."""
    if countries is None:
        countries = current_countries()
    return [COUNTRY_LABELS.get(c, c) for c in countries]


# ---------------------------------------------------------------------------
# YAML round-trip
# ---------------------------------------------------------------------------

def overrides_as_yaml_bytes() -> bytes:
    """Serialise the current overrides as a YAML document (bytes for download)."""
    overlay: Dict[str, Any] = {}
    for path, value in st.session_state.get("overrides", {}).items():
        parts = path.split(".")
        cur = overlay
        for key in parts[:-1]:
            cur = cur.setdefault(key, {})
        cur[parts[-1]] = value
    if not overlay:
        overlay = {"_comment": "no overrides have been set yet"}
    text = yaml.safe_dump(overlay, sort_keys=False, allow_unicode=True)
    return text.encode("utf-8")


def load_overrides_from_yaml_bytes(blob: bytes) -> int:
    """Load overrides from an uploaded YAML file, replacing any existing overlay.

    Returns the number of overrides loaded.
    """
    data = yaml.safe_load(blob.decode("utf-8")) or {}

    def flatten(d: dict, prefix: str = "") -> Dict[str, Any]:
        flat: Dict[str, Any] = {}
        for k, v in d.items():
            if k.startswith("_"):  # skip comments
                continue
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                flat.update(flatten(v, key))
            else:
                flat[key] = v
        return flat

    overrides = flatten(data)
    st.session_state["overrides"] = overrides
    return len(overrides)


# ---------------------------------------------------------------------------
# Recompute helper (for invalidating caches)
# ---------------------------------------------------------------------------

def request_recompute() -> None:
    """Bump the recompute counter — heavy computations keyed on this counter
    will refresh on the next render."""
    if "recompute_counter" not in st.session_state:
        init_session_state()
    st.session_state["recompute_counter"] += 1


def recompute_counter() -> int:
    """Current counter value — pass this as a cache key to expensive caches."""
    if "recompute_counter" not in st.session_state:
        init_session_state()
    return st.session_state["recompute_counter"]
