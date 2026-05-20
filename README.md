# commoditization-stack-simulation

**Computational appendix to:** *The Cost Gradient of the Build — How Differential Commoditization Reshapes Entrepreneurship and Valuation: A Layer-Decomposed Risk Premium for the Post-AI Firm* (de Miranda Neto, 2026, working paper).

This repository contains the simulation environment that materializes the seven-layer framework of the knowledge-production stack proposed in the paper, together with the four interlocking contributions developed from it: (a) a reformulated entrepreneurship toolkit anchored on the Minimum Viable Hypothesis rather than the Minimum Viable Product (Section 5 of the paper); (b) an inverted reading of Damodaran's key-person discount (Section 6); (c) the accounting-substitution problem and its jurisdictionally-structured analysis under Brazil (CLT), France (CDI), and the United States (W-2) (Section 7); (d) a layered theory of post-AI defensibility (Section 8). The framework is modulated by a tentative seventh layer — the cross-border knowledge regime, captured by a knowledge-integration coefficient K7 — that modulates the velocities of Layers 3, 4, and 5 in response to the trajectory of scientific decoupling and data-sovereignty fragmentation (Section 4.1 of the paper).

The repository allows any user — researcher, practitioner, firm strategist, policy analyst, student — to: (i) replicate the deterministic illustrations in the paper, (ii) run Monte Carlo experiments under modified parameter ranges, (iii) modify the layer specifications themselves, (iv) plug new sectors or new parameter regimes into the same framework, (v) re-run the jurisdictional analysis with substituted fiscal parameters for any jurisdiction the user wishes to study, and (vi) vary the knowledge-integration coefficient K7 and observe the implied sensitivity of the inversion premium and the substitutability trajectories.

> **Status of evidence.** The simulations in this repository are computational demonstrations of the *quantitative implications* of the framework under specified parameter ranges. They are not, and should not be cited as, empirical proof of any tested causal claim. Their epistemic role is to expose the internal consistency of the framework and to support sensitivity analysis. All parameters are documented and editable.

> **Status of Layer 7 (the K7 coefficient).** The seventh layer is offered as a tentative hypothesis rather than an empirically established regularity. The values of K7 used in the simulations (K7 = 1.0 baseline, K7 = 0.7 illustrative for 2026, K7 = 0.4 fragmented counterfactual for 2030) are illustrative, not estimated. The simulation lets the user vary K7 freely in [0, 1] and observe the implied conditional consequences for Layers 3, 4, and 5.

> **K7 is a descriptive indicator, not a policy lever.** A clarification helpful to users contemplating policy applications: K7 describes the state of the cross-border knowledge regime as it is *observed*. It is not a policy variable that a state can directly set. State actions — export controls on advanced semiconductors, sovereign-AI initiatives, data-localization mandates, foreign investment screening, restrictions on scientific co-authorship — *alter* K7. The reverse direction does not hold: declaring a target K7 does not by itself preserve employment or alter the operational reality of cross-border knowledge integration. The bidirectional relationship between K7 and labor-market outcomes is itself non-trivial: lower K7 mechanically slows Layer-4 substitution within a bloc (which can preserve specific local jobs in the short run), but the macroeconomic consequences of fragmentation, documented in the sovereign-AI literature, run in the opposite direction. The simulator exposes the within-bloc channel and is open for users wishing to extend it with macroeconomic channels.

## What this code does

The repository materializes the full framework of the paper across body sections (1–11) and Appendices A–H.

1. **Seven-layer framework** (`src/stack_layers.py`): all seven layers in a single module, with Layer 7 as `KnowledgeRegimeParameters` integrating the cross-border knowledge regime, `apply_knowledge_regime_modulation()`, and `crossborder_acquisition_friction()` functions.
2. **Deep-tech startup model** (`src/startup.py`): team composition, burn rate, runway, TRL, layer-by-layer mapping of where the firm's labor sits.
3. **Venture-capital investor model** (`src/investor.py`): the four canonical valuation methods (Berkus, VC method, comparable multiples, narrative-anchored DCF), with the inverted key-person discount.
4. **Layer-decomposed firm-specific risk premium and layered DCF** (`src/valuation.py`, `src/valuation_layered.py`): the generalization of Damodaran's key-person discount from a scalar to a vector of signed, per-layer coefficients (Eq C.1) and the TRL-modulated discount-rate trajectory (Appendix A).
5. **Phase-conditional reformulation of CAPM, WACC, EVA, ROI, Gordon perpetuity** (`src/valuation_two_phase.py`): Eqs B.3–B.11 under the post-AI double-valley dynamic (Appendix B).
6. **Dual-channel correction (B.2.6)** (`src/dual_channel.py`, `src/dual_channel_mc.py`): the partition of the second-valley risk effect into systematic and idiosyncratic components (Eq B.12), the adjusted Layer-4 coefficient (Eq B.13), the phase-conditional revenue-retreat factor `lambda_2V` (Eq B.14), the dual-channel enterprise value V0_dualchannel (Eq B.15), the unified-lambda variant, and the unified Monte Carlo over the four valuation paths.
7. **Reformulated Gartner Hype Cycle and valley-of-death** (`src/hype_cycle.py`, `src/death_valley.py`): two distinct valleys under post-AI conditions.
8. **Jurisdictional analysis** (`src/jurisdictional.py`): the accounting-substitution problem under Brazil (CLT), France (CDI), and the United States (W-2), with `compute_accounting_substitution()` and `jurisdictional_inverted_discount()`; extensible to additional jurisdictions by editing `JURISDICTION_DEFAULTS`.
9. **Migration dynamics and AI orchestrator function (Section 7.5)** (`src/migration_dynamics.py`): assessment-and-pilot phase, transition overheads, learning curve, permanent orchestrator overhead, break-even from the migration decision, and the team-size adoption threshold of Appendix E.2.
10. **Streaming case and fiscal blocs (Appendix D)** (`src/streaming_case.py`, `src/fiscal_blocs.py`): incumbent vs entrant price decomposition under three substitution scenarios, cross-jurisdictional matrix, and the five-year fiscal-impact projection across Brazil, France, and the United States.
11. **Dynamic case companies and fragility map (Appendix E)** (`src/fragility.py`): the NeuroCertify and DataFlow Pro trajectories across funding stages, the phase-conditional risk curves, founder dilution, investor multiple, and the fragility map across the seven-layer framework.
12. **Upstream AI value chain (Appendix F)** (`src/upstream_chain.py`): mapping of seven categories of upstream firms onto the layered framework, capex sensitivity to financing tightness, adoption-threshold curve, and the K7 inversion-premium sensitivity.
13. **Distributional, stewardship, and epistemic analysis (Appendix G)** (`src/distributional.py`): the double-threshold for AI migration (economic + XAI compliance), the XAI-capacity-gap accumulation under three K7 regimes, and the structural materialization of the questions raised by Appendix G.
14. **Multi-audience report generator** (`src/reporting.py`): the per-audience close of Section 11.1 — investor, founder, regulator, researcher, technologist, and journalist briefs constructed from a single shared computation.
15. **Empirical calibration scaffolding** (`src/calibration.py`): bootstrap-CI estimators for the dual-channel parameters from transaction observations, with explicit identifiability conditions; documented in `docs/empirical_calibration_program.md`.
16. **Simulation harness** (`src/simulation.py`): deterministic single-trajectory illustrations and Monte Carlo ensembles (10,000 runs by default; configurable).

## Quick start

```bash
git clone git@github.com:ademiran/commoditization-stack-simulation.git
cd commoditization-stack-simulation
python -m venv .venv && source .venv/bin/activate   # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Body figures (Sections 4–8)
python scripts/run_deterministic.py            # Figures 1, 2, 5, 6, 7
python scripts/run_layer7.py                   # Figures 3, 4 — K7 sensitivity
python scripts/run_jurisdictional.py           # Figures 8, 9, 10 — jurisdictional inversion
python scripts/run_section_7_5_migration.py    # Figures 11, 12, 13 — migration cash-flow trajectories
python scripts/run_monte_carlo.py              # Figure-grade Monte Carlo (10,000 runs)

# Appendix figures
python scripts/run_appendix_a.py               # Figures A.1–A.3 — layered DCF
python scripts/run_appendix_b.py               # Figures B.1–B.2 — phase-conditional CAPM/WACC/EVA
python scripts/run_b26_figures.py              # Figures B.3 / B.4 / B.5 — dual-channel correction (B.2.6)
python scripts/run_appendix_d.py               # Figures D.1–D.8 — streaming case + fiscal blocs
python scripts/run_appendix_e.py               # Figures E.1–E.5 — dynamic case companies + fragility map
python scripts/run_appendix_f.py               # Figures F.1–F.4 — upstream chain + structural sensitivities
python scripts/run_appendix_g.py               # Figures G.1–G.2 — double threshold + XAI-capacity gap

# Equations as PNGs + auxiliary scripts
python scripts/render_equations.py             # renders the equations of Appendices A, B (incl. B.12–B.15), C
python scripts/freeze_regression_baseline.py   # snapshots the canonical valuation paths to tests/baselines/
python scripts/calibration_demo.py             # demonstrates the bootstrap calibration of dual-channel params
python scripts/build_deployment_report.py      # one-shot report bundling all figures + numerical tables

jupyter notebook notebooks/                    # interactive exploration
```

## Production website (FastAPI + Next.js)

The repository ships with the foundation for a public-facing website:

- **Backend** ([`api/`](api/)) — FastAPI REST API exposing `src/` over
  44 endpoints under `/api/v1/`. Containerised for Cloud Run via the
  root [`Dockerfile`](Dockerfile). See [`docs/api.md`](docs/api.md) for
  the endpoint reference. Run locally: `python scripts/run_api.py`.
- **Frontend** ([`web/`](web/)) — Next.js 15 + Tailwind + shadcn/ui in
  Carta-style design system, with two modes (Explore the framework /
  Value your company) and a guided workflow with a jurisdiction gate.
  Deployable to Vercel out of the box. See [`web/README.md`](web/README.md).
- **CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) — runs
  pytest on the backend and `tsc --noEmit` + `next build` on the
  frontend.
- **GCP deployment** ([`cloudbuild.yaml`](cloudbuild.yaml)) — one-shot
  Cloud Build pipeline that pushes the API image to Artifact Registry
  and deploys to Cloud Run.

This stack replaces the legacy Streamlit app as the user-facing
deployment target for the public website. The Streamlit app (below) is
retained as an internal "lab" surface for parameter exploration.

## Interactive Streamlit UI (legacy / lab mode)

The repository ships with a complete Streamlit interface that exposes the full
framework in a navigable application with 18 tabs covering every section of the
paper:

- **Body**: Overview, Configuration, Seven Layers, Inverted Discount,
  Jurisdictional, Migration (Section 7.5), Hype Cycle, Research Levers,
  Company Valuation
- **Appendices**: Appendix A (layered DCF), Appendix B (phase-conditional +
  dual-channel B.2.6), Appendix D (streaming + fiscal blocs), Appendix E
  (dynamic case companies + fragility), Appendix F (upstream chain),
  Appendix G (distributional / stewardship / epistemic)
- **Reporting**: Multi-audience Reports, PDF Export, About

Global parameters (K₇, AI substitution potential, layer exposure, firm phase
β / D-E / Kd spreads, TRL trajectory, FCF, layer risk coefficients) are shared
across all tabs in a unified sidebar — adjusting K₇ once propagates to every
tab simultaneously.

```bash
streamlit run app/streamlit_app.py
```

The app opens at `http://localhost:8501` by default. Edits to YAML scenario
files in `config/scenarios/` propagate immediately on app restart.

## VSCode users

The repository includes a `.vscode/` configuration with launch tasks for each
script and for the Streamlit app. Open the folder in VSCode, install the
recommended extensions (Python, Pylance, Jupyter), select your Python
interpreter, and the Run/Debug menu will offer launch configurations for:
- Streamlit: app/streamlit_app.py
- Run: scripts/run_appendix_a.py (and b)
- Run: scripts/run_layer7.py
- Run: scripts/render_equations.py

The PNG figures generated above intentionally do not include the figure number in the image itself; the figure number is added by the paper's typesetting (in the caption underneath each figure), in line with academic-publishing convention.

## How to construct user-defined scenarios

The framework is built explicitly to permit users to construct their own scenarios. Five levels of modification, in increasing order of effort:

- **Level 1 — parameters only:** edit any of the YAML files in `config/scenarios/` (or copy one and modify). All numerical parameters used in the paper are exposed there.
- **Level 2 — new sector:** copy a scenario YAML, edit the sector-specific parameters, pass `--scenario <name>` to the run scripts.
- **Level 3 — new jurisdiction:** add a new entry to `JURISDICTION_DEFAULTS` in `src/jurisdictional.py` (with the local labor-cost multiplier, termination cost, import overhead, and salary base) and create a corresponding YAML scenario in `config/scenarios/`. The jurisdictional analysis runs unchanged.
- **Level 4 — new K7 trajectory or new bloc structure:** edit `KNOWLEDGE_REGIME_DEFAULTS` in `src/stack_layers.py` to add new regime points (different K7 values, different bloc assignments, different bias profiles). Re-run `scripts/run_layer7.py` to regenerate the Layer-7 figures and the K7-sensitivity table.
- **Level 5 — framework modification:** modify the layer definitions, velocities, valuation logic, or any other framework component in `src/`. The repository is designed so that framework modifications propagate automatically through the run scripts.

A "labor preservation scenario" example is provided in `config/scenarios/labor_preservation_K04.yaml` for users wishing to explore the within-bloc channel by which lower K7 mechanically slows Layer-4 substitution. See `docs/EXTENDING.md` for a complete walkthrough.

## Citation

**Paper:**
> de Miranda Neto, A. (2026). *The Cost Gradient of the Build — How Differential Commoditization Reshapes Entrepreneurship and Valuation: A Layer-Decomposed Risk Premium for the Post-AI Firm*. Working paper.

**Repository:**
> de Miranda Neto, A. (2026). *commoditization-stack-simulation* (v0.5) [Computer software]. GitHub.

A `CITATION.cff` file is provided so that GitHub's "Cite this repository" button produces a properly formatted citation automatically.

## License

MIT License (see `LICENSE`).

## Author

Arthur de Miranda Neto.
LinkedIn: https://www.linkedin.com/in/arthur-mneto/

Contributions, parameter critiques, jurisdictional case studies, alternative K7 trajectories, and pull requests are warmly welcome. The framework is intentionally open so that practitioners, firms, governments, and researchers can use, modify, extend, and improve it. The author hopes that the framework will serve as a starting point for a conversation, not as a finished account.

## Version history

- **v0.11** (May 2026): production website foundation — FastAPI backend at `api/` exposing the full `src/` core as 44 REST endpoints under `/api/v1/` (valuation / sensitivity / migration / jurisdictional / layers / appendices D-G / reports / meta); Next.js 15 + Tailwind + shadcn/ui frontend at `web/` with Carta-style design system, two-mode router (Explore framework vs Value your company), guided workflow with mandatory jurisdiction gate, full five-step valuation workflow (Jurisdictions → Company → Results → Sensitivity → Report); Recharts-based chart components (four-path bar, layers trajectory line, K7 sweep, fragility scatter); Dockerfile + cloudbuild.yaml + vercel.json + GitHub Actions CI; docs/api.md operational reference. 150/150 backend tests passing; backend live-tested.
- **v0.10** (May 2026): paper retitled to *The Cost Gradient of the Build — How Differential Commoditization Reshapes Entrepreneurship and Valuation: A Layer-Decomposed Risk Premium for the Post-AI Firm*; README, CITATION, About-tab realigned with the new title and subtitle; Appendix H (conceptual glossary, three sub-sections + H.4 note) materialized as `docs/glossary.md`; Appendix G supporting references annotated in `docs/appendix_g_references.md`; Mensch (2026) primary-source notes consolidated in `docs/mensch_2026_primary_source.md`; legacy `paper/The_End_of_the_Build.docx` renamed to `paper/The_Cost_Gradient_of_the_Build.docx`.
- **v0.9** (May 2026): subsection B.2.6 dual-channel correction — partition of the second-valley risk effect (Eq B.12), adjusted Layer-4 coefficient (Eq B.13), phase-conditional revenue-retreat factor `lambda_2V` (Eq B.14), dual-channel enterprise value `V0_dualchannel` (Eq B.15) added as a fourth valuation path (`src/dual_channel.py`); unified Monte Carlo over the four valuation paths (`src/dual_channel_mc.py`); unified-lambda variant retiring `delta_2V` documented in `docs/dual_channel_correction.md`; figures B.3, B.4, B.5 (six-bis geometry, risk partition, four-path reconciliation) added; substantive multi-audience reports (`src/reporting.py`) with macro-sensitivity grid; empirical-calibration scaffolding for the B.2.6 parameters (`src/calibration.py`) with bootstrap CIs and explicit identifiability conditions, documented in `docs/empirical_calibration_program.md`; Streamlit integration of B.2.6 and multi-audience reports; regression baselines frozen in `tests/baselines/`. Figure A.3 and B.1 captions cross-referenced to Figure B.5.
- **v0.8** (May 2026): UX polish — deployment report mode (Phase 1), unified palette + Sankey flow diagrams (Phase 2), named scenarios + Company Valuation workflow (Phase 3); horizontal tab strip restored after sidebar-nav experiment proved too destructive; internal file-path references scrubbed from user-facing strings.
- **v0.7** (May 2026): live figures for Appendices A/B in Streamlit; cleaner PDF and English-only UI; Research Levers tab with curated parameter chapter in the PDF export; multi-country comparative scenarios with cross-tab synchronization; live death-valley cash trajectory in the hype-cycle tab.
- **v0.6** (May 2026): full materialization of Sections 7.5, D, E, F, G — six new modules (`src/migration_dynamics.py`, `src/streaming_case.py`, `src/fiscal_blocs.py`, `src/fragility.py`, `src/upstream_chain.py`, `src/distributional.py`); five new scripts producing 21 paper figures; full Streamlit redesign mirroring the paper structure with 15 tabs (later 18 in v0.7+); live matplotlib figures across eight tabs reactive to parameter overrides; functional PDF export with all 41 figures.
- **v0.5** (May 2026): paper retitled *The Cost Gradient of the Build*; consolidated to four interlocking contributions; §9 rewritten with three blocks on AI as practitioner of science (Sakana AI Scientist; Google AI co-scientist); §10 entrepreneurship pedagogy removed; §11 fused with §12 into a single "Discussion and limitations" section. Figures regenerated without embedded figure-number titles. Added "K7 is a descriptive indicator, not a policy lever" clarification. Added `labor_preservation_K04.yaml` example scenario.
- **v0.4** (May 2026): introduction of the tentative seventh layer (cross-border knowledge regime) with the K7 coefficient, three reference regimes, and modulation of Layers 3, 4, and 5. New script `scripts/run_layer7.py` generates Figures 3 and 4.
- **v0.3** (May 2026): added Section 7 on the accounting-substitution problem and jurisdictional analysis under Brazil (CLT), France (CDI), and the United States (W-2). New module `src/jurisdictional.py`. Three new YAML scenarios.
- **v0.2** (May 2026): paper revised with three explicit contributions. Added Section 5.3 on the Minimum Viable Hypothesis. Added Section 7 on layered defensibility. Reference list corrected and expanded.
- **v0.1** (May 2026): initial release accompanying the working paper.
