#!/usr/bin/env python3
"""Run Monte Carlo ensemble across all four scenarios.

Default: 10,000 runs per scenario. Outputs distributional figures and
summary tables.

Usage:
    python scripts/run_monte_carlo.py
    python scripts/run_monte_carlo.py --runs 5000
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
import seaborn as sns

from src.simulation import load_scenario, run_monte_carlo, monte_carlo_summary


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


def figure_8_survival_rates(all_results: dict, outdir: Path):
    """Bar chart: survival rate by scenario."""
    rows = []
    for scenario_name, df in all_results.items():
        rows.append({
            "scenario": scenario_name,
            "survival_rate": df["survived"].mean(),
            "n_runs": len(df),
        })
    sdf = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    colors = ["#3498db", "#e74c3c", "#9b59b6", "#27ae60"]
    bars = ax.bar(sdf["scenario"], sdf["survival_rate"] * 100,
                  color=colors[:len(sdf)], edgecolor="black")
    ax.set_ylabel("Survival rate (%)")
    ax.set_title("")
    ax.set_ylim(0, max(sdf["survival_rate"].max() * 110, 30))
    for bar, rate in zip(bars, sdf["survival_rate"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{rate * 100:.1f}%", ha="center", fontsize=9)
    plt.xticks(rotation=10)
    plt.tight_layout()
    plt.savefig(outdir / "fig8_survival_rates.png", bbox_inches="tight")
    plt.close()
    print(f"  saved: fig8_survival_rates.png")


def figure_9_valuation_distributions(all_results: dict, outdir: Path):
    """Distribution of valuations per method per scenario (only survived)."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharey=True)
    methods = ["valuation_vc_method", "valuation_comparable_multiples",
               "valuation_damodaran_classical", "valuation_damodaran_inverted"]
    titles = ["VC method", "Comparable multiples",
              "Damodaran (classical)", "Damodaran (inverted)"]

    for ax, m, title in zip(axes.flatten(), methods, titles):
        for sc, df in all_results.items():
            survived = df[df["survived"]]
            if len(survived) > 10:
                vals = np.log10(np.clip(survived[m].values, 1, None))
                ax.hist(vals, bins=40, alpha=0.5, label=sc)
        ax.set_xlabel("log10(valuation USD)")
        ax.set_ylabel("Count (survivors only)")
        ax.set_title(title)
        ax.legend(fontsize=8)

    fig.suptitle("Figure 9. Monte Carlo distributions of valuation, by method and scenario",
                 fontsize=12)
    plt.tight_layout()
    plt.savefig(outdir / "fig9_valuation_distributions.png", bbox_inches="tight")
    plt.close()
    print(f"  saved: fig9_valuation_distributions.png")


def figure_10_keyperson_inversion_distribution(all_results: dict, outdir: Path):
    """Histogram: damodaran_inverted - damodaran_classical, per scenario."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    palette = {"pre_genai_2019": "#3498db",
               "post_genai_2026": "#e74c3c",
               "future_2030": "#9b59b6",
               "adas_regulated": "#27ae60"}
    for sc, df in all_results.items():
        survived = df[df["survived"]]
        if len(survived) < 10:
            continue
        diff_pct = 100 * (survived["valuation_damodaran_inverted"]
                          - survived["valuation_damodaran_classical"]) / np.clip(
            survived["valuation_damodaran_classical"], 1, None)
        ax.hist(diff_pct, bins=40, alpha=0.55, color=palette.get(sc, "gray"),
                label=f"{sc} (median={diff_pct.median():.1f}%)")
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Damodaran inverted vs classical, percentage difference")
    ax.set_ylabel("Count (survivors)")
    ax.set_title("Figure 10. Distribution of the inversion premium across Monte Carlo runs\n"
                 "(positive values = inverted method yields higher valuation than classical)")
    ax.legend(loc="upper right", fontsize=9)
    plt.tight_layout()
    plt.savefig(outdir / "fig10_keyperson_inversion_distribution.png", bbox_inches="tight")
    plt.close()
    print(f"  saved: fig10_keyperson_inversion_distribution.png")


def figure_11_monte_carlo_summary_table(all_results: dict, outdir: Path):
    """Generate a summary CSV and a printable table image."""
    rows = []
    for sc, df in all_results.items():
        survived = df[df["survived"]]
        row = {
            "scenario": sc,
            "n_runs": len(df),
            "survival_rate_pct": 100 * df["survived"].mean(),
            "median_arr_usd": survived["final_arr_usd"].median() if len(survived) else 0,
            "median_team_size": survived["final_team_size"].median() if len(survived) else 0,
            "median_val_classical_musd": survived["valuation_damodaran_classical"].median() / 1e6
                if len(survived) else 0,
            "median_val_inverted_musd": survived["valuation_damodaran_inverted"].median() / 1e6
                if len(survived) else 0,
        }
        if len(survived) > 0:
            diff = (survived["valuation_damodaran_inverted"]
                    - survived["valuation_damodaran_classical"])
            row["median_inversion_diff_musd"] = diff.median() / 1e6
            row["median_inversion_diff_pct"] = 100 * diff.median() / max(
                survived["valuation_damodaran_classical"].median(), 1.0)
            row["pct_runs_with_positive_inversion"] = 100 * (diff > 0).mean()
        rows.append(row)

    summary = pd.DataFrame(rows)
    summary.to_csv(outdir.parent / "tables" / "monte_carlo_summary.csv", index=False)
    print(f"  saved: tables/monte_carlo_summary.csv")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=None)
    args = parser.parse_args()

    setup_style()

    base_path = PROJECT_ROOT / "config" / "parameters.yaml"
    scenarios = ["pre_genai_2019", "post_genai_2026", "future_2030", "adas_regulated"]
    outdir = PROJECT_ROOT / "outputs" / "figures"
    outdir.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "outputs" / "tables").mkdir(parents=True, exist_ok=True)

    all_results = {}
    for sc in scenarios:
        sc_path = PROJECT_ROOT / "config" / "scenarios" / f"{sc}.yaml"
        config = load_scenario(sc_path, base_path)
        if args.runs:
            config["simulation"]["monte_carlo_runs"] = args.runs
        n_runs = int(config["simulation"]["monte_carlo_runs"])
        print(f"\n[{sc}] Running {n_runs:,} Monte Carlo iterations...")
        df = run_monte_carlo(config, n_runs=n_runs, show_progress=False)
        all_results[sc] = df
        df.to_csv(PROJECT_ROOT / "outputs" / "tables" / f"mc_runs_{sc}.csv",
                  index=False)
        print(f"  Survival rate: {100 * df['survived'].mean():.1f}%")

    print("\nGenerating Monte Carlo figures...\n")
    figure_8_survival_rates(all_results, outdir)
    figure_9_valuation_distributions(all_results, outdir)
    figure_10_keyperson_inversion_distribution(all_results, outdir)
    summary = figure_11_monte_carlo_summary_table(all_results, outdir)

    print("\n=== Monte Carlo summary ===")
    print(summary.to_string(index=False))
    print("\nDone.\n")


if __name__ == "__main__":
    main()
