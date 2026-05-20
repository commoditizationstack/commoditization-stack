# Appendix G — annotated references

Appendix G of the paper develops the *distributional, stewardship, and
epistemic dimensions* of the framework in a register that engages with
established literatures in ethics of technology, responsibility under
technological uncertainty, and the politics of knowledge regimes. The body
of the work operates in an economic-strategic register; Appendix G is the
complementary register that articulates dimensions the body raises but does
not develop. This document annotates the references mobilized in Appendix G
so the reader can see which literature supports which structural claim. The
implementation of the analytical content sits in `src/distributional.py`
(Appendix G.1 double threshold and XAI-capacity gap); this document supplies
the bibliographic scaffolding.

---

## G.1 The distributional question raised by the E.2 threshold

**Rudin (2019)** — *Stop explaining black box machine learning models for
high stakes decisions and use interpretable models instead.* Nature Machine
Intelligence, 1(5), 206–215. Argues that for high-stakes decisions the
appropriate response is to develop interpretable systems by design rather
than to deploy black-box systems and explain them post-hoc. Cited in
Appendix G.1 to support the claim that the XAI substrate is not optional
refinement of a system that already works but the substrate on which
institutional acceptance and certification depend. Combined with the
team-size adoption threshold of Appendix E.2, produces the *double*
threshold of Figure G.1 (economic floor + XAI compliance floor).

**Sen (1999)** — *Development as Freedom.* Oxford University Press.
Articulates the distinction between formal resources and effective
capabilities. Mobilized in G.1 to characterize the formal-effective gap
that small regulated firms face: formal access to AI-augmented operations
(the technology is available, the vendors are accessible, the contracts
are signable) is not the same as the effective capability to deploy these
operations responsibly within the regulatory environment. The
formal-effective gap is structural, not a transient market imperfection
that diffusion will resolve.

**Winner (1980)** — *Do Artifacts Have Politics?* Daedalus, 109(1), 121–136.
Argues that technical artifacts incorporate political choices about who is
included and who is excluded — not as a consequence of explicit design
intent, but as a property of the artifacts themselves. Applied to the
orchestrator overhead and the explainability substrate of Appendix G.1: the
fixed-cost structure of these components incorporates a choice about the
scale of firm that can participate in AI-augmented operations, and the
choice is invisible until it materializes as the threshold structure of
Figure G.1.

**de Miranda Neto (2026 PCC).** *A task-agnostic algebraic integrity metric
for event-camera streams toward SOTIF-compliant perception using Pearson
correlation coefficient.* Cited in G.1 as evidence that the XAI substrate
admits concrete construction in specific domains (ADAS perception under
ISO 21448 / ISO/PAS 8800:2024), not just abstract requirement.

---

## G.2 Stewardship of public resources in AI-era research decisions

**Jonas (1984)** — *The Imperative of Responsibility: In Search of an Ethics
for the Technological Age.* University of Chicago Press. Articulates
*prospective responsibility*: responsibility extends not only to
consequences directly intended by an action but to trajectories the action
contributes to producing, particularly when trajectories are long-range,
partially irreversible, and the action is one of many marginal
contributions. Applied to public-resource decisions in AI-era research:
the decision-maker bears responsibility not only for whether the project
achieves stated milestones but for whether the project remains, at
completion, a contribution the technical environment can absorb.

**Vallor (2016)** — *Technology and the Virtues: A Philosophical Guide to a
Future Worth Wanting.* Oxford University Press. Argues that emerging
technologies require institutional cultivation of practical virtues —
prudence, attentiveness, responsibility, care — through deliberate
institutional practice rather than through abstract principle. Applied to
the deliberative component of stewardship: the framework supplies the
analytical diagnostic (layer-by-layer decomposition of a project's
contribution) but the institutional practice of revisiting premises during
execution when the technical environment shifts is a practice the framework
*enables* but does not contain.

**Martinesco et al. (2019)** — *A note on accidents involving autonomous
vehicles: Interdependence of event data recorder, human-vehicle cooperation
and legal aspects.* IFAC-PapersOnLine, 51(34), 407–410. Cited in G.2 as a
concrete instance of the conjunction of technical substrate and procedural
regulation: discrimination among negligence, system-design failure, and
component failure requires both an EDR technical substrate and a regulatory
parameter (the appropriate-time parameter).

**Barbosa et al. (2016)** — *The new generation of standard data recording
device for intelligent vehicles.* IEEE ITSC 2016, pp. 2669–2674. Cited in
G.2 alongside Martinesco et al. (2019) as the EDR concept specifically
adapted to automated driving systems.

**Lima et al. (2020)** — *[Final report of the 1st Conference on Intelligent
Vehicles: legal and technological security for insertion in Brazil].*
Inmetro/UFLA. Cited in G.2 as an institutional process operationalizing the
deliberative practice Vallor (2016) articulates abstractly: five formal
recommendations for the regulatory and technological insertion of
intelligent vehicles in Brazil, including inter-administration coordination,
designation of a national authority, and a collaborative data-sharing
platform.

**Pinto, Miranda Neto, & Martinesco (2019)** — *Veículos Inteligentes são
tema de conferência realizada no Rio de Janeiro.* SAE Brasil. Companion
public-facing report of the Inmetro/UFLA conference referenced above.

---

## G.3 Epistemic dimensions of K7 and the geography of explicability

**Jasanoff (2004)** — *States of Knowledge: The Co-Production of Science and
Social Order.* Routledge. Articulates the co-production thesis: scientific
knowledge and political order develop together, each shaping the conditions
of possibility of the other. Applied in G.3 to argue that K7 is not a
neutral parameter of a stable global regime but a record of the political
and epistemic settlements that have been negotiated.

**Jasanoff (2016)** — *The Ethics of Invention: Technology and the Human
Future.* W. W. Norton. Companion to the 2004 volume, with particular
attention to the normative dimensions of co-production.

**Floridi (2013)** — *The Ethics of Information.* Oxford University Press.
Argues that information is a category of ethical concern in its own right
rather than a neutral medium through which other ethical questions are
conducted. Applied in G.3 to the information regimes within which AI
systems are trained and deployed: a frontier model trained on a corpus
systematically excluding the scientific output, cultural production, and
regulatory discourse of one knowledge bloc carries an asymmetry of
representation that propagates into every downstream application.

**Floridi et al. (2018)** — *AI4People — An Ethical Framework for a Good AI
Society: Opportunities, Risks, Principles, and Recommendations.* Minds and
Machines, 28(4), 689–707. Articulates the fifth ethical principle of AI —
*explicability* — alongside the four bioethical principles (beneficence,
non-maleficence, autonomy, justice). Connects the technical-strategic
observation that XAI is the substrate of Layer-6 institutional embedding
(Section 8.2) to the broader ethical infrastructure within which
AI-enabled firms operate.

**Coeckelbergh (2020)** — *AI Ethics.* MIT Press (Essential Knowledge
Series). Summarizes the broader literature on the ethics of AI in terms
that frame the K7 question accessibly: questions about the deployment of
AI systems are simultaneously questions about who controls the systems,
who benefits from them, who bears their consequences, and who is
recognized as a legitimate participant in the conversations about them.

---

## Cross-cutting integration

The framework provides a *structural vocabulary* in which the questions
articulated by these references can be posed with greater precision than
the vocabulary of "AI ethics" alone permits:

- the **seven-layer decomposition** identifies *where in the stack* a
  given question operates;
- the **jurisdictional analysis** identifies *where in the global regime*
  the question manifests;
- the **K7 hypothesis** identifies *how the question is modulated* by the
  trajectory of cross-border knowledge integration;
- the **geography of explicability** (Figure G.2) identifies how the
  asymmetry compounds over time under different regimes of integration.

The framework is, in this sense, a tool for *posing* ethical and political
questions about the global AI regime rather than a tool for *resolving*
them. The references above supply the literatures within which the
resolution can be pursued. Appendix G of the paper offers the dimensions
along which a complete ethical analysis would proceed; this document
identifies who has begun that analysis in each dimension.
