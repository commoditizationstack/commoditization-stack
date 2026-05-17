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

    fig_titles = [
        ("fig4_hype_cycle.png",
         "Figure 6 — Classical single-valley vs post-AI double-valley curve",
         "Classical Gartner curve shows recovery to plateau after one trough; "
         "the post-AI reformulation adds a second valley after the false "
         "recovery peak, reflecting competitor closure of the technical gap."),
        ("fig5_death_valley.png",
         "Figure 7 — Cash trajectory: classical vs post-AI",
         "Classical regime shows a single deep valley resolved by Series A "
         "funding. The post-AI regime shows a shallower first valley followed "
         "by a new second valley around month 24-36."),
    ]
    for fname, title, caption in fig_titles:
        st.markdown(f"#### {title}")
        fp = FIG_DIR / fname
        if fp.exists():
            st.image(str(fp), caption=caption, use_container_width=True)
        else:
            st.warning(f"Figure {fname} not found. "
                       f"Run `python scripts/run_deterministic.py`.")
