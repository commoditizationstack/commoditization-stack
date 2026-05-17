"""Overview tab — landing page with reader's guide."""

import streamlit as st

from app.shared import state


def render():
    state.init_session_state()

    st.header("Welcome")
    st.markdown(
        f"""
        This is the interactive simulator for the framework developed in
        **de Miranda Neto (2026), *The Cost Gradient of the Build***.

        > Currently selected jurisdiction: **{state.country_label()}** ·
        > Active overrides: **{len(st.session_state.get('overrides', {}))}**

        > 💵 All monetary values in this simulator are in **USD**.
        """
    )

    st.markdown("### How to use")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            **In the sidebar (left):**
            - 🌎 **Jurisdiction** — sync country across all tabs
            - ⚡ **Quick parameters** — K₇, AI substitution, layer exposure
              (live updates downstream)
            - 🔄 **Recalcular Tudo** — force re-execution of heavy simulations
            - 💾 **Scenario YAML** — download / upload your overrides
            """
        )
    with col2:
        st.markdown(
            """
            **In the tabs above (mirroring the paper):**
            - **⚙️ Configuration** — edit every variable
            - **🧬 Seven Layers** through **⚖️ Appendix G** —
              each topic from the paper
            - **📄 Export PDF** — single-button report (Phase 5)
            """
        )

    st.markdown("---")

    st.subheader("Reader's routes (from the paper's Section 1.1)")

    routes = [
        ("👨‍💼 Investor / acquirer", "Inverted Discount → Jurisdictional → Migration → Appendix D"),
        ("🚀 Founder / operator", "Seven Layers → Inverted Discount → Migration → Appendix E"),
        ("⚖️ Regulator / accreditation", "Seven Layers → Appendix F → Appendix G"),
        ("📚 Researcher / student", "Seven Layers → Inverted Discount → Hype Cycle → All appendices"),
        ("🔬 Research-funding evaluator", "Seven Layers → Appendix F → Appendix G"),
        ("💼 Strategy / M&A advisor", "Inverted Discount → Jurisdictional → Appendix A → Appendix D"),
    ]
    for audience, route in routes:
        st.markdown(f"- **{audience}** — {route}")

    st.markdown("---")

    st.subheader("Status of the framework")
    cols = st.columns(4)
    with cols[0]:
        st.metric("Layers operationalized", "7 of 7")
    with cols[1]:
        st.metric("Reference firms", "2 (NC, DF)")
    with cols[2]:
        st.metric("Reference jurisdictions", "3 (BR, FR, US)")
    with cols[3]:
        st.metric("Figures generated", "41")

    st.markdown(
        """
        ### Honest disclaimers
        - **Illustrative, not predictive.** All calibrations are grounded in
          publicly cited evidence (Damodaran, Carta, Equidam-Hectelion,
          Brynjolfsson, Dell'Acqua, etc.) but the specific magnitudes are
          plausibility-anchored rather than estimated.
        - **K₇ is a descriptive indicator**, not a policy lever. The simulator
          shows *conditional* consequences of varying K₇, not predictions of
          the actual K₇ trajectory.
        - **The inversion of Damodaran's key-person discount** is presented
          as a falsifiable proposition. Validation against firm-level
          transaction data is the natural next step.
        - **Appendix C (eight-step operational manual)** is reserved for a
          future iteration of the simulator.
        """
    )
