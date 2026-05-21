"""Fragility map across the seven-layer framework (Appendix E.5).

Computes the fragility index for a firm given its Layer-4 and Layer-6 shares:
  fragility = L4_share - coefficient * L6_share

Positive values indicate fragile profiles where Layer-4 erosion outpaces
Layer-6 protection; negative values indicate resilient profiles where
Layer-6 protection dominates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from . import config


@dataclass
class FragilityResult:
    """Output of a fragility-index computation."""
    firm_label: str
    layer4_share: float
    layer6_share: float
    fragility_index: float
    zone: str                            # "resilient", "borderline", "fragile"


def _fi() -> Dict:
    return config.load_parameters()["fragility_index"]


def compute_fragility(
    layer4_share: float,
    layer6_share: float,
    firm_label: str = "firm",
    l6_coefficient: Optional[float] = None,
    resilient_threshold: Optional[float] = None,
    fragile_threshold: Optional[float] = None,
) -> FragilityResult:
    """Compute the fragility index for a single firm.

    The three calibration knobs are user-overridable:

      ``l6_coefficient``       Multiplier on L6 (paper §E.5 default 1.5).
      ``resilient_threshold``  Lower band of the borderline zone (default −0.10).
      ``fragile_threshold``    Upper band of the borderline zone (default +0.10).

    When ``None``, each falls back to the YAML-canonical value.
    """
    fi = _fi()
    coef = float(l6_coefficient if l6_coefficient is not None
                 else fi["l6_coefficient"])
    resilient_thr = float(resilient_threshold if resilient_threshold is not None
                          else fi["resilient_threshold"])
    fragile_thr = float(fragile_threshold if fragile_threshold is not None
                        else fi["fragile_threshold"])

    index = layer4_share - coef * layer6_share

    if index < resilient_thr:
        zone = "resilient"
    elif index > fragile_thr:
        zone = "fragile"
    else:
        zone = "borderline"

    return FragilityResult(
        firm_label=firm_label,
        layer4_share=layer4_share,
        layer6_share=layer6_share,
        fragility_index=index,
        zone=zone,
    )


def case_studies_fragility(
    l6_coefficient: Optional[float] = None,
    resilient_threshold: Optional[float] = None,
    fragile_threshold: Optional[float] = None,
) -> Dict[str, FragilityResult]:
    """Compute fragility for the two case-study firms.

    The three optional overrides propagate into each per-firm
    ``compute_fragility`` call so the resulting zones reflect the
    user's calibration. When all three are ``None``, the result is
    identical to the paper-canonical case-studies fragility map.
    """
    cs = config.load_parameters()["case_studies_dynamic"]
    return {
        "neurocertify": compute_fragility(
            float(cs["neurocertify"]["layer_exposure"]["layer_4_codified"]),
            float(cs["neurocertify"]["layer_exposure"]["layer_6_institutional"]),
            firm_label=str(cs["neurocertify"]["label"]),
            l6_coefficient=l6_coefficient,
            resilient_threshold=resilient_threshold,
            fragile_threshold=fragile_threshold,
        ),
        "dataflow_pro": compute_fragility(
            float(cs["dataflow_pro"]["layer_exposure"]["layer_4_codified"]),
            float(cs["dataflow_pro"]["layer_exposure"]["layer_6_institutional"]),
            firm_label=str(cs["dataflow_pro"]["label"]),
            l6_coefficient=l6_coefficient,
            resilient_threshold=resilient_threshold,
            fragile_threshold=fragile_threshold,
        ),
    }
