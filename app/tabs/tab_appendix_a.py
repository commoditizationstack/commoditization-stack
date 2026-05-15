"""Tab Appendix A — layered DCF for two case companies."""
import streamlit as st
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    st.header("Appendix A — Layered DCF for Two Case Companies")
    st.markdown(
        """
        Appendix A introduces a layered DCF that adds a TRL-modulated
        discount rate and a layer-decomposed firm-specific risk premium
        to Damodaran's narrative-and-numbers framework. Two contrasting
        case companies are demonstrated:
        - **NeuroCertify** (deep-tech, regulated, Layer-6-rich):
          Healthcare Information & Technology sector, industry beta 0.99
          (Damodaran, January 2026).
        - **DataFlow Pro** (commoditizing-tech, Layer-4-heavy):
          Software System & Application sector, industry beta 1.23.
        """
    )

    st.subheader("Reference figures")

    fig_titles = [
        ("fig16_trl_discount_trajectory.png",
         "TRL-modulated discount rate trajectory",
         "TRL premium trajectory for NeuroCertify and DataFlow Pro across "
         "their projection periods. NeuroCertify starts at TRL 4 with a +10pp "
         "premium and finishes at TRL 7 with +4pp; DataFlow Pro starts at TRL 8 "
         "with +2pp throughout."),
        ("fig17_layer_risk_decomposition.png",
         "Layer-decomposed firm-specific risk premium",
         "Contribution of each of the seven layers to the firm-specific risk "
         "premium. Positive contributions (commoditizing layers) and negative "
         "contributions (anti-commoditizing layers, primarily Layer 6) sum to "
         "yield the total layer-decomposed premium."),
        ("fig18_valuation_comparison.png",
         "Valuation comparison: classical Damodaran vs layered DCF",
         "Enterprise value comparison for both firms. Classical Damodaran (single "
         "rate, no TRL or layer adjustment) on the left; layered DCF (with TRL "
         "premium and layer-decomposed risk premium) on the right. The layered "
         "framework moves the two firms apart by a factor of approximately 2.5x, "
         "with diagnostic implications for funding-round placement."),
    ]

    for fname, title, caption in fig_titles:
        fp = FIG_DIR / fname
        st.markdown(f"#### {title}")
        if fp.exists():
            st.image(str(fp), caption=caption, use_container_width=True)
        else:
            st.warning(f"Figure {fname} not found. Run scripts/run_appendix_a.py to generate.")

    st.markdown("---")

    st.subheader("Run your own scenario")
    st.markdown(
        f"""
        The current global parameters from the sidebar (K₇ = {global_params['K7']:.2f},
        AI substitution potential = {global_params['ai_substitution_potential']:.2f},
        Layer-4 share = {global_params['layer4_share']:.2f}, Layer-6 share =
        {global_params['layer6_share']:.2f}) would produce results that
        the user can replicate by running:

        ```bash
        python scripts/run_appendix_a.py
        ```

        Editing `config/scenarios/neurocertify.yaml` or `config/scenarios/dataflow_pro.yaml`
        allows full re-calibration of any of the layered-DCF parameters.
        See `docs/EXTENDING.md` for the four levels of extension supported.
        """
    )
