"""Investor model: VC and angel.

Implements two thesis configurations:
  - classical (pre-2024): weights team_quality, technology_moat, market_size,
    traction, regulatory_position.
  - ai_aware (post-2024): substitutes hypothesis_quality and institutional_embedding
    in place of team_quality and regulatory_position respectively, and reweights.

The investor scores a startup against its thesis weights and produces a
go/no-go decision plus a target valuation based on its thesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np

from . import config
from .valuation import (
    berkus_valuation,
    vc_method_valuation,
    comparable_multiple_valuation,
    damodaran_full_valuation,
)


@dataclass
class InvestmentDecision:
    decision: str
    confidence: float
    target_valuation_usd: float
    method_used: str
    notes: str = ""


@dataclass
class Investor:
    target_irr: float
    hold_period_years: float
    default_dilution_per_round: float
    use_ai_aware_thesis: bool
    thesis_weights: Dict[str, float]

    @classmethod
    def from_config(cls, cfg: Dict) -> "Investor":
        use_ai = bool(cfg.get("use_ai_aware_thesis", True))
        weights_key = ("thesis_weights_ai_aware" if use_ai
                       else "thesis_weights_classical")
        return cls(
            target_irr=float(cfg["target_irr"]),
            hold_period_years=float(cfg["hold_period_years"]),
            default_dilution_per_round=float(cfg["default_dilution_per_round"]),
            use_ai_aware_thesis=use_ai,
            thesis_weights=dict(cfg[weights_key]),
        )

    def score_startup(
        self,
        team_quality: float,
        technology_moat: float,
        market_size_usd: float,
        traction_arr_usd: float,
        regulatory_position: float,
        hypothesis_quality: float,
        institutional_embedding: float,
    ) -> float:
        """Score a startup against this investor's thesis weights.

        All inputs in [0, 1] except market_size_usd and traction_arr_usd which are
        normalized internally with log-transform.
        """
        sc = config.load_parameters()["investor"]["scoring"]
        ms_divisor = float(sc["market_size_log_divisor"])
        tr_divisor = float(sc["traction_log_divisor"])
        ms_floor = float(sc["market_size_floor_usd"])
        ms_score = float(np.clip(np.log10(max(market_size_usd, ms_floor)) / ms_divisor, 0, 1))
        tr_score = float(np.clip(np.log10(max(traction_arr_usd + 1, 1)) / tr_divisor, 0, 1))

        scores = {
            "team_quality": team_quality,
            "technology_moat": technology_moat,
            "market_size": ms_score,
            "traction": tr_score,
            "regulatory_position": regulatory_position,
            "hypothesis_quality": hypothesis_quality,
            "institutional_embedding": institutional_embedding,
        }

        total = 0.0
        for factor, weight in self.thesis_weights.items():
            total += weight * scores.get(factor, 0.0)
        return float(np.clip(total, 0.0, 1.0))

    def value_startup_via_methods(
        self,
        startup_arr_usd: float,
        projected_exit_revenue_usd: float,
        exit_multiple: float,
        revenue_multiple: float,
        team_layer4_share: float,
        ai_substitution_potential_layer4: float,
        valuation_cfg: Dict,
        rng: Optional[np.random.Generator] = None,
    ) -> Dict[str, float]:
        """Run all four valuation methods and return a dict of results."""
        results: Dict[str, float] = {}

        results["vc_method"] = vc_method_valuation(
            projected_exit_revenue_usd=projected_exit_revenue_usd,
            exit_multiple=exit_multiple,
            target_irr=self.target_irr,
            hold_period_years=self.hold_period_years,
            expected_dilution=self.default_dilution_per_round,
        ).point_estimate_usd

        comp_vol = float(valuation_cfg.get(
            "comparable_multiple_volatility_post_genai", 0.0)) if rng is not None else 0.0
        results["comparable_multiples"] = comparable_multiple_valuation(
            arr_usd=startup_arr_usd,
            revenue_multiple=revenue_multiple,
            multiple_volatility=comp_vol,
            rng=rng,
        ).point_estimate_usd

        # Damodaran with classical and inverted discount
        # Build a 5y projection from current ARR with a typical SaaS curve
        g = config.load_parameters()["startup"]["growth"]
        proj_growth = float(g["saas_projection_growth_rate"])
        min_arr = float(g["min_arr_for_saas_phase_usd"])
        terminal_growth = float(valuation_cfg.get(
            "damodaran_full_terminal_growth",
            config.load_parameters()["valuation"]["damodaran_full_terminal_growth"]))
        proj = []
        cur = max(startup_arr_usd, min_arr)
        for _ in range(5):
            cur = cur * proj_growth
            proj.append(cur)

        results["damodaran_classical"] = damodaran_full_valuation(
            revenue_projection_usd=proj,
            discount_rate=self.target_irr,
            terminal_growth=terminal_growth,
            terminal_multiple=exit_multiple,
            team_layer4_share=team_layer4_share,
            ai_substitution_potential_layer4=ai_substitution_potential_layer4,
            use_inverted_discount=False,
            classical_discount_rate=float(valuation_cfg.get(
                "damodaran_key_person_discount_classical", 0.175)),
        ).point_estimate_usd

        results["damodaran_inverted"] = damodaran_full_valuation(
            revenue_projection_usd=proj,
            discount_rate=self.target_irr,
            terminal_growth=terminal_growth,
            terminal_multiple=exit_multiple,
            team_layer4_share=team_layer4_share,
            ai_substitution_potential_layer4=ai_substitution_potential_layer4,
            use_inverted_discount=True,
            threshold_layer4_share=float(valuation_cfg.get(
                "damodaran_inverted_threshold_layer4_share", 0.55)),
            classical_discount_rate=float(valuation_cfg.get(
                "damodaran_key_person_discount_classical", 0.175)),
            max_premium_when_inverted=float(valuation_cfg.get(
                "damodaran_inverted_max_premium", 0.15)),
        ).point_estimate_usd

        return results

    def decide(
        self,
        thesis_score: float,
        proposed_valuation_usd: float,
        target_valuation_usd: float,
        decision_threshold: Optional[float] = None,
    ) -> InvestmentDecision:
        inv_cfg = config.load_parameters()["investor"]
        if decision_threshold is None:
            decision_threshold = float(inv_cfg["decision_threshold"])
        overpriced_mult = float(inv_cfg["overpriced_negotiation_multiple"])
        if thesis_score < decision_threshold:
            return InvestmentDecision(
                decision="pass",
                confidence=1.0 - thesis_score,
                target_valuation_usd=0.0,
                method_used="thesis_score",
                notes=f"Score {thesis_score:.2f} below threshold {decision_threshold:.2f}",
            )
        if proposed_valuation_usd > overpriced_mult * target_valuation_usd:
            return InvestmentDecision(
                decision="negotiate",
                confidence=thesis_score,
                target_valuation_usd=target_valuation_usd,
                method_used="valuation_gap",
                notes=f"Proposed valuation > {overpriced_mult:.1f}x target.",
            )
        return InvestmentDecision(
            decision="invest",
            confidence=thesis_score,
            target_valuation_usd=target_valuation_usd,
            method_used="thesis_aligned",
            notes="Score and valuation aligned.",
        )
