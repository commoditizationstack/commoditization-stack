# Extending the simulation

This document explains how to modify the simulation at three levels of increasing depth, from changing parameters to extending the framework itself.

---

## Level 1 — Parameters only

Edit `config/scenarios/post_genai_2026.yaml` (or any other scenario file) and re-run:

```bash
python scripts/run_deterministic.py
python scripts/run_monte_carlo.py
```

All numeric inputs to the simulation live in YAML. The most consequential parameters are:

- `startup.ai_substitution_potential_layer4` (0..1) — share of layer-4 work substitutable by frontier models. Higher values move the firm toward the inverted regime.
- `startup.team_layer_distribution.layer_3` (0..1) — share of team labor at layer 4. Crosses the threshold above which the inversion activates.
- `valuation.damodaran_inverted_threshold_layer4_share` — threshold above which the inversion regime begins.
- `valuation.damodaran_inverted_max_premium` — cap on the magnitude of the inverted premium.

To experiment quickly, edit one parameter, save, and re-run.

---

## Level 2 — New sector

To add a new sector (for example, MedTech, FinTech, climate-tech):

1. Copy `config/scenarios/post_genai_2026.yaml` to `config/scenarios/<your_sector>.yaml`.
2. Modify these blocks to reflect sector reality:
   - `startup.cac_usd`, `startup.ltv_usd`, `startup.churn_monthly` — sector economics.
   - `startup.initial_team_size`, `startup.monthly_burn_per_engineer_usd` — typical headcount and compensation.
   - `startup.trl_initial`, `startup.trl_target` — how mature the technology starts and how mature it must become before scaling.
   - `valuation.comparable_revenue_multiple_baseline` — sector-typical revenue multiple.
   - `startup.team_layer_distribution` — share of labor at each layer (regulated sectors weight layer-6 higher).
3. Run:
   ```bash
   python scripts/run_deterministic.py --scenario <your_sector>
   python scripts/run_monte_carlo.py
   ```

---

## Level 3 — Modify the framework

Three common framework-level modifications.

### Adding a layer

Open `src/stack_layers.py` and append a new entry to `LAYER_KEYS_ORDERED`. Then add the corresponding entry to `config/parameters.yaml` under `stack_layers`. The simulation treats layers as ordered but does not depend on the exact count.

### Modifying the inverted-discount logic

Open `src/valuation.py` and edit `damodaran_inverted_discount`. The current formulation uses a piecewise rule: classical regime below the threshold, linear interpolation between classical penalty and maximum premium above it, scaled by `ai_substitution_potential`. Reasonable alternatives include:

- A logistic crossover instead of a linear interpolation.
- An asymmetric inversion where the premium cap is itself a function of layer-4 share.
- A team-size-dependent magnitude (large absolute teams may invert more strongly than small ones at the same share).

### Replacing the Hype Cycle parametrization

Open `src/hype_cycle.py` and edit `post_genai_double_valley_curve`. The current implementation is piecewise-cosine for didactic clarity. For research use you may prefer a fitted dual-Gaussian or a calibration to actual Gartner expectation indices.

---

## Reproducing the paper's numbers exactly

The deterministic figures and tables are produced by a single command:

```bash
python scripts/run_deterministic.py
```

This regenerates everything in `outputs/figures/` and `outputs/tables/deterministic_results.csv`. The Monte Carlo figures and summary table are produced by:

```bash
python scripts/run_monte_carlo.py --runs 10000
```

The default seed is set in `config/parameters.yaml` under `simulation.random_seed`.

---

## Adding tests

A smoke test lives in `tests/test_smoke.py`. Add unit tests there using `pytest`:

```bash
pip install pytest
pytest tests/
```

Tests that target the inverted-discount logic and the layer-velocity computation are the highest-value additions, because those are the components most likely to break under modification.
