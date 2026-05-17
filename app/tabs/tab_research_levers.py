"""Tab — Research levers: the curated set of parameters that matter.

Renders the manifest defined in app/shared/research_levers.py. Each
group becomes a collapsible expander; each parameter becomes a slider
or number_input wired to the override engine in app/shared/state.py.

This tab is meant for working researchers and PhD students: every input
has a short description that names the paper section / equation /
figure it affects. The full ~500-parameter dump is still available in
the legacy "⚙️ Configuration" tab for power users.
"""

from __future__ import annotations

import streamlit as st

from app.shared import research_levers, state
from src import config


def _coerce(value, *, format: str):
    """Coerce ``value`` to the type required by Streamlit for the given format."""
    return int(value) if format == "%d" else float(value)


def _render_slider(param):
    fmt = param["format"]
    mn = _coerce(param["min"], format=fmt)
    mx = _coerce(param["max"], format=fmt)
    step = _coerce(param["step"], format=fmt)
    default = _coerce(config.get(param["dot_path"], mn), format=fmt)
    current = _coerce(state.get_override(param["dot_path"], default), format=fmt)
    val = st.slider(
        param["label"],
        min_value=mn, max_value=mx, value=current, step=step,
        format=fmt, help=param["description"],
        key=f"lvr_{param['dot_path']}",
    )
    return val, default


def _render_number(param):
    fmt = param["format"]
    mn = _coerce(param["min"], format=fmt)
    mx = _coerce(param["max"], format=fmt)
    step = _coerce(param["step"], format=fmt)
    default = _coerce(config.get(param["dot_path"], mn), format=fmt)
    current = _coerce(state.get_override(param["dot_path"], default), format=fmt)
    val = st.number_input(
        param["label"],
        min_value=mn, max_value=mx, value=current, step=step,
        format=fmt, help=param["description"],
        key=f"lvr_{param['dot_path']}",
    )
    return val, default


def _record_change(dot_path: str, value, default, *, format: str) -> None:
    tol = 0 if format == "%d" else 1e-9
    if abs(value - default) > tol:
        state.set_override(dot_path, value)
    elif dot_path in st.session_state.get("overrides", {}):
        del st.session_state["overrides"][dot_path]


def render():
    state.init_session_state()

    st.header("🔬 Research Levers")
    st.markdown(
        """
        Every parameter on this page is one a working researcher or PhD
        student would plausibly want to manipulate to test a hypothesis
        under *The Cost Gradient of the Build*.

        Internal mechanics — random seeds, Monte-Carlo run counts, grid
        resolutions, UI display constants — are deliberately *not* here.
        They live in the full **⚙️ Configuration** tab if you need them.

        Edits made here are saved as overrides on top of `parameters.yaml`,
        propagate live to every other tab, and are recorded in the
        scenario YAML you can download from the sidebar.

        > 💵 All monetary values in USD.
        """
    )

    n_over = len(st.session_state.get("overrides", {}))
    if n_over > 0:
        st.info(
            f"📝 **{n_over} override(s) active.** Use **🗑️ Clear** in the "
            f"sidebar to reset, or **📥 Download** to save this scenario.")

    for group in research_levers.LEVER_GROUPS:
        with st.expander(group["label"], expanded=(group["id"] == "headline")):
            st.caption(group["intro"])
            cols = st.columns(2)
            for i, param in enumerate(group["params"]):
                with cols[i % 2]:
                    if param["kind"] == "slider":
                        val, default = _render_slider(param)
                    else:
                        val, default = _render_number(param)
                    _record_change(param["dot_path"], val, default,
                                    format=param["format"])
