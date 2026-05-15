"""Generate figures and tables for Layer 7 (cross-border knowledge regime).

Produces:
  - outputs/figures/fig14_knowledge_regime_geometry.png — Layer 4 commoditization
    velocity as a function of K7, with the baseline (K7=1.0), current (K7=0.7),
    and fragmented (K7=0.4) regimes marked.
  - outputs/figures/fig15_layer7_k_sensitivity.png — sensitivity of the
    inversion premium to K7 under each jurisdiction.
  - Re-runs the jurisdictional comparison under K7=0.7 to update the principal
    figures (11, 12, 13) with the current regime, and saves the K7=1.0 baseline
    as an additional comparison.
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
from src.stack_layers import (
    KNOWLEDGE_REGIME_DEFAULTS,
    apply_knowledge_regime_modulation,
    crossborder_acquisition_friction,
)

FIGURE_DIR = Path(__file__).parent.parent / "outputs" / "figures"
TABLE_DIR = Path(__file__).parent.parent / "outputs" / "tables"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)


def make_fig14_knowledge_regime_geometry():
    """Show Layer 4 commoditization velocity as a function of K7, with the
    three reference regimes marked.

    The y-axis represents the effective Layer-4 substitution potential,
    interpreted as the fraction of Layer-4 tasks substitutable by AI tools.
    Under K7=1.0 (full integration), this approaches the headline industry
    estimates of 60-70%. Under K7<1, the substitution is constrained because
    frontier models within a bloc have less than complete access to the
    relevant corpora.
    """
    K7_values = np.linspace(0, 1, 101)
    baseline_substitutability = 0.70  # baseline at K7=1.0

    layer4_effective = K7_values * baseline_substitutability
    layer5_relative_value = 1.0 / np.maximum(0.1, K7_values * 0.85 + 0.15)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    ax1 = axes[0]
    ax1.plot(K7_values, layer4_effective, color="#2c7fb8", linewidth=2.4,
             label="Layer 4 effective substitutability")
    for k, label, color in [(1.0, "K\u2087=1.0\n(2020 baseline)", "#1b7837"),
                             (0.7, "K\u2087=0.7\n(2026 current)", "#fdb462"),
                             (0.4, "K\u2087=0.4\n(2030 fragmented)", "#762a83")]:
        y = k * baseline_substitutability
        ax1.plot([k], [y], 'o', color=color, markersize=10)
        offset_y = 0.06 if k == 0.4 else (0.05 if k == 0.7 else -0.10)
        ax1.annotate(label, (k, y), xytext=(k - 0.05, y + offset_y),
                     fontsize=9, ha="right" if k == 1.0 else "center",
                     color=color, fontweight="bold")

    ax1.set_xlim(0, 1.05)
    ax1.set_ylim(0, 0.85)
    ax1.set_xlabel("Knowledge-integration coefficient K\u2087", fontsize=11)
    ax1.set_ylabel("Effective Layer-4 substitutability", fontsize=11)
    ax1.set_title("Panel A. Layer-4 commoditization under varying K\u2087\n"
                  "(seven-layer framework, Section 4.7)",
                  fontsize=11, fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.5)
    ax1.set_axisbelow(True)

    ax2 = axes[1]
    ax2.plot(K7_values, layer5_relative_value, color="#d95f02", linewidth=2.4,
             label="Layer 5 relative judgment value")
    for k, label, color in [(1.0, "K\u2087=1.0", "#1b7837"),
                             (0.7, "K\u2087=0.7", "#fdb462"),
                             (0.4, "K\u2087=0.4", "#762a83")]:
        y = 1.0 / max(0.1, k * 0.85 + 0.15)
        ax2.plot([k], [y], 'o', color=color, markersize=10)
        ax2.annotate(label, (k, y), xytext=(k - 0.04, y + 0.10),
                     fontsize=10, ha="right", color=color, fontweight="bold")

    ax2.set_xlim(0, 1.05)
    ax2.set_xlabel("Knowledge-integration coefficient K\u2087", fontsize=11)
    ax2.set_ylabel("Layer 5 relative judgment value\n"
                   "(scale: 1.0 at K\u2087=1.0)", fontsize=11)
    ax2.set_title("Panel B. Layer-5 judgment value rises as K\u2087 falls\n"
                  "(more human curation needed for bloc-specific bias)",
                  fontsize=11, fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.5)
    ax2.set_axisbelow(True)

    fig.suptitle("")
    plt.tight_layout()
    out = FIGURE_DIR / "fig14_knowledge_regime_geometry.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig15_inversion_under_k():
    """Sensitivity of the inversion premium to K7 under each jurisdiction,
    plus a cross-bloc acquisition scenario that exposes Layer-7 friction.

    Plots four curves:
      - Brazil (CLT) - same-bloc acquisition
      - France (CDI) - same-bloc acquisition
      - United States (W-2) - same-bloc acquisition
      - United States (W-2) cross-bloc - target and acquirer in different
        knowledge blocs, friction coefficient 0.30 from
        crossborder_acquisition_friction

    Annotates the collapse threshold near K7 = 0.45, where the inversion regime
    breaks down across all jurisdictions and the classical key-person discount
    reasserts itself.
    """
    K7_values = np.linspace(0.2, 1.0, 17)
    enterprise_value = 200_000_000
    n_employees = 50
    team_layer4_share = 0.70
    base_substitution_potential = 0.65

    salaries = {
        "brazil": 35000,
        "france": 75000,
        "united_states": 165000,
    }
    colors = {
        "brazil": "#1b7837",
        "france": "#fdb462",
        "united_states": "#3182bd",
    }

    fig, ax = plt.subplots(figsize=(11, 6.4))

    rows = []
    # Three same-bloc curves
    for key, jur in JURISDICTION_DEFAULTS.items():
        salary = salaries[key]
        premium_pct = []
        for K7 in K7_values:
            modulated_potential = base_substitution_potential * K7
            adjusted, components = jurisdictional_inverted_discount(
                enterprise_value_usd=enterprise_value,
                team_layer4_share=team_layer4_share,
                ai_substitution_potential_layer4=modulated_potential,
                n_employees=n_employees,
                avg_base_salary_usd=salary,
                annual_ai_cost_per_replaced_employee_usd=4800,
                jurisdiction=jur,
            )
            premium_pct_k = (
                100 * components.get("inversion_premium_usd", 0.0) / enterprise_value
            )
            premium_pct.append(premium_pct_k)
            rows.append({
                "jurisdiction": jur.name,
                "scenario": "same_bloc",
                "K7": K7,
                "inversion_premium_pct": premium_pct_k,
            })

        ax.plot(K7_values, premium_pct,
                color=colors[key], linewidth=2.4, marker="o", markersize=5,
                label=jur.name)

    # Fourth curve: US under cross-bloc acquisition (target western,
    # acquirer in different bloc). Crossborder friction reduces the
    # effective substitution potential by 30%.
    us_jur = JURISDICTION_DEFAULTS["united_states"]
    crossbloc_premium_pct = []
    for K7 in K7_values:
        modulated_potential_same_bloc = base_substitution_potential * K7
        # Apply Layer-7 cross-bloc friction
        modulated_potential_crossbloc = crossborder_acquisition_friction(
            target_bloc="western",
            acquirer_bloc="non_aligned",
            base_substitution_potential=modulated_potential_same_bloc,
        )
        adjusted, components = jurisdictional_inverted_discount(
            enterprise_value_usd=enterprise_value,
            team_layer4_share=team_layer4_share,
            ai_substitution_potential_layer4=modulated_potential_crossbloc,
            n_employees=n_employees,
            avg_base_salary_usd=salaries["united_states"],
            annual_ai_cost_per_replaced_employee_usd=4800,
            jurisdiction=us_jur,
        )
        premium_pct_k = (
            100 * components.get("inversion_premium_usd", 0.0) / enterprise_value
        )
        crossbloc_premium_pct.append(premium_pct_k)
        rows.append({
            "jurisdiction": "United States (W-2) cross-bloc",
            "scenario": "cross_bloc",
            "K7": K7,
            "inversion_premium_pct": premium_pct_k,
        })

    ax.plot(K7_values, crossbloc_premium_pct,
            color="#762a83", linewidth=2.4, marker="s", markersize=5,
            linestyle="--",
            label="United States (W-2) - cross-bloc acquisition")

    # Compute the dynamic upper limit BEFORE drawing reference markers,
    # and add explicit headroom so that the K7 reference labels do not
    # overlap with the topmost data points OR with the collapse-threshold
    # annotation in the bottom-left region.
    all_y = []
    for v in premium_pct:
        all_y.append(v)
    for v in crossbloc_premium_pct:
        all_y.append(v)
    y_max_data = max(all_y) if all_y else 4.0
    y_top = y_max_data * 1.28   # 28% headroom for the top-row K7 labels
    ax.set_ylim(-0.3, y_top)

    # Collapse-threshold band: a NARROW band around K7 ≈ 0.45 (not encompassing
    # the K7=0.4 reference marker). Lower alpha so it does not visually compete
    # with the K7 reference labels.
    ax.axvspan(0.43, 0.47, color="red", alpha=0.06, zorder=0)

    # Reference K7 markers — vertical dotted lines plus a label box
    # placed in the headroom region. The labels are drawn with bbox +
    # ha="center" so they cannot overlap data or each other.
    label_y = y_top * 0.93
    for k, label, color in [(1.0, "K\u2087=1.0\n(2020 baseline)", "#1b7837"),
                            (0.7, "K\u2087=0.7\n(2026 illustrative)", "#fdb462"),
                            (0.4, "K\u2087=0.4\n(2030 fragmented)", "#762a83")]:
        ax.axvline(k, color=color, linestyle=":", alpha=0.7, linewidth=1.3,
                   zorder=1)
        ax.text(k, label_y, label,
                fontsize=8.5, color=color, ha="center", va="top",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                          edgecolor=color, alpha=0.95, linewidth=0.8),
                zorder=5)

    # Collapse-threshold annotation: placed in the MIDDLE-LEFT region,
    # below the K7=0.4 label but well clear of the shaded band and of any
    # data curves. Anchor text in white box, arrow points to the threshold.
    ax.annotate(
        "Collapse threshold\n(K\u2087 \u2248 0.45):\ninversion regime\nbreaks down",
        xy=(0.45, 0.05),
        xytext=(0.55, y_top * 0.55),
        fontsize=9, ha="left", color="darkred",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  edgecolor="darkred", alpha=0.92, linewidth=0.7),
        arrowprops=dict(arrowstyle="->", color="darkred", lw=1.2,
                        connectionstyle="arc3,rad=-0.18"),
        zorder=4,
    )

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Knowledge-integration coefficient K\u2087", fontsize=11)
    ax.set_ylabel("Inversion premium\n(% of $200M enterprise value)", fontsize=11)
    ax.set_title("")
    ax.legend(loc="lower right", fontsize=9, framealpha=0.95)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    plt.tight_layout()
    out = FIGURE_DIR / "fig15_layer7_k_sensitivity.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")

    df = pd.DataFrame(rows)
    out_csv = TABLE_DIR / "k_sensitivity_summary.csv"
    df.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv}")


def main():
    make_fig14_knowledge_regime_geometry()
    make_fig15_inversion_under_k()


if __name__ == "__main__":
    main()
