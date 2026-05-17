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

    # ===== Live K7 sensitivity =====
    from app.shared import live_figures
    from src.upstream_chain import k7_sensitivity_per_jurisdiction

    st.markdown("---")
    st.subheader("📈 Inversion premium sensitivity to K₇ (live)")
    st.caption("Sensitivity of the inversion premium to the cross-border "
                "knowledge regime across three jurisdictions. The collapse "
                "threshold near K₇ ≈ 0.45 is invariant; the magnitudes scale "
                "with K₇ per Figure 4 of the paper.")
    curves = k7_sensitivity_per_jurisdiction()
    k_grid = curves.pop("k_grid")
    fig = live_figures.upstream_k7_sensitivity(k_grid=k_grid, curves=curves)
    st.pyplot(fig, use_container_width=True)

    # ===== Paper PNGs =====
    with st.expander("📷 Original paper figures (F.1–F.4)", expanded=False):
        for fname, title in [
            ("fig36_appendix_f_scope.png",
             "F.1 — Scope of the framework"),
            ("fig37_appendix_f_mapping.png",
             "F.2 — 7 categories × 7 layers exposure matrix"),
            ("fig38_appendix_f_sensitivities.png",
             "F.3 — Three structural sensitivities (full)"),
            ("fig39_appendix_f_asymmetries.png",
             "F.4 — Recovery composition asymmetries"),
        ]:
            st.markdown(f"**{title}**")
            fp = FIG_DIR / fname
            if fp.exists():
                st.image(str(fp), use_container_width=True)
            else:
                st.warning(f"Figure `{fname}` not yet generated.")
