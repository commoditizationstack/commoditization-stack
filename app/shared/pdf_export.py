"""PDF report generation for the Streamlit simulator.

Produces a single A4 PDF containing:
  1. Cover page (timestamp, country, override count, executive summary)
  2. Complete parameter table organised by section, ~120 rows
  3. All 41 figures from the framework with paper-style captions
  4. Scenario YAML appendix for reproducibility

Built with reportlab. Self-contained; no external services.

The PDF is generated entirely in memory and returned as bytes for
st.download_button(). Generation typically takes 3-8 seconds depending on
the number of figures embedded.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


# ----------------------------------------------------------------------------
# Figure manifest (paper section → figure file → caption)
# ----------------------------------------------------------------------------

FIGURE_MANIFEST: List[Tuple[str, str, str]] = [
    # Section 4 — Seven-layer framework
    ("Section 4 — Seven-layer framework", "fig1_layer_velocities.png",
     "Commoditization velocity by layer of the knowledge-production stack."),
    ("Section 4 — Seven-layer framework", "fig2_substitutability_trajectories.png",
     "Layer-by-layer substitutability trajectories, 2026-2034."),
    ("Section 4.1 — K7 / Layer 7", "fig14_knowledge_regime_geometry.png",
     "Geometry of the cross-border knowledge regime (Layer 7 hypothetical)."),
    ("Section 4.1 — K7 / Layer 7", "fig15_layer7_k_sensitivity.png",
     "Sensitivity of the inversion premium to K7 across jurisdictions."),
    # Section 6 — Valuation
    ("Section 6.4 — Inverted key-person discount",
     "fig3_inverted_keyperson_heatmap.png",
     "Inverted Damodaran heatmap (team L4 share × AI substitutability)."),
    ("Section 6.5 — Hype Cycle & valleys", "fig4_hype_cycle.png",
     "Gartner Hype Cycle: classical (single valley) vs post-AI (double valley)."),
    ("Section 6.5 — Hype Cycle & valleys", "fig5_death_valley.png",
     "Cash trajectory under classical vs post-AI regimes."),
    ("Section 6.5 — Hype Cycle & valleys", "fig6_arr_trajectories.png",
     "ARR trajectories under each scenario."),
    ("Section 6.5 — Hype Cycle & valleys", "fig7_valuation_comparison.png",
     "Valuation comparison across methods."),
    # Section 7 — Jurisdictional
    ("Section 7 — Jurisdictional substitution",
     "fig8_survival_rates.png", "Monte Carlo survival rates by scenario."),
    ("Section 7 — Jurisdictional substitution",
     "fig9_valuation_distributions.png", "Valuation distributions."),
    ("Section 7 — Jurisdictional substitution",
     "fig10_keyperson_inversion_distribution.png",
     "Key-person inversion premium distribution."),
    ("Section 7.3 — Counterintuitive ordering",
     "fig11_jurisdictional_inversion.png",
     "Inversion premium across three jurisdictions (annual cost flow + EV %)."),
    ("Section 7.3 — Counterintuitive ordering",
     "fig12_substitution_npv_decomposition.png",
     "Substitution NPV decomposition (savings vs termination)."),
    ("Section 7.4 — Cross-border M&A", "fig13_crossborder.png",
     "Cross-border M&A operating-cost basis."),
    # Section 7.5 — Migration dynamics
    ("Section 7.5 — Migration dynamics",
     "fig21_migration_reference_firm.png",
     "Reference firm migration cash flow (50 engineers, 60% sub.)."),
    ("Section 7.5 — Migration dynamics",
     "fig22_neurocertify_migration.png",
     "NeuroCertify migration cash flow (Brazil/France/Consolidated)."),
    ("Section 7.5 — Migration dynamics",
     "fig23_dataflow_migration.png",
     "DataFlow Pro migration cash flow (3 substitution scenarios)."),
    # Appendix A — Layered DCF
    ("Appendix A — Layered DCF", "fig16_trl_discount_trajectory.png",
     "TRL-modulated discount rate trajectory."),
    ("Appendix A — Layered DCF", "fig17_layer_risk_decomposition.png",
     "Layer-decomposed firm-specific risk premium."),
    ("Appendix A — Layered DCF", "fig18_valuation_comparison.png",
     "Enterprise value: classical Damodaran vs layered DCF."),
    # Appendix B — Two-phase
    ("Appendix B — Two-phase CAPM/WACC", "fig19_two_phase_cost_of_capital.png",
     "Two-phase WACC trajectory for NeuroCertify and DataFlow Pro."),
    ("Appendix B — Two-phase CAPM/WACC", "fig20_two_phase_eva_trajectory.png",
     "Phase-conditional EVA vs classical single-WACC EVA."),
    # Appendix D — Streaming + fiscal
    ("Appendix D — Streaming case", "fig24_streaming_price_decomp.png",
     "Streaming price decomposition under 3 substitution scenarios."),
    ("Appendix D — Streaming case", "fig25_streaming_cross_jurisdictional.png",
     "Cross-jurisdictional price competition (5 pairings × 3 scenarios)."),
    ("Appendix D — Streaming case", "fig26_streaming_capital_trajectory.png",
     "Capital trajectory: legacy vs IA-native model."),
    ("Appendix D — Streaming case", "fig27_streaming_phase_risk.png",
     "Phase-conditional CAPM β: legacy vs IA-native."),
    ("Appendix D — Streaming case", "fig28_streaming_dilution_multiple.png",
     "Founder dilution + expected investor multiple by entry stage."),
    ("Appendix D — Streaming case", "fig29_streaming_payoff_matrix.png",
     "Payoff matrix: price advantage × catalog parity."),
    ("Appendix D — Fiscal blocs", "fig30_fiscal_blocs.png",
     "5-year fiscal impact across three jurisdictional blocs."),
    # Appendix E — Dynamic case companies
    ("Appendix E — Dynamic case companies",
     "fig31_appendix_e_migration.png",
     "Combined NC + DF migration cash flow trajectories."),
    ("Appendix E — Dynamic case companies",
     "fig32_appendix_e_capital.png",
     "Capital trajectory NC vs DF, legacy vs IA-native."),
    ("Appendix E — Dynamic case companies",
     "fig33_appendix_e_risk.png",
     "Phase-conditional risk curves with valley annotations."),
    ("Appendix E — Dynamic case companies",
     "fig34_appendix_e_dilution.png",
     "Founder dilution + expected investor multiple."),
    ("Appendix E — Dynamic case companies",
     "fig35_appendix_e_fragility.png",
     "Fragility map of NC + DF across L4 × L6 space."),
    # Appendix F — Upstream chain
    ("Appendix F — Upstream chain",
     "fig36_appendix_f_scope.png",
     "Scope of the framework (prices vs not-prices)."),
    ("Appendix F — Upstream chain",
     "fig37_appendix_f_mapping.png",
     "Mapping of 7 upstream firm categories onto 7 layers."),
    ("Appendix F — Upstream chain",
     "fig38_appendix_f_sensitivities.png",
     "Three structural sensitivities the framework illuminates."),
    ("Appendix F — Upstream chain",
     "fig39_appendix_f_asymmetries.png",
     "Recovery composition asymmetries under structural recalibration."),
    # Appendix G — Distributional + epistemic
    ("Appendix G — Distributional + epistemic",
     "fig40_appendix_g_threshold.png",
     "Double threshold for AI migration in regulated small firms."),
    ("Appendix G — Distributional + epistemic",
     "fig41_appendix_g_xai_gap.png",
     "XAI capacity gap across two blocs under three K7 regimes."),
]


# ----------------------------------------------------------------------------
# Parameter manifest (which top-level sections to include in the variable table)
# ----------------------------------------------------------------------------

PARAMETER_SECTIONS_TO_INCLUDE = [
    "simulation", "monte_carlo", "stack_layers", "knowledge_regimes", "startup",
    "investor", "valuation", "valuation_layered", "valuation_two_phase",
    "firms_appendix_b", "jurisdictions", "hype_cycle", "death_valley",
    "migration_dynamics", "streaming_case", "fiscal_blocs", "fragility_index",
    "upstream_chain", "distributional", "case_studies_dynamic", "macro",
    "funding_stages_carta", "streamlit_ui", "structural",
]


# Short, human-readable description for each parameter section.
SECTION_DESCRIPTIONS: Dict[str, str] = {
    "simulation": "Core simulation controls: random seed, Monte-Carlo run count, "
                  "and the simulation horizon in quarters.",
    "monte_carlo": "Coefficients of variation (log-normal envelopes) that perturb "
                   "team size, burn rate, AI substitution, market multiple and "
                   "layer velocities across Monte-Carlo iterations.",
    "stack_layers": "Section 4 — definition of the seven-layer knowledge-production "
                    "stack: each layer's commoditization velocity and its 2026 "
                    "substitutability starting value.",
    "knowledge_regimes": "Section 4.1 — the cross-border knowledge-integration "
                         "coefficient K7 under three reference regimes "
                         "(globalized 2020, current 2026, fragmented 2030) and "
                         "the cross-border friction it implies.",
    "startup": "Reference startup used in the canonical simulation: team size, "
               "burn rate, funding events, growth dynamics, and substitution "
               "potential of its Layer-4 work.",
    "investor": "Investor scoring framework: thesis weights (classical vs "
                "AI-aware), target IRR, hold period and decision threshold.",
    "valuation": "Section 6 — classical valuation parameters: Damodaran's "
                 "key-person discount (and its inverted variant), Berkus, VC "
                 "method and comparable-multiples constants.",
    "valuation_layered": "Appendix A — layered DCF inputs: TRL premium schedule, "
                         "per-layer risk coefficients, default layer exposure, "
                         "and US funding-stage benchmarks.",
    "valuation_two_phase": "Appendix B — default two-phase CAPM/WACC parameters: "
                            "phase boundaries, per-phase β, D/E and Kd spreads, "
                            "and effective tax rate.",
    "firms_appendix_b": "Appendix B — firm-specific two-phase calibration for the "
                         "two case studies (NeuroCertify, DataFlow Pro): industry "
                         "betas, capital structure trajectory and free cash flows.",
    "jurisdictions": "Section 7 — fiscal-accounting parameters per jurisdiction "
                      "(Brazil/CLT, France/CDI, United States/W-2): labor "
                      "multiplier, termination cost, AI-service overhead and "
                      "vendor-risk WACC premium.",
    "hype_cycle": "Section 6.5 — quarterly coordinates of the classical Hype Cycle "
                   "and the post-GenAI double-valley variant.",
    "death_valley": "Section 6.5 — cash-trajectory parameters under classical and "
                     "post-GenAI regimes (burn, refinancing, valley boundaries).",
    "migration_dynamics": "Section 7.5 — quarter-by-quarter migration model: "
                           "assessment phase, AI orchestrator overhead, learning "
                           "curve, retention bonus and per-jurisdiction loaded "
                           "costs.",
    "streaming_case": "Appendix D — streaming incumbent case study: revenue, "
                       "plan price, cost decomposition, three substitution "
                       "scenarios and cross-bloc friction.",
    "fiscal_blocs": "Appendix D.6 — 5-year jurisdictional fiscal impact: lost "
                     "social charges, AI-token export, compensating corporate-"
                     "tax gain, and transfer-pricing shares.",
    "fragility_index": "Appendix E.5 — fragility-index formula constants "
                        "(L6 coefficient, resilient/fragile thresholds, color "
                        "scale).",
    "upstream_chain": "Appendix F — seven upstream-AI firm categories mapped "
                       "onto the seven layers, plus capex-sensitivity grid "
                       "parameters.",
    "distributional": "Appendix G — distributional / epistemic dimensions: "
                       "double threshold for institution-dominant firms and "
                       "XAI capacity-gap trajectories under three K7 regimes.",
    "case_studies_dynamic": "Appendix E — dynamic calibration of the two case "
                             "companies: TRL trajectory, free cash flows, layer "
                             "exposure, β trajectory and migration scenarios.",
    "macro": "Macroeconomic constants used across modules: risk-free rate, "
              "equity risk premium and terminal growth rate.",
    "funding_stages_carta": "Carta Q3 2025 benchmarks: round size, pre-money "
                              "median, typical dilution and expected investor "
                              "multiple by stage.",
    "streamlit_ui": "UI defaults for the simulator: slider ranges, default firm "
                     "profiles and tab-specific display parameters. These do "
                     "not affect simulation outputs.",
    "structural": "Rarely-tuned structural constants: stack-layer logit scaling "
                   "and substitutability clip bounds.",
}


# Per-paper-section context for the Figures chapter. Keys must match the
# leading entries used in FIGURE_MANIFEST.
FIGURE_SECTION_DESCRIPTIONS: Dict[str, str] = {
    "Section 4 — Seven-layer framework":
        "How fast each layer of the knowledge-production stack is being "
        "commoditized by AI, and where each layer stands in 2026.",
    "Section 4.1 — K7 / Layer 7":
        "The cross-border knowledge-integration regime — a hypothetical seventh "
        "layer that modulates Layer-4 substitutability and the relative value "
        "of Layer-5 judgment as integration falls.",
    "Section 6.4 — Inverted key-person discount":
        "How a high Layer-4 team share combined with high AI substitution "
        "potential flips Damodaran's classical key-person discount into an "
        "acquisition premium.",
    "Section 6.5 — Hype Cycle & valleys":
        "The post-GenAI double-valley dynamic: a second commoditization valley "
        "appears after the classical trough, with material consequences for "
        "cash trajectories, ARR and exit valuations.",
    "Section 7 — Jurisdictional substitution":
        "Monte-Carlo distribution of survival and valuation outcomes across "
        "four scenarios; distribution of the key-person inversion premium.",
    "Section 7.3 — Counterintuitive ordering":
        "When the inversion regime is active, the magnitude of the premium "
        "scales with the cost-of-labor base — putting the United States ahead "
        "of France and Brazil despite higher headline costs.",
    "Section 7.4 — Cross-border M&A":
        "Operating-cost basis comparison when an acquirer reproduces the "
        "target's economic activity from its own jurisdiction vs holding the "
        "team locally.",
    "Section 7.5 — Migration dynamics":
        "Quarterly cash-flow trajectory under the AI orchestrator model: "
        "assessment phase, dual operation, learning curve and steady state, "
        "across reference firm and the two case companies.",
    "Appendix A — Layered DCF":
        "Layered DCF demonstration on NeuroCertify and DataFlow Pro: TRL "
        "discount trajectory, layer-decomposed firm-specific risk premium, and "
        "enterprise value vs the classical Damodaran benchmark.",
    "Appendix B — Two-phase CAPM/WACC":
        "Numerical demonstration of the phase-conditional reformulation: how "
        "WACC, Ke and EVA trajectories differ from their classical "
        "single-rate counterparts.",
    "Appendix D — Streaming case":
        "Mature streaming incumbent vs IA-native entrant: price decomposition, "
        "cross-jurisdictional pricing, capital trajectory, phase-conditional "
        "risk, founder dilution and the strategic payoff matrix.",
    "Appendix D — Fiscal blocs":
        "5-year jurisdictional fiscal impact decomposition: lost social "
        "charges, AI-token export, and compensating corporate-tax gain across "
        "Brazil, France and the United States.",
    "Appendix E — Dynamic case companies":
        "Combined view of NeuroCertify and DataFlow Pro: migration cash flow, "
        "capital trajectory, phase-conditional risk curves, founder dilution "
        "and the L4 × L6 fragility map.",
    "Appendix F — Upstream chain":
        "Mapping of seven categories of upstream AI value-chain firms onto the "
        "seven-layer framework, with the three structural sensitivities the "
        "framework illuminates and the recovery-composition asymmetries.",
    "Appendix G — Distributional + epistemic":
        "Double threshold for AI migration in regulated small firms, and the "
        "XAI capacity-gap accumulation across two reference blocs under three "
        "K7 regimes.",
}


# ----------------------------------------------------------------------------
# Style sheet
# ----------------------------------------------------------------------------

def _build_styles() -> Dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=styles["Title"],
                                 fontSize=22, textColor=colors.HexColor("#1B3A57"),
                                 spaceAfter=12, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", parent=styles["Normal"],
                                    fontSize=12, textColor=colors.HexColor("#3C6E91"),
                                    spaceAfter=18, alignment=TA_CENTER),
        "h1": ParagraphStyle("h1", parent=styles["Heading1"],
                              fontSize=14, textColor=colors.HexColor("#1B3A57"),
                              spaceBefore=12, spaceAfter=6, keepWithNext=True),
        "h2": ParagraphStyle("h2", parent=styles["Heading2"],
                              fontSize=11, textColor=colors.HexColor("#2C5282"),
                              spaceBefore=6, spaceAfter=4, keepWithNext=True),
        "body": ParagraphStyle("body", parent=styles["Normal"],
                                fontSize=9.5, leading=13, alignment=TA_JUSTIFY,
                                spaceAfter=6),
        "caption": ParagraphStyle("caption", parent=styles["Normal"],
                                   fontSize=8.5, leading=11, alignment=TA_CENTER,
                                   textColor=colors.HexColor("#555555"),
                                   spaceAfter=10),
        "code": ParagraphStyle("code", parent=styles["Code"],
                                fontSize=7.5, leading=10,
                                textColor=colors.HexColor("#222222")),
        "meta": ParagraphStyle("meta", parent=styles["Normal"],
                                fontSize=10, leading=14, alignment=TA_CENTER,
                                textColor=colors.HexColor("#555555")),
        # Used inside the parameter tables — character-level word-wrap so long
        # dot-paths break cleanly instead of overflowing into the value column.
        "table_path": ParagraphStyle("table_path", parent=styles["Normal"],
                                       fontSize=7, leading=8.5,
                                       wordWrap="CJK",
                                       textColor=colors.HexColor("#1A1A1A")),
        "table_value": ParagraphStyle("table_value", parent=styles["Normal"],
                                        fontSize=7, leading=8.5,
                                        wordWrap="CJK",
                                        textColor=colors.HexColor("#1A1A1A")),
        # Caption used in the figures chapter — left-aligned, slightly larger
        # than the table cells, with room for an interpretation line below.
        "fig_caption": ParagraphStyle("fig_caption", parent=styles["Normal"],
                                        fontSize=8.5, leading=11,
                                        alignment=TA_CENTER,
                                        textColor=colors.HexColor("#444444"),
                                        spaceAfter=8),
        # Per-section explainer above each parameter table / figure group.
        "intro": ParagraphStyle("intro", parent=styles["Normal"],
                                  fontSize=9, leading=12,
                                  alignment=TA_JUSTIFY,
                                  textColor=colors.HexColor("#444444"),
                                  spaceAfter=6),
    }


# ----------------------------------------------------------------------------
# Section builders
# ----------------------------------------------------------------------------

def _cover_page(styles, *, country_label: str, override_count: int,
                 timestamp: str) -> List:
    elements = []
    elements.append(Spacer(1, 4 * cm))
    elements.append(Paragraph("The Cost Gradient of the Build", styles["title"]))
    elements.append(Paragraph("Interactive Simulator — Scenario Report",
                                styles["subtitle"]))
    elements.append(Spacer(1, 1 * cm))
    elements.append(HRFlowable(width="60%", color=colors.HexColor("#1B3A57"),
                                 thickness=1, hAlign="CENTER"))
    elements.append(Spacer(1, 1.5 * cm))
    elements.append(Paragraph(f"<b>Generated:</b> {timestamp}", styles["meta"]))
    elements.append(Paragraph(f"<b>Active jurisdictions:</b> {country_label}",
                                styles["meta"]))
    elements.append(Paragraph(f"<b>Active overrides:</b> {override_count}",
                                styles["meta"]))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("💵 All monetary values in USD", styles["meta"]))
    elements.append(Spacer(1, 3 * cm))
    elements.append(Paragraph(
        "Companion to de Miranda Neto (2026), "
        "<i>The Cost Gradient of the Build</i>. "
        "Framework, parameters, simulation code, and this report are "
        "open-source under the MIT license.",
        styles["body"]))
    elements.append(PageBreak())
    return elements


def _executive_summary(styles, *, summary_metrics: Dict[str, str]) -> List:
    elements = [Paragraph("Executive Summary", styles["h1"])]
    elements.append(Paragraph(
        "Live metrics computed under the current parameter overlay and the "
        "selected jurisdiction. All values in USD.",
        styles["body"]))

    # Table of metrics
    table_data = [["Metric", "Value"]]
    for k, v in summary_metrics.items():
        table_data.append([k, v])
    table = Table(table_data, colWidths=[10 * cm, 6 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B3A57")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#F5F7FA"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(table)
    elements.append(PageBreak())
    return elements


def _flatten_params(data: Dict, prefix: str = "") -> List[Tuple[str, str]]:
    """Flatten a nested dict to a list of (dot_path, str_value) tuples."""
    out: List[Tuple[str, str]] = []
    for k, v in data.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.extend(_flatten_params(v, key))
        elif isinstance(v, list):
            out.append((key, str(v)))
        else:
            out.append((key, str(v)))
    return out


def _escape(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _get_by_dot_path(parameters: Dict[str, Any], path: str) -> Any:
    """Walk a dotted path through a nested dict; return None if missing.

    Tries the string key first; falls back to int(part) when the part
    is all-digit. (YAML loads keys like ``1: 0.16`` as integers, not
    strings.)
    """
    cur: Any = parameters
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        if part in cur:
            cur = cur[part]
        elif part.lstrip("-").isdigit() and int(part) in cur:
            cur = cur[int(part)]
        else:
            return None
    return cur


def _format_value(value: Any, fmt: str) -> str:
    """Render a parameter value for the table cell."""
    if value is None:
        return "—"
    try:
        if fmt == "%d":
            return f"{int(value)}"
        if fmt.startswith("%."):
            return fmt % float(value)
    except (TypeError, ValueError):
        pass
    return str(value)


def _parameter_tables(styles, *, parameters: Dict[str, Any],
                       overrides: Dict[str, Any]) -> List:
    """Build the curated research-levers chapter of the PDF.

    Driven by app.shared.research_levers.LEVER_GROUPS — the same manifest
    that powers the 🔬 Research Levers tab. Internal-mechanics parameters
    (random seeds, grid sizes, plot constants) are intentionally excluded.

    Each group is a section with a short intro and a table of
    Parameter / Description / Value / Modified. Section headers are
    glued to their first table chunk via KeepTogether to avoid orphans.
    """
    # Local import keeps the module load-order light.
    from . import research_levers

    elements: List = [Paragraph("Research levers — parameters that matter",
                                  styles["h1"])]
    elements.append(Paragraph(
        f"This chapter records the parameters a working researcher or PhD "
        f"student would plausibly want to manipulate to test a hypothesis "
        f"under the framework. Internal mechanics — random seeds, "
        f"Monte-Carlo run counts, plot constants — are intentionally "
        f"omitted from this curated view; the full ⚙️ Configuration tab "
        f"of the simulator exposes them for power users. "
        f"Variables modified by the user are flagged with ★ in the "
        f"rightmost column. Total active overrides: <b>{len(overrides)}</b>. "
        f"💵 Monetary values are in USD where applicable.",
        styles["body"]))

    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C5282")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#FAFBFC"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])

    # Column widths: Parameter / Description / Value / Mod.
    col_widths = [4.6 * cm, 8.6 * cm, 2.0 * cm, 1.2 * cm]

    head = [
        Paragraph("<b>Parameter</b>", styles["table_path"]),
        Paragraph("<b>What it is</b>", styles["table_path"]),
        Paragraph("<b>Value</b>", styles["table_value"]),
        "Mod.",
    ]

    for group in research_levers.LEVER_GROUPS:
        header = Paragraph(group["label"], styles["h2"])
        intro = Paragraph(group["intro"], styles["intro"])

        body_rows: List[List] = []
        for spec in group["params"]:
            value = _get_by_dot_path(parameters, spec["dot_path"])
            modified = "★" if spec["dot_path"] in overrides else ""
            body_rows.append([
                Paragraph(_escape(spec["label"]), styles["table_path"]),
                Paragraph(_escape(spec["description"]), styles["table_value"]),
                Paragraph(_escape(_format_value(value, spec["format"])),
                            styles["table_value"]),
                modified,
            ])

        chunk_size = 18
        chunks = [body_rows[i:i + chunk_size]
                  for i in range(0, len(body_rows), chunk_size)] or [[]]
        for i, chunk in enumerate(chunks):
            tbl = Table([head] + chunk, colWidths=col_widths, repeatRows=1)
            tbl.setStyle(table_style)
            if i == 0:
                elements.append(KeepTogether([header, intro, tbl]))
            else:
                elements.append(tbl)
            elements.append(Spacer(1, 4 * mm))
    elements.append(PageBreak())
    return elements


def _figures_section(styles) -> List:
    """All available framework figures, grouped by paper section.

    The section heading is bundled with its intro and first figure via
    KeepTogether, so a heading never appears alone at the bottom of a
    page. Every figure carries an italicised caption immediately beneath
    it; figure + caption travel together to avoid orphan captions.
    """
    elements: List = [Paragraph("Figures from the framework", styles["h1"])]
    elements.append(Paragraph(
        "Every figure the simulator currently generates, grouped by the "
        "section of the paper it illustrates. The short paragraph under "
        "each section heading sketches what the reader should look for; "
        "below each image, the italicised line names the source PNG and "
        "summarises the chart. All charts reflect the parameter overlay "
        "active at the moment this report was built — to regenerate under "
        "a different scenario, use the 🔄 Recompute All control in the "
        "simulator sidebar.",
        styles["body"]))

    # Group manifest by paper section so we can keep the heading with the
    # first figure of each section.
    grouped: Dict[str, List[Tuple[str, str]]] = {}
    section_order: List[str] = []
    for section, fname, caption in FIGURE_MANIFEST:
        if section not in grouped:
            grouped[section] = []
            section_order.append(section)
        grouped[section].append((fname, caption))

    for section in section_order:
        # Render every figure that exists on disk for this section.
        rendered: List[Tuple[Image, str, str]] = []
        for fname, caption in grouped[section]:
            fp = FIG_DIR / fname
            if not fp.exists():
                continue
            try:
                img = Image(str(fp), width=16 * cm, height=10 * cm,
                             kind="proportional")
                rendered.append((img, fname, caption))
            except Exception as exc:
                elements.append(Paragraph(
                    f"[Could not embed {fname}: {exc}]", styles["body"]))

        if not rendered:
            continue

        header = Paragraph(section, styles["h2"])
        intro_text = FIGURE_SECTION_DESCRIPTIONS.get(
            section, "Reference figures for this section of the paper.")
        intro = Paragraph(intro_text, styles["intro"])

        # Glue header + intro + the first figure block together so the heading
        # never sits alone at the bottom of a page.
        first_img, first_fname, first_caption = rendered[0]
        first_block: List = [
            header,
            intro,
            first_img,
            Paragraph(f"<i>{first_fname}</i> — {first_caption}",
                       styles["fig_caption"]),
        ]
        elements.append(KeepTogether(first_block))
        elements.append(Spacer(1, 4 * mm))

        # Remaining figures: each kept together with its own caption.
        for img, fname, caption in rendered[1:]:
            elements.append(KeepTogether([
                img,
                Paragraph(f"<i>{fname}</i> — {caption}",
                           styles["fig_caption"]),
            ]))
            elements.append(Spacer(1, 4 * mm))

    elements.append(PageBreak())
    return elements


def _appendix_yaml(styles, *, overrides: Dict[str, Any]) -> List:
    """Scenario YAML appendix for reproducibility."""
    elements: List = [Paragraph("Appendix — Scenario YAML", styles["h1"])]
    elements.append(Paragraph(
        "This appendix records the exact set of parameter changes that were "
        "active when this report was built. It is a self-contained record of "
        "the scenario: anyone with access to the simulator can recreate the "
        "same numbers and figures by loading this YAML.",
        styles["body"]))

    if not overrides:
        elements.append(Paragraph(
            "<b>No parameter changes were active.</b> This report was built on "
            "the default calibration of the framework — that is, the values "
            "shipped with the simulator's configuration file. To reproduce, "
            "open the simulator and leave every input untouched.",
            styles["body"]))
        return elements

    overlay: Dict[str, Any] = {}
    for path, value in overrides.items():
        parts = path.split(".")
        cur = overlay
        for key in parts[:-1]:
            cur = cur.setdefault(key, {})
        cur[parts[-1]] = value
    text = yaml.safe_dump(overlay, sort_keys=False, allow_unicode=True)

    elements.append(Paragraph(
        "<b>How to reproduce this scenario.</b> Copy the YAML below into a "
        "file (any name, e.g. <i>my_scenario.yaml</i>). In the simulator's "
        "left sidebar, open the <b>💾 Scenario YAML</b> section and use "
        "<b>📤 Upload scenario YAML</b> to load the file. Every parameter "
        "you changed when you built this report will be re-applied; all "
        "tabs and figures will then reflect this exact scenario.",
        styles["body"]))
    elements.append(Spacer(1, 4 * mm))
    # YAML in a code-styled paragraph (line by line for clean wrap)
    for line in text.splitlines():
        elements.append(Paragraph(
            line.replace(" ", "&nbsp;").replace("<", "&lt;").replace(">", "&gt;"),
            styles["code"]))
    return elements


# ----------------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------------

def generate_pdf_report(*,
                          parameters: Dict[str, Any],
                          overrides: Dict[str, Any],
                          country_label: str,
                          summary_metrics: Dict[str, str]) -> bytes:
    """Build the PDF and return its bytes for st.download_button()."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="Cost Gradient of the Build — Scenario Report",
        author="The Cost Gradient of the Build simulator",
    )
    styles = _build_styles()

    story: List = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.extend(_cover_page(styles,
                                country_label=country_label,
                                override_count=len(overrides),
                                timestamp=timestamp))
    story.extend(_executive_summary(styles,
                                       summary_metrics=summary_metrics))
    story.extend(_parameter_tables(styles,
                                      parameters=parameters,
                                      overrides=overrides))
    story.extend(_figures_section(styles))
    story.extend(_appendix_yaml(styles, overrides=overrides))

    # Header / footer with page numbers
    def _on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawString(1.8 * cm, 1 * cm,
                            "The Cost Gradient of the Build — Scenario Report")
        canvas.drawRightString(A4[0] - 1.8 * cm, 1 * cm,
                                 f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()
