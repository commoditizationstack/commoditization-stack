# Conceptual glossary (Appendix H of the paper)

This document materializes Appendix H of *The Cost Gradient of the Build — How
Differential Commoditization Reshapes Entrepreneurship and Valuation: A
Layer-Decomposed Risk Premium for the Post-AI Firm* (de Miranda Neto, 2026).
The intended audience is the reader whose disciplinary background does not
include the full technical, valuation, and regulatory vocabulary the
framework mobilizes. The glossary is organized in three sub-sections that
mirror the layered framework, plus a closing note on numerical magnitudes
attributed to the Mensch (2026) testimony.

---

## H.1 Technical vocabulary of the AI stack (Layers 1 through 4)

**Token.** The economic unit of contemporary AI services. A small unit of
text (typically a few characters or part of a word), an image patch, or an
audio segment, encoded as an integer in a vocabulary of typically tens of
thousands of entries. AI services are priced by the number of tokens
consumed in input and produced in output. The economic process is the
transformation of electrical energy and trained model weights into
sequences of tokens that, in aggregate, encode the work the user has
delegated to the system.

**Parameter.** A numerical value internal to a neural network that is
adjusted during training and that determines, in combination with other
parameters, the model's response to a given input. Contemporary frontier
models contain hundreds of billions to trillions of parameters.

**Training.** The process of adjusting a model's parameters on the basis
of a corpus of examples, such that the model's outputs come to approximate
the patterns present in the corpus. Training a frontier model in 2026
typically requires tens of thousands of specialized processors operating
in parallel for weeks or months. Training cost is the principal driver of
the Layer-1 *cumulative* capex that the framework characterizes as
anti-commoditizing.

**Inference.** The use of a trained model to produce outputs in response
to inputs, after training has completed. Inference is computationally
lighter than training per unit of work but operates continuously, in
proportion to user demand. Inference cost per token is the principal
driver of the Layer-1 *marginal* capex that the framework characterizes
as commoditizing on the unit-cost dimension while expanding on the
aggregate-demand dimension.

**Foundation model.** A large model trained on broad, general-purpose data
and adapted (through fine-tuning, prompting, or related techniques) to
specific downstream uses. Foundation models occupy Layer 2 of the
framework; the principal developers in 2026 are concentrated in a small
number of frontier laboratories.

**Frontier model.** A foundation model situated at the leading edge of
capability as measured by benchmark performance, parameter count,
training compute, or a combination of these. Membership in the set carries
strategic and regulatory consequences that intermediate-tier models do
not.

**Fine-tuning.** The process of further training a pre-trained foundation
model on a smaller, task-specific corpus. A principal mechanism by which
the capabilities of Layer 2 are deployed at Layer 4.

**Distillation.** The process of using a large, capable model to train a
smaller, more efficient model that approximates the larger model's
behavior on a target distribution of tasks. Reduces inference cost without
requiring re-creation of the large model; not a path by which actors
without frontier-training capacity can catch up.

**Retrieval-augmented generation (RAG).** An architectural pattern in
which a model's output is conditioned not only on its trained parameters
and the immediate input but also on documents retrieved from an external
corpus at the time of inference.

**Agent / Agentic system.** A system in which a model is granted the
capacity to take actions in an environment — executing code, querying
tools, modifying files, or invoking other services. Extends the Layer-4
substitution channel from advisory work to executory work.

**Prompt engineering.** The craft of formulating inputs to a model such
that the model produces outputs of useful quality. The principal skill
that the AI-orchestrator function described in Section 7.5 mobilizes.

**Cloud and AI services.** In contemporary practice the operational
integration of cloud computing services and AI services is sufficiently
tight that the two cannot be cleanly separated: the same firms supply
Layer 1 training compute, Layer 2 foundation models, Layer 3 capability
access, and the storage and orchestration services that surround them
(Mensch, 2026). The framework treats these as distinct layers for
analytical purposes while recognizing the operational integration as a
structural feature of the upstream market.

---

## H.2 Vocabulary of innovation, economics and valuation (Layers 5 through 6 and the appendices)

**Minimum Viable Product (MVP).** A version of a product with the smallest
feature set sufficient to test a falsifiable hypothesis with real users
(Ries, 2011). The MVP doctrine assumes that the principal cost in product
development is the build station, and that minimizing the building is the
route to learning.

**Minimum Viable Hypothesis (MVH).** The reformulation proposed in
Section 5.3: the testable hypothesis, formulated before the build and
increasingly testable through automated investigation, is the unit on
which the iterative cycle now turns, given that the build station has
shrunk by one to two orders of magnitude for a substantial subset of
digital products.

**Technology Readiness Level (TRL).** A nine-level scale, originated at
NASA, that characterizes the maturity of a technology from basic
principles observed (TRL 1) to system proven in operational environment
(TRL 9). Used as a modulator of the discount rate (Appendix A) and as a
marker of the lifecycle phases (Sections 6.5 and Appendix B).

**CAPM (Capital Asset Pricing Model).** A model that relates the expected
return on a risky asset to a risk-free rate plus a premium proportional
to the asset's exposure to market-wide risk (beta). Reformulated as
phase-conditional in Appendix B (Eqs B.3 and B.4); the risk-free rate is
held exogenous and constant, so that the phase structure enters only
through the time-varying beta.

**WACC (Weighted Average Cost of Capital).** The blended cost of equity
and debt financing weighted by the firm's capital structure, used as the
discount rate in DCF valuation. Reformulated as phase-conditional in
Appendix B (Eq B.6).

**EVA (Economic Value Added).** A measure of economic profit that
subtracts a charge for capital employed from operating profit; positive
EVA indicates value creation, negative EVA indicates value destruction.
Appendix B demonstrates that under the double-valley dynamic the
classical EVA framework masks a Phase-2 destruction-of-value period of
approximately 23 percent for Layer-4-heavy firms (Eq B.7).

**Gordon perpetuity.** A formula for the present value of a constantly
growing perpetual stream of cash flows, used to compute the terminal
value in a DCF valuation. The framework introduces a multiplicative
correction (the second-valley drag) to account for commoditization risk
(Eq B.9).

**Key-person discount.** A reduction applied to the valuation of a young
firm whose value depends critically on the continued involvement of a
small number of identifiable individuals (Damodaran, 2009). Section 6.4
argues that the *sign* of the discount can flip from positive to negative
once the technical labor surrounding the key person becomes substitutable
by frontier-model services, producing the inversion premium analyzed in
Section 7.

**Beta (unlevered).** A measure of the systematic risk of a sector's
equity, with leverage effects removed; used as the starting point for
firm-level discount-rate calibration. Damodaran (2026) publishes industry
betas annually; the framework retrieves the sector beta as Step 1 of the
operational manual (Appendix C).

**Terminal value.** The present value of the firm's cash flows beyond the
explicit projection period, computed by the Gordon perpetuity or by an
exit-multiple method. Appendix A modifies the terminal value by a
second-valley drag factor to reflect the commoditization risk of the
post-AI regime.

**Orchestrator function.** The role, formalized in Section 7.5, of a
senior engineer or technical leader who designs, supervises, and
integrates the output of AI-augmented operations within a firm. The
orchestrator function is the near-fixed cost that produces the team-size
adoption threshold of Appendix E.2.

**Substitution NPV (substitution net present value).** The cumulative
discounted economic gain or loss from substituting in-house technical
labor with AI services over the relevant horizon, net of the orchestrator
overhead and transition costs.

**Second valley (dual-channel correction).** The post-AI extension of the
venture valley-of-death pattern: a renewed downturn after the first
recovery, when competitors close the technical gap through frontier-model
substitution (Section 6.5). In valuation it acts through two channels — a
compression of projected revenue (the numerator of the DCF) and a rise in
the cost of capital (the denominator). The systematic portion is carried
by the phase-conditional beta; the firm-specific portion by the
layer-decomposed premium. The dual-channel correction is developed in
subsection B.2.6 (Eqs B.12–B.15) and implemented in `src/dual_channel.py`.

---

## H.3 Vocabulary of regulation, certification, and explainability (Layer 6)

**ISO/IEC 17025.** The international standard for the competence of
testing and calibration laboratories. Accreditation under 17025 is one
of the canonical mechanisms by which Layer-6 institutional embedding is
constructed in regulated technical domains.

**ISO/IEC 42001.** The international management-system standard for
artificial intelligence (published late 2023). Certification under 42001
attests to the existence of governance processes around the development
and deployment of AI systems within an organization; increasingly invoked
in conformity-assessment regimes for high-risk AI applications.

**EU AI Act.** Regulation (EU) 2024/1689 of the European Parliament and
of the Council. Classifies AI systems into risk tiers (unacceptable,
high, limited, minimal), imposes conformity-assessment obligations on
providers of high-risk systems, and is being phased in across 2025 and
2026.

**Conformity assessment.** The procedure by which a regulator or
accredited third party verifies that a product or system satisfies the
requirements of a regulatory regime before market placement. For
high-risk AI systems under the EU AI Act, conformity assessment is a
substantive obligation that requires an explainability substrate the
assessor can interrogate.

**Notified body.** An accredited third-party organization designated by
a regulator to perform conformity assessment on its behalf. The
accumulated relationships between a firm and the notified bodies that
assess its products are a component of the firm's Layer-6 defensibility.

**Accreditation.** The formal recognition by an authoritative body that
an organization is competent to perform specified tasks. Accreditation
regimes (under ISO/IEC 17025, ISO/IEC 42001, ANVISA in Brazil, FDA
processes in the United States, INMETRO/CIAI in Brazil, and equivalents)
construct the institutional trust that Layer 6 characterizes as
anti-commoditizing on the temporal scale of a decade or more.

**Event Data Recorder (EDR).** A device that captures and stores
time-series data from vehicle sensors and onboard systems before, during,
and after a critical event, supporting forensic reconstruction of
accidents and attribution of liability across the manufacturer, the
supervisor, the operator, and the automated driving system. The technical
instrument through which the institutional layer of accident
accountability is constructed (Martinesco et al., 2019; Barbosa et al.,
2016).

**Explainable AI (XAI).** The technical and methodological capacity to
render the outputs, internal computations, or decision boundaries of AI
systems interpretable to auditors, regulators, expert reviewers, and end
users. Section 8.2 and Appendix G of the paper develop XAI as the
technical substrate on which Layer-6 institutional embedding is
constructed. Rudin (2019) argues that for high-stakes decisions one
should develop interpretable models by design rather than rely on
post-hoc explanation; Doshi-Velez and Kim (2017) argue that the
methodological foundations of interpretable machine learning remain an
open scientific problem. A complementary line of work develops algebraic,
task-agnostic XAI primitives that operate directly on the sensor stream
without dependence on a downstream perception task, satisfying the
explainability requirements of ISO 21448 (SOTIF) and ISO/PAS 8800:2024 by
construction (de Miranda Neto, 2026 PCC).

**Explicability.** The fifth ethical principle of artificial intelligence,
articulated by Floridi et al. (2018) alongside the four bioethical
principles of beneficence, non-maleficence, autonomy, and justice.
Encompasses both intelligibility (the capacity of an AI system to be
understood) and accountability (the capacity of an AI system to be held
to account for its outputs).

**Sovereign AI.** The policy posture under which a state or bloc develops
domestic capability across the AI value chain — compute infrastructure,
foundation models, applications, regulation, and talent — sufficient to
reduce dependency on capability supplied from other blocs. The framework
treats sovereign AI as a phenomenon that modulates the K7 coefficient
(Section 4.1), not as a policy recommendation. Mensch (2026) reframes
the same posture as "sovereignty as leverage" rather than isolationism.

**K7 (knowledge-integration coefficient).** The tentative seventh-layer
hypothesis introduced in Section 4.1: a scalar in [0, 1] that
characterizes the state of the cross-border knowledge regime as
observed, with K7 = 1 indicating full integration and K7 approaching
zero indicating regime collapse. The framework treats K7 as a
*thermometer* of the regime rather than a *thermostat* — state actions
modulate K7, but K7 itself is not a policy variable that can be directly
set. Appendix G.3 develops the epistemic-justice dimensions of K7 that
the descriptive treatment in the body deliberately sets aside.

---

## H.4 Note on numerical magnitudes attributed to the Mensch (2026) testimony

The Mensch testimony is mobilized in the paper as a primary source
articulating, in contemporary policy register and from an operational
vantage, structural arguments that the framework develops in analytical
register. The specific numerical magnitudes the testimony advances —
notably:

- the order of magnitude of European AI consumption (≈10 percent of the
  wage bill, projected at ≈€1 trillion over a 3–4 year horizon)
- comparative capex deployment by extra-European actors (≈US$1 trillion
  annually in the near term)
- token-based AI services price reference (≈€1 per million input tokens
  and ≈€3 per million output tokens)

reflect three different reporting choices the reader should note:

1. The **wage-bill figure** is consistent with a broad definition of
   Europe that includes EU-27, EFTA states, and the United Kingdom;
   under the strict EU-27 definition the figure is approximately €800
   billion at 2025 data.
2. The **trillion-dollar capex figure** aggregates multiple announced
   commitments (Big Five hyperscaler 2026 capex projected at US$600–690
   billion, the Stargate Project commitment of US$500 billion over four
   years, and adjacent commitments) and reflects rounding to the
   relevant order of magnitude rather than a single attested industry
   source.
3. The **token-price reference** is compatible with the entry tier of
   European frontier-model catalogues and with the lowest-cost tier of
   US providers (Anthropic Haiku 4.5 at US$1 input / US$5 output per
   million tokens) but diverges from the dominant frontier-tier pricing
   of US providers (Sonnet 4.6 and Opus 4.7 at US$3–5 input / US$15–25
   output per million tokens; GPT-5.4 / GPT-5.5 in comparable ranges).

The structural arguments the framework mobilizes from the Mensch
testimony — the operational integration of upstream layers across
hyperscaler and frontier-lab actors, the framing of sovereignty as
leverage rather than as isolationism, and the temporal closure of
upstream supply capacity — are preserved across plausible recalibrations
of these magnitudes. See `docs/mensch_2026_primary_source.md` for the
consolidated source notes.

---

## See also

- `docs/dual_channel_correction.md` — diagnosis of the literal Eq B.15
  reading, state-of-the-art consultation, scientifically-coherent
  unified-lambda variant, and recommended manuscript edits.
- `docs/empirical_calibration_program.md` — data requirements, estimator
  design, identifiability conditions, and honest limits of the empirical
  calibration of the dual-channel parameters.
- `docs/appendix_g_references.md` — annotated references supporting
  Appendix G (distributional, stewardship, epistemic).
- `docs/mensch_2026_primary_source.md` — consolidated notes on the
  Mensch (2026) testimony as a primary source.
