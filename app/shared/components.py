"""Reusable UI components used across tabs.

  · ``status_bar()`` — persistent strip at the top of every page showing
    active jurisdictions, override count, and the headline lever values.
  · ``hero_strip(metrics)`` — 3-to-5 metrics rendered as ``st.metric`` in
    a single row at the top of a tab.
  · ``insight(message, kind='info')`` — styled callout used under live
    figures to name the dominant delta versus the YAML defaults.

These components are presentation-only: they read from ``effective_parameters``
and ``current_countries`` but never mutate state.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

import streamlit as st

from app.shared import state
from src import config


KindStyle = {
    "info":    ("#1B3A57", "#F1F5F9"),
    "success": ("#0B6E4F", "#E8F4EE"),
    "warning": ("#7A5C00", "#FFF6E0"),
    "danger":  ("#7A1F1F", "#FBEAEA"),
}


def status_bar() -> None:
    """Render a persistent status line at the top of any tab.

    Shows active blocs (flag chips), override count, K7 and the AI
    substitutability of Layer 4 — the three values a researcher most
    often wants to confirm before reading any chart. Stays in view as
    the user navigates tabs.
    """
    state.init_session_state()
    p = state.effective_parameters()
    overrides = st.session_state.get("overrides", {})
    countries = state.current_countries()

    k7 = float(p["knowledge_regimes"]["regimes"]["current_2026"]
               ["K_coefficient"])
    ai_sub = float(p["startup"]["ai_substitution_potential_layer4"])
    inv_thr = float(p["valuation"]
                    ["damodaran_inverted_threshold_layer4_share"])

    chips = " ".join(state.country_labels(countries))

    # Subtle highlight if overrides are active.
    if overrides:
        bg = "#FFF6E0"
        border = "#F5C242"
        badge = (f"<span style='background:#F5C242;color:#7A5C00;"
                 f"padding:1px 8px;border-radius:10px;font-size:0.78rem;"
                 f"font-weight:700;'>{len(overrides)} override(s)</span>")
    else:
        bg = "#F1F5F9"
        border = "#3C6E91"
        badge = ("<span style='background:#3C6E91;color:white;"
                 "padding:1px 8px;border-radius:10px;font-size:0.78rem;"
                 "font-weight:700;'>defaults</span>")

    html = (
        f"<div style='background:{bg};border-left:4px solid {border};"
        f"padding:7px 12px;border-radius:4px;margin-bottom:10px;"
        f"font-size:0.85rem;display:flex;flex-wrap:wrap;gap:14px;"
        f"align-items:center;'>"
        f"<span><b>Active blocs:</b> {chips}</span>"
        f"<span><b>K₇:</b> {k7:.2f}</span>"
        f"<span><b>AI sub L4:</b> {ai_sub:.2f}</span>"
        f"<span><b>Inversion threshold:</b> {inv_thr:.2f}</span>"
        f"{badge}"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def hero_strip(metrics: Iterable[Tuple[str, str, Optional[str]]]) -> None:
    """Render up to five ``st.metric`` cards in a single row.

    Parameters
    ----------
    metrics : iterable of (label, value, delta)
        ``delta`` may be None.
    """
    items = list(metrics)
    if not items:
        return
    cols = st.columns(min(len(items), 5))
    for col, (label, value, delta) in zip(cols, items):
        with col:
            if delta:
                st.metric(label, value, delta)
            else:
                st.metric(label, value)


def insight(message: str, *, kind: str = "info") -> None:
    """Styled callout used under live figures.

    ``kind`` is one of ``info``, ``success``, ``warning``, ``danger``.
    """
    text_color, bg = KindStyle.get(kind, KindStyle["info"])
    icon = {"info": "💡", "success": "✅",
            "warning": "⚠️", "danger": "🛑"}.get(kind, "💡")
    html = (
        f"<div style='background:{bg};border-left:4px solid {text_color};"
        f"padding:8px 12px;border-radius:4px;margin:6px 0 14px 0;"
        f"font-size:0.92rem;color:{text_color};'>"
        f"<span style='margin-right:6px;'>{icon}</span>"
        f"{message}"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Delta helpers — useful when an insight wants to name a numeric change.
# ----------------------------------------------------------------------

def baseline_value(dot_path: str) -> float:
    """Read the YAML default at ``dot_path`` (no override applied)."""
    return float(config.get(dot_path))


def override_delta(dot_path: str) -> Tuple[float, float]:
    """Return ``(baseline, current)`` for an override-tracked dot-path."""
    base = baseline_value(dot_path)
    cur = float(state.get_override(dot_path, base))
    return base, cur
