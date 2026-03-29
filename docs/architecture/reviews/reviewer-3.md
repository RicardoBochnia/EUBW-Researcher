# External Reviewer Batch Review

Status: complete
Reviewer ID: `reviewer-3`
Review scope: all four frozen architecture options

## 1. Inputs used

- Requirements basis: [../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- Masterplan: [../MASTERPLAN.md](../MASTERPLAN.md)
- Review rubric: [../REVIEW_RUBRIC.md](../REVIEW_RUBRIC.md)
- Requirements patches: [../REQUIREMENTS_PATCHES.md](../REQUIREMENTS_PATCHES.md) — no patches raised at review freeze
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
- Overall verdict: Strong V1 candidate with the best direct alignment to the non-negotiable requirement.
- Short rationale: The stage-gated evidence ledger approach maps most naturally to the requirements basis's emphasis on avoiding unsupported or wrongly supported core claims, explicit source-role preservation, and quality-over-latency. It achieves this without requiring heavy up-front corpus modeling or multi-agent coordination.

### Supported findings
- The plan explicitly defines a path from retrieved material through an evidence ledger to a synthesized final answer (sections 3–4), directly addressing R1.
- The Ranked Retrieval Planner and Layered Retriever Stack document access paths for regulation, implementing acts, referenced standards, and official project/web material (section 3), satisfying R2.
- Source Role and Conflict Controller is a dedicated component for preserving hierarchy, marking contradictions, and blocking unsupported claims (section 3), directly targeting R3 and R4.
- The plan explicitly describes EU-first scoping in the Query Intent and Scope Analyzer and treats national-level extension as controlled rather than default (sections 4, 8), matching R5.
- Stage gates between retrieval, evidence normalization, and synthesis trade speed for defensibility (section 8), matching R6.
- Web expansion is gap-driven and occurs only after curated high-rank retrieval has been attempted (sections 2, 5), matching R7.
- The plan acknowledges that provisional clustering may stay shallow (scenario coverage table) and that conservative evidence gating may reduce richness (section 10), providing a basis for later V1 success evaluation under R8.

### Judgment calls
- The evidence ledger is described as ephemeral and per-query. This is likely the right trade-off for V1 simplicity, but it means cross-query learning or iterative deepening across sessions is architecturally absent. Whether this matters for V1 depends on how the researcher actually uses the tool across sessions.
- Option A's reliance on retrieval quality is honest and well-documented, but the plan does not describe a concrete fallback if the retrieval planner's ranked ordering returns poor results from the curated corpus e.g., because document-level metadata is too coarse. The claim of "Strong for V1" in scenarios A and B is plausible but not proven.
- The "confirmed / interpretive / open" answer segmentation described in section 5 is a strong idea that maps well to the requirements basis's visibility expectations, but no concrete output format or user-facing example is given. Whether this works in practice is an evaluation-time question.

### Unresolved uncertainties
- The plan's first data assumption — that the curated corpus provides article/section-level structure for anchor-level citations — is load-bearing for the entire evidence ledger. If this assumption fails, the pipeline degrades to document-level citation, which may not satisfy the preferred evidence form in requirements §7.
- No detail is given on how the Query Intent and Scope Analyzer determines whether a question is "broad or specific" or what happens when it misjudges. This is a practical concern for scenarios like Scenario A where the right scope determination is non-trivial.
- The claim that the Source Role and Conflict Controller can "block" unsupported claims before final synthesis is stated but not mechanistically described. Whether this is a hard gate or a soft filter affects how well R4 is actually met.

### Likely later evaluation needs
- Empirical testing of anchor-level citation quality on the actual curated corpus.
- Evaluation of retrieval planner effectiveness on cross-layer questions (Scenario A type) where source layers are weakly linked.
- Testing whether the conflict controller actually prevents false elevation in realistic adversarial or ambiguous cases.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Met | Sections 3–4 describe an explicit path from retrieval through evidence ledger to synthesized answer with reasoning. The Final Answer Composer operates only on the approved ledger. | None. |
| R2 | Met | Section 3 (Ranked Retrieval Planner, Layered Retriever Stack) and section 5 (web expansion) together cover regulation, implementing acts, standards, and official project/web material. | Lateral discovery across weakly linked documents depends on retrieval quality, not modeled relationships; acknowledged as a weak point. |
| R3 | Met | Source Role and Conflict Controller is a dedicated component. Conflicts are preserved as separate ledger entries. Source ranking is explicit. | No concrete example of how hierarchy is represented in the final answer output. |
| R4 | Met | Plan states unsupported claims are "either dropped or explicitly marked as uncertain before the final synthesis stage" (section 5). Source Role and Conflict Controller is responsible. | The mechanism is described at design level but not mechanistically detailed. Whether "dropped" vs. "marked" decisions are auditable is unspecified. |
| R5 | Met | EU-first scoping is set by the Query Intent and Scope Analyzer; national extension is controlled (section 8). | None. |
| R6 | Met | "Stage gates and evidence control intentionally trade speed for defensibility" (section 8). Multi-step processing with explicit gates is inherently quality-first. | None. |
| R7 | Met | Web expansion is gap-driven and constrained to official sources (sections 2, 5). Curated corpus is the primary base. | None. |
| R8 | Met with caveat | The plan documents honest weak points per scenario and acknowledges where depths limits exist (section 7). Provides a plausible basis for later qualitative success judgment. | Provisional clustering is acknowledged as shallow; success on the primary scenario's grouping dimension may be limited. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Strong coverage. Pipeline can extract, align, and provisionally group requirements from proposal and annex via the evidence ledger. | Grouping quality may be shallow because the design optimizes for traceability first. |
| Scenario A | Strong coverage. Stage-gated cross-layer retrieval handles the multi-layer traversal naturally. | Discovery of weakly linked national/project documents depends on retrieval quality, not structural modeling. |
| Scenario B | Strong coverage. EU-first by design; Germany extension is controlled. | Best-effort national reasoning depends on metadata quality for national materials. |
| Scenario C | Good coverage. Anchor-level evidence supports protocol distinction explanation. | Edge-case protocol interpretation may be less elegant than in model-rich designs. |
| High-risk failure pattern | Good coverage. Ranked planner actively looks for missing higher-ranked sources. | If retrieval misses a source entirely, the pipeline can still produce a plausible but incomplete answer. This is the key residual risk. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Source-role fidelity is preserved by a dedicated controller component, which is the strongest explicit mechanism among the options.
- Evidence links are anchored in the ledger, but their quality depends on corpus metadata granularity — a load-bearing assumption.
- The "block or downgrade unsupported claims" mechanism directly targets the non-negotiable requirement, but its operational specifics need evaluation-time validation.

#### System / Data / Performance
- Depends heavily on article/section-level metadata in the curated corpus. If metadata is coarse, the ledger degrades gracefully (document-level citations) but loses the anchor-level traceability advantage.
- Operational complexity is moderate: more steps than baseline but no persistent infrastructure beyond the retrieval index.
- Cost and latency are medium — stage gates add time but avoid the heavy fan-out of multi-agent designs.

#### Research Workflow / User Value
- Directly reduces manual source-landscape reconstruction by providing source-bound synthesis with evidence.
- Fits the EU-first, deep-research workflow well because the pipeline naturally starts from high-rank sources and spends time on evidence quality.
- The researcher would still need manual intervention for relationship-heavy clustering and for validating completeness on questions where retrieval misses weakly linked sources.

## 4. Option B review

### Summary verdict
- Overall verdict: Architecturally ambitious with the strongest cross-layer relationship modeling, but V1 viability is uncertain due to high ingest and maintenance burden.
- Short rationale: The provenance graph design directly addresses cross-document linking and source-hierarchy modeling, which are clear pain points in the requirements basis. However, it requires the most up-front investment and carries the highest risk that graph incompleteness itself becomes a hidden failure mode.

### Supported findings
- The plan describes an explicit path from graph-guided retrieval through evidence packaging to synthesized answers (sections 3–4), satisfying R1.
- The provenance graph model with typed source nodes and edges across regulation, implementing acts, standards, and project material documents access to all required source layers (sections 3, 5), satisfying R2.
- Source role is encoded directly in node and edge types (section 5), with conflicts visible as competing graph paths (section 5), addressing R3.
- Missing edges or weakly grounded nodes are described as first-class uncertainty sources (section 5), contributing to R4. However, graph incompleteness is acknowledged as a risk (section 6).
- EU-level sources anchor the graph model (section 8), supporting R5.
- The design explicitly spends effort on structured provenance before answering (section 8), matching R6.
- The curated corpus is ingested first and preferred; web expansion attaches typed nodes (section 5), matching R7.
- Scenario coverage table provides honest V1 assessments with several "Medium" ratings, giving a basis for qualitative success judgment under R8.

### Judgment calls
- The graph-first approach is the strongest option for relationship-heavy scenarios (Scenario A, primary success scenario) if the graph is actually well-populated. This is a significant "if" for V1.
- The plan's own risk statement — that the graph may "give a false sense of completeness while actually hiding missing or weakly extracted relations" (section 6) — is a candid acknowledgment that the option's greatest strength is also its greatest vulnerability. This honest self-assessment increases confidence in the plan's analytical quality but also means the option's V1 viability is genuinely uncertain.
- The maintenance burden is rated "High" by the plan itself (section 9). For a V1 product, this is a significant concern, especially given that the requirements basis does not demand persistent knowledge modeling — it requires useful synthesis per query.
- Graph-guided retrieval could be more targeted than flat retrieval, potentially reducing the high-risk failure pattern. But this depends on graph quality, which is the core uncertainty.

### Unresolved uncertainties
- Whether the highest-value sources can be segmented into provisions and linked via references "with acceptable reliability" (Assumption 1) is the foundational uncertainty. No evidence is provided about actual corpus structure quality.
- The plan rates several scenarios as "Medium for V1" (Scenario A, Scenario B, high-risk failure pattern). Whether "Medium" is good enough depends on how many scenarios must be at least "Good" for V1 approval — a question the requirements basis does not quantify.
- Schema evolution and graph integrity maintenance are noted as ongoing concerns (section 9) but no mitigation strategy is described. The risk is that early schema decisions lock the graph into a structure that fits the initial corpus but not later additions.
- The plan does not describe what happens when a query requires information that should be in the graph but is not. Does the system fall back to text retrieval, or does it report a gap? This affects both R4 (unsupported claims) and the high-risk failure pattern.

### Likely later evaluation needs
- A proof-of-concept ingestion of 3–5 core source documents to test whether provision-level segmentation and reference linking are achievable at acceptable quality.
- Comparative evaluation of graph-guided retrieval vs. flat retrieval on the same scenario set to determine whether the graph investment yields measurably better results.
- Assessment of graph maintenance cost over a realistic corpus evolution period (e.g., when new implementing acts are published).

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Met | Sections 3–4 describe traversal from graph through evidence packaging to synthesized answer. | Synthesis quality depends on whether the graph provides enough text-level evidence, not just structural links. |
| R2 | Met | Graph model covers regulation, acts, standards, project material as typed nodes (sections 3, 5). | National/project documents with weak internal linking may enter as coarse nodes (scenario table), limiting depth on some layers. |
| R3 | Met | Source role encoded in node/edge types; conflicts appear as competing graph paths (section 5). | If graph links are incomplete, some conflicts may not be structurally visible and would need to be caught by the text layer. |
| R4 | Partially met | Missing edges and weakly grounded nodes are described as first-class uncertainty (section 5). | The plan acknowledges that graph incompleteness is itself a serious failure mode (section 6). A missing node is invisible — the system cannot detect what it does not know is absent. |
| R5 | Met | "EU-level sources can anchor the graph model" (section 8). | Germany/national handling is "feasible but likely coarser" (section 8). |
| R6 | Met | "Explicitly spends effort on structured provenance before answering" (section 8). | None. |
| R7 | Met | Curated corpus ingested first; web expansion typed by source role (section 5). | None. |
| R8 | Met with caveat | Honest V1 assessments with several "Medium" ratings provide a judgment basis. | Multiple "Medium for V1" scenario ratings may indicate that the option needs more maturity to justify the investment. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Strong if graph is well-populated. Clustering and cross-reference tracing become first-class. | Up-front graph model may overfit one document family and make provisional grouping look more certain than it is. |
| Scenario A | Excellent for explicit citation chains across layers. | National/project documents with weak linking may only enter as coarse nodes; the plan rates this "Medium for V1." |
| Scenario B | Good if jurisdiction encoding is in the graph. | Best-effort Germany reasoning is "thin unless national materials are normalized beyond document level" (plan's own assessment). |
| Scenario C | Good if standards sections are captured as graph nodes. | Detailed protocol reasoning still depends on the text interpretation layer, not the graph alone. |
| High-risk failure pattern | Very good if graph is complete; the structural approach can detect missing required link types. | Hidden graph incompleteness is itself the highest-risk failure mode for this option — the plan openly acknowledges this. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Source-role fidelity is structurally encoded, which is the strongest approach in principle.
- Evidence links are graph-backed and therefore more inspectable than flat retrieval evidence — but only for sources that are actually in the graph.
- The option's biggest compliance risk is invisible incompleteness: the graph cannot tell you what it does not contain.

#### System / Data / Performance
- Depends on the heaviest up-front corpus investment of all options: provision-level segmentation, reference extraction, and graph typing.
- Operational cost is medium-to-high; maintenance burden is rated high by the plan itself.
- Graph infrastructure (storage, query, integrity checks) adds a persistent stateful component that the other options avoid.
- Latency is medium — graph traversal may enable more targeted retrieval, partially offsetting the packaging overhead.

#### Research Workflow / User Value
- Would provide the strongest cross-layer linking and relationship-aware discovery if the graph is sufficiently complete.
- Fits the deep-research workflow well because graph-guided exploration is a natural research paradigm.
- The risk for the researcher is that the graph creates an illusion of completeness: if a source is not in the graph, the researcher may assume its absence means irrelevance, not missing data.

## 5. Option C review

### Summary verdict
- Overall verdict: Most flexible design for complex, multi-domain queries, but highest operational complexity and cost, with significant inspectability risk.
- Short rationale: The specialist orchestration approach is the most natural fit for ambiguity-heavy research questions that cross regulatory, technical, and implementation domains. However, the multi-agent decomposition, reconciliation, and adjudication introduce the most complexity and the hardest-to-audit control flow — running against the requirements basis's emphasis on inspectable, trustworthy answers.

### Supported findings
- The plan describes an explicit path from query decomposition through specialist investigation and adjudication to synthesized answer (sections 3–4), satisfying R1.
- Dedicated specialists for regulatory, standards, and implementation/web material provide role-specific access across all required source layers (section 3), satisfying R2.
- The Claim Adjudicator is a dedicated reconciliation component that resolves conflicts, preserves hierarchy, and downgrades unsupported conclusions (section 3), addressing R3 and R4.
- The plan states the orchestrator "always starts with regulatory and standards specialists before lower-rank expansion" (section 8), supporting R5.
- "Explicitly spends time on decomposition and reconciliation" (section 8), matching R6.
- Web expansion is assigned to one specialist and is domain-constrained (section 5), matching R7.
- Honest scenario assessments acknowledge multiple "Medium for V1" ratings, providing a qualitative success basis under R8.

### Judgment calls
- The specialist design is the most natural architecture for questions like Scenario A (cross-layer analysis) where the question inherently decomposes into regulatory, standards, and implementation sub-questions. However, most research questions in the requirements basis do not clearly decompose this way — the primary success scenario, Scenario B, and Scenario C are better served by a simpler pipeline.
- The plan honestly rates its own cost, latency, and maintenance posture as "High" across all three dimensions (section 9). This is the highest self-assessed operational burden of all four options. The requirements basis does not demand this level of complexity; it demands useful, source-bound synthesis with visible source roles and conflict handling.
- The adjudicator as a central reconciliation point is conceptually strong, but the plan does not describe how the adjudicator's own decisions are made transparent to the user. If the adjudicator silently resolves a conflict, this could violate R3 (making contradictions visible) even while technically satisfying R4 (blocking unsupported claims).
- The plan's Assumption 2 — that the shared evidence ledger is "strong enough to prevent source-role drift across specialists" — is critical and unproven. In multi-agent systems, coordination discipline is typically the hardest property to maintain.

### Unresolved uncertainties
- Whether the orchestrator can "keep sub-questions bounded and avoid unnecessary decomposition on simple prompts" (section 11) is a key practical question. Over-decomposition on simple questions wastes cost and latency while adding nothing to quality.
- The plan does not specify how specialist boundaries are enforced. Can the Regulatory Specialist access standards material? Can the Standards Specialist access implementation material? If boundaries are fuzzy, specialist roles become redundant.
- The adjudicator's decision-making process is not described. Whether it uses its own LLM call, rule-based logic, or a combination is unspecified. This affects both cost and inspectability.
- Interaction patterns between specialists are not described. Do specialists see each other's findings? Can the orchestrator re-dispatch after seeing partial results? The answers materially affect both quality and cost.

### Likely later evaluation needs
- A cost comparison of specialist orchestration vs. single-pipeline processing on the same question set, to determine whether the complexity premium provides measurable quality improvement.
- Evaluation of adjudicator transparency: can a researcher understand why conflicting specialist findings were resolved in a particular way?
- Testing of orchestrator decomposition quality: does decomposition improve answers for the requirements basis scenarios, or does it mainly add overhead?

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Met | Sections 3–4 describe orchestration through specialist investigation and adjudication to synthesized answer. | Synthesis occurs after a multi-stage process; the synthesis step itself depends on adjudication quality. |
| R2 | Met | Dedicated specialists for regulation, standards, and implementation/web cover all required source layers (section 3). | Specialist boundaries and access policies are described only at principle level, not operationally. |
| R3 | Met | Claim Adjudicator is dedicated to preserving hierarchy and making conflicts visible (section 3). Conflict handling is described as a primary design motivation (section 5). | If the adjudicator resolves conflicts before surfacing them, visibility may be reduced rather than increased. |
| R4 | Met | Adjudicator "downgrades unsupported conclusions before answer composition" (section 3). Source-role enforcement happens centrally (section 5). | Central enforcement depends on the shared evidence ledger being strict enough — this is Assumption 2, which is unproven. |
| R5 | Met | "Orchestrator always starts with regulatory and standards specialists before lower-rank expansion" (section 8). | None. |
| R6 | Met | "Explicitly spends time on decomposition and reconciliation" (section 8). Latency posture is high — quality clearly prioritized. | None — though the cost premium is significant. |
| R7 | Met | Web expansion assigned to one specialist with domain constraints (section 5). | None. |
| R8 | Met with caveat | Honest weakness assessment and multiple "Medium for V1" ratings provide a judgment basis. | The plan itself rates Scenario B and the high-risk failure pattern as "Medium for V1." |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Good coverage. Specialist decomposition can extract from multiple sub-documents. | Grouping consistency depends on adjudication and synthesis rather than a stable structural model — quality is less predictable. |
| Scenario A | Very good coverage. The question naturally maps to the specialist decomposition. | The design may over-investigate and incur high cost even when a simpler pipeline would suffice for this question. |
| Scenario B | Good coverage. Regulatory specialist anchors EU-first; implementation specialist extends to Germany. | Lower-rank web material may enter too early unless the adjudicator is strict — plan acknowledges this. |
| Scenario C | Good coverage. Standards specialist can focus on protocol behavior. | Full orchestrator may be overkill for a narrow technical question — acknowledged by the plan. |
| High-risk failure pattern | Good in principle. Multiple specialists can cross-check before synthesis. | If the orchestrator decomposes poorly, the system may still miss the governing source while appearing thorough — the worst kind of failure. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Source-role fidelity depends on both specialist discipline and adjudicator enforcement. Two control points is potentially stronger but also harder to audit.
- Evidence links pass through multiple processing stages (specialist → ledger → adjudicator → composer), creating more opportunities for link degradation or misattribution.
- The option addresses unsupported core claims through the adjudicator, but the adjudicator's own reasoning process is not described as inspectable.

#### System / Data / Performance
- Highest operational complexity: multi-agent coordination, shared state management, and adjudication logic.
- Cost posture is highest of all options — multiple LLM calls per specialist, plus orchestration and adjudication overhead.
- Maintenance burden is highest: prompt discipline, tool discipline, evidence-schema discipline, and inter-specialist coordination all need active upkeep.
- The plan does not describe graceful degradation if one specialist fails or returns low-quality results.

#### Research Workflow / User Value
- Would provide the most thorough investigation for genuinely complex, multi-domain questions.
- Fits the deep-research workflow for hard cases but may over-serve simple questions that do not need decomposition.
- The researcher's ability to understand why the system arrived at a particular answer is potentially weaker than in simpler designs, because the reasoning path crosses multiple agents.

## 6. Baseline review

### Summary verdict
- Overall verdict: Credible control option that fulfills its role as a simplicity benchmark. Not a viable V1 target because it does not adequately address the non-negotiable requirement.
- Short rationale: The baseline is intentionally simple and honest about its limitations. It demonstrates what a minimal credible architecture can deliver, making it valuable for comparison. However, its shallow evidence control, lack of dedicated source-role enforcement, and weak conflict handling mean it cannot reliably prevent the worst failure mode defined in the requirements basis.

### Supported findings
- The plan describes a single-pass synthesis from retrieved evidence (sections 3–4), providing a path from retrieval to answer and thus technically addressing R1. However, it stops at "answer in one synthesis pass" without a multi-stage evidence-control pipeline.
- Hybrid retrieval covers the curated corpus, with optional web fallback (sections 3, 5), providing basic coverage for R2. However, there is no ranked retrieval planner for systematic cross-layer access.
- Source ranking is "applied in a simplified way through retrieval preferences and post-hoc filtering" (section 5), providing weak coverage for R3. Conflict handling is described as "shallow" by the plan itself.
- The plan has no dedicated mechanism to block unsupported core claims. Uncertainty surfacing is "mostly as response wording rather than as a controlled internal state" (section 5). This is the weakest coverage of R4 across all options.
- EU-first fit is "Acceptable" through corpus weighting (section 8), which is a passive rather than active mechanism for R5.
- Quality-over-latency fit is described as "Mixed" by the plan itself (section 8), which is the weakest of all options for R6.
- Web expansion is narrow and constrained to acceptable sources (section 5), meeting R7.
- The plan provides honest weak assessments per scenario and explicitly says it is "useful as a control precisely because this risk stays visible" (scenario table), making it reviewable under R8.

### Judgment calls
- The baseline is fair and honest in its self-assessment. It does not try to disguise itself as a full option, which is exactly what the masterplan requires.
- "Weakest source-role control and weakest defense against plausible but under-supported synthesis" (section 8) is stated directly by the plan itself. This means the baseline cannot reliably prevent the worst failure defined in requirements §1: "a core claim is unsupported, wrongly supported, or grounded in the wrong source role without that being visible."
- The baseline's value is primarily as a comparison anchor: any serious option that does not demonstrably outperform the baseline on R3, R4, and the high-risk failure pattern has a weak justification for its additional complexity.
- Despite its limitations, the baseline could be a pragmatic starting point if time or resources force a phased approach. The requirements basis does not mandate a complex architecture — it mandates outcomes. Whether those outcomes can be achieved through retrieval quality and prompt design alone is an empirical question.

### Unresolved uncertainties
- Whether "basic metadata and reranking signals" (Assumption 2) are actually enough to prevent systematic false elevation is untested. This is the baseline's most critical practical uncertainty.
- The plan does not describe how the single-pass responder decides what to include and what to leave out. In a domain where omission is itself a risk (missing a governing source), a single-pass design without evidence control may systematically under-report.
- The "retrieval confidence" threshold that triggers web fallback is not defined. Without a clear trigger, the fallback may activate too rarely (missing useful web sources) or too often (undermining the curated-corpus-first principle).

### Likely later evaluation needs
- Head-to-head comparison with at least one serious option on the same scenario set, to quantify the quality gap that justifies additional architecture complexity.
- Testing of false-elevation frequency: how often does the baseline present medium- or low-rank sources as if they were high-rank?
- Assessment of whether prompt engineering alone can compensate for the absence of a dedicated evidence-control layer.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Partially met | Single-pass synthesis from retrieved evidence (sections 3–4). | No multi-stage evidence control. Synthesis quality depends entirely on LLM behavior in one pass, without structural guarantees. |
| R2 | Partially met | Hybrid retrieval over curated corpus with optional web fallback (sections 3, 5). | No ranked retrieval planner. Cross-layer access is opportunistic rather than systematic. |
| R3 | Weakly met | Source ranking through retrieval preferences and post-hoc filtering (section 5). Conflict handling is "shallow" (plan's own term). | No dedicated component for source-role preservation or conflict surfacing. The responder may note conflicts "if they are visible in the retrieved material" — a passive rather than active approach. |
| R4 | Not met | No dedicated mechanism defined. Uncertainty is surfaced "mostly as response wording" (section 5). | This is the central gap. The non-negotiable requirement — avoid unsupported or wrongly supported core claims — has no structural support in this design. |
| R5 | Met (weak) | Curated corpus can be weighted toward EU-level material (section 8). | Passive mechanism. No active EU-first scoping. |
| R6 | Partially met | "Can support deep-research use, but it does not inherently enforce quality-first behavior" (section 8, plan's own assessment). | No stage gates or evidence quality controls. Quality depends on retrieval luck and LLM behavior. |
| R7 | Met | Web expansion is narrow and limited to acceptable official sources (section 5). | None. |
| R8 | Met | The plan is honest about its limitations, making it reviewable. "Useful as a control precisely because this risk stays visible." | The plan itself describes the baseline as "weak as a target V1" for the primary success scenario. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Partial coverage. Can retrieve and synthesize but grouping and cross-document linking will likely be shallow and unstable. | Plan self-rates as "Acceptable as a control, weak as a target V1." |
| Scenario A | Partial coverage. Straightforward retrieval may find relevant sources. | Cross-layer linking and ranked gap-filling are weaker than serious options. |
| Scenario B | Partial coverage. EU-first answers possible if the right source is retrieved. | Germany reasoning is fragile; no strong source-layer distinction. |
| Scenario C | Good coverage for direct protocol questions if the right sections are retrieved. | If the right section is not retrieved, answer quality drops sharply with no recovery logic. |
| High-risk failure pattern | Weak coverage. This is the option most likely to produce the failure mode described in the requirements basis. | Missing higher-ranked evidence is harder to detect without a stronger evidence-control layer. This is the baseline's defining vulnerability. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Source-role fidelity relies entirely on LLM behavior and retrieval ordering, not on structural enforcement. This is the weakest traceability guarantee.
- Evidence links are attached post-hoc rather than constructed during evidence evaluation, creating risk of misattribution.
- The option does not help avoid unsupported core claims in any structural way. It relies on the LLM's own judgment, which is precisely what the requirements basis's non-negotiable property is designed to guard against.

#### System / Data / Performance
- Lowest complexity and lowest cost — appropriate for a control option.
- Depends on the curated corpus containing enough material that a simple retrieval path finds it. This is a reasonable assumption for well-curated sets but fragile for edge cases.
- Maintenance burden is the lowest: mainly corpus updates and retrieval tuning.
- No persistent infrastructure beyond the retrieval index.

#### Research Workflow / User Value
- Can reduce some manual source discovery for straightforward questions where retrieval finds the right material.
- Does not fit the EU-first, deep-research workflow as well as the serious options because it does not inherently enforce quality-first behavior.
- The researcher would need heavy manual verification because the baseline provides minimal structural assurance about source roles and evidence quality.

## 7. Optional cross-option notes

- **Non-negotiable requirement (R4) is the primary differentiator.** Option A has the most explicit, structurally enforced mechanism for blocking unsupported claims. Option B relies on graph completeness (a load-bearing assumption). Option C relies on adjudicator quality (underspecified). The baseline has no structural mechanism. Any final architecture decision should weight R4 performance heavily.
- **V1 viability vs. long-term potential.** Option B has the highest potential ceiling but the lowest V1 confidence. Option A has the best V1 risk-to-value ratio. Option C is best positioned for future extensibility but is also the most complex from day one.
- **The "Medium for V1" pattern.** Options B and C both self-rate several scenarios as "Medium for V1." This is honest, but a selection decision should clarify whether "Medium" on key scenarios is acceptable or disqualifying.
- **Inspectability is a latent requirements concern.** The requirements basis emphasizes making contradictions, hierarchy, and uncertainty visible. This implicitly requires that the system's reasoning path is itself inspectable enough for the researcher to trust it. Option A's simpler control flow supports this. Option C's multi-agent flow works against it. Option B's graph can aid it if the graph is transparent but can obscure it if the graph hides incompleteness. `Potential requirements patch:` The requirements basis does not explicitly require inspectability of the system's internal reasoning process, only of the final answer's source-role and evidence properties. Whether internal-process inspectability is a separate requirement or a derived property of the existing requirements may warrant clarification.
- **Baseline value.** The baseline serves its intended purpose well: it makes clear what the serious options need to surpass and where additional complexity must demonstrate measurable improvement. It should not be dismissed — it should be used as the empirical comparison floor.
