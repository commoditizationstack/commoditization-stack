"""Single source of truth for visual encoding across the simulator.

Imported by every live figure and PDF generator. Three palettes, three
named threshold values. Everything else is derived.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Jurisdiction palette — one colour per bloc, consistent across all charts.
# ---------------------------------------------------------------------------
JURISDICTION: dict[str, str] = {
    "brazil":        "#0B6E4F",   # green
    "france":        "#2C5282",   # blue
    "united_states": "#C44536",   # red
}

JURISDICTION_LABELS: dict[str, str] = {
    "brazil":        "Brazil",
    "france":        "France",
    "united_states": "United States",
}

# ---------------------------------------------------------------------------
# Layer palette — one colour per layer of the seven-layer stack.
# ---------------------------------------------------------------------------
LAYER: dict[str, str] = {
    "layer_1_infra":        "#9C7B5A",
    "layer_2_foundation":   "#7B68A6",
    "layer_3_capability":   "#3C8DAD",
    "layer_4_codified":     "#C44536",   # the commoditising villain
    "layer_5_judgment":     "#E89B3C",
    "layer_6_institutional": "#0B6E4F",  # the defensibility ally
    "layer_7_crossborder":  "#7A5C00",
}

# ---------------------------------------------------------------------------
# Scenario palette — Conservative / Moderate / Aggressive
# ---------------------------------------------------------------------------
SCENARIO: dict[str, str] = {
    "conservative": "#3C8DAD",
    "moderate":     "#E89B3C",
    "aggressive":   "#C44536",
}

# ---------------------------------------------------------------------------
# Phase palette — Phase 1 / Phase 2 / Phase 3 (Appendix B)
# ---------------------------------------------------------------------------
PHASE: dict[str, str] = {
    "phase_1": "#EEEEEE",
    "phase_2": "#F4CFCF",
    "phase_3": "#D6EAD6",
}

# ---------------------------------------------------------------------------
# Firms
# ---------------------------------------------------------------------------
FIRM: dict[str, str] = {
    "neurocertify": "#0B6E4F",
    "dataflow_pro": "#C44536",
}

# ---------------------------------------------------------------------------
# Semantic
# ---------------------------------------------------------------------------
GAIN  = "#0B6E4F"
LOSS  = "#C44536"
NEUTRAL = "#7B7D7D"
ACCENT  = "#1B3A57"
LIGHT_GREY = "#EEEEEE"
MID_GREY   = "#888888"

# ---------------------------------------------------------------------------
# Threshold values that should always be visualised when on the axis.
# ---------------------------------------------------------------------------
K7_COLLAPSE_LOW = 0.40
K7_COLLAPSE_HIGH = 0.50
K7_COLLAPSE_LABEL = 0.45
DAMODARAN_INVERSION_THRESHOLD = 0.55  # default L4 share; user may override


def shade_k7_collapse(ax, *, alpha: float = 0.10, color: str = LOSS,
                       annotate: bool = True) -> None:
    """Standard treatment of the K7 collapse band on any K7 axis."""
    ax.axvspan(K7_COLLAPSE_LOW, K7_COLLAPSE_HIGH,
               alpha=alpha, color=color)
    if annotate:
        ymin, ymax = ax.get_ylim()
        ax.text(K7_COLLAPSE_LABEL, ymin + (ymax - ymin) * 0.04,
                "K₇ collapse", fontsize=7.5,
                color="#7A1F1F", ha="center", style="italic")


def mark_inversion_threshold(ax, *, threshold: float = None,
                              alpha: float = 0.70) -> None:
    """Dashed vertical line marking the Damodaran inversion threshold."""
    t = DAMODARAN_INVERSION_THRESHOLD if threshold is None else threshold
    ax.axvline(t, color=ACCENT, linestyle="--", linewidth=0.9,
               alpha=alpha)
    ymin, ymax = ax.get_ylim()
    ax.text(t, ymax - (ymax - ymin) * 0.05,
            f"Inversion\nthreshold ({t:.2f})",
            fontsize=7.5, color=ACCENT, ha="left",
            style="italic")
