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

Scope of this Sprint 2-B
------------------------
This module ships as a SKELETON: the citation table is final, the
``Provenance`` enum and ``LabeledValue`` dataclass are final, the
``generate_report`` API is locked, and the consistency-checker
scaffold is in place. The body of each audience template is
intentionally short — the substantive prose templates land in
Sprint 5 once the V0_dualchannel reconciliation record (Sprint 2-A,
this same commit) is wired into the Streamlit run-result object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


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
        body = _render_investor(figures, foreground)
    elif audience is Audience.FOUNDER:
        title = "Operational read-out — founder view"
        body = _render_founder(figures, foreground)
    elif audience is Audience.POLICY:
        title = "Policy brief — stewardship view"
        body = _render_policy(figures, foreground)
    else:  # researcher
        title = "Technical record — researcher view"
        body = _render_researcher(figures, foreground)

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
    """
    figures: Dict[str, Any] = {}
    paths = run_result.get("paths", {})
    for key in ("v0_classical", "v0_layered_A", "v0_twophase_B", "v0_dualchannel"):
        if key in paths:
            figures[key] = paths[key]
            citations_used.append("damodaran_2026")
    if "funding_stage" in run_result:
        figures["funding_stage"] = run_result["funding_stage"]
        citations_used.append("carta_q3_2025")
    if "numerator_channel_effect" in run_result:
        figures["numerator_channel_effect"] = run_result["numerator_channel_effect"]
    return figures


# Each audience renderer is intentionally short in this skeleton.
# Sprint 5 expands them. They all read the SAME `figures` dict so
# acceptance check 8.2 (mutual consistency) is enforced by construction.

def _render_investor(figures: Dict[str, Any], foreground: str) -> str:
    return (
        f"*Foreground:* {foreground}\n\n"
        f"## Reconciled valuations\n\n"
        f"{_figures_table(figures)}\n\n"
        "(Bands and funding-stage placement land in Sprint 5.)"
    )


def _render_founder(figures: Dict[str, Any], foreground: str) -> str:
    return (
        f"*Foreground:* {foreground}\n\n"
        f"## Where the value sits\n\n"
        f"{_figures_table(figures)}\n\n"
        "(Cost-gradient breakdown and second-valley reserve land in Sprint 5.)"
    )


def _render_policy(figures: Dict[str, Any], foreground: str) -> str:
    return (
        f"*Foreground:* {foreground}\n\n"
        f"## Reconciled valuations (for context only)\n\n"
        f"{_figures_table(figures)}\n\n"
        "(K7 regime and stewardship language land in Sprint 5.)"
    )


def _render_researcher(figures: Dict[str, Any], foreground: str) -> str:
    return (
        f"*Foreground:* {foreground}\n\n"
        f"## Full reconciliation record\n\n"
        f"{_figures_table(figures)}\n\n"
        "(Equation traces, assumption ledger, and limits ledger land in Sprint 5.)"
    )


def _figures_table(figures: Dict[str, Any]) -> str:
    """Render `figures` as a small markdown table. Same renderer across
    all four audiences guarantees identical shared numbers."""
    if not figures:
        return "_(no figures available)_"
    rows = ["| Key | Value |", "|---|---|"]
    for k, v in figures.items():
        rows.append(f"| {k} | {v} |")
    return "\n".join(rows)
