"""Generate figures for Appendix G (Distributional, stewardship, epistemic).

Outputs:
    figures/fig40_appendix_g_threshold.png  — Figure G.1 (double threshold)
    figures/fig41_appendix_g_xai_gap.png    — Figure G.2 (XAI capacity gap)
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import matplotlib.pyplot as plt

from src.distributional import (
    compute_double_threshold,
    compute_xai_capacity_gap,
)

FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def make_fig_g1_threshold():
    """Figure G.1: double threshold for AI migration in regulated small firms."""
    d = compute_double_threshold()

    fig, ax = plt.subplots(figsize=(11, 7))

    ax.plot(d.headcount, d.gross_saving_usd / 1000, color="#0B6E4F", linewidth=2.4,
            label="Gross saving from substitution (institution-dominant firm profile)")
    ax.axhline(d.orchestrator_floor_usd / 1000, linestyle="--", color="grey",
                linewidth=1.5, label="Orchestrator overhead floor")
    ax.axhline(d.xai_floor_usd / 1000, linestyle="--", color="#7A1F1F",
                linewidth=1.5, label="Orchestrator overhead + XAI infrastructure floor")

    # Annotate the two thresholds
    ax.axvline(d.economic_break_even, linestyle=":", color="grey", alpha=0.7)
    ax.text(d.economic_break_even + 1, d.orchestrator_floor_usd / 1000 - 30,
            f"Economic threshold\n≈ {d.economic_break_even:.0f} eng.",
            fontsize=9, color="grey")
    ax.axvline(d.compliance_break_even, linestyle=":", color="#7A1F1F", alpha=0.7)
    ax.text(d.compliance_break_even + 1, d.xai_floor_usd / 1000 + 60,
            f"Regulatory-compliance threshold\n≈ {d.compliance_break_even:.0f} eng.",
            fontsize=9, color="#7A1F1F")

    # Shade the gap zone (firms can migrate economically but can't satisfy compliance)
    if d.compliance_break_even > d.economic_break_even:
        ax.axvspan(d.economic_break_even, d.compliance_break_even,
                    alpha=0.15, color="#F5C242",
                    label="Regulatory-compliance gap")
        gap_center = (d.economic_break_even + d.compliance_break_even) / 2
        ax.text(gap_center, 250,
                "Firms in this zone:\ncan migrate economically\n"
                "but cannot satisfy\nregulatory compliance",
                ha="center", fontsize=8.5, color="#7A5C00", style="italic",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="#F5C242", alpha=0.9))

    ax.set_xlabel("Engineering headcount of adopting firm")
    ax.set_ylabel("Annual amount (USD thousands)")
    ax.set_xlim(0, max(d.headcount))
    ax.set_ylim(0, max(d.gross_saving_usd) / 1000 * 1.05)
    ax.set_title("The double threshold for AI migration in regulated small firms",
                 fontsize=11, pad=10)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out = FIG_DIR / "fig40_appendix_g_threshold.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_g2_xai_gap():
    """Figure G.2: XAI capacity gap across two blocs under three K7 regimes."""
    x = compute_xai_capacity_gap()

    fig, ax = plt.subplots(figsize=(12, 7))

    # Three regimes × two blocs = 6 curves
    regimes = [
        ("K = 1.0 (full integration)", x.bloc_a_k1_0, x.bloc_b_k1_0,
         "#0B6E4F", x.endpoint_gaps["k_1_0"]),
        ("K = 0.7 (illustrative current regime)", x.bloc_a_k0_7, x.bloc_b_k0_7,
         "#F5C242", x.endpoint_gaps["k_0_7"]),
        ("K = 0.45 (collapse threshold)", x.bloc_a_k0_45, x.bloc_b_k0_45,
         "#C44536", x.endpoint_gaps["k_0_45"]),
    ]

    for label, bloc_a, bloc_b, color, gap in regimes:
        ax.plot(x.years, bloc_a, color=color, linewidth=2.4,
                label=f"Bloc A — {label}", linestyle="-" if "1.0" in label
                else "--" if "0.7" in label else ":")
        ax.plot(x.years, bloc_b, color=color, linewidth=1.6, alpha=0.55,
                linestyle="-" if "1.0" in label
                else "--" if "0.7" in label else ":")

    # Endpoint gap annotations
    for label, bloc_a, bloc_b, color, gap in regimes:
        ax.annotate("",
                    xy=(x.years[-1] + 0.2, bloc_b[-1]),
                    xytext=(x.years[-1] + 0.2, bloc_a[-1]),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.5))
        ax.text(x.years[-1] + 0.5,
                (bloc_a[-1] + bloc_b[-1]) / 2,
                f"Δ = {gap:.2f}",
                fontsize=9, fontweight="bold", color=color, va="center")

    # Bloc labels at end of curves
    ax.text(x.years[-1] - 0.1, x.bloc_a_k0_45[-1] + 0.02,
            "Bloc A", fontsize=10, color="#1F1F1F", fontweight="bold")
    ax.text(x.years[-1] - 0.1, x.bloc_b_k0_45[-1] - 0.02,
            "Bloc B", fontsize=10, color="#1F1F1F", fontweight="bold",
            va="top")

    # Center annotation: lower K → larger gap
    ax.text(0.50, 0.45,
            "Lower K → larger accumulated gap between blocs over the same time horizon",
            transform=ax.transAxes, ha="center", fontsize=9, color="#7A5C00",
            style="italic",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF5E5",
                      edgecolor="#F5C242", alpha=0.9))

    ax.set_xlabel("Year")
    ax.set_ylabel("XAI capacity index (1.0 = 2026 baseline)")
    ax.set_title("Asymmetric accumulation of XAI capacity across two reference blocs\n"
                 "under three regimes of cross-border knowledge integration",
                 fontsize=11, pad=10)
    ax.legend(loc="upper left", fontsize=8.5, framealpha=0.92)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)

    plt.tight_layout()
    out = FIG_DIR / "fig41_appendix_g_xai_gap.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def main():
    print("\nGenerating Appendix G figures (distributional + XAI capacity gap)\n" + "=" * 60)
    make_fig_g1_threshold()
    make_fig_g2_xai_gap()
    print("\nDone.")


if __name__ == "__main__":
    main()
