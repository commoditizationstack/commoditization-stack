"""Tab — Section 7.1-7.4: Jurisdictional substitution & cross-border M&A.

Shows fig11 (jurisdictional inversion), fig12 (NPV decomposition), and
fig13 (cross-border M&A) regenerated under the user's current country
selection and parameter overrides.
"""

from pathlib import Path

import streamlit as st

from app.shared import state

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()

    st.header("🌎 Jurisdictional substitution (Section 7)")
    st.markdown(
        f"""
        Currently selected jurisdiction: **{state.country_label()}**

        Section 7 demonstrates the counterintuitive jurisdictional ordering
        of the inverted Damodaran key-person discount: high-wage jurisdictions
        produce the largest absolute inversion premium, despite lower statutory
        labor-cost multipliers, because the absolute base salary dominates the
        dollar value of the substitution.

        > 💵 All monetary values in USD.
        """
    )

    fig_titles = [
        ("fig11_jurisdictional_inversion.png",
         "Figure 8 — Inversion premium across three jurisdictions",
         "Annual cost flow comparison (left) and inversion premium as % of "
         "$200M reference EV (right). United States produces approximately 3.9%, "
         "France 1.7%, Brazil 1.0% — under K7 = 1.0."),
        ("fig12_substitution_npv_decomposition.png",
         "Figure 9 — Substitution NPV decomposition by jurisdiction",
         "5-year recurring savings (blue) net of one-time termination cost "
         "(orange). France carries the heaviest termination penalty in absolute "
         "terms; the United States carries the smallest, reflecting at-will "
         "employment."),
        ("fig13_crossborder.png",
         "Figure 10 — Cross-border M&A operating-cost basis",
         "A US-domiciled acquirer of a Brazilian or French target, contemplating "
         "reproduction of the substituted function from US headquarters rather "
         "than under the local cost basis, captures a substantially larger "
         "inversion premium than a domestic acquirer holding the team in place."),
    ]

    for fname, title, caption in fig_titles:
        st.subheader(title)
        fp = FIG_DIR / fname
        if fp.exists():
            st.image(str(fp), caption=caption, use_container_width=True)
        else:
            st.warning(f"Figure {fname} not found. "
                       f"Run `python scripts/run_jurisdictional.py` to generate.")

    st.markdown("---")
    st.subheader("📖 Paper parameters (read-only — edit in ⚙️ Configuration)")
    p = state.effective_parameters()
    country = state.current_country()
    j = p["jurisdictions"]["defaults"][country]
    st.markdown(f"**Currently active jurisdiction: {state.country_label()}**")
    cols = st.columns(3)
    with cols[0]:
        st.metric("Labor cost multiplier", f"{j['labor_cost_multiplier']:.2f}")
        st.metric("Termination cost fraction", f"{j['termination_cost_fraction']:.2f}")
    with cols[1]:
        st.metric("AI service overhead", f"{j['ai_service_overhead']:.2f}")
        st.metric("Notice period fraction", f"{j['notice_period_fraction']:.3f}")
    with cols[2]:
        st.metric("Vendor risk WACC premium", f"{j['vendor_risk_wacc_premium']:.3f}")
        st.caption(j.get("notes", ""))
