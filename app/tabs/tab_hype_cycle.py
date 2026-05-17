"""Tab — Section 6.5: Hype Cycle & double-valley dynamic."""

from pathlib import Path

import streamlit as st

from app.shared import state

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()

    st.header("📈 Hype Cycle & Double-Valley Dynamic (Section 6.5)")
    st.markdown(
        """
        The classical Gartner Hype Cycle (Gartner, 1995) shows a single
        valley of disillusionment. Section 6.5 proposes a **double-valley**
        structure for the post-AI regime: a shallower classical valley
        followed by a second valley around month 24-36, when competitors
        close the technical gap through frontier-model substitution.

        This second valley has direct consequences for capital strategy
        (Appendix B reformulates CAPM/WACC/EVA/Gordon as phase-conditional).
        """
    )

    # ===== Live double-valley expectations curve =====
    from app.shared import live_figures
    from src.death_valley import (
        classical_cash_trajectory, post_genai_double_valley_cash_trajectory,
    )

    p = state.effective_parameters()
    st.subheader("📈 Hype Cycle: classical vs double-valley (live)")
    st.caption("Edit hype-cycle parameters in 🔬 Research Levers → "
                "Hype cycle to reshape the disillusionment trough and "
                "post-AI commoditization valley.")
    fig = live_figures.hype_cycle_double_valley(
        n_quarters=32,
        classical_params=p["hype_cycle"]["classical"],
        post_genai_params=p["hype_cycle"]["post_genai"],
        classical_rise_exp=float(p["structural"]["classical_hype_rise_exponent"]),
        post_rise_exp=float(p["structural"]["post_genai_hype_rise_exponent"]),
    )
    st.pyplot(fig, use_container_width=True)

    # ===== Live death-valley cash trajectory =====
    st.subheader("💀 Death-valley cash trajectory (live)")
    st.caption("Both curves consume the current parameter overlay. Edit "
                "**🔬 Research Levers → 💀 Death-valley dynamics** to "
                "rebalance burn, refinancing, peak revenue, or the "
                "commoditization-valley window — and watch how a Series A "
                "rescue still drops a firm into the second valley if its "
                "Layer-4 share is high and margin compression hits hard.")

    cls = p["death_valley"]["classical"]
    post = p["death_valley"]["post_genai"]
    classical_cash = classical_cash_trajectory(
        n_months=int(cls["n_months"]),
        initial_cash_usd=float(cls["initial_cash_usd"]),
        monthly_burn_usd=float(cls["monthly_burn_usd"]),
        valley_start_month=int(cls["valley_start_month"]),
        valley_end_month=int(cls["valley_end_month"]),
        revenue_ramp_start_month=int(cls["revenue_ramp_start_month"]),
        peak_revenue_usd_per_month=float(cls["peak_revenue_usd_per_month"]),
        revenue_growth=float(cls["revenue_growth"]),
    )
    post_cash = post_genai_double_valley_cash_trajectory(
        n_months=int(post["n_months"]),
        initial_cash_usd=float(post["initial_cash_usd"]),
        monthly_burn_usd_initial=float(post["monthly_burn_usd_initial"]),
        classical_valley_start_month=int(post["classical_valley_start_month"]),
        classical_valley_end_month=int(post["classical_valley_end_month"]),
        commoditization_valley_start_month=int(post["commoditization_valley_start_month"]),
        commoditization_valley_end_month=int(post["commoditization_valley_end_month"]),
        revenue_ramp_start_month=int(post["revenue_ramp_start_month"]),
        peak_revenue_usd_per_month=float(post["peak_revenue_usd_per_month"]),
        revenue_growth=float(post["revenue_growth"]),
        margin_compression_factor=float(post["margin_compression_factor"]),
        refinancing_event_month=int(post["refinancing_event_month"]),
        refinancing_amount_usd=float(post["refinancing_amount_usd"]),
        burn_growth_after_funding=float(post["burn_growth_after_funding"]),
    )
    fig_dv = live_figures.death_valley_cash_trajectories(
        classical_cash=classical_cash,
        post_genai_cash=post_cash,
        post_genai_params=post,
    )
    st.pyplot(fig_dv, use_container_width=True)

    # ===== Paper PNGs collapsed =====
    with st.expander("📷 Original paper figures (PNG snapshots)",
                       expanded=False):
        for fname, title, caption in [
            ("fig4_hype_cycle.png",
             "Figure 6 — Hype Cycle classical vs post-AI",
             "Reference paper figure."),
            ("fig5_death_valley.png",
             "Figure 7 — Cash trajectory classical vs post-AI",
             "Classical regime shows a single deep valley resolved by Series A "
             "funding. The post-AI regime shows a shallower first valley followed "
             "by a new second valley around month 24-36."),
        ]:
            st.markdown(f"**{title}**")
            fp = FIG_DIR / fname
            if fp.exists():
                st.image(str(fp), caption=caption, use_container_width=True)
            else:
                st.warning(f"Figure {fname} not found.")
