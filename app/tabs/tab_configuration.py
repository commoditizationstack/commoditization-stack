"""Configuration tab — full editing UI for every tunable parameter.

Organises ~120 variables from parameters.yaml into 13 collapsible expanders,
each grouped by area of the framework. Editing any slider records an
override in st.session_state; all other tabs re-render with the override
applied on the next interaction.

The tab is purely an editor — no simulation logic. The display of results
lives in the topic-specific tabs (Seven Layers, Jurisdictional, Migration, ...).
"""

from __future__ import annotations

import streamlit as st

from app.shared import state
from src import config


def _slider(label: str, dot_path: str, *,
            min_value: float, max_value: float, step: float,
            help: str = "", format: str = "%.3f") -> float:
    """Slider that reads override (if set) or YAML default."""
    # Streamlit refuses mixed int/float bounds — coerce everything to float.
    min_value = float(min_value)
    max_value = float(max_value)
    step = float(step)
    default = float(config.get(dot_path, min_value))
    current = float(state.get_override(dot_path, default))
    key = f"cfg_{dot_path}"
    # Pre-sync canonical value into session_state so an edit made in
    # another tab (Research Levers, topical sliders) is reflected here.
    st.session_state[key] = current
    val = st.slider(label, min_value=min_value, max_value=max_value,
                    value=current, step=step, help=help, format=format,
                    key=key)
    if abs(val - default) > 1e-12:
        state.set_override(dot_path, val)
    elif dot_path in st.session_state.get("overrides", {}):
        # User dragged it back to default → drop the override
        del st.session_state["overrides"][dot_path]
    return val


def _number(label: str, dot_path: str, *, help: str = "",
            min_value: float = 0.0, max_value: float = 1e15,
            step: float = 1.0, format: str = "%.0f"):
    """Number input that reads override (if set) or YAML default.

    Streamlit requires every numeric argument to share a single type.
    When `format` is "%d" we coerce everything to int (otherwise Streamlit
    warns "value has type float, but format %d displays as integer");
    otherwise we coerce to float.
    """
    as_int = format == "%d"
    cast = int if as_int else float
    min_value = cast(min_value)
    max_value = cast(max_value)
    step = cast(step) if as_int else float(step)
    default = cast(config.get(dot_path, min_value))
    current = cast(state.get_override(dot_path, default))
    key = f"cfg_{dot_path}"
    # Pre-sync canonical value into session_state for cross-tab sync.
    st.session_state[key] = current
    val = st.number_input(label, min_value=min_value, max_value=max_value,
                          value=current, step=step, help=help, format=format,
                          key=key)
    tol = 0 if as_int else 1e-9
    if abs(val - default) > tol:
        state.set_override(dot_path, val)
    elif dot_path in st.session_state.get("overrides", {}):
        del st.session_state["overrides"][dot_path]
    return val


def render():
    state.init_session_state()

    st.header("⚙️ Configuration — All Tunable Parameters")
    st.markdown(
        """
        Every numeric parameter in the framework is editable here.
        Changes are recorded as **overrides** layered on top of
        `config/parameters.yaml`; all other tabs respect the overrides
        on the next interaction.

        Use the sidebar **💾 Scenario YAML** controls to save your overrides
        as a portable file or clear them all back to defaults.

        > 💵 **All monetary values are in USD.**
        """
    )

    n_overrides = len(st.session_state.get("overrides", {}))
    if n_overrides > 0:
        st.info(f"📝 {n_overrides} override(s) currently active. "
                f"Use **🗑️ Clear** in the sidebar to reset to YAML defaults.")

    p = state.effective_parameters()

    # ===================================================================
    # 1. SIMULATION + MONTE CARLO
    # ===================================================================
    with st.expander("⚙️ Simulation core (seed, MC runs, horizon)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            _number("Random seed", "simulation.random_seed",
                    min_value=0, max_value=2**31 - 1, step=1, format="%d")
            _number("Monte Carlo runs", "simulation.monte_carlo_runs",
                    min_value=100, max_value=100000, step=1000, format="%d",
                    help="Number of Monte Carlo iterations per scenario.")
        with col2:
            _number("Time horizon (quarters)", "simulation.time_horizon_quarters",
                    min_value=4, max_value=80, step=4, format="%d")
        st.markdown("**Monte Carlo perturbation envelopes (log-normal CV)**")
        col1, col2 = st.columns(2)
        with col1:
            _slider("Team size CV", "monte_carlo.team_size_cv",
                    min_value=0.0, max_value=1.0, step=0.01)
            _slider("Burn rate CV", "monte_carlo.burn_rate_cv",
                    min_value=0.0, max_value=1.0, step=0.01)
            _slider("Layer velocity CV", "monte_carlo.layer_velocity_cv",
                    min_value=0.0, max_value=1.0, step=0.01)
        with col2:
            _slider("AI substitution CV", "monte_carlo.ai_substitution_cv",
                    min_value=0.0, max_value=1.0, step=0.01)
            _slider("Market multiple CV", "monte_carlo.market_multiple_cv",
                    min_value=0.0, max_value=1.0, step=0.01)

    # ===================================================================
    # 2. SEVEN-LAYER STACK
    # ===================================================================
    with st.expander("🧬 Seven-layer stack (velocities + substitutabilities, Section 4)",
                      expanded=False):
        st.caption("velocity = annual rate of change of substitutability; "
                   "negative = anti-commoditizing.")
        for layer_id in ["layer_1_infra_inference", "layer_1_infra_training",
                          "layer_2_foundation_models", "layer_3_capability_access",
                          "layer_4_codified_synthesis", "layer_5_hypothesis",
                          "layer_6_institutional"]:
            label = p["stack_layers"][layer_id].get("name", layer_id)
            st.markdown(f"**{label}**")
            col1, col2 = st.columns(2)
            with col1:
                _slider(f"velocity ({layer_id})",
                        f"stack_layers.{layer_id}.velocity",
                        min_value=-0.5, max_value=0.5, step=0.01,
                        help="Annual rate of change of substitutability "
                             "(logit-shift per year).")
            with col2:
                _slider(f"substitutability_2026 ({layer_id})",
                        f"stack_layers.{layer_id}.substitutability_2026",
                        min_value=0.0, max_value=1.0, step=0.01,
                        help="Substitutability at simulation start (0..1).")

    # ===================================================================
    # 3. KNOWLEDGE REGIMES (Layer 7 / K7)
    # ===================================================================
    with st.expander("🌐 Knowledge regimes (Layer 7 / K₇, Section 4.1)",
                      expanded=False):
        _slider("Cross-border friction (when target ≠ acquirer bloc)",
                "knowledge_regimes.cross_border_friction",
                min_value=0.0, max_value=1.0, step=0.01,
                help="Reduction in effective substitution potential under "
                     "cross-bloc acquisition.")
        _slider("Layer-5 judgment bias factor floor",
                "knowledge_regimes.layer5_judgment_bias_factor_floor",
                min_value=0.0, max_value=0.5, step=0.01)
        st.markdown("**Reference K₇ regimes** (illustrative)")
        for regime in ["globalized_2020", "current_2026", "fragmented_2030"]:
            r = p["knowledge_regimes"]["regimes"][regime]
            st.markdown(f"*{regime}* — {r.get('notes', '')[:120]}...")
            col1, col2, col3 = st.columns(3)
            with col1:
                _slider(f"K_coefficient ({regime})",
                        f"knowledge_regimes.regimes.{regime}.K_coefficient",
                        min_value=0.0, max_value=1.0, step=0.01)
            with col2:
                _slider(f"L4 modulator ({regime})",
                        f"knowledge_regimes.regimes.{regime}.layer4_substitution_modulator",
                        min_value=0.0, max_value=1.0, step=0.01)
            with col3:
                _slider(f"L5 bias factor ({regime})",
                        f"knowledge_regimes.regimes.{regime}.layer5_judgment_bias_factor",
                        min_value=0.0, max_value=1.5, step=0.01)

    # ===================================================================
    # 4. STARTUP GROWTH DYNAMICS
    # ===================================================================
    with st.expander("🚀 Startup growth dynamics", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            _slider("Runway months before team can grow",
                    "startup.growth.runway_months_before_team_can_grow",
                    min_value=0.0, max_value=24.0, step=1.0, format="%.0f")
            _slider("Max team-size multiplier",
                    "startup.growth.max_team_size_multiplier",
                    min_value=1.0, max_value=20.0, step=1.0, format="%.0f")
            _slider("Team growth per month",
                    "startup.growth.team_growth_per_month",
                    min_value=0.0, max_value=0.30, step=0.01)
            _slider("Base SaaS growth rate (monthly)",
                    "startup.growth.base_saas_growth_rate",
                    min_value=0.0, max_value=0.50, step=0.01)
        with col2:
            _slider("Seed ARR threshold (USD)",
                    "startup.growth.seed_arr_threshold_usd",
                    min_value=0.0, max_value=200000.0, step=5000.0, format="%.0f")
            _slider("Seed ARR per engineer-month (USD)",
                    "startup.growth.seed_arr_per_engineer_month_usd",
                    min_value=0.0, max_value=5000.0, step=50.0, format="%.0f")
            _slider("TRL growth per month",
                    "startup.growth.trl_growth_per_month",
                    min_value=0.0, max_value=0.30, step=0.01)
            _slider("SaaS projection growth rate (annual)",
                    "startup.growth.saas_projection_growth_rate",
                    min_value=1.0, max_value=3.0, step=0.05)
        st.markdown("**Funding events (Series A/B/C)**")
        col1, col2, col3 = st.columns(3)
        with col1:
            _number("Series A month", "startup.funding_events.series_a_month",
                    min_value=0, max_value=60, step=1, format="%d")
            _number("Series A min USD", "startup.funding_events.series_a_min_usd",
                    min_value=0.0, max_value=5e8, step=1e5)
        with col2:
            _number("Series B month", "startup.funding_events.series_b_month",
                    min_value=0, max_value=60, step=1, format="%d")
            _number("Series B min USD", "startup.funding_events.series_b_min_usd",
                    min_value=0.0, max_value=5e8, step=1e6)
        with col3:
            _number("Series C month", "startup.funding_events.series_c_month",
                    min_value=0, max_value=60, step=1, format="%d")
            _number("Series C min USD", "startup.funding_events.series_c_min_usd",
                    min_value=0.0, max_value=5e8, step=1e6)
        _number("Market size (USD)", "startup.market_size_usd",
                min_value=0.0, max_value=1e12, step=1e8)

    # ===================================================================
    # 5. VALUATION (Damodaran, comparables, Berkus)
    # ===================================================================
    with st.expander("💰 Valuation (Damodaran inverted, comparables, Berkus, Section 6)",
                      expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            _slider("Damodaran classical discount rate",
                    "valuation.damodaran_key_person_discount_classical",
                    min_value=0.0, max_value=0.50, step=0.005)
            _slider("Threshold layer-4 share for inversion",
                    "valuation.damodaran_inverted_threshold_layer4_share",
                    min_value=0.0, max_value=1.0, step=0.01)
            _slider("Max premium when inverted",
                    "valuation.damodaran_inverted_max_premium",
                    min_value=0.0, max_value=0.50, step=0.01)
        with col2:
            _slider("Min AI substitution for inversion",
                    "valuation.damodaran_inversion_min_substitution_potential",
                    min_value=0.0, max_value=1.0, step=0.05)
            _slider("Terminal growth (Damodaran full)",
                    "valuation.damodaran_full_terminal_growth",
                    min_value=0.0, max_value=0.10, step=0.005)
            _slider("Comparable revenue multiple baseline",
                    "valuation.comparable_revenue_multiple_baseline",
                    min_value=1.0, max_value=30.0, step=0.5)
        _number("Berkus factor cap (USD)",
                "valuation.berkus_factor_cap_usd",
                min_value=0.0, max_value=2e6, step=1e4)

    # ===================================================================
    # 6. VALUATION LAYERED (Appendix A)
    # ===================================================================
    with st.expander("📐 Layered DCF (Appendix A: TRL premium, layer risk, exposure)",
                      expanded=False):
        st.markdown("**TRL → discount premium schedule**")
        cols = st.columns(3)
        for i, trl in enumerate(range(1, 10)):
            with cols[i % 3]:
                _slider(f"TRL {trl}",
                        f"valuation_layered.trl_discount_premium.{trl}",
                        min_value=0.0, max_value=0.30, step=0.005)
        st.markdown("**Layer risk coefficients (per-layer signed premium)**")
        layer_keys = ["layer_1_infra", "layer_2_foundation", "layer_3_capability",
                       "layer_4_codified", "layer_5_judgment",
                       "layer_6_institutional", "layer_7_crossborder"]
        cols = st.columns(2)
        for i, lk in enumerate(layer_keys):
            with cols[i % 2]:
                _slider(f"{lk}",
                        f"valuation_layered.layer_risk_coefficients.{lk}",
                        min_value=-0.10, max_value=0.20, step=0.005)
        st.markdown("**Default layer exposure (must sum to ~1.0)**")
        cols = st.columns(2)
        for i, lk in enumerate(layer_keys):
            with cols[i % 2]:
                _slider(f"Default exposure {lk}",
                        f"valuation_layered.default_layer_exposure.{lk}",
                        min_value=0.0, max_value=1.0, step=0.01)

    # ===================================================================
    # 7. VALUATION TWO-PHASE (Appendix B)
    # ===================================================================
    with st.expander("🔄 Two-phase CAPM/WACC (Appendix B)", expanded=False):
        st.markdown("**Generic defaults — firm-specific in section 'Case studies' below**")
        col1, col2 = st.columns(2)
        with col1:
            _slider("Phase 1 end year",
                    "valuation_two_phase.default_phase_boundaries.phase_1_end_year",
                    min_value=1.0, max_value=6.0, step=1.0, format="%.0f")
            _slider("Phase 2 end year",
                    "valuation_two_phase.default_phase_boundaries.phase_2_end_year",
                    min_value=2.0, max_value=10.0, step=1.0, format="%.0f")
        with col2:
            _slider("Default effective tax rate",
                    "valuation_two_phase.default_effective_tax_rate",
                    min_value=0.0, max_value=0.50, step=0.01)
        st.markdown("**Default per-phase betas / D-E / Kd spreads**")
        for phase in ["phase_1", "phase_2", "phase_3"]:
            st.markdown(f"*{phase.replace('_', ' ').title()}*")
            col1, col2, col3 = st.columns(3)
            with col1:
                _slider(f"β unlevered {phase}",
                        f"valuation_two_phase.default_betas.{phase}",
                        min_value=0.0, max_value=3.0, step=0.05)
            with col2:
                _slider(f"D/E {phase}",
                        f"valuation_two_phase.default_de_ratios.{phase}",
                        min_value=0.0, max_value=1.0, step=0.01)
            with col3:
                _slider(f"Kd spread {phase}",
                        f"valuation_two_phase.default_kd_spreads.{phase}",
                        min_value=0.0, max_value=0.20, step=0.005)

    # ===================================================================
    # 8. JURISDICTIONS (per country)
    # ===================================================================
    with st.expander("🌎 Jurisdictions (Brazil / France / United States, Section 7)",
                      expanded=False):
        sub_tabs = st.tabs(["🇧🇷 Brazil", "🇫🇷 France", "🇺🇸 United States"])
        for tab, country in zip(sub_tabs, ["brazil", "france", "united_states"]):
            with tab:
                col1, col2 = st.columns(2)
                with col1:
                    _slider(f"Labor cost multiplier ({country})",
                            f"jurisdictions.defaults.{country}.labor_cost_multiplier",
                            min_value=1.0, max_value=2.5, step=0.01)
                    _slider(f"Termination cost fraction ({country})",
                            f"jurisdictions.defaults.{country}.termination_cost_fraction",
                            min_value=0.0, max_value=1.0, step=0.01)
                    _slider(f"AI service overhead ({country})",
                            f"jurisdictions.defaults.{country}.ai_service_overhead",
                            min_value=1.0, max_value=2.0, step=0.01)
                with col2:
                    _slider(f"Notice period fraction ({country})",
                            f"jurisdictions.defaults.{country}.notice_period_fraction",
                            min_value=0.0, max_value=1.0, step=0.01)
                    _slider(f"AI opex deductibility ({country})",
                            f"jurisdictions.defaults.{country}.ai_opex_deductibility",
                            min_value=0.0, max_value=1.0, step=0.05)
                    _slider(f"Vendor risk WACC premium ({country})",
                            f"jurisdictions.defaults.{country}.vendor_risk_wacc_premium",
                            min_value=0.0, max_value=0.05, step=0.001)

    # ===================================================================
    # 9. MIGRATION DYNAMICS (Section 7.5)
    # ===================================================================
    with st.expander("⏱ Migration dynamics (Section 7.5: orchestrator + transition)",
                      expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            _slider("Assessment phase (months)",
                    "migration_dynamics.assessment_months",
                    min_value=0.0, max_value=24.0, step=1.0, format="%.0f")
            _slider("Orchestrator ratio (engineers per orchestrator)",
                    "migration_dynamics.orchestrator_ratio",
                    min_value=1.0, max_value=50.0, step=1.0, format="%.0f")
            _slider("Orchestrator premium over senior SWE",
                    "migration_dynamics.orchestrator_premium_pct",
                    min_value=0.0, max_value=0.50, step=0.01)
        with col2:
            _slider("Dual-operation overhead (quarters)",
                    "migration_dynamics.dual_operation_overhead_quarters",
                    min_value=0.0, max_value=8.0, step=1.0, format="%.0f")
            _slider("Retention bonus (quarters)",
                    "migration_dynamics.retention_bonus_quarters",
                    min_value=0.0, max_value=8.0, step=1.0, format="%.0f")
            _slider("Retention bonus fraction",
                    "migration_dynamics.retention_bonus_fraction",
                    min_value=0.0, max_value=0.50, step=0.01)
        _number("AI tooling cost per developer-year (USD)",
                "migration_dynamics.ai_tooling_cost_per_dev_usd_year",
                min_value=0.0, max_value=100000.0, step=1000.0)

        st.markdown("**Senior SWE loaded annual cost per jurisdiction**")
        col1, col2, col3 = st.columns(3)
        with col1:
            _number("Brazil",
                    "migration_dynamics.loaded_swe_cost_usd_year.brazil",
                    min_value=0.0, max_value=1e6, step=5000.0)
        with col2:
            _number("France",
                    "migration_dynamics.loaded_swe_cost_usd_year.france",
                    min_value=0.0, max_value=1e6, step=5000.0)
        with col3:
            _number("United States",
                    "migration_dynamics.loaded_swe_cost_usd_year.united_states",
                    min_value=0.0, max_value=1e6, step=5000.0)

    # ===================================================================
    # 10. CASE STUDIES (NeuroCertify + DataFlow Pro)
    # ===================================================================
    with st.expander("🏢 Case studies (NeuroCertify + DataFlow Pro, Appendices A, B, E)",
                      expanded=False):
        st.markdown("**NeuroCertify (deep-tech, regulated, HIT)**")
        col1, col2 = st.columns(2)
        with col1:
            _slider("Layer-4 share",
                    "case_studies_dynamic.neurocertify.layer_4_share",
                    min_value=0.0, max_value=1.0, step=0.05)
            _slider("AI substitution potential",
                    "case_studies_dynamic.neurocertify.ai_substitution_potential",
                    min_value=0.0, max_value=1.0, step=0.05)
        with col2:
            _slider("Second-valley drag",
                    "case_studies_dynamic.neurocertify.second_valley_drag",
                    min_value=0.0, max_value=0.50, step=0.01)
        st.markdown("**DataFlow Pro (commoditizing, B2B SaaS)**")
        col1, col2 = st.columns(2)
        with col1:
            _slider("Layer-4 share ",
                    "case_studies_dynamic.dataflow_pro.layer_4_share",
                    min_value=0.0, max_value=1.0, step=0.05)
            _slider("AI substitution potential ",
                    "case_studies_dynamic.dataflow_pro.ai_substitution_potential",
                    min_value=0.0, max_value=1.0, step=0.05)
        with col2:
            _slider("Second-valley drag ",
                    "case_studies_dynamic.dataflow_pro.second_valley_drag",
                    min_value=0.0, max_value=0.50, step=0.01)

    # ===================================================================
    # 11. STREAMING CASE (Appendix D)
    # ===================================================================
    with st.expander("🎬 Streaming case (Appendix D)", expanded=False):
        _number("Annual revenue (USD)",
                "streaming_case.annual_revenue_usd",
                min_value=0.0, max_value=1e12, step=1e9)
        _slider("Standard plan price (USD/month)",
                "streaming_case.standard_plan_price_usd_monthly",
                min_value=0.0, max_value=50.0, step=0.50)
        _number("Engineers count",
                "streaming_case.engineers_count",
                min_value=0, max_value=50000, step=100, format="%d")
        _number("Support agents count",
                "streaming_case.support_agents_count",
                min_value=0, max_value=20000, step=100, format="%d")
        st.markdown("**Three substitution scenarios**")
        col1, col2, col3 = st.columns(3)
        with col1:
            _slider("Conservative",
                    "streaming_case.substitution_scenarios.conservative_pct",
                    min_value=0.0, max_value=1.0, step=0.05)
        with col2:
            _slider("Moderate",
                    "streaming_case.substitution_scenarios.moderate_pct",
                    min_value=0.0, max_value=1.0, step=0.05)
        with col3:
            _slider("Aggressive",
                    "streaming_case.substitution_scenarios.aggressive_pct",
                    min_value=0.0, max_value=1.0, step=0.05)
        _slider("Cross-bloc friction",
                "streaming_case.cross_bloc_friction_pct",
                min_value=0.0, max_value=1.0, step=0.05)

    # ===================================================================
    # 12. FISCAL BLOCS (Appendix D.6)
    # ===================================================================
    with st.expander("🏛 Fiscal blocs (Appendix D.6)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            _slider("Horizon (years)",
                    "fiscal_blocs.horizon_years",
                    min_value=1.0, max_value=20.0, step=1.0, format="%.0f")
            _slider("Sector workforce multiplier",
                    "fiscal_blocs.sector_workforce_multiplier",
                    min_value=1.0, max_value=30.0, step=1.0, format="%.0f")
            _slider("Transfer pricing parent share",
                    "fiscal_blocs.transfer_pricing_parent_share",
                    min_value=0.0, max_value=1.0, step=0.05)
        with col2:
            _slider("Transfer pricing subsidiary share",
                    "fiscal_blocs.transfer_pricing_subsidiary_share",
                    min_value=0.0, max_value=1.0, step=0.05)
        st.markdown("**Corporate tax rate per country**")
        col1, col2, col3 = st.columns(3)
        with col1:
            _slider("Brazil",
                    "fiscal_blocs.corporate_tax_rate.brazil",
                    min_value=0.0, max_value=0.60, step=0.01)
        with col2:
            _slider("France",
                    "fiscal_blocs.corporate_tax_rate.france",
                    min_value=0.0, max_value=0.60, step=0.01)
        with col3:
            _slider("United States",
                    "fiscal_blocs.corporate_tax_rate.united_states",
                    min_value=0.0, max_value=0.60, step=0.01)

    # ===================================================================
    # 13. MACRO + FUNDING STAGES + STRUCTURAL
    # ===================================================================
    with st.expander("📊 Macro + funding stages + structural constants",
                      expanded=False):
        st.markdown("**Macro**")
        col1, col2, col3 = st.columns(3)
        with col1:
            _slider("Risk-free rate", "macro.risk_free_rate",
                    min_value=0.0, max_value=0.15, step=0.0025)
        with col2:
            _slider("Equity risk premium", "macro.equity_risk_premium",
                    min_value=0.0, max_value=0.20, step=0.005)
        with col3:
            _slider("Terminal growth rate", "macro.terminal_growth_rate",
                    min_value=0.0, max_value=0.10, step=0.005)
        st.markdown("**Funding stages (Carta Q3 2025)**")
        col1, col2 = st.columns(2)
        with col1:
            _slider("AI-native round reduction",
                    "funding_stages_carta.ai_native_round_reduction",
                    min_value=0.0, max_value=0.80, step=0.05)
            _slider("Legacy dilution per round",
                    "funding_stages_carta.legacy_dilution_per_round",
                    min_value=0.0, max_value=0.50, step=0.01)
        with col2:
            _slider("AI-native dilution per round",
                    "funding_stages_carta.ai_native_dilution_per_round",
                    min_value=0.0, max_value=0.50, step=0.01)
        st.markdown("**Structural constants** (rarely tuned)")
        col1, col2 = st.columns(2)
        with col1:
            _slider("Stack-layer logit scaling",
                    "structural.stack_layer_logit_scaling",
                    min_value=0.5, max_value=5.0, step=0.1)
            _slider("Substitutability clip min",
                    "structural.substitutability_clip_min",
                    min_value=0.0, max_value=0.10, step=0.005)
        with col2:
            _slider("Substitutability clip max",
                    "structural.substitutability_clip_max",
                    min_value=0.90, max_value=1.0, step=0.005)

    st.markdown("---")
    st.caption(
        f"All values above are in **USD** unless otherwise noted. "
        f"Active overrides: **{len(st.session_state.get('overrides', {}))}**. "
        f"Use **💾 Scenario YAML** in the sidebar to save your scenario."
    )
