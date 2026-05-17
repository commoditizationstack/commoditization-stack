"""Generate figures for Section 7.5 (Migration dynamics under AI orchestrator).

Outputs:
    figures/fig21_migration_reference_firm.png  — Figure 11 in the paper
    figures/fig22_neurocertify_migration.png    — Figure 12 in the paper
    figures/fig23_dataflow_migration.png        — Figure 13 in the paper

Each figure has two panels: cumulative cash-flow trajectory (left) and total
migration cost decomposition (right), mirroring the layout of the paper.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import matplotlib.pyplot as plt

from src import config
from src.migration_dynamics import (
    MigrationParameters,
    compute_migration,
    reference_firm_migration,
    case_study_migration,
)

FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


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


def _phase_shading(ax):
    """Add assessment / transition / learning / steady-state phase shading."""
    ax.axvspan(-3.5, -0.5, alpha=0.12, color="#F5C242", zorder=0)   # assessment
    ax.axvspan(-0.5, 3.5, alpha=0.12, color="#C44536", zorder=0)    # transition
    ax.axvspan(3.5, 10.5, alpha=0.10, color="#2C5282", zorder=0)    # learning
    ax.axvspan(10.5, 21, alpha=0.10, color="#0B6E4F", zorder=0)     # steady state
    ymin, ymax = ax.get_ylim()
    label_y = ymax - (ymax - ymin) * 0.04
    ax.text(-2, label_y, "Assessment\n& pilot", ha="center", fontsize=8,
            color="#7A5C00", va="top", style="italic")
    ax.text(1.5, label_y, "Transition", ha="center", fontsize=8,
            color="#7A1F1F", va="top", style="italic")
    ax.text(7, label_y, "Learning curve", ha="center", fontsize=8,
            color="#1F3A6A", va="top", style="italic")
    ax.text(16, label_y, "Steady state", ha="center", fontsize=8,
            color="#1F5040", va="top", style="italic")


def _draw_cash_flow_panel(ax, trajectories, title, ylabel):
    """Plot cumulative cash flow trajectories on a phase-shaded axis."""
    for label, (quarters, cum, color) in trajectories.items():
        cum_m = np.array(cum) / 1e6
        ax.plot(quarters, cum_m, marker="o", markersize=4, linewidth=2,
                color=color, label=label)
        # Endpoint annotation
        ax.annotate(f"${cum_m[-1]:.2f}M", xy=(quarters[-1], cum_m[-1]),
                    xytext=(5, 0), textcoords="offset points",
                    fontsize=10, fontweight="bold", color=color, va="center")

    ax.axhline(0, color="black", linewidth=0.7)
    ax.axvline(0, color="grey", linewidth=0.5, linestyle="--")
    ax.set_xlabel("Quarters (T0 = migration decision; T-3 = assessment & pilot start)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11, pad=8)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92)
    _phase_shading(ax)


def _draw_cost_decomposition_panel(ax, results, jurisdictions, labels):
    """Stacked bar chart of cumulative migration cost components by jurisdiction."""
    md = config.load_parameters()["migration_dynamics"]
    n_arms = len(results)
    x = np.arange(n_arms)
    width = 0.6

    # Compute cost components per result
    orch_assessment = []
    termination = []
    dual_op = []
    retention = []
    orch_ongoing = []

    for r in results:
        # Assessment phase: 3 quarters of orchestrator cost (T-3 to T-1)
        orch_assessment.append(r.annual_orchestrator_cost_usd * 0.75 / 1e6)
        termination.append(r.termination_cost_t0_usd / 1e6)
        # Dual op overhead (T1-T3, decaying)
        # Approx: 0.5 * 0.5 * substituted_eng_loaded_cost * 3 quarters
        dual_op_total = 0.75 * r.n_substitutable * config.load_parameters()[
            "migration_dynamics"]["loaded_mid_engineer_usd_year"]["united_states"]
        dual_op.append(dual_op_total * 0.20 / 1e6)  # approximated decay
        retention.append(
            (r.n_retained * 95000 * float(md["retention_bonus_fraction"]) * 0.5) / 1e6
        )
        # Ongoing 5y orchestrator cost
        orch_ongoing.append(r.annual_orchestrator_cost_usd * 5 / 1e6)

    orch_assessment = np.array(orch_assessment)
    termination = np.array(termination)
    dual_op = np.array(dual_op)
    retention = np.array(retention)
    orch_ongoing = np.array(orch_ongoing)

    totals = orch_assessment + termination + dual_op + retention + orch_ongoing

    bottom = np.zeros(n_arms)
    for vals, color, label in [
        (orch_assessment, "#F5C242", "Orchestrators in assessment (T-3 to T-1)"),
        (termination, "#C44536", "Termination cost (T0)"),
        (dual_op, "#8E44AD", "Dual-operation overhead (T1-T3)"),
        (retention, "#F8C8DC", "Retention bonus (T1-T2)"),
        (orch_ongoing, "#0B6E4F", "Orchestrators ongoing (5 years post-T0)"),
    ]:
        bars = ax.bar(x, vals, width, bottom=bottom, color=color, label=label,
                      edgecolor="white", linewidth=0.4)
        for i, (b, v) in enumerate(zip(bars, vals)):
            if v > 0.05:  # only annotate visible segments
                ax.text(b.get_x() + b.get_width()/2,
                        bottom[i] + v/2,
                        f"${v:.2f}M",
                        ha="center", va="center", fontsize=8,
                        color="white" if color in ["#C44536", "#8E44AD", "#0B6E4F"] else "black")
        bottom += vals

    for i, total in enumerate(totals):
        ax.text(i, total + 0.1, f"${total:.2f}M", ha="center",
                fontsize=10, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Cumulative cost over 5+ years (USD millions)")
    ax.set_title("Total migration cost decomposition\n"
                 "(orchestrators as permanent function included)",
                 fontsize=10, pad=8)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.92,
              bbox_to_anchor=(0.0, -0.10), ncol=1)
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)


def make_fig11_reference_firm():
    """Figure 11: reference firm migration (50 engineers, 60% sub), three jurisdictions."""
    results = {j: reference_firm_migration(j) for j in JURISDICTION_COLORS}

    fig, axes = plt.subplots(2, 1, figsize=(11, 11),
                              gridspec_kw={"height_ratios": [1.3, 1]})

    # Top panel: cash flow trajectories
    trajectories = {
        JURISDICTION_LABEL[j]: (results[j].quarters,
                                results[j].cumulative_cash_usd,
                                JURISDICTION_COLORS[j])
        for j in results
    }
    title = ("Cumulative cash flow of AI-migration with AI orchestrators "
             "as permanent function\n(50 engineers, 60% substitution, "
             "2 orchestrators permanent, K7 = 1.0)")
    _draw_cash_flow_panel(axes[0], trajectories, title,
                          ylabel="Cumulative cash flow (USD millions)")

    # Break-even inset
    be_text = "Break-even from T0:\n"
    for j in ["united_states", "brazil", "france"]:
        be = results[j].break_even_quarter
        be_str = f"Q{be:.1f} ({be*3:.0f} months)" if be else "> 5 years"
        be_text += f"  • {JURISDICTION_LABEL[j]}: {be_str}\n"
    axes[0].text(0.55, 0.30, be_text.strip(), transform=axes[0].transAxes,
                 fontsize=9, verticalalignment="top",
                 bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                           edgecolor="grey", alpha=0.9))

    # Bottom panel: cost decomposition
    _draw_cost_decomposition_panel(
        axes[1],
        [results[j] for j in ["brazil", "france", "united_states"]],
        ["brazil", "france", "united_states"],
        ["Brazil", "France", "US"],
    )

    plt.suptitle("Migration cash flow with AI orchestrators (permanent) and learning curve",
                 fontsize=13, fontweight="bold", y=0.995)
    plt.tight_layout()
    out = FIG_DIR / "fig21_migration_reference_firm.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig12_neurocertify():
    """Figure 12: NeuroCertify migration (Brazilian arm, French arm, consolidated)."""
    br = case_study_migration("neurocertify", "brazil")
    fr = case_study_migration("neurocertify", "france")
    # Consolidated = sum of arms
    consolidated_cum = [
        b + f for b, f in zip(br.cumulative_cash_usd, fr.cumulative_cash_usd)
    ]

    fig, axes = plt.subplots(2, 1, figsize=(11, 11),
                              gridspec_kw={"height_ratios": [1.3, 1]})

    trajectories = {
        f"NeuroCertify (Brazil arm, {br.n_substitutable} substitutable)": (
            br.quarters, br.cumulative_cash_usd, "#0B6E4F"),
        f"NeuroCertify (France arm, {fr.n_substitutable} substitutable)": (
            fr.quarters, fr.cumulative_cash_usd, "#2C5282"),
        f"Consolidated (25 eng, {br.n_substitutable + fr.n_substitutable} substitutable)": (
            br.quarters, consolidated_cum, "#8E44AD"),
    }
    title = ("NeuroCertify migration cash flow "
             "(deep-tech regulated, Layer 4 = 20%, AI sub = 0.50)\n"
             "Cumulative cash flow of IA-migration\n"
             "(NeuroCertify per Appendix A.3; Franco-Brazilian, K7 = 1.0)")
    _draw_cash_flow_panel(axes[0], trajectories, title,
                          ylabel="Cumulative cash flow (USD millions)")

    # Break-even inset
    be_text = ("Break-even from T0:\n"
               f"  • Brazil arm (15 eng, {br.n_substitutable} substitutable): > 5 years\n"
               f"  • France arm (10 eng, {fr.n_substitutable} substitutable): > 5 years\n"
               f"  • Consolidated (25 eng, {br.n_substitutable + fr.n_substitutable} "
               "substitutable): > 5 years")
    axes[0].text(0.40, 0.96, be_text, transform=axes[0].transAxes,
                 fontsize=9, verticalalignment="top",
                 bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                           edgecolor="grey", alpha=0.9))

    # Bottom panel: cost decomposition with consolidated
    class FakeConsolidatedResult:
        annual_orchestrator_cost_usd = (br.annual_orchestrator_cost_usd
                                         + fr.annual_orchestrator_cost_usd)
        termination_cost_t0_usd = (br.termination_cost_t0_usd
                                    + fr.termination_cost_t0_usd)
        n_substitutable = br.n_substitutable + fr.n_substitutable
        n_retained = br.n_retained + fr.n_retained

    _draw_cost_decomposition_panel(
        axes[1],
        [br, fr, FakeConsolidatedResult()],
        ["brazil", "france", "consolidated"],
        ["BR arm", "FR arm", "Consolidated"],
    )

    plt.suptitle("NeuroCertify migration: arms operated separately + consolidated view",
                 fontsize=13, fontweight="bold", y=0.995)
    plt.tight_layout()
    out = FIG_DIR / "fig22_neurocertify_migration.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig13_dataflow():
    """Figure 13: DataFlow Pro migration (three substitution scenarios)."""
    scenarios = ["conservative", "moderate", "aggressive"]
    colors = ["#0B6E4F", "#F5C242", "#C44536"]
    results = {
        sc: case_study_migration("dataflow_pro", "united_states", scenario=sc)
        for sc in scenarios
    }

    fig, axes = plt.subplots(2, 1, figsize=(11, 11),
                              gridspec_kw={"height_ratios": [1.3, 1]})

    cs = config.load_parameters()["case_studies_dynamic"]["dataflow_pro"]["scenarios"]
    trajectories = {}
    for sc, color in zip(scenarios, colors):
        sub_pct = int(float(cs[sc]["substitution_pct"]) * 100)
        n_sub = int(cs[sc]["substitutable_engineers"])
        trajectories[
            f"{sc.title()} ({sub_pct}% sub.) — {n_sub} subst."
        ] = (results[sc].quarters, results[sc].cumulative_cash_usd, color)

    title = ("DataFlow Pro migration cash flow "
             "(commoditizing-tech, Layer 4 = 55%, three scenarios)\n"
             "Cumulative cash flow of IA-migration\n"
             "(DataFlow Pro per Appendix A.3; US-domiciled, K7 = 1.0)")
    _draw_cash_flow_panel(axes[0], trajectories, title,
                          ylabel="Cumulative cash flow (USD millions)")

    # Break-even inset
    be_text = "Break-even from T0:\n"
    for sc in scenarios:
        sub_pct = int(float(cs[sc]["substitution_pct"]) * 100)
        n_sub = int(cs[sc]["substitutable_engineers"])
        be = results[sc].break_even_quarter
        be_str = f"Q{be:.1f} ({be*3:.0f} mo)" if be else "> 5 years"
        be_text += f"  • {sc.title()} ({sub_pct}% sub.) — {n_sub} subst.: {be_str}\n"
    axes[0].text(0.55, 0.45, be_text.strip(), transform=axes[0].transAxes,
                 fontsize=9, verticalalignment="top",
                 bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                           edgecolor="grey", alpha=0.9))

    # Bottom panel
    _draw_cost_decomposition_panel(
        axes[1],
        [results[sc] for sc in scenarios],
        ["united_states"] * 3,
        ["Conservative", "Moderate", "Aggressive"],
    )

    plt.suptitle("DataFlow Pro migration: three substitution scenarios",
                 fontsize=13, fontweight="bold", y=0.995)
    plt.tight_layout()
    out = FIG_DIR / "fig23_dataflow_migration.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def main():
    print("\nGenerating Section 7.5 migration dynamics figures\n" + "=" * 60)
    make_fig11_reference_firm()
    make_fig12_neurocertify()
    make_fig13_dataflow()
    print("\nDone.")


if __name__ == "__main__":
    main()
