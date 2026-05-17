"""Tab — Section 7.1-7.4: Jurisdictional substitution & cross-border M&A.

Shows fig11 (jurisdictional inversion), fig12 (NPV decomposition), and
fig13 (cross-border M&A) regenerated under the user's current country
selection and parameter overrides.
"""

from pathlib import Path

import streamlit as st

from app.shared import components, state
from src.jurisdictional import (
    JURISDICTION_DEFAULTS, jurisdictional_inverted_discount,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()

    active = state.current_countries()
    active_labels = " · ".join(state.country_labels(active))

    # Hero strip: inversion premium per active bloc.
    try:
        p_now = state.effective_parameters()
        startup_cfg = p_now.get("startup", {})
        val_cfg = p_now["valuation"]
        ev_ref = 200_000_000.0
        salaries = {"brazil": 35000.0, "france": 75000.0,
                    "united_states": 165000.0}
        metrics = []
        for c in active[:4]:
            j = JURISDICTION_DEFAULTS[c]
            _, info = jurisdictional_inverted_discount(
                enterprise_value_usd=ev_ref,
                team_layer4_share=float(val_cfg.get(
                    "damodaran_inverted_threshold_layer4_share", 0.55)) + 0.15,
                ai_substitution_potential_layer4=float(val_cfg.get(
                    "damodaran_inversion_min_substitution_potential", 0.30))
                    + 0.30,
                n_employees=int(startup_cfg.get("n_employees",
                                                  startup_cfg.get(
                                                      "initial_team_size", 50))),
                avg_base_salary_usd=salaries.get(c, 80000.0),
                annual_ai_cost_per_replaced_employee_usd=float(
                    startup_cfg.get("annual_ai_cost_per_replaced_employee_usd",
                                     12000)),
                jurisdiction=j,
            )
            metrics.append((
                state.country_label(c),
                f"${info['inversion_premium_usd']/1e6:+.1f}M",
                info["regime"],
            ))
        components.hero_strip(metrics)
    except Exception:
        pass

    st.header("🌎 Jurisdictional substitution (Section 7)")
    st.markdown(
        f"""
        Active jurisdictions in this comparative view: **{active_labels}**

        Section 7 demonstrates the counterintuitive jurisdictional ordering
        of the inverted Damodaran key-person discount: high-wage jurisdictions
        produce the largest absolute inversion premium, despite lower statutory
        labor-cost multipliers, because the absolute base salary dominates the
        dollar value of the substitution.

        > 💵 All monetary values in USD. Edit the **🌎 Jurisdictions in scope**
        > multi-select in the sidebar to add or remove blocs from the comparison.
        """
    )

    # ===== Live figures (regenerate on every parameter change) =====
    from app.shared import live_figures
    p = state.effective_parameters()

    # Salary base per jurisdiction (illustrative; can be overridden)
    salaries = {
        "brazil": 35000.0,
        "france": 75000.0,
        "united_states": 165000.0,
    }
    jurisdiction_params = {
        c: p["jurisdictions"]["defaults"][c] for c in
        ["brazil", "france", "united_states"]
    }

    st.subheader("📊 Substitution NPV decomposition (live)")
    st.caption("Edit jurisdictional multipliers in ⚙️ Configuration → "
                "🌎 Jurisdictions and the bars below refresh instantly.")
    n_emp = st.slider("Employees substituted by AI tooling",
                        min_value=5, max_value=200, value=30, step=5,
                        key="jur_n_emp")
    fig_npv = live_figures.substitution_npv_bars(
        n_employees_replaced=n_emp,
        avg_base_salary_by_country=salaries,
        jurisdiction_params=jurisdiction_params,
        ai_cost_per_eng_year_usd=float(
            p["migration_dynamics"]["ai_tooling_cost_per_dev_usd_year"]),
        discount_rate=float(p["jurisdictions"]["default_discount_rate"]),
        horizon_years=int(p["jurisdictions"]["default_horizon_years"]),
        highlight_country=state.current_country(),
        countries=active,
    )
    st.pyplot(fig_npv, use_container_width=True)

    st.subheader("🌐 Cross-border M&A: inversion premium by operating-cost basis (live)")
    ev_million = st.slider("Reference enterprise value (USD millions)",
                             min_value=50, max_value=1000, value=200, step=50,
                             key="jur_ev")
    fig_cb = live_figures.crossborder_basis_bars(
        n_employees=n_emp,
        avg_base_salary_by_country=salaries,
        jurisdiction_params=jurisdiction_params,
        enterprise_value_usd=ev_million * 1e6,
        ai_cost_per_eng_year_usd=float(
            p["migration_dynamics"]["ai_tooling_cost_per_dev_usd_year"]),
        countries=active,
    )
    st.pyplot(fig_cb, use_container_width=True)

    # ===== Paper PNGs (collapsed by default to save space) =====
    with st.expander("📷 Original paper figures (PNG snapshots)", expanded=False):
        for fname, title, caption in [
            ("fig11_jurisdictional_inversion.png",
             "Figure 8 — Inversion premium across three jurisdictions",
             "Annual cost flow comparison (left) and inversion premium as % of "
             "$200M reference EV (right)."),
            ("fig12_substitution_npv_decomposition.png",
             "Figure 9 — Substitution NPV decomposition by jurisdiction",
             "5-year recurring savings (blue) net of one-time termination cost (orange)."),
            ("fig13_crossborder.png",
             "Figure 10 — Cross-border M&A operating-cost basis",
             "US-domiciled acquirer reproducing from HQ vs holding team locally."),
        ]:
            st.markdown(f"**{title}**")
            fp = FIG_DIR / fname
            if fp.exists():
                st.image(str(fp), caption=caption, use_container_width=True)
            else:
                st.warning(f"Figure `{fname}` not yet generated.")

    st.markdown("---")
    st.subheader("📖 Paper parameters (read-only — edit in ⚙️ Configuration)")
    p = state.effective_parameters()
    country = state.current_country()
    j = p["jurisdictions"]["defaults"][country]
    st.markdown(f"**Currently active jurisdiction: {state.country_label()}**")
    cols = st.columns(3)
    with cols[0]:
        st.metric("Labor cost multiplier", f"{j['labor_cost_multiplier']:.2f}")
        st.metric("Termination cost fraction", f"{j['termination_cost_fraction']:.2f}")
    with cols[1]:
        st.metric("AI service overhead", f"{j['ai_service_overhead']:.2f}")
        st.metric("Notice period fraction", f"{j['notice_period_fraction']:.3f}")
    with cols[2]:
        st.metric("Vendor risk WACC premium", f"{j['vendor_risk_wacc_premium']:.3f}")
        st.caption(j.get("notes", ""))
