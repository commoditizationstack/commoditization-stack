"""Deep-tech startup model.

A startup is characterized by:
  - team_size and its distribution across stack layers (layer_3, layer_4, layer_5)
  - financial state (runway, burn, ARR)
  - technological maturity (TRL)
  - sector parameters (CAC, LTV, churn)
  - exposure to AI substitution at layer 4

The model evolves the firm month-by-month, consuming cash, growing revenue,
and being subject to commoditization-driven cost pressure on its layer-4 labor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

from . import config


def _growth() -> Dict:
    return config.load_parameters()["startup"]["growth"]


@dataclass
class StartupState:
    month: int
    team_size: float
    cash_usd: float
    arr_usd: float
    customers: int
    trl: float
    is_alive: bool
    layer4_share: float
    notes: str = ""


@dataclass
class Startup:
    sector: str
    initial_team_size: int
    team_layer_distribution: Dict[str, float]
    initial_runway_months: float
    monthly_burn_per_engineer_usd: float
    initial_arr_usd: float
    trl_initial: float
    trl_target: float
    cac_usd: float
    ltv_usd: float
    churn_monthly: float
    ai_substitution_potential_layer4: float

    history: List[StartupState] = field(default_factory=list)

    @classmethod
    def from_config(cls, cfg: Dict) -> "Startup":
        return cls(
            sector=cfg.get("sector", "generic_deeptech"),
            initial_team_size=int(cfg["initial_team_size"]),
            team_layer_distribution=dict(cfg["team_layer_distribution"]),
            initial_runway_months=float(cfg["initial_runway_months"]),
            monthly_burn_per_engineer_usd=float(cfg["monthly_burn_per_engineer_usd"]),
            initial_arr_usd=float(cfg.get("initial_arr_usd", 0.0)),
            trl_initial=float(cfg["trl_initial"]),
            trl_target=float(cfg["trl_target"]),
            cac_usd=float(cfg["cac_usd"]),
            ltv_usd=float(cfg["ltv_usd"]),
            churn_monthly=float(cfg["churn_monthly"]),
            ai_substitution_potential_layer4=float(
                cfg.get("ai_substitution_potential_layer4", 0.50)),
        )

    def initial_cash_usd(self) -> float:
        return self.initial_runway_months * self.monthly_burn(self.initial_team_size)

    def monthly_burn(self, team_size: float) -> float:
        return team_size * self.monthly_burn_per_engineer_usd

    def layer4_share(self) -> float:
        return self.team_layer_distribution.get("layer_3", 0.65)

    def initial_state(self) -> StartupState:
        return StartupState(
            month=0,
            team_size=float(self.initial_team_size),
            cash_usd=self.initial_cash_usd(),
            arr_usd=self.initial_arr_usd,
            customers=0,
            trl=self.trl_initial,
            is_alive=True,
            layer4_share=self.layer4_share(),
        )

    def step(
        self,
        prev: StartupState,
        market_size_usd: float,
        layer4_substitutability: float,
        rng: Optional[np.random.Generator] = None,
        new_funding_usd: float = 0.0,
        team_growth_per_month: Optional[float] = None,
        ai_team_optimization: bool = True,
    ) -> StartupState:
        if not prev.is_alive:
            return prev

        g = _growth()
        if team_growth_per_month is None:
            team_growth_per_month = float(g["team_growth_per_month"])

        # Team grows only when revenue is increasing or funding came in
        cash_runway_months = prev.cash_usd / max(self.monthly_burn(prev.team_size), 1.0)
        can_grow = (cash_runway_months > float(g["runway_months_before_team_can_grow"])
                    ) or (new_funding_usd > 0)
        max_team_size = self.initial_team_size * int(g["max_team_size_multiplier"])
        effective_team_growth = team_growth_per_month if (
            can_grow and prev.team_size < max_team_size) else 0.0
        team_size = prev.team_size * (1 + effective_team_growth)
        team_size = min(team_size, max_team_size)

        if ai_team_optimization:
            effective_layer4_cost_factor = 1.0 - (
                layer4_substitutability * self.ai_substitution_potential_layer4
            )
        else:
            effective_layer4_cost_factor = 1.0

        layer4_share = prev.layer4_share
        non_layer4_share = 1.0 - layer4_share
        effective_team_cost = team_size * self.monthly_burn_per_engineer_usd * (
            layer4_share * effective_layer4_cost_factor + non_layer4_share
        )

        # Revenue dynamics - realistic SaaS ramp
        # Pre-revenue: while TRL < 6, no real revenue
        # Once TRL >= 6: ARR ramps from a base proportional to team size
        # Then once ARR > threshold: compounding growth with churn
        seed_threshold = float(g["seed_arr_threshold_usd"])
        seed_per_eng = float(g["seed_arr_per_engineer_month_usd"])
        seed_noise = float(g["seed_growth_noise_sigma"])
        base_growth = float(g["base_saas_growth_rate"])
        base_noise = float(g["base_growth_noise_sigma"])
        revenue_factor = float(g["revenue_to_monthly_factor"])
        trl_growth_rate = float(g["trl_growth_per_month"])

        if prev.trl < 6.0:
            new_arr = 0.0
        elif prev.arr_usd < seed_threshold:
            seed_growth = team_size * seed_per_eng
            if rng is not None:
                seed_growth *= float(np.exp(rng.normal(0, seed_noise)))
            new_arr = prev.arr_usd + seed_growth
        else:
            base_growth_rate = base_growth
            if rng is not None:
                base_growth_rate *= float(np.exp(rng.normal(0, base_noise)))
            market_penetration = prev.arr_usd / max(market_size_usd, 1.0)
            growth_rate = base_growth_rate * max(0.0, 1.0 - market_penetration)
            churn_loss = prev.arr_usd * self.churn_monthly
            new_arr = prev.arr_usd * (1 + growth_rate) - churn_loss
            new_arr = max(0.0, new_arr)

        new_customers = int(new_arr / max(self.ltv_usd / revenue_factor, 1.0))

        monthly_revenue = new_arr / revenue_factor
        cash = prev.cash_usd + monthly_revenue + new_funding_usd - effective_team_cost

        trl_growth = trl_growth_rate if prev.trl < self.trl_target else 0.0
        trl = min(self.trl_target, prev.trl + trl_growth)

        is_alive = cash > 0

        notes = ""
        if ai_team_optimization and effective_layer4_cost_factor < 0.95:
            notes = (f"AI optimization: layer-4 cost factor "
                     f"{effective_layer4_cost_factor:.2f}")

        return StartupState(
            month=prev.month + 1,
            team_size=team_size,
            cash_usd=cash,
            arr_usd=new_arr,
            customers=new_customers,
            trl=trl,
            is_alive=is_alive,
            layer4_share=layer4_share,
            notes=notes,
        )

    def run(
        self,
        n_months: int,
        market_size_usd: float,
        layer4_substitutability_trajectory: List[float],
        funding_events: Optional[Dict[int, float]] = None,
        rng: Optional[np.random.Generator] = None,
        ai_team_optimization: bool = True,
    ) -> List[StartupState]:
        funding_events = funding_events or {}
        states = [self.initial_state()]
        for m in range(1, n_months + 1):
            sub_idx = min(m, len(layer4_substitutability_trajectory) - 1)
            sub = layer4_substitutability_trajectory[sub_idx]
            funding = funding_events.get(m, 0.0)
            new_state = self.step(
                prev=states[-1],
                market_size_usd=market_size_usd,
                layer4_substitutability=sub,
                rng=rng,
                new_funding_usd=funding,
                ai_team_optimization=ai_team_optimization,
            )
            states.append(new_state)
            if not new_state.is_alive:
                break
        self.history = states
        return states

    def summary(self) -> Dict:
        if not self.history:
            return {"status": "not_run"}
        final = self.history[-1]
        survived = final.is_alive
        return {
            "sector": self.sector,
            "months_simulated": final.month,
            "survived": survived,
            "final_arr_usd": final.arr_usd,
            "final_team_size": final.team_size,
            "final_cash_usd": final.cash_usd,
            "final_trl": final.trl,
            "death_month": final.month if not survived else None,
        }
