# External Reviewer Batch Review

Status: external review
Reviewer ID: `reviewer-2`
Review scope: all four frozen architecture options

## 1. Inputs used

- Requirements basis: [../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- Masterplan: [../MASTERPLAN.md](../MASTERPLAN.md)
- Review rubric: [../REVIEW_RUBRIC.md](../REVIEW_RUBRIC.md)
- Requirements patches: [../REQUIREMENTS_PATCHES.md](../REQUIREMENTS_PATCHES.md)
- Option A plan: [../options/option-a/PLAN.md](../options/option-a/PLAN.md)
- Option B plan: [../options/option-b/PLAN.md](../options/option-b/PLAN.md)
- Option C plan: [../options/option-c/PLAN.md](../options/option-c/PLAN.md)
- Baseline plan: [../options/baseline/PLAN.md](../options/baseline/PLAN.md)

## 2. Global review notes

- Review all options against the requirements basis, not against architecture taste.
- Use the same rubric logic across all four options.
- Keep supported findings, judgment calls, and unresolved uncertainties separate.
- If a blocker suggests a requirements issue, record it with the label `Potential requirements patch:` and do not edit `REQUIREMENTS_PATCHES.md`.

## 3. Option A review

### Summary verdict
- Overall verdict: Strongly viable for V1.
- Short rationale: Option A strikes the best balance between strict traceability (answering R4's non-negotiable requirement) and operational feasibility, keeping evidence gating explicit without the overhead of persistent graph maintenance.

### Supported findings
- The design enforces an explicit stage-gate (Evidence Ledger Builder and Source Role Controller) between evidence collection and answer synthesis.
- Web expansion is strictly gap-driven and constrained to official domains only after curated retrieval.
- Retrieval natively targets higher-ranked sources before expanding to lower-ranked or web sources.

### Judgment calls
- The ephemeral ledger approach will likely provide sufficient traceability for V1 without the massive up-front ingestion cost of a persistent graph.
- Reliance on inline extraction for article/section anchors might struggle if the raw curated corpus lacks consistent structural markers, potentially degrading the precision of its source links.

### Unresolved uncertainties
- The exact mechanism for defining what constitutes a "gap" that triggers web expansion is under-specified.
- The fallback behavior when document-level metadata for article/section anchors is missing entirely from a highly relevant text snippet.

### Likely later evaluation needs
- Benchmarking the reliability of the article/section anchor extraction against the real curated corpus format.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Pass | "Final Answer Composer: Produce the final answer only from the approved evidence ledger." | None. |
| R2 | Pass | "Build a ranked retrieval plan that starts from regulation and referenced standards, then expands..." | None. |
| R3 | Pass | "Conflicts between source layers are preserved as separate ledger entries." | None. |
| R4 | Pass | "Unsupported claims are either dropped or explicitly marked as uncertain before the final synthesis stage." | None. |
| R5 | Pass | "EU-first fit: Very strong. The pipeline naturally starts from high-rank EU-level sources." | None. |
| R6 | Pass | "Expected latency posture: Medium to medium-high... explicitly trade speed for defensibility." | None. |
| R7 | Pass | "Web expansion is used only when the curated corpus leaves a documented gap. The allowed target set is defensive..." | None. |
| R8 | Pass | Focus is placed on producing a traceable, provisional grouping within a ledger. | Ledger extraction depth may be limited by prompt capacity. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Strong fit. | Provisional clustering may stay shallow because it targets traceability over relationship mapping. |
| Scenario A | Strong fit. | Lateral discovery across poorly linked project documentation relies purely on retrieval performance. |
| Scenario B | Strong fit. | Best-effort DE reasoning might miss implicit national signals if strict metadata filtering hides them. |
| Scenario C | Good fit. | Narrow standard comparisons may be slightly constrained compared to a persistent graph of standard clauses. |
| High-risk failure pattern | Good fit. | An entirely missed governing source in retrieval could still lead to a plausible but structurally incomplete output. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Source-role fidelity is actively preserved because the Source Role and Conflict Controller acts strictly as a gatekeeper before synthesis.
- Evidence links are generated ephemerally, which protects against stale linkage but demands high extraction reliability on every run.
- Blocks unsupported claims firmly via the explicit ledger mechanic.

#### System / Data / Performance
- Depends strongly on the assumption that article- and section-level anchors can be extracted on the fly.
- Operational and maintenance risks center around tuning the Ranked Retrieval Planner across evolving corpus domains.
- The latency cost is acceptable and well aligned with deep-research goals.

#### Research Workflow / User Value
- Will significantly reduce manual landscape reconstruction because it presents the user with an openly sourced ledger of conflicting or conforming claims.
- Allows researchers to instantly trace a statement to its governing artifact.
- Deep clustering of requirements might still require manual user intervention if the initial query is broadly scoped.

## 4. Option B review

### Summary verdict
- Overall verdict: High potential but risky for V1.
- Short rationale: The persistent graph perfectly answers cross-layer relationship tracking and standards interpretation, but the up-front maintenance and ingestion burden likely eclipses V1 scope constraints.

### Supported findings
- Relies on a persistent provenance graph to encode source roles, jurisdictions, and relationships before querying.
- Graph traversal explicitly predates text evidence packaging, making relationships structural rather than inferred at runtime.
- Web expansion formally attaches new nodes to the graph rather than injecting raw text.

### Judgment calls
- Upfront modeling dramatically improves relationship-heavy queries (primary success scenario) but creates a high barrier to entry for unstructured/weakly-linked national materials.
- Graph completeness simultaneously acts as the system's biggest strength and its most silent failure risk; missing edges might aggressively mislead the planner into treating a lack of evidence as a true negative.

### Unresolved uncertainties
- The manual vs. automated effort required to maintain the graph schema and provision-level links as regulations naturally evolve.
- How ambiguous or conflicting citations are handled during the initial graph ingestion phase before a specific user query provides necessary context.

### Likely later evaluation needs
- Evaluating the quantitative cost and human effort of graph ingestion on a representative sample of EU and DE documents prior to a V1 commitment.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Pass | "Assemble graph-derived evidence into a synthesis-ready package... Synthesize the answer from the evidence set" | None. |
| R2 | Pass | "traverse the provenance graph across regulation, acts, referenced standards..." | Assumes graph maintains these links dynamically. |
| R3 | Pass | "Source role is encoded directly in node and edge types..." | None. |
| R4 | Pass | "Missing edges or weakly grounded nodes are a first-class uncertainty source and should be made visible" | None. |
| R5 | Pass | "EU-level sources can anchor the graph model." | None. |
| R6 | Pass | "Strong, because the design explicitly spends effort on structured provenance before answering." | None. |
| R7 | Pass | "Web expansion is used to attach missing official material as new, typed graph inputs..." | None. |
| R8 | Pass | Reviewable by examining whether graph outputs structurally reduce manual reconstruction. | Graph maintenance could stall the path to value. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Excellent fit. | Up-front graph model may overfit one document family and hallucinate certainty in provisional groupings. |
| Scenario A | Excellent fit. | National documents with weak internal linking only enter as coarse nodes, diluting value. |
| Scenario B | Good fit. | Best-effort DE handling will be thin without significant custom normalization effort for German sources. |
| Scenario C | Good fit. | Protocol nuances still rely heavily on text-passage retrieval, which graph structure cannot entirely replace. |
| High-risk failure pattern | Very good fit. | Silent graph incompleteness (a missing relation edge) will hide the governing source and fail the user invisibly. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Source-role fidelity is hardcoded into the data models. This provides near-perfect compliance if the graph is accurate.
- Evidence links won't break at runtime, but they might be incorrectly mapped during ingestion.
- The option heavily prevents unsupported claims, provided the graph relationships are complete.

#### System / Data / Performance
- Total dependency on the ability to segment provisions and reference links reliably.
- The highest maintenance risk among the severe options due to schema evolution and data integrity requirements.
- Retrieval latency is very low, but data engineering cost is extraordinarily high.

#### Research Workflow / User Value
- Best-in-class for reducing manual reconstruction because related provisions are physically mapped to each other.
- Fits the deep-research workflow seamlessly.
- The user will heavily need to intervene if the graph lacks the edges necessary to traverse to a required member-state act.

## 5. Option C review

### Summary verdict
- Overall verdict: Viable, but overly complex for baseline V1 needs.
- Short rationale: The orchestration model handles mixed-layer ambiguity aggressively and naturally mirrors human research, but introduces severe latency, token cost, and orchestration instability for standard queries.

### Supported findings
- Uses a multi-worker model with dedicated specialists (Regulatory, Standards, Implementation/Web) to decompose tasks.
- A Claim Adjudicator acts as a chokepoint to resolve contradictions before final synthesis.
- Exposes uncertainty naturally by highlighting where specialists actively contradict one another or fail to secure evidence.

### Judgment calls
- Extremely flexible and likely the best fit for deeply ambiguous questions, but introduces high instability. Specialist drift is a notorious problem in multi-agent patterns.
- Demands rigorous agent prompting and strict tool boundaries to prevent specialists from overlapping searches and multiplying costs arbitrarily.

### Unresolved uncertainties
- The heuristic for the orchestrator to decide when *not* to decompose a simple question.
- How the adjudicator resolves situations where a lower-ranked specialist finds explicit, highly relevant web evidence while a higher-ranked specialist finds dense, tangentially related regulation evidence.

### Likely later evaluation needs
- Tuning the adjudicator's prompts to strictly enforce source hierarchy without blindly dismissing useful implementation context.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Pass | "Merge specialist outputs into the shared ledger... Compose the final answer from the adjudicated ledger" | None. |
| R2 | Pass | "Dispatch the relevant specialists with shared evidence and source-role rules." | None. |
| R3 | Pass | "Claim Adjudicator: Resolve conflicts, preserve hierarchy... makes it visible" | None. |
| R4 | Pass | "... downgrade unsupported conclusions before answer composition." | Adjudicator prompt must be extremely robust. |
| R5 | Pass | "EU-first fit: Strong if the orchestrator always starts with regulatory and standards specialists..." | None. |
| R6 | Pass | "Expected latency posture: High... explicitly spends time on decomposition and reconciliation." | None. |
| R7 | Pass | "Web expansion is primarily the responsibility of the implementation/web specialist..." | None. |
| R8 | Pass | Can be qualitatively reviewed by auditing specialist traces against the synthesized answer. | Obscure logic across multiple agents makes review harder. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Good fit. | Consistency of grouping heavily depends on the final synthesis layer rather than systemic structure. |
| Scenario A | Very good fit. | Over-investigation could lead to excessive delays and costs for questions that are easily answered via single retrieval. |
| Scenario B | Good fit. | Implementation specialist might prematurely elevate DE web material unless the adjudicator steps in forcefully. |
| Scenario C | Good fit. | The full orchestrator setup is likely massive overkill for a targeted technical protocol query. |
| High-risk failure pattern | Good fit. | If the orchestrator poorly routes the initial task, all specialists might search the wrong spaces and miss the governing source. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Source-role fidelity requires the Adjudicator to actively correct Specialists, which adds an AI-interpretation risk layer to compliance.
- Evidence links are generated by individual specialists, and may become disjointed in the final ledger.
- Can successfully avoid unsupported claims via explicit inter-agent cross-checking.

#### System / Data / Performance
- Dependency on clear bounds around specialist domains.
- Massive operational and maintenance burden compared to non-agentic options due to complex prompt management.
- Latency is very high. Cost per query is very high.

#### Research Workflow / User Value
- Plausibly mimics reading multiple sources at once and adjudicating them, which greatly aids user trust.
- The highest level of "deep research" feeling.
- Manual verification is still needed over the Adjudicator's logic to assure it hasn't unfairly dismissed a specialist's findings.

## 6. Baseline review

### Summary verdict
- Overall verdict: Inadequate for production V1.
- Short rationale: Fails the non-negotiable requirement (R4) and operates purely on semantic/lexical similarity without structural awareness of source hierarchy, exposing users to flat, non-compliant evidence blending.

### Supported findings
- Employs a single-pass hybrid retrieval setup with post-hoc citation packaging.
- Explicitly lacks dedicated conflict adjudication or source-gating steps.
- Handles source-hierarchy purely through retrieval scoring preferences and lightweight post-filtering.

### Judgment calls
- Extremely vulnerable to the high-risk scenario (missing governing sources) as it cannot structurally realize a source is absent.
- Will likely fail the non-negotiable requirement in complex edge cases because conflicting evidence from varying hierarchical layers is flattened into a single context window, inviting hallucinations of authority.

### Unresolved uncertainties
- Whether lightweight post-hoc citation processing can even meet the qualitative threshold required for basic researcher trust.
- How effectively dense retrieval routing can be tuned to simulate regulatory source-preferences.

### Likely later evaluation needs
- Establishing the baseline failure rate for missing the actual governing source on complex regulatory queries.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Marginal | "Produce the answer in one synthesis pass from the retrieved evidence." | Synthesizes answers, but lacks strict adherence to source-bound constraints. |
| R2 | Pass | "Hybrid Search Index: Retrieve relevant text from the curated corpus..." | Dependent entirely on search indexing rather than traversal. |
| R3 | Fail | "Conflict handling is shallow... no dedicated adjudication layer." | Smooths over hierarchy and flattens contradictory information. |
| R4 | Fail | "Main risk... The baseline will produce plausible but under-governed answers..." | Plainly fails the non-negotiable requirement to avoid unsupported claims. |
| R5 | Pass | "Acceptable, because the curated corpus can still be weighted toward EU-level material." | None. |
| R6 | Fail | "Expected latency posture: Low to medium." | Does not enforce quality over chat-style response behavior. |
| R7 | Pass | "Web expansion is intentionally narrow and only used when the initial retrieval path looks obviously insufficient." | None. |
| R8 | Marginal | Provides a basis to judge, but likely falls short of the adoption threshold due to missing control structures. | None. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Partial fit. | Provisional grouping and cross-mapping of requirements will be erratic based on embedding similarities. |
| Scenario A | Partial fit. | Missing structural awareness makes resolving cross-layer regulatory implications largely a guess. |
| Scenario B | Partial fit. | Best-effort DE compliance is extremely fragile and prone to randomly elevating DE acts over EU primacy if similarity scores align that way. |
| Scenario C | Good fit. | Direct queries against clearly delimited standard text perform well in basic RAG setups. |
| High-risk failure pattern | Weak fit. | Almost guaranteed to succumb to the failure pattern; lower-level sources with higher lexical match will override unseen high-level sources. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Source-role fidelity will be frequently lost.
- Evidence links will be fragile, relying on post-hoc matching instead of inline provenance generation.
- Highly likely to generate unsupported or mis-attributed core claims.

#### System / Data / Performance
- Depends on the sheer richness of the curated corpus.
- Very low maintenance and operational risk.
- Excellent latency and low architectural complexity.

#### Research Workflow / User Value
- Will not reliably reduce manual landscape reconstruction because the user cannot trust its hierarchical judgment.
- Fails the core deep-research constraint of authority-aware synthesis.
- Requires heavy manual intervention to verify the cited articles actually carry the authority the agent claims they do.

## 7. Optional cross-option notes

- The trade-off spectrum is very clear: Option B pays up front in data engineering, Option C pays at runtime in compute/complexity, and Option A pays a balanced middle ground in pipeline engineering. The Baseline demonstrates clearly why architectural mechanisms for source hierarchy are mandatory for this specific use case.
