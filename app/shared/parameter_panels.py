"""Global sidebar with parameters shared across tabs."""
import streamlit as st


def global_sidebar() -> dict:
    """Render the global parameter sidebar and return current values."""
    st.sidebar.header("Global Parameters")
    st.sidebar.caption(
        "These parameters are shared across all tabs. Adjust here once; "
        "all tabs respect the same values."
    )

    st.sidebar.subheader("Cross-Border Knowledge Regime")
    K7 = st.sidebar.slider(
        "K₇ — knowledge integration coefficient",
        min_value=0.0, max_value=1.0, value=0.7, step=0.05,
        help="0.0 = fully fragmented; 1.0 = fully integrated. "
             "K₇=1.0: 2020 baseline; K₇=0.7: 2026 illustrative; "
             "K₇=0.4: 2030 fragmented counterfactual. Collapse threshold ≈ 0.45."
    )

    ai_substitution_potential = st.sidebar.slider(
        "AI substitution potential",
        min_value=0.0, max_value=1.0, value=0.6, step=0.05,
        help="Probability that a Layer-4 task can be performed by frontier-model "
             "services in the near term."
    )

    st.sidebar.subheader("Reference Firm")
    firm_choice = st.sidebar.radio(
        "Select firm profile",
        ["NeuroCertify (deep-tech, HIT)", "DataFlow Pro (commoditizing, S&A)", "Custom"],
        index=0,
    )

    if firm_choice.startswith("NeuroCertify"):
        layer4_share = 0.20
        layer5_share = 0.20
        layer6_share = 0.40
    elif firm_choice.startswith("DataFlow"):
        layer4_share = 0.55
        layer5_share = 0.10
        layer6_share = 0.10
    else:
        st.sidebar.subheader("Custom Layer Exposure")
        layer4_share = st.sidebar.slider(
            "Layer 4 share (codified)", 0.0, 0.8, 0.30, 0.05,
            help="Fraction of effort at Layer 4 (codified, AI-substitutable)."
        )
        layer5_share = st.sidebar.slider(
            "Layer 5 share (judgment)", 0.0, 0.6, 0.20, 0.05,
            help="Fraction of effort at Layer 5 (judgment-laden)."
        )
        layer6_share = st.sidebar.slider(
            "Layer 6 share (institutional)", 0.0, 0.6, 0.20, 0.05,
            help="Fraction of effort at Layer 6 (institutional/regulatory embedding)."
        )

    return {
        "K7": K7,
        "ai_substitution_potential": ai_substitution_potential,
        "firm_choice": firm_choice,
        "layer4_share": layer4_share,
        "layer5_share": layer5_share,
        "layer6_share": layer6_share,
    }
