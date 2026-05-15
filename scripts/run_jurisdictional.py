"""Generate jurisdictional comparison figure and summary table.

Produces:
  - outputs/figures/fig11_jurisdictional_inversion.png
  - outputs/figures/fig12_substitution_npv_decomposition.png
  - outputs/tables/jurisdictional_summary.csv

These materials operationalize the accounting-substitution analysis of
section 6.5 (de Miranda Neto, 2026), showing that the magnitude of the
inverted key-person discount depends materially on the jurisdiction.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.jurisdictional import (
    JURISDICTION_DEFAULTS,
    compute_accounting_substitution,
    jurisdictional_inverted_discount,
)

FIGURE_DIR = Path(__file__).parent.parent / "outputs" / "figures"
TABLE_DIR = Path(__file__).parent.parent / "outputs" / "tables"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Reference scenario for comparison: a 50-engineer SaaS B2B with $30M ARR,
# enterprise value ~$200M (using a 7x revenue multiple). Acquirer evaluates
# replacing 60% of layer-4 engineers with AI tooling.
# =============================================================================

ENTERPRISE_VALUE_USD = 200_000_000
N_EMPLOYEES = 50
TEAM_LAYER3_SHARE = 0.70
AI_SUBSTITUTION_POTENTIAL = 0.65
ANNUAL_AI_COST_PER_EMP = 4800  # USD

# Local salary by jurisdiction (already set in scenarios)
LOCAL_SALARIES = {
    "brazil": 35000,
    "france": 75000,
    "united_states": 165000,
}


def run_jurisdictional_comparison():
    rows = []
    for key, jur in JURISDICTION_DEFAULTS.items():
        salary = LOCAL_SALARIES[key]

        # Compute accounting-substitution decomposition
        sub = compute_accounting_substitution(
            n_employees_replaced=int(round(N_EMPLOYEES * 0.6)),
            avg_base_salary_usd=salary,
            annual_ai_cost_per_replaced_employee_usd=ANNUAL_AI_COST_PER_EMP,
            jurisdiction=jur,
            discount_rate=0.12,
            horizon_years=5,
        )

        # Compute jurisdictional inverted discount
        adjusted, components = jurisdictional_inverted_discount(
            enterprise_value_usd=ENTERPRISE_VALUE_USD,
            team_layer4_share=TEAM_LAYER3_SHARE,
            ai_substitution_potential_layer4=AI_SUBSTITUTION_POTENTIAL,
            n_employees=N_EMPLOYEES,
            avg_base_salary_usd=salary,
            annual_ai_cost_per_replaced_employee_usd=ANNUAL_AI_COST_PER_EMP,
            jurisdiction=jur,
        )

        inversion_premium_pct = 100 * components.get("inversion_premium_usd", 0.0) / ENTERPRISE_VALUE_USD
        effective_disc = 100 * components.get("effective_discount_rate", 0.0)

        rows.append({
            "jurisdiction": jur.name,
            "labor_cost_multiplier": jur.labor_cost_multiplier,
            "ai_overhead": jur.ai_service_overhead,
            "termination_frac": jur.termination_cost_fraction + jur.notice_period_fraction,
            "avg_salary_usd": salary,
            "annual_labor_eliminated_usd": sub.annual_labor_cost_eliminated_usd,
            "annual_ai_added_usd": sub.annual_ai_service_cost_usd,
            "net_annual_savings_usd": sub.net_annual_savings_usd,
            "termination_cost_usd": sub.one_time_termination_cost_usd,
            "npv_substitution_usd": sub.npv_substitution_usd,
            "inversion_premium_pct_of_EV": inversion_premium_pct,
            "effective_discount_rate_pct": effective_disc,
            "regime": components.get("regime", "n/a"),
        })

    return pd.DataFrame(rows)


def make_figure_jurisdictional_inversion(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    # ---- Left panel: stacked-bar of cost components ----
    ax1 = axes[0]
    jurisdictions = df["jurisdiction"].tolist()
    x = np.arange(len(jurisdictions))
    width = 0.35

    labor_elim = df["annual_labor_eliminated_usd"].values / 1e6
    ai_added = df["annual_ai_added_usd"].values / 1e6
    net = df["net_annual_savings_usd"].values / 1e6

    ax1.bar(x - width/2, labor_elim, width,
            label="Annual labor cost eliminated", color="#2c7fb8")
    ax1.bar(x + width/2, ai_added, width,
            label="Annual AI service cost added", color="#d95f02")

    for i, n in enumerate(net):
        ax1.annotate(f"net +${n:.1f}M",
                     xy=(x[i], max(labor_elim[i], ai_added[i]) * 1.05),
                     ha="center", fontsize=10, fontweight="bold",
                     color="#1b7837")

    ax1.set_xticks(x)
    ax1.set_xticklabels(jurisdictions, fontsize=10)
    ax1.set_ylabel("Annual cost flow (USD millions)")
    ax1.set_title("Annual cost substitution: labor eliminated vs. AI services added\n"
                  "(50-engineer firm, 60% replaceable, 5-year horizon)",
                  fontsize=11)
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(True, linestyle=":", alpha=0.5)
    ax1.set_axisbelow(True)

    # ---- Right panel: inversion premium as % of EV ----
    ax2 = axes[1]
    inversion_pct = df["inversion_premium_pct_of_EV"].values
    colors = ["#1b7837" if v > 0 else "#762a83" for v in inversion_pct]
    bars = ax2.barh(jurisdictions, inversion_pct, color=colors)
    ax2.axvline(0, color="black", linewidth=0.8)
    ax2.set_xlabel("Inversion premium as % of enterprise value\n(positive = upside for acquirer)")
    ax2.set_title("Jurisdictional magnitude of the inversion\n"
                  "(EV = $200M reference)", fontsize=11)
    ax2.grid(True, linestyle=":", alpha=0.5, axis="x")
    ax2.set_axisbelow(True)

    for bar, value in zip(bars, inversion_pct):
        x_text = value + (0.3 if value > 0 else -0.3)
        ha = "left" if value > 0 else "right"
        ax2.text(x_text, bar.get_y() + bar.get_height() / 2,
                 f"{value:+.1f}%", va="center", ha=ha, fontsize=11,
                 fontweight="bold")

    fig.suptitle("")
    plt.tight_layout()
    out = FIGURE_DIR / "fig11_jurisdictional_inversion.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_figure_substitution_decomposition(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(11, 5.5))

    jurisdictions = df["jurisdiction"].tolist()
    x = np.arange(len(jurisdictions))

    # Stacked composition of the NPV
    npv_recurring_5y = df["net_annual_savings_usd"].values * 3.605  # approximate annuity factor at 12%
    termination = -df["termination_cost_usd"].values
    npv_total = df["npv_substitution_usd"].values

    bars1 = ax.bar(x, npv_recurring_5y / 1e6,
                   color="#2c7fb8", label="NPV of 5-year recurring savings")
    bars2 = ax.bar(x, termination / 1e6,
                   bottom=npv_recurring_5y / 1e6,
                   color="#d95f02", label="One-time termination cost (negative)")

    # Annotate net NPV
    for i, n in enumerate(npv_total / 1e6):
        ax.annotate(f"NPV total: ${n:.1f}M",
                    xy=(x[i], npv_recurring_5y[i] / 1e6 + 8),
                    ha="center", fontsize=11, fontweight="bold",
                    color="#1b7837" if n > 0 else "#762a83")

    ax.set_xticks(x)
    ax.set_xticklabels(jurisdictions, fontsize=11)
    ax.set_ylabel("NPV components (USD millions)")
    ax.set_title("")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.5, axis="y")
    ax.set_axisbelow(True)

    plt.tight_layout()
    out = FIGURE_DIR / "fig12_substitution_npv_decomposition.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def run_crossborder_comparison():
    """Cross-border M&A: same target firm, evaluated under different jurisdictional
    cost structures depending on where the acquirer plans to operate the team.
    A US acquirer of a Brazilian startup may either keep the team in Brazil
    (Brazilian cost structure) or relocate / replace with US labor (US cost
    structure). The inversion premium is computed under each scenario.

    For a Brazilian SaaS B2B target, the relevant comparison is:
    (a) acquirer keeps team in-country with Brazilian cost structure,
    (b) acquirer dissolves Brazilian team and operates from US cost structure,
    (c) acquirer keeps team but the *same number of replaceable engineers*
        substituted by AI (the standard inverted-discount logic).

    This isolates the effect of cost-structure choice on the magnitude of
    the inversion premium.
    """
    rows = []
    target_n_employees = 50
    target_share_replaceable = 0.6
    n_replaced = int(round(target_n_employees * target_share_replaceable))

    for key, jur in JURISDICTION_DEFAULTS.items():
        salary = LOCAL_SALARIES[key]
        sub = compute_accounting_substitution(
            n_employees_replaced=n_replaced,
            avg_base_salary_usd=salary,
            annual_ai_cost_per_replaced_employee_usd=ANNUAL_AI_COST_PER_EMP,
            jurisdiction=jur,
            discount_rate=0.12,
            horizon_years=5,
        )
        rows.append({
            "operating_cost_basis": jur.name,
            "annual_savings_usd": sub.net_annual_savings_usd,
            "termination_cost_usd": sub.one_time_termination_cost_usd,
            "npv_substitution_usd": sub.npv_substitution_usd,
            "premium_pct_of_200M_EV": 100 * sub.npv_substitution_usd / 200_000_000,
        })
    return pd.DataFrame(rows)


def make_figure_crossborder(df_cb: pd.DataFrame):
    """A US acquirer evaluating a target. The inversion premium it can capture
    depends on whether the post-deal operating model uses local labor (Brazilian
    or French) or relocates to US cost structure.
    """
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bases = df_cb["operating_cost_basis"].tolist()
    pct = df_cb["premium_pct_of_200M_EV"].values
    colors = ["#1b7837", "#fdb462", "#9ecae1"]
    bars = ax.bar(bases, pct, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("Inversion premium (% of $200M enterprise value)")
    ax.set_title("")
    for bar, value in zip(bars, pct):
        ax.text(bar.get_x() + bar.get_width()/2, value + 0.08,
                f"+{value:.2f}%", ha="center", fontsize=11, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.5, axis="y")
    ax.set_axisbelow(True)
    ax.set_xlabel("Operating-cost basis post-acquisition")
    plt.tight_layout()
    out = FIGURE_DIR / "fig13_crossborder.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def main():
    df = run_jurisdictional_comparison()
    out_csv = TABLE_DIR / "jurisdictional_summary.csv"
    df.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv}")
    print()
    print(df.to_string(index=False))
    make_figure_jurisdictional_inversion(df)
    make_figure_substitution_decomposition(df)

    df_cb = run_crossborder_comparison()
    out_cb = TABLE_DIR / "crossborder_summary.csv"
    df_cb.to_csv(out_cb, index=False)
    print()
    print("Cross-border comparison:")
    print(df_cb.to_string(index=False))
    make_figure_crossborder(df_cb)


if __name__ == "__main__":
    main()
