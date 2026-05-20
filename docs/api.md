# Cost Gradient Framework API

REST API exposing the computational core of *The Cost Gradient of the
Build — How Differential Commoditization Reshapes Entrepreneurship and
Valuation: A Layer-Decomposed Risk Premium for the Post-AI Firm* (de
Miranda Neto, 2026).

This document is the operational reference. For the canonical
interactive docs, run the API locally and open `/docs` (Swagger UI) or
`/redoc`.

---

## Quick start

### Local development

```bash
# from the repository root
pip install -r requirements.txt
python scripts/run_api.py
# API at http://127.0.0.1:8000
# Docs at http://127.0.0.1:8000/docs
```

### Docker (Cloud Run / Fly.io / any container host)

```bash
docker build -t cost-gradient-api .
docker run --rm -p 8000:8000 cost-gradient-api
```

### Health check

```bash
curl http://127.0.0.1:8000/api/v1/meta/health
```

---

## Endpoint surface (v1)

All endpoints are namespaced under **`/api/v1/`** and grouped by tag in
the OpenAPI schema. Authentication is not yet enforced (Marco 5 of the
website rollout); for production deployment, set
`CORS_ALLOWED_ORIGINS` to your frontend domain(s).

### Meta — `tag: meta`

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/meta/health` | Health + version surface |
| GET | `/api/v1/meta/citation` | Canonical paper + repository citation |
| GET | `/api/v1/meta/parameters/defaults` | Full YAML parameter defaults |

### Valuation — `tag: valuation`

The four valuation paths plus reconciliation and lightweight Monte
Carlo. These are the primary endpoints the Next.js frontend uses for
the **Mode B — Value your company** workflow.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/valuation/berkus` | Berkus method (pre-revenue) |
| POST | `/api/v1/valuation/vc-method` | VC method (exit-multiple discounted at target IRR) |
| POST | `/api/v1/valuation/comparable-multiple` | Revenue-multiple with optional noise |
| POST | `/api/v1/valuation/damodaran/classical` | Classical Damodaran key-person discount |
| POST | `/api/v1/valuation/damodaran/inverted` | Inverted key-person discount (Section 6.4) |
| POST | `/api/v1/valuation/layered` | Layered DCF (Appendix A) |
| POST | `/api/v1/valuation/two-phase` | Phase-conditional DCF (Appendix B) |
| POST | `/api/v1/valuation/dual-channel` | Dual-channel correction Eqs B.14–B.15 |
| POST | `/api/v1/valuation/four-path` | All four paths + ratios in one call |
| POST | `/api/v1/valuation/monte-carlo` | Lightweight MC bands over the four paths |

### Sensitivity — `tag: sensitivity`

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/sensitivity/k7` | Sweep K7 across a list of values |
| POST | `/api/v1/sensitivity/ai-substitution` | Sweep AI substitution potential |
| POST | `/api/v1/sensitivity/macro-grid` | Macro regime × funding environment grid |

### Migration (Section 7.5) — `tag: migration`

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/migration/compute` | Full cash-flow trajectory for a firm |
| GET | `/api/v1/migration/reference-firm/{jurisdiction}` | Section 7.5 reference (50 eng, 60% sub) |
| POST | `/api/v1/migration/multi-jurisdiction` | Parallel computation across blocs |

### Jurisdictional — `tag: jurisdictional`

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/jurisdictional/defaults` | Brazil / France / US reference parameters |
| POST | `/api/v1/jurisdictional/substitution-npv` | Accounting-substitution NPV |
| POST | `/api/v1/jurisdictional/inverted-discount` | Jurisdictional inversion premium |

### Seven layers — `tag: layers`

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/layers/defaults` | Default parameters for the seven layers |
| POST | `/api/v1/layers/substitutability-trajectory` | Year-by-year per-layer trajectory |
| GET | `/api/v1/layers/knowledge-regimes` | Reference K7 regimes (2020 / 2026 / 2030) |
| POST | `/api/v1/layers/k7-modulation` | Apply K7 modulation to layer-4/5/6 baselines |

### Appendix D — `tag: appendix-d` (Streaming + fiscal blocs)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/appendix-d/streaming/scenarios` | Three substitution scenarios |
| POST | `/api/v1/appendix-d/streaming/cross-jurisdictional` | Cross-bloc minimum-viable price |
| GET | `/api/v1/appendix-d/fiscal/projections` | Five-year fiscal projections |

### Appendix E — `tag: appendix-e` (Fragility)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/appendix-e/fragility/compute` | Fragility index for a custom firm |
| GET | `/api/v1/appendix-e/fragility/case-studies` | NeuroCertify + DataFlow Pro reference |

### Appendix F — `tag: appendix-f` (Upstream chain)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/appendix-f/upstream/categories` | Seven upstream firm categories |
| GET | `/api/v1/appendix-f/upstream/capex-sensitivity` | Layer-1 capex under financing tightness |
| GET | `/api/v1/appendix-f/upstream/adoption-threshold` | L4-heavy vs L6-rich threshold curves |
| GET | `/api/v1/appendix-f/upstream/k7-jurisdictional` | K7 inversion sweep per jurisdiction |

### Appendix G — `tag: appendix-g` (Distributional)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/appendix-g/double-threshold` | Economic + XAI compliance threshold |
| GET | `/api/v1/appendix-g/xai-capacity-gap` | XAI capacity gap under three K7 regimes |

### Reports — `tag: reports`

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/reports/audiences` | Supported audiences (investor/founder/policy/researcher) |
| POST | `/api/v1/reports/generate` | Multi-audience report from the four EVs |

---

## Worked example: end-to-end company valuation

The four-path endpoint is the principal entry point for the Mode B
workflow. Below is a complete request reproducing the NeuroCertify
calibration from Appendix A.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/valuation/four-path \
  -H "Content-Type: application/json" \
  -d '{
    "firm_label": "NeuroCertify",
    "fcf_by_year_usd": [-1500000, -800000, 1200000, 5500000, 12000000],
    "macro": {"risk_free_rate": 0.045, "equity_risk_premium": 0.055},
    "phases": {
      "phase_1_end_year": 2,
      "phase_2_end_year": 4,
      "beta_unlevered_phase_1": 0.85,
      "beta_unlevered_phase_2": 1.10,
      "beta_unlevered_phase_3": 0.99,
      "de_ratio_phase_1": 0.05,
      "de_ratio_phase_2": 0.12,
      "de_ratio_phase_3": 0.16,
      "kd_spread_phase_1": 0.025,
      "kd_spread_phase_2": 0.045,
      "kd_spread_phase_3": 0.035,
      "effective_tax_rate": 0.064
    },
    "trl_trajectory": {"years": [4, 5, 6, 7, 7]},
    "layer_exposure": {
      "layer1": 0.05, "layer2": 0.05, "layer3": 0.05,
      "layer4": 0.20, "layer5": 0.20, "layer6": 0.40, "layer7": 0.05
    },
    "k7": 0.7,
    "ai_substitution_potential": 0.50,
    "terminal_growth_rate": 0.025,
    "second_valley_drag": 0.05,
    "lambda_phase2": 0.95,
    "lambda_phase3": 1.0,
    "use_unified_variant": false
  }'
```

Response (abbreviated):

```json
{
  "firm_label": "NeuroCertify",
  "v0_classical_usd": 126500000.0,
  "v0_layered_A_usd": 69300000.0,
  "v0_twophase_B_usd": 113900000.0,
  "v0_dualchannel_usd": 113300000.0,
  "ratios": {
    "layered_over_classical": 0.548,
    "dualchannel_over_twophase": 0.995,
    "numerator_channel_effect_usd": 600000.0
  },
  "notes": "..."
}
```

The Next.js frontend chains this with `/api/v1/valuation/monte-carlo`
for confidence bands and `/api/v1/sensitivity/k7` for the K7 sweep.

---

## Deployment

### Google Cloud Run (recommended)

```bash
# build + push to Artifact Registry
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT/REPO/cost-gradient-api

# deploy
gcloud run deploy cost-gradient-api \
  --image REGION-docker.pkg.dev/PROJECT/REPO/cost-gradient-api \
  --region REGION \
  --allow-unauthenticated \
  --set-env-vars CORS_ALLOWED_ORIGINS=https://your-frontend.com \
  --memory 512Mi --cpu 1 --concurrency 80
```

### Fly.io

```bash
fly launch --no-deploy
fly deploy
fly secrets set CORS_ALLOWED_ORIGINS=https://your-frontend.com
```

### Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `PORT` | TCP port the server binds to | `8000` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins | `localhost:3000`, `localhost:5173` |

---

## Versioning

All endpoints live under `/api/v1/`. Breaking changes will move to
`/api/v2/`. Additive changes (new fields, new endpoints) are released
under v1 without version bump and announced in the changelog.

API version: see `/api/v1/meta/health`.
Paper version: see `/api/v1/meta/citation`.

---

## See also

- [`docs/glossary.md`](glossary.md) — Appendix H conceptual glossary
- [`docs/EXTENDING.md`](EXTENDING.md) — How to extend the underlying framework
- [`docs/dual_channel_correction.md`](dual_channel_correction.md) — B.2.6 implementation notes
- [`docs/empirical_calibration_program.md`](empirical_calibration_program.md) — Calibration methodology
