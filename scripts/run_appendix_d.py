"""Generate figures for Appendix D (streaming case + cross-bloc fiscal flows).

Outputs:
    figures/fig24_streaming_price_decomp.png   — Figure D.2 in the paper
    figures/fig25_streaming_cross_jurisdictional.png — Figure D.3
    figures/fig26_streaming_capital_trajectory.png  — Figure D.4
    figures/fig27_streaming_phase_risk.png     — Figure D.5
    figures/fig28_streaming_dilution_multiple.png — Figure D.6
    figures/fig29_streaming_payoff_matrix.png  — Figure D.7
    figures/fig30_fiscal_blocs.png             — Figure D.8
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from src import config
from src.streaming_case import (
    incumbent_price_decomposition,
    run_three_scenarios,
    cross_jurisdictional_price,
)
from src.fiscal_blocs import project_all_blocs

FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


COST_COMPONENT_COLORS = {
    "content_licensing": "#2C5282",
    "engineering": "#E07B39",
    "support": "#C44536",
    "cloud": "#8E44AD",
    "marketing": "#F5C242",
    "g_and_a": "#7B7D7D",
    "margin": "#0B6E4F",
}

COST_COMPONENT_LABELS = {
    "content_licensing": "Content licensing & production",
    "engineering": "Engineering & technology",
    "support": "Customer support",
    "cloud": "Cloud & CDN infrastructure",
    "marketing": "Marketing",
    "g_and_a": "G&A",
    "margin": "Operating margin",
}


def make_fig_d2_price_decomposition():
    """Figure D.2: incumbent vs 3-scenario entrant price decomposition (stacked bars)."""
    results = run_three_scenarios()
    incumbent = results[0].incumbent  # all results share the same incumbent

    fig, ax = plt.subplots(figsize=(11, 7))

    labels = ["Incumbent\n(legacy)"] + [
        f"Entrant\n({r.scenario_label})\n{int(r.substitution_pct*100)}% sub."
        for r in results
    ]
    x = np.arange(len(labels))
    width = 0.55

    # Order: content (bottom) → engineering → support → cloud → marketing → G&A → margin
    component_order = [
        "content_licensing", "engineering", "support",
        "cloud", "marketing", "g_and_a", "margin",
    ]

    decompositions = [incumbent.to_dict()] + [r.entrant.to_dict() for r in results]
    bottom = np.zeros(len(labels))
    for comp in component_order:
        vals = np.array([d[comp] for d in decompositions])
        bars = ax.bar(x, vals, width, bottom=bottom,
                      color=COST_COMPONENT_COLORS[comp],
                      label=COST_COMPONENT_LABELS[comp],
                      edgecolor="white", linewidth=0.4)
        for i, (b, v) in enumerate(zip(bars, vals)):
            if v > 0.30:
                ax.text(b.get_x() + b.get_width()/2, bottom[i] + v/2,
                        f"${v:.2f}", ha="center", va="center",
                        fontsize=8.5, color="white" if comp != "marketing"
                        and comp != "margin" else "black",
                        fontweight="bold")
        bottom += vals

    # Total prices above each bar
    for i, total in enumerate(bottom):
        if i == 0:
            ax.text(i, total + 0.3, f"${total:.2f}", ha="center",
                    fontsize=11, fontweight="bold", color="#2C5282")
        else:
            reduction = (incumbent.total - total) / incumbent.total
            ax.text(i, total + 0.3, f"${total:.2f}", ha="center",
                    fontsize=11, fontweight="bold", color="#C44536")
            ax.text(i, total + 0.95, f"−{reduction*100:.0f}%", ha="center",
                    fontsize=10, color="#C44536",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFE5E5",
                              edgecolor="#C44536", alpha=0.85))

    # Content-licensing floor line
    ax.axhline(incumbent.content_licensing, linestyle="--", color="#2C5282",
               linewidth=1.2, alpha=0.7)
    ax.text(0.02, incumbent.content_licensing - 0.4,
            "Content licensing floor (Layer 6 untouchable by AI)",
            fontsize=8, color="#2C5282", style="italic")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Monthly subscription price (USD)")
    ax.set_ylim(0, 20)
    ax.set_title("Decomposition of consumer price: incumbent vs IA-native entrant\n"
                 "(United States benchmark, three substitution scenarios)",
                 fontsize=11, pad=10)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncol=4, fontsize=8.5, framealpha=0.92)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out = FIG_DIR / "fig24_streaming_price_decomp.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_d3_cross_jurisdictional():
    """Figure D.3: cross-jurisdictional price competition under 3 scenarios."""
    incumbent = incumbent_price_decomposition().total

    sc = config.load_parameters()["streaming_case"]
    scenarios = [
        ("Conservative\n(40% headcount reduction)", float(sc["substitution_scenarios"]["conservative_pct"])),
        ("Moderate\n(60% headcount reduction)", float(sc["substitution_scenarios"]["moderate_pct"])),
        ("Aggressive\n(78% headcount reduction)", float(sc["substitution_scenarios"]["aggressive_pct"])),
    ]
    pairings = [
        ("Brazil\n→ Brazil", "brazil", "brazil", False),
        ("Brazil\n→ US*", "brazil", "united_states", True),
        ("France\n→ France", "france", "france", False),
        ("France\n→ US*", "france", "united_states", True),
        ("US\n→ US", "united_states", "united_states", False),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), sharey=True)

    for ax, (sc_label, sub) in zip(axes, scenarios):
        x = np.arange(len(pairings))
        width = 0.36

        incumbent_vals = [incumbent] * len(pairings)
        entrant_vals = [
            cross_jurisdictional_price(target, acquirer, sub)
            for _, target, acquirer, _ in pairings
        ]

        bars1 = ax.bar(x - width/2, incumbent_vals, width, color="#2C5282",
                       label="Incumbent (legacy)", edgecolor="black", linewidth=0.4)
        bars2 = ax.bar(x + width/2, entrant_vals, width, color="#0B6E4F",
                       label="Entrant (IA-native)", edgecolor="black", linewidth=0.4)

        for b, v in zip(bars1, incumbent_vals):
            ax.text(b.get_x() + b.get_width()/2, v + 0.10, f"${v:.2f}",
                    ha="center", fontsize=8.5)
        for b, v, (_, _, _, is_cross) in zip(bars2, entrant_vals, pairings):
            ax.text(b.get_x() + b.get_width()/2, v + 0.10, f"${v:.2f}",
                    ha="center", fontsize=8.5)
            reduction = (incumbent - v) / incumbent * 100
            ax.text(b.get_x() + b.get_width()/2, v / 2,
                    f"−{reduction:.0f}%", ha="center", fontsize=8,
                    color="white" if reduction > 5 else "black", fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels([p[0] for p in pairings], fontsize=8)
        # Shade cross-bloc pairings
        for i, (_, _, _, is_cross) in enumerate(pairings):
            if is_cross:
                ax.axvspan(i - 0.5, i + 0.5, alpha=0.10, color="grey", zorder=0)

        ax.set_title(sc_label, fontsize=10)
        ax.set_ylim(0, 17.5)
        ax.grid(True, axis="y", linestyle=":", alpha=0.4)
        ax.set_axisbelow(True)
        if ax is axes[0]:
            ax.set_ylabel("Monthly subscription price (USD)")
            ax.legend(loc="lower left", fontsize=8, framealpha=0.92)
        ax.text(0.5, -0.18, "* shaded = cross-bloc attack",
                transform=ax.transAxes, ha="center", fontsize=8,
                color="#C44536", style="italic")

    plt.suptitle("Cross-jurisdictional price competition under three substitution scenarios",
                 fontsize=12, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = FIG_DIR / "fig25_streaming_cross_jurisdictional.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_d4_capital_trajectory():
    """Figure D.4: capital trajectory legacy vs AI-native through funding stages."""
    fs = config.load_parameters()["funding_stages_carta"]
    stages = fs["stages"]
    stage_order = ["pre_seed", "seed", "series_a", "series_b", "series_c"]
    reduction = float(fs["ai_native_round_reduction"])

    legacy_cumulative = []
    ai_native_cumulative = []
    legacy_running = 0
    ai_running = 0
    for s in stage_order:
        legacy_running += float(stages[s]["round_size_usd"])
        ai_running += float(stages[s]["round_size_usd"]) * (1 - reduction)
        legacy_cumulative.append(legacy_running / 1e6)
        ai_native_cumulative.append(ai_running / 1e6)
    # Maturity = same as Series C
    stage_labels = ["Pre-Seed", "Seed", "Series A", "Series B", "Series C", "Maturity"]
    legacy_cumulative.append(legacy_running / 1e6)
    ai_native_cumulative.append(ai_running / 1e6)

    headcount_legacy = ["3 eng", "10 eng", "35 eng", "120 eng", "300 eng", "3500 eng"]
    headcount_ai = ["0 sup", "2 sup", "8 sup", "30 sup", "80 sup", "1200 sup"]

    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(stage_labels))
    width = 0.36

    bars1 = ax.bar(x - width/2, legacy_cumulative, width, color="#2C5282",
                   label="Legacy model (cumulative funding)",
                   edgecolor="black", linewidth=0.4)
    bars2 = ax.bar(x + width/2, ai_native_cumulative, width, color="#0B6E4F",
                   label="IA-native model (cumulative funding)",
                   edgecolor="black", linewidth=0.4)

    for b, v in zip(bars1, legacy_cumulative):
        ax.text(b.get_x() + b.get_width()/2, v + 3, f"${v:.0f}M",
                ha="center", fontsize=9, color="#2C5282", fontweight="bold")
    for b, v in zip(bars2, ai_native_cumulative):
        ax.text(b.get_x() + b.get_width()/2, v + 3, f"${v:.0f}M",
                ha="center", fontsize=9, color="#0B6E4F", fontweight="bold")

    # Headcount annotations below x-axis
    for i, (h_l, h_a) in enumerate(zip(headcount_legacy, headcount_ai)):
        ax.text(i, -15, f"{h_l}\n{h_a}", ha="center", fontsize=7.5,
                color="grey", style="italic")

    # Shade the two valleys
    ax.axvspan(1.5, 2.5, alpha=0.15, color="#C44536")
    ax.text(2, ax.get_ylim()[1] * 0.85, "1st Valley\n(TRL 4)\nproduct-market\nfit risk",
            ha="center", fontsize=8.5, color="#C44536",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="#C44536", alpha=0.9))
    ax.axvspan(2.5, 3.5, alpha=0.15, color="#7A1F1F")
    ax.text(3, ax.get_ylim()[1] * 0.85, "2nd Valley\n(TRL 6)\ndefensibility\nrisk",
            ha="center", fontsize=8.5, color="#7A1F1F",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="#7A1F1F", alpha=0.9))

    ax.set_xticks(x)
    ax.set_xticklabels(stage_labels)
    ax.set_ylabel("Cumulative funding raised (USD millions)")
    ax.set_title("Capital required by stage: legacy vs IA-native, with the two valleys "
                 "of TRL maturation",
                 fontsize=11, pad=10)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_ylim(-30, max(legacy_cumulative) * 1.15)

    plt.tight_layout()
    out = FIG_DIR / "fig26_streaming_capital_trajectory.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_d5_phase_risk():
    """Figure D.5: phase-conditional CAPM beta legacy vs AI-native."""
    stages = ["Pre-Seed", "Seed", "Series A", "Series B", "Series C", "Maturity"]
    legacy_beta = [3.5, 3.0, 2.2, 2.5, 1.6, 1.0]
    ai_native_beta = [3.2, 3.4, 1.9, 2.0, 1.4, 0.95]

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(stages))

    ax.plot(x, legacy_beta, marker="o", markersize=8, linewidth=2.4,
            color="#2C5282", label="Legacy model (CAPM β)")
    ax.plot(x, ai_native_beta, marker="s", markersize=8, linewidth=2.4,
            color="#0B6E4F", label="IA-native model (CAPM β)")

    # Annotations for AI-native deviations
    ax.annotate("IA-native risk lift:\nthird-party AI\nprovider dependency",
                xy=(1, ai_native_beta[1]), xytext=(0.5, 3.8),
                fontsize=8, color="#7A5C00", ha="center",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF5E5",
                          edgecolor="#F5C242", alpha=0.9))
    ax.annotate("IA-native risk dip:\nsmaller team,\nlower burn",
                xy=(2, ai_native_beta[2]), xytext=(2, 0.8),
                fontsize=8, color="#1F5040", ha="center",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#E5F5E5",
                          edgecolor="#0B6E4F", alpha=0.9))

    # Two valleys
    ax.axvspan(1.5, 2.5, alpha=0.10, color="#C44536")
    ax.text(2, 0.4, "1st Valley\n(TRL 4)", ha="center", fontsize=8,
            color="#7A1F1F", style="italic")
    ax.axvspan(2.5, 3.5, alpha=0.10, color="#7A1F1F")
    ax.text(3, 0.4, "2nd Valley\n(commoditization\n— DataFlow risk lift)",
            ha="center", fontsize=8, color="#7A1F1F", style="italic")

    ax.axhline(1.0, color="grey", linewidth=0.6, linestyle="--")
    ax.text(5.2, 1.05, "Market β = 1.0", fontsize=8, color="grey", style="italic")

    ax.set_xticks(x)
    ax.set_xticklabels(stages)
    ax.set_ylabel("CAPM β (firm-specific risk relative to market)")
    ax.set_ylim(0, 4.2)
    ax.set_title("Phase-conditional risk curve: legacy vs IA-native\n"
                 "(Appendix B framework applied to streaming case)",
                 fontsize=11, pad=10)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out = FIG_DIR / "fig27_streaming_phase_risk.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_d6_dilution_multiple():
    """Figure D.6: founder dilution + expected multiple by entry stage."""
    fs = config.load_parameters()["funding_stages_carta"]
    stages = ["Founding", "Pre-Seed", "Seed", "Series A", "Series B", "Series C"]
    legacy_dilution = float(fs["legacy_dilution_per_round"])
    ai_dilution = float(fs["ai_native_dilution_per_round"])

    legacy_retained = [1.0]
    ai_retained = [1.0]
    for _ in range(5):
        legacy_retained.append(legacy_retained[-1] * (1 - legacy_dilution))
        ai_retained.append(ai_retained[-1] * (1 - ai_dilution))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left panel: cumulative dilution
    ax = axes[0]
    x = np.arange(len(stages))
    ax.plot(x, [r * 100 for r in legacy_retained], marker="o", linewidth=2.2,
            color="#2C5282", label="Legacy model")
    ax.plot(x, [r * 100 for r in ai_retained], marker="s", linewidth=2.2,
            color="#0B6E4F", label="IA-native model")

    for i, (l, a) in enumerate(zip(legacy_retained, ai_retained)):
        ax.text(i, l * 100 - 4, f"{l*100:.0f}%", ha="center",
                fontsize=8.5, color="#2C5282")
        ax.text(i, a * 100 + 1, f"{a*100:.0f}%", ha="center",
                fontsize=8.5, color="#0B6E4F")

    # Gap annotation at Series C
    ai_extra_pct = (ai_retained[-1] - legacy_retained[-1]) * 100
    ax.annotate(f"+{ai_extra_pct:.0f} pp\nfounder\nretention",
                xy=(5, (ai_retained[-1] + legacy_retained[-1]) / 2 * 100),
                xytext=(4.5, 60), fontsize=9, color="#0B6E4F",
                ha="center", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#E5F5E5",
                          edgecolor="#0B6E4F", alpha=0.9),
                arrowprops=dict(arrowstyle="->", color="#0B6E4F"))

    ax.set_xticks(x)
    ax.set_xticklabels(stages, rotation=15, ha="right")
    ax.set_ylabel("Founder ownership remaining (%)")
    ax.set_title("Founder cumulative dilution\n"
                 "(stopping at each company's layered-EV stage placement)",
                 fontsize=10, pad=8)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_ylim(20, 105)

    # Right panel: expected multiple by entry stage
    ax = axes[1]
    em = fs["expected_multiple"]
    entry_stages = ["Pre-Seed", "Seed", "Series A"]
    nc_legacy = [em["neurocertify_legacy"][s.lower().replace(" ", "_").replace("-", "_")]
                 for s in ["pre_seed", "seed", "series_a"]]
    nc_ai = [em["neurocertify_ai_native"][s] for s in ["pre_seed", "seed", "series_a"]]
    df_legacy = [em["dataflow_legacy"]["pre_seed"], em["dataflow_legacy"]["seed"], 0]
    df_ai = [em["dataflow_ai_native"]["pre_seed"], em["dataflow_ai_native"]["seed"], 0]

    x = np.arange(len(entry_stages))
    width = 0.20

    bars1 = ax.bar(x - 1.5*width, nc_legacy, width, color="#2C5282",
                   label="NC, legacy", edgecolor="black", linewidth=0.3)
    bars2 = ax.bar(x - 0.5*width, nc_ai, width, color="#0B6E4F",
                   label="NC, IA-native", edgecolor="black", linewidth=0.3)
    bars3 = ax.bar(x + 0.5*width, df_legacy, width, color="#1F1F1F",
                   label="DF, legacy", edgecolor="black", linewidth=0.3)
    bars4 = ax.bar(x + 1.5*width, df_ai, width, color="#C44536",
                   label="DF, IA-native", edgecolor="black", linewidth=0.3)

    for bars, vals in [(bars1, nc_legacy), (bars2, nc_ai), (bars3, df_legacy), (bars4, df_ai)]:
        for b, v in zip(bars, vals):
            if v > 0:
                ax.text(b.get_x() + b.get_width()/2, v + 0.3, f"{v:.1f}x",
                        ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(entry_stages)
    ax.set_ylabel("Expected investor multiple (10-year horizon)")
    ax.set_title("Expected multiple by entry stage", fontsize=10, pad=8)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(max(nc_ai), max(df_ai)) * 1.2)

    plt.suptitle("Founder dilution and investor return: legacy vs IA-native",
                 fontsize=12, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = FIG_DIR / "fig28_streaming_dilution_multiple.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_d7_payoff_matrix():
    """Figure D.7: payoff matrix (price advantage × catalog parity)."""
    cells = [
        # Row order: low (top of price advantage axis), medium, high
        ["entrant\ndominates", "entrant\ndominates", "partial\ncapture"],
        ["entrant\ndominates", "partial\ncapture", "entrant\nirrelevant"],
        ["partial\ncapture", "entrant\nirrelevant", "entrant\nirrelevant"],
    ]
    # Flip rows so "high price advantage" is at TOP (matches paper Fig D.7)
    cell_colors = [
        ["#0B6E4F", "#0B6E4F", "#F5C242"],
        ["#0B6E4F", "#F5C242", "#F8C8DC"],
        ["#F5C242", "#F8C8DC", "#F8C8DC"],
    ]

    fig, ax = plt.subplots(figsize=(10, 8))

    for i, (row, color_row) in enumerate(zip(cells, cell_colors)):
        for j, (cell_text, color) in enumerate(zip(row, color_row)):
            rect = plt.Rectangle((j, 2 - i), 1, 1, facecolor=color,
                                  edgecolor="black", linewidth=0.6)
            ax.add_patch(rect)
            ax.text(j + 0.5, 2 - i + 0.5, cell_text, ha="center", va="center",
                    fontsize=12, fontweight="bold",
                    color="white" if color == "#0B6E4F" else "black")

    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3)
    ax.set_xticks([0.5, 1.5, 2.5])
    ax.set_xticklabels(["Full Layer-6 parity\n(comparable catalog\n& negotiated rights)",
                         "Partial parity\n(major titles\nbut not all)",
                         "No parity\n(weak catalog\nrelative to incumbent)"],
                        fontsize=9)
    ax.set_yticks([0.5, 1.5, 2.5])
    ax.set_yticklabels(["Low\n(<15% below)", "Medium\n(15-30% below)",
                         "High\n(>30% below\nincumbent)"], fontsize=9)
    ax.set_xlabel("Catalog parity (Layer-6 defensibility)", fontsize=10)
    ax.set_ylabel("Entrant's price advantage (Layer-4 IA economy)", fontsize=10)
    ax.set_title("Commoditization, defensibility, and the fragility window in the valleys",
                 fontsize=12, pad=10)

    # Legend
    legend_items = [
        mpatches.Patch(facecolor="#0B6E4F", edgecolor="black",
                       label="Entrant dominates: rapid market capture (months, not years)"),
        mpatches.Patch(facecolor="#F5C242", edgecolor="black",
                       label="Partial capture: meaningful share shift, both viable"),
        mpatches.Patch(facecolor="#F8C8DC", edgecolor="black",
                       label="Entrant irrelevant: incumbent retains market by Layer-6 lock-in"),
    ]
    ax.legend(handles=legend_items, loc="upper center", bbox_to_anchor=(0.5, -0.15),
              ncol=1, fontsize=9, framealpha=0.92)

    plt.tight_layout()
    out = FIG_DIR / "fig29_streaming_payoff_matrix.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_d8_fiscal_blocs():
    """Figure D.8: fiscal impact across three blocs (5-year decomposition + trajectory)."""
    blocs = project_all_blocs()
    bloc_order = ["brazil", "france", "united_states"]
    bloc_labels = ["Brazil", "France", "United States"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left panel: 5-year stacked decomposition
    ax = axes[0]
    x = np.arange(len(bloc_order))
    width = 0.55

    lost = np.array([blocs[j].lost_social_charges_usd_millions for j in bloc_order])
    export = np.array([blocs[j].ai_token_export_usd_millions for j in bloc_order])
    gain = np.array([blocs[j].compensating_tax_gain_usd_millions for j in bloc_order])

    bars_lost = ax.bar(x, lost, width, color="#F5C242",
                        label="Lost employer social charges",
                        edgecolor="black", linewidth=0.4)
    bars_export = ax.bar(x, export, width, bottom=lost, color="#8E44AD",
                          label="Fiscal exportation via AI tokens",
                          edgecolor="black", linewidth=0.4)
    bars_gain = ax.bar(x, -gain, width, color="#0B6E4F",
                       label="Compensating gain: corporate tax on higher margin",
                       edgecolor="black", linewidth=0.4)

    # Net impact labels above each bar (color = red for loss, green for gain)
    for i, j in enumerate(bloc_order):
        net = blocs[j].net_impact_usd_millions
        # Position above the highest stack
        top = max(lost[i] + max(0, export[i]), 0)
        color = "#C44536" if net > 0 else "#0B6E4F"
        sign = "+" if net > 0 else ""
        ax.text(i, top + 200,
                f"Net impact:\n${sign}{net:.0f}M",
                ha="center", fontsize=9, fontweight="bold", color=color,
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#FFE5E5" if net > 0 else "#E5F5E5",
                          edgecolor=color, alpha=0.9))

    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(bloc_labels)
    ax.set_ylabel("Cumulative impact over 5 years (USD millions)")
    ax.set_title("State revenue impact by jurisdiction\n"
                 "(moderate substitution scenario, 60% headcount reduction)",
                 fontsize=10, pad=8)
    ax.legend(loc="lower left", fontsize=8, framealpha=0.92,
              bbox_to_anchor=(0.0, -0.30))
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)

    # Right panel: cumulative trajectory by year
    ax = axes[1]
    years = list(range(0, 6))
    colors = {"brazil": "#0B6E4F", "france": "#2C5282", "united_states": "#C44536"}
    for j in bloc_order:
        cum = [0.0] + blocs[j].cumulative_by_year
        label = bloc_labels[bloc_order.index(j)]
        ax.plot(years, cum, marker="o", markersize=6, linewidth=2.2,
                color=colors[j], label=label)
        ax.annotate(f"${cum[-1]:+.0f}M", xy=(5, cum[-1]),
                    xytext=(5, 5), textcoords="offset points",
                    fontsize=9, fontweight="bold", color=colors[j])

    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xlabel("Years from IA-native transition")
    ax.set_ylabel("Cumulative net fiscal impact (USD millions)\n(positive = State loses; negative = State gains)")
    ax.set_title("5-year cumulative fiscal trajectory", fontsize=10, pad=8)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)

    plt.suptitle("Fiscal impact across three jurisdictional blocs: 5-year projection",
                 fontsize=12, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = FIG_DIR / "fig30_fiscal_blocs.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def main():
    print("\nGenerating Appendix D figures (streaming + fiscal blocs)\n" + "=" * 60)
    make_fig_d2_price_decomposition()
    make_fig_d3_cross_jurisdictional()
    make_fig_d4_capital_trajectory()
    make_fig_d5_phase_risk()
    make_fig_d6_dilution_multiple()
    make_fig_d7_payoff_matrix()
    make_fig_d8_fiscal_blocs()
    print("\nDone.")


if __name__ == "__main__":
    main()
