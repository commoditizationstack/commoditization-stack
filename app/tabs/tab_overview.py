"""Overview tab — explains the framework and the simulator."""
import streamlit as st


def render():
    st.header("Welcome")
    st.markdown(
        """
        This simulator materializes the framework developed in
        **de Miranda Neto (2026), *The Cost Gradient of the Build***,
        an open-source companion that allows researchers, practitioners,
        founders, and educators to interactively explore the four
        contributions of the paper:

        1. **Inverted Damodaran key-person discount under jurisdictional structure**
           — the central proposition of the paper, demonstrated as a
           counterintuitive ordering across Brazil, France, and the United States.
        2. **Seven-layer framework** of the knowledge-production stack,
           with explicit modulation by the cross-border knowledge regime
           (the K₇ coefficient).
        3. **Minimum Viable Hypothesis** as a positive substitute for the
           Minimum Viable Product (Section 5 of the paper).
        4. **Layered theory of post-AI defensibility**, showing the migration
           of strategic value from Layer 4 (commoditizing) to Layers 5 and 6
           (anti-commoditizing).

        ### How to use this simulator

        - **Sidebar (left)** — global parameters that all tabs respect:
          K₇, AI substitution potential, layer exposure of the reference firm.
        - **Tabs above** — each tab focuses on one component of the framework
          or one of the appendices of the paper:
          - **Seven Layers** — visualization of K₇ effect on Layers 4 and 5
          - **Appendix A** — layered DCF for two case companies
          - **Appendix B** — phase-conditional CAPM/WACC with eleven equations

        All defaults are calibrated to publicly cited evidence; all parameters
        are editable. The simulator is deliberately illustrative rather than
        predictive; it allows you to construct your own scenarios and explore
        the consequences of your own assumptions.
        """
    )

    st.markdown("---")

    st.subheader("Status of the framework")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Layers operationalized", "7 of 7")
    with col2:
        st.metric("Reference firms", "2 (NeuroCertify, DataFlow)")
    with col3:
        st.metric("Reference jurisdictions", "3 (BR, FR, US)")

    st.markdown(
        """
        ### Honest disclaimers
        - The simulator is **illustrative**, not predictive. Calibrations are
          grounded in publicly cited evidence (Damodaran, Carta, Dell'Acqua,
          Felin-Holweg, Equidam-Hectelion) but the specific magnitudes used
          should be read as plausibility-anchored rather than estimated.
        - **K₇ is a descriptive indicator of the cross-border knowledge regime,
          not a policy lever.** The simulator shows conditional consequences
          of varying K₇, not predictions of the actual K₇ trajectory.
        - **The inversion of Damodaran's key-person discount** (the paper's
          central contribution) is presented as a falsifiable proposition,
          not as an empirically validated finding. Validation against
          firm-level transaction data is the natural next step.
        """
    )
