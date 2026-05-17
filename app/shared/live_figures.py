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
                            highlight_country: str = "united_states"
                            ) -> plt.Figure:
    """Bar chart of substitution NPV decomposition across three jurisdictions."""
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
                            ) -> plt.Figure:
    """Inversion premium as % of EV under each operating-cost basis."""
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

def fiscal_blocs_decomposition(blocs: Dict[str, "FiscalBlocResult"]) -> plt.Figure:
    """Stacked decomposition + net impact label per bloc."""
    countries = ["brazil", "france", "united_states"]

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
