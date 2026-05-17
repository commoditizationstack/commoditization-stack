"""Tab — Appendix F: Upstream value chain + structural sensitivities."""

from pathlib import Path

import streamlit as st

from app.shared import state
from src.upstream_chain import all_categories

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()

    st.header("🔗 Appendix F — Upstream Value Chain + Sensitivities")
    st.markdown(
        """
        Appendix F maps **seven categories of upstream AI value-chain firms**
        onto the seven-layer framework, and articulates three structural
        sensitivities the framework illuminates without forecasting their
        realisation:

        1. Capex of training to dynamics of financing
        2. Aggregate inference demand to the team-size adoption threshold
        3. Jurisdictional inversion premium to K₇

        The appendix is **conditional analysis**, not a forecast.
        """
    )

    # Upstream category list (live)
    st.subheader("Seven upstream firm categories")
    cats = all_categories()
    for cat in cats:
        with st.expander(f"**{cat.label}**", expanded=False):
            st.markdown(f"*{cat.structural_sensitivity}*")
            exposure_text = " | ".join(
                f"{k}: {v}" for k, v in cat.exposure.items() if v > 0
            )
            st.caption(f"Layer exposure (0..3): {exposure_text}")

    st.markdown("---")
    st.subheader("Paper figures")

    fig_titles = [
        ("fig36_appendix_f_scope.png",
         "F.1 — Scope of the framework (prices vs not-prices)"),
        ("fig37_appendix_f_mapping.png",
         "F.2 — 7 categories × 7 layers exposure matrix"),
        ("fig38_appendix_f_sensitivities.png",
         "F.3 — Three structural sensitivities"),
        ("fig39_appendix_f_asymmetries.png",
         "F.4 — Recovery composition asymmetries"),
    ]
    for fname, title in fig_titles:
        with st.expander(title, expanded=False):
            fp = FIG_DIR / fname
            if fp.exists():
                st.image(str(fp), use_container_width=True)
            else:
                st.warning(f"Figure {fname} not found. "
                           f"Run `python scripts/run_appendix_f.py`.")
