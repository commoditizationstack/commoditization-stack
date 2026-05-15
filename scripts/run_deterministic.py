#!/usr/bin/env python3
"""Run all deterministic simulations and generate paper figures.

Reproduces every figure in de Miranda Neto (2026, working paper).
Outputs go to outputs/figures/ as PNG and outputs/tables/ as CSV.

Usage:
    python scripts/run_deterministic.py
    python scripts/run_deterministic.py --scenario adas_regulated

This script is the single source of truth for all paper figures.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from src.simulation import load_scenario, run_single_simulation
from src.stack_layers import KnowledgeStack
from src.valuation import (
    damodaran_classical_discount,
    damodaran_inverted_discount,
)
from src.hype_cycle import (
    classical_hype_curve,
    post_genai_double_valley_curve,
)
from src.death_valley import (
    classical_cash_trajectory,
    post_genai_double_valley_cash_trajectory,
)


def setup_style():
    plt.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "legend.frameon": False,
    })


def figure_1_layer_velocities(config, outdir):
    """Bar chart of commoditization velocity by layer."""
    stack = KnowledgeStack(config["stack_layers"])
    rows = stack.summary_table()
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    colors = ["#c0392b" if v < 0 else ("#27ae60" if v > 0.15 else "#f39c12")
              for v in df["velocity"]]

    # Use clean short labels on y-axis, full names as text annotations
    short_labels = [
        "L1 train",
        "L1 inference",
        "L2 foundation",
        "L3 capability",
        "L4 codified",
        "L5 hypothesis",
        "L6 institutional",
    ]
    bars = ax.barh(short_labels, df["velocity"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Annual commoditization velocity (logit-shift per year)")
    ax.set_title("")
    ax.invert_yaxis()
    for bar, name, sub in zip(bars, df["name"], df["substitutability_2026"]):
        x = bar.get_width()
        if x >= 0:
            ax.text(x + 0.012, bar.get_y() + bar.get_height() / 2,
                    f"{name}  (s={sub:.2f})",
                    va="center", ha="left", fontsize=8.5)
        else:
            # For negative bars, put label to the right of zero (not overlapping y-tick label)
            ax.text(0.012, bar.get_y() + bar.get_height() / 2,
                    f"{name}  (s={sub:.2f})",
                    va="center", ha="left", fontsize=8.5)
    ax.set_xlim(-0.20, 0.78)
    legend = [
        mpatches.Patch(color="#27ae60", label="Strongly commoditizing"),
        mpatches.Patch(color="#f39c12", label="Weakly commoditizing"),
        mpatches.Patch(color="#c0392b", label="Anti-commoditizing"),
    ]
    ax.legend(handles=legend, loc="lower right")
    plt.tight_layout()
    plt.savefig(outdir / "fig1_layer_velocities.png", bbox_inches="tight")
    plt.close()
    print(f"  saved: fig1_layer_velocities.png")


def figure_2_substitutability_trajectories(config, outdir):
    """Substitutability over time per layer."""
    stack = KnowledgeStack(config["stack_layers"])
    years = np.linspace(0, 8, 33)
    fig, ax = plt.subplots(figsize=(9, 5))
    colors_map = {
        "layer_1_infra_training": "#8e44ad",
        "layer_1_infra_inference": "#2980b9",
        "layer_2_foundation_models": "#16a085",
        "layer_3_capability_access": "#27ae60",
        "layer_4_codified_synthesis": "#d35400",
        "layer_5_hypothesis": "#f39c12",
        "layer_6_institutional": "#c0392b",
    }
    for layer in stack:
        ys = [layer.substitutability_at(y) for y in years]
        ax.plot(years + 2026, ys, label=layer.name,
                color=colors_map.get(layer.layer_id, "gray"), linewidth=2)
    ax.set_xlabel("Year")
    ax.set_ylabel("Substitutability (0..1)")
    ax.set_title("")
    ax.set_ylim(0, 1)
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8)
    plt.tight_layout()
    plt.savefig(outdir / "fig2_substitutability_trajectories.png", bbox_inches="tight")
    plt.close()
    print(f"  saved: fig2_substitutability_trajectories.png")


def figure_3_inverted_keyperson_heatmap(config, outdir):
    """Heatmap: discount sign as a function of layer-4 share x AI substitution."""
    layer3_shares = np.linspace(0.20, 0.90, 36)
    ai_potentials = np.linspace(0.05, 0.95, 36)
    threshold = float(config["valuation"]["damodaran_inverted_threshold_layer4_share"])
    classical_rate = float(config["valuation"]["damodaran_key_person_discount_classical"])
    max_premium = float(config["valuation"]["damodaran_inverted_max_premium"])

    Z = np.zeros((len(ai_potentials), len(layer3_shares)))
    for i, ai in enumerate(ai_potentials):
        for j, l3 in enumerate(layer3_shares):
            _, comp = damodaran_inverted_discount(
                enterprise_value_usd=100_000_000,
                team_layer4_share=l3,
                ai_substitution_potential_layer4=ai,
                threshold_layer4_share=threshold,
                classical_discount_rate=classical_rate,
                max_premium_when_inverted=max_premium,
            )
            Z[i, j] = comp["effective_discount_rate"] * 100

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(Z, aspect="auto", origin="lower",
                   extent=(layer3_shares.min(), layer3_shares.max(),
                           ai_potentials.min(), ai_potentials.max()),
                   cmap="RdBu_r", vmin=-15, vmax=20)
    ax.contour(layer3_shares, ai_potentials, Z, levels=[0],
               colors="black", linewidths=2, linestyles="--")
    ax.axvline(threshold, color="white", linewidth=1, linestyle=":", alpha=0.7)
    ax.text(threshold + 0.005, 0.92, f"  threshold = {threshold:.2f}",
            color="white", fontsize=9)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Effective discount rate (%)\n(positive=classical penalty, negative=inverted premium for acquirer)")
    ax.set_xlabel("Team layer-4 share")
    ax.set_ylabel("Layer-4 AI substitution potential")
    ax.set_title("")
    plt.tight_layout()
    plt.savefig(outdir / "fig3_inverted_keyperson_heatmap.png", bbox_inches="tight")
    plt.close()
    print(f"  saved: fig3_inverted_keyperson_heatmap.png")


def figure_4_hype_cycle_comparison(config, outdir):
    """Classical Gartner vs post-genAI double-valley curve."""
    n = 32
    classical = classical_hype_curve(n_quarters=n,
                                     **config["hype_cycle"]["classical"])
    post = post_genai_double_valley_curve(n_quarters=n,
                                          **config["hype_cycle"]["post_genai"])
    quarters = np.arange(n + 1)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(quarters, classical, label="Classical Hype Cycle (single valley)",
            color="#3498db", linewidth=2.2)
    ax.plot(quarters, post, label="Post-GenAI (double valley)",
            color="#e74c3c", linewidth=2.4)

    # annotate the new commoditization valley
    cv_q = config["hype_cycle"]["post_genai"]["commoditization_valley_quarter"]
    cv_h = config["hype_cycle"]["post_genai"]["commoditization_valley_height"]
    ax.annotate("Commoditization\nValley\n(new)",
                xy=(cv_q, cv_h),
                xytext=(cv_q + 4, cv_h - 12),
                arrowprops=dict(arrowstyle="->", color="black"),
                fontsize=9, ha="center")
    ax.annotate("Classical\nTrough",
                xy=(config["hype_cycle"]["classical"]["trough_quarter"],
                    config["hype_cycle"]["classical"]["trough_height"]),
                xytext=(config["hype_cycle"]["classical"]["trough_quarter"] - 3,
                        config["hype_cycle"]["classical"]["trough_height"] - 8),
                arrowprops=dict(arrowstyle="->", color="black"),
                fontsize=9, ha="center")

    ax.set_xlabel("Quarters since innovation trigger")
    ax.set_ylabel("Expectations (Gartner-style index)")
    ax.set_title("")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 110)
    plt.tight_layout()
    plt.savefig(outdir / "fig4_hype_cycle.png", bbox_inches="tight")
    plt.close()
    print(f"  saved: fig4_hype_cycle.png")


def figure_5_death_valley_comparison(config, outdir):
    """Classical death valley vs post-AI double valley cash curve."""
    classical = classical_cash_trajectory(**config["death_valley"]["classical"]
                                          if False else {})  # use defaults
    post = post_genai_double_valley_cash_trajectory()

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(np.arange(len(classical)), classical / 1e6,
            label="Classical (single valley)", color="#3498db", linewidth=2.2)
    ax.plot(np.arange(len(post)), post / 1e6,
            label="Post-GenAI (double valley)", color="#e74c3c", linewidth=2.4)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.fill_between(np.arange(len(post)), post / 1e6, 0,
                    where=(post < 0), color="red", alpha=0.15,
                    label="Cash crisis zone")
    ax.set_xlabel("Months since founding")
    ax.set_ylabel("Cash (USD millions)")
    ax.set_title("")
    ax.annotate("Series A", xy=(14, 3.0), xytext=(16, 3.5),
                arrowprops=dict(arrowstyle="->", color="gray"), fontsize=8)
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(outdir / "fig5_death_valley.png", bbox_inches="tight")
    plt.close()
    print(f"  saved: fig5_death_valley.png")


def figure_6_arr_trajectories_compared(scenarios, outdir, base_path):
    """ARR trajectories under all four scenarios."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    palette = {"pre_genai_2019": "#3498db",
               "post_genai_2026": "#e74c3c",
               "future_2030": "#9b59b6",
               "adas_regulated": "#27ae60"}
    for sc in scenarios:
        cfg = load_scenario(f"config/scenarios/{sc}.yaml", base_path)
        result = run_single_simulation(cfg)
        months = [h["month"] for h in result.history]
        arrs = [h["arr_usd"] / 1e6 for h in result.history]
        ax.plot(months, arrs, label=sc, color=palette.get(sc, "gray"), linewidth=2)
    ax.set_xlabel("Month since founding")
    ax.set_ylabel("ARR (USD millions)")
    ax.set_title("Figure 6. ARR trajectories under four scenarios")
    ax.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(outdir / "fig6_arr_trajectories.png", bbox_inches="tight")
    plt.close()
    print(f"  saved: fig6_arr_trajectories.png")


def figure_7_valuation_method_comparison(scenarios, outdir, base_path):
    """Bar chart: four valuation methods x four scenarios."""
    rows = []
    for sc in scenarios:
        cfg = load_scenario(f"config/scenarios/{sc}.yaml", base_path)
        result = run_single_simulation(cfg)
        for method, val in result.valuations_at_exit.items():
            rows.append({"scenario": sc, "method": method, "valuation_musd": val / 1e6})
    df = pd.DataFrame(rows)
    pivot = df.pivot(index="scenario", columns="method", values="valuation_musd")
    pivot = pivot[["vc_method", "comparable_multiples",
                   "damodaran_classical", "damodaran_inverted"]]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    pivot.plot(kind="bar", ax=ax, colormap="tab10", edgecolor="black")
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Valuation at exit (USD millions)")
    ax.set_title("Figure 7. Four canonical valuation methods, four scenarios\n"
                 "(post_genai_2026 is the only scenario where Damodaran inverted > classical)")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig(outdir / "fig7_valuation_comparison.png", bbox_inches="tight")
    plt.close()
    print(f"  saved: fig7_valuation_comparison.png")
    # also dump CSV
    pivot.to_csv(outdir.parent / "tables" / "valuations_by_scenario.csv")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="post_genai_2026")
    args = parser.parse_args()

    setup_style()
    base_path = PROJECT_ROOT / "config" / "parameters.yaml"
    sc_path = PROJECT_ROOT / "config" / "scenarios" / f"{args.scenario}.yaml"
    config = load_scenario(sc_path, base_path)

    outdir = PROJECT_ROOT / "outputs" / "figures"
    outdir.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "outputs" / "tables").mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating deterministic figures for scenario: {args.scenario}\n")

    figure_1_layer_velocities(config, outdir)
    figure_2_substitutability_trajectories(config, outdir)
    figure_3_inverted_keyperson_heatmap(config, outdir)
    figure_4_hype_cycle_comparison(config, outdir)
    figure_5_death_valley_comparison(config, outdir)

    all_scenarios = ["pre_genai_2019", "post_genai_2026", "future_2030", "adas_regulated"]
    figure_6_arr_trajectories_compared(all_scenarios, outdir, base_path)
    figure_7_valuation_method_comparison(all_scenarios, outdir, base_path)

    # write deterministic results table
    rows = []
    for sc in all_scenarios:
        cfg = load_scenario(f"{PROJECT_ROOT}/config/scenarios/{sc}.yaml", base_path)
        result = run_single_simulation(cfg)
        rows.append({
            "scenario": sc,
            "survived": result.survived,
            "months_run": result.months_run,
            "final_arr_usd": result.final_arr_usd,
            "final_team_size": result.final_team_size,
            "final_layer3_substitutability": result.final_layer3_substitutability,
            **{f"val_{k}": v for k, v in result.valuations_at_exit.items()},
        })
    pd.DataFrame(rows).to_csv(PROJECT_ROOT / "outputs" / "tables"
                              / "deterministic_results.csv", index=False)
    print(f"\n  saved: outputs/tables/deterministic_results.csv")
    print("\nDone.\n")


if __name__ == "__main__":
    main()
