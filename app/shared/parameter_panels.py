"""Global sidebar — fast-iteration controls + country selector + YAML round-trip.

Three behavior tiers:
  · Fast sliders (K7, AI substitution, layer exposure) recompute downstream
    visualisations live on each interaction.
  · Country selector — synchronously rebinds every jurisdiction-dependent
    figure across all tabs.
  · "Recompute All" — bumps the recompute counter so cached heavy
    simulations (Monte Carlo, full migration scan, 5-year fiscal projection)
    refresh on the next render.

YAML download/upload preserves the current overrides as a portable scenario
file for archival, version control, or peer review.

Currency note: every dollar figure in the app is in USD.
"""

from __future__ import annotations

import streamlit as st

from app.shared import state
from src import config


def global_sidebar() -> dict:
    """Render the global sidebar and return the resolved parameter values.

    The returned dict is a convenience handle for tabs that want the
    quick parameters (K7, AI sub, layer exposure) without going through
    the full `effective_parameters()` round-trip.
    """
    state.init_session_state()

    ui = config.streamlit_ui()
    sl = ui["sliders"]

    # -------- Header + currency badge ----------------------------------
    st.sidebar.markdown(
        "<div style='padding: 8px 12px; background: #1B3A57; color: white; "
        "border-radius: 6px; font-size: 0.95rem; font-weight: 600;'>"
        "💵 All monetary values in USD"
        "</div>",
        unsafe_allow_html=True,
    )

    # -------- Country selector (multi-bloc comparative scenario) ------
    st.sidebar.subheader("🌎 Jurisdictions in scope")
    country_keys = list(state.COUNTRY_LABELS.keys())
    country_label_to_key = {state.COUNTRY_LABELS[k]: k for k in country_keys}
    current_labels = [state.COUNTRY_LABELS[k]
                       for k in state.current_countries()]
    chosen_labels = st.sidebar.multiselect(
        "Active blocs (Section 7 + Appendix D + all comparative charts)",
        options=[state.COUNTRY_LABELS[k] for k in country_keys],
        default=current_labels,
        help="Select one or more jurisdictions. Every comparative chart "
             "(jurisdictional inversion, migration cash flow, fiscal blocs, "
             "cross-border M&A) iterates only over the selected blocs.",
    )
    chosen_slugs = [country_label_to_key[lbl] for lbl in chosen_labels]
    if not chosen_slugs:
        st.sidebar.warning("Pick at least one jurisdiction — falling back "
                            "to all three.")
        chosen_slugs = list(state.DEFAULT_COUNTRIES)
    st.session_state["countries"] = chosen_slugs
    # Keep the legacy single-country pointer aligned with the first selection.
    if st.session_state.get("country") not in chosen_slugs:
        st.session_state["country"] = chosen_slugs[0]

    # -------- Fast sliders --------------------------------------------
    st.sidebar.subheader("⚡ Quick parameters")
    st.sidebar.caption("Live updates. For paper parameters, use the "
                       "**⚙️ Configuration** tab.")

    K7 = st.sidebar.slider(
        "K₇ — knowledge integration coefficient",
        min_value=float(sl["k7_min"]),
        max_value=float(sl["k7_max"]),
        value=state.get_override("streamlit_ui.sliders.k7_default",
                                  float(sl["k7_default"])),
        step=float(sl["k7_step"]),
        help="0.0 = fully fragmented; 1.0 = fully integrated. "
             "Collapse threshold near K₇ = 0.45.",
        key="sidebar_k7",
    )

    ai_sub = st.sidebar.slider(
        "AI substitution potential (Layer 4)",
        min_value=float(sl["ai_substitution_min"]),
        max_value=float(sl["ai_substitution_max"]),
        value=state.get_override("streamlit_ui.sliders.ai_substitution_default",
                                  float(sl["ai_substitution_default"])),
        step=float(sl["ai_substitution_step"]),
        help="Probability that a Layer-4 task can be performed by frontier-model "
             "services in the near term.",
        key="sidebar_ai_sub",
    )

    # -------- Reference firm profile ----------------------------------
    st.sidebar.subheader("🏢 Reference firm")
    profiles = ui["firm_profiles"]
    profile_keys = list(profiles.keys())
    profile_labels = [profiles[k]["label"] for k in profile_keys] + ["Custom"]

    chosen_profile_label = st.sidebar.radio(
        "Firm profile (Layer 4/5/6 exposure)",
        options=profile_labels,
        index=0,
        key="sidebar_firm_profile",
    )

    layer4 = float(sl["layer4_exposure_default"])
    layer5 = float(sl["layer5_exposure_default"])
    layer6 = float(sl["layer6_exposure_default"])

    matched_profile = None
    for key, label in zip(profile_keys, profile_labels[:-1]):
        if chosen_profile_label == label:
            matched_profile = profiles[key]
            break

    if matched_profile is not None:
        layer4 = float(matched_profile["layer4_codified"])
        layer5 = float(matched_profile["layer5_judgment"])
        layer6 = float(matched_profile["layer6_institutional"])
    else:
        step = float(sl["layer_exposure_step"])
        layer4 = st.sidebar.slider("Layer 4 share (codified)",
                                   0.0, 0.8, layer4, step,
                                   key="sidebar_l4")
        layer5 = st.sidebar.slider("Layer 5 share (judgment)",
                                   0.0, 0.6, layer5, step,
                                   key="sidebar_l5")
        layer6 = st.sidebar.slider("Layer 6 share (institutional)",
                                   0.0, 0.6, layer6, step,
                                   key="sidebar_l6")

    # -------- Recompute -----------------------------------------------
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Recompute All", use_container_width=True,
                          help="Force re-execution of heavy simulations "
                               "(Monte Carlo, full migration scan, fiscal projection)."):
        state.request_recompute()
        st.rerun()

    # -------- Scenario YAML round-trip --------------------------------
    st.sidebar.markdown("---")
    st.sidebar.subheader("💾 Scenario YAML")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.download_button(
            "📥 Download",
            data=state.overrides_as_yaml_bytes(),
            file_name="scenario_overrides.yaml",
            mime="application/x-yaml",
            use_container_width=True,
            help="Save current parameter overrides as a YAML file.",
        )
    with col2:
        if st.button("🗑️ Clear", use_container_width=True,
                      help="Reset all overrides to YAML defaults."):
            state.clear_overrides()
            st.rerun()

    uploaded = st.sidebar.file_uploader(
        "📤 Upload scenario YAML",
        type=["yaml", "yml"],
        help="Load a previously-saved scenario file. Replaces current overrides.",
    )
    if uploaded is not None:
        try:
            n_loaded = state.load_overrides_from_yaml_bytes(uploaded.read())
            st.sidebar.success(f"Loaded {n_loaded} override(s).")
        except Exception as e:
            st.sidebar.error(f"Failed to load: {e}")

    # Override count badge
    n_overrides = len(st.session_state.get("overrides", {}))
    if n_overrides > 0:
        st.sidebar.caption(f"📝 {n_overrides} override(s) active.")
    else:
        st.sidebar.caption("Using YAML defaults (no overrides).")

    return {
        "K7": K7,
        "ai_substitution_potential": ai_sub,
        "firm_choice": chosen_profile_label,
        "layer4_share": layer4,
        "layer5_share": layer5,
        "layer6_share": layer6,
        "country": state.current_country(),
        "countries": state.current_countries(),
    }
