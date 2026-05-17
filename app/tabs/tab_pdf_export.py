"""Tab — PDF report export. Implemented in Phase 5."""

import streamlit as st


def render():
    st.header("📄 Export PDF Report")
    st.markdown(
        """
        ### 🚧 Coming in Phase 5

        A single button to generate a comprehensive PDF report containing:

        - **Cover page** with timestamp, country selection, and active overrides
        - **Complete parameter table** — every variable used, with unit (USD)
          and 1-line explanation
        - **All generated figures** (41 PNGs) with interpretation captions
        - **Executive summary** — enterprise value, inversion premium,
          jurisdictional ordering, fragility classification
        - **Scenario YAML** appended as an annex for reproducibility

        Built with `reportlab` for a paper-grade ~30-50 page A4 document.

        > Use this tab once Phase 5 is delivered to capture your study as
        > a citable, archive-ready PDF.
        """
    )
    st.info(
        "💡 **Workaround until Phase 5 ships**: use the **💾 Scenario YAML** "
        "buttons in the sidebar to save your overrides, then run the "
        "scripts (or `python main.py 2`) to regenerate every figure under "
        "your scenario. The PNGs live in `outputs/figures/`."
    )
