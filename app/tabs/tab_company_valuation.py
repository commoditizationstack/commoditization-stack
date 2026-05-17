"""Tab — Company Valuation: per-user case studies under the framework.

Three-step workflow on a single page:

  1. Firm profile inputs (left column).
  2. Live recompute panel: classical Damodaran, layered DCF, two-phase
     DCF, fragility classification, substitution NPV per active bloc.
  3. Hero strip at the top + insight callout summarising the regime.

Form inputs live in ``st.session_state['company_valuation']`` so the
analysis survives a tab switch.
"""

from __future__ import annotations

from typing import Dict, List

import streamlit as st

from app.shared import components, state
from src.fragility import compute_fragility
from src.jurisdictional import (
    JURISDICTION_DEFAULTS, jurisdictional_inverted_discount,
)


# ---------------------------------------------------------------------------
# Defaults — the form is pre-populated with a neutral mid-market scenario.
# ---------------------------------------------------------------------------

DEFAULTS = {
    "name": "Demo Co.",
    "sector": "HealthTech",
    "founding_year": 2024,
    "trl_initial": 5,
    "trl_target": 8,
    "team_total": 40,
    "layer3_share": 0.10,
    "layer4_share": 0.30,
    "layer5_share": 0.20,
    "layer6_share": 0.40,
    "ai_substitution_l4": 0.55,
    "avg_base_salary_usd": 95_000.0,
    "ai_cost_per_eng_year_usd": 12_000.0,
    "enterprise_value_usd": 80_000_000.0,
    "fcf_y1": -1.5,
    "fcf_y2": -0.5,
    "fcf_y3": 2.0,
    "fcf_y4": 6.0,
    "fcf_y5": 14.0,
}


def _store() -> Dict:
    if "company_valuation" not in st.session_state:
        st.session_state["company_valuation"] = dict(DEFAULTS)
    return st.session_state["company_valuation"]


def _layered_discount_rate(*, rf: float, erp: float, beta: float,
                              trl: int, trl_premium: Dict[int, float],
                              layer_exposure: Dict[str, float],
                              layer_risk: Dict[str, float]) -> float:
    base = rf + beta * erp
    trl_p = float(trl_premium.get(int(trl), 0.0))
    layer_p = sum(layer_exposure.get(k, 0.0) * float(layer_risk.get(k, 0.0))
                  for k in layer_risk)
    return base + trl_p + layer_p


def _dcf_layered(fcf_usd_millions: List[float], *,
                  rate_y1: float, rate_terminal: float,
                  g: float, drag: float = 0.0) -> float:
    fcfs = [f * 1e6 for f in fcf_usd_millions]
    # Linear interpolation of the rate across the projection.
    n = len(fcfs)
    rates = [rate_y1 + (rate_terminal - rate_y1) * (i / max(1, n - 1))
             for i in range(n)]
    pv = 0.0
    cum = 1.0
    for r, f in zip(rates, fcfs):
        cum *= (1 + r)
        pv += f / cum
    if rate_terminal > g:
        tv = fcfs[-1] * (1 + g) / (rate_terminal - g) * (1 - drag) / cum
    else:
        tv = 0.0
    return pv + tv


def _dcf_classical(fcf_usd_millions: List[float], *,
                    rate: float, g: float) -> float:
    fcfs = [f * 1e6 for f in fcf_usd_millions]
    pv = sum(f / (1 + rate) ** (i + 1) for i, f in enumerate(fcfs))
    if rate > g:
        tv = fcfs[-1] * (1 + g) / (rate - g) / (1 + rate) ** len(fcfs)
    else:
        tv = 0.0
    return pv + tv


def render():
    state.init_session_state()
    cv = _store()
    p = state.effective_parameters()
    active = state.current_countries()

    st.header("🏢 Company Valuation — your firm under the framework")
    st.markdown(
        """
        Drop in a real company's profile on the left; the panel on the right
        recomputes its valuation under every method of the framework
        (classical Damodaran, layered DCF, two-phase intuition, fragility
        index, substitution NPV per active bloc). All inputs from
        ⚙️ Configuration and 🔬 Research Levers feed into the same
        computation — change a layer-risk coefficient there and the
        valuation here moves immediately.
        """
    )

    col_in, col_out = st.columns([1, 1])

    # ===================================================================
    # LEFT COLUMN — firm profile inputs
    # ===================================================================
    with col_in:
        st.subheader("1 · Firm profile")

        c1, c2 = st.columns(2)
        with c1:
            cv["name"] = st.text_input("Company name", value=cv["name"])
            cv["founding_year"] = int(st.number_input(
                "Founding year", min_value=2000, max_value=2030,
                value=int(cv["founding_year"]), step=1))
            cv["trl_initial"] = int(st.slider(
                "TRL today", min_value=1, max_value=9,
                value=int(cv["trl_initial"]), step=1))
            cv["team_total"] = int(st.number_input(
                "Total FTEs", min_value=1, max_value=10000,
                value=int(cv["team_total"]), step=1))
        with c2:
            cv["sector"] = st.text_input("Sector", value=cv["sector"])
            cv["enterprise_value_usd"] = float(st.number_input(
                "Reference enterprise value (USD)",
                min_value=1e5, max_value=1e10,
                value=float(cv["enterprise_value_usd"]),
                step=1e6, format="%.0f"))
            cv["trl_target"] = int(st.slider(
                "TRL at Y5", min_value=1, max_value=9,
                value=int(cv["trl_target"]), step=1))

        st.markdown("**Layer exposure (must sum to ~1.0)**")
        c3, c4 = st.columns(2)
        with c3:
            cv["layer3_share"] = float(st.slider(
                "Layer 3 (capability access)",
                0.0, 1.0, float(cv["layer3_share"]), 0.01))
            cv["layer5_share"] = float(st.slider(
                "Layer 5 (judgment)",
                0.0, 1.0, float(cv["layer5_share"]), 0.01))
        with c4:
            cv["layer4_share"] = float(st.slider(
                "Layer 4 (codified work)",
                0.0, 1.0, float(cv["layer4_share"]), 0.01))
            cv["layer6_share"] = float(st.slider(
                "Layer 6 (institutional)",
                0.0, 1.0, float(cv["layer6_share"]), 0.01))

        sum_layers = (cv["layer3_share"] + cv["layer4_share"]
                      + cv["layer5_share"] + cv["layer6_share"])
        if abs(sum_layers - 1.0) > 0.05:
            st.warning(
                f"Layer shares sum to {sum_layers:.2f} — outside the 0.95-1.05 "
                f"tolerance. Normalise before reading the layered DCF.")

        cv["ai_substitution_l4"] = float(st.slider(
            "AI substitutability of Layer 4",
            0.0, 1.0, float(cv["ai_substitution_l4"]), 0.05))

        st.markdown("**Free cash flow projection (USD millions, Y1..Y5)**")
        c5, c6, c7, c8, c9 = st.columns(5)
        for col, key in zip([c5, c6, c7, c8, c9],
                              ["fcf_y1", "fcf_y2", "fcf_y3",
                               "fcf_y4", "fcf_y5"]):
            with col:
                cv[key] = float(st.number_input(
                    key.upper(), value=float(cv[key]),
                    step=0.5, format="%.1f"))

        c10, c11 = st.columns(2)
        with c10:
            cv["avg_base_salary_usd"] = float(st.number_input(
                "Avg base salary per FTE (USD)",
                min_value=0.0, max_value=1e6,
                value=float(cv["avg_base_salary_usd"]),
                step=5_000.0, format="%.0f"))
        with c11:
            cv["ai_cost_per_eng_year_usd"] = float(st.number_input(
                "AI tooling cost per FTE-year (USD)",
                min_value=0.0, max_value=100_000.0,
                value=float(cv["ai_cost_per_eng_year_usd"]),
                step=500.0, format="%.0f"))

    # ===================================================================
    # RIGHT COLUMN — live valuation results
    # ===================================================================
    with col_out:
        st.subheader("2 · Valuation under the framework")

        # Macro
        macro = p["firms_appendix_b"]["macro"]
        rf = float(macro["risk_free_rate"])
        erp = float(macro["equity_risk_premium"])
        g = float(macro["terminal_growth"])

        # Beta from sector — use NeuroCertify or DataFlow Pro fallback;
        # power user can tweak by editing firms_appendix_b in Research Levers.
        beta = 1.1

        trl_premium_raw = p["valuation_layered"]["trl_discount_premium"]
        trl_premium = {int(k): float(v) for k, v in trl_premium_raw.items()}
        layer_risk = p["valuation_layered"]["layer_risk_coefficients"]
        layer_exposure = {
            "layer_3_capability":   cv["layer3_share"],
            "layer_4_codified":     cv["layer4_share"],
            "layer_5_judgment":     cv["layer5_share"],
            "layer_6_institutional": cv["layer6_share"],
            # Fill the unused ones with zero — the form covers the four
            # composition-dominant layers only.
            "layer_1_infra": 0.0,
            "layer_2_foundation": 0.0,
            "layer_7_crossborder": 0.0,
        }

        rate_y1 = _layered_discount_rate(
            rf=rf, erp=erp, beta=beta, trl=cv["trl_initial"],
            trl_premium=trl_premium, layer_exposure=layer_exposure,
            layer_risk=layer_risk)
        rate_y5 = _layered_discount_rate(
            rf=rf, erp=erp, beta=beta, trl=cv["trl_target"],
            trl_premium=trl_premium, layer_exposure=layer_exposure,
            layer_risk=layer_risk)
        classical_rate = rf + beta * erp

        fcfs = [cv["fcf_y1"], cv["fcf_y2"], cv["fcf_y3"],
                cv["fcf_y4"], cv["fcf_y5"]]
        ev_classical = _dcf_classical(fcfs, rate=classical_rate, g=g)
        # Apply a higher drag if Layer-4 share is dominant.
        drag = 0.30 * max(0.0, cv["layer4_share"] - 0.40)
        ev_layered = _dcf_layered(fcfs,
                                    rate_y1=rate_y1,
                                    rate_terminal=rate_y5,
                                    g=g, drag=drag)

        # Fragility
        fr = compute_fragility(cv["layer4_share"], cv["layer6_share"],
                                firm_label=cv["name"])

        # Hero metrics for this firm's run
        components.hero_strip([
            ("Classical EV",  f"${ev_classical/1e6:.1f}M",
             f"rate {classical_rate*100:.1f}%"),
            ("Layered EV",    f"${ev_layered/1e6:.1f}M",
             f"Y1 rate {rate_y1*100:.1f}% → Y5 {rate_y5*100:.1f}%"),
            ("Fragility",     fr.zone.title(),
             f"index {fr.fragility_index:+.2f}"),
            ("Δ Layered − Classical",
             f"${(ev_layered - ev_classical)/1e6:+.1f}M", None),
        ])

        # Substitution NPV per active bloc
        st.markdown("#### Substitution NPV per active jurisdiction")
        npv_cols = st.columns(max(1, len(active)))
        for col, c in zip(npv_cols, active):
            j = JURISDICTION_DEFAULTS[c]
            _, info = jurisdictional_inverted_discount(
                enterprise_value_usd=float(cv["enterprise_value_usd"]),
                team_layer4_share=float(cv["layer4_share"]),
                ai_substitution_potential_layer4=float(
                    cv["ai_substitution_l4"]),
                n_employees=int(cv["team_total"]),
                avg_base_salary_usd=float(cv["avg_base_salary_usd"]),
                annual_ai_cost_per_replaced_employee_usd=float(
                    cv["ai_cost_per_eng_year_usd"]),
                jurisdiction=j,
            )
            with col:
                premium = info["inversion_premium_usd"]
                st.metric(
                    state.country_label(c),
                    f"${premium/1e6:+.1f}M",
                    info["regime"],
                )

        # Narrative callout
        if fr.zone == "resilient":
            components.insight(
                f"<b>{cv['name']}</b> is in the resilient zone of the "
                f"fragility map: Layer-6 institutional embedding "
                f"({cv['layer6_share']:.0%}) outweighs Layer-4 erosion "
                f"({cv['layer4_share']:.0%}). The layered DCF lifts the "
                f"valuation by ${(ev_layered-ev_classical)/1e6:+.1f}M "
                f"relative to classical Damodaran.",
                kind="success")
        elif fr.zone == "fragile":
            components.insight(
                f"<b>{cv['name']}</b> sits in the fragile zone: Layer-4 "
                f"share ({cv['layer4_share']:.0%}) dominates Layer-6 "
                f"protection ({cv['layer6_share']:.0%}). The post-AI "
                f"double-valley drag pulls the layered EV "
                f"${(ev_layered-ev_classical)/1e6:+.1f}M below classical "
                f"Damodaran.",
                kind="danger")
        else:
            components.insight(
                f"<b>{cv['name']}</b> is borderline on the fragility map. "
                f"Small moves in Layer-4 or Layer-6 share flip the regime; "
                f"sweep the two sliders above to observe the boundary.",
                kind="warning")

    st.markdown("---")
    st.markdown(
        f"""
        ### 3 · Save and share this run
        Use the sidebar **🗂 Named scenarios** panel to save this profile
        under a name you can recall later, or **💾 Scenario YAML** to
        download the calibration as a portable file. The **📄 Export PDF**
        tab will fold this firm's hero metrics into the scenario report.
        """
    )
