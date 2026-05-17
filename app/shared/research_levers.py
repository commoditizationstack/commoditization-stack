"""Curated catalogue of research levers — the parameters that matter.

Every entry in ``LEVER_GROUPS`` below is a parameter that a PhD student or
senior researcher would plausibly want to manipulate to test a hypothesis
under *The Cost Gradient of the Build* (de Miranda Neto, 2026).

Calibration constants whose only role is to shape internal mechanics
(random seeds, grid sizes, UI defaults, plot colors, computed outputs
written back into the YAML for convenience) are deliberately *excluded*.
They remain in ``parameters.yaml`` for power-user inspection via the full
"⚙️ Configuration" tab and via the YAML round-trip, but they do not
appear in the curated tab or in the PDF parameter chapter.

Each entry carries:
  - ``dot_path``: the YAML address the override targets.
  - ``label``: human-readable name shown in the UI / PDF.
  - ``description``: one or two sentences. What is this? Which paper
    section / figure does it affect?
  - ``kind``: ``"slider"`` or ``"number"``.
  - ``min`` / ``max`` / ``step``: bounds for the widget.
  - ``format``: matplotlib-style format string. ``"%d"`` → integer widget.

The data structure is consumed by:
  * ``app/tabs/tab_research_levers.py`` to render the new tab.
  * ``app/shared/pdf_export.py`` to build the parameter chapter of the
    scenario report.
"""

from __future__ import annotations

from typing import Any, Dict, List


LeverSpec = Dict[str, Any]
LeverGroup = Dict[str, Any]


LEVER_GROUPS: List[LeverGroup] = [
    # ======================================================================
    # 1 — Headline levers
    # ======================================================================
    {
        "id": "headline",
        "label": "🎯 Headline levers — what moves every figure",
        "intro": (
            "The five parameters a researcher will typically touch first. "
            "K7 is the central hypothesis variable of Section 4.1; the AI "
            "substitutability of Layer 4 is the inversion trigger of "
            "Section 6.4; the team's Layer-4 / Layer-6 shares position a "
            "firm on the fragility map of Appendix E.5; the inversion "
            "threshold sets when Damodaran's classical key-person discount "
            "flips sign."),
        "params": [
            {
                "dot_path": "knowledge_regimes.regimes.current_2026.K_coefficient",
                "label": "K7 — cross-border knowledge-integration coefficient",
                "description": (
                    "Tentative seventh layer of the stack (Section 4.1). "
                    "1.0 = globally integrated; 0.45 = collapse threshold. "
                    "Controls inversion-premium magnitude (Figures 4, 11) "
                    "and the XAI capacity gap (Appendix G.2)."),
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
                "format": "%.2f",
            },
            {
                "dot_path": "startup.ai_substitution_potential_layer4",
                "label": "AI substitutability potential of Layer 4",
                "description": (
                    "Fraction of Layer-4 work that AI tooling can substitute "
                    "(Section 6.4). Combined with high Layer-4 team share, "
                    "above the threshold below, the classical key-person "
                    "discount flips to premium. Drives Figures 3, 11, 12."),
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
                "format": "%.2f",
            },
            {
                "dot_path": "valuation.damodaran_inverted_threshold_layer4_share",
                "label": "Damodaran inversion threshold — Layer-4 team share",
                "description": (
                    "Above this Layer-4 team share, AND with high AI "
                    "substitutability, the classical −17.5% key-person "
                    "discount becomes an acquisition premium "
                    "(Section 6.4, Figure 3)."),
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
                "format": "%.2f",
            },
            {
                "dot_path": "case_studies_dynamic.dataflow_pro.layer_4_share",
                "label": "DataFlow Pro — Layer-4 share",
                "description": (
                    "Codified-work fraction of the commoditizing-tech firm. "
                    "Positions DataFlow on the fragility map (Appendix E.5, "
                    "Figure 35) and drives its inversion intensity."),
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
                "format": "%.2f",
            },
            {
                "dot_path": "case_studies_dynamic.neurocertify.layer_exposure.layer_6_institutional",
                "label": "NeuroCertify — Layer-6 institutional share",
                "description": (
                    "Regulatory/accreditation moat of the deep-tech firm. "
                    "Drives the anti-commoditizing protection in the "
                    "layered DCF (Appendix A.2, Figure 17) and the firm's "
                    "position in the resilient zone (Figure 35)."),
                "kind": "slider", "min": 0.0, "max": 0.7, "step": 0.05,
                "format": "%.2f",
            },
        ],
    },

    # ======================================================================
    # 2 — Seven-layer stack (Section 4)
    # ======================================================================
    {
        "id": "stack",
        "label": "🧬 Seven-layer stack (Section 4)",
        "intro": (
            "The annual commoditization velocity and 2026 starting "
            "substitutability for each of the seven layers. Positive "
            "velocity = commoditizing (AI tooling substitutes more of this "
            "layer's work each year); negative velocity = anti-commoditizing "
            "(Layer 1 training and Layer 6 institutional). Drives Figures 1 "
            "and 2."),
        "params": [
            *[{
                "dot_path": f"stack_layers.{k}.velocity",
                "label": f"{label} — velocity (logit-shift / year)",
                "description": "Annual rate of change of substitutability for this layer.",
                "kind": "slider", "min": -0.5, "max": 0.6, "step": 0.01,
                "format": "%.2f",
            } for k, label in [
                ("layer_1_infra_training", "L1 Infrastructure (training)"),
                ("layer_1_infra_inference", "L1 Infrastructure (inference)"),
                ("layer_2_foundation_models", "L2 Foundation models"),
                ("layer_3_capability_access", "L3 Capability access"),
                ("layer_4_codified_synthesis", "L4 Codified synthesis"),
                ("layer_5_hypothesis", "L5 Hypothesis & judgment"),
                ("layer_6_institutional", "L6 Institutional"),
            ]],
            *[{
                "dot_path": f"stack_layers.{k}.substitutability_2026",
                "label": f"{label} — substitutability at 2026 (0..1)",
                "description": "Starting point of the trajectory.",
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
                "format": "%.2f",
            } for k, label in [
                ("layer_1_infra_training", "L1 Infrastructure (training)"),
                ("layer_1_infra_inference", "L1 Infrastructure (inference)"),
                ("layer_2_foundation_models", "L2 Foundation models"),
                ("layer_3_capability_access", "L3 Capability access"),
                ("layer_4_codified_synthesis", "L4 Codified synthesis"),
                ("layer_5_hypothesis", "L5 Hypothesis & judgment"),
                ("layer_6_institutional", "L6 Institutional"),
            ]],
        ],
    },

    # ======================================================================
    # 3 — Cross-border knowledge regime (Section 4.1)
    # ======================================================================
    {
        "id": "k7_regime",
        "label": "🌐 Cross-border knowledge regime (Section 4.1)",
        "intro": (
            "The K7 coefficient under three reference regimes (globalized "
            "2020, current 2026, fragmented 2030) and the friction added "
            "when the acquirer and target belong to different blocs. The "
            "Layer-4 modulator scales effective Layer-4 substitutability; "
            "the Layer-5 bias factor scales the relative value of human "
            "judgment under low K7. Drives Figures 14, 15."),
        "params": [
            {
                "dot_path": "knowledge_regimes.cross_border_friction",
                "label": "Cross-border friction (target ≠ acquirer bloc)",
                "description": (
                    "Reduction in effective substitution potential under "
                    "cross-bloc acquisition. Drives the dashed line in "
                    "Figure 15 and the Section 7.4 ordering."),
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
                "format": "%.2f",
            },
        ] + [item for regime, regime_label, expose_k in [
                ("globalized_2020", "Globalized 2020", True),
                ("current_2026", "Current 2026", False),
                ("fragmented_2030", "Fragmented 2030", True),
            ] for item in (
                # K7 for current_2026 lives in the 🎯 Headline group above to
                # avoid a duplicate-widget conflict.
                ([{
                    "dot_path": f"knowledge_regimes.regimes.{regime}.K_coefficient",
                    "label": f"K7 — {regime_label}",
                    "description": "Reference K7 value for this regime.",
                    "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
                    "format": "%.2f",
                }] if expose_k else []) + [
                    {
                        "dot_path": f"knowledge_regimes.regimes.{regime}.layer4_substitution_modulator",
                        "label": f"Layer-4 modulator — {regime_label}",
                        "description": (
                            "How much K7 of this regime scales Layer-4 effective "
                            "substitutability."),
                        "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
                        "format": "%.2f",
                    },
                    {
                        "dot_path": f"knowledge_regimes.regimes.{regime}.layer5_judgment_bias_factor",
                        "label": f"Layer-5 judgment bias — {regime_label}",
                        "description": (
                            "How much human judgment is needed for bloc-specific "
                            "bias detection under this regime."),
                        "kind": "slider", "min": 0.0, "max": 1.5, "step": 0.01,
                        "format": "%.2f",
                    },
                ]
            )
        ],
    },

    # ======================================================================
    # 4 — Inverted key-person discount (Section 6.4)
    # ======================================================================
    {
        "id": "inverted_discount",
        "label": "💰 Inverted key-person discount (Section 6.4)",
        "intro": (
            "Damodaran's classical key-person discount (−17.5% on average) "
            "is inverted into an acquisition premium when the target's "
            "Layer-4 team share and the AI substitutability of Layer 4 are "
            "both high enough. These four constants define the regime "
            "switch and its magnitude. Drives Figure 3."),
        "params": [
            {
                "dot_path": "valuation.damodaran_key_person_discount_classical",
                "label": "Classical Damodaran key-person discount",
                "description": (
                    "Baseline downward valuation adjustment when the "
                    "framework is in the classical regime. Damodaran's "
                    "documented range is 10–25%; the default 17.5% is the "
                    "midpoint."),
                "kind": "slider", "min": 0.0, "max": 0.50, "step": 0.005,
                "format": "%.3f",
            },
            {
                "dot_path": "valuation.damodaran_inverted_max_premium",
                "label": "Max premium when fully inverted",
                "description": (
                    "Cap on the inverted (positive) adjustment when team "
                    "Layer-4 share and AI substitutability are at their "
                    "maxima. Acts as the upper bound on the colour scale "
                    "of the heatmap."),
                "kind": "slider", "min": 0.0, "max": 0.50, "step": 0.01,
                "format": "%.2f",
            },
            {
                "dot_path": "valuation.damodaran_inversion_min_substitution_potential",
                "label": "Minimum AI substitutability to enable inversion",
                "description": (
                    "Below this AI substitutability, the framework stays in "
                    "the classical regime regardless of Layer-4 share."),
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
                "format": "%.2f",
            },
            {
                "dot_path": "valuation.damodaran_full_terminal_growth",
                "label": "Terminal growth rate (Damodaran DCF)",
                "description": (
                    "Used by the classical Damodaran DCF for the perpetuity "
                    "after the explicit projection period."),
                "kind": "slider", "min": 0.0, "max": 0.10, "step": 0.005,
                "format": "%.3f",
            },
            {
                "dot_path": "valuation.comparable_revenue_multiple_baseline",
                "label": "Comparable revenue multiple — baseline",
                "description": (
                    "Industry-median revenue multiple used by the comparables "
                    "valuation method (Section 6.3)."),
                "kind": "slider", "min": 1.0, "max": 30.0, "step": 0.5,
                "format": "%.1f",
            },
            {
                "dot_path": "valuation.berkus_factor_cap_usd",
                "label": "Berkus method — factor cap (USD)",
                "description": (
                    "Maximum value any single Berkus factor can contribute. "
                    "Drives the Berkus distribution in Figure 9."),
                "kind": "number", "min": 0.0, "max": 2_000_000.0,
                "step": 10_000.0, "format": "%.0f",
            },
        ],
    },

    # ======================================================================
    # 5 — Layered DCF (Appendix A)
    # ======================================================================
    {
        "id": "layered_dcf",
        "label": "📐 Layered DCF (Appendix A)",
        "intro": (
            "Two innovations on top of classical Damodaran: a TRL-modulated "
            "discount-rate premium (TRL 1 → +16pp, TRL 9 → 0), and a "
            "signed risk coefficient for each of the seven layers that "
            "decomposes the firm-specific risk premium. Drives Figures 16, "
            "17, 18."),
        "params": [
            *[{
                "dot_path": f"valuation_layered.trl_discount_premium.{t}",
                "label": f"TRL {t} → discount premium (pp)",
                "description": (
                    f"Premium added to base CAPM when the firm is at TRL {t}. "
                    "Calibration follows Equidam (2025) and Hectelion (2025)."),
                "kind": "slider", "min": 0.0, "max": 0.30, "step": 0.005,
                "format": "%.3f",
            } for t in range(1, 10)],
            *[{
                "dot_path": f"valuation_layered.layer_risk_coefficients.{k}",
                "label": f"{label} — risk coefficient",
                "description": (
                    "Signed per-layer contribution to the firm-specific "
                    "risk premium. Positive = layer is commoditizing and "
                    "adds risk; negative = anti-commoditizing protection."),
                "kind": "slider", "min": -0.10, "max": 0.20, "step": 0.005,
                "format": "%.3f",
            } for k, label in [
                ("layer_1_infra", "L1 Infrastructure"),
                ("layer_2_foundation", "L2 Foundation"),
                ("layer_3_capability", "L3 Capability"),
                ("layer_4_codified", "L4 Codified"),
                ("layer_5_judgment", "L5 Judgment"),
                ("layer_6_institutional", "L6 Institutional"),
                ("layer_7_crossborder", "L7 Cross-border"),
            ]],
        ],
    },

    # ======================================================================
    # 6 — Two-phase CAPM/WACC (Appendix B)
    # ======================================================================
    {
        "id": "two_phase",
        "label": "🔄 Two-phase CAPM / WACC (Appendix B)",
        "intro": (
            "Per-firm, per-phase calibration of the post-AI double valley. "
            "Phase 1 = growth; Phase 2 = second valley (commoditization "
            "shock for Layer-4-heavy firms; regulatory accreditation dip "
            "for Layer-6-heavy firms); Phase 3 = terminal. Drives Figures "
            "19, 20."),
        "params": [
            {
                "dot_path": "firms_appendix_b.neurocertify.phases.phase_1_end_year",
                "label": "NeuroCertify — Phase 1 end (year)",
                "description": "Last year of Phase 1 (growth) for NeuroCertify.",
                "kind": "number", "min": 1, "max": 6, "step": 1, "format": "%d",
            },
            {
                "dot_path": "firms_appendix_b.neurocertify.phases.phase_2_end_year",
                "label": "NeuroCertify — Phase 2 end (year)",
                "description": "Last year of Phase 2 (second valley).",
                "kind": "number", "min": 2, "max": 10, "step": 1, "format": "%d",
            },
            *[{
                "dot_path": f"firms_appendix_b.{firm}.phases.beta_unlevered_{phase}",
                "label": f"{firm_label} — β unlevered {phase_label}",
                "description": (
                    f"Unlevered β for {firm_label} during {phase_label}. "
                    "Higher β = higher cost of equity in that phase."),
                "kind": "slider", "min": 0.0, "max": 3.5, "step": 0.05,
                "format": "%.2f",
            } for firm, firm_label in [("neurocertify", "NeuroCertify"),
                                         ("dataflow", "DataFlow Pro")]
              for phase, phase_label in [("phase_1", "Phase 1"),
                                          ("phase_2", "Phase 2"),
                                          ("phase_3", "Phase 3")]],
            *[{
                "dot_path": f"firms_appendix_b.{firm}.phases.de_ratio_{phase}",
                "label": f"{firm_label} — D/E {phase_label}",
                "description": "Debt-to-equity ratio in this phase.",
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
                "format": "%.2f",
            } for firm, firm_label in [("neurocertify", "NeuroCertify"),
                                         ("dataflow", "DataFlow Pro")]
              for phase, phase_label in [("phase_1", "Phase 1"),
                                          ("phase_2", "Phase 2"),
                                          ("phase_3", "Phase 3")]],
            {
                "dot_path": "firms_appendix_b.neurocertify.second_valley_drag",
                "label": "NeuroCertify — second-valley drag on terminal value",
                "description": (
                    "Multiplicative haircut on terminal value to reflect the "
                    "second commoditization valley."),
                "kind": "slider", "min": 0.0, "max": 0.50, "step": 0.01,
                "format": "%.2f",
            },
            {
                "dot_path": "firms_appendix_b.dataflow.second_valley_drag",
                "label": "DataFlow Pro — second-valley drag",
                "description": "Same drag, calibrated for the commoditizing firm.",
                "kind": "slider", "min": 0.0, "max": 0.50, "step": 0.01,
                "format": "%.2f",
            },
        ],
    },

    # ======================================================================
    # 7 — Macro (Appendices A, B)
    # ======================================================================
    {
        "id": "macro",
        "label": "📊 Macro inputs",
        "intro": (
            "Risk-free rate, equity risk premium, and terminal growth rate "
            "used by every DCF in the framework. Defaults reflect Damodaran's "
            "January 2026 US calibration."),
        "params": [
            {"dot_path": "macro.risk_free_rate",
             "label": "Risk-free rate (Rf)",
             "description": "US 10-year Treasury rate at the time of analysis.",
             "kind": "slider", "min": 0.0, "max": 0.15, "step": 0.0025,
             "format": "%.4f"},
            {"dot_path": "macro.equity_risk_premium",
             "label": "Equity risk premium (ERP)",
             "description": "Damodaran's implied ERP for the analysis date.",
             "kind": "slider", "min": 0.0, "max": 0.20, "step": 0.005,
             "format": "%.3f"},
            {"dot_path": "macro.terminal_growth_rate",
             "label": "Terminal growth rate (g)",
             "description": "Long-run nominal growth in the Gordon perpetuity.",
             "kind": "slider", "min": 0.0, "max": 0.08, "step": 0.0025,
             "format": "%.4f"},
        ],
    },

    # ======================================================================
    # 8 — Jurisdictional fiscal parameters (Section 7)
    # ======================================================================
    {
        "id": "jurisdictions",
        "label": "🌎 Jurisdictional fiscal structure (Section 7)",
        "intro": (
            "Per-country fiscal-accounting parameters: how much each dollar "
            "of base salary actually costs the employer, how much it costs "
            "to fire someone, and how much overhead foreign AI services "
            "attract. Drives Figures 11, 12, 13 and the counterintuitive "
            "ordering of Section 7.3."),
        "params": [
            item for country, country_label in [
                ("brazil", "Brazil (CLT)"),
                ("france", "France (CDI)"),
                ("united_states", "United States (W-2)"),
            ] for item in [
                {
                    "dot_path": f"jurisdictions.defaults.{country}.labor_cost_multiplier",
                    "label": f"{country_label} — labor cost multiplier",
                    "description": (
                        "Total cost of labor as a multiple of the base "
                        "salary, including all employer charges."),
                    "kind": "slider", "min": 1.0, "max": 2.5, "step": 0.01,
                    "format": "%.2f",
                },
                {
                    "dot_path": f"jurisdictions.defaults.{country}.termination_cost_fraction",
                    "label": f"{country_label} — termination cost (fraction of annual salary)",
                    "description": (
                        "Indemnity + notice + rescission cost as a fraction "
                        "of one year's base salary."),
                    "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
                    "format": "%.2f",
                },
                {
                    "dot_path": f"jurisdictions.defaults.{country}.ai_service_overhead",
                    "label": f"{country_label} — AI service overhead",
                    "description": (
                        "Effective cost multiplier on imported AI services "
                        "(IRRF + CIDE in Brazil; TVA in France; domestic in US)."),
                    "kind": "slider", "min": 1.0, "max": 2.0, "step": 0.01,
                    "format": "%.2f",
                },
                {
                    "dot_path": f"jurisdictions.defaults.{country}.vendor_risk_wacc_premium",
                    "label": f"{country_label} — vendor-risk WACC premium",
                    "description": (
                        "Premium added to WACC to reflect dependency on "
                        "foreign frontier AI providers."),
                    "kind": "slider", "min": 0.0, "max": 0.05, "step": 0.001,
                    "format": "%.3f",
                },
            ]
        ],
    },

    # ======================================================================
    # 9 — Migration dynamics (Section 7.5)
    # ======================================================================
    {
        "id": "migration",
        "label": "⏱ Migration dynamics (Section 7.5)",
        "intro": (
            "Quarter-by-quarter parameters of the AI-orchestrator migration "
            "model: how long the assessment phase lasts, how many engineers "
            "one orchestrator supervises, how steep the learning curve is, "
            "and how much a loaded SWE costs per country. Drives Figures "
            "21, 22, 23."),
        "params": [
            {"dot_path": "migration_dynamics.assessment_months",
             "label": "Assessment phase length (months)",
             "description": "Months between the migration decision and pilot start.",
             "kind": "slider", "min": 0.0, "max": 24.0, "step": 1.0, "format": "%.0f"},
            {"dot_path": "migration_dynamics.orchestrator_ratio",
             "label": "Engineers per AI orchestrator",
             "description": "How many remaining engineers each orchestrator supervises.",
             "kind": "slider", "min": 1.0, "max": 50.0, "step": 1.0, "format": "%.0f"},
            {"dot_path": "migration_dynamics.orchestrator_premium_pct",
             "label": "Orchestrator compensation premium over senior SWE",
             "description": "Extra compensation for the orchestrator role.",
             "kind": "slider", "min": 0.0, "max": 0.50, "step": 0.01, "format": "%.2f"},
            {"dot_path": "migration_dynamics.dual_operation_overhead_quarters",
             "label": "Dual-operation overhead (quarters)",
             "description": "Quarters during which legacy and AI operations run in parallel.",
             "kind": "slider", "min": 0.0, "max": 8.0, "step": 1.0, "format": "%.0f"},
            {"dot_path": "migration_dynamics.retention_bonus_quarters",
             "label": "Retention bonus duration (quarters)",
             "description": "Quarters that retention bonuses are paid to remaining staff.",
             "kind": "slider", "min": 0.0, "max": 8.0, "step": 1.0, "format": "%.0f"},
            {"dot_path": "migration_dynamics.retention_bonus_fraction",
             "label": "Retention bonus (fraction of salary)",
             "description": "Bonus amount as a fraction of base salary.",
             "kind": "slider", "min": 0.0, "max": 0.50, "step": 0.01, "format": "%.2f"},
            {"dot_path": "migration_dynamics.ai_tooling_cost_per_dev_usd_year",
             "label": "AI tooling cost per developer (USD/year)",
             "description": "Annual cost of AI tooling licences per remaining engineer.",
             "kind": "number", "min": 0.0, "max": 100000.0,
             "step": 1000.0, "format": "%.0f"},
            *[{
                "dot_path": f"migration_dynamics.loaded_swe_cost_usd_year.{c}",
                "label": f"Senior SWE loaded cost — {label} (USD/year)",
                "description": (
                    "Total cost per senior software engineer in this "
                    "jurisdiction, including employer charges."),
                "kind": "number", "min": 0.0, "max": 1e6,
                "step": 5000.0, "format": "%.0f",
            } for c, label in [("brazil", "Brazil"),
                                 ("france", "France"),
                                 ("united_states", "United States")]],
        ],
    },

    # ======================================================================
    # 10 — Case-study firms (Appendix E)
    # ======================================================================
    {
        "id": "firms",
        "label": "🏢 Case-study firms — NeuroCertify & DataFlow Pro",
        "intro": (
            "Composition and trajectory parameters for the two reference "
            "firms. NeuroCertify is deep-tech, regulated, Layer-6-rich. "
            "DataFlow Pro is commoditizing-tech, Layer-4-heavy. Edit these "
            "to position your own firm on the fragility map and to drive "
            "Figures 22, 23, 31–35, A.1, A.3."),
        "params": [
            # NeuroCertify layer exposure (Layer 6 lives in the 🎯 Headline
            # group above to avoid a duplicate-widget conflict).
            *[{
                "dot_path": f"case_studies_dynamic.neurocertify.layer_exposure.{k}",
                "label": f"NeuroCertify — {label}",
                "description": "Fraction of firm value located in this layer.",
                "kind": "slider", "min": 0.0, "max": 0.7, "step": 0.01,
                "format": "%.2f",
            } for k, label in [
                ("layer_3_capability", "Layer 3 (capability)"),
                ("layer_4_codified", "Layer 4 (codified)"),
                ("layer_5_judgment", "Layer 5 (judgment)"),
            ]],
            # DataFlow layer exposure
            *[{
                "dot_path": f"case_studies_dynamic.dataflow_pro.layer_exposure.{k}",
                "label": f"DataFlow Pro — {label}",
                "description": "Fraction of firm value located in this layer.",
                "kind": "slider", "min": 0.0, "max": 0.7, "step": 0.01,
                "format": "%.2f",
            } for k, label in [
                ("layer_3_capability", "Layer 3 (capability)"),
                ("layer_4_codified", "Layer 4 (codified)"),
                ("layer_5_judgment", "Layer 5 (judgment)"),
                ("layer_6_institutional", "Layer 6 (institutional)"),
            ]],
            {
                "dot_path": "case_studies_dynamic.neurocertify.ai_substitution_potential",
                "label": "NeuroCertify — AI substitution potential",
                "description": (
                    "How much of NeuroCertify's Layer-4 work AI can substitute."),
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
                "format": "%.2f",
            },
            {
                "dot_path": "case_studies_dynamic.dataflow_pro.ai_substitution_potential",
                "label": "DataFlow Pro — AI substitution potential",
                "description": "Same metric for the commoditizing firm.",
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
                "format": "%.2f",
            },
        ],
    },

    # ======================================================================
    # 11 — Streaming case (Appendix D)
    # ======================================================================
    {
        "id": "streaming",
        "label": "🎬 Streaming case (Appendix D)",
        "intro": (
            "Mature streaming incumbent vs IA-native entrant. The plan "
            "price, cost decomposition (7 buckets), and three substitution "
            "scenarios drive the price-decomposition figure (24) and the "
            "cross-jurisdictional comparison (25)."),
        "params": [
            {"dot_path": "streaming_case.standard_plan_price_usd_monthly",
             "label": "Standard plan price (USD / month)",
             "description": "Headline subscription price the entrant compresses.",
             "kind": "slider", "min": 5.0, "max": 30.0, "step": 0.5,
             "format": "%.2f"},
            {"dot_path": "streaming_case.engineers_count",
             "label": "Engineers headcount",
             "description": "Total engineering headcount before substitution.",
             "kind": "number", "min": 0, "max": 50000, "step": 100,
             "format": "%d"},
            {"dot_path": "streaming_case.support_agents_count",
             "label": "Support agents headcount",
             "description": "Customer-support headcount targeted by AI agents.",
             "kind": "number", "min": 0, "max": 20000, "step": 100,
             "format": "%d"},
            {"dot_path": "streaming_case.substitution_scenarios.conservative_pct",
             "label": "Conservative substitution",
             "description": "Substitution share in the conservative scenario.",
             "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
             "format": "%.2f"},
            {"dot_path": "streaming_case.substitution_scenarios.moderate_pct",
             "label": "Moderate substitution",
             "description": "Substitution share in the moderate scenario.",
             "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
             "format": "%.2f"},
            {"dot_path": "streaming_case.substitution_scenarios.aggressive_pct",
             "label": "Aggressive substitution",
             "description": "Substitution share in the aggressive scenario.",
             "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
             "format": "%.2f"},
            {"dot_path": "streaming_case.cross_bloc_friction_pct",
             "label": "Cross-bloc friction",
             "description": "Friction added when the entrant operates across blocs.",
             "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
             "format": "%.2f"},
        ],
    },

    # ======================================================================
    # 12 — Fiscal blocs (Appendix D.6)
    # ======================================================================
    {
        "id": "fiscal_blocs",
        "label": "🏛 Fiscal blocs (Appendix D.6)",
        "intro": (
            "5-year fiscal-impact projection across the three jurisdictions. "
            "Corporate tax rates and effective employer charges combine "
            "with transfer-pricing shares to produce the asymmetric impact "
            "of Figure 30."),
        "params": [
            *[{
                "dot_path": f"fiscal_blocs.corporate_tax_rate.{c}",
                "label": f"Corporate tax rate — {label}",
                "description": "Effective corporate tax rate on profits.",
                "kind": "slider", "min": 0.0, "max": 0.60, "step": 0.01,
                "format": "%.2f",
            } for c, label in [("brazil", "Brazil"),
                                 ("france", "France"),
                                 ("united_states", "United States")]],
            *[{
                "dot_path": f"fiscal_blocs.employer_charges_effective_pct.{c}",
                "label": f"Effective employer charges — {label}",
                "description": (
                    "Charges effectively lost to the state when the firm "
                    "switches from human labour to AI tooling."),
                "kind": "slider", "min": 0.0, "max": 0.70, "step": 0.01,
                "format": "%.2f",
            } for c, label in [("brazil", "Brazil"),
                                 ("france", "France"),
                                 ("united_states", "United States")]],
            {"dot_path": "fiscal_blocs.transfer_pricing_parent_share",
             "label": "Transfer-pricing parent share",
             "description": "Share of value attributed to the parent jurisdiction.",
             "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
             "format": "%.2f"},
            {"dot_path": "fiscal_blocs.transfer_pricing_subsidiary_share",
             "label": "Transfer-pricing subsidiary share",
             "description": "Share retained by the subsidiary jurisdiction.",
             "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
             "format": "%.2f"},
            {"dot_path": "fiscal_blocs.sector_workforce_multiplier",
             "label": "Sector workforce multiplier",
             "description": (
                 "Ratio of the broader affected workforce to the firm's "
                 "directly substituted headcount."),
             "kind": "slider", "min": 1.0, "max": 30.0, "step": 1.0,
             "format": "%.0f"},
        ],
    },

    # ======================================================================
    # 13 — Fragility map (Appendix E.5)
    # ======================================================================
    {
        "id": "fragility",
        "label": "🗺 Fragility map (Appendix E.5)",
        "intro": (
            "Two-line formula at the heart of the fragility map: "
            "index = Layer-4 share − coefficient × Layer-6 share. The "
            "coefficient sets how much institutional defensibility offsets "
            "Layer-4 erosion. Drives Figure 35."),
        "params": [
            {"dot_path": "fragility_index.l6_coefficient",
             "label": "Layer-6 coefficient",
             "description": (
                 "Multiplier on Layer-6 share when computing the fragility "
                 "index. Higher = stronger protection from institutional moat."),
             "kind": "slider", "min": 0.0, "max": 3.0, "step": 0.1,
             "format": "%.1f"},
            {"dot_path": "fragility_index.resilient_threshold",
             "label": "Resilient-zone upper threshold",
             "description": "Fragility index below this value classifies as resilient.",
             "kind": "slider", "min": -1.0, "max": 0.0, "step": 0.01,
             "format": "%.2f"},
            {"dot_path": "fragility_index.fragile_threshold",
             "label": "Fragile-zone lower threshold",
             "description": "Fragility index above this value classifies as fragile.",
             "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
             "format": "%.2f"},
        ],
    },

    # ======================================================================
    # 14 — Distributional & epistemic (Appendix G)
    # ======================================================================
    {
        "id": "distributional",
        "label": "⚖️ Distributional & epistemic (Appendix G)",
        "intro": (
            "Two structural thresholds for AI migration in regulated small "
            "firms: the economic floor (orchestrator overhead) and the "
            "compliance floor (orchestrator + XAI infrastructure). Drives "
            "Figures 40, 41."),
        "params": [
            {"dot_path": "distributional.double_threshold.gross_saving_per_eng_usd_year",
             "label": "Gross saving per engineer (USD/year)",
             "description": (
                 "Annual savings per substituted engineer in an institution-"
                 "dominant profile."),
             "kind": "number", "min": 0.0, "max": 500000.0,
             "step": 1000.0, "format": "%.0f"},
            {"dot_path": "distributional.double_threshold.orchestrator_overhead_floor_usd",
             "label": "Orchestrator overhead floor (USD/year)",
             "description": "Minimum annual cost of running an AI orchestration team.",
             "kind": "number", "min": 0.0, "max": 2_000_000.0,
             "step": 10_000.0, "format": "%.0f"},
            {"dot_path": "distributional.double_threshold.xai_infrastructure_floor_usd",
             "label": "XAI infrastructure floor (USD/year)",
             "description": (
                 "Minimum cost of the explainability infrastructure required "
                 "for regulatory compliance."),
             "kind": "number", "min": 0.0, "max": 2_000_000.0,
             "step": 10_000.0, "format": "%.0f"},
            *[{
                "dot_path": f"distributional.xai_capacity_gap.bloc_a_growth_factor.{k}",
                "label": f"Bloc A growth factor — {label}",
                "description": "Annual compounding factor for Bloc A under this K7 regime.",
                "kind": "slider", "min": 1.0, "max": 1.10, "step": 0.001,
                "format": "%.3f",
            } for k, label in [("k_1_0", "K7=1.0"),
                                 ("k_0_7", "K7=0.7"),
                                 ("k_0_45", "K7=0.45")]],
            *[{
                "dot_path": f"distributional.xai_capacity_gap.bloc_b_growth_factor.{k}",
                "label": f"Bloc B growth factor — {label}",
                "description": "Annual compounding factor for Bloc B under this K7 regime.",
                "kind": "slider", "min": 1.0, "max": 1.10, "step": 0.001,
                "format": "%.3f",
            } for k, label in [("k_1_0", "K7=1.0"),
                                 ("k_0_7", "K7=0.7"),
                                 ("k_0_45", "K7=0.45")]],
            {
                "dot_path": "distributional.double_threshold.institution_profile.layer4_share",
                "label": "Institution-dominant firm — Layer 4 share",
                "description": (
                    "Profile of the regulated small firm used in the double-"
                    "threshold figure. Lower Layer-4 share = harder to clear "
                    "the economic threshold."),
                "kind": "slider", "min": 0.0, "max": 0.6, "step": 0.01,
                "format": "%.2f",
            },
            {
                "dot_path": "distributional.double_threshold.institution_profile.ai_substitution_potential",
                "label": "Institution-dominant firm — AI substitution potential",
                "description": "AI substitution that the same profile can realise.",
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
                "format": "%.2f",
            },
        ],
    },

    # ======================================================================
    # 15 — Startup economics (Section 6)
    # ======================================================================
    {
        "id": "startup_economics",
        "label": "🚀 Startup economics (Section 6)",
        "intro": (
            "Headline operating economics of the reference startup used "
            "throughout Section 6: initial team and runway, burn per "
            "engineer, growth assumptions, and the unit economics that "
            "feed every valuation method (Damodaran, comparables, Berkus, "
            "VC method)."),
        "params": [
            {"dot_path": "startup.initial_team_size",
             "label": "Initial team size",
             "description": "Founding engineering headcount at T0.",
             "kind": "number", "min": 1, "max": 200, "step": 1, "format": "%d"},
            {"dot_path": "startup.initial_runway_months",
             "label": "Initial runway (months)",
             "description": "Months of cash on hand at founding.",
             "kind": "slider", "min": 0.0, "max": 36.0, "step": 1.0,
             "format": "%.0f"},
            {"dot_path": "startup.monthly_burn_per_engineer_usd",
             "label": "Monthly burn per engineer (USD)",
             "description": "Fully-loaded monthly cost of one engineer.",
             "kind": "number", "min": 0.0, "max": 50_000.0, "step": 500.0,
             "format": "%.0f"},
            {"dot_path": "startup.trl_initial",
             "label": "Initial TRL",
             "description": "Technology Readiness Level at T0 (1–9).",
             "kind": "number", "min": 1, "max": 9, "step": 1, "format": "%d"},
            {"dot_path": "startup.trl_target",
             "label": "Target TRL at exit",
             "description": "TRL achieved by the end of the projection horizon.",
             "kind": "number", "min": 1, "max": 9, "step": 1, "format": "%d"},
            {"dot_path": "startup.cac_usd",
             "label": "Customer Acquisition Cost (USD)",
             "description": "Sales + marketing cost per acquired customer.",
             "kind": "number", "min": 0.0, "max": 100_000.0, "step": 500.0,
             "format": "%.0f"},
            {"dot_path": "startup.ltv_usd",
             "label": "Lifetime Value (USD)",
             "description": "Discounted gross profit per customer over its lifecycle.",
             "kind": "number", "min": 0.0, "max": 500_000.0, "step": 1_000.0,
             "format": "%.0f"},
            {"dot_path": "startup.churn_monthly",
             "label": "Monthly churn",
             "description": "Fraction of customers lost per month.",
             "kind": "slider", "min": 0.0, "max": 0.20, "step": 0.005,
             "format": "%.3f"},
            {"dot_path": "startup.market_size_usd",
             "label": "Addressable market (USD)",
             "description": "Total addressable market used to bound the VC valuation method.",
             "kind": "number", "min": 0.0, "max": 1e12, "step": 1e8,
             "format": "%.0f"},
            {"dot_path": "startup.growth.base_saas_growth_rate",
             "label": "Base SaaS growth rate (monthly)",
             "description": "Steady-state monthly ARR growth in the SaaS phase.",
             "kind": "slider", "min": 0.0, "max": 0.40, "step": 0.01,
             "format": "%.2f"},
            {"dot_path": "startup.growth.saas_projection_growth_rate",
             "label": "SaaS projection growth (annual)",
             "description": "Annualised growth used by the projection module.",
             "kind": "slider", "min": 1.0, "max": 3.0, "step": 0.05,
             "format": "%.2f"},
        ],
    },

    # ======================================================================
    # 16 — Investor framework (Section 6)
    # ======================================================================
    {
        "id": "investor",
        "label": "👨‍💼 Investor framework (Section 6)",
        "intro": (
            "Investor decision and thesis parameters. ``target_irr`` and "
            "``hold_period`` drive the VC-method valuation; "
            "``decision_threshold`` is the score above which the AI-aware "
            "thesis approves a deal."),
        "params": [
            {"dot_path": "investor.target_irr",
             "label": "Target IRR",
             "description": "Required internal rate of return for an investor go-decision.",
             "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
             "format": "%.2f"},
            {"dot_path": "investor.hold_period_years",
             "label": "Hold period (years)",
             "description": "Investment horizon for the VC-method valuation.",
             "kind": "number", "min": 1, "max": 15, "step": 1, "format": "%d"},
            {"dot_path": "investor.default_dilution_per_round",
             "label": "Default dilution per round",
             "description": "Equity dilution assumed at each financing event.",
             "kind": "slider", "min": 0.0, "max": 0.50, "step": 0.01,
             "format": "%.2f"},
            {"dot_path": "investor.decision_threshold",
             "label": "Decision threshold (thesis score)",
             "description": (
                 "Composite thesis score above which an AI-aware investor "
                 "approves a deal."),
             "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
             "format": "%.2f"},
            {"dot_path": "investor.thesis_weights_ai_aware.hypothesis_quality",
             "label": "AI-aware weight — Hypothesis quality",
             "description": "Weight on Layer-5 hypothesis quality in the AI-aware thesis.",
             "kind": "slider", "min": 0.0, "max": 0.6, "step": 0.05,
             "format": "%.2f"},
            {"dot_path": "investor.thesis_weights_ai_aware.institutional_embedding",
             "label": "AI-aware weight — Institutional embedding",
             "description": "Weight on Layer-6 institutional embedding (regulatory/accreditation).",
             "kind": "slider", "min": 0.0, "max": 0.6, "step": 0.05,
             "format": "%.2f"},
        ],
    },

    # ======================================================================
    # 17 — Hype cycle (Section 6.5)
    # ======================================================================
    {
        "id": "hype_cycle",
        "label": "📈 Hype cycle — classical and post-GenAI (Section 6.5)",
        "intro": (
            "Quarterly coordinates of the two Hype-Cycle curves. The "
            "classical curve has a single valley; the post-GenAI curve "
            "exhibits the new commoditization valley around quarters "
            "14–22, the central observation of Section 6.5. Drives "
            "Figure 4."),
        "params": [
            # Classical curve
            *[{
                "dot_path": f"hype_cycle.classical.{k}",
                "label": f"Classical — {label}",
                "description": "Coordinate of the classical Gartner Hype Cycle.",
                "kind": "number", "min": 0, "max": 200, "step": 1,
                "format": "%d",
            } for k, label in [
                ("peak_quarter", "peak quarter"),
                ("trough_quarter", "trough quarter"),
                ("plateau_quarter", "plateau quarter"),
                ("peak_height", "peak height"),
                ("trough_height", "trough height"),
                ("plateau_height", "plateau height"),
            ]],
            # Post-GenAI curve
            *[{
                "dot_path": f"hype_cycle.post_genai.{k}",
                "label": f"Post-GenAI — {label}",
                "description": "Coordinate of the post-AI double-valley curve.",
                "kind": "number", "min": 0, "max": 200, "step": 1,
                "format": "%d",
            } for k, label in [
                ("peak_quarter", "peak quarter"),
                ("trough_quarter", "first trough quarter"),
                ("trough_height", "first trough height"),
                ("second_peak_quarter", "second peak quarter"),
                ("second_peak_height", "second peak height"),
                ("commoditization_valley_quarter", "commoditization-valley quarter"),
                ("commoditization_valley_height", "commoditization-valley height"),
                ("plateau_quarter", "plateau quarter"),
                ("plateau_height", "plateau height"),
            ]],
        ],
    },

    # ======================================================================
    # 18 — Death valley dynamics (Section 6.5)
    # ======================================================================
    {
        "id": "death_valley",
        "label": "💀 Death-valley dynamics (Section 6.5)",
        "intro": (
            "Cash-trajectory parameters of the post-AI double valley: "
            "burn rates, refinancing event, revenue ramp, and margin "
            "compression after the second valley. Drives Figure 5."),
        "params": [
            {"dot_path": "death_valley.post_genai.initial_cash_usd",
             "label": "Initial cash (USD)",
             "description": "Founding cash balance.",
             "kind": "number", "min": 0.0, "max": 50e6, "step": 100_000.0,
             "format": "%.0f"},
            {"dot_path": "death_valley.post_genai.monthly_burn_usd_initial",
             "label": "Initial monthly burn (USD)",
             "description": "Burn rate at founding before any funding event.",
             "kind": "number", "min": 0.0, "max": 5e6, "step": 5_000.0,
             "format": "%.0f"},
            {"dot_path": "death_valley.post_genai.refinancing_event_month",
             "label": "Refinancing event month",
             "description": "Month at which the Series A (or equivalent) injection occurs.",
             "kind": "number", "min": 0, "max": 60, "step": 1, "format": "%d"},
            {"dot_path": "death_valley.post_genai.refinancing_amount_usd",
             "label": "Refinancing amount (USD)",
             "description": "Cash raised at the refinancing event.",
             "kind": "number", "min": 0.0, "max": 100e6, "step": 100_000.0,
             "format": "%.0f"},
            {"dot_path": "death_valley.post_genai.peak_revenue_usd_per_month",
             "label": "Peak monthly revenue (USD)",
             "description": "Revenue ceiling reached after the second valley.",
             "kind": "number", "min": 0.0, "max": 10e6, "step": 10_000.0,
             "format": "%.0f"},
            {"dot_path": "death_valley.post_genai.margin_compression_factor",
             "label": "Margin compression after second valley",
             "description": (
                 "Fraction of margin lost to commoditization in the post-"
                 "second-valley regime."),
             "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.05,
             "format": "%.2f"},
            {"dot_path": "death_valley.post_genai.commoditization_valley_start_month",
             "label": "Commoditization valley — start month",
             "description": "Onset of the second (commoditization) valley.",
             "kind": "number", "min": 0, "max": 60, "step": 1, "format": "%d"},
            {"dot_path": "death_valley.post_genai.commoditization_valley_end_month",
             "label": "Commoditization valley — end month",
             "description": "End of the second valley.",
             "kind": "number", "min": 0, "max": 60, "step": 1, "format": "%d"},
        ],
    },

    # ======================================================================
    # 19 — Streaming cost decomposition (Appendix D)
    # ======================================================================
    {
        "id": "streaming_costs",
        "label": "🎬 Streaming cost decomposition (Appendix D)",
        "intro": (
            "Seven-component cost decomposition of the streaming incumbent's "
            "plan price. The sum (excluding operating margin) defines the "
            "stack the IA-native entrant compresses. Drives Figure 24."),
        "params": [
            *[{
                "dot_path": f"streaming_case.cost_decomposition_pct.{k}",
                "label": f"{label} (% of price)",
                "description": "Fraction of the standard plan price attributed to this cost component.",
                "kind": "slider", "min": 0.0, "max": 1.0, "step": 0.01,
                "format": "%.2f",
            } for k, label in [
                ("content_licensing_production", "Content licensing & production"),
                ("engineering_technology", "Engineering & technology"),
                ("customer_support", "Customer support"),
                ("cloud_cdn_infrastructure", "Cloud & CDN infrastructure"),
                ("marketing", "Marketing"),
                ("general_administrative", "General & administrative"),
                ("operating_margin", "Operating margin"),
            ]],
        ],
    },

    # ======================================================================
    # 20 — Upstream chain — exposure matrix (Appendix F.2)
    # ======================================================================
    {
        "id": "upstream",
        "label": "🔗 Upstream chain — exposure matrix (Appendix F.2)",
        "intro": (
            "How exposed each of the seven upstream AI value-chain "
            "categories is to each of the seven layers. 0 = not exposed; "
            "3 = predominant exposure. Drives Figure 37."),
        "params": [
            item for cat_key, cat_label in [
                ("foundry_pure_plays", "Foundry pure-plays"),
                ("training_silicon", "Training silicon"),
                ("inference_edge_silicon", "Inference & edge silicon"),
                ("memory_hbm", "Memory & HBM"),
                ("hyperscalers", "Hyperscalers"),
                ("frontier_labs", "Frontier labs"),
                ("ai_tooling_platforms", "AI tooling platforms"),
            ] for item in [{
                "dot_path": f"upstream_chain.categories.{cat_key}.exposure.{layer_key}",
                "label": f"{cat_label} — {layer_label}",
                "description": (
                    f"Exposure level (0..3) of {cat_label} to {layer_label}."),
                "kind": "slider", "min": 0, "max": 3, "step": 1, "format": "%d",
            } for layer_key, layer_label in [
                ("L1_train", "L1 training compute"),
                ("L1_infer", "L1 inference compute"),
                ("L2", "L2 foundation models"),
                ("L3", "L3 capability access"),
                ("L4", "L4 codified synthesis"),
                ("L5", "L5 judgment"),
                ("L6", "L6 institutional"),
            ]]
        ],
    },
]


def all_dot_paths() -> List[str]:
    """Flat list of every dot-path exposed in the curated set."""
    out: List[str] = []
    for group in LEVER_GROUPS:
        for param in group["params"]:
            out.append(param["dot_path"])
    return out
