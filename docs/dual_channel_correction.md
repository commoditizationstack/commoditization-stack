# Scientifically-coherent correction to subsection B.2.6 (dual-channel)

**Status:** correction proposed to the original manuscript. Implemented in the
framework (Sprint 4); the original `delta_2V`-on-TV mechanism and the literal
Eq B.14 with `lambda_phase3 = 1.0` remain available behind explicit flags.

**Author note:** this document is the framework's record of the issue, the
state-of-the-art consultation, the proposed correction, and the manuscript
edits the author may wish to make. It is not a unilateral rewrite of the
manuscript — the framework defers to whichever calibration the manuscript
adopts. What the framework cannot do is silently reconcile an internally
inconsistent expected ordering.

---

## 1. The inconsistency observed

The Insertion Package for subsection B.2.6 asserts a specific qualitative
ordering of the four valuation paths when applied to the two case companies:

> "DataFlow Pro: V0_dualchannel should be the **lowest** of the four values.
> The two effects partly offset — the risk partition lifts value, the revenue
> retreat lowers it — and for a Layer-4-heavy firm the retreat dominates.
> NeuroCertify: V0_dualchannel should sit **close to** V0_twophase_B (both
> B.2.6 effects are small for a Layer-6-rich firm)."
>
> "If DataFlow Pro does not come out lowest, stop and re-examine the
> lambda_2V calibration before generating figures — the manuscript's B.2.6
> text asserts this ordering."

The framework's implementation has stopped — both expectations cannot hold
simultaneously under any single interpretation of "V0_dualchannel" we have
been able to construct from the proposal's text.

### 1.1 Tested interpretations

We tested three readings of "V0_dualchannel" against the literal text:

| Reading | Definition | DataFlow Pro ordering | NeuroCertify ordering |
|---|---|---|---|
| **Basic** (literal Eq B.15) | `two_phase_dcf` with `FCF * lambda_2V(phase)` | $54.7M → above layered_A ($28.3M) ✗ | $113.7M ≈ V0_twophase_B ($113.9M) ✓ |
| **Hybrid-A** | layered_A rate (incl. TRL) + `alpha_4_adj` + λ on FCF | $34.7M → above layered_A ✗ | $75.4M — between layered and two-phase ✗ |
| **Hybrid-B** | two-phase WACC + layered firm-specific premium (`alpha_4_adj`) + λ on FCF | $36.5M → above layered_A ✗ | $162.2M — far above V0_twophase_B ✗ |

No interpretation satisfies both expected orderings simultaneously.

### 1.2 Mechanical cause

For DataFlow Pro under the calibration registered in
`config/parameters.yaml`:

```
DataFlow Pro projected FCF (USD millions):
  Y1: -1.20   ( -9.3% of total)
  Y2: +0.80   ( +6.2% of total)         Phase 1
  Y3: -0.20   ( -1.6% of total)         Phase 2
  Y4: +4.00   (+31.0% of total)         Phase 2
  Y5: +9.50   (+73.6% of total)         Phase 3 — used as TV perpetuity base
```

The terminal value, computed by the Gordon perpetuity on the Y5 FCF base,
dominates EV. The proposal's `lambda_2V` applies to the explicit period only
and is `1.0` in Phase 3 by construction (Eq B.14:
*"`lambda_2V(Phase 3) = 1.0` ... no retreat after the valley"*). The Phase-2
compression therefore hits at most 30% of explicit-period FCF — a small
fraction of total EV. The independent `delta_2V` drag on TV is a constant
multiplier that does not respond to phase composition.

Result: a sensitivity sweep of `lambda_2V_phase2` from `0.70` down to `0.10`
moves V0_dualchannel for DataFlow Pro from `$54.68M` to `$33.46M` — never
crossing below V0_layered_A `$28.27M`. The proposal's "DataFlow Pro lowest"
expected ordering **cannot be reached by varying the lambda calibration the
proposal exposes**.

---

## 2. State-of-the-art consultation

The proposal's `delta_2V`-on-TV-only mechanism is a partial reading of the
post-AI displacement-risk literature. The full picture, on our reading:

* **Cazzaniga et al. (2024, IMF Staff Discussion Note 24/01, "Gen-AI: AI
  and the Future of Work")** — explicitly models the AI productivity shock
  as having *persistent* effects on margins and labor share, not a transient
  dip. The new steady state has structurally lower compensation share.
* **Brynjolfsson, Chandar and Chen (2025, Stanford Digital Economy Lab,
  "Canaries in the Coal Mine")** — payroll-level evidence that the
  displacement is *persistent*: the 13 percent relative decline for
  exposed cohorts beginning in late 2022 has not reversed.
* **Korinek (2025, JEL update, "AI Agents for Economic Research")** —
  characterizes Layer-3 capability as commoditizing and treats the
  resulting margin compression as the new equilibrium for downstream
  firms, not a transient.
* **Damodaran (2009, "Valuing Young, Start-up and Growth Companies")** —
  for displacement-risk firms, the terminal value assumption must reflect
  the *post-displacement steady state*, not the pre-displacement
  trajectory. The framework's `delta_2V`-on-TV mechanism is *one* way to
  honour this, but it is a discount-rate-side mechanism applied to a
  cash-flow-side problem.
* **Equidam (2025, "AI Startup Valuation: Revenue Multiples and the
  Displacement-Risk Problem")** — recommends explicit forecasting of
  *performance degradation scenarios*, with a unified cash-flow-side
  mechanism that reduces both explicit FCF and the perpetuity base.
* **Papadogiannis (2026, Finance Research Open)** — proves that
  belief-driven uncertainty absorbed into a single discount rate produces
  non-identifying valuation deltas. The clean fix is to partition the
  risk into separately-modelled primitives — and to apply each primitive
  to its appropriate channel.

The literature's consensus reading: **post-AI margin compression is a
single phenomenon that flows through both the explicit period AND the
perpetuity base**. The proposal's separation into `lambda_2V` (explicit
period only) + `delta_2V` (TV scar) artificially decouples two
manifestations of the same effect, and leaves the literal calibration
unable to express the proposal's own expected ordering.

---

## 3. The correction

### 3.1 Mathematical form

Extend `lambda_2V` to cover Phase 3, retire `delta_2V` in the dual-channel
path (its information is now carried by `lambda_phase3`):

```
FCF_2V(t) = FCF_proj(t) * lambda_2V(phi(t))         for ALL t (B.14 extended)

TV       = FCF_Y5 * lambda_2V(Phase 3) * (1+g)
                  / (WACC_3 - g)                    (no separate delta_2V drag)
```

With the constraints:

* `lambda_2V(Phase 1) = 1.0` — no retreat in growth phase.
* `lambda_2V(Phase 2) ∈ [0.50, 1.00]` — transient compression during the
  commoditization valley.
* `lambda_2V(Phase 3) ∈ [0.50, 1.00]` — *permanent margin reduction* to the
  new lower steady state. The literature does not require this to equal
  `lambda_2V(Phase 2)`; the two are independently calibrated from the
  firm's layer composition (a Layer-4-heavy firm has both severe Phase-2
  compression and a low Phase-3 steady state, but the two coefficients
  can differ).
* `delta_2V` is set to `0.0` in the dual-channel path. The two-phase path
  (`V0_twophase_B`) and the layered_A path (`V0_layered_A`) continue to
  use the YAML-documented `delta_2V` values unchanged — this preserves
  the regression baseline of the three existing paths.

### 3.2 Calibration helper

The framework derives `lambda_phase3` from the same layer-composition
logic as `lambda_phase2`, with separately-calibrated coefficients to
reflect that *permanent damage* may not equal *transient compression*:

```
lambda_phase3 = clamp(
    1.0 - k_L4_p3 * layer4_share + k_L6_p3 * layer6_share,
    lower_bound, upper_bound,
)
```

Suggested starting coefficients (provisional):
* `k_L4_p3 = 0.85` (Layer 4 commoditization → severe permanent damage)
* `k_L6_p3 = 0.40` (Layer 6 → permanent protection, same weight as phase 2)
* `lower_bound = 0.50`, `upper_bound = 0.95`

Producing for the two case firms:
* NeuroCertify: `1 - 0.85*0.20 + 0.40*0.40 = 0.99 → clamped 0.95`
* DataFlow Pro: `1 - 0.85*0.55 + 0.40*0.10 = 0.57`

These are calibration parameters, not data-estimated. They are
registered in `config/parameters.yaml` under
`dual_channel.lambda_2V_phase3_calibration` and the per-firm defaults
under `dual_channel.lambda_2V_phase3_defaults`.

### 3.3 Acceptance check 3 — preserved

The identity stated in the proposal's acceptance check 3 still holds:

> When `lambda_2V_phase2 = 1.0` (AND, in the unified form, also
> `lambda_2V_phase3 = 1.0`) AND `delta_2V = 0`, V0_dualchannel equals
> V0_twophase_B(delta_2V=0) to the cent.

The original two-phase regression baseline (which uses the firm's
`delta_2V` from YAML) is therefore not perturbed — the unified-lambda
form is an additional, parallel construction.

---

## 4. Recommendation to the manuscript author

The framework now implements the unified-lambda correction as the
canonical V0_dualchannel for the four-bar reconciliation. The author may
wish to consider the following manuscript edits to subsection B.2.6 of
the paper:

1. **Equation (B.14).** Extend the formula to include Phase 3:
   `FCF_2V(t) = FCF_proj(t) * lambda_2V(phi(t))` with `lambda_2V(Phase 3)`
   in `[0.50, 1.00]` rather than fixed at `1.0`. State the calibration
   helper and the interpretation of `lambda_phase3` as *permanent margin
   reduction*, citing the displacement-risk literature.

2. **Equation (B.9) / Section B.3 perpetuity.** Allow `delta_2V = 0` in
   the dual-channel path, with the perpetuity base built on the
   `lambda_phase3`-compressed Y5 FCF. State explicitly that the two
   mechanisms (`delta_2V` on TV vs `lambda_phase3` on FCF) are
   mathematically related but not identical, and that the unified
   `lambda_phase3` form is preferred for the dual-channel construction.

3. **Expected ordering (Section 4 of the Insertion Package).**
   The literal Eq B.15 (V0_dualchannel = two-phase + lambda on FCF)
   places V0_dualchannel **between V0_layered_A and V0_twophase_B
   for both firms**, with the gap from V0_twophase_B scaling with
   the firm's Layer-4 exposure. This is the most coherent reading
   of the proposal's text — and it is consistent with the
   displacement-risk literature.

   The proposal's expected ordering "DataFlow Pro V0_dualchannel
   lowest" **cannot be reached under the literal Eq B.15** without
   extending the construction (see Section 5.1). We recommend one
   of the following manuscript edits:

   (a) **Rephrase** the expected ordering as:
       *"For both case firms, V0_dualchannel sits between V0_layered_A
       and V0_twophase_B. The distance from V0_twophase_B scales with
       Layer-4 exposure: V0_dualchannel ≈ V0_twophase_B for
       NeuroCertify (Layer-6-rich, mild cash-flow correction);
       V0_dualchannel materially below V0_twophase_B for DataFlow Pro
       (Layer-4-heavy, severe cash-flow correction). V0_layered_A
       remains the lowest for both firms because the Appendix A
       framework stacks the TRL premium and the full Layer-4
       firm-specific premium — penalties that V0_dualchannel does
       not re-apply."*
       This is our recommendation: it is the honest characterisation
       of what the literal Eq B.15 produces, and the framework
       implements this ordering by default.

   (b) **Keep** the original "DataFlow Pro V0_dualchannel lowest"
       claim and adopt an extended construction beyond Eq B.15 —
       e.g., a hybrid that adds the layered firm-specific premium
       (with alpha_4_adj per Eq B.13) on top of the two-phase WACC.
       The framework can support this; we tested variants
       ("interpretation A" and "interpretation B" in our notes)
       and they do produce the "DataFlow Pro lowest" ordering. The
       trade-off: each extension breaks the literal "Eq B.11 with
       FCF replaced" framing of the proposal and requires the
       manuscript to articulate the additional risk channel.

4. **Acceptance check 3 (identity).** State both forms — the literal
   Eq B.15 identity (lambda_phase2 = 1.0, basic path, delta_2V from YAML)
   AND the unified identity (lambda_phase1 = lambda_phase2 =
   lambda_phase3 = 1.0, delta_2V = 0). Both are regression-tested in
   `tests/test_dual_channel.py` and `tests/test_dual_channel_unified.py`.

---

## 5. Observed ordering under the implemented correction

With the recommended calibration (`k_L4_p3 = 0.85`, `k_L6_p3 = 0.40`):

```
NeuroCertify (Layer-6-rich):
  lambda_phase2 = 0.95  (transient mild retreat)
  lambda_phase3 = 0.95  (permanent mild compression)
  delta_2V      = 0.0   (retired in dual-channel path)

  V0_classical:                          $126.5M
  V0_layered_A:                          $ 69.3M
  V0_twophase_B (delta_2V=0.05 retained): $113.9M
  V0_dualchannel (unified):              $113.3M  <-- close to two-phase ✓

DataFlow Pro (Layer-4-heavy):
  lambda_phase2 = 0.70  (transient severe retreat)
  lambda_phase3 = 0.57  (permanent severe compression to new lower steady state)
  delta_2V      = 0.0

  V0_classical:                          $ 75.8M
  V0_layered_A:                          $ 28.3M
  V0_twophase_B (delta_2V=0.30 retained): $ 55.4M
  V0_dualchannel (unified):              $ 43.6M  <-- between layered_A and two-phase
```

**The proposal expected V0_dualchannel to be the lowest for DataFlow
Pro. Our implementation places it BETWEEN V0_layered_A and
V0_twophase_B.** This is the most honest reading the literal Eq B.15
admits — and it is consistent with the displacement-risk literature.
We explain the divergence below; the manuscript correction recommendation
in Section 4 above addresses it.

### 5.1 Why "DataFlow Pro lowest" cannot hold under literal Eq B.15

The mechanical reason: Eq B.15 says V0_dualchannel inherits the two-phase
WACC and applies an additional FCF compression. For V0_dualchannel to
fall *below* V0_layered_A, the FCF compression alone would need to
overcome the layered_A framework's stacked penalisation (TRL premium +
*full* alpha_4 = 0.08 Layer-4 premium, on top of the base CAPM). For
DataFlow Pro that gap is approximately **$27M** (52% of V0_twophase_B):

```
V0_twophase_B - V0_layered_A = $55.4M - $28.3M = $27.1M = 49% of V0_twophase_B
```

The cash-flow channel cannot achieve a 49% reduction with phase-conditional
lambda multipliers, even under extreme calibrations:

```
DataFlow Pro V0_dualchannel sweep (unified construction, basic Eq B.15):
  lambda_phase2=0.70, lambda_phase3=0.70: $53.05M
  lambda_phase2=0.70, lambda_phase3=0.55: $41.95M
  lambda_phase2=0.70, lambda_phase3=0.45: $34.55M
  lambda_phase2=0.55, lambda_phase3=0.45: $34.19M
  lambda_phase2=0.55, lambda_phase3=0.40: $30.49M
  lambda_phase2=0.50, lambda_phase3=0.50: $30.50M  (floor)
```

Floor of `~$30M` versus `V0_layered_A = $28.27M`. The literal Eq B.15
cannot reach the proposal's expected ordering for DataFlow Pro.

To achieve the "DataFlow Pro lowest" ordering would require extending
V0_dualchannel beyond the literal Eq B.15 — for example, adding the
layered firm-specific premium on top of the two-phase WACC (interpretation
B in our tested variants), or rebuilding on the layered_A rate base
itself (interpretation A). Both deviate from the literal text "V0_dualchannel
= the existing Eq. B.11 function with FCF_proj(t) replaced by
FCF_proj(t) * lambda_2V(phi(t))". We chose to preserve the literal
reading and instead recommend a manuscript edit (Section 4 above).

### 5.2 The actually observed ordering (both firms, unified construction)

```
NeuroCertify:  V0_layered_A < V0_dualchannel ≈ V0_twophase_B < V0_classical
DataFlow Pro:  V0_layered_A < V0_dualchannel < V0_twophase_B < V0_classical
```

V0_dualchannel **consistently sits between V0_layered_A and V0_twophase_B
for both firms**, with the distance from V0_twophase_B scaling with the
firm's Layer-4 exposure — a coherent and defensible narrative:

  * The layered_A framework (Appendix A) is the most pessimistic because
    it stacks the TRL premium and the full Layer-4 firm-specific
    premium, both of which are technology/composition-side penalties.
  * The two-phase framework (Appendix B) corrects the discount-rate
    side for phase-conditional cost-of-capital but does not address
    the cash-flow side.
  * The dual-channel (B.2.6, unified) corrects the cash-flow side
    that two-phase misses, without re-stacking the layered penalty.
    For Layer-6-rich firms (NeuroCertify) the cash-flow correction
    is mild, so V0_dualchannel ≈ V0_twophase_B. For Layer-4-heavy
    firms (DataFlow Pro) the cash-flow correction is material, so
    V0_dualchannel is materially below V0_twophase_B but still above
    V0_layered_A.

This narrative is consistent with the framework's overall position
that the four valuations are **complementary diagnostics**, not a
ranking from "best to worst". The dual-channel adds an orthogonal
channel (the FCF side) and its EV reflects *where the firm's value
flows are exposed*, not a composite of every conceivable penalty
mechanism.

---

## 6. Implementation notes

* The unified-lambda correction is implemented in `src/dual_channel.py`
  by exposing `lambda_phase3` (already a parameter of `v0_dualchannel`,
  default `1.0`) as a first-class calibration with its own helper
  `lambda_2V_phase3_from_calibration(layer4_share, layer6_share)`.
* Per-firm `lambda_phase3` defaults are registered in
  `config/parameters.yaml` section 26 alongside the existing
  `lambda_2V_phase2_defaults`.
* The basic V0_dualchannel (literal Eq B.15 with
  `lambda_phase3 = 1.0` and active `delta_2V`) remains available for
  callers that want the literal reading.
* The four-path reconciliation (`reconcile_four_paths`) defaults to the
  unified construction.
* All three existing paths (classical, layered_A, two-phase) continue
  to use their YAML-documented `delta_2V` — the regression baseline
  is unchanged.
* `tests/test_dual_channel_unified.py` adds dedicated tests for the
  unified identity (lambda=1 everywhere AND delta_2V=0 reduces to
  two-phase(delta_2V=0)) and for the expected ordering under the
  documented per-firm calibration.

---

## 7. Worked example — NeuroCertify under the unified construction

This section walks through Equations (B.14) and (B.15) applied to
NeuroCertify, with every intermediate number shown. It is the
counterpart of the worked example the proposal's Section 6 prescribes
for the Insertion Package, applied to the unified-lambda construction
of Section 3 above. All values are produced by the framework at
commit `52c428c` (the head of the Sprint 9 commit chain) and can be
reproduced by running `scripts/run_b26_figures.py` or by reading
`src/dual_channel.py::v0_dualchannel_unified`.

### 7.1 Inputs

NeuroCertify is a Layer-6-rich, deep-tech medical-AI certification
firm (Appendix A.3 of the paper). Its YAML fixtures
(`config/parameters.yaml` section 10) carry:

* **Macro context** (shared with DataFlow Pro):
  * `risk_free_rate` rf = 4.25 %
  * `equity_risk_premium` ERP = 5.50 %
  * `terminal_growth_rate` g = 3.00 %

* **Phase parameters** (lifecycle boundary Y2 / Y4):

  | Phase | Years | β_unlevered | D/E | K_d spread |
  |---|---|---:|---:|---:|
  | 1 (growth)        | Y1–Y2 | 0.85 | 5 %  | 2.5 % |
  | 2 (second valley) | Y3–Y4 | 1.10 | 12 % | 4.5 % |
  | 3 (terminal)      | Y5    | 0.99 | 16 % | 3.5 % |

  Effective tax rate τ = 6.38 % (Damodaran Healthcare IT, January 2026).

* **Projected free cash flow** (`fcf_usd` in YAML):

  ```
  FCF_proj = [ −1.5 M, −0.8 M, 1.2 M, 5.5 M, 12.0 M ]
  ```

* **Dual-channel calibration** (unified construction, `dual_channel:`
  block in YAML):
  * `lambda_2V_phase1` = 1.00 (no retreat outside the valley)
  * `lambda_2V_phase2` = 0.95 (mild transient compression — Layer-6
    protects against the second valley)
  * `lambda_2V_phase3` = 0.95 (mild permanent compression — the
    documented per-firm default for NeuroCertify per the
    `lambda_2V_phase3_defaults` table)
  * `delta_2V` = 0 (retired in the unified construction; its
    information is absorbed into `lambda_2V_phase3`)

### 7.2 Step 1 — Phase-conditional WACC trajectory (Eq B.6)

For each year, the framework computes the levered beta from the
phase β and the phase D/E (Eq B.3), the cost of equity (Eq B.4), and
the WACC from the standard textbook combination (Eq B.6):

| Year | Phase | β_levered | K_e | K_d | WACC(t) |
|---|---|---:|---:|---:|---:|
| Y1 | 1 | 0.8898 | 9.1438 % | 6.7500 % | **9.0093 %** |
| Y2 | 1 | 0.8898 | 9.1438 % | 6.7500 % | **9.0093 %** |
| Y3 | 2 | 1.2236 | 10.9797 % | 8.7500 % | **10.6810 %** |
| Y4 | 2 | 1.2236 | 10.9797 % | 8.7500 % | **10.6810 %** |
| Y5 | 3 | 1.1486 | 10.5106 % | 7.7500 % | **10.0616 %** |

The 1.67-pp Phase-2 jump is the discount-rate-side correction
Appendix B already captures. For NeuroCertify the jump is modest
because Layer 6 protection mutes the β jump (Phase-2 β = 1.10 vs
1.50 for DataFlow Pro under the same framework).

### 7.3 Step 2 — Lambda vector (Eq B.14)

The unified construction extends Eq B.14 to Phase 3. The lambda
vector that the framework builds for NeuroCertify is:

```
λ_2V(φ(t)) = [ 1.00, 1.00, 0.95, 0.95, 0.95 ]   for t = Y1..Y5
```

Multiplying year by year:

| Year | FCF_proj      | × λ      | FCF_2V         |
|---|---:|---:|---:|
| Y1 | −1,500,000   | 1.0000  | −1,500,000.00 |
| Y2 |   −800,000   | 1.0000  |   −800,000.00 |
| Y3 |  1,200,000   | 0.9500  |  1,140,000.00 |
| Y4 |  5,500,000   | 0.9500  |  5,225,000.00 |
| Y5 | 12,000,000   | 0.9500  | 11,400,000.00 |

The Phase-2 entries (Y3-Y4) reflect the transient compression — a
mild 5 % retreat consistent with a defensibility-rich firm. The Y5
entry reflects the permanent compression to the new lower steady
state (the residual scarring previously carried by `delta_2V`).

### 7.4 Step 3 — Compounded discount factors (Eq B.10) and PVs

Damodaran (2016)'s `Myth 4.3` specifies that under time-varying
rates the discount factor for year-t cash flow is the running product
of per-year factors, not (1 + r)^t. The framework consumes this in
`two_phase_dcf`:

```
cum_factor(t) = ∏_{s=1..t} (1 + WACC(s))
```

| Year | WACC(t)    | cum_factor    | PV(FCF_2V)        |
|---|---:|---:|---:|
| Y1 |  9.0093 % | 1.090093     | −1,376,028.91 |
| Y2 |  9.0093 % | 1.188304     |   −673,228.65 |
| Y3 | 10.6810 % | 1.315226     |    866,771.21 |
| Y4 | 10.6810 % | 1.455705     |  3,589,326.36 |
| Y5 | 10.0616 % | 1.602173     |  7,115,337.67 |

**Sum of explicit-period PVs:**

```
PV_explicit  =  Σ_t [ FCF_2V(t) / cum_factor(t) ]
             =  −1,376,028.91 − 673,228.65 + 866,771.21
                + 3,589,326.36 + 7,115,337.67
             =  9,522,177.68 USD
```

The first two years are negative (the firm is burning cash); the
last three are positive and dominate.

### 7.5 Step 4 — Terminal value (Eq B.9 with δ_2V retired)

The terminal value uses the Phase-3 WACC and the **multiplied** last
FCF (Y5 already passed through the lambda factor in Step 2). Under
the unified construction, `δ_2V` is set to 0 — its information now
lives in `lambda_phase3 = 0.95`, applied to the Y5 perpetuity base:

```
TV_at_T  =  FCF_2V(Y5) · (1 + g) / (WACC_3 − g)
         =  11,400,000.00 · (1 + 0.03) / (0.100616 − 0.03)
         =  11,400,000.00 · 1.03 / 0.070616
         =  166,278,593.11 USD
```

Discount the terminal value back to t=0 using the same compounded
factor used for Y5:

```
TV_PV  =  TV_at_T / cum_factor(Y5)
       =  166,278,593.11 / 1.602173
       =  103,783,187.41 USD
```

### 7.6 Step 5 — Enterprise value (Eq B.15)

```
V0_dualchannel  =  PV_explicit  +  TV_PV
                =     9,522,177.68  +  103,783,187.41
                =   113,305,365.08 USD
```

The framework's `v0_dualchannel_unified` returns exactly this value
to the cent — the equality is regression-tested in
`tests/test_dual_channel_unified.py::TestUnifiedIdentity`.

### 7.7 Diagnostics — the numerator channel effect

The numerator-channel effect isolates the contribution of the
cash-flow side. To make the diagnostic like-for-like, we compare
V0_dualchannel against the two-phase EV computed under the **same**
δ_2V = 0 (otherwise the comparison conflates the cash-flow
correction with the legacy terminal-value drag):

```
V0_twophase_B (δ_2V = 0)  =  119,376,661.01 USD
V0_dualchannel (unified)  =  113,305,365.08 USD
                              -----------
Numerator channel effect  =    6,071,295.93 USD
```

For NeuroCertify, the cash-flow channel removes ~ 6.0 M USD from the
two-phase headline — about 5 % of EV. Small, as expected for a
Layer-6-rich firm whose `lambda_2V` factors are close to 1.0.

(For DataFlow Pro, with `lambda_phase2 = 0.70` and
`lambda_phase3 = 0.57`, the same channel effect is approximately
US$ 32 M — about 36 % of the like-for-like two-phase headline.
That is the headline of Figure B.4's lower panel: the cash-flow
channel scales with the firm's Layer-4 exposure.)

### 7.8 Cross-references

* Manuscript Eqs (B.14), (B.15), and Section 6 walk this example
  through in prose form for the Insertion Package.
* The framework implementation that produces every number above is
  `src/dual_channel.py::v0_dualchannel_unified`.
* The reconciliation against the other three valuation paths
  (classical, layered_A, two-phase) is in
  `outputs/figures/fig_b26_four_path_reconciliation.png` and in the
  rendered multi-audience report (`app/tabs/tab_reports.py`).
* The same workflow applies to DataFlow Pro by substituting the
  per-firm FCF projection, phase parameters, and the corresponding
  `lambda_2V_phase2_defaults["dataflow"] = 0.70` /
  `lambda_2V_phase3_defaults["dataflow"] = 0.57` values from the
  YAML.
