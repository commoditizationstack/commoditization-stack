"""Migration dynamics under the AI orchestrator framework (Section 7.5).

Models the temporal arc of substituting in-house engineering labor with AI
services, including:
  - Assessment-and-pilot phase pre-T0 (Brynjolfsson, Li & Raymond 2025: ~9 months)
  - Termination cost at T0
  - Dual-operation overhead during transition (T0 to T3)
  - Retention bonus during T1-T2
  - Sigmoidal learning curve T4 to T10 (Cazzaniga et al. IMF 2024)
  - Permanent orchestrator function at steady state (Gartner 2025; McKinsey 2025)

Generates the cumulative cash-flow trajectory plotted in Figures 11, 12, 13
of the paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import config


@dataclass
class MigrationParameters:
    """Inputs for a migration cash-flow simulation.

    Each of the per-jurisdiction and global override fields below is
    optional. When set, it takes precedence over the corresponding
    ``config/parameters.yaml`` value; when ``None``, the YAML default
    applies. This is how the website's Advanced parameters lab lets
    a user probe sensitivity without touching the YAML.
    """
    n_total_engineers: int
    substitution_fraction: float
    jurisdiction: str                    # "brazil", "france", or "united_states"
    # Per-jurisdiction overrides (paper §7.5)
    loaded_swe_cost_usd_year: Optional[float] = None    # per senior engineer
    loaded_mid_cost_usd_year: Optional[float] = None    # per substitutable engineer
    termination_cost_fraction: Optional[float] = None
    orchestrator_floor: int = 1
    horizon_quarters: int = 23           # T-3 to T20 inclusive
    # Global migration-dynamics overrides (paper §7.5 — AI-orchestrator
    # function, transition overhead, retention bonus).
    orchestrator_ratio: Optional[float] = None
    orchestrator_premium_pct: Optional[float] = None
    ai_tooling_cost_per_dev_usd_year: Optional[float] = None
    dual_operation_overhead_quarters: Optional[int] = None
    retention_bonus_quarters: Optional[int] = None
    retention_bonus_fraction: Optional[float] = None


@dataclass
class MigrationResult:
    """Output of a migration cash-flow simulation."""
    quarters: List[int] = field(default_factory=list)            # T-3 to T_horizon
    cumulative_cash_usd: List[float] = field(default_factory=list)
    annual_gross_saving_usd: float = 0.0
    annual_orchestrator_cost_usd: float = 0.0
    annual_net_saving_usd: float = 0.0
    termination_cost_t0_usd: float = 0.0
    break_even_quarter: Optional[float] = None
    cumulative_5y_post_t0_usd: float = 0.0
    n_substitutable: int = 0
    n_retained: int = 0
    n_orchestrators: int = 0


def _md() -> Dict:
    return config.load_parameters()["migration_dynamics"]


def compute_migration(params: MigrationParameters) -> MigrationResult:
    """Compute the migration cash-flow trajectory for a given firm + jurisdiction.

    The cash flow is reported quarter by quarter from T-3 (assessment phase
    start) through the horizon. Components by phase:
      - T-3 to T-1: orchestrator cost during assessment
      - T0: termination cost + start of dual-operation
      - T0 to T3: dual-operation overhead + retention bonus
      - T4 to T10: learning curve (gross saving captured progressively)
      - T11+: steady state (full gross saving - orchestrator cost)
    """
    md = _md()
    j = params.jurisdiction

    if params.loaded_swe_cost_usd_year is None:
        params.loaded_swe_cost_usd_year = float(md["loaded_swe_cost_usd_year"][j])
    if params.loaded_mid_cost_usd_year is None:
        params.loaded_mid_cost_usd_year = float(md["loaded_mid_engineer_usd_year"][j])
    if params.termination_cost_fraction is None:
        params.termination_cost_fraction = float(
            config.jurisdiction_defaults()[j]["termination_cost_fraction"])

    # Resolve global migration-dynamics knobs: prefer caller override,
    # fall back to YAML.
    orchestrator_ratio = (
        params.orchestrator_ratio
        if params.orchestrator_ratio is not None
        else float(md["orchestrator_ratio"])
    )
    orchestrator_premium_pct = (
        params.orchestrator_premium_pct
        if params.orchestrator_premium_pct is not None
        else float(md["orchestrator_premium_pct"])
    )
    ai_tooling_cost_per_dev = (
        params.ai_tooling_cost_per_dev_usd_year
        if params.ai_tooling_cost_per_dev_usd_year is not None
        else float(md["ai_tooling_cost_per_dev_usd_year"])
    )

    n_sub = int(round(params.n_total_engineers * params.substitution_fraction))
    n_retained = params.n_total_engineers - n_sub
    n_orchestrators = max(
        params.orchestrator_floor,
        int(round(n_retained / orchestrator_ratio)) if n_sub > 0 else 0,
    ) if n_sub > 0 else 0

    # Annual flows
    annual_gross_saving = n_sub * params.loaded_mid_cost_usd_year
    annual_ai_tooling_cost = (
        n_retained + n_sub  # AI tooling helps retained team too
    ) * ai_tooling_cost_per_dev
    orchestrator_annual = n_orchestrators * (
        params.loaded_swe_cost_usd_year * (1.0 + orchestrator_premium_pct)
    )
    annual_net = annual_gross_saving - orchestrator_annual - annual_ai_tooling_cost

    # One-time termination cost at T0
    termination_cost = n_sub * params.loaded_mid_cost_usd_year * params.termination_cost_fraction

    # Build quarter-by-quarter cash flow
    quarters = list(range(-3, params.horizon_quarters - 2))  # T-3 to T20
    cumulative = [0.0]

    learning_curve = md["learning_curve"]
    dual_op_overhead_q = (
        params.dual_operation_overhead_quarters
        if params.dual_operation_overhead_quarters is not None
        else int(md["dual_operation_overhead_quarters"])
    )
    retention_bonus_q = (
        params.retention_bonus_quarters
        if params.retention_bonus_quarters is not None
        else int(md["retention_bonus_quarters"])
    )
    retention_bonus_frac = (
        params.retention_bonus_fraction
        if params.retention_bonus_fraction is not None
        else float(md["retention_bonus_fraction"])
    )

    for q in quarters[1:]:  # skip T-3 since cumulative starts at 0
        cash_q = 0.0
        if q < 0:
            # Assessment phase: only orchestrator cost (quarterly)
            cash_q = -(orchestrator_annual / 4.0)
        elif q == 0:
            # T0: termination + start of dual-op + orchestrator (quarterly)
            cash_q = -termination_cost - (orchestrator_annual / 4.0)
        else:
            # Post-T0
            q_idx = q  # quarters past T0

            # Learning curve fraction for this quarter
            key = f"Q{min(q_idx, 10)}"
            learn_frac = float(learning_curve.get(key, 1.0))

            # Quarterly gross saving (captured by learning curve)
            gross_saving_q = (annual_gross_saving * learn_frac) / 4.0

            # AI tooling cost (always full)
            ai_tooling_q = annual_ai_tooling_cost / 4.0

            # Orchestrator cost (always full)
            orch_q = orchestrator_annual / 4.0

            # Dual-operation overhead (T1 to T3): retained team carries load
            # while AI ramps up. We model this as keeping the substituted
            # team partially on payroll for the dual-op period.
            dual_op_q = 0.0
            if 1 <= q_idx <= dual_op_overhead_q:
                # 50% of substituted team still on payroll, decaying
                dual_op_fraction = 1.0 - (q_idx / float(dual_op_overhead_q + 1))
                dual_op_q = (n_sub * params.loaded_mid_cost_usd_year * dual_op_fraction) / 4.0

            # Retention bonus (T1-T2): paid to remaining senior engineers
            retention_q = 0.0
            if 1 <= q_idx <= retention_bonus_q:
                retention_q = (n_retained * params.loaded_swe_cost_usd_year
                               * retention_bonus_frac) / 4.0

            cash_q = gross_saving_q - ai_tooling_q - orch_q - dual_op_q - retention_q

        cumulative.append(cumulative[-1] + cash_q)

    # Find break-even (first quarter where cumulative >= 0 post-T0)
    break_even = None
    for q, c in zip(quarters, cumulative):
        if q > 0 and c >= 0 and break_even is None:
            break_even = float(q)

    # 5-year (Q20) cumulative
    cumulative_5y = cumulative[-1] if quarters[-1] >= 20 else cumulative[
        min(range(len(quarters)), key=lambda i: abs(quarters[i] - 20))
    ]

    return MigrationResult(
        quarters=quarters,
        cumulative_cash_usd=cumulative,
        annual_gross_saving_usd=annual_gross_saving,
        annual_orchestrator_cost_usd=orchestrator_annual,
        annual_net_saving_usd=annual_net,
        termination_cost_t0_usd=termination_cost,
        break_even_quarter=break_even,
        cumulative_5y_post_t0_usd=cumulative_5y,
        n_substitutable=n_sub,
        n_retained=n_retained,
        n_orchestrators=n_orchestrators,
    )


def reference_firm_migration(jurisdiction: str) -> MigrationResult:
    """Migration for the Section 7.5 reference firm (50 engineers, 60% sub)."""
    ref = _md()["reference_firm"]
    return compute_migration(MigrationParameters(
        n_total_engineers=int(ref["n_engineers"]),
        substitution_fraction=float(ref["substitution_fraction"]),
        jurisdiction=jurisdiction,
    ))


def case_study_migration(firm_slug: str, jurisdiction: str,
                         scenario: Optional[str] = None) -> MigrationResult:
    """Migration for one of the case-study firms (Appendix E).

    Parameters
    ----------
    firm_slug : str
        "neurocertify" or "dataflow_pro"
    jurisdiction : str
        Which arm to operate under ("brazil", "france", "united_states")
    scenario : str, optional
        For dataflow_pro: "conservative", "moderate", or "aggressive"
        For neurocertify: ignored (uses default substitution fraction)
    """
    cs = config.load_parameters()["case_studies_dynamic"][firm_slug]
    if firm_slug == "neurocertify":
        arm = cs["arms"][jurisdiction]
        n_eng = int(arm["engineers"])
        sub_pct = float(cs["ai_substitution_potential"]) * float(cs["layer_4_share"])
    elif firm_slug == "dataflow_pro":
        if scenario is None:
            scenario = "moderate"
        sc = cs["scenarios"][scenario]
        n_eng = sum(int(v) for k, v in cs["arms"]["united_states"].items()
                    if "engineer" in k.lower())
        sub_pct = float(sc["substitution_pct"])
    else:
        raise ValueError(f"Unknown firm_slug: {firm_slug}")

    return compute_migration(MigrationParameters(
        n_total_engineers=n_eng,
        substitution_fraction=sub_pct,
        jurisdiction=jurisdiction,
    ))
