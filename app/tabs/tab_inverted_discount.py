"""Tab — Section 6: Inverted Damodaran key-person discount."""

from pathlib import Path

import streamlit as st

from app.shared import state
from src.valuation import damodaran_classical_discount, damodaran_inverted_discount

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    state.init_session_state()

    st.header("💰 Inverted Key-Person Discount (Section 6)")
    st.markdown(
        """
        The classical Damodaran key-person discount assigns a positive
        reduction to firms whose value depends disproportionately on
        one individual. Section 6.4 shows that under post-AI conditions
        the discount can **flip in sign** when the technical labor
        surrounding the key person becomes substitutable by frontier-model
        services.

        > 💵 All monetary values in USD.
        """
    )

    p = state.effective_parameters()
    val = p["valuation"]

    # Live single-firm calculation
    st.subheader("Live single-firm calculation")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        ev = st.number_input("Enterprise value (USD millions)",
                              min_value=1.0, max_value=10000.0,
                              value=100.0, step=10.0,
                              key="inv_disc_ev")
    with col_b:
        l4_share = st.slider("Team Layer-4 share",
                              min_value=0.0, max_value=1.0,
                              value=global_params.get("layer4_share", 0.30),
                              step=0.05,
                              key="inv_disc_l4")
    with col_c:
        ai_sub = st.slider("AI substitution potential (L4)",
                            min_value=0.0, max_value=1.0,
                            value=global_params.get("ai_substitution_potential", 0.60),
                            step=0.05,
                            key="inv_disc_ai")

    ev_usd = ev * 1e6
    cls_adj, cls_comp = damodaran_classical_discount(
        ev_usd, key_person_discount_rate=float(
            val["damodaran_key_person_discount_classical"]))
    inv_adj, inv_comp = damodaran_inverted_discount(
        ev_usd, team_layer4_share=l4_share, ai_substitution_potential_layer4=ai_sub,
        threshold_layer4_share=float(val["damodaran_inverted_threshold_layer4_share"]),
        classical_discount_rate=float(val["damodaran_key_person_discount_classical"]),
        max_premium_when_inverted=float(val["damodaran_inverted_max_premium"]),
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Classical adjusted value", f"${cls_adj / 1e6:.1f}M",
                   delta=f"−{val['damodaran_key_person_discount_classical']*100:.1f}%")
    with col2:
        st.metric("Inverted adjusted value", f"${inv_adj / 1e6:.1f}M",
                   delta=f"{inv_comp['effective_discount_rate']*100:+.1f}%")
    with col3:
        st.metric("Regime", inv_comp["regime"].title())

    if inv_comp["regime"] == "inverted":
        st.success(
            f"✅ **Inversion regime active.** The sign of the key-person "
            f"discount has flipped: a team whose Layer-4 share ({l4_share:.0%}) "
            f"is above the threshold "
            f"({val['damodaran_inverted_threshold_layer4_share']:.0%}) with "
            f"high AI substitution potential ({ai_sub:.0%}) is now a "
            f"**negative signal of legacy cost overhang**."
        )
    else:
        st.info(
            f"ℹ️ **Classical regime.** The team Layer-4 share ({l4_share:.0%}) "
            f"is below the threshold "
            f"({val['damodaran_inverted_threshold_layer4_share']:.0%}), so the "
            f"classical positive-sign discount applies."
        )

    st.markdown("---")
    st.subheader("📈 Inverted key-person heatmap (live)")
    st.markdown("Effective discount rate as a function of team L4 share and "
                 "AI substitution potential. The black dashed line marks the "
                 "sign flip. **Edits to the threshold, classical rate, or max "
                 "premium in ⚙️ Configuration propagate here instantly.**")

    from app.shared import live_figures
    fig = live_figures.inverted_discount_heatmap(
        threshold_layer4_share=float(val["damodaran_inverted_threshold_layer4_share"]),
        classical_discount_rate=float(val["damodaran_key_person_discount_classical"]),
        max_premium_when_inverted=float(val["damodaran_inverted_max_premium"]),
        min_substitution_for_inversion=float(
            val["damodaran_inversion_min_substitution_potential"]),
    )
    st.pyplot(fig, use_container_width=True)
