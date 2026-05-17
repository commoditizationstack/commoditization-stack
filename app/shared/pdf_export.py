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
    elements.append(Paragraph(f"<b>Jurisdiction:</b> {country_label}",
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


def _parameter_tables(styles, *, parameters: Dict[str, Any],
                       overrides: Dict[str, Any]) -> List:
    """Build per-section tables of every parameter with override indicator."""
    elements = [Paragraph("Complete parameter table", styles["h1"])]
    elements.append(Paragraph(
        f"Every numeric parameter in the simulation under the current overlay. "
        f"Variables modified by the user are flagged ★. "
        f"Total active overrides: <b>{len(overrides)}</b>. "
        f"💵 Monetary values in USD where applicable.",
        styles["body"]))

    for section in PARAMETER_SECTIONS_TO_INCLUDE:
        if section not in parameters:
            continue
        elements.append(Paragraph(f"§ {section}", styles["h2"]))
        rows = _flatten_params({section: parameters[section]})
        table_data = [["Parameter", "Value", "Modified"]]
        for path, value in rows:
            modified = "★" if path in overrides else ""
            display_value = value if len(value) <= 60 else value[:57] + "..."
            table_data.append([path, display_value, modified])
        # Split into pages of ~30 rows
        chunk_size = 30
        for chunk_start in range(1, len(table_data), chunk_size):
            chunk = [table_data[0]] + table_data[chunk_start:chunk_start + chunk_size]
            tbl = Table(chunk, colWidths=[8.5 * cm, 7 * cm, 1.5 * cm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C5282")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.HexColor("#FAFBFC"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 1), (2, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            elements.append(tbl)
            elements.append(Spacer(1, 4 * mm))
    elements.append(PageBreak())
    return elements


def _figures_section(styles) -> List:
    """All 41 figures, grouped by paper section."""
    elements = [Paragraph("Figures from the framework", styles["h1"])]
    elements.append(Paragraph(
        "All figures generated from the framework, grouped by paper section. "
        "Each figure reflects the active parameter overlay at the moment of "
        "generation. To regenerate any figure under your own scenario, run "
        "<font face='Courier'>python main.py 2</font>.",
        styles["body"]))

    current_section = None
    for section, fname, caption in FIGURE_MANIFEST:
        fp = FIG_DIR / fname
        if not fp.exists():
            continue
        if section != current_section:
            elements.append(Paragraph(section, styles["h2"]))
            current_section = section
        try:
            img = Image(str(fp), width=16 * cm, height=10 * cm, kind="proportional")
            elements.append(KeepTogether([
                img,
                Paragraph(f"<i>{fname}</i> — {caption}", styles["caption"]),
                Spacer(1, 4 * mm),
            ]))
        except Exception as e:
            elements.append(Paragraph(
                f"[Could not embed {fname}: {e}]", styles["body"]))
    elements.append(PageBreak())
    return elements


def _appendix_yaml(styles, *, overrides: Dict[str, Any]) -> List:
    """Scenario YAML appendix for reproducibility."""
    elements = [Paragraph("Appendix — Scenario YAML", styles["h1"])]
    if not overrides:
        elements.append(Paragraph(
            "No overrides were active when this report was generated. "
            "Re-running the simulator with this scenario reproduces the default "
            "behavior of <font face='Courier'>config/parameters.yaml</font>.",
            styles["body"]))
        return elements

    # Build the nested YAML form of the overlay
    overlay: Dict[str, Any] = {}
    for path, value in overrides.items():
        parts = path.split(".")
        cur = overlay
        for key in parts[:-1]:
            cur = cur.setdefault(key, {})
        cur[parts[-1]] = value
    text = yaml.safe_dump(overlay, sort_keys=False, allow_unicode=True)
    elements.append(Paragraph(
        "Save this YAML as <font face='Courier'>scenario.yaml</font> and pass "
        "to <font face='Courier'>load_overrides_from_yaml_bytes()</font> in "
        "<font face='Courier'>app/shared/state.py</font> to reproduce this "
        "scenario in the simulator.",
        styles["body"]))
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
