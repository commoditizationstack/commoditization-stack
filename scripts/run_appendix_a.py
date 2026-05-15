"""Run the Appendix A demonstration: NeuroCertify (deep-tech, regulated)
vs DataFlow Pro (SaaS, commoditizing). Generates three figures and a
comparative table that materialize Section 9 (Appendix A) of the paper
"The Cost Gradient of the Build" (de Miranda Neto, 2026).

Outputs:
    figures/fig16_trl_discount_trajectory.png   - Figure 12 in the paper
    figures/fig17_layer_risk_decomposition.png  - Figure 13 in the paper
    figures/fig18_valuation_comparison.png      - Figure 14 in the paper
    tables/appendix_a_comparative.csv           - the comparative table
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yaml

from src.valuation_layered import (
    LayerExposure,
    LayeredDiscountRateInputs,
    TRLTrajectory,
    CashFlowProjection,
    compute_layered_discount_rate,
    classical_damodaran_dcf,
    layered_dcf,
    trl_premium,
    US_FUNDING_STAGE_BENCHMARKS,
    stage_for_valuation,
)

FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)


def load_scenario(name: str) -> dict:
    path = PROJECT_ROOT / "config" / "scenarios" / f"{name}.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def build_inputs_from_scenario(scn: dict) -> LayeredDiscountRateInputs:
    le = scn["layer_exposure"]
    exposure = LayerExposure(
        layer_1_infra=le["layer_1_infra"],
        layer_2_foundation=le["layer_2_foundation"],
        layer_3_capability=le["layer_3_capability"],
        layer_4_codified=le["layer_4_codified"],
        layer_5_judgment=le["layer_5_judgment"],
        layer_6_institutional=le["layer_6_institutional"],
        layer_7_crossborder=le["layer_7_crossborder"],
    )
    dri = scn["discount_rate_inputs"]
    di = scn["damodaran_industry"]
    return LayeredDiscountRateInputs(
        risk_free_rate=dri["risk_free_rate"],
        equity_risk_premium=dri["equity_risk_premium"],
        industry_unlevered_beta=di["unlevered_beta"],
        de_ratio=di["market_de_ratio"],
        effective_tax_rate=di["effective_tax_rate"],
        trl=scn["trl_trajectory"]["trl_by_year"][0],
        layer_exposure=exposure,
        K7=scn["K7"],
        layer4_substitution_potential=scn["layer4_substitution_potential"],
        sector_label=di["industry_name"],
    )


def run_company(scenario_name: str) -> dict:
    scn = load_scenario(scenario_name)
    inputs = build_inputs_from_scenario(scn)
    trl_traj = TRLTrajectory(
        year_labels=scn["trl_trajectory"]["year_labels"],
        trl_by_year=scn["trl_trajectory"]["trl_by_year"],
    )
    cf = CashFlowProjection(
        year_labels=scn["cash_flows"]["year_labels"],
        fcf_usd=scn["cash_flows"]["fcf_usd"],
    )
    # Classical Damodaran rate (TRL 0 adjustment, no layer premium)
    classical_rate_result = compute_layered_discount_rate(
        LayeredDiscountRateInputs(
            risk_free_rate=inputs.risk_free_rate,
            equity_risk_premium=inputs.equity_risk_premium,
            industry_unlevered_beta=inputs.industry_unlevered_beta,
            de_ratio=inputs.de_ratio,
            effective_tax_rate=inputs.effective_tax_rate,
            trl=9,  # use TRL 9 → 0 premium for the classical comparison
            layer_exposure=LayerExposure(
                layer_1_infra=1/7, layer_2_foundation=1/7, layer_3_capability=1/7,
                layer_4_codified=1/7, layer_5_judgment=1/7, layer_6_institutional=1/7,
                layer_7_crossborder=1/7
            ),  # no layer information used
            K7=1.0, layer4_substitution_potential=0.0,
            sector_label=inputs.sector_label,
        )
    )
    classical_rate = classical_rate_result.base_capm

    # Layered rate at firm's average TRL
    layered_rate_result = compute_layered_discount_rate(inputs)

    # Run both DCFs
    dcf_classical = classical_damodaran_dcf(
        cf, discount_rate=classical_rate, terminal_growth_rate=scn["terminal_growth_rate"],
        sector_label=scn["scenario_name"],
    )
    dcf_layered = layered_dcf(
        cf, inputs=inputs, trl_trajectory=trl_traj,
        terminal_growth_rate=scn["terminal_growth_rate"],
        second_valley_drag=scn["second_valley_drag"],
    )

    # Per-year layered discount rates (for plotting)
    yearly_rates = []
    for trl_y in trl_traj.trl_by_year:
        y_inputs = LayeredDiscountRateInputs(
            risk_free_rate=inputs.risk_free_rate,
            equity_risk_premium=inputs.equity_risk_premium,
            industry_unlevered_beta=inputs.industry_unlevered_beta,
            de_ratio=inputs.de_ratio,
            effective_tax_rate=inputs.effective_tax_rate,
            trl=trl_y,
            layer_exposure=inputs.layer_exposure,
            K7=inputs.K7,
            layer4_substitution_potential=inputs.layer4_substitution_potential,
            sector_label=inputs.sector_label,
        )
        yearly_rates.append(compute_layered_discount_rate(y_inputs).total_discount_rate)

    return {
        "scenario": scn,
        "inputs": inputs,
        "trl_trajectory": trl_traj,
        "cf": cf,
        "classical_rate": classical_rate,
        "classical_rate_result": classical_rate_result,
        "layered_rate_result": layered_rate_result,
        "yearly_rates": yearly_rates,
        "dcf_classical": dcf_classical,
        "dcf_layered": dcf_layered,
    }


# ---------------------------------------------------------------------------
# Figure A1: TRL × discount-rate trajectory (NeuroCertify focus)
# ---------------------------------------------------------------------------
def make_fig_trl_trajectory(neurocertify: dict, dataflow: dict) -> None:
    fig, ax = plt.subplots(figsize=(10, 6.0))

    years_n = neurocertify["trl_trajectory"].year_labels
    rates_n = [r * 100 for r in neurocertify["yearly_rates"]]
    trls_n = neurocertify["trl_trajectory"].trl_by_year

    rates_d = [r * 100 for r in dataflow["yearly_rates"]]
    trls_d = dataflow["trl_trajectory"].trl_by_year

    classical_n = neurocertify["classical_rate"] * 100
    classical_d = dataflow["classical_rate"] * 100

    x = np.arange(len(years_n))

    # Layered (variable) rate trajectory
    ax.plot(x, rates_n, marker="o", linewidth=2.4, color="#0B6E4F",
            label="NeuroCertify - Layered rate (TRL-modulated)")
    ax.plot(x, rates_d, marker="s", linewidth=2.4, color="#C44536",
            label="DataFlow Pro - Layered rate (TRL-modulated)")
    # Classical Damodaran (flat reference lines)
    ax.axhline(classical_n, linestyle="--", color="#0B6E4F", alpha=0.55,
               label=f"NeuroCertify - Classical Damodaran ({classical_n:.1f}%)")
    ax.axhline(classical_d, linestyle="--", color="#C44536", alpha=0.55,
               label=f"DataFlow Pro - Classical Damodaran ({classical_d:.1f}%)")

    # Annotate TRL levels
    for i, (label, trl) in enumerate(zip(years_n, trls_n)):
        ax.annotate(f"TRL {trl}", (i, rates_n[i]), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=9, color="#0B6E4F")
    for i, (label, trl) in enumerate(zip(years_n, trls_d)):
        ax.annotate(f"TRL {trl}", (i, rates_d[i]), textcoords="offset points",
                    xytext=(0, -16), ha="center", fontsize=9, color="#C44536")

    ax.set_xticks(x)
    ax.set_xticklabels(years_n)
    ax.set_xlabel("Year")
    ax.set_ylabel("Discount rate (%)")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", fontsize=9, framealpha=0.92)
    ax.set_title("")

    plt.tight_layout()
    out = FIG_DIR / "fig16_trl_discount_trajectory.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


# ---------------------------------------------------------------------------
# Figure A2: Layer-decomposed risk-premium for both companies
# ---------------------------------------------------------------------------
def make_fig_layer_decomposition(neurocertify: dict, dataflow: dict) -> None:
    layer_labels = ["L1 Infra", "L2 Foundation", "L3 Capability",
                    "L4 Codified", "L5 Judgment", "L6 Institutional",
                    "L7 Crossborder"]
    layer_keys = ["layer_1_infra", "layer_2_foundation", "layer_3_capability",
                  "layer_4_codified", "layer_5_judgment", "layer_6_institutional",
                  "layer_7_crossborder"]

    nc_breakdown = neurocertify["layered_rate_result"].layer_breakdown
    df_breakdown = dataflow["layered_rate_result"].layer_breakdown

    nc_vals = [nc_breakdown[k] * 100 for k in layer_keys]
    df_vals = [df_breakdown[k] * 100 for k in layer_keys]

    y = np.arange(len(layer_labels))
    width = 0.36

    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    bars_n = ax.barh(y - width/2, nc_vals, width, color="#0B6E4F",
                     label="NeuroCertify (deep-tech, HIT)", edgecolor="black", linewidth=0.5)
    bars_d = ax.barh(y + width/2, df_vals, width, color="#C44536",
                     label="DataFlow Pro (Software, commoditizing)",
                     edgecolor="black", linewidth=0.5)

    for bar, val in list(zip(bars_n, nc_vals)) + list(zip(bars_d, df_vals)):
        x_pos = bar.get_width()
        ha = "left" if x_pos >= 0 else "right"
        offset = 0.05 if x_pos >= 0 else -0.05
        ax.text(x_pos + offset, bar.get_y() + bar.get_height()/2,
                f"{val:+.2f}pp", va="center", ha=ha, fontsize=8.5)

    ax.set_yticks(y)
    ax.set_yticklabels(layer_labels)
    ax.set_xlabel("Contribution to firm-specific risk premium (percentage points)")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.invert_yaxis()
    ax.legend(loc="lower right", fontsize=9.5, framealpha=0.92)
    ax.set_title("")

    plt.tight_layout()
    out = FIG_DIR / "fig17_layer_risk_decomposition.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


# ---------------------------------------------------------------------------
# Figure A3: Valuation classical vs layered, with Monte Carlo bands
# ---------------------------------------------------------------------------
def monte_carlo_layered(scn: dict, inputs: LayeredDiscountRateInputs,
                        trl_traj: TRLTrajectory, n_runs: int = 5000) -> np.ndarray:
    """Monte Carlo over the four most uncertain inputs:
       - K7 (cross-border regime)         ~ Normal(scn["K7"], 0.10) clipped [0.3, 1.0]
       - layer4_substitution_potential   ~ Normal(scn[..], 0.10) clipped [0.1, 0.95]
       - terminal_growth_rate            ~ Normal(scn["terminal_growth_rate"], 0.01) clipped [0, 0.06]
       - cash flow shock                 ~ Lognormal(0, 0.20) per year
    """
    rng = np.random.default_rng(seed=42)
    evs = np.empty(n_runs)
    for i in range(n_runs):
        K7 = float(np.clip(rng.normal(scn["K7"], 0.10), 0.3, 1.0))
        sub_pot = float(np.clip(rng.normal(scn["layer4_substitution_potential"], 0.10), 0.1, 0.95))
        g = float(np.clip(rng.normal(scn["terminal_growth_rate"], 0.01), 0.0, 0.06))
        cf_shocks = rng.lognormal(0.0, 0.20, size=len(scn["cash_flows"]["fcf_usd"]))
        cf_perturbed = CashFlowProjection(
            year_labels=scn["cash_flows"]["year_labels"],
            fcf_usd=[float(c) * float(s) for c, s in zip(scn["cash_flows"]["fcf_usd"], cf_shocks)],
        )
        new_inputs = LayeredDiscountRateInputs(
            risk_free_rate=inputs.risk_free_rate,
            equity_risk_premium=inputs.equity_risk_premium,
            industry_unlevered_beta=inputs.industry_unlevered_beta,
            de_ratio=inputs.de_ratio,
            effective_tax_rate=inputs.effective_tax_rate,
            trl=trl_traj.trl_by_year[0],
            layer_exposure=inputs.layer_exposure,
            K7=K7,
            layer4_substitution_potential=sub_pot,
            sector_label=inputs.sector_label,
        )
        result = layered_dcf(
            cf_perturbed, inputs=new_inputs, trl_trajectory=trl_traj,
            terminal_growth_rate=g, second_valley_drag=scn["second_valley_drag"],
        )
        evs[i] = result.enterprise_value_usd
    return evs


def make_fig_valuation_comparison(neurocertify: dict, dataflow: dict) -> None:
    n_runs = 5000

    nc_evs = monte_carlo_layered(
        neurocertify["scenario"], neurocertify["inputs"],
        neurocertify["trl_trajectory"], n_runs=n_runs
    )
    df_evs = monte_carlo_layered(
        dataflow["scenario"], dataflow["inputs"],
        dataflow["trl_trajectory"], n_runs=n_runs
    )

    nc_classical = neurocertify["dcf_classical"].enterprise_value_usd
    nc_layered_pt = neurocertify["dcf_layered"].enterprise_value_usd
    df_classical = dataflow["dcf_classical"].enterprise_value_usd
    df_layered_pt = dataflow["dcf_layered"].enterprise_value_usd

    nc_p10, nc_p50, nc_p90 = np.percentile(nc_evs, [10, 50, 90])
    df_p10, df_p50, df_p90 = np.percentile(df_evs, [10, 50, 90])

    fig, ax = plt.subplots(figsize=(10.5, 6.0))

    companies = ["NeuroCertify\n(deep-tech, HIT)", "DataFlow Pro\n(Software, commoditizing)"]
    x = np.array([0, 1])
    bar_w = 0.28

    # Classical Damodaran (single bar)
    classical_vals = [nc_classical / 1e6, df_classical / 1e6]
    bars_classical = ax.bar(x - bar_w/2, classical_vals, bar_w,
                            color="#7B7D7D", label="Classical Damodaran (single rate)",
                            edgecolor="black", linewidth=0.5)
    # Layered (point estimate) with Monte Carlo error bars
    layered_vals = [nc_layered_pt / 1e6, df_layered_pt / 1e6]
    layered_low = [(nc_p50 - nc_p10) / 1e6, (df_p50 - df_p10) / 1e6]
    layered_high = [(nc_p90 - nc_p50) / 1e6, (df_p90 - df_p50) / 1e6]
    bars_layered = ax.bar(x + bar_w/2, layered_vals, bar_w,
                          yerr=[layered_low, layered_high], capsize=8,
                          color=["#0B6E4F", "#C44536"],
                          label="Layered seven-layer DCF (with MC bands)",
                          edgecolor="black", linewidth=0.5)

    for bar, val in zip(bars_classical, classical_vals):
        ax.text(bar.get_x() + bar.get_width()/2, val + 1.2,
                f"${val:.1f}M", ha="center", fontsize=10)
    for bar, val in zip(bars_layered, layered_vals):
        ax.text(bar.get_x() + bar.get_width()/2, val + 1.2,
                f"${val:.1f}M", ha="center", fontsize=10, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(companies)
    ax.set_ylabel("Enterprise Value (USD millions)")
    ax.legend(loc="upper right", fontsize=9.5)
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.set_title("")
    # Add stage benchmark annotations
    ax.axhline(US_FUNDING_STAGE_BENCHMARKS["seed"]["median_premoney_usd"]/1e6,
               linestyle=":", color="#888", alpha=0.55, linewidth=1)
    ax.axhline(US_FUNDING_STAGE_BENCHMARKS["series_a"]["median_premoney_usd"]/1e6,
               linestyle=":", color="#888", alpha=0.55, linewidth=1)
    ax.axhline(US_FUNDING_STAGE_BENCHMARKS["series_b"]["median_premoney_usd"]/1e6,
               linestyle=":", color="#888", alpha=0.55, linewidth=1)
    # Annotate the stage lines on the right edge
    ax.text(1.55, US_FUNDING_STAGE_BENCHMARKS["seed"]["median_premoney_usd"]/1e6,
            "Seed median (~$16M)", fontsize=8, color="#666", va="center")
    ax.text(1.55, US_FUNDING_STAGE_BENCHMARKS["series_a"]["median_premoney_usd"]/1e6,
            "Series A median (~$49M)", fontsize=8, color="#666", va="center")
    ax.text(1.55, US_FUNDING_STAGE_BENCHMARKS["series_b"]["median_premoney_usd"]/1e6,
            "Series B median (~$119M)", fontsize=8, color="#666", va="center")
    ax.set_xlim(-0.55, 2.0)

    plt.tight_layout()
    out = FIG_DIR / "fig18_valuation_comparison.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


# ---------------------------------------------------------------------------
# Comparative table (CSV)
# ---------------------------------------------------------------------------
def make_comparative_table(neurocertify: dict, dataflow: dict) -> None:
    rows = []
    for label, data in [("NeuroCertify (Deep-tech HIT)", neurocertify),
                        ("DataFlow Pro (Software commoditizing)", dataflow)]:
        scn = data["scenario"]
        di = scn["damodaran_industry"]
        rows.append({
            "Company": label,
            "Damodaran sector": di["industry_name"],
            "Industry unlevered beta (Jan 2026)": f"{di['unlevered_beta']:.2f}",
            "Industry std dev equity": f"{di['std_dev_equity']*100:.1f}%",
            "TRL Y1": scn["trl_trajectory"]["trl_by_year"][0],
            "TRL Y5": scn["trl_trajectory"]["trl_by_year"][-1],
            "Layer-4 share": f"{scn['layer_exposure']['layer_4_codified']*100:.0f}%",
            "Layer-6 share": f"{scn['layer_exposure']['layer_6_institutional']*100:.0f}%",
            "Classical Damodaran rate": f"{data['classical_rate']*100:.2f}%",
            "Layered rate (Y1)": f"{data['yearly_rates'][0]*100:.2f}%",
            "Layered rate (Y5)": f"{data['yearly_rates'][-1]*100:.2f}%",
            "Classical EV (USD)": f"${data['dcf_classical'].enterprise_value_usd:,.0f}",
            "Layered EV (USD)": f"${data['dcf_layered'].enterprise_value_usd:,.0f}",
            "Layered/Classical ratio": f"{data['dcf_layered'].enterprise_value_usd / max(data['dcf_classical'].enterprise_value_usd, 1):.2f}x",
            "Implied funding stage (classical)": stage_for_valuation(data['dcf_classical'].enterprise_value_usd),
            "Implied funding stage (layered)": stage_for_valuation(data['dcf_layered'].enterprise_value_usd),
        })
    df = pd.DataFrame(rows).T
    df.columns = ["NeuroCertify", "DataFlow Pro"]
    out = TABLE_DIR / "appendix_a_comparative.csv"
    df.to_csv(out)
    print(f"Wrote {out}")
    print(df)


def main() -> None:
    print("\nRunning Appendix A — NeuroCertify vs DataFlow Pro\n" + "="*60)
    neurocertify = run_company("neurocertify")
    print(f"  NeuroCertify classical rate: {neurocertify['classical_rate']*100:.2f}%")
    print(f"  NeuroCertify layered rate Y1: {neurocertify['yearly_rates'][0]*100:.2f}%")
    print(f"  NeuroCertify layered rate Y5: {neurocertify['yearly_rates'][-1]*100:.2f}%")
    print(f"  NeuroCertify EV classical: ${neurocertify['dcf_classical'].enterprise_value_usd:,.0f}")
    print(f"  NeuroCertify EV layered:   ${neurocertify['dcf_layered'].enterprise_value_usd:,.0f}")
    print()
    dataflow = run_company("dataflow_pro")
    print(f"  DataFlow Pro classical rate: {dataflow['classical_rate']*100:.2f}%")
    print(f"  DataFlow Pro layered rate Y1: {dataflow['yearly_rates'][0]*100:.2f}%")
    print(f"  DataFlow Pro layered rate Y5: {dataflow['yearly_rates'][-1]*100:.2f}%")
    print(f"  DataFlow Pro EV classical: ${dataflow['dcf_classical'].enterprise_value_usd:,.0f}")
    print(f"  DataFlow Pro EV layered:   ${dataflow['dcf_layered'].enterprise_value_usd:,.0f}")
    print()

    make_fig_trl_trajectory(neurocertify, dataflow)
    make_fig_layer_decomposition(neurocertify, dataflow)
    make_fig_valuation_comparison(neurocertify, dataflow)
    make_comparative_table(neurocertify, dataflow)
    print("\nDone.")


if __name__ == "__main__":
    main()
