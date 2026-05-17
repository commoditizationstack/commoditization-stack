"""Tab — Appendix E: Dynamic analysis of NeuroCertify + DataFlow Pro."""

from pathlib import Path

import streamlit as st

from app.shared import state
from src.fragility import case_studies_fragility

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()

    st.header("🏢 Appendix E — Dynamic Case Companies")
    st.markdown(
        """
        Appendix E extends the static valuation of Appendix A into the
        **temporal dimension**: migration cash flow, capital trajectory
        through funding stages, phase-conditional risk curves, founder
        dilution, and fragility map.

        Two contrasting illustrative firms:
        - **NeuroCertify** — deep-tech, regulated, Layer-6-rich (resilient)
        - **DataFlow Pro** — commoditizing-tech, Layer-4-heavy (fragile)

        > 💵 All monetary values in USD.
        """
    )

    # Live fragility computation
    st.subheader("Fragility zone (live)")
    fr = case_studies_fragility()
    col1, col2 = st.columns(2)
    with col1:
        nc = fr["neurocertify"]
        st.metric("NeuroCertify",
                   f"index = {nc.fragility_index:.2f}",
                   delta=nc.zone.title(),
                   delta_color="normal" if nc.zone == "resilient" else "inverse")
    with col2:
        df = fr["dataflow_pro"]
        st.metric("DataFlow Pro",
                   f"index = {df.fragility_index:.2f}",
                   delta=df.zone.title(),
                   delta_color="normal" if df.zone == "resilient" else "inverse")

    st.markdown("---")
    st.subheader("Paper figures")

    nc_tab, df_tab, joint_tab = st.tabs([
        "📘 NeuroCertify", "📕 DataFlow Pro", "📊 Joint comparison"
    ])

    with nc_tab:
        st.markdown("#### NeuroCertify migration cash flow")
        fp = FIG_DIR / "fig22_neurocertify_migration.png"
        if fp.exists():
            st.image(str(fp),
                      caption="All trajectories net-negative within 5y "
                              "(orchestrator overhead > gross saving).",
                      use_container_width=True)
        else:
            st.warning("Figure not found. Run `python scripts/run_section_7_5_migration.py`.")

    with df_tab:
        st.markdown("#### DataFlow Pro migration (3 scenarios)")
        fp = FIG_DIR / "fig23_dataflow_migration.png"
        if fp.exists():
            st.image(str(fp),
                      caption="All scenarios reach break-even within 5y, but "
                              "absolute gains are modest at small scale.",
                      use_container_width=True)
        else:
            st.warning("Figure not found. Run `python scripts/run_section_7_5_migration.py`.")

    with joint_tab:
        fig_titles = [
            ("fig31_appendix_e_migration.png", "E.1 — Combined migration trajectories"),
            ("fig32_appendix_e_capital.png", "E.2 — Capital trajectory by stage"),
            ("fig33_appendix_e_risk.png", "E.3 — Phase-conditional risk curves"),
            ("fig34_appendix_e_dilution.png", "E.4 — Dilution + investor multiple"),
            ("fig35_appendix_e_fragility.png", "E.5 — Fragility map (L4 × L6 space)"),
        ]
        for fname, title in fig_titles:
            with st.expander(title, expanded=False):
                fp = FIG_DIR / fname
                if fp.exists():
                    st.image(str(fp), use_container_width=True)
                else:
                    st.warning(f"Figure {fname} not found. "
                               f"Run `python scripts/run_appendix_e.py`.")
