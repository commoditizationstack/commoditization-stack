# Empirical calibration program

**Status:** scaffolding only. The framework's operative parameters
(`alpha_4_sys`, `lambda_2V_phase2`, `lambda_2V_phase3`, the per-layer
risk coefficients `alpha_i`, the K7 trajectory) are documented as
"calibration parameter — provisional, not data-estimated" throughout
the paper and in `config/parameters.yaml`. This document explains
what firm-level transaction data would be needed to refine them, what
the estimator looks like, and what the identifiability conditions
are.

The scaffolding lives in `src/calibration.py`. It is **infrastructure
for future work** — not a current empirical claim.

---

## 1. What the calibration program needs

A calibration run consumes a sample of `TransactionObservation`
records (defined in `src/calibration.py`). One record corresponds to
one observed deal: an M&A transaction, a priced funding round, or a
documented secondary. Each record carries:

| Field | Source | Provenance |
|---|---|---|
| `firm_id` | analyst's internal anonymized identifier | analyst |
| `sector` | Damodaran industry classification | Damodaran (2026) |
| `transaction_date` | deal close date | Pitchbook / Crunchbase / Carta / disclosed |
| `observed_enterprise_value_usd` | the deal's implied EV | observed |
| `layer_exposure` | analyst-reconstructed layer shares | analyst's reconstruction |
| `phases` | phase parameters (β, D/E, K_d spreads) at transaction time | Damodaran sector + analyst |
| `fcf_by_year` | projected FCF at transaction time | analyst's reconstruction |
| `risk_free_rate`, `equity_risk_premium`, `terminal_growth_rate` | macro at transaction time | Damodaran ERP / Treasury yield |
| `K7`, `layer4_substitution_potential` | regime + capability at transaction time | de Miranda Neto (2026) calibration |
| `second_valley_drag` | per-firm Phase-2/3 scarring (legacy field) | analyst |

The estimator treats `observed_enterprise_value_usd` as the ONLY
ground-truth field. Every other field is the analyst's reconstruction
of firm context at transaction time, supplied to the predictor
function. This separation makes the calibration auditable: a reader
can challenge a fit by challenging the reconstruction of any single
observation, not just the aggregate estimate.

### 1.1 Where the data lives

The transaction data does not exist in this repository. Plausible
sources, in approximate ascending order of friction:

  * **Carta** (private-market funding rounds, Q3 2025 medians already
    used as Carta reference lines in `config/parameters.yaml`).
  * **Pitchbook** (broader transaction database, paid).
  * **Crunchbase** (free tier covers funding events; deal sizes are
    self-reported).
  * **SEC EDGAR** (Form 8-K M&A disclosures, S-1 filings — for public
    targets and acquirers).
  * **Damodaran's annual data updates** (industry-level aggregates,
    not transaction-level).

A first-pass calibration would aim for **n ≥ 30 transactions** per
sector × jurisdiction cell. The estimator refuses to fit below
`src.calibration.MIN_OBSERVATIONS = 10`.

### 1.2 What honest calibration looks like

Three properties distinguish a defensible calibration from a noise
fit:

  1. **Out-of-sample residuals are bounded.** A fit produced from
     2020-2023 deals should produce residuals on 2024-2025 deals that
     are statistically indistinguishable from the in-sample residuals.
     This is testable by k-fold cross-validation over the transaction
     date.
  2. **Bootstrap bands are narrow.** P10–P90 width less than 30% of
     the point estimate suggests the parameter is identified by the
     data; wider bands suggest the data does not pin the parameter
     down and the calibration should be rejected.
  3. **The fit honours sectoral homogeneity.** Pooling Software
     System & Application with Healthcare Information & Technology
     in a single fit gives a hybrid estimate that may match neither
     sector well. Calibrate per-sector, not pooled.

---

## 2. The estimator

The objective minimized at the optimum is the sum of squared (log)
EV residuals:

```
J(parameter) = Σ_i [ log V0_predicted_i(parameter) − log V0_observed_i ]²
```

Log space is the canonical choice because EV magnitudes span orders
of magnitude across realistic samples. A $10M error on a $1B firm
contributes the same to `J` as a $100k error on a $10M firm — they
are proportional residuals, not absolute.

The predictor `V0_predicted_i(parameter)` is the dual-channel
construction under the unified-lambda interpretation
(`v0_dualchannel_unified`), with `second_valley_drag = 0` enforced
inside the predictor (per the unified-lambda doctrine — its
information lives in `lambda_phase3`).

### 2.1 Per-parameter estimators

The module supplies three estimators:

  * **`fit_lambda_phase2`** — grid-searches `lambda_2V_phase2 ∈
    [0.50, 1.00]` while holding `lambda_phase3` at either a caller-
    supplied value or at `1 − second_valley_drag` per observation.
  * **`fit_lambda_phase3`** — grid-searches `lambda_2V_phase3 ∈
    [0.50, 1.00]` while holding `lambda_phase2` at either a caller-
    supplied value or at `1.0`.
  * **`fit_alpha_4_sys`** — grid-searches `alpha_4_sys ∈ [0, 0.08]`
    using the hybrid construction (layered DCF with the `alpha_4_adj`
    substitution, plus lambda on FCF). Heavier than the two lambda
    estimators because the layered firm-specific premium is rebuilt
    at each grid point.

Each estimator runs a 200-resample non-parametric bootstrap to
produce P10/P50/P90 bands around the point estimate.

### 2.2 Identifiability

A single-parameter fit is well-identified when **the predictor's EV
is monotonic in the parameter over the relevant grid**. All three
estimators satisfy this:

  * `lambda_2V_phase2` enters the explicit-period FCF multiplicatively
    in Phase 2 — lower λ → lower EV.
  * `lambda_2V_phase3` enters Phase-3 explicit FCF and the perpetuity
    base multiplicatively — lower λ → lower EV.
  * `alpha_4_sys` enters the Layer-4 firm-specific premium negatively
    (via `alpha_4_adj = alpha_4 − alpha_4_sys`) — higher `alpha_4_sys`
    → lower discount rate → higher EV.

Joint identifiability of multiple parameters from the same sample is
weaker (the three parameters can partially substitute for one
another in fitting the EV). The estimators are therefore designed
for **sequential** rather than joint use:

  1. Fit `lambda_phase3` first on Phase-3-mature firms (small
     `second_valley_drag` exposure).
  2. Fit `lambda_phase2` next, holding the `lambda_phase3` from
     step 1 fixed.
  3. Fit `alpha_4_sys` last, on the hybrid construction with both
     lambdas from steps 1-2 fixed.

This decomposition is documented in the estimator docstrings.

### 2.3 Diagnostics

`compute_residuals(observations, lambda_phase2, lambda_phase3)`
returns the per-observation log-EV residual at any (λ_p2, λ_p3) pair.
Plotting the residuals against `layer4_share`, `K7`, sector, and
transaction date is the canonical diagnostic for misspecification
(non-zero average, fanning, trending residuals all indicate the
estimator should be rejected for the supplied sample).

`recover_layer4_premium(observation)` backs out the implied Layer-4
firm-specific premium from a single observation in isolation —
useful for sanity-checking individual transactions against the
framework's documented coefficients before pooling. It is a one-pass
approximation, not a full fit.

---

## 3. What this module does NOT do

To prevent the scaffolding from being misread as an empirical claim:

  * **No automatic YAML override.** A fit produced by `src.calibration`
    is returned as an `EmpiricalCalibration` record. The practitioner
    decides explicitly whether to accept it; nothing in the code path
    rewrites `config/parameters.yaml`.
  * **No data ingestion.** The module does not read CSVs, query
    databases, or fetch web pages. The caller assembles a list of
    `TransactionObservation` and passes it in.
  * **No suppression of failed fits.** The estimators raise
    `ValueError` when given fewer than `MIN_OBSERVATIONS = 10`
    observations. There is no silent fall-through to a default.
  * **No claim about the documented case firms.** NeuroCertify and
    DataFlow Pro are illustrative — they are NOT transaction
    observations. The fixtures in `config/parameters.yaml` exist for
    teaching and Figure B.5 rendering, not as calibration data.

---

## 4. Acceptance properties

Tested in `tests/test_calibration.py`:

  * **Round-trip recovery.** Generating synthetic observations from a
    known `lambda_2V_phase2 = 0.70` (plus noise), then running
    `fit_lambda_phase2` on the generated sample, recovers
    `0.70 ± 0.05` for `n ≥ 30` observations under realistic noise
    levels. The same property holds for `lambda_phase3` and (with
    looser tolerance) for `alpha_4_sys`.
  * **Sample-size guard.** `fit_*` raises `ValueError` when
    `len(observations) < MIN_OBSERVATIONS`.
  * **Bootstrap consistency.** P10 ≤ P50 ≤ P90 on every fit; the
    P50 is close to the point estimate (within one grid step) for
    reasonably-sized samples.
  * **No side effects.** Running a fit does NOT alter
    `LAYER_RISK_COEFFICIENTS` or any module-level state after return;
    the alpha_4_sys estimator's temporary mutation of the Layer-4
    coefficient is restored in a `finally` clause.
  * **Pure objective function.** The same `(observations, parameter)`
    pair always produces the same objective value (reproducibility
    under fixed seed).

---

## 5. A worked toy example

`scripts/calibration_demo.py` runs a synthetic end-to-end calibration:

  1. Generates 50 synthetic transactions with known
     `lambda_2V_phase2 = 0.70`, `lambda_2V_phase3 = 0.85`,
     and a Lognormal(0, 0.15) per-firm EV noise.
  2. Fits all three parameters sequentially per Section 2.2.
  3. Prints the point estimates with bootstrap bands and the
     residual diagnostics.

Recovered values for the toy example land within ±0.02 of the
generators on the lambda parameters, and within ±0.01 of the
generator on `alpha_4_sys`. This is the expected behaviour and is
documented as a regression test.

When real data is available, the same workflow applies — the only
difference is that the observations come from the world rather than
from a synthetic data generator.
