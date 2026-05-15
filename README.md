# commoditization-stack-simulation

**Computational appendix to:** *The Cost Gradient of the Build: Generative AI and the Strategic Reinvention of Innovation-Driven Entrepreneurship* (de Miranda Neto, 2026, working paper).

This repository contains the simulation environment that materializes the seven-layer framework of the knowledge-production stack proposed in the paper, together with the four interlocking contributions developed from it: (a) a reformulated entrepreneurship toolkit anchored on the Minimum Viable Hypothesis rather than the Minimum Viable Product (Section 5 of the paper); (b) an inverted reading of Damodaran's key-person discount (Section 6); (c) the accounting-substitution problem and its jurisdictionally-structured analysis under Brazil (CLT), France (CDI), and the United States (W-2) (Section 7); (d) a layered theory of post-AI defensibility (Section 8). The framework is modulated by a tentative seventh layer — the cross-border knowledge regime, captured by a knowledge-integration coefficient K7 — that modulates the velocities of Layers 3, 4, and 5 in response to the trajectory of scientific decoupling and data-sovereignty fragmentation (Section 4.7 of the paper).

The repository allows any user — researcher, practitioner, firm strategist, policy analyst, student — to: (i) replicate the deterministic illustrations in the paper, (ii) run Monte Carlo experiments under modified parameter ranges, (iii) modify the layer specifications themselves, (iv) plug new sectors or new parameter regimes into the same framework, (v) re-run the jurisdictional analysis with substituted fiscal parameters for any jurisdiction the user wishes to study, and (vi) vary the knowledge-integration coefficient K7 and observe the implied sensitivity of the inversion premium and the substitutability trajectories.

> **Status of evidence.** The simulations in this repository are computational demonstrations of the *quantitative implications* of the framework under specified parameter ranges. They are not, and should not be cited as, empirical proof of any tested causal claim. Their epistemic role is to expose the internal consistency of the framework and to support sensitivity analysis. All parameters are documented and editable.

> **Status of Layer 7 (the K7 coefficient).** The seventh layer is offered as a tentative hypothesis rather than an empirically established regularity. The values of K7 used in the simulations (K7 = 1.0 baseline, K7 = 0.7 illustrative for 2026, K7 = 0.4 fragmented counterfactual for 2030) are illustrative, not estimated. The simulation lets the user vary K7 freely in [0, 1] and observe the implied conditional consequences for Layers 3, 4, and 5.

> **K7 is a descriptive indicator, not a policy lever.** A clarification helpful to users contemplating policy applications: K7 describes the state of the cross-border knowledge regime as it is *observed*. It is not a policy variable that a state can directly set. State actions — export controls on advanced semiconductors, sovereign-AI initiatives, data-localization mandates, foreign investment screening, restrictions on scientific co-authorship — *alter* K7. The reverse direction does not hold: declaring a target K7 does not by itself preserve employment or alter the operational reality of cross-border knowledge integration. The bidirectional relationship between K7 and labor-market outcomes is itself non-trivial: lower K7 mechanically slows Layer-4 substitution within a bloc (which can preserve specific local jobs in the short run), but the macroeconomic consequences of fragmentation, documented in the sovereign-AI literature, run in the opposite direction. The simulator exposes the within-bloc channel and is open for users wishing to extend it with macroeconomic channels.

## What this code does

1. **Seven-layer framework** (`src/stack_layers.py`): all seven layers in a single module, with Layer 7 as `KnowledgeRegimeParameters` integrating the cross-border knowledge regime.
2. **Deep-tech startup model** (`src/startup.py`): team composition, burn rate, runway, TRL, layer-by-layer mapping of where the firm's labor sits.
3. **Venture-capital investor model** (`src/investor.py`): the four canonical valuation methods (Berkus, VC method, comparable multiples, narrative-anchored DCF), with the inverted key-person discount mechanism.
4. **Reformulated Gartner Hype Cycle and valley-of-death** (`src/hype_cycle.py`, `src/death_valley.py`): two distinct valleys under post-AI conditions.
5. **Jurisdictional analysis module** (`src/jurisdictional.py`): the accounting-substitution problem under three reference regimes, with the `compute_accounting_substitution()` and `jurisdictional_inverted_discount()` functions; trivially extensible to additional jurisdictions by adding entries to `JURISDICTION_DEFAULTS`.
6. **Cross-border knowledge regime** (`src/stack_layers.py`): K7 coefficient, three reference regimes, `apply_knowledge_regime_modulation()`, and `crossborder_acquisition_friction()` functions.
7. **Simulation harness** (`src/simulation.py`): deterministic single-trajectory illustrations and Monte Carlo ensembles (10,000 runs by default; configurable).

## Quick start

```bash
git clone [GitHub TBD].git
cd commoditization-stack-simulation
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/run_deterministic.py            # generates Figures 1, 2, 5, 6, 7 of the paper
python scripts/run_jurisdictional.py           # generates Figures 9, 10, 11 + jurisdictional tables
python scripts/run_layer7.py                   # generates Figures 3, 4 + K7-sensitivity tables
python scripts/run_appendix_a.py               # generates Figures 12-14 (Appendix A: layered DCF)
python scripts/run_appendix_b.py               # generates Figures 15-16 (Appendix B: phase-conditional)
python scripts/render_equations.py             # renders 13 equations of Appendices B and C as PNGs
python scripts/run_monte_carlo.py              # generates Figure 8 (10,000 runs)
jupyter notebook notebooks/                    # interactive exploration
```

## Interactive Streamlit UI (recommended)

The repository ships with a complete Streamlit interface that exposes the full
framework in a navigable application with five tabs (Overview, Seven Layers,
Appendix A, Appendix B, About). Global parameters (K₇, AI substitution
potential, layer exposure) are shared across all tabs in a unified sidebar,
so adjusting K₇ once propagates to all tabs simultaneously.

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
> de Miranda Neto, A. (2026). *The Cost Gradient of the Build: Generative AI and the Strategic Reinvention of Innovation-Driven Entrepreneurship*. Working paper.

**Repository:**
> de Miranda Neto, A. (2026). *commoditization-stack-simulation* (v0.5) [Computer software]. GitHub.

A `CITATION.cff` file is provided so that GitHub's "Cite this repository" button produces a properly formatted citation automatically.

## License

MIT License (see `LICENSE`).

## Author

Arthur de Miranda Neto — Federal University of Lavras (UFLA), Department of Automation, Lavras, Minas Gerais, Brazil.
Email: arthur.miranda@ufla.br

Contributions, parameter critiques, jurisdictional case studies, alternative K7 trajectories, and pull requests are warmly welcome. The framework is intentionally open so that practitioners, firms, governments, and researchers can use, modify, extend, and improve it. The author hopes that the framework will serve as a starting point for a conversation, not as a finished account.

## Version history

- **v0.5** (May 2026): paper retitled *The Cost Gradient of the Build*; consolidated to four interlocking contributions; §9 rewritten with three blocks on AI as practitioner of science (Lu et al., 2026 / Sakana AI Scientist; Penadés et al., 2025 / Google AI co-scientist); §10 entrepreneurship pedagogy removed; §11 fused with §12 into a single "Discussion and limitations" section. Figures regenerated without embedded figure-number titles. Added "K7 is a descriptive indicator, not a policy lever" clarification. Added `labor_preservation_K04.yaml` example scenario.
- **v0.4** (May 2026): introduction of the tentative seventh layer (cross-border knowledge regime) with the K7 coefficient, three reference regimes, and modulation of Layers 3, 4, and 5. New script `scripts/run_layer7.py` generates Figures 3 and 4.
- **v0.3** (May 2026): added Section 7 on the accounting-substitution problem and jurisdictional analysis under Brazil (CLT), France (CDI), and the United States (W-2). New module `src/jurisdictional.py`. Three new YAML scenarios.
- **v0.2** (May 2026): paper revised with three explicit contributions. Added Section 5.3 on the Minimum Viable Hypothesis. Added Section 7 on layered defensibility. Reference list corrected and expanded.
- **v0.1** (May 2026): initial release accompanying the working paper.
