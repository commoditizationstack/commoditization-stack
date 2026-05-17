"""Generate figures for Appendix F (Upstream value chain + sensitivities).

Outputs:
    figures/fig36_appendix_f_scope.png        — Figure F.1 (framework scope)
    figures/fig37_appendix_f_mapping.png      — Figure F.2 (7 categories × 7 layers)
    figures/fig38_appendix_f_sensitivities.png — Figure F.3 (3-panel sensitivities)
    figures/fig39_appendix_f_asymmetries.png  — Figure F.4 (recovery asymmetries)
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from src import config
from src.upstream_chain import (
    all_categories,
    capex_sensitivity_curves,
    adoption_threshold_curves,
    k7_sensitivity_per_jurisdiction,
)

FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def make_fig_f1_scope():
    """Figure F.1: scope of the framework (what it prices vs what it doesn't)."""
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.axis("off")

    # Two columns: prices vs does not price
    prices = [
        "Layer-by-layer decomposition of firm value",
        "Substitutability of technical labor by AI services",
        "Jurisdictional structure of substitution NPV",
        "TRL trajectory and discount-rate evolution",
        "Phase-conditional CAPM, WACC, EVA, Gordon",
        "Layer-decomposed firm-specific risk premium",
        "Defensibility migration upward through stack",
        "Cross-border knowledge regime (tentative)",
    ]
    not_prices = [
        "Systemic risk-off shocks across asset classes",
        "Private credit cycle and leverage dynamics",
        "Cross-asset flows and liquidity premia",
        "Concentration risk at index level",
        "Monetary policy regime transitions",
        "Speculative narrative and reflexivity effects",
        "Timing of macro events or regime changes",
        "Probabilistic forecasts of any kind",
    ]

    # Left column (prices) — green tones
    ax.text(0.25, 0.92, "What the framework prices", ha="center",
            fontsize=14, fontweight="bold", color="#1F5040",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#E5F5E5",
                      edgecolor="#0B6E4F", linewidth=1.5))
    ax.text(0.25, 0.86, "(structural, firm-level, microeconomic)",
            ha="center", fontsize=9, style="italic", color="#1F5040")
    for i, item in enumerate(prices):
        ax.text(0.05, 0.80 - i * 0.07, "•", fontsize=14, color="#0B6E4F")
        ax.text(0.08, 0.80 - i * 0.07, item, fontsize=10, color="#1F1F1F",
                va="center")

    # Right column (does not price) — red tones
    ax.text(0.75, 0.92, "What the framework does NOT price",
            ha="center", fontsize=14, fontweight="bold", color="#7A1F1F",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFE5E5",
                      edgecolor="#C44536", linewidth=1.5))
    ax.text(0.75, 0.86, "(systemic, macro-prudential, cyclical)",
            ha="center", fontsize=9, style="italic", color="#7A1F1F")
    for i, item in enumerate(not_prices):
        ax.text(0.55, 0.80 - i * 0.07, "•", fontsize=14, color="#C44536")
        ax.text(0.58, 0.80 - i * 0.07, item, fontsize=10, color="#1F1F1F",
                va="center")

    # Bottom note
    ax.text(0.5, 0.05,
            "Structural-microeconomic, timing-agnostic. "
            "Macro-prudential dimensions interact with the framework "
            "but are not modeled by it.",
            ha="center", fontsize=9, style="italic", color="#555555",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#F5F5F5",
                      edgecolor="grey", alpha=0.9))

    plt.tight_layout()
    out = FIG_DIR / "fig36_appendix_f_scope.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_f2_mapping():
    """Figure F.2: 7 upstream categories × 7 layers exposure matrix."""
    cats = all_categories()
    layers = ["L1 train\n(cumul.)", "L1 infer\n(margin.)", "L2\nfoundation",
              "L3\ncapability", "L4\ncodified", "L5\njudgment", "L6\ninstitut."]
    layer_keys = ["L1_train", "L1_infer", "L2", "L3", "L4", "L5", "L6"]

    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.axis("off")

    # Matrix of exposure values
    n_cats = len(cats)
    n_layers = len(layers)
    cell_w = 0.10
    cell_h = 0.08
    matrix_x = 0.30
    matrix_y = 0.85

    # Header row: layer names
    ax.text(0.05, matrix_y + cell_h * 0.5, "Upstream firm category",
            fontsize=10, fontweight="bold", va="center")
    for j, layer in enumerate(layers):
        ax.text(matrix_x + (j + 0.5) * cell_w, matrix_y + cell_h * 0.5,
                layer, ha="center", va="center", fontsize=8, fontweight="bold")

    # Body rows
    for i, cat in enumerate(cats):
        y = matrix_y - (i + 1) * cell_h
        ax.text(0.05, y + cell_h * 0.5, cat.label, fontsize=8.5, va="center")
        for j, key in enumerate(layer_keys):
            exposure = cat.exposure.get(key, 0)
            x = matrix_x + j * cell_w
            # Draw circles based on exposure level
            if exposure == 3:
                ax.add_patch(plt.Circle((x + cell_w * 0.5, y + cell_h * 0.5),
                                          0.018, color="#0B6E4F"))
                ax.add_patch(plt.Circle((x + cell_w * 0.5 - 0.025, y + cell_h * 0.5),
                                          0.018, color="#0B6E4F"))
                ax.add_patch(plt.Circle((x + cell_w * 0.5 + 0.025, y + cell_h * 0.5),
                                          0.018, color="#0B6E4F"))
            elif exposure == 2:
                ax.add_patch(plt.Circle((x + cell_w * 0.5 - 0.012, y + cell_h * 0.5),
                                          0.016, color="#F5C242"))
                ax.add_patch(plt.Circle((x + cell_w * 0.5 + 0.012, y + cell_h * 0.5),
                                          0.016, color="#F5C242"))
            elif exposure == 1:
                ax.add_patch(plt.Circle((x + cell_w * 0.5, y + cell_h * 0.5),
                                          0.014, color="#B0DCC2"))

    # Legend
    legend_y = matrix_y - (n_cats + 2) * cell_h
    ax.text(0.05, legend_y, "Legend:", fontsize=10, fontweight="bold")
    legend_items = [
        ("#0B6E4F", "Predominant exposure", 0.18),
        ("#F5C242", "Secondary exposure", 0.40),
        ("#B0DCC2", "Marginal exposure", 0.62),
    ]
    for color, text, x_pos in legend_items:
        ax.add_patch(plt.Circle((x_pos, legend_y + 0.005), 0.012, color=color))
        ax.text(x_pos + 0.02, legend_y, text, fontsize=9, va="center")

    # Structural sensitivities below the matrix
    note_y = legend_y - 0.04
    ax.text(0.05, note_y, "Structural sensitivities implied by each row:",
            fontsize=9, fontweight="bold")
    sens_items = [
        "• Foundry pure-plays and training silicon: sensitive to training-capex cycle + financing conditions.",
        "• Inference & edge silicon: sensitive to aggregate Layer-4 adoption (subject to team-size adoption threshold).",
        "• Hyperscalers: dual exposure (capacity supply + capability access); structurally insulated by scale + switching costs.",
        "• Frontier labs: anti-commoditizing on training side; sensitive to the cross-border knowledge regime.",
        "• AI-tooling platforms: most exposed to Layer-4 commoditization themselves (recursive feedback into Layer 4).",
    ]
    for i, item in enumerate(sens_items):
        ax.text(0.05, note_y - 0.025 - i * 0.025, item, fontsize=8, color="#1F1F1F")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("Mapping of seven categories of upstream AI value-chain firms "
                 "onto the seven-layer framework",
                 fontsize=11, pad=10)

    plt.tight_layout()
    out = FIG_DIR / "fig37_appendix_f_mapping.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_f3_sensitivities():
    """Figure F.3: three structural sensitivities in three panels.

    Layout: Panel A and Panel B side-by-side on top, Panel C spanning the
    full width below. Built with GridSpec so tight_layout doesn't collide
    with manual positioning.
    """
    from matplotlib.gridspec import GridSpec
    fig = plt.figure(figsize=(14, 11))
    gs = GridSpec(2, 2, figure=fig, hspace=0.40, wspace=0.25,
                  left=0.07, right=0.97, top=0.93, bottom=0.07)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])

    # Panel A: capex sensitivity to financing
    ax = ax_a
    t, train, infer = capex_sensitivity_curves()
    cs = config.load_parameters()["upstream_chain"]["capex_sensitivity"]
    ax.plot(t, train, color="#C44536", linewidth=2.4,
            label="Training compute (cumulative)")
    ax.plot(t, infer, color="#0B6E4F", linewidth=2.4,
            label="Inference compute (marginal)")
    ax.axvspan(0, float(cs["loose_credit_threshold"]),
                alpha=0.10, color="#0B6E4F")
    ax.text(0.10, 60, "Loose\ncredit", fontsize=8, color="#0B6E4F",
            style="italic", ha="center")
    ax.axvspan(float(cs["tight_credit_threshold"]), 1.0,
                alpha=0.10, color="#C44536")
    ax.text(0.85, 60, "Tight\ncredit", fontsize=8, color="#7A1F1F",
            style="italic", ha="center")
    ax.set_xlabel("Financing tightness (private credit + rate environment)")
    ax.set_ylabel("Capex index (100 = current)")
    ax.set_title("Panel A — Capex sensitivity to financing", fontsize=11, pad=8)
    ax.legend(loc="lower left", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_ylim(30, 105)

    # Panel B: adoption threshold
    ax = ax_b
    curves = adoption_threshold_curves()
    ax.plot(curves["headcount"], curves["l4_heavy_saving_usd"] / 1000,
            color="#C44536", linewidth=2.4, label="Gross saving — L4-heavy firm")
    ax.plot(curves["headcount"], curves["l6_rich_saving_usd"] / 1000,
            color="#2C5282", linewidth=2.4, label="Gross saving — L6-rich firm")
    ax.plot(curves["headcount"], curves["orchestrator_floor_usd"] / 1000,
            color="grey", linewidth=1.2, linestyle="--",
            label="Orchestrator overhead floor")
    # Threshold lines
    di = config.load_parameters()["distributional"]["double_threshold"]
    l4_thresh = float(di["orchestrator_overhead_floor_usd"]) / (
        float(curves["l4_heavy_saving_usd"][1] / curves["headcount"][1]))
    l6_thresh = float(di["orchestrator_overhead_floor_usd"]) / (
        float(curves["l6_rich_saving_usd"][1] / curves["headcount"][1]))
    ax.axvline(l4_thresh, color="#C44536", linestyle=":", alpha=0.7)
    ax.text(l4_thresh + 1, 1300, f"L4-heavy threshold\n≈ {l4_thresh:.0f} eng.",
            fontsize=8, color="#7A1F1F")
    ax.axvline(l6_thresh, color="#2C5282", linestyle=":", alpha=0.7)
    ax.text(l6_thresh + 1, 1100, f"L6-rich threshold\n≈ {l6_thresh:.0f} eng.",
            fontsize=8, color="#1F3A6A")
    ax.set_xlabel("Engineering headcount of adopting firm")
    ax.set_ylabel("Annual amount (USD thousands)")
    ax.set_title("Panel B — Adoption threshold for migration", fontsize=11, pad=8)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_ylim(0, 1500)
    ax.set_xlim(0, 100)

    # Panel C: K7 sensitivity per jurisdiction (spans bottom row)
    ax = ax_c

    k7 = k7_sensitivity_per_jurisdiction()
    k_grid = k7["k_grid"]
    ax.plot(k_grid, k7["united_states_same_bloc"] * 100, color="#2C5282",
            linewidth=2.2, label="United States (same-bloc)")
    ax.plot(k_grid, k7["france_same_bloc"] * 100, color="#F5C242",
            linewidth=2.2, label="France (same-bloc)")
    ax.plot(k_grid, k7["brazil_same_bloc"] * 100, color="#0B6E4F",
            linewidth=2.2, label="Brazil (same-bloc)")
    ax.plot(k_grid, k7["united_states_cross_bloc"] * 100, color="#8E44AD",
            linewidth=2.2, linestyle="--",
            label="United States (cross-bloc)")
    # Collapse threshold
    ax.axvspan(0.0, 0.45, alpha=0.10, color="#C44536")
    ax.axvline(0.45, color="#C44536", linewidth=1.2, linestyle=":")
    ax.set_xlabel("Knowledge-integration coefficient K₇")
    ax.set_ylabel("Inversion premium (% of EV)")
    ax.set_title("Panel C — Inversion premium sensitivity to\n"
                 "the cross-border knowledge regime",
                 fontsize=11, pad=8)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_xlim(0.2, 1.0)
    ax.set_ylim(0, 4.5)

    fig.suptitle("Three structural sensitivities the framework illuminates",
                 fontsize=13, fontweight="bold", y=0.985)
    out = FIG_DIR / "fig38_appendix_f_sensitivities.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


def make_fig_f4_asymmetries():
    """Figure F.4: recovery composition asymmetries under structural recalibration."""
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

    # Top: trigger box
    ax.add_patch(mpatches.FancyBboxPatch((3.5, 8.7), 3, 0.8,
                                          boxstyle="round,pad=0.1",
                                          facecolor="#F5F5F5",
                                          edgecolor="grey", linewidth=1.5))
    ax.text(5, 9.3, "Structural recalibration occurs",
            ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(5, 8.9, "(any cause: macro shock, knowledge-regime fragmentation,\n"
                    "financing tightening, adoption ceiling)",
            ha="center", va="center", fontsize=8, style="italic", color="#555555")

    # Three downstream paths
    paths = [
        (1.5, "Semiconductor recovery\nsplits into two velocities",
         ["• Training-capex players (cumulative compute):",
          "  slow recovery, permanent multiple compression",
          "• Inference & edge silicon (marginal compute):",
          "  faster recovery, sustained by aggregate demand",
          "• Memory & HBM: tracks training-capex side"], "#C44536"),
        (5, "Cross-firm asymmetry\nby layer profile",
         ["• Institution-rich firms:",
          "  lead recovery — classical under-pricing reverses",
          "• Codified-work-heavy firms:",
          "  lag recovery — multiples remain compressed",
          "• Survivors migrate upward through the stack"], "#0B6E4F"),
        (8.5, "Jurisdictional &\ncross-border recomposition",
         ["• Inversion premium ordering preserved (US>FR>BR)",
          "  but absolute magnitudes attenuated",
          "• Knowledge regime contracting:",
          "  uniform contraction of inversion premium",
          "• Cross-bloc M&A structurally less value-creating"], "#8E44AD"),
    ]

    for x_center, title, bullets, color in paths:
        # Title box
        ax.add_patch(mpatches.FancyBboxPatch((x_center - 1.4, 6.5), 2.8, 1.0,
                                              boxstyle="round,pad=0.1",
                                              facecolor="white",
                                              edgecolor=color, linewidth=2))
        ax.text(x_center, 7.0, title, ha="center", va="center",
                fontsize=10, fontweight="bold", color=color)
        # Bullets
        for i, b in enumerate(bullets):
            ax.text(x_center - 1.3, 5.9 - i * 0.35, b, fontsize=7.5,
                    va="top", color="#1F1F1F")
        # Arrow from trigger
        ax.annotate("", xy=(x_center, 7.5), xytext=(5, 8.7),
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.5))

    # Cross-cutting predictions box at bottom
    ax.add_patch(mpatches.FancyBboxPatch((0.5, 1.5), 9, 2.0,
                                          boxstyle="round,pad=0.1",
                                          facecolor="#FFF9E5",
                                          edgecolor="#F5C242", linewidth=1.5))
    ax.text(5, 3.2, "Cross-cutting structural predictions",
            ha="center", fontsize=11, fontweight="bold", color="#7A5C00")
    cross_cuts = [
        "• Dispersion across firms within indices increases during recalibration — fragility profile becomes a better predictor of drawdown than sector beta.",
        "• Recovery composition is structurally different from pre-recalibration composition; the \"winners\" of the recovery are not the same firms that led the prior expansion.",
        "• Firms that already migrated to AI-augmented operations carry residual vendor-concentration exposure that materializes if the knowledge regime also recalibrates.",
    ]
    for i, item in enumerate(cross_cuts):
        ax.text(0.8, 2.7 - i * 0.35, item, fontsize=8.5, color="#1F1F1F")

    # Intellectual posture footer
    ax.add_patch(mpatches.FancyBboxPatch((0.5, 0.2), 9, 1.0,
                                          boxstyle="round,pad=0.1",
                                          facecolor="#F5F5F5",
                                          edgecolor="grey", linewidth=1,
                                          linestyle="--"))
    ax.text(5, 0.95, "Intellectual posture", ha="center", fontsize=9,
            fontweight="bold", color="#555555")
    ax.text(5, 0.65,
            "The framework does not forecast whether or when a structural recalibration occurs.\n"
            "It articulates conditional asymmetries that follow from the layered decomposition if a recalibration materializes.\n"
            "Each prediction is testable post-hoc; the framework will survive or not depending on emergent evidence.",
            ha="center", va="top", fontsize=8, style="italic", color="#555555")

    plt.tight_layout()
    out = FIG_DIR / "fig39_appendix_f_asymmetries.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def main():
    print("\nGenerating Appendix F figures (upstream chain + sensitivities)\n" + "=" * 60)
    make_fig_f1_scope()
    make_fig_f2_mapping()
    make_fig_f3_sensitivities()
    make_fig_f4_asymmetries()
    print("\nDone.")


if __name__ == "__main__":
    main()
