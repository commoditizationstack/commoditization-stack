"""Tab — Section 7.1-7.4: Jurisdictional substitution & cross-border M&A.

Shows fig11 (jurisdictional inversion), fig12 (NPV decomposition), and
fig13 (cross-border M&A) regenerated under the user's current country
selection and parameter overrides.
"""

from pathlib import Path

import streamlit as st

from app.shared import state

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()

    st.header("🌎 Jurisdictional substitution (Section 7)")
    st.markdown(
        f"""
        Currently selected jurisdiction: **{state.country_label()}**

        Section 7 demonstrates the counterintuitive jurisdictional ordering
        of the inverted Damodaran key-person discount: high-wage jurisdictions
        produce the largest absolute inversion premium, despite lower statutory
        labor-cost multipliers, because the absolute base salary dominates the
        dollar value of the substitution.

        > 💵 All monetary values in USD.
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
                st.warning(f"Figure {fname} not found. "
                           f"Run `python scripts/run_jurisdictional.py`.")

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
