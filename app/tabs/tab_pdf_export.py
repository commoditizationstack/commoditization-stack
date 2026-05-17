"""Tab — PDF report export (Phase 5)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

import streamlit as st

from app.shared import pdf_export, state
from src.distributional import compute_double_threshold, compute_xai_capacity_gap
from src.fragility import case_studies_fragility
from src.jurisdictional import (
    JURISDICTION_DEFAULTS,
    jurisdictional_inverted_discount,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def _build_summary_metrics(parameters: Dict, country_slug: str) -> Dict[str, str]:
    """Compute a small set of live executive-summary metrics."""
    overrides = st.session_state.get("overrides", {})

    metrics: Dict[str, str] = {}
    metrics["Selected jurisdiction"] = state.country_label(country_slug)
    metrics["Active parameter overrides"] = str(len(overrides))
    metrics["Currency"] = "USD (all monetary values)"

    # Fragility classifications
    fr = case_studies_fragility()
    nc = fr["neurocertify"]
    df = fr["dataflow_pro"]
    metrics["NeuroCertify — fragility index"] = (
        f"{nc.fragility_index:+.2f} ({nc.zone})"
    )
    metrics["DataFlow Pro — fragility index"] = (
        f"{df.fragility_index:+.2f} ({df.zone})"
    )

    # Double threshold (Appendix G)
    dt = compute_double_threshold()
    metrics["Economic break-even (engineers)"] = f"{dt.economic_break_even:.0f}"
    metrics["Compliance break-even (engineers)"] = f"{dt.compliance_break_even:.0f}"

    # XAI capacity gap (Appendix G)
    xai = compute_xai_capacity_gap()
    metrics["XAI gap @ year 8 — K7=1.0"] = f"Δ = {xai.endpoint_gaps['k_1_0']:.2f}"
    metrics["XAI gap @ year 8 — K7=0.45"] = f"Δ = {xai.endpoint_gaps['k_0_45']:.2f}"

    # Sample inverted-discount premium for the selected jurisdiction
    try:
        j = JURISDICTION_DEFAULTS[country_slug]
        v_cfg = parameters["valuation"]
        startup_cfg = parameters.get("startup", {})
        adjusted, info = jurisdictional_inverted_discount(
            enterprise_value_usd=float(v_cfg.get("enterprise_value_usd", 50_000_000)),
            team_layer4_share=float(v_cfg.get(
                "damodaran_inverted_threshold_layer4_share", 0.45)) + 0.15,
            ai_substitution_potential_layer4=float(v_cfg.get(
                "damodaran_inversion_min_substitution_potential", 0.4)) + 0.2,
            n_employees=int(startup_cfg.get("n_employees", 50)),
            avg_base_salary_usd=float(startup_cfg.get(
                "avg_base_salary_usd", 120_000)),
            annual_ai_cost_per_replaced_employee_usd=float(startup_cfg.get(
                "annual_ai_cost_per_replaced_employee_usd", 18_000)),
            jurisdiction=j,
        )
        metrics[f"Sample inversion premium ({state.country_label(country_slug)})"] = (
            f"${info['inversion_premium_usd']:,.0f} ({info['regime']})"
        )
    except Exception as exc:
        metrics["Sample inversion premium"] = f"(unavailable: {exc})"

    return metrics


def render():
    state.init_session_state()

    st.header("📄 Export PDF Report")
    st.markdown(
        """
        Generate a single PDF capturing the current scenario:

        - **Cover page** with timestamp, jurisdiction, and number of active overrides
        - **Executive summary** — live metrics (fragility, thresholds, sample
          inversion premium for the selected country)
        - **Complete parameter table** — every value in the active overlay,
          with a ★ next to anything you've changed
        - **All available figures** from the framework (up to 41 PNGs) with
          paper-style captions
        - **Scenario YAML appendix** — paste it back later to reproduce this run

        > 💵 All monetary values in USD.
        > Generation takes ~3–8 seconds depending on how many figures are
        > present on disk.
        """
    )

    fig_count = sum(1 for fname in {f for _, f, _ in pdf_export.FIGURE_MANIFEST}
                    if (FIG_DIR / fname).exists())
    total_fig = len({fname for _, fname, _ in pdf_export.FIGURE_MANIFEST})

    cols = st.columns(3)
    with cols[0]:
        st.metric("Figures available", f"{fig_count} / {total_fig}")
    with cols[1]:
        st.metric("Active overrides",
                   str(len(st.session_state.get("overrides", {}))))
    with cols[2]:
        st.metric("Jurisdiction", state.country_label())

    if fig_count < total_fig:
        st.warning(
            f"⚠️ {total_fig - fig_count} figures not yet generated. "
            f"Use 🔄 **Recompute All** in the sidebar (or the launcher) to "
            f"regenerate them under your scenario before exporting."
        )

    st.markdown("---")

    if st.button("🛠 Generate PDF report", type="primary",
                  use_container_width=True):
        country_slug = state.current_country()
        parameters = state.effective_parameters()
        overrides = dict(st.session_state.get("overrides", {}))
        countries = state.current_countries()
        countries_label = " · ".join(state.country_labels(countries))

        with st.spinner("Building PDF — embedding figures, this may take a few seconds…"):
            try:
                summary_metrics = _build_summary_metrics(parameters, country_slug)
                pdf_bytes = pdf_export.generate_pdf_report(
                    parameters=parameters,
                    overrides=overrides,
                    country_label=countries_label,
                    summary_metrics=summary_metrics,
                )
            except Exception as exc:
                st.error(f"❌ PDF generation failed: {exc}")
                st.exception(exc)
                return

        # Persist the bytes in session_state so the download button survives reruns
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.session_state["last_pdf_bytes"] = pdf_bytes
        st.session_state["last_pdf_name"] = (
            f"cost_gradient_report_{country_slug}_{ts}.pdf"
        )
        st.success(f"✅ PDF ready — {len(pdf_bytes) / 1024:.0f} KB.")

    if st.session_state.get("last_pdf_bytes"):
        st.download_button(
            label="⬇️ Download PDF",
            data=st.session_state["last_pdf_bytes"],
            file_name=st.session_state.get("last_pdf_name", "report.pdf"),
            mime="application/pdf",
            use_container_width=True,
        )
        st.caption(
            f"File: `{st.session_state.get('last_pdf_name', 'report.pdf')}` · "
            f"{len(st.session_state['last_pdf_bytes']) / 1024:.0f} KB"
        )
