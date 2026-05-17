"""Tab — Company Valuation: per-user case studies under the framework.

Placeholder for the workflow:
  1. Researcher inputs a real company's profile (team composition, TRL,
     cash flows, jurisdictional arms, layer exposure).
  2. The framework computes its valuation under every method (classical
     Damodaran, layered DCF, two-phase DCF, comparables) using the
     parameter overlay active at that moment.
  3. The user iterates on parameters in 🔬 Research Levers /
     ⚙️ Configuration to study how the valuation moves across blocs.

The skeleton is in place so the tab is wired and reachable; the
end-to-end workflow will be filled in once the input schema settles.
"""

from __future__ import annotations

import streamlit as st

from app.shared import state


def render():
    state.init_session_state()

    st.header("🏢 Company Valuation — Bring your own case study")
    st.markdown(
        """
        This tab is being built so a researcher can drop in a real
        company's profile and watch its valuation move under every
        parameter the framework prices.

        > 🚧 **Coming next.** The current page is a wiring placeholder so
        > the multi-country selector, the parameter overlay, and the PDF
        > export pipeline can all see this tab. The end-to-end form is
        > scheduled for the next iteration.
        """
    )

    active = state.current_countries()
    st.subheader("Planned workflow")
    st.markdown(
        f"""
        1. **Company profile.** Name, sector, founding year, current TRL,
           team headcount split by Layer 3 / 4 / 5 / 6, AI substitution
           potential of Layer 4.
        2. **Jurisdictional arms.** For each active bloc
           ({" · ".join(state.country_labels(active)) or "no blocs selected"}),
           the engineer / specialist / regulatory headcount and the loaded
           local cost per role.
        3. **Cash flow projection.** Year-by-year free cash flow, NOPAT,
           and invested capital for the projection horizon.
        4. **Run the framework.** The framework computes:
           - Classical Damodaran enterprise value
           - Layered DCF (TRL-modulated rate + per-layer risk premium)
           - Two-phase DCF (post-AI double-valley reformulation, Appendix B)
           - Damodaran inverted discount (Section 6.4)
           - Substitution NPV per active jurisdiction
           - Fragility-index classification (resilient / borderline / fragile)
        5. **Compare across blocs.** With the multi-select in the sidebar,
           every figure regenerates restricted to the chosen blocs, so the
           user can see how the same company is valued differently in
           Brazil vs France vs the United States — exactly the question
           Section 7.3 raises.
        """
    )

    st.subheader("In the meantime")
    st.markdown(
        """
        - Use **🔬 Research Levers** to set the parameter overlay that will
          drive the valuation when this tab is wired up.
        - Use **💾 Scenario YAML** in the sidebar to save the calibration
          you build, so it survives the next session.
        - Use **📄 Export PDF** to capture the calibration alongside every
          paper figure, as a reproducibility document.
        """
    )
