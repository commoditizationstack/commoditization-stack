"""Live matplotlib figure generators used by the Streamlit tabs.

Each function below builds a single matplotlib Figure object that the
caller renders via `st.pyplot(fig)`. Functions are pure: they take all
their dependencies as arguments, never read st.session_state directly.

This makes them trivial to memoise with @st.cache_data when needed, and
trivial to unit-test outside Streamlit. Tabs are responsible for
applying the user's parameter overrides (via `state.effective_parameters()`)
before calling these functions.

Conventions:
  · All monetary values in USD.
  · All figures use a consistent palette (jurisdiction colors, layer colors).
  · `figsize` is tuned for 1100px Streamlit container width.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


JURISDICTION_COLORS = {
    "brazil": "#0B6E4F",
    "france": "#2C5282",
    "united_states": "#C44536",
}

JURISDICTION_LABEL = {
    "brazil": "Brazil",
    "france": "France",
    "united_states": "United States",
}


# ---------------------------------------------------------------------------
# Section 6 — Inverted Damodaran heatmap
# ---------------------------------------------------------------------------

def inverted_discount_heatmap(*,
                                threshold_layer4_share: float,
                                classical_discount_rate: float,
                                max_premium_when_inverted: float,
                                min_substitution_for_inversion: float = 0.30,
                                n_grid: int = 32) -> plt.Figure:
    """Heatmap of effective discount rate as a function of L4 share and AI sub."""
    layer4_shares = np.linspace(0.20, 0.90, n_grid)
    ai_potentials = np.linspace(0.05, 0.95, n_grid)
    Z = np.zeros((n_grid, n_grid))

    for i, ai in enumerate(ai_potentials):
        for j, l4 in enumerate(layer4_shares):
            if l4 <= threshold_layer4_share or ai < min_substitution_for_inversion:
                Z[i, j] = classical_discount_rate * 100
            else:
                above = (l4 - threshold_layer4_share) / max(1e-6, 1.0 - threshold_layer4_share)
                strength = above * ai
                effective_rate = (classical_discount_rate * (1.0 - strength)
                                  - max_premium_when_inverted * strength)
                Z[i, j] = effective_rate * 100

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(Z, aspect="auto", origin="lower",
                    extent=(layer4_shares.min(), layer4_shares.max(),
                            ai_potentials.min(), ai_potentials.max()),
                    cmap="RdBu_r", vmin=-15, vmax=20)
    ax.contour(layer4_shares, ai_potentials, Z, levels=[0],
                colors="black", linewidths=2, linestyles="--")
    ax.axvline(threshold_layer4_share, color="white", linewidth=1,
                linestyle=":", alpha=0.7)
    ax.text(threshold_layer4_share + 0.005, 0.92,
            f"  threshold = {threshold_layer4_share:.2f}",
            color="white", fontsize=9)
    plt.colorbar(im, ax=ax, label="Effective discount rate (%)")
    ax.set_xlabel("Team Layer-4 share")
    ax.set_ylabel("Layer-4 AI substitution potential")
    ax.set_title("Inverted key-person discount\n"
                  "(black dashed line = sign flip)", fontsize=10, pad=8)
    return fig


# ---------------------------------------------------------------------------
# Section 7.3 — Substitution NPV by jurisdiction (live bars)
# ---------------------------------------------------------------------------

def substitution_npv_bars(*,
                            n_employees_replaced: int,
                            avg_base_salary_by_country: Dict[str, float],
                            jurisdiction_params: Dict[str, Dict],
                            ai_cost_per_eng_year_usd: float = 12000,
                            discount_rate: float = 0.12,
                            horizon_years: int = 5,
                            highlight_country: str = "united_states",
                            countries: List[str] = None,
                            ) -> plt.Figure:
    """Bar chart of substitution NPV decomposition across the selected jurisdictions."""
    if countries is None:
        countries = ["brazil", "france", "united_states"]
    annuity_factor = sum(1.0 / (1.0 + discount_rate) ** t
                          for t in range(1, horizon_years + 1))

    recurring_savings = []
    termination_costs = []
    net_npv = []

    for c in countries:
        salary = avg_base_salary_by_country[c]
        j = jurisdiction_params[c]
        annual_labor = n_employees_replaced * salary * j["labor_cost_multiplier"]
        annual_ai = n_employees_replaced * ai_cost_per_eng_year_usd * j["ai_service_overhead"]
        net_annual = annual_labor - annual_ai
        termination = n_employees_replaced * salary * (
            j["termination_cost_fraction"] + j.get("notice_period_fraction", 0))
        npv_recur = net_annual * annuity_factor
        npv = npv_recur - termination

        recurring_savings.append(npv_recur / 1e6)
        termination_costs.append(termination / 1e6)
        net_npv.append(npv / 1e6)

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(countries))
    width = 0.6

    bars_save = ax.bar(x, recurring_savings, width, color="#2C5282",
                        label="NPV of 5-year recurring savings",
                        edgecolor="black", linewidth=0.4)
    bars_term = ax.bar(x, [-t for t in termination_costs], width,
                        bottom=recurring_savings, color="#C44536",
                        label="One-time termination cost (negative)",
                        edgecolor="black", linewidth=0.4)

    for i, (npv, c) in enumerate(zip(net_npv, countries)):
        is_highlight = (c == highlight_country)
        ax.text(i, npv + 1.5 if npv > 0 else npv - 1.5,
                f"NPV total: ${npv:.1f}M",
                ha="center", fontsize=10,
                fontweight="bold" if is_highlight else "normal",
                color="#1F1F1F" if not is_highlight else "#7A5C00",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#FFF5E5" if is_highlight else "white",
                          edgecolor="#F5C242" if is_highlight else "grey",
                          alpha=0.9))

    ax.set_xticks(x)
    ax.set_xticklabels([JURISDICTION_LABEL[c] + (" (CLT)" if c == "brazil"
                         else " (CDI)" if c == "france" else " (W-2)")
                         for c in countries])
    ax.set_ylabel("USD millions")
    ax.set_title(f"Substitution NPV decomposition by jurisdiction\n"
                 f"({n_employees_replaced} employees, "
                 f"{horizon_years}y horizon, discount rate {discount_rate:.0%})",
                 fontsize=10, pad=8)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.axhline(0, color="black", linewidth=0.6)
    return fig


# ---------------------------------------------------------------------------
# Section 7.4 — Cross-border M&A operating-cost basis
# ---------------------------------------------------------------------------

def crossborder_basis_bars(*,
                            n_employees: int,
                            avg_base_salary_by_country: Dict[str, float],
                            jurisdiction_params: Dict[str, Dict],
                            enterprise_value_usd: float = 200_000_000,
                            ai_cost_per_eng_year_usd: float = 12000,
                            discount_rate: float = 0.12,
                            horizon_years: int = 5,
                            countries: List[str] = None,
                            ) -> plt.Figure:
    """Inversion premium as % of EV under each operating-cost basis."""
    if countries is None:
        countries = ["brazil", "france", "united_states"]
    annuity_factor = sum(1.0 / (1.0 + discount_rate) ** t
                          for t in range(1, horizon_years + 1))
    premiums_pct = []
    for c in countries:
        salary = avg_base_salary_by_country[c]
        j = jurisdiction_params[c]
        annual_labor = n_employees * salary * j["labor_cost_multiplier"]
        annual_ai = n_employees * ai_cost_per_eng_year_usd * j["ai_service_overhead"]
        net = annual_labor - annual_ai
        termination = n_employees * salary * (
            j["termination_cost_fraction"] + j.get("notice_period_fraction", 0))
        npv = net * annuity_factor - termination
        premiums_pct.append(npv / enterprise_value_usd * 100)

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [JURISDICTION_COLORS[c] for c in countries]
    bars = ax.bar([JURISDICTION_LABEL[c] for c in countries], premiums_pct,
                   color=colors, edgecolor="black", linewidth=0.4)
    for b, v in zip(bars, premiums_pct):
        ax.text(b.get_x() + b.get_width()/2, v + 0.2, f"+{v:.2f}%",
                ha="center", fontsize=11, fontweight="bold")

    ax.set_ylabel(f"Inversion premium\n(% of ${enterprise_value_usd/1e6:.0f}M enterprise value)")
    ax.set_xlabel("Operating-cost basis post-acquisition")
    ax.set_title(f"Cross-border M&A: how the operating-cost basis drives the "
                 f"inversion premium\n({n_employees} employees substituted)",
                 fontsize=10, pad=8)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(premiums_pct) * 1.15)
    return fig


# ---------------------------------------------------------------------------
# Section 7.5 — Migration cash flow trajectories (3 jurisdictions)
# ---------------------------------------------------------------------------

def migration_cash_flow_trajectories(results_by_country: Dict[str, "MigrationResult"]
                                       ) -> plt.Figure:
    """Cumulative cash flow Q-3 to Q20 for three jurisdictions with phase shading."""
    fig, ax = plt.subplots(figsize=(11, 5.5))

    for country, color in JURISDICTION_COLORS.items():
        if country not in results_by_country:
            continue
        r = results_by_country[country]
        cum_m = np.array(r.cumulative_cash_usd) / 1e6
        ax.plot(r.quarters, cum_m, marker="o", markersize=4, linewidth=2,
                color=color, label=JURISDICTION_LABEL[country])
        ax.annotate(f"${cum_m[-1]:.2f}M", xy=(r.quarters[-1], cum_m[-1]),
                    xytext=(5, 0), textcoords="offset points",
                    fontsize=9, fontweight="bold", color=color, va="center")

    ax.axhline(0, color="black", linewidth=0.7)
    ax.axvline(0, color="grey", linewidth=0.5, linestyle="--")
    ax.axvspan(-3.5, -0.5, alpha=0.10, color="#F5C242")
    ax.axvspan(-0.5, 3.5, alpha=0.10, color="#C44536")
    ax.axvspan(3.5, 10.5, alpha=0.08, color="#2C5282")
    ax.axvspan(10.5, 21, alpha=0.08, color="#0B6E4F")

    ymin, ymax = ax.get_ylim()
    label_y = ymax - (ymax - ymin) * 0.04
    ax.text(-2, label_y, "Assessment", ha="center", fontsize=8,
            color="#7A5C00", va="top", style="italic")
    ax.text(1.5, label_y, "Transition", ha="center", fontsize=8,
            color="#7A1F1F", va="top", style="italic")
    ax.text(7, label_y, "Learning", ha="center", fontsize=8,
            color="#1F3A6A", va="top", style="italic")
    ax.text(16, label_y, "Steady state", ha="center", fontsize=8,
            color="#1F5040", va="top", style="italic")

    ax.set_xlabel("Quarters from T0 (migration decision)")
    ax.set_ylabel("Cumulative cash flow (USD millions)")
    ax.set_title("Migration cash-flow trajectories with AI orchestrator (live)",
                 fontsize=10, pad=8)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    return fig


# ---------------------------------------------------------------------------
# Section 6.5 — Hype Cycle classical vs double-valley
# ---------------------------------------------------------------------------

def hype_cycle_double_valley(*,
                              n_quarters: int = 32,
                              classical_params: Dict,
                              post_genai_params: Dict,
                              classical_rise_exp: float = 1.5,
                              post_rise_exp: float = 1.3,
                              ) -> plt.Figure:
    """Build classical single-valley curve + post-AI double-valley curve."""
    t = np.arange(n_quarters + 1)

    # Classical curve
    cp = classical_params
    pk_q, tr_q, pl_q = cp["peak_quarter"], cp["trough_quarter"], cp["plateau_quarter"]
    pk_h, tr_h, pl_h = cp["peak_height"], cp["trough_height"], cp["plateau_height"]
    y_cls = np.zeros_like(t, dtype=float)
    rise = t <= pk_q
    y_cls[rise] = pk_h * (t[rise] / pk_q) ** classical_rise_exp
    decline = (t > pk_q) & (t <= tr_q)
    nrm = (t[decline] - pk_q) / max(1, tr_q - pk_q)
    y_cls[decline] = pk_h + (tr_h - pk_h) * (1 - np.cos(np.pi * nrm)) / 2
    enlight = (t > tr_q) & (t <= pl_q)
    nrm = (t[enlight] - tr_q) / max(1, pl_q - tr_q)
    y_cls[enlight] = tr_h + (pl_h - tr_h) * (1 - np.cos(np.pi * nrm)) / 2
    y_cls[t > pl_q] = pl_h

    # Post-AI curve
    pp = post_genai_params
    y_post = np.zeros_like(t, dtype=float)
    m1 = t <= pp["peak_quarter"]
    y_post[m1] = pp.get("peak_height", 100) * (t[m1] / pp["peak_quarter"]) ** post_rise_exp
    m2 = (t > pp["peak_quarter"]) & (t <= pp["trough_quarter"])
    nrm = (t[m2] - pp["peak_quarter"]) / max(1, pp["trough_quarter"] - pp["peak_quarter"])
    y_post[m2] = pp.get("peak_height", 100) + (
        pp["trough_height"] - pp.get("peak_height", 100)) * (1 - np.cos(np.pi * nrm)) / 2
    m3 = (t > pp["trough_quarter"]) & (t <= pp["second_peak_quarter"])
    nrm = (t[m3] - pp["trough_quarter"]) / max(
        1, pp["second_peak_quarter"] - pp["trough_quarter"])
    y_post[m3] = pp["trough_height"] + (pp["second_peak_height"]
                                          - pp["trough_height"]) * (1 - np.cos(np.pi * nrm)) / 2
    m4 = (t > pp["second_peak_quarter"]) & (t <= pp["commoditization_valley_quarter"])
    nrm = (t[m4] - pp["second_peak_quarter"]) / max(
        1, pp["commoditization_valley_quarter"] - pp["second_peak_quarter"])
    y_post[m4] = pp["second_peak_height"] + (pp["commoditization_valley_height"]
                                                - pp["second_peak_height"]) * (1 - np.cos(np.pi * nrm)) / 2
    m5 = (t > pp["commoditization_valley_quarter"]) & (t <= pp["plateau_quarter"])
    nrm = (t[m5] - pp["commoditization_valley_quarter"]) / max(
        1, pp["plateau_quarter"] - pp["commoditization_valley_quarter"])
    y_post[m5] = pp["commoditization_valley_height"] + (pp["plateau_height"]
                                                          - pp["commoditization_valley_height"]) * (1 - np.cos(np.pi * nrm)) / 2
    y_post[t > pp["plateau_quarter"]] = pp["plateau_height"]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(t, y_cls, color="#2C5282", linewidth=2.2,
            label="Classical Hype Cycle (single valley)")
    ax.plot(t, y_post, color="#C44536", linewidth=2.2,
            label="Post-GenAI (double valley)")
    # Annotations
    ax.annotate("Classical Trough", xy=(tr_q, tr_h), xytext=(tr_q - 5, tr_h + 5),
                fontsize=8, color="#1F3A6A",
                arrowprops=dict(arrowstyle="->", color="#2C5282", lw=0.6))
    ax.annotate("Commoditization\nValley (new)",
                xy=(pp["commoditization_valley_quarter"],
                    pp["commoditization_valley_height"]),
                xytext=(pp["commoditization_valley_quarter"] + 1,
                        pp["commoditization_valley_height"] - 5),
                fontsize=8, color="#7A1F1F",
                arrowprops=dict(arrowstyle="->", color="#C44536", lw=0.6))

    ax.set_xlabel("Quarters since innovation trigger")
    ax.set_ylabel("Expectations (Gartner-style index)")
    ax.set_title("Hype Cycle: classical (single valley) vs post-AI (double valley)",
                 fontsize=10, pad=8)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    return fig


# ---------------------------------------------------------------------------
# Appendix D — Streaming price decomposition + cross-jurisdictional
# ---------------------------------------------------------------------------

def streaming_price_decomposition(*, results: List) -> plt.Figure:
    """Stacked-bar decomposition: incumbent + 3 scenario entrants."""
    incumbent = results[0].incumbent

    fig, ax = plt.subplots(figsize=(10, 5.5))
    labels = ["Incumbent"] + [f"{r.scenario_label.title()}\n({int(r.substitution_pct*100)}%)"
                                for r in results]
    x = np.arange(len(labels))
    width = 0.55

    component_order = ["content_licensing", "engineering", "support", "cloud",
                        "marketing", "g_and_a", "margin"]
    component_colors = {
        "content_licensing": "#2C5282", "engineering": "#E07B39",
        "support": "#C44536", "cloud": "#8E44AD", "marketing": "#F5C242",
        "g_and_a": "#7B7D7D", "margin": "#0B6E4F",
    }
    component_labels = {
        "content_licensing": "Content", "engineering": "Engineering",
        "support": "Support", "cloud": "Cloud", "marketing": "Marketing",
        "g_and_a": "G&A", "margin": "Margin",
    }

    decomps = [incumbent.to_dict()] + [r.entrant.to_dict() for r in results]
    bottom = np.zeros(len(labels))
    for comp in component_order:
        vals = np.array([d[comp] for d in decomps])
        ax.bar(x, vals, width, bottom=bottom,
                color=component_colors[comp],
                label=component_labels[comp],
                edgecolor="white", linewidth=0.3)
        bottom += vals

    for i, total in enumerate(bottom):
        if i == 0:
            ax.text(i, total + 0.3, f"${total:.2f}", ha="center",
                    fontsize=10, fontweight="bold", color="#2C5282")
        else:
            reduction = (incumbent.total - total) / incumbent.total
            ax.text(i, total + 0.3, f"${total:.2f}", ha="center",
                    fontsize=10, fontweight="bold", color="#C44536")
            ax.text(i, total + 0.85, f"−{reduction*100:.0f}%", ha="center",
                    fontsize=9, color="#C44536")

    ax.axhline(incumbent.content_licensing, linestyle="--", color="#2C5282",
                linewidth=1, alpha=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Monthly subscription price (USD)")
    ax.set_ylim(0, 20)
    ax.set_title("Streaming price decomposition: incumbent vs IA-native entrant",
                 fontsize=10, pad=8)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92, ncol=3)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    return fig


# ---------------------------------------------------------------------------
# Appendix D.6 — Fiscal blocs 5-year decomposition
# ---------------------------------------------------------------------------

def fiscal_blocs_decomposition(blocs: Dict[str, "FiscalBlocResult"],
                                  countries: List[str] = None) -> plt.Figure:
    """Stacked decomposition + net impact label per bloc."""
    if countries is None:
        countries = list(blocs.keys()) or ["brazil", "france", "united_states"]
    countries = [c for c in countries if c in blocs]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(countries))
    width = 0.55

    lost = np.array([blocs[c].lost_social_charges_usd_millions for c in countries])
    export = np.array([blocs[c].ai_token_export_usd_millions for c in countries])
    gain = np.array([blocs[c].compensating_tax_gain_usd_millions for c in countries])

    ax.bar(x, lost, width, color="#F5C242", label="Lost employer social charges",
            edgecolor="black", linewidth=0.4)
    ax.bar(x, export, width, bottom=lost, color="#8E44AD",
            label="Fiscal exportation via AI tokens", edgecolor="black", linewidth=0.4)
    ax.bar(x, -gain, width, color="#0B6E4F",
            label="Compensating gain (corporate tax)", edgecolor="black", linewidth=0.4)

    for i, c in enumerate(countries):
        net = blocs[c].net_impact_usd_millions
        top = max(lost[i] + max(0, export[i]), 0)
        color = "#C44536" if net > 0 else "#0B6E4F"
        sign = "+" if net > 0 else ""
        ax.text(i, top + 350,
                f"Net: ${sign}{net:.0f}M",
                ha="center", fontsize=9, fontweight="bold", color=color,
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#FFE5E5" if net > 0 else "#E5F5E5",
                          edgecolor=color, alpha=0.9))

    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels([JURISDICTION_LABEL[c] for c in countries])
    ax.set_ylabel("Cumulative 5-year impact (USD millions)")
    ax.set_title("Fiscal impact across 3 blocs (5-year, moderate substitution)",
                 fontsize=10, pad=8)
    ax.legend(loc="lower left", fontsize=8, framealpha=0.92,
              bbox_to_anchor=(0, -0.30))
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    return fig


# ---------------------------------------------------------------------------
# Appendix E.5 — Fragility map with two case studies + custom firm
# ---------------------------------------------------------------------------

def fragility_map(*,
                    l6_coefficient: float,
                    color_vmin: float,
                    color_vmax: float,
                    firms: List[Tuple[str, float, float, str]]
                    ) -> plt.Figure:
    """Fragility contour + plotted firms.

    `firms` is a list of (label, L4 share, L6 share, color) tuples.
    """
    l4 = np.linspace(0, 0.70, 100)
    l6 = np.linspace(0, 0.50, 100)
    L4, L6 = np.meshgrid(l4, l6)
    Z = L4 - l6_coefficient * L6

    fig, ax = plt.subplots(figsize=(9, 6))
    im = ax.contourf(L4, L6, Z, levels=20, cmap="RdYlGn_r",
                      vmin=color_vmin, vmax=color_vmax)
    ax.contour(L4, L6, Z, levels=[0], colors="black",
                linewidths=1.5, linestyles="--")
    ax.plot([0, 0.50], [0, 0.50], color="grey", linestyle=":",
            linewidth=1, alpha=0.7)

    for label, l4_s, l6_s, color in firms:
        idx = l4_s - l6_coefficient * l6_s
        zone = "resilient" if idx < -0.1 else "fragile" if idx > 0.1 else "borderline"
        ax.scatter(l4_s, l6_s, s=200, color=color, marker="o",
                    edgecolor="black", linewidth=1.5, zorder=10,
                    label=f"{label} (idx={idx:.2f}, {zone})")

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(f"Fragility index\n(L4 − {l6_coefficient:.1f} × L6)", fontsize=9)
    ax.set_xlabel("Layer-4 share (codified, AI-substitutable work)")
    ax.set_ylabel("Layer-6 share (institutional defensibility)")
    ax.set_xlim(0, 0.70)
    ax.set_ylim(0, 0.55)
    ax.set_title("Fragility map (live)", fontsize=10, pad=8)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.3)
    return fig


# ---------------------------------------------------------------------------
# Appendix F.3 — Three structural sensitivities
# ---------------------------------------------------------------------------

def upstream_k7_sensitivity(*, k_grid: np.ndarray,
                              curves: Dict[str, np.ndarray]) -> plt.Figure:
    """K7 sensitivity per jurisdiction with collapse threshold."""
    fig, ax = plt.subplots(figsize=(9, 5))

    colors = {
        "united_states_same_bloc": ("#2C5282", "United States (same-bloc)", "-"),
        "france_same_bloc": ("#F5C242", "France (same-bloc)", "-"),
        "brazil_same_bloc": ("#0B6E4F", "Brazil (same-bloc)", "-"),
        "united_states_cross_bloc": ("#8E44AD", "United States (cross-bloc)", "--"),
    }
    for key, (color, label, ls) in colors.items():
        if key in curves:
            ax.plot(k_grid, curves[key] * 100, color=color, linewidth=2.2,
                    linestyle=ls, label=label)

    ax.axvspan(0, 0.45, alpha=0.10, color="#C44536")
    ax.axvline(0.45, color="#C44536", linewidth=1, linestyle=":")
    ax.text(0.30, ax.get_ylim()[1] * 0.85,
            "Collapse threshold\n(K₇ ≈ 0.45)",
            fontsize=9, color="#7A1F1F", ha="center")

    ax.set_xlabel("Knowledge-integration coefficient K₇")
    ax.set_ylabel("Inversion premium (% of EV)")
    ax.set_title("Inversion premium sensitivity to the cross-border knowledge regime",
                 fontsize=10, pad=8)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_xlim(0.2, 1.0)
    return fig


# ---------------------------------------------------------------------------
# Appendix G.1 — Double threshold
# ---------------------------------------------------------------------------

def double_threshold(*, d: "DoubleThresholdData") -> plt.Figure:
    """Gross saving + 2 floors (orchestrator economic + XAI compliance)."""
    fig, ax = plt.subplots(figsize=(9, 5.5))

    ax.plot(d.headcount, d.gross_saving_usd / 1000, color="#0B6E4F", linewidth=2.4,
            label="Gross saving from substitution")
    ax.axhline(d.orchestrator_floor_usd / 1000, linestyle="--", color="grey",
                linewidth=1.5, label="Orchestrator overhead floor")
    ax.axhline(d.xai_floor_usd / 1000, linestyle="--", color="#7A1F1F",
                linewidth=1.5, label="Orchestrator + XAI infrastructure floor")

    ax.axvline(d.economic_break_even, linestyle=":", color="grey", alpha=0.7)
    ax.text(d.economic_break_even + 1, d.orchestrator_floor_usd / 1000 - 25,
            f"Econ. threshold\n≈ {d.economic_break_even:.0f} eng.",
            fontsize=8, color="grey")
    ax.axvline(d.compliance_break_even, linestyle=":", color="#7A1F1F", alpha=0.7)
    ax.text(d.compliance_break_even + 1, d.xai_floor_usd / 1000 + 50,
            f"Compliance threshold\n≈ {d.compliance_break_even:.0f} eng.",
            fontsize=8, color="#7A1F1F")

    if d.compliance_break_even > d.economic_break_even:
        ax.axvspan(d.economic_break_even, d.compliance_break_even,
                    alpha=0.15, color="#F5C242",
                    label="Regulatory-compliance gap")

    ax.set_xlabel("Engineering headcount of adopting firm")
    ax.set_ylabel("Annual amount (USD thousands)")
    ax.set_xlim(0, max(d.headcount))
    ax.set_ylim(0, max(d.gross_saving_usd) / 1000 * 1.05)
    ax.set_title("Double threshold for AI migration in regulated small firms",
                 fontsize=10, pad=8)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    return fig


# ---------------------------------------------------------------------------
# Appendix G.2 — XAI capacity gap
# ---------------------------------------------------------------------------

def xai_capacity_gap(*, x: "XAICapacityGapData") -> plt.Figure:
    """Three K7 regimes × two blocs over 8 years."""
    fig, ax = plt.subplots(figsize=(10, 5.5))

    regimes = [
        ("K = 1.0 (integrated)", x.bloc_a_k1_0, x.bloc_b_k1_0, "#0B6E4F",
         x.endpoint_gaps["k_1_0"], "-"),
        ("K = 0.7 (current)", x.bloc_a_k0_7, x.bloc_b_k0_7, "#F5C242",
         x.endpoint_gaps["k_0_7"], "--"),
        ("K = 0.45 (collapse)", x.bloc_a_k0_45, x.bloc_b_k0_45, "#C44536",
         x.endpoint_gaps["k_0_45"], ":"),
    ]
    for label, bloc_a, bloc_b, color, gap, ls in regimes:
        ax.plot(x.years, bloc_a, color=color, linewidth=2.2, linestyle=ls,
                label=f"Bloc A — {label}")
        ax.plot(x.years, bloc_b, color=color, linewidth=1.4, alpha=0.55,
                linestyle=ls)
        # Endpoint Δ
        ax.annotate("",
                    xy=(x.years[-1] + 0.15, bloc_b[-1]),
                    xytext=(x.years[-1] + 0.15, bloc_a[-1]),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.2))
        ax.text(x.years[-1] + 0.3,
                (bloc_a[-1] + bloc_b[-1]) / 2,
                f"Δ={gap:.2f}",
                fontsize=8, fontweight="bold", color=color, va="center")

    ax.set_xlabel("Year")
    ax.set_ylabel("XAI capacity index (1.0 = baseline)")
    ax.set_title("XAI capacity gap across 2 blocs under 3 K₇ regimes (live)",
                 fontsize=10, pad=8)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    return fig


# ===========================================================================
# Appendix A — Layered DCF (live)
# ===========================================================================
#
# These helpers consume the parameter overlay directly so the user's edits
# in ⚙️ Configuration (or via Scenario YAML upload) flow straight through to
# the plots. They compute simplified versions of the figures from the paper
# without Monte Carlo bands (kept synchronous so they redraw in < 1 s).

NC_COLOR = "#0B6E4F"
DF_COLOR = "#C44536"


def _classical_capm(*, rf: float, beta: float, erp: float) -> float:
    return rf + beta * erp


def _layered_yearly_rate(*, rf: float, beta: float, erp: float,
                          trl_for_year: int,
                          trl_premium_schedule: Dict[int, float],
                          layer_exposure: Dict[str, float],
                          layer_risk_coefficients: Dict[str, float]) -> float:
    """Base CAPM + TRL premium + Σ (exposure_l × risk_coefficient_l)."""
    base = _classical_capm(rf=rf, beta=beta, erp=erp)
    trl_p = float(trl_premium_schedule.get(int(trl_for_year), 0.0))
    layer_p = sum(float(layer_exposure.get(k, 0.0))
                  * float(layer_risk_coefficients.get(k, 0.0))
                  for k in layer_risk_coefficients)
    return base + trl_p + layer_p


def appendix_a_trl_trajectory(*, parameters: Dict) -> plt.Figure:
    """A.1 — TRL × discount rate trajectory (live)."""
    macro = parameters["firms_appendix_b"]["macro"]
    rf = float(macro["risk_free_rate"])
    erp = float(macro["equity_risk_premium"])
    trl_sched_raw = parameters["valuation_layered"]["trl_discount_premium"]
    trl_sched = {int(k): float(v) for k, v in trl_sched_raw.items()}
    coeffs = parameters["valuation_layered"]["layer_risk_coefficients"]
    cs = parameters["case_studies_dynamic"]

    fig, ax = plt.subplots(figsize=(10, 5.6))

    for firm_key, color, marker in [("neurocertify", NC_COLOR, "o"),
                                       ("dataflow_pro", DF_COLOR, "s")]:
        firm = cs[firm_key]
        trls = firm["trl_trajectory"]
        beta = float(parameters["firms_appendix_b"][
            "dataflow" if firm_key == "dataflow_pro" else firm_key
        ]["phases"]["beta_unlevered_phase_3"])
        layer_exp = firm["layer_exposure"]
        years = [f"Y{i+1}" for i in range(len(trls))]
        rates = [_layered_yearly_rate(
            rf=rf, beta=beta, erp=erp,
            trl_for_year=t,
            trl_premium_schedule=trl_sched,
            layer_exposure=layer_exp,
            layer_risk_coefficients=coeffs,
        ) * 100 for t in trls]
        classical_rate = _classical_capm(rf=rf, beta=beta, erp=erp) * 100

        x = np.arange(len(years))
        label = firm.get("label", firm_key)
        ax.plot(x, rates, marker=marker, linewidth=2.4, color=color,
                label=f"{label} — layered (TRL-modulated)")
        ax.axhline(classical_rate, linestyle="--", color=color, alpha=0.55,
                   label=f"{label} — classical Damodaran ({classical_rate:.1f}%)")
        for i, trl in enumerate(trls):
            ax.annotate(f"TRL {trl}", (i, rates[i]),
                          textcoords="offset points", xytext=(0, 8),
                          ha="center", fontsize=8, color=color)
        ax.set_xticks(x)
        ax.set_xticklabels(years)

    ax.set_xlabel("Year")
    ax.set_ylabel("Discount rate (%)")
    ax.set_title("Appendix A.1 — TRL-modulated discount rate trajectory (live)",
                 fontsize=10, pad=8)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", fontsize=8.5, framealpha=0.92)
    fig.tight_layout()
    return fig


def appendix_a_layer_risk_decomposition(*, parameters: Dict) -> plt.Figure:
    """A.2 — Layer-decomposed firm-specific risk premium (live)."""
    coeffs = parameters["valuation_layered"]["layer_risk_coefficients"]
    cs = parameters["case_studies_dynamic"]

    layer_keys = ["layer_1_infra", "layer_2_foundation", "layer_3_capability",
                   "layer_4_codified", "layer_5_judgment",
                   "layer_6_institutional", "layer_7_crossborder"]
    labels = ["L1 Infra", "L2 Foundation", "L3 Capability",
              "L4 Codified", "L5 Judgment", "L6 Institutional",
              "L7 Crossborder"]

    def contributions(firm: Dict) -> List[float]:
        exp = firm["layer_exposure"]
        return [float(exp.get(k, 0.0)) * float(coeffs.get(k, 0.0)) * 100
                for k in layer_keys]

    nc_vals = contributions(cs["neurocertify"])
    df_vals = contributions(cs["dataflow_pro"])

    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    y = np.arange(len(labels))
    w = 0.36
    bars_n = ax.barh(y - w/2, nc_vals, w, color=NC_COLOR,
                       label=cs["neurocertify"].get("label", "NeuroCertify"),
                       edgecolor="black", linewidth=0.4)
    bars_d = ax.barh(y + w/2, df_vals, w, color=DF_COLOR,
                       label=cs["dataflow_pro"].get("label", "DataFlow Pro"),
                       edgecolor="black", linewidth=0.4)
    for bar, val in list(zip(bars_n, nc_vals)) + list(zip(bars_d, df_vals)):
        x_pos = bar.get_width()
        ha = "left" if x_pos >= 0 else "right"
        offset = 0.05 if x_pos >= 0 else -0.05
        ax.text(x_pos + offset, bar.get_y() + bar.get_height()/2,
                f"{val:+.2f}pp", va="center", ha=ha, fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.invert_yaxis()
    ax.set_xlabel("Contribution to firm-specific risk premium (pp)")
    ax.set_title("Appendix A.2 — Layer-decomposed risk premium (live)",
                 fontsize=10, pad=8)
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92)
    fig.tight_layout()
    return fig


def appendix_a_valuation_comparison(*, parameters: Dict) -> plt.Figure:
    """A.3 — Enterprise value: classical Damodaran vs layered DCF (live)."""
    macro = parameters["firms_appendix_b"]["macro"]
    rf = float(macro["risk_free_rate"])
    erp = float(macro["equity_risk_premium"])
    g = float(macro.get("terminal_growth", 0.03))
    trl_sched_raw = parameters["valuation_layered"]["trl_discount_premium"]
    trl_sched = {int(k): float(v) for k, v in trl_sched_raw.items()}
    coeffs = parameters["valuation_layered"]["layer_risk_coefficients"]
    cs = parameters["case_studies_dynamic"]

    def ev_pair(firm: Dict, firms_b_key: str) -> Tuple[float, float]:
        fcfs = [float(x) * 1e6 for x in firm["fcf_usd_millions"]]
        trls = firm["trl_trajectory"]
        layer_exp = firm["layer_exposure"]
        beta = float(parameters["firms_appendix_b"][firms_b_key]
                      ["phases"]["beta_unlevered_phase_3"])
        classical = _classical_capm(rf=rf, beta=beta, erp=erp)
        layered_rates = [_layered_yearly_rate(
            rf=rf, beta=beta, erp=erp,
            trl_for_year=t,
            trl_premium_schedule=trl_sched,
            layer_exposure=layer_exp,
            layer_risk_coefficients=coeffs,
        ) for t in trls]

        # Classical DCF: single rate, terminal at year T
        pv_c = sum(f / (1 + classical) ** (i + 1) for i, f in enumerate(fcfs))
        tv_c = (fcfs[-1] * (1 + g) / max(classical - g, 1e-6)
                / (1 + classical) ** len(fcfs))
        ev_classical = pv_c + tv_c

        # Layered DCF: compounded discount factors, year-by-year
        pv_l = 0.0
        cum = 1.0
        for rate, fcf in zip(layered_rates, fcfs):
            cum *= (1 + rate)
            pv_l += fcf / cum
        drag = float(firm.get("second_valley_drag", 0.0))
        last_rate = layered_rates[-1]
        if last_rate > g:
            tv_l = fcfs[-1] * (1 + g) / (last_rate - g) * (1 - drag) / cum
        else:
            tv_l = 0.0
        ev_layered = pv_l + tv_l
        return ev_classical, ev_layered

    nc_c, nc_l = ev_pair(cs["neurocertify"], "neurocertify")
    df_c, df_l = ev_pair(cs["dataflow_pro"], "dataflow")

    fig, ax = plt.subplots(figsize=(10, 5.6))
    x = np.arange(2)
    w = 0.32
    classical_vals = [nc_c / 1e6, df_c / 1e6]
    layered_vals = [nc_l / 1e6, df_l / 1e6]
    bars_c = ax.bar(x - w/2, classical_vals, w, color="#7B7D7D",
                      label="Classical Damodaran (single rate)",
                      edgecolor="black", linewidth=0.4)
    bars_l = ax.bar(x + w/2, layered_vals, w,
                      color=[NC_COLOR, DF_COLOR],
                      label="Layered seven-layer DCF",
                      edgecolor="black", linewidth=0.4)
    for bar, val in zip(bars_c, classical_vals):
        ax.text(bar.get_x() + bar.get_width()/2, val + max(classical_vals + layered_vals) * 0.02,
                f"${val:.1f}M", ha="center", fontsize=9.5)
    for bar, val in zip(bars_l, layered_vals):
        ax.text(bar.get_x() + bar.get_width()/2, val + max(classical_vals + layered_vals) * 0.02,
                f"${val:.1f}M", ha="center", fontsize=9.5, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([cs["neurocertify"].get("label", "NeuroCertify"),
                         cs["dataflow_pro"].get("label", "DataFlow Pro")])
    ax.set_ylabel("Enterprise Value (USD millions)")
    ax.set_title("Appendix A.3 — Enterprise value: classical vs layered DCF (live)",
                 fontsize=10, pad=8)
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    return fig


# ===========================================================================
# Appendix B — Two-phase CAPM / WACC / EVA (live)
# ===========================================================================

def _two_phase_wacc(*, year: int, rf: float, erp: float,
                     phases: Dict) -> Dict[str, float]:
    p1_end = int(phases["phase_1_end_year"])
    p2_end = int(phases["phase_2_end_year"])
    if year <= p1_end:
        suffix = "phase_1"
    elif year <= p2_end:
        suffix = "phase_2"
    else:
        suffix = "phase_3"
    beta_u = float(phases[f"beta_unlevered_{suffix}"])
    de = float(phases[f"de_ratio_{suffix}"])
    kd_spread = float(phases[f"kd_spread_{suffix}"])
    tax = float(phases["effective_tax_rate"])
    beta_l = beta_u * (1.0 + (1.0 - tax) * de)
    ke = rf + beta_l * erp
    kd = rf + kd_spread
    d_v = de / (1.0 + de)
    e_v = 1.0 / (1.0 + de)
    wacc = e_v * ke + d_v * kd * (1.0 - tax)
    return {"wacc": wacc, "ke": ke, "phase": suffix}


def appendix_b_two_phase_cost_of_capital(*, parameters: Dict) -> plt.Figure:
    """B.1 — Two-phase WACC and Ke trajectory for both case companies (live)."""
    macro = parameters["firms_appendix_b"]["macro"]
    rf = float(macro["risk_free_rate"])
    erp = float(macro["equity_risk_premium"])

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))

    for ax, firm_key, color in [(axes[0], "neurocertify", NC_COLOR),
                                  (axes[1], "dataflow", DF_COLOR)]:
        phases = parameters["firms_appendix_b"][firm_key]["phases"]
        label = parameters["firms_appendix_b"][firm_key].get(
            "label", firm_key.title())
        n_years = int(phases["phase_2_end_year"]) + 1
        years = list(range(1, n_years + 1))
        wacc_traj = []
        ke_traj = []
        for yr in years:
            comp = _two_phase_wacc(year=yr, rf=rf, erp=erp, phases=phases)
            wacc_traj.append(comp["wacc"] * 100)
            ke_traj.append(comp["ke"] * 100)
        # Classical: use phase-3 (terminal) values as the single-rate reference
        classical = _two_phase_wacc(year=n_years, rf=rf, erp=erp, phases=phases)
        classical_wacc = classical["wacc"] * 100

        # Background shading for phases
        p1_end = int(phases["phase_1_end_year"])
        p2_end = int(phases["phase_2_end_year"])
        ax.axvspan(0.5, p1_end + 0.5, color="#EEEEEE", alpha=0.5)
        ax.axvspan(p1_end + 0.5, p2_end + 0.5, color="#F4CFCF", alpha=0.5)
        ax.axvspan(p2_end + 0.5, n_years + 0.5, color="#D6EAD6", alpha=0.5)
        ax.text(0.5 + p1_end / 2, ax.get_ylim()[1] if False else 9.0,
                "Phase 1 (growth)", fontsize=8, color="#666",
                ha="center", style="italic")

        ax.plot(years, wacc_traj, marker="o", color=color, linewidth=2.2,
                label="Two-phase WACC")
        ax.plot(years, ke_traj, marker="s", linestyle="--", color=color,
                linewidth=1.6, alpha=0.85, label="Two-phase Ke")
        ax.axhline(classical_wacc, linestyle=":", color="#444", linewidth=1.2,
                   label=f"Classical single-rate WACC ({classical_wacc:.2f}%)")
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Year")
        ax.set_ylabel("Cost of capital (%)")
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.set_axisbelow(True)
        ax.legend(fontsize=8, loc="lower right", framealpha=0.92)

    fig.suptitle("Appendix B.1 — Two-phase cost of capital (live)",
                 fontsize=11, y=1.02)
    fig.tight_layout()
    return fig


def death_valley_cash_trajectories(*,
                                      classical_cash: np.ndarray,
                                      post_genai_cash: np.ndarray,
                                      post_genai_params: Dict,
                                      ) -> plt.Figure:
    """Cash trajectories under classical vs post-AI regimes (live).

    Takes pre-computed cash arrays (the caller computes them from
    src.death_valley using the user's parameter overlay) plus the
    post-AI parameter dict so we can annotate the refinancing event
    and the commoditization-valley window.
    """
    fig, ax = plt.subplots(figsize=(11, 5.6))
    n_c = len(classical_cash)
    n_p = len(post_genai_cash)
    ax.plot(np.arange(n_c), classical_cash / 1e6, color="#2C5282",
            linewidth=2.2, label="Classical (single valley)")
    ax.plot(np.arange(n_p), post_genai_cash / 1e6, color="#C44536",
            linewidth=2.4, label="Post-GenAI (double valley)")

    # Cash-crisis fill
    ax.fill_between(np.arange(n_p), post_genai_cash / 1e6, 0,
                     where=(post_genai_cash < 0),
                     color="#C44536", alpha=0.15, label="Cash crisis zone")

    ax.axhline(0, color="black", linewidth=0.7)

    # Annotate refinancing event
    refi_month = int(post_genai_params.get("refinancing_event_month", 14))
    if 0 <= refi_month < n_p:
        refi_y = post_genai_cash[refi_month] / 1e6
        ax.annotate("Series A\n(refinancing)",
                     xy=(refi_month, refi_y),
                     xytext=(refi_month + 3, refi_y + 1.5),
                     arrowprops=dict(arrowstyle="->", color="grey",
                                       lw=0.8),
                     fontsize=8.5, color="#444")

    # Shade the commoditization valley window
    cv_start = int(post_genai_params.get(
        "commoditization_valley_start_month", 22))
    cv_end = int(post_genai_params.get(
        "commoditization_valley_end_month", 36))
    cv_end = min(cv_end, n_p - 1)
    if cv_end > cv_start:
        ax.axvspan(cv_start, cv_end, color="#C44536", alpha=0.08,
                    label="Commoditization valley")
        ax.text((cv_start + cv_end) / 2,
                 ax.get_ylim()[1] * 0.92 if ax.get_ylim()[1] > 0 else 0.5,
                 "Second valley", fontsize=8, color="#7A1F1F",
                 ha="center", style="italic")

    ax.set_xlabel("Months since founding")
    ax.set_ylabel("Cash (USD millions)")
    ax.set_title("Death valley: classical vs post-AI double valley (live)",
                  fontsize=10, pad=8)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=8.5, framealpha=0.92)
    fig.tight_layout()
    return fig


def appendix_b_two_phase_eva_trajectory(*, parameters: Dict) -> plt.Figure:
    """B.2 — EVA: phase-conditional WACC vs classical single-WACC (live)."""
    macro = parameters["firms_appendix_b"]["macro"]
    rf = float(macro["risk_free_rate"])
    erp = float(macro["equity_risk_premium"])

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
    for ax, firm_key, color in [(axes[0], "neurocertify", NC_COLOR),
                                  (axes[1], "dataflow", DF_COLOR)]:
        firm = parameters["firms_appendix_b"][firm_key]
        phases = firm["phases"]
        label = firm.get("label", firm_key.title())
        nopat = list(firm.get("nopat_usd", []))
        ic = list(firm.get("invested_capital_usd", []))
        n = min(len(nopat), len(ic))
        years = list(range(1, n + 1))
        eva_two_phase = []
        eva_classical = []
        classical = _two_phase_wacc(year=n, rf=rf, erp=erp, phases=phases)["wacc"]
        for yr in years:
            wacc = _two_phase_wacc(year=yr, rf=rf, erp=erp, phases=phases)["wacc"]
            eva_two_phase.append(
                (nopat[yr - 1] - wacc * ic[yr - 1]) / 1e6)
            eva_classical.append(
                (nopat[yr - 1] - classical * ic[yr - 1]) / 1e6)

        x = np.arange(len(years))
        w = 0.36
        bars_c = ax.bar(x - w/2, eva_classical, w, color="#7B7D7D",
                          label="Classical single-WACC EVA",
                          edgecolor="black", linewidth=0.4)
        bars_p = ax.bar(x + w/2, eva_two_phase, w, color=color,
                          label="Two-phase EVA",
                          edgecolor="black", linewidth=0.4)
        for bar, val in list(zip(bars_c, eva_classical)) + list(zip(bars_p, eva_two_phase)):
            offset = 0.1 if val >= 0 else -0.1
            ax.text(bar.get_x() + bar.get_width() / 2,
                    val + offset,
                    f"${val:.1f}M", ha="center", fontsize=8,
                    va="bottom" if val >= 0 else "top")
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels([str(y) for y in years])
        ax.set_xlabel("Year")
        ax.set_ylabel("EVA (USD millions)")
        ax.set_title(label, fontsize=10)
        ax.grid(True, axis="y", linestyle=":", alpha=0.5)
        ax.set_axisbelow(True)
        ax.legend(fontsize=8, loc="upper left", framealpha=0.92)

    fig.suptitle("Appendix B.2 — EVA trajectory: classical vs two-phase (live)",
                 fontsize=11, y=1.02)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Section 6.5 / Appendix B.2.6 — Dual-channel figures (Sprint 5)
# ---------------------------------------------------------------------------

# Two case-firm colours used across Appendix A/B figures.
NEUROCERTIFY_COLOR = "#0B6E4F"     # deep-tech green
DATAFLOW_COLOR = "#C44536"         # commoditizing-tech red
PHASE_2_COLOR = "#C44536"          # Phase 2 (second valley) shading
PHASE_1_COLOR = "#888888"          # Phase 1 (growth) shading
PHASE_3_COLOR = "#0B6E4F"          # Phase 3 (terminal) shading


def figure_b3_dualchannel_geometry(*,
                                    formal_labels: bool = True,
                                    figsize: Tuple[float, float] = (10.5, 6.0),
                                    ) -> plt.Figure:
    """Figure 6-bis / B.3 — Conceptual dual-channel geometry.

    Two curves on a shared time axis:
      * Upper curve: projected revenue — rising, false-recovery peak,
        second-valley dip, partial recovery to a NEW lower steady
        state (per the unified-lambda correction in
        docs/dual_channel_correction.md).
      * Lower curve: cost of capital (WACC) — flat in Phase 1,
        Phase-2 rise, partial settle in Phase 3.

    The Phase-2 window is shaded across both curves. The figure is
    purely conceptual — no axis values — and is intended to be
    cross-referenced from §6.5 (where the second valley is first
    introduced) and from Appendix B.2.6 (the formal treatment).

    Parameters
    ----------
    formal_labels : bool
        When True (default), renders the formal B.3 labels (numerator
        and denominator of the DCF, with the compounding window
        bracket). When False, renders the §6.5 cross-reference
        version with only the prose annotations.
    """
    fig, (ax_rev, ax_wacc) = plt.subplots(2, 1, figsize=figsize, sharex=True)

    # Shared horizontal axis: "time" in 50-step grid covering the
    # three lifecycle phases. Phase boundaries at 35% and 70% of the
    # x-axis put Phase 2 in the visual middle.
    t = np.linspace(0, 1, 200)
    phase1_end = 0.35
    phase2_end = 0.70

    # --- Upper curve: projected revenue ---
    # Schematic, monotonic within each phase:
    #   Phase 1: smooth rise 0.40 → 1.10  (false-recovery peak at end of Phase 1)
    #   Phase 2: smooth dip   1.10 → 0.65 (the second valley, half cosine)
    #   Phase 3: partial recovery 0.65 → 0.85 (asymptote to a NEW lower
    #            steady state, BELOW the false-recovery peak — captures
    #            the permanent margin compression of lambda_phase3 < 1)
    u_p1 = np.clip(t / phase1_end, 0, 1)
    u_p2 = np.clip((t - phase1_end) / (phase2_end - phase1_end), 0, 1)
    u_p3 = np.clip((t - phase2_end) / (1.0 - phase2_end), 0, 1)
    rev = np.where(
        t < phase1_end,
        0.40 + 0.70 * u_p1 ** 1.3,
        np.where(
            t < phase2_end,
            # Half cosine: smoothly monotonic decline 1.10 → 0.65
            1.10 - 0.45 * (1.0 - np.cos(np.pi * u_p2)) / 2.0,
            # Exponential approach to new lower steady state 0.85
            0.65 + 0.20 * (1.0 - np.exp(-3.5 * u_p3)),
        ),
    )
    ax_rev.plot(t, rev, color=DATAFLOW_COLOR, linewidth=2.5,
                label="Projected revenue (numerator of DCF)")
    ax_rev.fill_between(t, rev.min() * 0.95, rev, alpha=0.10,
                        color=DATAFLOW_COLOR)
    ax_rev.set_ylabel("Revenue (schematic)", fontsize=10)
    ax_rev.set_yticks([])
    ax_rev.grid(False)

    # --- Lower curve: cost of capital (WACC) ---
    # Flat-low in Phase 1, monotonic rise in Phase 2 (half cosine),
    # partial settle in Phase 3 (residual scarring above Phase-1 level).
    #   Phase 1: 0.100  (flat)
    #   Phase 2: 0.100 → 0.140  (smooth rise via half cosine)
    #   Phase 3: 0.140 → 0.115  (asymptotic settle, ABOVE 0.100)
    wacc = np.where(
        t < phase1_end,
        0.100 * np.ones_like(t),
        np.where(
            t < phase2_end,
            0.100 + 0.040 * (1.0 - np.cos(np.pi * u_p2)) / 2.0,
            0.115 + 0.025 * np.exp(-3.5 * u_p3),
        ),
    )
    ax_wacc.plot(t, wacc, color="#2C5282", linewidth=2.5,
                 label="Cost of capital WACC (denominator of DCF)")
    ax_wacc.fill_between(t, wacc, wacc.max() * 1.05, alpha=0.10,
                         color="#2C5282")
    ax_wacc.set_ylabel("WACC (schematic)", fontsize=10)
    ax_wacc.set_yticks([])
    ax_wacc.set_xlabel("Time (firm lifecycle, schematic)", fontsize=10)
    ax_wacc.set_xticks([])
    ax_wacc.grid(False)

    # --- Phase shading on both panels ---
    for ax in (ax_rev, ax_wacc):
        ax.axvspan(0, phase1_end, alpha=0.10, color=PHASE_1_COLOR)
        ax.axvspan(phase1_end, phase2_end, alpha=0.20, color=PHASE_2_COLOR)
        ax.axvspan(phase2_end, 1.0, alpha=0.10, color=PHASE_3_COLOR)

    # --- Phase labels at top of upper panel ---
    y_top = rev.max() * 1.05
    ax_rev.set_ylim(rev.min() * 0.85, y_top * 1.08)
    label_y = y_top * 0.98
    ax_rev.text(phase1_end / 2, label_y, "Phase 1\n(growth)",
                ha="center", fontsize=9, color="#555", style="italic", va="top")
    ax_rev.text((phase1_end + phase2_end) / 2, label_y, "Phase 2\n(2nd valley)",
                ha="center", fontsize=9, color="#8B0000", style="italic", va="top")
    ax_rev.text((phase2_end + 1) / 2, label_y, "Phase 3\n(terminal)",
                ha="center", fontsize=9, color="#0B6E4F", style="italic", va="top")

    # --- Channel annotations ---
    valley_mid = (phase1_end + phase2_end) / 2
    valley_rev_y = rev[np.argmin(np.abs(t - valley_mid))]
    valley_wacc_y = wacc[np.argmin(np.abs(t - valley_mid))]

    # Upper: "numerator channel — revenue compressed"
    # Anchor LEFT of the trough, well below the bracket.
    ax_rev.annotate(
        "Numerator channel:\nrevenue compressed by λ_2V",
        xy=(valley_mid - 0.02, valley_rev_y),
        xytext=(phase1_end - 0.02, valley_rev_y - 0.05),
        fontsize=9, color="#8B0000", ha="right",
        arrowprops=dict(arrowstyle="->", color="#8B0000", lw=1.2),
    )
    # Lower: "denominator channel — WACC rises (β jump)"
    # Anchor to the right of the WACC peak, above the curve.
    peak_t = phase2_end - (phase2_end - phase1_end) * 0.10
    peak_wacc_y = wacc[np.argmin(np.abs(t - peak_t))]
    ax_wacc.annotate(
        "Denominator channel:\nWACC rises (β jump, Eq B.6)",
        xy=(peak_t, peak_wacc_y),
        xytext=(phase2_end + 0.08, peak_wacc_y + 0.010),
        fontsize=9, color="#1F365B", ha="left",
        arrowprops=dict(arrowstyle="->", color="#1F365B", lw=1.2),
    )

    # --- Bracket showing both channels act in the same window ---
    # Put the bracket near the BOTTOM of the upper panel so it does not
    # collide with the trough or with the numerator-channel annotation.
    y_lim_lo, y_lim_hi = ax_rev.get_ylim()
    bracket_y = y_lim_lo + (y_lim_hi - y_lim_lo) * 0.12
    ax_rev.annotate(
        "", xy=(phase1_end, bracket_y),
        xytext=(phase2_end, bracket_y),
        arrowprops=dict(arrowstyle="<->", color="#444", lw=1.3,
                        shrinkA=0, shrinkB=0),
    )
    ax_rev.text((phase1_end + phase2_end) / 2,
                bracket_y - (y_lim_hi - y_lim_lo) * 0.04,
                "Both channels act in the same window",
                ha="center", fontsize=8.5, color="#444", style="italic")

    # --- Formal B.3 labels (DCF compounding window) ---
    if formal_labels:
        # Bottom-right of upper panel — out of the way of phase labels
        ax_rev.text(0.98, 0.04,
                    "Numerator: FCF(t) · λ_2V(φ(t))  (Eq B.14)",
                    fontsize=8.5, color="#444", style="italic",
                    ha="right", va="bottom",
                    transform=ax_rev.transAxes)
        # Bottom-right of lower panel
        ax_wacc.text(0.98, 0.04,
                     "Denominator: ∏ (1 + WACC(s))  (Eq B.10)",
                     fontsize=8.5, color="#444", style="italic",
                     ha="right", va="bottom",
                     transform=ax_wacc.transAxes)

    title = ("Appendix B.2.6 — Dual-channel geometry"
             if formal_labels
             else "Section 6.5 — Second valley, dual-channel intuition")
    fig.suptitle(title, fontsize=11, y=0.995)
    fig.tight_layout()
    return fig


def figure_b4_risk_partition_and_corrected_fcf(*,
        firms: Dict[str, Dict],
        figsize: Tuple[float, float] = (12.0, 8.0),
        ) -> plt.Figure:
    """Figure B.4 — Risk partition + corrected cash flow (two panels).

    Upper panel: stacked bars per firm decomposing the second-valley
    Layer-4 risk contribution ``π_2V`` into ``π_2V_sys`` (systematic,
    already carried by the Phase-2 beta jump in Eq B.3) and
    ``π_2V_idio`` (idiosyncratic, carried by the firm-specific premium
    with ``alpha_4_adj`` per Eq B.13). In percentage points.

    Lower panel: per-firm projected free cash flow before (``FCF_proj``)
    and after (``FCF_2V = FCF_proj * λ_2V``) the unified-lambda
    revenue-retreat factor, year by year. Phase 2 window shaded.

    Parameters
    ----------
    firms : dict
        Maps firm slug → dict with keys:
          ``label`` (str), ``color`` (str hex),
          ``layer4_share`` (float), ``ai_substitution_potential`` (float),
          ``alpha_4`` (float), ``alpha_4_sys`` (float),
          ``amp_base`` (float),
          ``fcf_proj`` (list[float], USD), ``lambda_vector`` (list[float]),
          ``phase_boundaries`` (tuple[int, int]) — (phase_1_end_year,
          phase_2_end_year).
    """
    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=figsize,
                                          gridspec_kw={"height_ratios": [1, 1.3]})

    # --- Upper panel: π_2V_sys vs π_2V_idio (stacked bars per firm) ---
    firm_slugs = list(firms.keys())
    x = np.arange(len(firm_slugs))
    bar_width = 0.45

    sys_vals = []
    idio_vals = []
    totals = []
    for slug in firm_slugs:
        f = firms[slug]
        amp = f["amp_base"] + f["ai_substitution_potential"]
        # π_2V_sys: systematic share, carried by the beta jump.
        pi_sys = f["alpha_4_sys"] * f["layer4_share"] * amp * 100.0  # pp
        # π_2V_idio: idiosyncratic, in the firm-specific premium.
        alpha_adj = max(0.0, f["alpha_4"] - f["alpha_4_sys"])
        pi_idio = alpha_adj * f["layer4_share"] * amp * 100.0        # pp
        sys_vals.append(pi_sys)
        idio_vals.append(pi_idio)
        totals.append(pi_sys + pi_idio)

    bars_sys = ax_top.bar(x, sys_vals, bar_width,
                           color="#7B7D7D", label="π_2V_sys (systematic — carried by β jump, Eq B.12)",
                           edgecolor="black", linewidth=0.5)
    bars_idio = ax_top.bar(x, idio_vals, bar_width, bottom=sys_vals,
                            color=[firms[s]["color"] for s in firm_slugs],
                            label="π_2V_idio (idiosyncratic — α_4_adj, Eq B.13)",
                            edgecolor="black", linewidth=0.5)

    for i, (slug, total) in enumerate(zip(firm_slugs, totals)):
        ax_top.text(i, sys_vals[i] / 2, f"{sys_vals[i]:.2f}pp",
                    ha="center", va="center", fontsize=8.5, color="white",
                    fontweight="bold")
        ax_top.text(i, sys_vals[i] + idio_vals[i] / 2, f"{idio_vals[i]:.2f}pp",
                    ha="center", va="center", fontsize=8.5, color="white",
                    fontweight="bold")
        ax_top.text(i, total + 0.15, f"π_2V = {total:.2f}pp",
                    ha="center", fontsize=9, fontweight="bold")

    ax_top.set_xticks(x)
    ax_top.set_xticklabels([firms[s]["label"] for s in firm_slugs])
    ax_top.set_ylabel("Layer-4 risk contribution (percentage points)")
    ax_top.set_title("Upper panel — Risk partition (Eq B.12–B.13): "
                     "systematic vs idiosyncratic share of the second-valley risk",
                     fontsize=10, pad=8)
    ax_top.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax_top.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax_top.set_axisbelow(True)
    ax_top.set_ylim(0, max(totals) * 1.20)

    # --- Lower panel: FCF before / after lambda ---
    # Per firm, side-by-side grouped bars for each year.
    n_firms = len(firm_slugs)
    n_years = len(firms[firm_slugs[0]]["fcf_proj"])
    group_width = 0.9
    bar_w = group_width / (2 * n_firms)

    # Phase shading determined from the first firm's boundaries (assume same).
    p1_end, p2_end = firms[firm_slugs[0]]["phase_boundaries"]
    for year in range(1, n_years + 1):
        if year <= p1_end:
            color = PHASE_1_COLOR
            alpha = 0.06
        elif year <= p2_end:
            color = PHASE_2_COLOR
            alpha = 0.15
        else:
            color = PHASE_3_COLOR
            alpha = 0.06
        ax_bot.axvspan(year - 0.5, year + 0.5, color=color, alpha=alpha, zorder=0)

    for fi, slug in enumerate(firm_slugs):
        f = firms[slug]
        fcf_proj = [c / 1e6 for c in f["fcf_proj"]]
        fcf_2v = [c * l / 1e6 for c, l in zip(f["fcf_proj"], f["lambda_vector"])]
        years = np.arange(1, n_years + 1)
        offset_proj = -group_width / 2 + (2 * fi) * bar_w + bar_w / 2
        offset_2v = -group_width / 2 + (2 * fi + 1) * bar_w + bar_w / 2
        ax_bot.bar(years + offset_proj, fcf_proj, bar_w,
                   color="#BBBBBB", edgecolor="black", linewidth=0.4,
                   label=f"{f['label']} — FCF_proj" if fi == 0 else None,
                   alpha=0.75)
        ax_bot.bar(years + offset_2v, fcf_2v, bar_w,
                   color=f["color"], edgecolor="black", linewidth=0.4,
                   label=f"{f['label']} — FCF_2V (× λ_2V)",
                   alpha=0.9)

    ax_bot.axhline(0, color="black", linewidth=0.7)
    ax_bot.set_xticks(np.arange(1, n_years + 1))
    ax_bot.set_xticklabels([f"Y{y}" for y in range(1, n_years + 1)])
    ax_bot.set_xlabel("Year")
    ax_bot.set_ylabel("Free cash flow (USD millions)")
    ax_bot.set_title("Lower panel — Eq B.14: corrected free cash flow "
                     "FCF_2V(t) = FCF_proj(t) · λ_2V(φ(t))",
                     fontsize=10, pad=8)
    ax_bot.legend(loc="upper left", fontsize=8.5, framealpha=0.92, ncol=2)
    ax_bot.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax_bot.set_axisbelow(True)

    # Phase labels at top of lower panel
    y_top_bot = ax_bot.get_ylim()[1]
    ax_bot.text((p1_end + 1) / 2, y_top_bot * 0.93, "Phase 1",
                ha="center", fontsize=8.5, color="#555", style="italic")
    ax_bot.text((p1_end + 1 + p2_end) / 2, y_top_bot * 0.93, "Phase 2",
                ha="center", fontsize=8.5, color="#8B0000", style="italic")
    ax_bot.text((p2_end + n_years + 1) / 2, y_top_bot * 0.93, "Phase 3",
                ha="center", fontsize=8.5, color="#0B6E4F", style="italic")

    fig.suptitle("Appendix B.2.6 — Figure B.4: Risk partition and corrected cash flow",
                 fontsize=11, y=0.995)
    fig.tight_layout()
    return fig


def figure_b5_four_path_reconciliation(*,
        firms: Dict[str, Dict],
        funding_stage_lines: Dict[str, float],
        figsize: Tuple[float, float] = (12.0, 6.5),
        ) -> plt.Figure:
    """Figure B.5 — Four-path valuation reconciliation (the most important
    figure of subsection B.2.6).

    For each case firm, four bars side by side: ``V0_classical``,
    ``V0_layered_A``, ``V0_twophase_B``, ``V0_dualchannel``. P10–P90
    Monte Carlo error bars on every bar. Dotted horizontal reference
    lines for the Carta funding-stage medians.

    The caption notes that the dual-channel bar is the recommended
    figure for practitioners; the other three are diagnostic
    comparators.

    Parameters
    ----------
    firms : dict
        Maps firm slug → dict with keys:
          ``label`` (str), ``color`` (str hex),
          ``v0_classical``, ``v0_layered_A``,
          ``v0_twophase_B``, ``v0_dualchannel`` (floats in USD),
          ``bands`` (dict path_key → {p10, p50, p90}).
    funding_stage_lines : dict
        Maps short label → median pre-money valuation in USD.
        Typically ``{"seed": 16e6, "series_a": 49.3e6, "series_b": 118.9e6}``.
    """
    firm_slugs = list(firms.keys())
    n_firms = len(firm_slugs)
    fig, axes = plt.subplots(1, n_firms, figsize=figsize, sharey=False)
    if n_firms == 1:
        axes = [axes]

    path_keys = ("v0_classical", "v0_layered_A",
                 "v0_twophase_B", "v0_dualchannel")
    path_labels = ("Classical\nDamodaran",
                   "Appendix A\nLayered DCF",
                   "Appendix B\nTwo-phase",
                   "B.2.6\nDual-channel\n(recommended)")
    path_colors = ("#7B7D7D", "#888888", "#A0A0A0", None)  # last filled per firm

    for ax, slug in zip(axes, firm_slugs):
        f = firms[slug]
        x = np.arange(len(path_keys))
        values = [f[k] / 1e6 for k in path_keys]

        # Error bars from MC bands when available.
        yerr_low: List[float] = []
        yerr_high: List[float] = []
        for k in path_keys:
            bands = f.get("bands", {}).get(k, {})
            if bands:
                p10 = bands["p10"] / 1e6
                p50 = bands["p50"] / 1e6
                p90 = bands["p90"] / 1e6
                # Centre the bar on the point estimate (values[i]) and
                # express error bars as distance from THAT estimate.
                # We deliberately use the point estimate, not the MC
                # median, as the bar height (Damodaran convention).
                pt = values[path_keys.index(k)]
                yerr_low.append(max(0.0, pt - p10))
                yerr_high.append(max(0.0, p90 - pt))
            else:
                yerr_low.append(0.0)
                yerr_high.append(0.0)

        colors = list(path_colors[:-1]) + [f["color"]]
        bars = ax.bar(x, values, 0.6, color=colors,
                      edgecolor="black", linewidth=0.5,
                      yerr=[yerr_low, yerr_high], capsize=6,
                      ecolor="#333", error_kw={"linewidth": 1.2})

        for bar, v in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    v + max(values) * 0.04,
                    f"${v:.1f}M",
                    ha="center", fontsize=9.5, fontweight="bold")

        # Set the y limit before drawing reference lines, so we can
        # filter out lines that would fall outside the visible band
        # (this avoids the annotation-overflow bug we observed when
        # Series B = $119M was rendered on the DataFlow Pro subplot
        # whose y_max sits near $95M).
        ax.set_xticks(x)
        ax.set_xticklabels(path_labels, fontsize=9)
        ax.set_ylabel("Enterprise Value (USD millions)")
        ax.set_title(f"{f['label']}", fontsize=11, pad=8)
        ax.grid(True, axis="y", linestyle=":", alpha=0.4)
        ax.set_axisbelow(True)
        ax.set_xlim(-0.5, len(path_keys) - 0.5 + 0.55)
        # y_lim needs to accommodate point estimates + their P90 error
        # bars + the funding-stage lines that fall inside the
        # visible range.
        y_max_from_bars = max(v + e for v, e in zip(values, yerr_high))
        y_max = max(y_max_from_bars, max(values)) * 1.18
        ax.set_ylim(0, y_max)

        # Funding-stage reference lines + right-edge annotations,
        # filtered to only those that lie within the visible y-band.
        for stage_label, stage_amt in funding_stage_lines.items():
            stage_m = stage_amt / 1e6
            if stage_m < 0 or stage_m > y_max:
                continue
            ax.axhline(stage_m, linestyle=":", color="#888", alpha=0.6,
                       linewidth=1.0)
            # Anchor the annotation at the right edge of the plot
            # using axis-fraction coords so it never spills into the
            # neighbouring subplot or the suptitle area.
            ax.text(0.995, stage_m, f"  {stage_label.replace('_', ' ').title()} "
                                     f"(~${stage_m:.0f}M)",
                    fontsize=8, color="#666", va="center", ha="right",
                    transform=ax.get_yaxis_transform(),
                    bbox=dict(boxstyle="round,pad=0.15",
                              facecolor="white", edgecolor="none",
                              alpha=0.75))

    fig.suptitle("Appendix B.2.6 — Figure B.5: Four-path valuation reconciliation\n"
                 "Dual-channel bar is the recommended figure for practitioners; "
                 "the others are diagnostic comparators",
                 fontsize=11, y=1.00)
    fig.tight_layout()
    return fig
