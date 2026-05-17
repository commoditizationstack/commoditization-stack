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

    st.markdown("---")
    st.subheader("Paper figures")

    fig_titles = [
        ("fig21_migration_reference_firm.png",
         "Figure 11 — Reference firm (50 engineers, 60% substitution)",
         "Cumulative cash-flow trajectory across the three jurisdictions, "
         "with assessment / transition / learning / steady state phases shaded. "
         "The United States reaches break-even fastest because its absolute "
         "loaded labor cost dominates the orchestrator overhead."),
        ("fig22_neurocertify_migration.png",
         "Figure 12 — NeuroCertify (Brazilian + French arms + consolidated)",
         "All three trajectories net-negative within the 5-year horizon: "
         "the orchestrator overhead floor exceeds the gross saving because "
         "Layer-4-substitutable subset is small (only 1-2 engineers per arm)."),
        ("fig23_dataflow_migration.png",
         "Figure 13 — DataFlow Pro (3 substitution scenarios)",
         "All scenarios reach break-even within 5 years, but cumulative gains "
         "are modest in absolute terms ($0.77M conservative to $3.05M aggressive) "
         "because the team itself is small (8 engineers)."),
    ]
    for fname, title, caption in fig_titles:
        st.markdown(f"#### {title}")
        fp = FIG_DIR / fname
        if fp.exists():
            st.image(str(fp), caption=caption, use_container_width=True)
        else:
            st.warning(f"Figure {fname} not found. "
                       f"Run `python scripts/run_section_7_5_migration.py`.")
