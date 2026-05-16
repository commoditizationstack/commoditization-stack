"""Simulation orchestration - deterministic single-trajectory and Monte Carlo ensemble.

Loads a scenario YAML, builds the KnowledgeStack and Startup objects,
constructs a trajectory of layer-4 substitutability, runs the firm forward,
runs the Investor over the firm's state at exit, and reports the four
valuation method outputs.

Monte Carlo wraps this with parameter perturbation across 10,000 runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
import numpy as np
import pandas as pd
from tqdm import tqdm

from . import config as _global_config
from .stack_layers import KnowledgeStack
from .startup import Startup
from .investor import Investor


def load_scenario(scenario_path: str | Path,
                  base_params_path: str | Path) -> Dict:
    """Load a scenario YAML, merging it onto the base parameters file."""
    base = yaml.safe_load(Path(base_params_path).read_text())
    scenario = yaml.safe_load(Path(scenario_path).read_text())

    def deep_merge(target: dict, source: dict) -> dict:
        for k, v in source.items():
            if (k in target and isinstance(target[k], dict)
                    and isinstance(v, dict)):
                deep_merge(target[k], v)
            else:
                target[k] = v
        return target

    merged = deep_merge(base, {k: v for k, v in scenario.items()
                               if k != "inherits"})
    merged["scenario_name"] = scenario.get("scenario_name", "unnamed")
    merged["description"] = scenario.get("description", "")
    return merged


@dataclass
class SimulationResult:
    scenario_name: str
    survived: bool
    months_run: int
    final_arr_usd: float
    final_team_size: float
    final_cash_usd: float
    final_trl: float
    final_layer4_substitutability: float
    valuations_at_exit: Dict[str, float] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)
    notes: str = ""


def build_substitutability_trajectory(
    stack: KnowledgeStack,
    n_months: int,
    rng: Optional[np.random.Generator] = None,
) -> List[float]:
    """Build a trajectory of layer-4 substitutability over n_months."""
    layer4 = stack["layer_4_codified_synthesis"]
    months = np.arange(n_months + 1)
    years = months / 12.0
    trajectory = [layer4.substitutability_at(y) for y in years]
    return trajectory


def run_single_simulation(
    config: Dict,
    rng: Optional[np.random.Generator] = None,
    perturb_params: bool = False,
) -> SimulationResult:
    """Run one deterministic (or single Monte Carlo) trajectory."""
    if rng is None:
        rng = np.random.default_rng(int(config["simulation"]["random_seed"]))

    stack = KnowledgeStack(config["stack_layers"])
    if perturb_params:
        cv = float(config["monte_carlo"]["layer_velocity_cv"])
        stack = stack.perturb(rng, cv=cv)

    startup_cfg = dict(config["startup"])
    if perturb_params:
        # multiplicative noise on team size and burn
        team_cv = float(config["monte_carlo"]["team_size_cv"])
        burn_cv = float(config["monte_carlo"]["burn_rate_cv"])
        ai_cv = float(config["monte_carlo"]["ai_substitution_cv"])
        startup_cfg["initial_team_size"] = max(2, int(round(
            startup_cfg["initial_team_size"] * np.exp(rng.normal(0, team_cv))
        )))
        startup_cfg["monthly_burn_per_engineer_usd"] *= float(
            np.exp(rng.normal(0, burn_cv)))
        startup_cfg["ai_substitution_potential_layer4"] = float(np.clip(
            startup_cfg["ai_substitution_potential_layer4"]
            * np.exp(rng.normal(0, ai_cv)), 0.05, 0.95
        ))

    startup = Startup.from_config(startup_cfg)
    investor = Investor.from_config(config["investor"])

    n_months = int(config["simulation"]["time_horizon_quarters"]) * 3
    sub_trajectory = build_substitutability_trajectory(stack, n_months, rng)

    # Realistic funding rounds, scaled to sector burn-rate. All knobs in
    # config/parameters.yaml under startup.funding_events and startup.market_size_usd.
    base_burn = startup.monthly_burn(startup.initial_team_size)
    startup_cfg_full = _global_config.load_parameters()["startup"]
    fe = startup_cfg_full["funding_events"]
    series_a = max(float(fe["series_a_min_usd"]), base_burn * float(fe["series_a_burn_multiplier"]))
    series_b = max(float(fe["series_b_min_usd"]), base_burn * float(fe["series_b_burn_multiplier"]))
    series_c = max(float(fe["series_c_min_usd"]), base_burn * float(fe["series_c_burn_multiplier"]))
    funding_events = {
        int(fe["series_a_month"]): series_a,
        int(fe["series_b_month"]): series_b,
        int(fe["series_c_month"]): series_c,
    }
    market_size_usd = float(startup_cfg_full.get("market_size_usd", 2_000_000_000))

    states = startup.run(
        n_months=n_months,
        market_size_usd=market_size_usd,
        layer4_substitutability_trajectory=sub_trajectory,
        funding_events=funding_events,
        rng=rng,
    )

    # valuation at exit (final state)
    final = states[-1]
    val_cfg = config["valuation"]
    valuations = investor.value_startup_via_methods(
        startup_arr_usd=max(final.arr_usd, 1.0),
        projected_exit_revenue_usd=max(final.arr_usd, 1.0) * 4,
        exit_multiple=float(val_cfg["comparable_revenue_multiple_baseline"]),
        revenue_multiple=float(val_cfg["comparable_revenue_multiple_baseline"]),
        team_layer4_share=final.layer4_share,
        ai_substitution_potential_layer4=startup.ai_substitution_potential_layer4,
        valuation_cfg=val_cfg,
        rng=rng if perturb_params else None,
    )

    history_dicts = [
        {"month": s.month, "team_size": s.team_size, "cash_usd": s.cash_usd,
         "arr_usd": s.arr_usd, "trl": s.trl, "is_alive": s.is_alive}
        for s in states
    ]

    return SimulationResult(
        scenario_name=config.get("scenario_name", "unnamed"),
        survived=final.is_alive,
        months_run=final.month,
        final_arr_usd=final.arr_usd,
        final_team_size=final.team_size,
        final_cash_usd=final.cash_usd,
        final_trl=final.trl,
        final_layer4_substitutability=sub_trajectory[
            min(final.month, len(sub_trajectory) - 1)],
        valuations_at_exit=valuations,
        history=history_dicts,
    )


def run_monte_carlo(
    config: Dict,
    n_runs: Optional[int] = None,
    show_progress: bool = True,
) -> pd.DataFrame:
    """Run Monte Carlo ensemble. Returns a DataFrame with one row per run."""
    n_runs = n_runs or int(config["simulation"]["monte_carlo_runs"])
    seed = int(config["simulation"]["random_seed"])
    master_rng = np.random.default_rng(seed)

    rows = []
    iterator = range(n_runs)
    if show_progress:
        iterator = tqdm(iterator, desc=f"MC ({config.get('scenario_name', '')})")
    for _ in iterator:
        run_seed = int(master_rng.integers(0, 2**31 - 1))
        rng = np.random.default_rng(run_seed)
        result = run_single_simulation(config, rng=rng, perturb_params=True)
        row = {
            "scenario": result.scenario_name,
            "survived": result.survived,
            "months_run": result.months_run,
            "final_arr_usd": result.final_arr_usd,
            "final_team_size": result.final_team_size,
            "final_cash_usd": result.final_cash_usd,
            "final_trl": result.final_trl,
            "final_layer4_substitutability": result.final_layer4_substitutability,
        }
        for method, val in result.valuations_at_exit.items():
            row[f"valuation_{method}"] = val
        rows.append(row)

    return pd.DataFrame(rows)


def monte_carlo_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summary statistics for a Monte Carlo ensemble."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    summary = df[numeric_cols].agg(["mean", "median", "std",
                                    lambda x: np.percentile(x, 5),
                                    lambda x: np.percentile(x, 95)]).T
    summary.columns = ["mean", "median", "std", "p5", "p95"]
    summary["survival_rate"] = df["survived"].mean()
    return summary
