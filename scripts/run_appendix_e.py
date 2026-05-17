"""Generate figures for Appendix E (Dynamic analysis of the two case companies).

Outputs:
    figures/fig31_appendix_e_migration.png  — Figure E.1 (NC + DF migration)
    figures/fig32_appendix_e_capital.png    — Figure E.2 (capital trajectory)
    figures/fig33_appendix_e_risk.png       — Figure E.3 (phase-conditional risk)
    figures/fig34_appendix_e_dilution.png   — Figure E.4 (dilution + multiple)
    figures/fig35_appendix_e_fragility.png  — Figure E.5 (fragility map)
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import matplotlib.pyplot as plt

from src import config
from src.migration_dynamics import case_study_migration
from src.fragility import case_studies_fragility, compute_fragility

FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def make_fig_e1_migration():
    """Figure E.1: combined NeuroCertify + DataFlow migration trajectories."""
    nc_br = case_study_migration("neurocertify", "brazil")
    nc_fr = case_study_migration("neurocertify", "france")
    df_cons = case_study_migration("dataflow_pro", "united_states", "conservative")
    df_mod = case_study_migration("dataflow_pro", "united_states", "moderate")
    df_agg = case_study_migration("dataflow_pro", "united_states", "aggressive")

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # Left: NeuroCertify (both arms + consolidated)
    ax = axes[0]
    consolidated_cum = [b + f for b, f in zip(nc_br.cumulative_cash_usd,
                                                nc_fr.cumulative_cash_usd)]
    ax.plot(nc_br.quarters, np.array(nc_br.cumulative_cash_usd) / 1e6,
            marker="o", markersize=4, linewidth=2, color="#0B6E4F",
            label="NC Brazil arm (15 eng)")
    ax.plot(nc_fr.quarters, np.array(nc_fr.cumulative_cash_usd) / 1e6,
            marker="s", markersize=4, linewidth=2, color="#2C5282",
            label="NC France arm (10 eng)")
    ax.plot(nc_br.quarters, np.array(consolidated_cum) / 1e6,
            marker="^", markersize=4, linewidth=2, color="#8E44AD",
            label="NC Consolidated (25 eng)")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.axvline(0, color="grey", linewidth=0.5, linestyle="--")
    ax.set_xlabel("Quarters from T0")
    ax.set_ylabel("Cumulative cash flow (USD millions)")
    ax.set_title("NeuroCertify migration (Layer 6 = 40%, AI sub = 0.50)\n"
                 "All trajectories net-negative within 5-year horizon",
                 fontsize=10, pad=8)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)

    # Right: DataFlow Pro (three scenarios)
    ax = axes[1]
    ax.plot(df_cons.quarters, np.array(df_cons.cumulative_cash_usd) / 1e6,
            marker="o", markersize=4, linewidth=2, color="#0B6E4F",
            label="DF Conservative (40% sub.)")
    ax.plot(df_mod.quarters, np.array(df_mod.cumulative_cash_usd) / 1e6,
            marker="s", markersize=4, linewidth=2, color="#F5C242",
            label="DF Moderate (60% sub.)")
    ax.plot(df_agg.quarters, np.array(df_agg.cumulative_cash_usd) / 1e6,
            marker="^", markersize=4, linewidth=2, color="#C44536",
            label="DF Aggressive (78% sub.)")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.axvline(0, color="grey", linewidth=0.5, linestyle="--")
    ax.set_xlabel("Quarters from T0")
    ax.set_ylabel("Cumulative cash flow (USD millions)")
    ax.set_title("DataFlow Pro migration (Layer 4 = 55%, AI sub = 0.75)\n"
                 "All three scenarios break even within 5 years",
                 fontsize=10, pad=8)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)

    plt.suptitle("Migration cash flow under the AI orchestrator framework: "
                 "two case companies",
                 fontsize=12, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = FIG_DIR / "fig31_appendix_e_migration.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_e2_capital():
    """Figure E.2: capital trajectory by stage, NC + DF, legacy vs IA-native."""
    fs = config.load_parameters()["funding_stages_carta"]
    cs = config.load_parameters()["case_studies_dynamic"]
    stages_full = ["pre_seed", "seed", "series_a", "series_b", "series_c"]
    stage_labels = ["Pre-Seed", "Seed", "Series A", "Series B", "Series C"]
    reduction = float(fs["ai_native_round_reduction"])

    # Compute cumulative by stage for both firms
    def cum_capital(firm_slug, ai_native=False):
        firm = cs[firm_slug]
        max_stage = firm["funding_stage"]
        max_idx = stages_full.index(max_stage)
        cum = []
        running = 0.0
        for i, s in enumerate(stages_full):
            if i > max_idx:
                cum.append(None)
                continue
            r = float(fs["stages"][s]["round_size_usd"])
            if ai_native:
                r *= (1 - reduction)
            running += r
            cum.append(running / 1e6)
        return cum

    nc_legacy = cum_capital("neurocertify", False)
    nc_ai = cum_capital("neurocertify", True)
    df_legacy = cum_capital("dataflow_pro", False)
    df_ai = cum_capital("dataflow_pro", True)

    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(stage_labels))
    width = 0.20

    def plot_bars(positions, values, color, label):
        for px, val in zip(positions, values):
            if val is not None:
                ax.bar(px, val, width, color=color, edgecolor="black",
                        linewidth=0.3)
                ax.text(px, val + 1, f"${val:.0f}M", ha="center", fontsize=8)
        ax.bar([], [], color=color, label=label)   # legend handle

    plot_bars(x - 1.5*width, nc_legacy, "#2C5282", "NeuroCertify, legacy")
    plot_bars(x - 0.5*width, nc_ai, "#7DB1D9", "NeuroCertify, IA-native")
    plot_bars(x + 0.5*width, df_legacy, "#7A1F1F", "DataFlow Pro, legacy")
    plot_bars(x + 1.5*width, df_ai, "#E07B39", "DataFlow Pro, IA-native")

    # Highlight 1st valley
    ax.axvspan(1.5, 2.5, alpha=0.10, color="#C44536")
    ax.text(2, ax.get_ylim()[1] * 0.65, "1st Valley\n(NC clears\nlayered max)",
            ha="center", fontsize=8.5, color="#7A1F1F",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="#7A1F1F", alpha=0.9))

    # Annotation: DataFlow stops at seed
    ax.text(1, ax.get_ylim()[1] * 0.50,
            "DataFlow Pro\nstops at Seed\n(layered EV $28.3M\n< Series A median)",
            ha="center", fontsize=8, color="#7A1F1F",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="#7A1F1F", alpha=0.9))

    ax.set_xticks(x)
    ax.set_xticklabels(stage_labels)
    ax.set_ylabel("Cumulative funding raised (USD millions)")
    ax.set_title("Capital trajectory through funding stages, NeuroCertify vs DataFlow Pro\n"
                 "(Funding stage placement per Appendix A.3; IA-native rounds 35% smaller per Section 7.5)",
                 fontsize=10, pad=8)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.92)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out = FIG_DIR / "fig32_appendix_e_capital.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_e3_risk():
    """Figure E.3: phase-conditional CAPM beta trajectories with valleys."""
    cs = config.load_parameters()["case_studies_dynamic"]
    stages = ["Pre-Seed", "Seed", "Series A", "Series B", "Series C", "Maturity"]
    x = np.arange(len(stages))

    nc_legacy = cs["neurocertify"]["beta_trajectory_legacy"]
    nc_ai = cs["neurocertify"]["beta_trajectory_ai_native"]
    df_legacy = cs["dataflow_pro"]["beta_trajectory_legacy"]
    df_ai = cs["dataflow_pro"]["beta_trajectory_ai_native"]

    fig, ax = plt.subplots(figsize=(13, 6))

    ax.plot(x, nc_legacy, marker="o", linewidth=2, color="#2C5282",
            label="NeuroCertify, legacy")
    ax.plot(x, nc_ai, marker="s", linewidth=2, color="#7DB1D9",
            label="NeuroCertify, IA-native", linestyle="--")
    ax.plot(x, df_legacy, marker="^", linewidth=2, color="#7A1F1F",
            label="DataFlow Pro, legacy")
    ax.plot(x, df_ai, marker="d", linewidth=2, color="#E07B39",
            label="DataFlow Pro, IA-native", linestyle="--")

    # Annotations
    ax.annotate("NC: Layer-6 dip\n(regulatory accred.)", xy=(2, nc_legacy[2]),
                xytext=(1.5, 0.6), fontsize=8, color="#2C5282",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8F0FF",
                          edgecolor="#2C5282", alpha=0.9))
    ax.annotate("DF: 2nd-valley risk lift\n(Layer-4 erosion)", xy=(3, df_legacy[3]),
                xytext=(2.5, 3.2), fontsize=8, color="#7A1F1F",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFE5E5",
                          edgecolor="#7A1F1F", alpha=0.9))

    # Two valleys
    ax.axvspan(1.5, 2.5, alpha=0.10, color="#C44536")
    ax.text(2, 0.30, "1st Valley\n(TRL 4)", ha="center", fontsize=8,
            color="#7A1F1F", style="italic")
    ax.axvspan(2.5, 3.5, alpha=0.10, color="#7A1F1F")
    ax.text(3, 0.30, "2nd Valley\n(commoditization)", ha="center", fontsize=8,
            color="#7A1F1F", style="italic")

    ax.axhline(1.0, color="grey", linewidth=0.6, linestyle="--")
    ax.text(5.2, 1.02, "Market β = 1.0", fontsize=8, color="grey", style="italic")

    ax.set_xticks(x)
    ax.set_xticklabels(stages)
    ax.set_ylabel("CAPM β (firm-specific risk relative to market)")
    ax.set_ylim(0, 4.0)
    ax.set_title("Phase-conditional risk curves: NeuroCertify vs DataFlow Pro\n"
                 "(Appendix B framework applied to two case companies)",
                 fontsize=11, pad=10)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out = FIG_DIR / "fig33_appendix_e_risk.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_e4_dilution():
    """Figure E.4: founder cumulative dilution + expected investor multiple."""
    fs = config.load_parameters()["funding_stages_carta"]
    cs = config.load_parameters()["case_studies_dynamic"]

    # Each firm has a different stopping stage
    stage_indices = {
        "neurocertify": 3,    # Founding, Pre-Seed, Seed, Series A
        "dataflow_pro": 2,    # Founding, Pre-Seed, Seed
    }
    stages_labels = ["Founding", "Pre-Seed", "Seed", "Series A"]
    legacy_dil = float(fs["legacy_dilution_per_round"])
    ai_dil = float(fs["ai_native_dilution_per_round"])

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left: dilution by stage for both firms
    ax = axes[0]
    for firm_slug, color_l, color_a, marker_l, marker_a, label_prefix in [
        ("neurocertify", "#2C5282", "#7DB1D9", "o", "s", "NeuroCertify"),
        ("dataflow_pro", "#7A1F1F", "#E07B39", "^", "d", "DataFlow Pro"),
    ]:
        max_idx = stage_indices[firm_slug]
        legacy = [1.0]
        ai = [1.0]
        for _ in range(max_idx):
            legacy.append(legacy[-1] * (1 - legacy_dil))
            ai.append(ai[-1] * (1 - ai_dil))
        x = list(range(max_idx + 1))
        ax.plot(x, [r * 100 for r in legacy], marker=marker_l, linewidth=2.2,
                color=color_l, label=f"{label_prefix}, legacy")
        ax.plot(x, [r * 100 for r in ai], marker=marker_a, linewidth=2.2,
                color=color_a, label=f"{label_prefix}, IA-native", linestyle="--")
        for i, (l, a) in enumerate(zip(legacy, ai)):
            ax.text(i, l * 100 - 4, f"{l*100:.0f}%", ha="center",
                    fontsize=8, color=color_l)
            ax.text(i, a * 100 + 1, f"{a*100:.0f}%", ha="center",
                    fontsize=8, color=color_a)

    ax.set_xticks(range(len(stages_labels)))
    ax.set_xticklabels(stages_labels)
    ax.set_ylabel("Founder ownership remaining (%)")
    ax.set_title("Founder cumulative dilution\n"
                 "(stopping at each company's layered-EV stage placement)",
                 fontsize=10, pad=8)
    ax.legend(loc="lower left", fontsize=8, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_ylim(40, 105)

    # Right: investor multiple
    ax = axes[1]
    em = fs["expected_multiple"]
    entry_stages = ["pre_seed", "seed", "series_a"]
    entry_labels = ["Pre-Seed", "Seed", "Series A"]
    nc_legacy = [em["neurocertify_legacy"].get(s, 0) for s in entry_stages]
    nc_ai = [em["neurocertify_ai_native"].get(s, 0) for s in entry_stages]
    df_legacy = [em["dataflow_legacy"].get(s, 0) for s in entry_stages]
    df_ai = [em["dataflow_ai_native"].get(s, 0) for s in entry_stages]

    x = np.arange(len(entry_stages))
    width = 0.20
    bars_groups = [
        (x - 1.5*width, nc_legacy, "#2C5282", "NC, legacy"),
        (x - 0.5*width, nc_ai, "#7DB1D9", "NC, IA-native"),
        (x + 0.5*width, df_legacy, "#7A1F1F", "DF, legacy"),
        (x + 1.5*width, df_ai, "#E07B39", "DF, IA-native"),
    ]
    for px, vals, color, label in bars_groups:
        for p, v in zip(px, vals):
            if v > 0:
                ax.bar(p, v, width, color=color, edgecolor="black", linewidth=0.3)
                ax.text(p, v + 0.4, f"{v:.1f}x", ha="center", fontsize=8)
        ax.bar([], [], color=color, label=label)

    ax.set_xticks(x)
    ax.set_xticklabels(entry_labels)
    ax.set_ylabel("Expected investor multiple (10-year horizon)")
    ax.set_title("Expected multiple by entry stage", fontsize=10, pad=8)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(max(nc_ai), max(df_ai)) * 1.2)

    plt.suptitle("Founder dilution and investor return: NeuroCertify vs DataFlow Pro",
                 fontsize=12, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = FIG_DIR / "fig34_appendix_e_dilution.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_e5_fragility():
    """Figure E.5: fragility map of NeuroCertify + DataFlow Pro on L4 × L6 space."""
    fi = config.load_parameters()["fragility_index"]
    coef = float(fi["l6_coefficient"])

    # Build the colour contour
    l4 = np.linspace(0, 0.70, 100)
    l6 = np.linspace(0, 0.50, 100)
    L4, L6 = np.meshgrid(l4, l6)
    Z = L4 - coef * L6

    fig, ax = plt.subplots(figsize=(11, 7))
    im = ax.contourf(L4, L6, Z, levels=20, cmap="RdYlGn_r",
                      vmin=float(fi["color_vmin"]), vmax=float(fi["color_vmax"]))
    ax.contour(L4, L6, Z, levels=[0], colors="black", linewidths=1.5, linestyles="--")

    # Parity line: L4 = L6
    ax.plot([0, 0.50], [0, 0.50], color="grey", linestyle=":", linewidth=1, alpha=0.7)
    ax.text(0.40, 0.42, "Parity line\n(L4 = L6)", fontsize=8, color="grey",
            style="italic", rotation=45)

    # Plot the two case studies
    fr = case_studies_fragility()
    nc = fr["neurocertify"]
    df = fr["dataflow_pro"]

    ax.scatter(nc.layer4_share, nc.layer6_share, s=200, color="#2C5282",
                marker="s", edgecolor="black", linewidth=1.5, zorder=10,
                label=f"NeuroCertify (idx={nc.fragility_index:.2f}, {nc.zone})")
    ax.annotate(f"NeuroCertify\n(Layer 4: 20%, Layer 6: 40%)\nResilient: Layer-6 moat",
                xy=(nc.layer4_share, nc.layer6_share),
                xytext=(0.05, 0.45), fontsize=9, color="#2C5282",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor="#2C5282", alpha=0.9),
                arrowprops=dict(arrowstyle="->", color="#2C5282"))

    ax.scatter(df.layer4_share, df.layer6_share, s=200, color="#7A1F1F",
                marker="o", edgecolor="black", linewidth=1.5, zorder=10,
                label=f"DataFlow Pro (idx={df.fragility_index:.2f}, {df.zone})")
    ax.annotate(f"DataFlow Pro\n(Layer 4: 55%, Layer 6: 10%)\nFragile: Layer-4 exposure",
                xy=(df.layer4_share, df.layer6_share),
                xytext=(0.55, 0.30), fontsize=9, color="#7A1F1F",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor="#7A1F1F", alpha=0.9),
                arrowprops=dict(arrowstyle="->", color="#7A1F1F"))

    # Zone labels
    ax.text(0.05, 0.05, "Resilient zone\n(low L4, high L6)\nNeuroCertify-like firms",
            fontsize=9, color="#0B6E4F", style="italic",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#E5F5E5",
                      edgecolor="#0B6E4F", alpha=0.9))
    ax.text(0.55, 0.02, "Fragile zone\n(high L4, low L6)\nDataFlow-like firms",
            fontsize=9, color="#7A1F1F", style="italic",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFE5E5",
                      edgecolor="#7A1F1F", alpha=0.9))

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(f"Fragility index\n(Layer-4 − {coef} × Layer-6)", fontsize=9)

    ax.set_xlabel("Layer-4 share (codified, AI-substitutable work)")
    ax.set_ylabel("Layer-6 share (institutional defensibility, regulatory moat)")
    ax.set_xlim(0, 0.70)
    ax.set_ylim(0, 0.55)
    ax.set_title("Fragility map: NeuroCertify vs DataFlow Pro across the seven layers\n"
                 "(green = resilient, red = fragile under post-AI dynamics)",
                 fontsize=11, pad=10)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.3)

    plt.tight_layout()
    out = FIG_DIR / "fig35_appendix_e_fragility.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def main():
    print("\nGenerating Appendix E figures (dynamic case companies)\n" + "=" * 60)
    make_fig_e1_migration()
    make_fig_e2_capital()
    make_fig_e3_risk()
    make_fig_e4_dilution()
    make_fig_e5_fragility()
    print("\nDone.")


if __name__ == "__main__":
    main()
