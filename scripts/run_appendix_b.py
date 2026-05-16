"""Run the Appendix B demonstration: two-phase reformulation of CAPM,
WACC, EVA, and Gordon perpetuity applied to NeuroCertify and DataFlow Pro.

Outputs:
    figures/fig19_two_phase_cost_of_capital.png   - Figure 15 in the paper
    figures/fig20_two_phase_eva_trajectory.png    - Figure 16 in the paper
    tables/appendix_b_comparative.csv             - phase-by-phase numbers
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src import config
from src.valuation_two_phase import (
    PhaseParameters,
    two_phase_capm,
    two_phase_wacc,
    two_phase_dcf,
    two_phase_eva,
    two_phase_roi,
    classical_capm,
    classical_wacc,
)

FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Firm calibrations and macro come from config/parameters.yaml
# (section firms_appendix_b). NeuroCertify is defensibility-rich (Layer 6
# protects); DataFlow Pro is Layer-4-heavy (severe second-valley beta jump).
# Damodaran (Jan 2026) industry data: HIT unlevered beta 0.99 D/E 15.74% tax 6.38%;
# Software (S&A) unlevered beta 1.23 D/E 5.58% tax 5.51%.
# ---------------------------------------------------------------------------

_FIRMS = config.firms_appendix_b()


def _phases_from_yaml(slug: str) -> PhaseParameters:
    p = _FIRMS[slug]["phases"]
    return PhaseParameters(
        phase_1_end_year=int(p["phase_1_end_year"]),
        phase_2_end_year=int(p["phase_2_end_year"]),
        beta_unlevered_phase_1=float(p["beta_unlevered_phase_1"]),
        beta_unlevered_phase_2=float(p["beta_unlevered_phase_2"]),
        beta_unlevered_phase_3=float(p["beta_unlevered_phase_3"]),
        de_ratio_phase_1=float(p["de_ratio_phase_1"]),
        de_ratio_phase_2=float(p["de_ratio_phase_2"]),
        de_ratio_phase_3=float(p["de_ratio_phase_3"]),
        kd_spread_phase_1=float(p["kd_spread_phase_1"]),
        kd_spread_phase_2=float(p["kd_spread_phase_2"]),
        kd_spread_phase_3=float(p["kd_spread_phase_3"]),
        effective_tax_rate=float(p["effective_tax_rate"]),
    )


NEUROCERTIFY_PHASES = _phases_from_yaml("neurocertify")
NEUROCERTIFY_FCF = list(_FIRMS["neurocertify"]["fcf_usd"])
NEUROCERTIFY_INVESTED_CAPITAL = list(_FIRMS["neurocertify"]["invested_capital_usd"])
NEUROCERTIFY_NOPAT = list(_FIRMS["neurocertify"]["nopat_usd"])
NEUROCERTIFY_LABEL = str(_FIRMS["neurocertify"]["label"])
NEUROCERTIFY_DRAG = float(_FIRMS["neurocertify"]["second_valley_drag"])

DATAFLOW_PHASES = _phases_from_yaml("dataflow")
DATAFLOW_FCF = list(_FIRMS["dataflow"]["fcf_usd"])
DATAFLOW_INVESTED_CAPITAL = list(_FIRMS["dataflow"]["invested_capital_usd"])
DATAFLOW_NOPAT = list(_FIRMS["dataflow"]["nopat_usd"])
DATAFLOW_LABEL = str(_FIRMS["dataflow"]["label"])
DATAFLOW_DRAG = float(_FIRMS["dataflow"]["second_valley_drag"])

# Common macro (from YAML)
RF = float(_FIRMS["macro"]["risk_free_rate"])
ERP = float(_FIRMS["macro"]["equity_risk_premium"])
TERMINAL_GROWTH = float(_FIRMS["macro"]["terminal_growth"])


def run_company(name: str, phases: PhaseParameters, fcf, ic, nopat,
                terminal_growth: float, second_valley_drag: float):
    n_years = len(fcf)
    yearly_data = []
    for t in range(1, n_years + 1):
        ke = two_phase_capm(t, RF, ERP, phases)
        wacc_d = two_phase_wacc(t, RF, ERP, phases)
        eva_d = two_phase_eva(nopat[t-1], ic[t-1], t, RF, ERP, phases)
        roi_d = two_phase_roi(nopat[t-1], ic[t-1], t, RF, ERP, phases)
        yearly_data.append({
            "year": t,
            "phase": phases.phase_for_year(t),
            "ke": ke,
            "wacc": wacc_d["wacc"],
            "kd": wacc_d["kd"],
            "beta_u": phases.beta_for_year(t),
            "de_ratio": phases.de_ratio_for_year(t),
            "nopat": nopat[t-1],
            "ic": ic[t-1],
            "eva": eva_d["eva"],
            "roi": roi_d["roi"],
            "spread": roi_d["spread"],
        })
    # Two-phase DCF
    dcf = two_phase_dcf(fcf, RF, ERP, phases, terminal_growth, second_valley_drag)

    # Classical comparator: use Phase 1 parameters as the "single rate"
    classical_wacc_val = classical_wacc(
        RF, ERP,
        phases.beta_unlevered_phase_1,
        phases.de_ratio_phase_1,
        phases.effective_tax_rate,
        phases.kd_spread_phase_1,
    )
    # Classical EVA per year (same WACC throughout)
    classical_eva = []
    for t in range(1, n_years + 1):
        classical_eva.append(nopat[t-1] - classical_wacc_val * ic[t-1])

    return {
        "name": name,
        "yearly": yearly_data,
        "dcf": dcf,
        "classical_wacc": classical_wacc_val,
        "classical_eva_by_year": classical_eva,
    }


def make_fig_cost_of_capital(neurocertify, dataflow):
    """Figure 15: Two-phase WACC and Ke trajectory for both companies."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)

    # First pass: plot to establish y-limits
    for ax, data, color, marker in [
        (axes[0], neurocertify, "#0B6E4F", "o"),
        (axes[1], dataflow, "#C44536", "s"),
    ]:
        years = [y["year"] for y in data["yearly"]]
        wacc = [y["wacc"] * 100 for y in data["yearly"]]
        ke = [y["ke"] * 100 for y in data["yearly"]]
        classical_w = data["classical_wacc"] * 100

        # Phase regions
        ax.axvspan(0.5, 2.5, alpha=0.10, color="#888")
        ax.axvspan(2.5, 4.5, alpha=0.20, color="#C44536")
        ax.axvspan(4.5, 5.5, alpha=0.10, color="#0B6E4F")

        # Plot WACC and Ke
        ax.plot(years, wacc, marker=marker, color=color, linewidth=2.5,
                label=f"Two-phase WACC")
        ax.plot(years, ke, marker=marker, color=color, linewidth=1.5,
                linestyle="--", alpha=0.65, label=f"Two-phase Ke")
        ax.axhline(classical_w, linestyle=":", color="#7B7D7D", linewidth=1.5,
                   label=f"Classical single-rate WACC ({classical_w:.2f}%)")

        ax.set_xticks(years)
        ax.set_xlabel("Year")
        if ax is axes[0]:
            ax.set_ylabel("Cost of capital (%)")
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.set_axisbelow(True)
        ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92)
        ax.set_title(data["name"], fontsize=11, pad=10)
        ax.set_xlim(0.5, 5.5)

    # Second pass: now that y-limits are set, add Phase labels INSIDE each axes
    for ax in axes:
        ymin, ymax = ax.get_ylim()
        # Expand top by 10% to give room for labels
        ax.set_ylim(ymin, ymax + (ymax - ymin) * 0.15)
        ymin2, ymax2 = ax.get_ylim()
        label_y = ymax2 - (ymax2 - ymin2) * 0.06
        ax.text(1.5, label_y, "Phase 1\n(growth)", ha="center", fontsize=8.5,
                color="#555", style="italic", va="top")
        ax.text(3.5, label_y, "Phase 2\n(2nd valley)", ha="center", fontsize=8.5,
                color="#8B0000", style="italic", va="top")
        ax.text(5.0, label_y, "Phase 3\n(terminal)", ha="center", fontsize=8.5,
                color="#0B6E4F", style="italic", va="top")

    plt.tight_layout()
    out = FIG_DIR / "fig19_two_phase_cost_of_capital.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_fig_eva_trajectory(neurocertify, dataflow):
    """Figure 16: Two-phase EVA vs classical single-WACC EVA."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=False)

    for ax, data, color in [
        (axes[0], neurocertify, "#0B6E4F"),
        (axes[1], dataflow, "#C44536"),
    ]:
        years = [y["year"] for y in data["yearly"]]
        two_phase_eva_vals = [y["eva"] / 1e6 for y in data["yearly"]]
        classical_eva_vals = [v / 1e6 for v in data["classical_eva_by_year"]]

        # Phase regions
        ax.axvspan(0.5, 2.5, alpha=0.10, color="#888")
        ax.axvspan(2.5, 4.5, alpha=0.20, color="#C44536")
        ax.axvspan(4.5, 5.5, alpha=0.10, color="#0B6E4F")

        x = np.array(years)
        width = 0.36
        bars_classical = ax.bar(x - width/2, classical_eva_vals, width,
                                color="#7B7D7D", label="Classical (single WACC)",
                                edgecolor="black", linewidth=0.4)
        bars_two_phase = ax.bar(x + width/2, two_phase_eva_vals, width,
                                color=color, label="Two-phase (phase-conditional WACC)",
                                edgecolor="black", linewidth=0.4)

        # Annotate values
        for bar, v in list(zip(bars_classical, classical_eva_vals)):
            offset = 0.15 if v >= 0 else -0.4
            ax.text(bar.get_x() + bar.get_width()/2, v + offset,
                    f"${v:.1f}M", ha="center", fontsize=7.5)
        for bar, v in list(zip(bars_two_phase, two_phase_eva_vals)):
            offset = 0.15 if v >= 0 else -0.4
            ax.text(bar.get_x() + bar.get_width()/2, v + offset,
                    f"${v:.1f}M", ha="center", fontsize=7.5, fontweight="bold")

        ax.axhline(0, color="black", linewidth=0.7)
        ax.set_xticks(years)
        ax.set_xlabel("Year")
        if ax is axes[0]:
            ax.set_ylabel("EVA (USD millions)")
        ax.grid(True, axis="y", linestyle=":", alpha=0.5)
        ax.set_axisbelow(True)
        ax.legend(loc="upper left", fontsize=8.5, framealpha=0.92)
        ax.set_title(data["name"], fontsize=11, pad=10)
        ax.set_xlim(0.5, 5.5)

    plt.tight_layout()
    out = FIG_DIR / "fig20_two_phase_eva_trajectory.png"
    plt.savefig(out, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"Wrote {out}")


def make_table(neurocertify, dataflow):
    rows = []
    for data in [neurocertify, dataflow]:
        for y in data["yearly"]:
            rows.append({
                "Company": data["name"],
                "Year": y["year"],
                "Phase": y["phase"],
                "Beta_unlevered": f"{y['beta_u']:.2f}",
                "D/E": f"{y['de_ratio']*100:.1f}%",
                "Ke": f"{y['ke']*100:.2f}%",
                "Kd": f"{y['kd']*100:.2f}%",
                "WACC (two-phase)": f"{y['wacc']*100:.2f}%",
                "WACC (classical)": f"{data['classical_wacc']*100:.2f}%",
                "ROI": f"{y['roi']*100:.2f}%",
                "ROI-WACC spread": f"{y['spread']*100:.2f}pp",
                "EVA (two-phase) [USD]": f"{y['eva']:,.0f}",
                "EVA (classical) [USD]": f"{data['classical_eva_by_year'][y['year']-1]:,.0f}",
            })
    df = pd.DataFrame(rows)
    out = TABLE_DIR / "appendix_b_comparative.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {out}")
    print()
    print(df.to_string(index=False))


def main():
    print("\nRunning Appendix B - Two-phase reformulation\n" + "="*60)

    neurocertify = run_company(
        NEUROCERTIFY_LABEL,
        NEUROCERTIFY_PHASES,
        NEUROCERTIFY_FCF, NEUROCERTIFY_INVESTED_CAPITAL, NEUROCERTIFY_NOPAT,
        TERMINAL_GROWTH, second_valley_drag=NEUROCERTIFY_DRAG,
    )
    print(f"\nNeuroCertify two-phase DCF EV: ${neurocertify['dcf']['enterprise_value']:,.0f}")
    print(f"NeuroCertify Phase 1 WACC: {neurocertify['yearly'][0]['wacc']*100:.2f}%")
    print(f"NeuroCertify Phase 2 WACC: {neurocertify['yearly'][2]['wacc']*100:.2f}%")
    print(f"NeuroCertify Phase 3 WACC: {neurocertify['yearly'][4]['wacc']*100:.2f}%")
    print(f"NeuroCertify classical single-WACC: {neurocertify['classical_wacc']*100:.2f}%")

    dataflow = run_company(
        DATAFLOW_LABEL,
        DATAFLOW_PHASES,
        DATAFLOW_FCF, DATAFLOW_INVESTED_CAPITAL, DATAFLOW_NOPAT,
        TERMINAL_GROWTH, second_valley_drag=DATAFLOW_DRAG,
    )
    print(f"\nDataFlow Pro two-phase DCF EV: ${dataflow['dcf']['enterprise_value']:,.0f}")
    print(f"DataFlow Pro Phase 1 WACC: {dataflow['yearly'][0]['wacc']*100:.2f}%")
    print(f"DataFlow Pro Phase 2 WACC: {dataflow['yearly'][2]['wacc']*100:.2f}%")
    print(f"DataFlow Pro Phase 3 WACC: {dataflow['yearly'][4]['wacc']*100:.2f}%")
    print(f"DataFlow Pro classical single-WACC: {dataflow['classical_wacc']*100:.2f}%")

    print()
    make_fig_cost_of_capital(neurocertify, dataflow)
    make_fig_eva_trajectory(neurocertify, dataflow)
    make_table(neurocertify, dataflow)
    print("\nDone.")


if __name__ == "__main__":
    main()
