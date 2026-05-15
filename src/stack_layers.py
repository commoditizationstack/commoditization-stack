"""Seven-layer framework of the knowledge-production stack.

All seven layers of the framework introduced in Section 4 of the working paper
"The End of the Build" (de Miranda Neto, 2026) are implemented in this single
module. Layers 1 through 6 are the empirically grounded core; Layer 7
(cross-border knowledge regime) is offered as a tentative hypothesis in
Section 4.7 and is implemented at the end of this module via
KnowledgeRegimeParameters, KNOWLEDGE_REGIME_DEFAULTS,
apply_knowledge_regime_modulation, and crossborder_acquisition_friction.

Layer 1 (Infrastructure) is sub-divided internally into training and inference
because their commoditization velocities differ in sign, but the two sub-keys
count as a single layer in the seven-layer numbering used in the paper.

Implements the conceptual framework introduced in de Miranda Neto (2026, Section 4).
Each layer is parameterized by:
  - velocity: annual rate of change of substitutability (negative = anti-commoditizing)
  - substitutability_2026: baseline substitutability at simulation start (0..1)

The framework's central claim is that commoditization is a property of *layers*
of the stack, not of "AI" considered as a single object. Different layers move
at different speeds, sometimes in opposite directions.

Status: heuristic framework, not measured. Parameters are conceptual estimates
calibrated to align with the qualitative directions reported in the paper's
Section 4. Adjust in config/parameters.yaml for sensitivity analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import numpy as np


@dataclass
class StackLayer:
    """A single layer of the knowledge-production stack."""

    layer_id: str
    name: str
    velocity: float
    substitutability_2026: float
    description: str = ""

    def substitutability_at(self, year_offset: float) -> float:
        """Substitutability at year (year_offset) relative to 2026.

        Uses bounded logistic update so substitutability stays in (0, 1).
        For positive velocity, approaches 1; for negative velocity, approaches 0.
        """
        s0 = self.substitutability_2026
        v = self.velocity
        s_clipped = min(max(s0, 0.01), 0.99)
        logit_s = np.log(s_clipped / (1 - s_clipped))
        new_logit = logit_s + v * year_offset * 2.0
        new_s = 1.0 / (1.0 + np.exp(-new_logit))
        return float(np.clip(new_s, 0.0, 1.0))

    def is_commoditizing(self) -> bool:
        return self.velocity > 0

    def __repr__(self) -> str:
        direction = "up" if self.velocity > 0 else ("down" if self.velocity < 0 else "flat")
        return (f"StackLayer({self.layer_id}, velocity={self.velocity:+.2f} {direction}, "
                f"s2026={self.substitutability_2026:.2f})")


class KnowledgeStack:
    """Container for the six core layers (Layers 1 through 6, with Layer 1 split into training and inference sub-keys). Layer 7 (KnowledgeRegimeParameters) is also defined in this module."""

    LAYER_KEYS_ORDERED = [
        "layer_1_infra_training",
        "layer_1_infra_inference",
        "layer_2_foundation_models",
        "layer_3_capability_access",
        "layer_4_codified_synthesis",
        "layer_5_hypothesis",
        "layer_6_institutional",
    ]

    def __init__(self, layers_config: Dict[str, dict]):
        self.layers: Dict[str, StackLayer] = {}
        for layer_id in self.LAYER_KEYS_ORDERED:
            if layer_id not in layers_config:
                raise KeyError(f"Missing layer in config: {layer_id}")
            cfg = layers_config[layer_id]
            self.layers[layer_id] = StackLayer(
                layer_id=layer_id,
                name=cfg["name"],
                velocity=float(cfg["velocity"]),
                substitutability_2026=float(cfg["substitutability_2026"]),
                description=cfg.get("description", ""),
            )

    def __getitem__(self, layer_id: str) -> StackLayer:
        return self.layers[layer_id]

    def __iter__(self):
        return iter(self.layers.values())

    def all_substitutabilities_at(self, year_offset: float) -> Dict[str, float]:
        return {lid: layer.substitutability_at(year_offset)
                for lid, layer in self.layers.items()}

    def commoditizing_layers(self) -> List[StackLayer]:
        return [layer for layer in self if layer.is_commoditizing()]

    def anti_commoditizing_layers(self) -> List[StackLayer]:
        return [layer for layer in self if layer.velocity < 0]

    def perturb(self, rng: np.random.Generator, cv: float = 0.20) -> "KnowledgeStack":
        """Return a perturbed copy for Monte Carlo."""
        new_config = {}
        for lid, layer in self.layers.items():
            sign = np.sign(layer.velocity) if layer.velocity != 0 else 1.0
            mag = abs(layer.velocity)
            mag_perturbed = mag * np.exp(rng.normal(0, cv))
            v_new = sign * mag_perturbed
            s_new = float(np.clip(
                layer.substitutability_2026 + rng.normal(0, 0.05),
                0.01, 0.99
            ))
            new_config[lid] = {
                "name": layer.name,
                "velocity": v_new,
                "substitutability_2026": s_new,
                "description": layer.description,
            }
        return KnowledgeStack(new_config)

    def summary_table(self) -> List[Dict]:
        rows = []
        for layer in self:
            rows.append({
                "layer_id": layer.layer_id,
                "name": layer.name,
                "velocity": layer.velocity,
                "substitutability_2026": layer.substitutability_2026,
                "direction": ("commoditizing" if layer.velocity > 0 else
                              ("anti-commoditizing" if layer.velocity < 0 else "stable")),
            })
        return rows


# ============================================================================
# Layer 7 - Cross-border knowledge regime (tentative hypothesis)
# ============================================================================
#
# This section implements Layer 7 of the seven-layer framework, integrated
# directly into stack_layers.py. The layer is offered as a tentative hypothesis
# in Section 4.7 of the paper (de Miranda Neto, 2026) and captures the regime
# under which codified knowledge produced in one jurisdiction is computationally
# accessible in another.
#
# Status: hypothesis, not established regularity. The values of the
# knowledge-integration coefficient K7 are illustrative rather than estimated.
# Concrete operational illustrations of the direction of the regime in
# 2025-2026 include: Anthropic's Claude Gov (June 2025, restricted to U.S.
# national security customers); Anthropic's tightening of access policy to
# block entities under majority Chinese ownership globally (September 2025);
# and Anthropic's Claude Mythos Preview (April 2026) under Project Glasswing -
# a closed consortium of Western big-tech and critical-software firms that
# explicitly excludes the principal Anthropic competitor.
#
# K7 modulates the velocity of Layer 4 (codified synthesis, since this layer
# depends on access to globally trained frontier corpora) and the bias profile
# of Layer 5 (hypothesis formulation and judgment, since judgment trained on
# bloc-specific corpora acquires bloc-specific oversimplifications). Layer 6
# is not modulated by K7 because institutional trust accumulates locally
# regardless of the global regime.


@dataclass
class KnowledgeRegimeParameters:
    """Parameters of the cross-border knowledge regime (Layer 7).

    These parameters are illustrative rather than estimated. They are intended
    to allow the reader to explore the implied consequences of varying K7 on
    the predictions of the surrounding framework. They should not be read as
    empirical estimates of the actual state of the regime in 2026 or beyond.

    Attribute naming follows the seven-layer numbering of the paper:
      layer4_substitution_modulator: scales Layer-4 (codified synthesis)
        substitutability. Layer 3 (capability access) is also modulated
        downstream through this same coefficient because access constrains
        synthesis.
      layer5_judgment_bias_factor: factor by which Layer-5 judgment value
        increases as K7 falls (more curatorial human judgment needed).
    """
    K_coefficient: float = 0.70
    bloc_assignment: str = "western"
    layer4_substitution_modulator: float = 0.70
    layer5_judgment_bias_factor: float = 0.85
    notes: str = ""

    def is_baseline(self) -> bool:
        return self.K_coefficient >= 0.99


KNOWLEDGE_REGIME_DEFAULTS: Dict[str, KnowledgeRegimeParameters] = {
    "globalized_2020": KnowledgeRegimeParameters(
        K_coefficient=1.00,
        bloc_assignment="globally_integrated",
        layer4_substitution_modulator=1.00,
        layer5_judgment_bias_factor=1.00,
        notes="Pre-decoupling baseline. Frontier models freely accessible "
              "across blocs; scientific corpora globally indexed; researcher "
              "mobility unconstrained. Approximate state circa 2018-2020.",
    ),
    "current_2026": KnowledgeRegimeParameters(
        K_coefficient=0.70,
        bloc_assignment="western",
        layer4_substitution_modulator=0.70,
        layer5_judgment_bias_factor=0.85,
        notes="Current estimated regime. Partial fragmentation evidenced by "
              "Anthropic Claude Gov (Jun 2025) restricted to US national "
              "security customers; Anthropic policy tightening (Sep 2025) "
              "blocking Chinese-owned entities globally; Anthropic Claude "
              "Mythos Preview (Apr 2026) released only to closed Project "
              "Glasswing consortium; EU AI Act enforcement (Aug 2025); "
              "collapse of EU-US Data Privacy Framework (late 2025); "
              "CLOUD Act extraterritoriality; US-China STA renewal with "
              "restrictions on emerging tech (Dec 2024); ASPI Critical Tech "
              "Tracker showing peak collaboration in 2019. Illustrative "
              "value, not estimated.",
    ),
    "fragmented_2030": KnowledgeRegimeParameters(
        K_coefficient=0.40,
        bloc_assignment="western",
        layer4_substitution_modulator=0.40,
        layer5_judgment_bias_factor=0.55,
        notes="Hypothetical 2030 scenario of severe fragmentation. Frontier "
              "models deployed only within bloc; scientific corpora subject "
              "to dual-use restrictions; researcher mobility constrained; "
              "data sovereignty fully enforced. Counterfactual scenario for "
              "exploring framework sensitivity, not a forecast.",
    ),
}


def apply_knowledge_regime_modulation(
    layer4_substitutability_baseline: float,
    layer5_judgment_value_baseline: float,
    layer6_institutional_value_baseline: float,
    regime: KnowledgeRegimeParameters,
):
    """Apply knowledge-regime modulation to the per-layer parameters.

    Returns a tuple (layer4, layer5, layer6) of modulated values.

      Layer 4 (codified retrieval, synthesis, prototyping) substitutability
      scales linearly with the modulator. When K7 is lower, AI tools are less
      effective at substituting Layer-4 tasks because the underlying frontier
      models have access to a smaller and more bloc-specific training corpus.
      Layer 3 (capability access) is correlated by construction since access
      is the input to synthesis.

      Layer 5 (hypothesis formulation and judgment) value increases as the
      judgment bias factor decreases. The scale-up factor is the reciprocal
      of the bias factor.

      Layer 6 (institutional embedding and certification) value is unchanged.
    """
    modulated_layer4 = (
        layer4_substitutability_baseline * regime.layer4_substitution_modulator
    )
    modulated_layer5 = (
        layer5_judgment_value_baseline / max(0.1, regime.layer5_judgment_bias_factor)
    )
    modulated_layer6 = layer6_institutional_value_baseline
    return modulated_layer4, modulated_layer5, modulated_layer6


def crossborder_acquisition_friction(
    target_bloc: str,
    acquirer_bloc: str,
    base_substitution_potential: float,
) -> float:
    """Friction on substitution potential when target and acquirer differ in bloc.

    Reduces substitution potential when blocs differ to reflect: (i) regulatory
    scrutiny over cross-border AI technology transfer (CFIUS in US, FDI
    screening in EU); (ii) restrictions on data movement across bloc
    boundaries; (iii) operational complexity of relocating AI-substituted
    function across jurisdictions with different regulatory regimes.
    """
    if target_bloc == acquirer_bloc:
        return base_substitution_potential
    cross_bloc_friction = 0.30
    return base_substitution_potential * (1.0 - cross_bloc_friction)
