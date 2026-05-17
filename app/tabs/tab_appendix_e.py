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

    # ===== Live fragility map =====
    from app.shared import live_figures
    p = state.effective_parameters()

    st.markdown("---")
    st.subheader("🗺 Fragility map (live)")
    st.caption("The two case-study firms positioned on the L4 × L6 fragility "
                "surface. Add a third 'custom firm' below to explore your own "
                "calibration. The map regenerates when you edit Layer-4 / "
                "Layer-6 shares for either firm in ⚙️ Configuration.")

    cs = p["case_studies_dynamic"]
    nc_exp = cs["neurocertify"]["layer_exposure"]
    df_exp = cs["dataflow_pro"]["layer_exposure"]

    firms_to_plot = [
        ("NeuroCertify", float(nc_exp["layer_4_codified"]),
         float(nc_exp["layer_6_institutional"]), "#2C5282"),
        ("DataFlow Pro", float(df_exp["layer_4_codified"]),
         float(df_exp["layer_6_institutional"]), "#7A1F1F"),
    ]

    with st.expander("➕ Add a custom firm to the fragility map", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            custom_l4 = st.slider("Custom firm — Layer 4 share",
                                    min_value=0.0, max_value=0.80, value=0.35,
                                    step=0.05, key="custom_firm_l4")
        with col2:
            custom_l6 = st.slider("Custom firm — Layer 6 share",
                                    min_value=0.0, max_value=0.55, value=0.25,
                                    step=0.05, key="custom_firm_l6")
        firms_to_plot.append(("Custom firm", custom_l4, custom_l6, "#F5C242"))

    fig = live_figures.fragility_map(
        l6_coefficient=float(p["fragility_index"]["l6_coefficient"]),
        color_vmin=float(p["fragility_index"]["color_vmin"]),
        color_vmax=float(p["fragility_index"]["color_vmax"]),
        firms=firms_to_plot,
    )
    st.pyplot(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📊 Paper figures (PNG snapshots)")

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
                      caption="All scenarios reach break-even within 5y.",
                      use_container_width=True)
        else:
            st.warning("Figure not found. Run `python scripts/run_section_7_5_migration.py`.")

    with joint_tab:
        for fname, title in [
            ("fig31_appendix_e_migration.png", "E.1 — Combined migration trajectories"),
            ("fig32_appendix_e_capital.png", "E.2 — Capital trajectory by stage"),
            ("fig33_appendix_e_risk.png", "E.3 — Phase-conditional risk curves"),
            ("fig34_appendix_e_dilution.png", "E.4 — Dilution + investor multiple"),
            ("fig35_appendix_e_fragility.png", "E.5 — Fragility map (paper version)"),
        ]:
            with st.expander(title, expanded=False):
                fp = FIG_DIR / fname
                if fp.exists():
                    st.image(str(fp), use_container_width=True)
                else:
                    st.warning(f"Figure {fname} not found. "
                               f"Run `python scripts/run_appendix_e.py`.")
