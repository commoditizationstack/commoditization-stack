"""Tab — Appendix D: Streaming case + cross-bloc fiscal flows."""

from pathlib import Path

import streamlit as st

from app.shared import state
from src.streaming_case import run_three_scenarios, cross_jurisdictional_price
from src.fiscal_blocs import project_all_blocs

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()
    country = state.current_country()

    st.header("🎬 Appendix D — Streaming Case + Cross-Bloc Fiscal Flows")
    st.markdown(
        f"""
        Appendix D translates the inversion-premium arithmetic of Section 7
        into **consumer prices** for a competitive entry into the global
        streaming market, and extends to **5-year fiscal projections** for
        three jurisdictional blocs.

        Currently selected target jurisdiction: **{state.country_label()}**

        > 💵 All monetary values in USD.
        """
    )

    # Live computation
    st.subheader("Live computation: entrant price under your current parameters")
    results = run_three_scenarios()
    cols = st.columns(3)
    for col, r in zip(cols, results):
        with col:
            reduction = r.price_reduction_pct * 100
            st.metric(
                f"Entrant — {r.scenario_label.title()} ({int(r.substitution_pct*100)}%)",
                f"${r.entrant.total:.2f}/mo",
                delta=f"−{reduction:.1f}%",
            )

    # Cross-jurisdictional comparison for the selected country
    st.subheader(f"Cross-jurisdictional attack — selected target: {state.country_label()}")
    sub = float(state.effective_parameters()["streaming_case"][
        "substitution_scenarios"]["moderate_pct"])
    cols = st.columns(3)
    for col, acquirer in zip(cols, ["brazil", "france", "united_states"]):
        with col:
            price = cross_jurisdictional_price(country, acquirer, sub)
            inc = results[0].incumbent.total
            reduction = (inc - price) / inc * 100
            st.metric(f"Entrant from {state.COUNTRY_LABELS[acquirer]}",
                       f"${price:.2f}/mo",
                       delta=f"−{reduction:.1f}%")

    # Fiscal blocs
    st.subheader("5-year fiscal impact by bloc")
    blocs = project_all_blocs()
    cols = st.columns(3)
    for col, b in zip(cols, ["brazil", "france", "united_states"]):
        with col:
            net = blocs[b].net_impact_usd_millions
            sign = "loss" if net > 0 else "gain"
            color = "off" if net > 0 else "normal"
            st.metric(
                f"{state.COUNTRY_LABELS[b]}",
                f"${abs(net):.0f}M {sign}",
                delta=f"{'+' if net > 0 else '-'}{abs(net):.0f}",
                delta_color="inverse" if net > 0 else "normal",
            )

    # ===== Live figures =====
    from app.shared import live_figures

    st.markdown("---")
    st.subheader("📊 Streaming price decomposition (live)")
    st.caption("Adjust the substitution percentages in ⚙️ Configuration → "
                "Streaming case, and the stacked bars below refresh instantly.")
    fig_price = live_figures.streaming_price_decomposition(results=results)
    st.pyplot(fig_price, use_container_width=True)

    st.subheader("🏛 Fiscal impact across 3 blocs (live)")
    st.caption("Edit corporate tax rates, employer charges, or transfer-pricing "
                "shares in ⚙️ Configuration → Fiscal blocs to reshape.")
    fig_fiscal = live_figures.fiscal_blocs_decomposition(blocs)
    st.pyplot(fig_fiscal, use_container_width=True)

    # ===== Paper PNGs collapsed =====
    with st.expander("📷 Original paper figures (Fig D.2–D.8 PNGs)", expanded=False):
        for fname, title in [
            ("fig24_streaming_price_decomp.png", "D.2 — Price decomposition"),
            ("fig25_streaming_cross_jurisdictional.png", "D.3 — Cross-jurisdictional"),
            ("fig26_streaming_capital_trajectory.png", "D.4 — Capital trajectory"),
            ("fig27_streaming_phase_risk.png", "D.5 — Phase-conditional risk"),
            ("fig28_streaming_dilution_multiple.png", "D.6 — Dilution + multiple"),
            ("fig29_streaming_payoff_matrix.png", "D.7 — Payoff matrix"),
            ("fig30_fiscal_blocs.png", "D.8 — Fiscal blocs"),
        ]:
            st.markdown(f"**{title}**")
            fp = FIG_DIR / fname
            if fp.exists():
                st.image(str(fp), use_container_width=True)
            else:
                st.warning(f"Figure `{fname}` not yet generated.")
