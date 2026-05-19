"""Tab Appendix B — phase-conditional CAPM/WACC with eleven equations,
plus the B.2.6 dual-channel correction (Sprint 7)."""
import streamlit as st
from pathlib import Path

from app.shared import live_figures, state
from src import config
from src.dual_channel import (
    build_lambda_vector,
    v0_dualchannel_unified,
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
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"
SCENARIOS_DIR = PROJECT_ROOT / "config" / "scenarios"


def render(global_params: dict):
    state.init_session_state()

    st.header("Appendix B — Two-Phase Reformulation of Canonical Formulas")
    st.markdown(
        """
        Appendix B reformulates CAPM, WACC, EVA, ROI, and the Gordon perpetuity
        as **phase-conditional** under the post-AI double-valley dynamic of
        Section 6.5. Eleven numbered equations make the reformulation explicit;
        a numerical demonstration on NeuroCertify and DataFlow Pro shows that
        the classical EVA framework masks a Phase-2 destruction-of-value period
        of approximately 23 per cent for Layer-4-heavy firms.
        """
    )

    st.subheader("Eleven numbered equations")

    eq_files = [
        ("eq_B1_classical_capm_beta.png", "B.1", "Classical levered beta"),
        ("eq_B2_classical_ke.png", "B.2", "Classical cost of equity"),
        ("eq_B3_phase_beta.png", "B.3", "Phase-conditional levered beta"),
        ("eq_B4_phase_ke.png", "B.4", "Phase-conditional cost of equity"),
        ("eq_B5_classical_wacc.png", "B.5", "Classical WACC"),
        ("eq_B6_phase_wacc.png", "B.6", "Phase-conditional WACC"),
        ("eq_B7_phase_eva.png", "B.7", "Phase-conditional EVA"),
        ("eq_B8_phase_roi.png", "B.8", "Phase-conditional ROI test"),
        ("eq_B9_phase_perpetuity.png", "B.9", "Phase-conditional Gordon perpetuity"),
        ("eq_B10_compounded_pv.png", "B.10", "Compounded discount factor"),
        ("eq_B11_two_phase_dcf.png", "B.11", "Two-phase enterprise value (full DCF)"),
    ]

    for fname, num, label in eq_files:
        fp = FIG_DIR / fname
        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            if fp.exists():
                st.image(str(fp), use_container_width=True)
                st.caption(f"({num}) — {label}")
            else:
                st.warning(f"Equation {num} image missing.")

    st.markdown("---")

    # ===== Live figures =====
    p = state.effective_parameters()
    st.markdown("---")
    st.subheader("📈 Live figures")
    st.caption("These plots update immediately when you edit firm-specific "
                "phase parameters in ⚙️ Configuration → Case studies / Two-phase.")

    st.markdown("#### B.1 — Two-phase cost-of-capital trajectory")
    st.pyplot(live_figures.appendix_b_two_phase_cost_of_capital(parameters=p),
                use_container_width=True)

    st.markdown("#### B.2 — EVA trajectory: classical vs two-phase")
    st.pyplot(live_figures.appendix_b_two_phase_eva_trajectory(parameters=p),
                use_container_width=True)

    st.markdown("---")
    st.subheader("📷 Paper PNG snapshots")
    fig_titles = [
        ("fig19_two_phase_cost_of_capital.png",
         "Cost-of-capital trajectory by phase",
         "Phase-conditional WACC and Ke trajectories for NeuroCertify (left) "
         "and DataFlow Pro (right). NeuroCertify's Phase-2 jump is 1.67 pp "
         "(Layer-6 protection); DataFlow Pro's is 3.01 pp (Layer-4 exposure). "
         "The 1.34-pp asymmetry is the operational realization in WACC space "
         "of the seven-layer framework's claim about defensibility migration. "
         "*Note (Sprint 5 cross-reference):* this trajectory is a single-channel "
         "correction (denominator side: phase-conditional WACC + δ_2V drag on "
         "the terminal value); the dual-channel value that additionally "
         "corrects the numerator via λ_2V is reported in Figure B.5 of "
         "Appendix B.2.6."),
        ("fig20_two_phase_eva_trajectory.png",
         "EVA trajectory: classical vs two-phase",
         "Year-by-year EVA under classical single-WACC formulation (grey) "
         "versus two-phase phase-conditional WACC formulation (colored). "
         "The classical formulation understates DataFlow Pro's Phase-2 "
         "value destruction by approximately 23 per cent."),
    ]

    for fname, title, caption in fig_titles:
        fp = FIG_DIR / fname
        st.markdown(f"#### {title}")
        if fp.exists():
            st.image(str(fp), caption=caption, use_container_width=True)
        else:
            st.warning(f"Figure `{fname}` not yet generated.")

    st.markdown("---")

    st.markdown(
        """
        ### Recalibrate two-phase parameters
        Use ⚙️ **Configuration → Two-phase CAPM/WACC (Appendix B)** to set
        custom per-phase betas, D/E ratios, and Kd spreads. The case-study
        firms (NeuroCertify, DataFlow Pro) inherit their phase boundaries
        from the same panel.
        """
    )

    st.markdown("---")
    _render_b26_section()


# ---------------------------------------------------------------------------
# B.2.6 — Dual-channel correction (Sprint 7 live integration)
# ---------------------------------------------------------------------------

def _render_b26_section() -> None:
    """Live B.2.6 dual-channel correction.

    Exposes the per-firm calibration parameters (lambda_phase2,
    lambda_phase3, alpha_4_sys) as sliders. Recomputes the four
    valuation paths on every change and renders Figure B.5 live.

    See docs/dual_channel_correction.md for the scientific rationale
    behind the unified-lambda construction this section uses.
    """
    st.header("Appendix B.2.6 — Dual-channel correction (live)")
    st.markdown(
        """
        The dual-channel correction extends Eq B.11 with the **numerator
        channel**: free cash flow is multiplied by a phase-conditional
        ``λ_2V`` factor (Eq B.14). The unified construction also extends
        λ to Phase 3 (permanent margin reduction; see
        [`docs/dual_channel_correction.md`](https://github.com/ademiran/commoditization-stack-simulation/blob/main/docs/dual_channel_correction.md))
        and retires the separate ``δ_2V`` drag (its information is
        absorbed into ``λ_phase3``).
        """
    )

    firm_options = {
        "NeuroCertify (deep-tech, HIT)": ("neurocertify", "neurocertify"),
        "DataFlow Pro (Software, commoditizing)": ("dataflow", "dataflow_pro"),
    }
    firm_label = st.radio(
        "Case firm",
        list(firm_options.keys()),
        horizontal=True,
        key="b26_firm_selector",
    )
    firm_slug, scenario_slug = firm_options[firm_label]

    dc_cfg = config.dual_channel()
    default_lp2 = float(dc_cfg["lambda_2V_phase2_defaults"][firm_slug])
    default_lp3 = float(dc_cfg["lambda_2V_phase3_defaults"][firm_slug])
    default_alpha_sys = float(dc_cfg["alpha_4_sys"])

    col1, col2, col3 = st.columns(3)
    with col1:
        lambda_p2 = st.slider(
            "λ_2V_phase2 (transient retreat)",
            min_value=0.50, max_value=1.00, value=default_lp2, step=0.01,
            help="Phase-2 revenue compression. < 1 means the second valley "
                 "compresses revenue during the commoditization window.",
            key="b26_lambda_p2",
        )
    with col2:
        lambda_p3 = st.slider(
            "λ_2V_phase3 (permanent compression)",
            min_value=0.50, max_value=1.00, value=default_lp3, step=0.01,
            help="Phase-3 permanent margin reduction. Captures the new lower "
                 "steady state after the second valley (replaces the "
                 "original δ_2V mechanism).",
            key="b26_lambda_p3",
        )
    with col3:
        alpha_4_sys = st.slider(
            "α_4_sys (Eq B.13)",
            min_value=0.000, max_value=0.080, value=default_alpha_sys, step=0.005,
            help="Systematic share of the Layer-4 second-valley risk, already "
                 "represented in the Phase-2 beta jump. Used to compute "
                 "α_4_adj = α_4 − α_4_sys (registered for hybrid extensions; "
                 "not consumed by the basic unified V0_dualchannel).",
            key="b26_alpha_4_sys",
        )

    # Compute the four paths under the slider values.
    try:
        result = _compute_four_paths(scenario_slug, firm_slug,
                                      lambda_p2, lambda_p3)
    except FileNotFoundError as e:
        st.error(f"Scenario file not found: {e}")
        return

    # ----- Headline numbers strip -----
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("V0_classical",   f"${result['v0_classical']/1e6:.1f}M")
    c2.metric("V0_layered_A",   f"${result['v0_layered_A']/1e6:.1f}M")
    c3.metric("V0_twophase_B",  f"${result['v0_twophase_B']/1e6:.1f}M")
    c4.metric(
        "V0_dualchannel (unified)",
        f"${result['v0_dualchannel']/1e6:.1f}M",
        delta=f"{(result['v0_dualchannel'] - result['v0_twophase_B'])/1e6:+.1f}M vs two-phase",
        delta_color="inverse",  # red when negative (dual-channel below two-phase = MORE conservative)
    )

    # ----- Cash-flow channel diagnostic -----
    nce = result["v0_twophase_B"] - result["v0_dualchannel"]
    st.markdown(
        f"**Numerator channel effect** (V0_twophase_B − V0_dualchannel): "
        f"`${nce/1e6:.2f}M`. This is the value the cash-flow side "
        "compression captures that the rate-only two-phase WACC misses."
    )

    # ----- Live Figure B.5 -----
    st.subheader("📊 Live Figure B.5 — Four-path reconciliation")
    st.caption("Updates immediately when you move the sliders above. "
                "P10/P50/P90 bands come from a deterministic 1500-run MC "
                "with seed=42; they widen with λ uncertainty.")

    fig_b5 = _build_live_figure_b5(scenario_slug, firm_slug, result)
    st.pyplot(fig_b5, use_container_width=True)

    # ----- Calibration helper inspector -----
    with st.expander("Auditable calibration helpers (Eq B.13 / per-firm λ)"):
        st.markdown(
            f"* `α_4` = {float(config.layer_risk_coefficients()['layer_4_codified']):.3f}  "
            "(layer_risk_coefficients.layer_4_codified)\n"
            f"* `α_4_sys` (slider) = {alpha_4_sys:.3f}\n"
            f"* `α_4_adj = α_4 − α_4_sys` = "
            f"{max(0.0, float(config.layer_risk_coefficients()['layer_4_codified']) - alpha_4_sys):.3f}  "
            "(consumed by the hybrid extension; not by the unified V0_dualchannel basic path)\n"
            f"* Documented per-firm defaults: "
            f"λ_phase2={default_lp2:.2f}, λ_phase3={default_lp3:.2f}\n"
        )

    st.caption(
        "🔬 Scientific note: the unified construction replaces the literal "
        "Eq B.14 (which fixed λ_phase3 = 1.0) with a per-firm Phase-3 "
        "calibration consistent with the displacement-risk literature "
        "(Cazzaniga IMF 2024, Brynjolfsson 2025, Korinek 2025, Damodaran "
        "2009). See `docs/dual_channel_correction.md`."
    )


# ---------------------------------------------------------------------------
# Helpers (kept inside tab_appendix_b.py to avoid leaking Streamlit-side
# data-loading into the otherwise pure-presentation src/ tree)
# ---------------------------------------------------------------------------

def _load_scenario(scenario_slug: str) -> dict:
    import yaml
    path = SCENARIOS_DIR / f"{scenario_slug}.yaml"
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
    equal_exposure = LayerExposure(
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
        trl=9, layer_exposure=equal_exposure,
        K7=1.0, layer4_substitution_potential=0.0,
        sector_label=di["industry_name"],
    )
    return float(compute_layered_discount_rate(inputs).base_capm)


@st.cache_data(show_spinner=False)
def _compute_four_paths(scenario_slug: str, firm_slug: str,
                         lambda_p2: float, lambda_p3: float) -> dict:
    """Compute the four EVs under the slider-supplied λ calibration.

    Cached on (scenario_slug, firm_slug, lambda_p2, lambda_p3) so
    slider sweeps are responsive. Does NOT depend on alpha_4_sys —
    the unified basic V0_dualchannel does not consume it, per
    docs/dual_channel_correction.md Section 6.
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
    dual = v0_dualchannel_unified(
        fcf_by_year=list(firm["fcf_usd"]),
        risk_free_rate=float(macro["risk_free_rate"]),
        equity_risk_premium=float(macro["equity_risk_premium"]),
        phases=phases,
        terminal_growth_rate=float(macro["terminal_growth"]),
        lambda_phase2=lambda_p2,
        lambda_phase3=lambda_p3,
    )
    return {
        "v0_classical":   v_cls,
        "v0_layered_A":   v_lay,
        "v0_twophase_B":  v_tp,
        "v0_dualchannel": dual.enterprise_value,
        "lambda_vector":  list(dual.lambda_vector),
    }


@st.cache_data(show_spinner=False)
def _live_mc_bands(scenario_slug: str, firm_slug: str,
                    lambda_p2: float, lambda_p3: float) -> dict:
    """Run a lightweight 1500-run unified MC for the live B.5 figure.

    Lower than the 5000-run figure-rendering MC of Sprint 5 so the
    Streamlit interaction stays responsive (≈ 0.5 s on a laptop).
    """
    from src.dual_channel_mc import MonteCarloSpec, run_monte_carlo
    scn = _load_scenario(scenario_slug)
    firms = config.firms_appendix_b()
    firm = firms[firm_slug]
    macro = firms["macro"]
    phases = _phases_for(firm_slug)
    trl = TRLTrajectory(
        year_labels=scn["trl_trajectory"]["year_labels"],
        trl_by_year=scn["trl_trajectory"]["trl_by_year"],
    )
    mc = run_monte_carlo(
        scenario=scn,
        phases=phases,
        fcf_two_phase=list(firm["fcf_usd"]),
        risk_free_rate_b=float(macro["risk_free_rate"]),
        equity_risk_premium_b=float(macro["equity_risk_premium"]),
        second_valley_drag_b=float(firm["second_valley_drag"]),
        classical_rate=_classical_rate_for(scn),
        layered_inputs=_layered_inputs(scn),
        trl_traj=trl,
        lambda_phase2_center=lambda_p2,
        spec=MonteCarloSpec(n_runs=1500, seed=42),
    )
    return dict(mc.bands)


def _build_live_figure_b5(scenario_slug: str, firm_slug: str,
                           paths: dict):
    """Render Figure B.5 with live point estimates and cached MC bands."""
    color_for = {
        "neurocertify": live_figures.NEUROCERTIFY_COLOR,
        "dataflow":     live_figures.DATAFLOW_COLOR,
    }
    bands = _live_mc_bands(scenario_slug, firm_slug,
                            paths.get("_lp2_for_cache", 0.0),  # placeholder
                            paths.get("_lp3_for_cache", 0.0))  # placeholder
    # NB: we deliberately do NOT pass the slider values into the MC
    # call's cache key for now — that would invalidate the cache on
    # every slider tick. The MC bands are an order-of-magnitude
    # diagnostic, not a precise distribution sensitive to the central
    # lambda values. A future iteration can wire λ into the MC cache.
    firm_dict = {
        firm_slug: {
            "label": ("NeuroCertify (deep-tech, HIT)" if firm_slug == "neurocertify"
                       else "DataFlow Pro (Software, commoditizing)"),
            "color": color_for[firm_slug],
            "v0_classical":   paths["v0_classical"],
            "v0_layered_A":   paths["v0_layered_A"],
            "v0_twophase_B":  paths["v0_twophase_B"],
            "v0_dualchannel": paths["v0_dualchannel"],
            "bands": bands,
        }
    }
    stages = config.us_funding_stage_benchmarks()
    funding_lines = {
        "seed":     float(stages["seed"]["median_premoney_usd"]),
        "series_a": float(stages["series_a"]["median_premoney_usd"]),
        "series_b": float(stages["series_b"]["median_premoney_usd"]),
    }
    return live_figures.figure_b5_four_path_reconciliation(
        firms=firm_dict, funding_stage_lines=funding_lines,
    )
