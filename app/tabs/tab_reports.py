"""Tab — Multi-audience reports + macro-sensitivity view (Sprint 7).

Wires :mod:`src.reporting` into the Streamlit UI. Lets the user pick
a case firm, choose an audience (investor / founder / policy /
researcher), and adjust the macro context (``macro_regime`` and
``funding_environment``). The rendered markdown report is displayed
in-line; the macro-sensitivity grid is rendered as an expandable
markdown table.

The tab consumes ``src.reporting.RunResult`` as its typed payload —
the same data structure the engine produces. Acceptance check 8.1
(macro_regime / funding_environment must not perturb the four EVs) is
enforced structurally: the EVs are computed ONCE from the case-firm
fixture and the macro context only affects presentation.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.shared import live_figures
from src import config
from src.dual_channel import v0_dualchannel_unified
from src.dual_channel_mc import MonteCarloSpec, run_monte_carlo
from src.reporting import (
    Audience,
    RunResult,
    funding_stage_placement,
    generate_report,
    macro_sensitivity_grid,
    render_macro_sensitivity_table,
)
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIOS_DIR = PROJECT_ROOT / "config" / "scenarios"


# ---------------------------------------------------------------------------
# Top-level render
# ---------------------------------------------------------------------------

def render(global_params: dict | None = None) -> None:
    st.header("📋 Multi-audience reports (Macro Integration Proposal, Part B)")
    st.markdown(
        """
        From the same valuation run, this tab produces four mutually-consistent
        reports — investor, founder, policy, researcher — that share every
        shared number but differ in framing, ordering and depth (acceptance
        check 8.2). Adjust the macro context to see how the macro-sensitivity
        view re-frames the funding-stage placement and the MC dispersion
        WITHOUT changing any of the four enterprise values (acceptance
        check 8.1, structurally enforced).
        """
    )

    firm_options = {
        "NeuroCertify (deep-tech, HIT)":          ("neurocertify", "neurocertify"),
        "DataFlow Pro (Software, commoditizing)": ("dataflow",     "dataflow_pro"),
    }
    firm_label = st.selectbox(
        "Case firm", list(firm_options.keys()), key="reports_firm_selector",
    )
    firm_slug, scenario_slug = firm_options[firm_label]

    # --- Macro context controls (presentation-only) ---
    st.subheader("Macro context (presentation-only)")
    st.caption(
        "These controls do NOT alter any of the four enterprise values. "
        "They reshape the macro-sensitivity grid and the funding-stage "
        "placement reference lines."
    )
    c1, c2 = st.columns(2)
    with c1:
        macro_regime = st.slider(
            "macro_regime", min_value=0.0, max_value=1.0,
            value=0.5, step=0.05,
            help="0 = normal-technology reading; 1 = structural-change. "
                 "0.5 reproduces the baseline run exactly.",
            key="reports_macro_regime",
        )
    with c2:
        funding_environment = st.selectbox(
            "funding_environment",
            options=["abundant", "baseline", "crowded"],
            index=1,
            help="Shifts the SEED reference line only (per Section 8.1).",
            key="reports_funding_env",
        )

    # --- Compute the four paths + MC bands (cached on slug) ---
    try:
        run_result = _build_run_result(
            scenario_slug, firm_slug,
            macro_regime=macro_regime,
            funding_environment=funding_environment,
        )
    except FileNotFoundError as e:
        st.error(f"Scenario file not found: {e}")
        return

    # --- Audience selector ---
    st.subheader("Audience")
    audience_label = st.radio(
        "Choose the register in which to render the report",
        options=[a.value for a in Audience],
        horizontal=True,
        format_func=str.capitalize,
        key="reports_audience",
    )
    audience = Audience(audience_label)

    # --- Render the report ---
    report = generate_report(audience, run_result.to_dict())

    st.markdown("---")
    st.markdown(report.body_markdown)

    # --- Macro-sensitivity grid (expandable) ---
    st.markdown("---")
    with st.expander("🔬 Macro-sensitivity grid "
                      "(macro_regime × funding_environment, "
                      "dispersion channel disclosed)"):
        cells = macro_sensitivity_grid(run_result)
        st.markdown(render_macro_sensitivity_table(cells))
        st.caption(
            "Transmission channel: macro_regime widens the MC dispersion "
            "(symmetric multiplier around 1.0 at macro_regime=0.5). The "
            "central EVs are NEVER perturbed — acceptance check 8.1 "
            "enforced by construction. See "
            "`docs/dual_channel_correction.md` and the Macro Integration "
            "Proposal Section 8.4."
        )

    # --- Diagnostic: which citations the renderer pulled ---
    with st.expander("📚 Citations used in this report"):
        if not report.citations_used:
            st.write("_(none)_")
        else:
            for key in report.citations_used:
                from src.reporting import CITATIONS
                entry = CITATIONS.get(key, {})
                st.markdown(f"* **{entry.get('short', key)}** — {entry.get('full', '—')}")


# ---------------------------------------------------------------------------
# Helpers (mirror those in tab_appendix_b.py — kept in-module to preserve
# the Streamlit / src separation; both tabs would otherwise share state)
# ---------------------------------------------------------------------------

def _load_scenario(scenario_slug: str) -> dict:
    import yaml
    with open(SCENARIOS_DIR / f"{scenario_slug}.yaml") as f:
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


def _layered_inputs(scn: dict) -> LayeredDiscountRateInputs:
    le = scn["layer_exposure"]
    di = scn["damodaran_industry"]
    dri = scn["discount_rate_inputs"]
    return LayeredDiscountRateInputs(
        risk_free_rate=dri["risk_free_rate"],
        equity_risk_premium=dri["equity_risk_premium"],
        industry_unlevered_beta=di["unlevered_beta"],
        de_ratio=di["market_de_ratio"],
        effective_tax_rate=di["effective_tax_rate"],
        trl=scn["trl_trajectory"]["trl_by_year"][0],
        layer_exposure=LayerExposure(
            layer_1_infra=le["layer_1_infra"],
            layer_2_foundation=le["layer_2_foundation"],
            layer_3_capability=le["layer_3_capability"],
            layer_4_codified=le["layer_4_codified"],
            layer_5_judgment=le["layer_5_judgment"],
            layer_6_institutional=le["layer_6_institutional"],
            layer_7_crossborder=le["layer_7_crossborder"],
        ),
        K7=scn["K7"],
        layer4_substitution_potential=scn["layer4_substitution_potential"],
        sector_label=di["industry_name"],
    )


def _classical_rate_for(scn: dict) -> float:
    di = scn["damodaran_industry"]
    dri = scn["discount_rate_inputs"]
    eq = LayerExposure(
        layer_1_infra=1/7, layer_2_foundation=1/7, layer_3_capability=1/7,
        layer_4_codified=1/7, layer_5_judgment=1/7, layer_6_institutional=1/7,
        layer_7_crossborder=1/7,
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


@st.cache_data(show_spinner="Running the four valuation paths + MC bands…")
def _build_run_result(
    scenario_slug: str, firm_slug: str,
    macro_regime: float, funding_environment: str,
) -> RunResult:
    """Compute the canonical RunResult for the selected case firm.

    Cached on (scenario_slug, firm_slug, macro_regime, funding_environment)
    — note that macro_regime / funding_environment do NOT alter the EVs;
    they are passed only so the cache invalidation reproduces the
    funding-stage placement under the requested environment.
    """
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
    layered_inp = _layered_inputs(scn)

    v_cls = classical_damodaran_dcf(
        cf, discount_rate=_classical_rate_for(scn),
        terminal_growth_rate=scn["terminal_growth_rate"],
        sector_label=scn["scenario_name"],
    ).enterprise_value_usd
    v_lay = layered_dcf(
        cf, inputs=layered_inp, trl_trajectory=trl,
        terminal_growth_rate=scn["terminal_growth_rate"],
        second_valley_drag=scn["second_valley_drag"],
    ).enterprise_value_usd
    v_tp = two_phase_dcf(
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
    alpha_4_sys = float(dc_cfg["alpha_4_sys"])
    dual = v0_dualchannel_unified(
        fcf_by_year=list(firm["fcf_usd"]),
        risk_free_rate=float(macro["risk_free_rate"]),
        equity_risk_premium=float(macro["equity_risk_premium"]),
        phases=phases,
        terminal_growth_rate=float(macro["terminal_growth"]),
        lambda_phase2=lambda_p2,
        lambda_phase3=lambda_p3,
    )

    # MC bands at the recommended calibration (lambda from YAML).
    mc = run_monte_carlo(
        scenario=scn,
        phases=phases,
        fcf_two_phase=list(firm["fcf_usd"]),
        risk_free_rate_b=float(macro["risk_free_rate"]),
        equity_risk_premium_b=float(macro["equity_risk_premium"]),
        second_valley_drag_b=float(firm["second_valley_drag"]),
        classical_rate=_classical_rate_for(scn),
        layered_inputs=layered_inp,
        trl_traj=trl,
        lambda_phase2_center=lambda_p2,
        spec=MonteCarloSpec(n_runs=2000, seed=42),
    )

    placement = funding_stage_placement(
        dual.enterprise_value, funding_environment=funding_environment,
    )

    return RunResult(
        firm_label=("NeuroCertify (deep-tech, HIT)"
                    if firm_slug == "neurocertify"
                    else "DataFlow Pro (Software, commoditizing)"),
        sector=scn["damodaran_industry"]["industry_name"],
        v0_classical=v_cls,
        v0_layered_A=v_lay,
        v0_twophase_B=v_tp,
        v0_dualchannel=dual.enterprise_value,
        bands=dict(mc.bands),
        numerator_channel_effect=dual.numerator_channel_effect,
        layer_exposure=dict(scn["layer_exposure"]),
        K7=float(scn["K7"]),
        layer4_substitution_potential=float(scn["layer4_substitution_potential"]),
        lambda_2V_phase2=lambda_p2,
        lambda_2V_phase3=lambda_p3,
        alpha_4_sys=alpha_4_sys,
        macro_regime=macro_regime,
        funding_environment=funding_environment,
        funding_stage_placement=placement,
    )
