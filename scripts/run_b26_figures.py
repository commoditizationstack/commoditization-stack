"""Render the three figures of subsection B.2.6 (dual-channel correction).

Generates:
  outputs/figures/fig_b26_geometry.png      — Figure 6-bis / B.3 (single,
                                              cross-referenced)
  outputs/figures/fig_b26_risk_partition_and_lambda_fcf.png   — Figure B.4
  outputs/figures/fig_b26_four_path_reconciliation.png        — Figure B.5

The script wires:
  · The unified V0_dualchannel construction
    (src.dual_channel.v0_dualchannel_unified) from Sprint 4
  · The unified Monte Carlo (src.dual_channel_mc.run_monte_carlo)
    from Sprint 3 — for the P10–P90 bands on Figure B.5
  · The classical Damodaran, Appendix A layered, and Appendix B two-phase
    paths — for the three comparator bars on Figure B.5

Usage:
    python scripts/run_b26_figures.py

See docs/dual_channel_correction.md for the scientific rationale and the
proposed manuscript correction.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import yaml

from app.shared.live_figures import (
    DATAFLOW_COLOR,
    NEUROCERTIFY_COLOR,
    figure_b3_dualchannel_geometry,
    figure_b4_risk_partition_and_corrected_fcf,
    figure_b5_four_path_reconciliation,
)
from src import config
from src.dual_channel import (
    build_lambda_vector,
    v0_dualchannel_unified,
)
from src.dual_channel_mc import MonteCarloSpec, run_monte_carlo
from src.valuation_layered import (
    CashFlowProjection,
    LayerExposure,
    LayeredDiscountRateInputs,
    TRLTrajectory,
    classical_damodaran_dcf,
    compute_layered_discount_rate,
    layered_dcf,
)
from src.valuation_two_phase import PhaseParameters, two_phase_dcf

FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_scenario(slug: str) -> dict:
    path = PROJECT_ROOT / "config" / "scenarios" / f"{slug}.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _phases_for(firm_slug: str) -> PhaseParameters:
    p = config.firms_appendix_b()[firm_slug]["phases"]
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


def _classical_rate_for(scn: dict) -> float:
    """Equal-weight exposure + TRL 9 to zero the TRL premium and the
    layered firm-specific premium, leaving the classical adjusted-CAPM
    rate (matches scripts/run_appendix_a.py)."""
    di = scn["damodaran_industry"]
    dri = scn["discount_rate_inputs"]
    eq = LayerExposure(
        layer_1_infra=1 / 7, layer_2_foundation=1 / 7,
        layer_3_capability=1 / 7, layer_4_codified=1 / 7,
        layer_5_judgment=1 / 7, layer_6_institutional=1 / 7,
        layer_7_crossborder=1 / 7,
    )
    inputs = LayeredDiscountRateInputs(
        risk_free_rate=dri["risk_free_rate"],
        equity_risk_premium=dri["equity_risk_premium"],
        industry_unlevered_beta=di["unlevered_beta"],
        de_ratio=di["market_de_ratio"],
        effective_tax_rate=di["effective_tax_rate"],
        trl=9, layer_exposure=eq, K7=1.0,
        layer4_substitution_potential=0.0,
        sector_label=di["industry_name"],
    )
    return float(compute_layered_discount_rate(inputs).base_capm)


def _build_layered_inputs(scn: dict) -> LayeredDiscountRateInputs:
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


def _compute_four_paths_for_firm(scenario_slug: str, firm_slug: str) -> dict:
    """Compute the four point-estimate EVs plus the MC bands."""
    scn = _load_scenario(scenario_slug)
    firms = config.firms_appendix_b()
    firm = firms[firm_slug]
    macro = firms["macro"]
    phases = _phases_for(firm_slug)
    cf = CashFlowProjection(
        year_labels=scn["cash_flows"]["year_labels"],
        fcf_usd=scn["cash_flows"]["fcf_usd"],
    )
    trl = TRLTrajectory(
        year_labels=scn["trl_trajectory"]["year_labels"],
        trl_by_year=scn["trl_trajectory"]["trl_by_year"],
    )

    classical_rate = _classical_rate_for(scn)
    layered_inputs = _build_layered_inputs(scn)

    v_classical = classical_damodaran_dcf(
        cf, discount_rate=classical_rate,
        terminal_growth_rate=scn["terminal_growth_rate"],
        sector_label=scn["scenario_name"],
    ).enterprise_value_usd

    v_layered_A = layered_dcf(
        cf, inputs=layered_inputs, trl_trajectory=trl,
        terminal_growth_rate=scn["terminal_growth_rate"],
        second_valley_drag=scn["second_valley_drag"],
    ).enterprise_value_usd

    v_twophase_B = two_phase_dcf(
        fcf_by_year=list(firm["fcf_usd"]),
        risk_free_rate=float(macro["risk_free_rate"]),
        equity_risk_premium=float(macro["equity_risk_premium"]),
        phases=phases,
        terminal_growth_rate=float(macro["terminal_growth"]),
        second_valley_drag=float(firm["second_valley_drag"]),
    )["enterprise_value"]

    dc_cfg = config.dual_channel()
    lambda_p2 = float(dc_cfg["lambda_2V_phase2_defaults"][firm_slug])
    lambda_p3 = float(dc_cfg["lambda_2V_phase3_defaults"][firm_slug])
    dual = v0_dualchannel_unified(
        fcf_by_year=list(firm["fcf_usd"]),
        risk_free_rate=float(macro["risk_free_rate"]),
        equity_risk_premium=float(macro["equity_risk_premium"]),
        phases=phases,
        terminal_growth_rate=float(macro["terminal_growth"]),
        lambda_phase2=lambda_p2,
        lambda_phase3=lambda_p3,
    )
    v_dualchannel = dual.enterprise_value

    mc = run_monte_carlo(
        scenario=scn,
        phases=phases,
        fcf_two_phase=list(firm["fcf_usd"]),
        risk_free_rate_b=float(macro["risk_free_rate"]),
        equity_risk_premium_b=float(macro["equity_risk_premium"]),
        second_valley_drag_b=float(firm["second_valley_drag"]),
        classical_rate=classical_rate,
        layered_inputs=layered_inputs,
        trl_traj=trl,
        lambda_phase2_center=lambda_p2,
        spec=MonteCarloSpec(n_runs=5000, seed=42),
    )

    return {
        "v0_classical": v_classical,
        "v0_layered_A": v_layered_A,
        "v0_twophase_B": v_twophase_B,
        "v0_dualchannel": v_dualchannel,
        "bands": mc.bands,
        "lambda_vector": dual.lambda_vector,
        "lambda_phase2": lambda_p2,
        "lambda_phase3": lambda_p3,
    }


def _build_b4_firm_dict(firm_slug: str, four_paths: dict, color: str,
                        display_label: str) -> dict:
    """Assemble the per-firm dict B.4 expects."""
    firms = config.firms_appendix_b()
    firm = firms[firm_slug]
    p = firm["phases"]
    scn_slug = "neurocertify" if firm_slug == "neurocertify" else "dataflow_pro"
    scn = _load_scenario(scn_slug)
    vl = config.load_parameters()["valuation_layered"]
    coefs = config.layer_risk_coefficients()
    dc = config.dual_channel()
    return {
        "label": display_label,
        "color": color,
        "layer4_share": float(scn["layer_exposure"]["layer_4_codified"]),
        "ai_substitution_potential": float(scn["layer4_substitution_potential"]),
        "alpha_4": float(coefs["layer_4_codified"]),
        "alpha_4_sys": float(dc["alpha_4_sys"]),
        "amp_base": float(vl["layer4_substitution_amplifier_base"]),
        "fcf_proj": list(firm["fcf_usd"]),
        "lambda_vector": four_paths["lambda_vector"],
        "phase_boundaries": (
            int(p["phase_1_end_year"]),
            int(p["phase_2_end_year"]),
        ),
    }


def _build_b5_firm_dict(four_paths: dict, color: str, display_label: str) -> dict:
    return {
        "label": display_label,
        "color": color,
        "v0_classical":   four_paths["v0_classical"],
        "v0_layered_A":   four_paths["v0_layered_A"],
        "v0_twophase_B":  four_paths["v0_twophase_B"],
        "v0_dualchannel": four_paths["v0_dualchannel"],
        "bands":          four_paths["bands"],
    }


def main() -> None:
    print("Rendering B.2.6 figures (6-bis / B.3, B.4, B.5)")
    print("=" * 60)

    # --- Figure 6-bis / B.3: conceptual geometry (no data dependencies) ---
    fig_b3 = figure_b3_dualchannel_geometry(formal_labels=True)
    out_b3 = FIG_DIR / "fig_b26_geometry.png"
    fig_b3.savefig(out_b3, dpi=140, bbox_inches="tight")
    plt.close(fig_b3)
    print(f"  Wrote {out_b3.relative_to(PROJECT_ROOT)}")

    # --- Compute paths for both firms ---
    print("\n  Computing four valuation paths + MC bands for both firms...")
    nc = _compute_four_paths_for_firm("neurocertify", "neurocertify")
    df = _compute_four_paths_for_firm("dataflow_pro", "dataflow")

    print(f"\n  NeuroCertify  classical=${nc['v0_classical']/1e6:6.1f}M  "
          f"layered=${nc['v0_layered_A']/1e6:6.1f}M  "
          f"twophase=${nc['v0_twophase_B']/1e6:6.1f}M  "
          f"dualchannel=${nc['v0_dualchannel']/1e6:6.1f}M")
    print(f"  DataFlow Pro  classical=${df['v0_classical']/1e6:6.1f}M  "
          f"layered=${df['v0_layered_A']/1e6:6.1f}M  "
          f"twophase=${df['v0_twophase_B']/1e6:6.1f}M  "
          f"dualchannel=${df['v0_dualchannel']/1e6:6.1f}M")

    # --- Figure B.4 ---
    firms_b4 = {
        "neurocertify": _build_b4_firm_dict(
            "neurocertify", nc, NEUROCERTIFY_COLOR,
            "NeuroCertify (deep-tech, HIT)",
        ),
        "dataflow": _build_b4_firm_dict(
            "dataflow", df, DATAFLOW_COLOR,
            "DataFlow Pro (Software, commoditizing)",
        ),
    }
    fig_b4 = figure_b4_risk_partition_and_corrected_fcf(firms=firms_b4)
    out_b4 = FIG_DIR / "fig_b26_risk_partition_and_lambda_fcf.png"
    fig_b4.savefig(out_b4, dpi=140, bbox_inches="tight")
    plt.close(fig_b4)
    print(f"\n  Wrote {out_b4.relative_to(PROJECT_ROOT)}")

    # --- Figure B.5 ---
    stages = config.us_funding_stage_benchmarks()
    funding_lines = {
        "seed":     float(stages["seed"]["median_premoney_usd"]),
        "series_a": float(stages["series_a"]["median_premoney_usd"]),
        "series_b": float(stages["series_b"]["median_premoney_usd"]),
    }
    firms_b5 = {
        "neurocertify": _build_b5_firm_dict(
            nc, NEUROCERTIFY_COLOR, "NeuroCertify (deep-tech, HIT)",
        ),
        "dataflow": _build_b5_firm_dict(
            df, DATAFLOW_COLOR, "DataFlow Pro (Software, commoditizing)",
        ),
    }
    fig_b5 = figure_b5_four_path_reconciliation(
        firms=firms_b5,
        funding_stage_lines=funding_lines,
    )
    out_b5 = FIG_DIR / "fig_b26_four_path_reconciliation.png"
    fig_b5.savefig(out_b5, dpi=140, bbox_inches="tight")
    plt.close(fig_b5)
    print(f"  Wrote {out_b5.relative_to(PROJECT_ROOT)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
