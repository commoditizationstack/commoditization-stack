"""Tab — Appendix G: Distributional + epistemic dimensions."""

from pathlib import Path

import streamlit as st

from app.shared import state
from src.distributional import compute_double_threshold, compute_xai_capacity_gap

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()

    st.header("⚖️ Appendix G — Distributional + Epistemic Dimensions")
    st.markdown(
        """
        Appendix G develops three dimensions of the framework in a
        complementary register:
        - **Distributional**: the team-size adoption threshold (Appendix E.2)
          has implications across the size distribution of regulated firms,
          producing a double threshold that small firms cannot cross.
        - **Stewardship**: public-resource decisions on AI-era research
          require prospective responsibility under accelerated obsolescence.
        - **Epistemic**: the cross-border knowledge regime has a
          geography-of-explicability dimension that compounds under low K₇.
        """
    )

    # Live computations
    st.subheader("Live computation of the two thresholds")
    d = compute_double_threshold()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Economic break-even",
                   f"{d.economic_break_even:.0f} engineers",
                   help="Headcount at which gross saving = orchestrator overhead.")
    with col2:
        st.metric("Compliance break-even",
                   f"{d.compliance_break_even:.0f} engineers",
                   help="Headcount at which gross saving = orchestrator + XAI infrastructure floor.")

    st.subheader("XAI capacity gap at year 8")
    xai = compute_xai_capacity_gap()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("K₇ = 1.0 (integrated)",
                   f"Δ = {xai.endpoint_gaps['k_1_0']:.2f}")
    with col2:
        st.metric("K₇ = 0.7 (current)",
                   f"Δ = {xai.endpoint_gaps['k_0_7']:.2f}")
    with col3:
        st.metric("K₇ = 0.45 (collapse)",
                   f"Δ = {xai.endpoint_gaps['k_0_45']:.2f}")

    st.markdown("---")
    st.subheader("Paper figures")

    fig_titles = [
        ("fig40_appendix_g_threshold.png",
         "G.1 — Double threshold for AI migration in regulated small firms",
         "Gross saving (green) vs orchestrator floor (grey dashed) vs "
         "orchestrator + XAI infrastructure floor (dark red dashed). "
         "Firms in the shaded gap zone can migrate economically but cannot "
         "satisfy regulatory compliance."),
        ("fig41_appendix_g_xai_gap.png",
         "G.2 — XAI capacity gap across two blocs under three K₇ regimes",
         "Lower K₇ produces a larger accumulated gap between blocs over the "
         "same time horizon. The endpoint gap grows from 0.05 (K=1.0) to "
         "0.34 (K=0.45) — an order of magnitude."),
    ]
    for fname, title, caption in fig_titles:
        st.markdown(f"#### {title}")
        fp = FIG_DIR / fname
        if fp.exists():
            st.image(str(fp), caption=caption, use_container_width=True)
        else:
            st.warning(f"Figure {fname} not found. "
                       f"Run `python scripts/run_appendix_g.py`.")
