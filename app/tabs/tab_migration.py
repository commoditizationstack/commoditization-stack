"""Tab — Section 7.5: Migration dynamics with AI orchestrator function.

Shows fig21 (reference firm), fig22 (NeuroCertify), fig23 (DataFlow Pro)
plus live computation of break-even quarters for the user's calibration.
"""

from pathlib import Path

import streamlit as st

from app.shared import state
from src.migration_dynamics import reference_firm_migration, case_study_migration

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()

    st.header("⏱ Migration Dynamics (Section 7.5)")
    st.markdown(
        f"""
        Currently selected jurisdiction: **{state.country_label()}**

        Section 7.5 introduces the AI-orchestrator function as a **permanent**
        labor input alongside the assessment phase, dual-operation overhead,
        retention bonus, and sigmoidal learning curve. The result is a
        temporal break-even arithmetic that the steady-state Section 7 analysis
        conceals.

        > 💵 All monetary values in USD. Calibrations from Sections 7.2 and 7.5.
        """
    )

    # Live computation under current country
    country = state.current_country()
    st.subheader(f"Live break-even computation for current jurisdiction")
    ref_result = reference_firm_migration(country)

    col1, col2, col3 = st.columns(3)
    with col1:
        be = ref_result.break_even_quarter
        be_str = f"Q{be:.1f} ({be*3:.0f} months)" if be else "> 5 years"
        st.metric("Reference firm break-even", be_str)
    with col2:
        st.metric("Annual gross saving",
                   f"${ref_result.annual_gross_saving_usd / 1e6:.2f}M")
    with col3:
        st.metric("5-year cumulative gain",
                   f"${ref_result.cumulative_5y_post_t0_usd / 1e6:.2f}M")

    # ===== Live cash-flow trajectories across 3 jurisdictions =====
    st.markdown("---")
    st.subheader("📈 Reference firm migration cash flow (live)")
    st.caption("Trajectories regenerate when you change orchestrator ratio, "
                "premium, learning curve, or loaded SWE cost in ⚙️ Configuration.")
    results = {
        j: reference_firm_migration(j)
        for j in ["brazil", "france", "united_states"]
    }
    from app.shared import live_figures
    fig = live_figures.migration_cash_flow_trajectories(results)
    st.pyplot(fig, use_container_width=True)

    # ===== Paper PNGs collapsed =====
    with st.expander("📷 Original paper figures (PNG snapshots)", expanded=False):
        for fname, title, caption in [
            ("fig21_migration_reference_firm.png",
             "Figure 11 — Reference firm (50 engineers, 60% substitution)",
             "Cumulative cash-flow trajectory with phase shading and decomposition table."),
            ("fig22_neurocertify_migration.png",
             "Figure 12 — NeuroCertify (Brazilian + French arms + consolidated)",
             "All three trajectories net-negative within 5y."),
            ("fig23_dataflow_migration.png",
             "Figure 13 — DataFlow Pro (3 substitution scenarios)",
             "All scenarios reach break-even within 5y."),
        ]:
            st.markdown(f"**{title}**")
            fp = FIG_DIR / fname
            if fp.exists():
                st.image(str(fp), caption=caption, use_container_width=True)
            else:
                st.warning(f"Figure `{fname}` not yet generated.")
