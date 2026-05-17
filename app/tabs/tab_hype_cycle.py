"""Tab — Section 6.5: Hype Cycle & double-valley dynamic."""

from pathlib import Path

import streamlit as st

from app.shared import state

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()

    st.header("📈 Hype Cycle & Double-Valley Dynamic (Section 6.5)")
    st.markdown(
        """
        The classical Gartner Hype Cycle (Gartner, 1995) shows a single
        valley of disillusionment. Section 6.5 proposes a **double-valley**
        structure for the post-AI regime: a shallower classical valley
        followed by a second valley around month 24-36, when competitors
        close the technical gap through frontier-model substitution.

        This second valley has direct consequences for capital strategy
        (Appendix B reformulates CAPM/WACC/EVA/Gordon as phase-conditional).
        """
    )

    # ===== Live double-valley curve =====
    from app.shared import live_figures
    p = state.effective_parameters()
    st.subheader("📈 Hype Cycle: classical vs double-valley (live)")
    st.caption("Edit hype-cycle parameters in ⚙️ Configuration to reshape the "
                "trajectories. Adjust peak/trough/plateau heights to explore "
                "alternative regime calibrations.")
    fig = live_figures.hype_cycle_double_valley(
        n_quarters=32,
        classical_params=p["hype_cycle"]["classical"],
        post_genai_params=p["hype_cycle"]["post_genai"],
        classical_rise_exp=float(p["structural"]["classical_hype_rise_exponent"]),
        post_rise_exp=float(p["structural"]["post_genai_hype_rise_exponent"]),
    )
    st.pyplot(fig, use_container_width=True)

    # ===== Paper PNGs =====
    with st.expander("📷 Original paper figures + death-valley cash trajectory",
                       expanded=False):
        for fname, title, caption in [
            ("fig4_hype_cycle.png",
             "Figure 6 — Hype Cycle classical vs post-AI",
             "Reference paper figure."),
            ("fig5_death_valley.png",
             "Figure 7 — Cash trajectory classical vs post-AI",
             "Classical regime shows a single deep valley resolved by Series A "
             "funding. The post-AI regime shows a shallower first valley followed "
             "by a new second valley around month 24-36."),
        ]:
            st.markdown(f"**{title}**")
            fp = FIG_DIR / fname
            if fp.exists():
                st.image(str(fp), caption=caption, use_container_width=True)
            else:
                st.warning(f"Figure {fname} not found.")
