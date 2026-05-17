"""Plotly Sankey diagrams used by Appendix D.

Sankeys are an additional lens — they live alongside the existing
stacked-bar / matplotlib views, not in place of them. The bars answer
'how much in each bucket'; the Sankey answers 'where the money flows'.

Both functions take the same data structures that already power the
matplotlib views, so the call site can render the two charts side by
side without recomputing.
"""

from __future__ import annotations

from typing import Dict, List

import plotly.graph_objects as go


def _alpha(hex_color: str, alpha: float = 0.55) -> str:
    """Convert a #rrggbb hex string to rgba() with the given alpha."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


# ---------------------------------------------------------------------------
# Streaming case — incumbent vs IA-native entrant price decomposition
# ---------------------------------------------------------------------------

def streaming_price_sankey(results: List) -> go.Figure:
    """Sankey of monthly price flowing into each cost bucket, per scenario.

    Source nodes: the headline plan price under the incumbent and under
    each entrant scenario. Target nodes: the seven cost buckets.
    """
    incumbent = results[0].incumbent
    scenarios = [r for r in results]

    labels: List[str] = []
    sources: List[int] = []
    targets: List[int] = []
    values: List[float] = []
    colors: List[str] = []

    def add(label: str) -> int:
        labels.append(label)
        return len(labels) - 1

    # Source nodes — one per column.
    inc_src = add(f"Incumbent  (${incumbent.total:.2f})")
    scen_srcs = []
    for r in scenarios:
        scen_srcs.append(add(
            f"{r.scenario_label.title()}  "
            f"({int(r.substitution_pct*100)}% sub.)\n"
            f"${r.entrant.total:.2f}"))

    # Target nodes — seven cost buckets (key matches PriceDecomposition attr).
    bucket_keys = [
        ("content_licensing", "Content licensing & production", "#3C8DAD"),
        ("engineering",       "Engineering & technology",       "#E89B3C"),
        ("support",           "Customer support",               "#C44536"),
        ("cloud",             "Cloud & CDN infrastructure",     "#7B68A6"),
        ("marketing",         "Marketing",                      "#9C7B5A"),
        ("g_and_a",           "G & A",                           "#7A5C00"),
        ("margin",            "Operating margin",                "#0B6E4F"),
    ]
    bucket_node_ids: Dict[str, int] = {}
    bucket_colors: Dict[str, str] = {}
    for key, label, color in bucket_keys:
        bucket_node_ids[key] = add(label)
        bucket_colors[key] = color

    # Edges: incumbent  →  each bucket
    def add_edges_from(src_id: int, breakdown):
        for key, _, _ in bucket_keys:
            value = float(getattr(breakdown, key))
            if value <= 0:
                continue
            sources.append(src_id)
            targets.append(bucket_node_ids[key])
            values.append(value)
            colors.append(_alpha(bucket_colors[key]))

    add_edges_from(inc_src, incumbent)
    for src, r in zip(scen_srcs, scenarios):
        add_edges_from(src, r.entrant)

    node_colors = (["#1B3A57"] * (1 + len(scenarios))
                    + [b[2] for b in bucket_keys])

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=18,
            thickness=18,
            line=dict(color="white", width=0.5),
            label=labels,
            color=node_colors,
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=colors,
        ),
    ))
    fig.update_layout(
        title=dict(
            text="Streaming price → cost-bucket flows",
            font=dict(size=12),
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        height=440,
    )
    return fig


# ---------------------------------------------------------------------------
# Fiscal blocs — 5-year decomposition (Appendix D.6)
# ---------------------------------------------------------------------------

def fiscal_blocs_sankey(blocs: Dict[str, "FiscalBlocResult"],
                          countries: List[str] = None) -> go.Figure:
    """Sankey of fiscal flows per bloc: lost / exported / compensating."""
    if countries is None:
        countries = list(blocs.keys()) or ["brazil",
                                            "france",
                                            "united_states"]
    countries = [c for c in countries if c in blocs]

    labels: List[str] = []
    sources: List[int] = []
    targets: List[int] = []
    values: List[float] = []
    colors: List[str] = []

    def add(label: str) -> int:
        labels.append(label)
        return len(labels) - 1

    label_map = {
        "brazil": "Brazil",
        "france": "France",
        "united_states": "United States",
    }
    bloc_color = {
        "brazil": "#0B6E4F",
        "france": "#2C5282",
        "united_states": "#C44536",
    }

    bloc_ids = {c: add(f"{label_map.get(c, c)}  (5-year)") for c in countries}
    flow_keys = [
        ("lost_social_charges_usd_millions",
         "Lost employer charges",  "#C44536"),
        ("ai_token_export_usd_millions",
         "AI-token export",        "#7B68A6"),
        ("compensating_tax_gain_usd_millions",
         "Corporate-tax gain",     "#0B6E4F"),
    ]
    flow_ids = {key: add(label) for key, label, _ in flow_keys}
    flow_colors = {key: color for key, _, color in flow_keys}

    for c in countries:
        b = blocs[c]
        for key, _, _ in flow_keys:
            v = abs(float(getattr(b, key)))
            if v <= 0:
                continue
            sources.append(bloc_ids[c])
            targets.append(flow_ids[key])
            values.append(v)
            colors.append(_alpha(flow_colors[key]))

    node_colors = ([bloc_color.get(c, "#444") for c in countries]
                    + [c[2] for c in flow_keys])

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=18, thickness=18,
            line=dict(color="white", width=0.5),
            label=labels, color=node_colors,
        ),
        link=dict(source=sources, target=targets, value=values, color=colors),
    ))
    fig.update_layout(
        title=dict(
            text="Fiscal blocs — flow per bloc into the three structural components",
            font=dict(size=12),
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        height=400,
    )
    return fig
