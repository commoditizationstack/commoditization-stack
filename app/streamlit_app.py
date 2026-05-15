"""Streamlit entry point for the framework simulator.

Run with:
    cd commoditization-stack-simulation
    streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

# Add repo root to path so we can import src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.tabs import tab_overview, tab_layers, tab_appendix_a, tab_appendix_b, tab_about
from app.shared import parameter_panels


def main():
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
            h1 { font-size: 1.85rem !important; color: #1B3A57; }
            h2 { font-size: 1.35rem !important; color: #2C5282; margin-top: 1.5rem !important; }
            h3 { font-size: 1.10rem !important; color: #3C6E91; }
            .stTabs [data-baseweb="tab-list"] { gap: 4px; }
            .stTabs [data-baseweb="tab"] {
                padding: 8px 16px; background: #EEF2F5; border-radius: 6px 6px 0 0;
            }
            .stTabs [aria-selected="true"] { background: #1B3A57 !important; color: white !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("The Cost Gradient of the Build — Interactive Simulator")
    st.markdown(
        "*Companion to de Miranda Neto (2026), "
        "[The Cost Gradient of the Build](https://ssrn.com).*"
    )

    # Global parameter panel in sidebar
    global_params = parameter_panels.global_sidebar()

    # Tabs
    tabs = st.tabs([
        "📖 Overview",
        "🧬 Seven Layers",
        "📐 Appendix A: Layered DCF",
        "📈 Appendix B: Two-Phase DCF",
        "ℹ️ About",
    ])

    with tabs[0]:
        tab_overview.render()
    with tabs[1]:
        tab_layers.render(global_params)
    with tabs[2]:
        tab_appendix_a.render(global_params)
    with tabs[3]:
        tab_appendix_b.render(global_params)
    with tabs[4]:
        tab_about.render()


if __name__ == "__main__":
    main()
