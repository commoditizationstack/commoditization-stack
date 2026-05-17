"""Streamlit entry point for the framework simulator.

Run with:
    cd commoditization-stack-simulation
    streamlit run app/streamlit_app.py

Or via the launcher:
    python main.py 1

The 17 horizontal tabs at the top of the page expose every section of
the paper. The sidebar holds the multi-country selector, the headline
sliders, the named-scenario store, and the YAML scenario round-trip.
A persistent status bar above the tabs shows the active blocs, the
headline lever values, and the override count.
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
            .stTabs [data-baseweb="tab-list"] { gap: 2px; flex-wrap: wrap; }
            .stTabs [data-baseweb="tab"] {
                padding: 6px 12px;
                background: #EEF2F5;
                border-radius: 6px 6px 0 0;
                font-size: 0.88rem;
            }
            .stTabs [aria-selected="true"] {
                background: #1B3A57 !important;
                color: white !important;
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

    # Global sidebar (country selector + quick parameters + scenario YAML
    # + named scenarios).
    global_params = parameter_panels.global_sidebar()

    # Persistent status bar above the tab strip — active blocs, K7,
    # AI substitutability of Layer 4, override count.
    components.status_bar()

    # 17 horizontal tabs mirroring the paper structure.
    tabs = st.tabs([
        "🏠 Overview",
        "🔬 Research Levers",
        "🏢 Company Valuation",
        "⚙️ Configuration",
        "🧬 Seven Layers",
        "💰 Inverted Discount",
        "🌎 Jurisdictional",
        "⏱ Migration",
        "📈 Hype Cycle",
        "📐 Appendix A",
        "🔄 Appendix B",
        "🎬 Appendix D",
        "🏢 Appendix E",
        "🔗 Appendix F",
        "⚖️ Appendix G",
        "📄 Export PDF",
        "ℹ️ About",
    ])

    with tabs[0]:
        tab_overview.render()
    with tabs[1]:
        tab_research_levers.render()
    with tabs[2]:
        tab_company_valuation.render()
    with tabs[3]:
        tab_configuration.render()
    with tabs[4]:
        tab_layers.render(global_params)
    with tabs[5]:
        tab_inverted_discount.render(global_params)
    with tabs[6]:
        tab_jurisdictional.render(global_params)
    with tabs[7]:
        tab_migration.render(global_params)
    with tabs[8]:
        tab_hype_cycle.render(global_params)
    with tabs[9]:
        tab_appendix_a.render(global_params)
    with tabs[10]:
        tab_appendix_b.render(global_params)
    with tabs[11]:
        tab_appendix_d.render(global_params)
    with tabs[12]:
        tab_appendix_e.render(global_params)
    with tabs[13]:
        tab_appendix_f.render(global_params)
    with tabs[14]:
        tab_appendix_g.render(global_params)
    with tabs[15]:
        tab_pdf_export.render()
    with tabs[16]:
        tab_about.render()


if __name__ == "__main__":
    main()
