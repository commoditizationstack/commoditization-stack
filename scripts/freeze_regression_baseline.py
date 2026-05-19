"""Freeze the deterministic outputs of the three existing valuation paths
(classical Damodaran, Appendix A layered DCF, Appendix B two-phase DCF)
for the two case firms (NeuroCertify, DataFlow Pro).

This produces golden-file snapshots used by ``tests/test_regression_baseline.py``
to guarantee that subsequent additive changes (e.g. the dual-channel
correction of subsection B.2.6) do NOT alter the numerical output of the
three existing paths.

Usage:
    python scripts/freeze_regression_baseline.py

Outputs:
    tests/baselines/neurocertify.json
    tests/baselines/dataflow_pro.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from src import config
from src.valuation_layered import (
    CashFlowProjection,
    LayerExposure,
    LayeredDiscountRateInputs,
    TRLTrajectory,
    classical_damodaran_dcf,
    compute_layered_discount_rate,
    layered_dcf,
)
from src.valuation_two_phase import PhaseParameters, two_phase_dcf, two_phase_wacc

BASELINE_DIR = PROJECT_ROOT / "tests" / "baselines"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)


def _load_scenario(slug: str) -> dict:
    path = PROJECT_ROOT / "config" / "scenarios" / f"{slug}.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _snapshot_appendix_a(scn: dict) -> dict:
    """Run the classical Damodaran and the layered DCF paths and return a
    snapshot of their deterministic outputs.

    Mirrors ``scripts/run_appendix_a.py::run_company`` but emits a dict
    suitable for JSON serialization rather than a result object graph.
    """
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
    di = scn["damodaran_industry"]
    dri = scn["discount_rate_inputs"]
    inputs = LayeredDiscountRateInputs(
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
    trl_traj = TRLTrajectory(
        year_labels=scn["trl_trajectory"]["year_labels"],
        trl_by_year=scn["trl_trajectory"]["trl_by_year"],
    )
    cf = CashFlowProjection(
        year_labels=scn["cash_flows"]["year_labels"],
        fcf_usd=scn["cash_flows"]["fcf_usd"],
    )

    # Classical Damodaran rate: TRL 9 (no premium), equal-weight layer
    # exposure (so the layer premium is zero by construction), K7=1.0.
    classical_rate_result = compute_layered_discount_rate(
        LayeredDiscountRateInputs(
            risk_free_rate=inputs.risk_free_rate,
            equity_risk_premium=inputs.equity_risk_premium,
            industry_unlevered_beta=inputs.industry_unlevered_beta,
            de_ratio=inputs.de_ratio,
            effective_tax_rate=inputs.effective_tax_rate,
            trl=9,
            layer_exposure=LayerExposure(
                layer_1_infra=1 / 7, layer_2_foundation=1 / 7,
                layer_3_capability=1 / 7, layer_4_codified=1 / 7,
                layer_5_judgment=1 / 7, layer_6_institutional=1 / 7,
                layer_7_crossborder=1 / 7,
            ),
            K7=1.0,
            layer4_substitution_potential=0.0,
            sector_label=inputs.sector_label,
        )
    )
    classical_rate = classical_rate_result.base_capm

    dcf_classical = classical_damodaran_dcf(
        cf,
        discount_rate=classical_rate,
        terminal_growth_rate=scn["terminal_growth_rate"],
        sector_label=scn["scenario_name"],
    )
    dcf_layered = layered_dcf(
        cf,
        inputs=inputs,
        trl_trajectory=trl_traj,
        terminal_growth_rate=scn["terminal_growth_rate"],
        second_valley_drag=scn["second_valley_drag"],
    )

    return {
        "path_1_classical_damodaran": {
            "enterprise_value_usd": dcf_classical.enterprise_value_usd,
            "pv_explicit_period_usd": dcf_classical.pv_explicit_period_usd,
            "pv_terminal_usd": dcf_classical.pv_terminal_usd,
            "discount_rate": classical_rate,
        },
        "path_2_layered_dcf": {
            "enterprise_value_usd": dcf_layered.enterprise_value_usd,
            "pv_explicit_period_usd": dcf_layered.pv_explicit_period_usd,
            "pv_terminal_usd": dcf_layered.pv_terminal_usd,
            "discount_rates_by_year": list(dcf_layered.discount_rate_used),
        },
    }


def _snapshot_appendix_b(firm_slug: str) -> dict:
    """Run the two-phase DCF path for ``firm_slug`` and return a snapshot.

    Reads firm-level fixtures from ``config/parameters.yaml`` under
    ``firms_appendix_b.<slug>``. Mirrors ``scripts/run_appendix_b.py``.
    """
    firms = config.firms_appendix_b()
    macro = firms["macro"]
    firm = firms[firm_slug]
    p = firm["phases"]

    phases = PhaseParameters(
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

    rf = float(macro["risk_free_rate"])
    erp = float(macro["equity_risk_premium"])
    g = float(macro["terminal_growth"])
    drag = float(firm["second_valley_drag"])
    fcf = list(firm["fcf_usd"])

    dcf = two_phase_dcf(fcf, rf, erp, phases, g, second_valley_drag=drag)

    # Capture phase-conditional WACC for each year — diagnostic richer than EV alone.
    yearly = []
    for year in range(1, len(fcf) + 1):
        w = two_phase_wacc(year, rf, erp, phases)
        yearly.append({
            "year": year,
            "phase": w["phase"],
            "wacc": w["wacc"],
            "ke": w["ke"],
            "kd": w["kd"],
        })

    return {
        "path_3_two_phase_dcf": {
            "enterprise_value_usd": dcf["enterprise_value"],
            "pv_explicit_usd": dcf["pv_explicit"],
            "pv_terminal_usd": dcf["pv_terminal"],
            "phase_3_wacc": dcf["phase_3_wacc"],
            "yearly": yearly,
        },
    }


def freeze_firm(scenario_slug: str, firm_slug: str, output_filename: str) -> Path:
    scn = _load_scenario(scenario_slug)
    snapshot = {
        "_meta": {
            "firm": firm_slug,
            "scenario": scenario_slug,
            "purpose": (
                "Regression baseline for the three existing valuation paths "
                "(classical Damodaran, Appendix A layered DCF, Appendix B "
                "two-phase DCF). Subsequent additive changes (e.g. the dual-"
                "channel correction of subsection B.2.6) MUST NOT alter "
                "these numbers."
            ),
        },
    }
    snapshot.update(_snapshot_appendix_a(scn))
    snapshot.update(_snapshot_appendix_b(firm_slug))

    out_path = BASELINE_DIR / output_filename
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)
    return out_path


def main() -> None:
    print("Freezing regression baseline for the three valuation paths")
    print("=" * 60)

    nc_path = freeze_firm("neurocertify", "neurocertify", "neurocertify.json")
    print(f"  Wrote {nc_path.relative_to(PROJECT_ROOT)}")

    df_path = freeze_firm("dataflow_pro", "dataflow", "dataflow_pro.json")
    print(f"  Wrote {df_path.relative_to(PROJECT_ROOT)}")

    print()
    print("Done. Run pytest tests/test_regression_baseline.py to verify.")


if __name__ == "__main__":
    main()
