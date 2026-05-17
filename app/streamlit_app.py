"""Streamlit entry point for the framework simulator.

Run with:
    cd commoditization-stack-simulation
    streamlit run app/streamlit_app.py

Or via the launcher:
    python main.py 1

Navigation
----------
The sidebar groups the 17 pages of the simulator into five sections:

    🧭 Orient        — Overview, About
    🎛 Configure     — Research Levers, Company Valuation, Configuration
    🔍 Explore       — Seven Layers, Inverted Discount, Jurisdictional,
                       Migration, Hype Cycle
    📚 Appendices    — A, B, D, E, F, G
    📄 Report        — Export PDF

The user picks a section, then a page within the section. The list of
pages is identical to the legacy horizontal tab strip: nothing has been
removed; only the organisation has improved.
"""
import sys
from pathlib import Path

# Add repo root to path so we can import src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.shared import components, parameter_panels, state
from app.tabs import (
    tab_overview,
    tab_research_levers,
    tab_company_valuation,
    tab_configuration,
    tab_layers,
    tab_inverted_discount,
    tab_jurisdictional,
    tab_migration,
    tab_hype_cycle,
    tab_appendix_a,
    tab_appendix_b,
    tab_appendix_d,
    tab_appendix_e,
    tab_appendix_f,
    tab_appendix_g,
    tab_pdf_export,
    tab_about,
)


# ---------------------------------------------------------------------------
# Navigation manifest — single source of truth for the sidebar nav tree.
# Tabs are exactly the same modules as before; only the grouping is new.
# ---------------------------------------------------------------------------

NAV_GROUPS = [
    ("🧭 Orient", [
        ("Overview",            "tab_overview",         False),
        ("About",               "tab_about",            False),
    ]),
    ("🎛 Configure", [
        ("🔬 Research Levers",  "tab_research_levers",  False),
        ("🏢 Company Valuation", "tab_company_valuation", False),
        ("⚙️ Configuration",     "tab_configuration",    False),
    ]),
    ("🔍 Explore", [
        ("🧬 Seven Layers",      "tab_layers",            True),
        ("💰 Inverted Discount", "tab_inverted_discount", True),
        ("🌎 Jurisdictional",    "tab_jurisdictional",    True),
        ("⏱ Migration",          "tab_migration",         True),
        ("📈 Hype Cycle",        "tab_hype_cycle",        True),
    ]),
    ("📚 Appendices", [
        ("📐 A — Layered DCF",        "tab_appendix_a", True),
        ("🔄 B — Two-phase WACC",     "tab_appendix_b", True),
        ("🎬 D — Streaming + Fiscal", "tab_appendix_d", True),
        ("🏢 E — Case Companies",     "tab_appendix_e", True),
        ("🔗 F — Upstream Chain",     "tab_appendix_f", True),
        ("⚖️ G — Distributional",      "tab_appendix_g", True),
    ]),
    ("📄 Report", [
        ("📄 Export PDF",       "tab_pdf_export",       False),
    ]),
]


def _module(name: str):
    """Module lookup so the nav manifest stays purely declarative."""
    return globals()[name]


def main():
    state.init_session_state()

    st.set_page_config(
        page_title="The Cost Gradient of the Build — Simulator",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
            .main > div { padding-top: 1rem; }
            h1 { font-size: 1.75rem !important; color: #1B3A57; }
            h2 { font-size: 1.30rem !important; color: #2C5282; margin-top: 1.4rem !important; }
            h3 { font-size: 1.08rem !important; color: #3C6E91; }
            /* Sidebar radio prettier */
            section[data-testid="stSidebar"] .stRadio > label > div {
                font-size: 0.92rem;
            }
            /* Tighten the section selector */
            section[data-testid="stSidebar"] [data-testid="stSelectbox"] label {
                font-weight: 600;
                color: #1B3A57;
                font-size: 0.95rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("The Cost Gradient of the Build — Interactive Simulator")
    active = " · ".join(state.country_labels())
    st.markdown(
        "*Companion to de Miranda Neto (2026), "
        "*The Cost Gradient of the Build*. "
        f"Active jurisdictions: **{active}**. 💵 USD throughout.*"
    )

    # Global sidebar (country selector + quick parameters + scenario YAML).
    global_params = parameter_panels.global_sidebar()

    # ---------------------------------------------------------------------
    # Navigation — two-level tree in the sidebar.
    # ---------------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.subheader("🗂 Navigation")

    section_labels = [g[0] for g in NAV_GROUPS]
    chosen_section = st.sidebar.selectbox(
        "Section",
        options=section_labels,
        index=section_labels.index(
            st.session_state.get("nav_section", section_labels[0])),
        key="nav_section_select",
    )
    st.session_state["nav_section"] = chosen_section

    pages = next(g[1] for g in NAV_GROUPS if g[0] == chosen_section)
    page_labels = [p[0] for p in pages]
    nav_page_key = f"nav_page_in_{chosen_section}"
    chosen_page = st.sidebar.radio(
        "Page",
        options=page_labels,
        index=page_labels.index(
            st.session_state.get(nav_page_key, page_labels[0])
            if st.session_state.get(nav_page_key) in page_labels
            else page_labels[0]),
        key=f"nav_page_radio_{chosen_section}",
    )
    st.session_state[nav_page_key] = chosen_page

    # Lookup the module + render.
    page_label, module_name, takes_global = next(
        p for p in pages if p[0] == chosen_page)

    # Persistent status bar at the top of every page.
    components.status_bar()

    module = _module(module_name)
    if takes_global:
        module.render(global_params)
    else:
        module.render()


if __name__ == "__main__":
    main()
