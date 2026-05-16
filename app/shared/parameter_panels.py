"""Global sidebar with parameters shared across tabs.

Slider defaults, ranges, steps, and firm profiles all come from
config/parameters.yaml (sections streamlit_ui and firms_appendix_b).
"""
import streamlit as st

from src import config


def global_sidebar() -> dict:
    """Render the global parameter sidebar and return current values."""
    ui = config.streamlit_ui()
    sl = ui["sliders"]
    profiles = ui["firm_profiles"]

    st.sidebar.header("Global Parameters")
    st.sidebar.caption(
        "Interactive controls below. Paper-defined parameters (TRL premium "
        "schedule, layer risk coefficients, US funding-stage benchmarks, "
        "jurisdictional fiscal data) are read-only and displayed inside "
        "each tab. Edit `config/parameters.yaml` to change those."
    )

    st.sidebar.subheader("Cross-Border Knowledge Regime")
    K7 = st.sidebar.slider(
        "K₇ — knowledge integration coefficient",
        min_value=float(sl["k7_min"]),
        max_value=float(sl["k7_max"]),
        value=float(sl["k7_default"]),
        step=float(sl["k7_step"]),
        help="0.0 = fully fragmented; 1.0 = fully integrated. "
             "K₇=1.0: 2020 baseline; K₇=0.7: 2026 illustrative; "
             "K₇=0.4: 2030 fragmented counterfactual.",
    )

    ai_substitution_potential = st.sidebar.slider(
        "AI substitution potential",
        min_value=float(sl["ai_substitution_min"]),
        max_value=float(sl["ai_substitution_max"]),
        value=float(sl["ai_substitution_default"]),
        step=float(sl["ai_substitution_step"]),
        help="Probability that a Layer-4 task can be performed by frontier-model "
             "services in the near term.",
    )

    st.sidebar.subheader("Reference Firm")
    profile_keys = list(profiles.keys())
    profile_labels = [profiles[k]["label"] for k in profile_keys] + ["Custom"]
    firm_choice = st.sidebar.radio("Select firm profile", profile_labels, index=0)

    layer4_share = float(sl["layer4_exposure_default"])
    layer5_share = float(sl["layer5_exposure_default"])
    layer6_share = float(sl["layer6_exposure_default"])

    matched_profile = None
    for key, label in zip(profile_keys, profile_labels[:-1]):
        if firm_choice == label:
            matched_profile = profiles[key]
            break

    if matched_profile is not None:
        layer4_share = float(matched_profile["layer4_codified"])
        layer5_share = float(matched_profile["layer5_judgment"])
        layer6_share = float(matched_profile["layer6_institutional"])
    else:
        step = float(sl["layer_exposure_step"])
        st.sidebar.subheader("Custom Layer Exposure")
        layer4_share = st.sidebar.slider(
            "Layer 4 share (codified)", 0.0, 0.8, layer4_share, step,
            help="Fraction of effort at Layer 4 (codified, AI-substitutable).",
        )
        layer5_share = st.sidebar.slider(
            "Layer 5 share (judgment)", 0.0, 0.6, layer5_share, step,
            help="Fraction of effort at Layer 5 (judgment-laden).",
        )
        layer6_share = st.sidebar.slider(
            "Layer 6 share (institutional)", 0.0, 0.6, layer6_share, step,
            help="Fraction of effort at Layer 6 (institutional/regulatory embedding).",
        )

    return {
        "K7": K7,
        "ai_substitution_potential": ai_substitution_potential,
        "firm_choice": firm_choice,
        "layer4_share": layer4_share,
        "layer5_share": layer5_share,
        "layer6_share": layer6_share,
    }
