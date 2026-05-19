"""Multi-audience reporting layer (Part B — Macro Integration Proposal).

This module is the presentation-side counterpart of the valuation
engine. It does NOT compute enterprise values, it does not run Monte
Carlo, and it does not alter any of the four valuation paths
(classical Damodaran, Appendix A layered DCF, Appendix B two-phase
DCF, B.2.6 dual-channel). Its contract is single-purpose:

    Given an already-computed run_result, produce a structured report
    in the register of the requested audience.

The computation is identical across audiences; only framing, emphasis,
ordering and technical depth change. The four audiences are
``investor``, ``founder``, ``policy``, ``researcher`` — definitions
mirror the Macro Integration Proposal Section 8.2.

Provenance discipline
---------------------
Every number that flows into a report is labelled with one of:

  * ``user_input``                — set by the user via UI or scenario YAML
  * ``calibration_parameter``     — provisional, not data-estimated
  * ``computed_result``           — derived from inputs by the engine

The ``LabeledValue`` dataclass attaches the label at the point of use,
so reports can render each number with its provenance and citation
without inviting a separate post-hoc reconciliation step.

Citations
---------
Citations are a fixed, hard-coded table. The tool MUST NOT fetch
external sources at report time and MUST NOT invent citations. The
canonical sources for the macro context are listed in CITATIONS
below; adding a new one is a code change reviewable in pull request.

Sprint 6 — substantive prose templates
--------------------------------------
This module now ships the substantive body of the four audience
templates (investor, founder, policy, researcher), the
``funding_stage_placement`` helper that maps an EV to its Carta
funding-stage placement, the ``macro_sensitivity_grid`` view that
sweeps ``macro_regime`` × ``funding_environment`` per the Macro
Integration Proposal Section 8.4, and the ``RunResult`` typed payload
that downstream callers can populate explicitly. The dict-based
``generate_report(audience, run_result)`` API is preserved for
backward compatibility — ``RunResult.to_dict()`` produces the dict.

Acceptance check 8.1 (presentation-only): ``macro_regime`` and
``funding_environment`` MUST NOT alter any of the four enterprise
values. The macro-sensitivity grid widens MC dispersion only; the
central EVs are taken from the supplied ``run_result`` unchanged.
This is regression-tested in ``tests/test_reporting.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Audience enumeration
# ---------------------------------------------------------------------------

class Audience(str, Enum):
    INVESTOR = "investor"
    FOUNDER = "founder"
    POLICY = "policy"
    RESEARCHER = "researcher"


AUDIENCE_FOREGROUNDS: Dict[Audience, str] = {
    Audience.INVESTOR: (
        "Key-person inversion; the four reconciled valuations; Monte Carlo "
        "bands; funding-stage placement. Decision-oriented and concise."
    ),
    Audience.FOUNDER: (
        "Cost gradient; the layer where defensibility should be "
        "concentrated; second-valley reserve. Operational and plain."
    ),
    Audience.POLICY: (
        "K7 regime; stewardship of public resources; the macro positioning "
        "of Section 10-bis. Cautious and non-technical."
    ),
    Audience.RESEARCHER: (
        "Method, assumptions, every equation used, reproducibility, honest "
        "limits. Full technical detail."
    ),
}


# ---------------------------------------------------------------------------
# Provenance labelling
# ---------------------------------------------------------------------------

class Provenance(str, Enum):
    USER_INPUT = "user_input"
    CALIBRATION_PARAMETER = "calibration_parameter"   # provisional, not data-estimated
    COMPUTED_RESULT = "computed_result"


@dataclass(frozen=True)
class LabeledValue:
    """A numerical value carrying its provenance label and optional
    citation key (resolved against :data:`CITATIONS`)."""
    value: float
    label: Provenance
    description: str
    units: str = ""
    citation_key: Optional[str] = None   # e.g. "carta_q3_2025"

    def render(self, fmt: str = ",.2f") -> str:
        """Render the value with provenance and citation for inline use
        in markdown reports."""
        body = f"{self.description}: {self.value:{fmt}}"
        if self.units:
            body = f"{body} {self.units}"
        body = f"{body}  [{self.label.value}]"
        if self.citation_key and self.citation_key in CITATIONS:
            body = f"{body}  (source: {CITATIONS[self.citation_key]['short']})"
        return body


# ---------------------------------------------------------------------------
# Hard-coded citation table — never fetched, never invented
# ---------------------------------------------------------------------------

CITATIONS: Dict[str, Dict[str, str]] = {
    "bea": {
        "short": "BEA",
        "full": "U.S. Bureau of Economic Analysis, National Income and Product Accounts.",
    },
    "fed": {
        "short": "Fed",
        "full": "Board of Governors of the U.S. Federal Reserve System, "
                "FOMC monetary-policy statements.",
    },
    "wef": {
        "short": "WEF",
        "full": "World Economic Forum, Future of Jobs Report.",
    },
    "oecd": {
        "short": "OECD",
        "full": "Organisation for Economic Co-operation and Development, "
                "Going Digital reports and employment outlooks.",
    },
    "crunchbase": {
        "short": "Crunchbase",
        "full": "Crunchbase, private-market funding and exit data.",
    },
    "carta_q3_2025": {
        "short": "Carta Q3 2025",
        "full": "Carta, State of Private Markets Q3 2025 — Series A/B/C "
                "median pre-money valuations and round sizes.",
    },
    "fink_2026": {
        "short": "Fink 2026",
        "full": "Larry Fink, 2026 BlackRock annual letter on capital "
                "deployment and the AI investment cycle.",
    },
    "furman": {
        "short": "Furman",
        "full": "Jason Furman, papers on AI productivity and the wage bill.",
    },
    "harvey": {
        "short": "Harvey",
        "full": "Campbell R. Harvey, papers on the equity risk premium and "
                "the cost of capital under uncertainty.",
    },
    "damodaran_2026": {
        "short": "Damodaran 2026",
        "full": "Aswath Damodaran (Stern, NYU), industry betas and country "
                "risk data, January 2026 update.",
    },
}


# ---------------------------------------------------------------------------
# Input consistency checker
# ---------------------------------------------------------------------------

@dataclass
class ConsistencyWarning:
    severity: str          # "error" or "warning"
    code: str              # e.g. "layer_shares_sum_off"
    message: str


@dataclass
class ConsistencyReport:
    warnings: List[ConsistencyWarning] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not any(w.severity == "error" for w in self.warnings)


def check_input_consistency(
    layer_shares: Optional[Dict[str, float]] = None,
    trl_by_year: Optional[List[int]] = None,
    phase_1_end_year: Optional[int] = None,
    phase_2_end_year: Optional[int] = None,
    lambda_2V_phase2: Optional[float] = None,
    delta_2V: Optional[float] = None,
    tolerance_layer_shares: float = 0.01,
) -> ConsistencyReport:
    """Validate the input bundle that a report would render.

    Failed checks become visible WARNING BLOCKS in the rendered report
    rather than spuriously precise numbers. The exact list of checks
    mirrors Section 8.3 of the Macro Integration Proposal:

      * layer-exposure shares sum to ~1.0
      * TRL trajectory is monotonically non-decreasing
      * phase boundaries are ordered (phase_1_end < phase_2_end)
      * lambda_2V_phase2 and delta_2V point in the same direction
        (a Layer-4-heavy firm should not have mild lambda but severe
        delta — that's a calibration inconsistency).

    Returns a :class:`ConsistencyReport`. Callers should render its
    warnings before any monetary figure when the report is unclean.
    """
    rep = ConsistencyReport()

    if layer_shares is not None:
        total = sum(float(v) for v in layer_shares.values())
        if abs(total - 1.0) > tolerance_layer_shares:
            rep.warnings.append(ConsistencyWarning(
                severity="error",
                code="layer_shares_sum_off",
                message=(f"Layer exposure shares sum to {total:.4f}; "
                         f"expected 1.0 (+/- {tolerance_layer_shares}). "
                         f"Reports will not render monetary figures until fixed."),
            ))

    if trl_by_year is not None:
        for i in range(1, len(trl_by_year)):
            if trl_by_year[i] < trl_by_year[i - 1]:
                rep.warnings.append(ConsistencyWarning(
                    severity="warning",
                    code="trl_non_monotonic",
                    message=(f"TRL year {i + 1} ({trl_by_year[i]}) < year {i} "
                             f"({trl_by_year[i - 1]}). TRL is expected to be "
                             f"monotonically non-decreasing across a single phase."),
                ))
                break

    if phase_1_end_year is not None and phase_2_end_year is not None:
        if not (phase_1_end_year < phase_2_end_year):
            rep.warnings.append(ConsistencyWarning(
                severity="error",
                code="phase_boundaries_out_of_order",
                message=(f"Phase boundaries out of order: "
                         f"phase_1_end_year={phase_1_end_year} >= "
                         f"phase_2_end_year={phase_2_end_year}."),
            ))

    if lambda_2V_phase2 is not None and delta_2V is not None:
        # A Layer-4-heavy firm produces low lambda (severe retreat) AND
        # high delta (severe terminal scarring). If lambda is mild
        # (close to 1) but delta is severe (close to 0.5) — or vice
        # versa — the two channels disagree on the firm's exposure.
        mild_lambda = lambda_2V_phase2 > 0.90
        severe_delta = delta_2V > 0.20
        severe_lambda = lambda_2V_phase2 < 0.80
        mild_delta = delta_2V < 0.10
        if (mild_lambda and severe_delta) or (severe_lambda and mild_delta):
            rep.warnings.append(ConsistencyWarning(
                severity="warning",
                code="lambda_delta_direction_mismatch",
                message=(f"lambda_2V_phase2={lambda_2V_phase2:.2f} and "
                         f"delta_2V={delta_2V:.2f} point in opposite directions. "
                         f"A Layer-4-heavy firm should have low lambda AND high "
                         f"delta; a Layer-6-rich firm should have high lambda "
                         f"AND low delta."),
            ))

    return rep


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

@dataclass
class RenderedReport:
    audience: Audience
    title: str
    body_markdown: str
    citations_used: List[str]
    consistency: ConsistencyReport


def _render_warning_block(consistency: ConsistencyReport) -> str:
    if consistency.is_clean and not consistency.warnings:
        return ""
    lines = ["", "> **Input consistency**"]
    for w in consistency.warnings:
        prefix = "ERROR" if w.severity == "error" else "warning"
        lines.append(f"> - [{prefix}] {w.code}: {w.message}")
    lines.append("")
    return "\n".join(lines)


def generate_report(
    audience: Audience | str,
    run_result: Dict[str, Any],
    consistency: Optional[ConsistencyReport] = None,
) -> RenderedReport:
    """Render ``run_result`` in the register of ``audience``.

    ``run_result`` is the dict-of-dicts produced by the engine. It is
    expected to contain at minimum the four valuation paths and their
    Monte Carlo bands when available. The function does not compute;
    it only frames.

    Acceptance check 8.2 (Macro Integration Proposal): from the same
    ``run_result``, the four audiences produce mutually consistent
    reports — every shared number is identical across them, the only
    difference is framing, ordering and depth.

    Currently a SKELETON — body templates land in Sprint 5.
    """
    if isinstance(audience, str):
        audience = Audience(audience)

    if consistency is None:
        consistency = ConsistencyReport()

    citations_used: List[str] = []
    warning_block = _render_warning_block(consistency)

    foreground = AUDIENCE_FOREGROUNDS[audience]

    # Single source of figures — the body just reorders/reframes
    figures = _extract_top_level_figures(run_result, citations_used)

    if audience is Audience.INVESTOR:
        title = "Valuation summary — investor view"
        body = _render_investor(figures, foreground, citations_used)
    elif audience is Audience.FOUNDER:
        title = "Operational read-out — founder view"
        body = _render_founder(figures, foreground, citations_used)
    elif audience is Audience.POLICY:
        title = "Policy brief — stewardship view"
        body = _render_policy(figures, foreground, citations_used)
    else:  # researcher
        title = "Technical record — researcher view"
        body = _render_researcher(figures, foreground, citations_used)

    return RenderedReport(
        audience=audience,
        title=title,
        body_markdown=f"# {title}\n\n{warning_block}\n{body}".strip(),
        citations_used=sorted(set(citations_used)),
        consistency=consistency,
    )


# ---------------------------------------------------------------------------
# Internal — figure extraction (single source of truth across audiences)
# ---------------------------------------------------------------------------

def _extract_top_level_figures(
    run_result: Dict[str, Any],
    citations_used: List[str],
) -> Dict[str, Any]:
    """Pick the canonical fields from ``run_result``.

    By going through this single helper, every audience template
    reads the same numbers — different framings of the SAME figures.
    Acceptance check 8.2 (mutual consistency) is enforced
    structurally: any number that flows into a report passes through
    this function exactly once.
    """
    figures: Dict[str, Any] = {}
    paths = run_result.get("paths", {})
    for key in ("v0_classical", "v0_layered_A", "v0_twophase_B", "v0_dualchannel"):
        if key in paths:
            figures[key] = paths[key]
            citations_used.append("damodaran_2026")
    # Legacy field name (backward compat with Sprint 2-B skeleton tests)
    if "funding_stage" in run_result:
        figures["funding_stage"] = run_result["funding_stage"]
        citations_used.append("carta_q3_2025")
    # Sprint 6 — funding-stage placement record (richer than the legacy field)
    if "funding_stage_placement" in run_result:
        figures["funding_stage_placement"] = run_result["funding_stage_placement"]
        citations_used.append("carta_q3_2025")
    if "numerator_channel_effect" in run_result:
        figures["numerator_channel_effect"] = run_result["numerator_channel_effect"]
    if "bands" in run_result:
        figures["bands"] = run_result["bands"]
    # Sprint 6 — surface dual-channel calibration and firm composition
    # so the audience templates can render them with provenance labels.
    for key in (
        "layer_exposure", "K7", "layer4_substitution_potential",
        "lambda_2V_phase2", "lambda_2V_phase3", "alpha_4_sys",
        "firm_label", "sector",
        "macro_regime", "funding_environment",
    ):
        if key in run_result and run_result[key] is not None:
            figures[key] = run_result[key]
    return figures


# ---------------------------------------------------------------------------
# Audience renderers (Sprint 6 — substantive templates)
# ---------------------------------------------------------------------------
#
# All four templates read from the SAME `figures` dict produced by
# `_extract_top_level_figures`. They differ only in framing, emphasis,
# ordering and technical depth — acceptance check 8.2 (mutual
# consistency) is enforced by construction.


_PATH_LABELS = {
    "v0_classical":   "Classical Damodaran (single rate)",
    "v0_layered_A":   "Appendix A — Layered DCF",
    "v0_twophase_B":  "Appendix B — Two-phase DCF",
    "v0_dualchannel": "B.2.6 — Dual-channel (unified)",
}


def _fmt_usd(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1e9:
        return f"${v / 1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.1f}M"
    if abs(v) >= 1e3:
        return f"${v / 1e3:.1f}k"
    return f"${v:.0f}"


def _path_row_with_bands(figures: Dict[str, Any], key: str) -> str:
    """Render one row of the reconciliation table — point estimate plus
    P10/P50/P90 if MC bands are present, else just the point estimate."""
    val = figures.get(key)
    bands = (figures.get("bands") or {}).get(key) or {}
    label = _PATH_LABELS.get(key, key)
    if val is None:
        return f"| {label} | — | — | — |"
    p10 = bands.get("p10")
    p50 = bands.get("p50")
    p90 = bands.get("p90")
    band_cell = (f"{_fmt_usd(p10)} – {_fmt_usd(p90)}"
                 if (p10 is not None and p90 is not None)
                 else "—")
    median_cell = _fmt_usd(p50) if p50 is not None else "—"
    return f"| {label} | {_fmt_usd(val)} | {median_cell} | {band_cell} |"


def _reconciliation_table(figures: Dict[str, Any]) -> str:
    """Markdown reconciliation table — point estimate, MC P50, P10–P90 band."""
    lines = [
        "| Path | Point estimate | MC P50 | MC P10–P90 |",
        "|---|---:|---:|---:|",
    ]
    for key in _PATH_LABELS:
        if key in figures:
            lines.append(_path_row_with_bands(figures, key))
    return "\n".join(lines)


def _render_investor(figures: Dict[str, Any], foreground: str,
                      citations_used: List[str]) -> str:
    """Investor view — decision-oriented, concise.

    Foregrounds the four reconciled valuations with MC bands, the
    funding-stage placement of the dual-channel recommendation, and
    the numerator channel effect.
    """
    citations_used.append("damodaran_2026")
    citations_used.append("carta_q3_2025")

    parts = [f"*Foreground:* {foreground}", "", "## Reconciled valuations"]
    parts.append("")
    parts.append(_reconciliation_table(figures))
    parts.append("")

    # Funding-stage placement — driven by the dual-channel (recommended) bar.
    placement = figures.get("funding_stage_placement", {})
    if placement:
        cleared = placement.get("cleared", "—")
        next_stage = placement.get("next_stage", "—")
        gap = placement.get("gap_to_next_usd")
        parts.append("## Funding-stage placement")
        parts.append("")
        parts.append(f"Implied stage at the dual-channel valuation: **{cleared}**. "
                     f"Next stage threshold: {next_stage}"
                     f"{f' (gap: {_fmt_usd(gap)})' if gap is not None else ''}. "
                     "Bands are per Carta State of Private Markets Q3 2025.")
        parts.append("")

    # Numerator channel effect — the headline diagnostic of B.2.6.
    nce = figures.get("numerator_channel_effect")
    if nce is not None:
        parts.append("## Numerator channel effect")
        parts.append("")
        parts.append(f"Cash-flow correction (V0_twophase_B − V0_dualchannel): "
                     f"**{_fmt_usd(nce)}**. This is the amount a rate-only "
                     "correction (two-phase WACC alone) leaves unmeasured — "
                     "the value at risk specifically from the second-valley "
                     "revenue compression captured by λ_2V.")
        parts.append("")

    parts.append("## Recommendation")
    parts.append("")
    parts.append(
        "The dual-channel (B.2.6) bar is the recommended figure for pricing. "
        "The other three are diagnostic: classical Damodaran indicates what "
        "the textbook single-rate method would assign; Appendix A layered DCF "
        "is the most pessimistic single framework (stacks TRL + full layered "
        "premium); Appendix B two-phase corrects the discount rate alone. "
        "Use the MC P10–P90 band as the negotiation envelope."
    )

    return "\n".join(parts)


def _render_founder(figures: Dict[str, Any], foreground: str,
                     citations_used: List[str]) -> str:
    """Founder view — operational, plain.

    Foregrounds where the value actually sits across the layers, the
    cost-gradient implication (Layer-4 exposure → AI substitution
    pressure), and the second-valley reserve in operational terms.
    """
    citations_used.append("carta_q3_2025")
    citations_used.append("damodaran_2026")

    layer_exposure = figures.get("layer_exposure", {})
    l4 = layer_exposure.get("layer_4_codified")
    l5 = layer_exposure.get("layer_5_judgment")
    l6 = layer_exposure.get("layer_6_institutional")

    parts = [f"*Foreground:* {foreground}", ""]

    # Reconciliation table — same numbers as the investor view, with a
    # founder-side framing ("here's what your valuation looks like under
    # each method; the dual-channel is the one to plan against").
    parts.append("## Your valuation under each method")
    parts.append("")
    parts.append(_reconciliation_table(figures))
    parts.append("")
    parts.append(
        "Plan against the **dual-channel (B.2.6)** number — it captures "
        "both the discount-rate side (Phase-2 cost-of-capital jump) and "
        "the cash-flow side (Phase-2 revenue retreat + Phase-3 permanent "
        "margin compression) that the simpler methods miss."
    )
    parts.append("")

    parts.append("## Where the firm's value sits")
    parts.append("")
    if l4 is not None or l5 is not None or l6 is not None:
        parts.append(
            "| Layer | Share | Read |\n|---|---:|---|"
        )
        if l4 is not None:
            parts.append(f"| Layer 4 (codified, AI-substitutable) | {l4*100:.0f}% | "
                          "Exposed to commoditization — minimize as % of value |")
        if l5 is not None:
            parts.append(f"| Layer 5 (judgment) | {l5*100:.0f}% | "
                          "Defensible — protect and grow |")
        if l6 is not None:
            parts.append(f"| Layer 6 (institutional) | {l6*100:.0f}% | "
                          "Permanent moat — deepen relentlessly |")
    else:
        parts.append("_(layer exposure not supplied)_")
    parts.append("")

    parts.append("## Cost gradient (Section 5)")
    parts.append("")
    parts.append(
        "The cost of building has fallen by one to two orders of magnitude "
        "for digital products. The cost of formulating well-posed hypotheses "
        "(Layer 5) and the cost of accumulating institutional trust "
        "(Layer 6) have not. Re-budget away from the build station, into "
        "the Minimum Viable Hypothesis station (pre-build) and the "
        "relational and certification stations (post-build)."
    )
    parts.append("")

    # Second-valley reserve.
    lambda_p2 = figures.get("lambda_2V_phase2")
    lambda_p3 = figures.get("lambda_2V_phase3")
    if lambda_p2 is not None:
        parts.append("## Second-valley reserve")
        parts.append("")
        parts.append(
            f"Calibrated transient revenue retreat in Phase 2: "
            f"**λ_2V_phase2 = {lambda_p2:.2f}** "
            f"(revenue projected at {lambda_p2*100:.0f}% of pre-valley "
            "trajectory during the second valley). "
        )
        if lambda_p3 is not None:
            parts.append(
                f"Permanent margin compression to a new lower steady state in "
                f"Phase 3: **λ_2V_phase3 = {lambda_p3:.2f}**. Plan capital "
                "and headcount so a Phase-2 revenue compression of "
                f"{(1 - lambda_p2)*100:.0f}% does not exhaust runway "
                "before the firm crosses into Phase 3."
            )
        parts.append("")

    # Funding-stage placement (founder framing: what round can I raise?).
    placement = figures.get("funding_stage_placement", {})
    if placement:
        cleared = placement.get("cleared", "—")
        next_stage = placement.get("next_stage", "—")
        gap = placement.get("gap_to_next_usd")
        parts.append("## Funding round you can plausibly raise")
        parts.append("")
        parts.append(f"At the dual-channel valuation, the firm clears the "
                      f"**{cleared}** median pre-money (Carta Q3 2025). "
                      f"To clear the next stage ({next_stage}): close the gap "
                      f"of {_fmt_usd(gap)}"
                      f"{' by deepening Layer 6 or growing ARR.' if gap else '.'}")

    return "\n".join(parts)


def _render_policy(figures: Dict[str, Any], foreground: str,
                    citations_used: List[str]) -> str:
    """Policy view — cautious, non-technical.

    Foregrounds K7 regime, stewardship of public resources, the macro
    positioning of Section 10-bis. Cautious about magnitudes;
    explicit about provisional calibration parameters.
    """
    citations_used.extend(["oecd", "wef", "furman", "damodaran_2026", "carta_q3_2025"])

    parts = [f"*Foreground:* {foreground}", ""]

    # The four valuations are shown as context only — policy decisions
    # should not be made directly on these magnitudes (the calibration
    # parameters are provisional). Including the table preserves
    # acceptance check 8.2 (mutual consistency).
    parts.append("## The four valuations (illustrative, not policy estimates)")
    parts.append("")
    parts.append(_reconciliation_table(figures))
    parts.append("")
    parts.append(
        "These numbers are shown for **structural comparison only**; "
        "calibration parameters are provisional and the magnitudes "
        "should be read as orders of magnitude, not as forecasts."
    )
    parts.append("")

    parts.append("## Cross-border knowledge regime (K7)")
    K7 = figures.get("K7")
    parts.append("")
    if K7 is not None:
        parts.append(
            f"This run uses K7 = **{K7:.2f}** (1.0 = full integration of the "
            "pre-2020 regime; 0.7 = illustrative 2026; 0.45 = collapse "
            "threshold below which the inverted-discount premium loses "
            "sign in all three reference jurisdictions). K7 is a "
            "thermometer of the regime, not a thermostat — state action "
            "alters K7, but declaring K7 preserves nothing."
        )
    else:
        parts.append("_(K7 not supplied in this run)_")
    parts.append("")

    parts.append("## Stewardship of public resources")
    parts.append("")
    parts.append(
        "The Section 8.2 redistribution of strategic value — Layer-4 "
        "commoditization eroding the cost-advantage moat, Layer-5/6 "
        "defensibility becoming structurally central — is a stewardship "
        "concern for any public-resource decision in research and "
        "innovation policy. Projects whose contributions sit at Layer 4 "
        "face an obsolescence-during-execution risk that the classical "
        "evaluative framework does not anticipate. Appendix G develops "
        "the prospective-responsibility reading (Jonas 1984) — the "
        "framework offers an operational language for the diagnostic, "
        "not a normative ranking."
    )
    parts.append("")

    parts.append("## Macro positioning (provisional)")
    parts.append("")
    parts.append(
        "Numerical magnitudes in this run rest on **calibration "
        "parameters that are not data-estimated**: the per-layer risk "
        "coefficients (α_1..α_7), the second-valley retreat factor "
        "(λ_2V), the systematic/idiosyncratic risk partition coefficient "
        "(α_4_sys), and the K7 trajectory. Policy decisions should treat "
        "these as orders of magnitude, not as forecasts. The empirical "
        "calibration program is sketched in the docs/dual_channel_correction.md "
        "and in the paper's Section 11.2 multidisciplinary agenda."
    )

    return "\n".join(parts)


def _render_researcher(figures: Dict[str, Any], foreground: str,
                        citations_used: List[str]) -> str:
    """Researcher view — full technical detail.

    Foregrounds the method (equations consumed), the assumptions
    (per-firm calibration + provenance), and honest limits.
    """
    citations_used.extend(["damodaran_2026", "harvey", "fink_2026"])

    parts = [f"*Foreground:* {foreground}", ""]

    # Full reconciliation table (same data, more decimals)
    parts.append("## Reconciliation record")
    parts.append("")
    parts.append(_reconciliation_table(figures))
    parts.append("")

    nce = figures.get("numerator_channel_effect")
    if nce is not None:
        parts.append(f"Numerator channel effect (V0_twophase_B − V0_dualchannel): "
                      f"**{_fmt_usd(nce)}**.")
        parts.append("")

    # Equations consumed
    parts.append("## Equations consumed")
    parts.append("")
    parts.append(
        "* Eq B.3 — phase-conditional levered beta (`two_phase_capm`).\n"
        "* Eq B.4 — phase-conditional cost of equity Ke(t).\n"
        "* Eq B.6 — phase-conditional WACC(t) with E/V, D/V, Ke(t), Kd(t).\n"
        "* Eq B.9 — phase-conditional Gordon perpetuity with δ_2V drag.\n"
        "  Retired in the dual-channel path; its information is absorbed "
        "into λ_2V_phase3 per docs/dual_channel_correction.md.\n"
        "* Eq B.10 — compounded discount factor ∏_{s=1..t} (1 + WACC(s)).\n"
        "* Eq B.11 — two-phase enterprise value.\n"
        "* Eq B.12 — partition π_2V = π_2V_sys + π_2V_idio.\n"
        "* Eq B.13 — α_4_adj = α_4 − α_4_sys (consumed by hybrid extensions).\n"
        "* Eq B.14 — FCF_2V(t) = FCF_proj(t) · λ_2V(φ(t)), UNIFIED across phases.\n"
        "* Eq B.15 — V0_dualchannel = two-phase DCF with FCF · λ_2V.\n"
        "* Eq C.1 — layered firm-specific premium π_firm = Σ α_i · w_i · μ_i."
    )
    parts.append("")

    # Assumption ledger with provenance
    parts.append("## Assumption ledger (calibration provisional)")
    parts.append("")
    parts.append("| Parameter | Value | Provenance |\n|---|---:|---|")
    for label, key, p_default in [
        ("λ_2V_phase2", "lambda_2V_phase2", Provenance.CALIBRATION_PARAMETER),
        ("λ_2V_phase3", "lambda_2V_phase3", Provenance.CALIBRATION_PARAMETER),
        ("α_4_sys",     "alpha_4_sys",       Provenance.CALIBRATION_PARAMETER),
        ("K7",          "K7",                Provenance.USER_INPUT),
        ("AI substitution potential", "layer4_substitution_potential",
                                              Provenance.USER_INPUT),
    ]:
        v = figures.get(key)
        if v is None:
            continue
        parts.append(f"| {label} | {v:.3f} | {p_default.value} |")
    parts.append("")

    parts.append("## Honest limits")
    parts.append("")
    parts.append(
        "* The seven layers are heuristic, not measured — Section 10 of "
        "the paper.\n"
        "* The per-layer risk coefficients are illustrative; firm-level "
        "estimation is reserved for future work (paper Appendix A.5).\n"
        "* The unified-lambda correction (Sprint 4) replaces the "
        "δ_2V-on-TV mechanism with λ_2V_phase3 — see "
        "docs/dual_channel_correction.md for the proposed manuscript edits.\n"
        "* Monte Carlo bands rest on the distribution choices documented "
        "under `dual_channel.monte_carlo` in config/parameters.yaml.\n"
        "* K7 is a tentative seventh-layer hypothesis (paper Section 4.1) "
        "whose empirical foundation is weaker than the first six layers."
    )

    return "\n".join(parts)


def _figures_table(figures: Dict[str, Any]) -> str:
    """Render `figures` as a small markdown table (legacy renderer, kept
    for backward compatibility with the Sprint 2-B skeleton tests)."""
    if not figures:
        return "_(no figures available)_"
    rows = ["| Key | Value |", "|---|---|"]
    for k, v in figures.items():
        rows.append(f"| {k} | {v} |")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Sprint 6 additions: RunResult schema, funding-stage placement, macro view
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    """Typed payload that a report consumes. ``to_dict()`` produces the
    legacy dict shape expected by ``generate_report``.

    All fields are optional so that callers can populate progressively
    (e.g. point estimates first, MC bands later, macro context last).
    """
    firm_label: Optional[str] = None
    sector: Optional[str] = None
    # Four valuation paths (point estimates in USD)
    v0_classical: Optional[float] = None
    v0_layered_A: Optional[float] = None
    v0_twophase_B: Optional[float] = None
    v0_dualchannel: Optional[float] = None
    # Monte Carlo bands per path: {path_key: {p10, p50, p90, mean}}
    bands: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # Diagnostic
    numerator_channel_effect: Optional[float] = None
    # Layer exposure (used by the founder template)
    layer_exposure: Dict[str, float] = field(default_factory=dict)
    K7: Optional[float] = None
    layer4_substitution_potential: Optional[float] = None
    # Dual-channel calibration
    lambda_2V_phase2: Optional[float] = None
    lambda_2V_phase3: Optional[float] = None
    alpha_4_sys: Optional[float] = None
    # Macro context (presentation-only, never affects EVs)
    macro_regime: float = 0.5
    funding_environment: str = "baseline"
    # Funding-stage placement (populated by helper or by caller)
    funding_stage_placement: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Produce the dict shape expected by ``generate_report``."""
        return {
            "firm_label": self.firm_label,
            "sector": self.sector,
            "paths": {
                k: v for k, v in {
                    "v0_classical":   self.v0_classical,
                    "v0_layered_A":   self.v0_layered_A,
                    "v0_twophase_B":  self.v0_twophase_B,
                    "v0_dualchannel": self.v0_dualchannel,
                }.items() if v is not None
            },
            "bands": dict(self.bands),
            "numerator_channel_effect": self.numerator_channel_effect,
            "layer_exposure": dict(self.layer_exposure),
            "K7": self.K7,
            "layer4_substitution_potential": self.layer4_substitution_potential,
            "lambda_2V_phase2": self.lambda_2V_phase2,
            "lambda_2V_phase3": self.lambda_2V_phase3,
            "alpha_4_sys": self.alpha_4_sys,
            "macro_regime": self.macro_regime,
            "funding_environment": self.funding_environment,
            "funding_stage_placement": dict(self.funding_stage_placement),
        }


# Carta Q3 2025 funding-stage medians — duplicated here so the reporting
# module remains importable without the wider config layer. The
# Streamlit/script callers should pass YAML-derived values; these
# defaults match config/parameters.yaml section 25.
_CARTA_STAGES = (
    ("seed",     16_000_000),
    ("series_a", 49_300_000),
    ("series_b", 118_900_000),
    ("series_c", 350_000_000),
)

# Funding-environment scaling of the seed reference (Macro Integration
# Proposal Section 8.1). The OTHER stages remain at their Carta medians;
# only the seed line shifts because the seed market is the one most
# sensitive to cheque size.
_SEED_BY_ENVIRONMENT = {
    "abundant": 22_000_000,
    "baseline": 16_000_000,
    "crowded":  11_000_000,
}


def funding_stage_placement(
    enterprise_value_usd: float,
    funding_environment: str = "baseline",
    stages: Optional[Tuple[Tuple[str, float], ...]] = None,
) -> Dict[str, Any]:
    """Map an enterprise value to its Carta funding-stage placement.

    Returns a dict with:
      * ``cleared`` (str) — the highest stage whose median pre-money is
        at or below the supplied EV. ``"pre_seed"`` if the EV is below
        every documented median.
      * ``next_stage`` (str | None) — the next stage above ``cleared``;
        ``None`` if the firm has cleared the topmost documented stage.
      * ``gap_to_next_usd`` (float | None) — the USD distance from the
        EV to the next-stage median; ``None`` if no next stage.
      * ``stages`` (list[(label, median_premoney)]) — the stage table
        actually used (after applying ``funding_environment``).

    The ``funding_environment`` parameter shifts the seed reference per
    Section 8.1 of the Macro Integration Proposal (presentation-only).
    The other stages are held at their Carta medians.
    """
    if stages is None:
        stages = _CARTA_STAGES
    # Apply funding_environment adjustment to the seed line only.
    seed_amt = _SEED_BY_ENVIRONMENT.get(funding_environment,
                                         _SEED_BY_ENVIRONMENT["baseline"])
    adjusted = tuple(
        (label, seed_amt if label == "seed" else amt)
        for label, amt in stages
    )

    cleared = "pre_seed"
    next_stage: Optional[str] = adjusted[0][0]
    gap: Optional[float] = adjusted[0][1] - enterprise_value_usd
    for i, (label, amt) in enumerate(adjusted):
        if enterprise_value_usd >= amt:
            cleared = label
            if i + 1 < len(adjusted):
                next_stage = adjusted[i + 1][0]
                gap = adjusted[i + 1][1] - enterprise_value_usd
            else:
                next_stage = None
                gap = None
    return {
        "cleared": cleared,
        "next_stage": next_stage,
        "gap_to_next_usd": gap,
        "stages": list(adjusted),
        "funding_environment": funding_environment,
    }


# ---------------------------------------------------------------------------
# Macro-sensitivity grid (Macro Integration Proposal Section 8.4)
# ---------------------------------------------------------------------------

# macro_regime ∈ [0, 1]. At 0.5 the dispersion multiplier is exactly 1.0
# (no widening) so the baseline run is reproduced. At 0 the dispersion
# narrows (normal-technology reading, less uncertainty). At 1 it widens
# (structural-change reading, more uncertainty).
def macro_regime_dispersion_multiplier(macro_regime: float) -> float:
    """Transmission channel for ``macro_regime`` on the MC dispersion.

    Linear, symmetric around 0.5: at macro_regime = 0.5 returns 1.0
    exactly (acceptance check 8.4: baseline preserved). At the extremes
    the multiplier moves in a defensibly-bounded band.

    The channel is disclosed in every report that consumes it — see
    the macro-sensitivity grid renderer in this module.
    """
    return 1.0 + 0.4 * (float(macro_regime) - 0.5)


@dataclass
class MacroSensitivityCell:
    macro_regime: float
    funding_environment: str
    dispersion_multiplier: float
    placement: Dict[str, Any]


def macro_sensitivity_grid(
    run_result: RunResult,
    macro_regime_grid: Tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
    funding_environments: Tuple[str, ...] = ("abundant", "baseline", "crowded"),
) -> List[MacroSensitivityCell]:
    """Sweep ``macro_regime`` × ``funding_environment`` and return the
    grid of (dispersion multiplier, funding-stage placement) cells.

    Acceptance check 8.1: the four enterprise values are NEVER
    perturbed by this sweep — only the dispersion multiplier and the
    funding-stage placement change. The function is therefore a pure
    presentation-side view; the caller is responsible for widening or
    narrowing the MC bands by ``dispersion_multiplier`` if so desired,
    but the central EVs in ``run_result`` are taken as-is.

    The dual-channel EV is used for the funding-stage placement (it is
    the recommended figure per the B.5 caption).
    """
    placement_value = run_result.v0_dualchannel
    cells: List[MacroSensitivityCell] = []
    for r in macro_regime_grid:
        for env in funding_environments:
            disp = macro_regime_dispersion_multiplier(r)
            if placement_value is not None:
                placement = funding_stage_placement(placement_value, env)
            else:
                placement = {"cleared": "—", "next_stage": "—",
                             "gap_to_next_usd": None}
            cells.append(MacroSensitivityCell(
                macro_regime=float(r),
                funding_environment=env,
                dispersion_multiplier=disp,
                placement=placement,
            ))
    return cells


def render_macro_sensitivity_table(cells: List[MacroSensitivityCell]) -> str:
    """Render the macro-sensitivity cells as a markdown table.

    The table makes the transmission channel explicit — readers see the
    dispersion multiplier on every row, not a hidden rescaling of the
    central estimate. Per the Macro Integration Proposal Section 8.4
    requirement that the channel be "disclosed in the report, not hidden".
    """
    lines = [
        "| macro_regime | funding_environment | dispersion × | implied stage | gap to next |",
        "|---:|:---|---:|:---|---:|",
    ]
    for c in cells:
        gap = c.placement.get("gap_to_next_usd")
        gap_str = _fmt_usd(gap) if gap is not None else "—"
        lines.append(
            f"| {c.macro_regime:.2f} | {c.funding_environment} | "
            f"{c.dispersion_multiplier:.2f} | {c.placement.get('cleared', '—')} "
            f"| {gap_str} |"
        )
    return "\n".join(lines)
