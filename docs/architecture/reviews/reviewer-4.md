# External Reviewer Batch Review

Status: completed external review
Reviewer ID: `reviewer-4`
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

- Review logic below is requirements-first. Favorable comments are limited to cases where the plan materially supports the frozen requirements basis.
- All four plans use the expected common structure and scenario set, so they are reviewable as one comparable wave.
- No blocker-level requirements contradiction surfaced from these frozen plans. No `Potential requirements patch:` is being raised in this batch review.
- The main comparative fault line is not "simple versus sophisticated" in the abstract; it is whether the option gives enough explicit control against plausible but wrongly supported core claims while still reducing manual source-landscape reconstruction.

## 3. Option A review

### Summary verdict
- Overall verdict: `Strongest serious V1 fit`
- Short rationale: The plan gives the clearest document-supported path from question to ranked evidence to controlled synthesis, and it is the most explicit serious option on blocking or downgrading unsupported core claims. Its main V1 weakness is not requirements fidelity but whether retrieval and anchors are good enough to keep the ledger complete.

### Supported findings
- The plan defines an explicit staged path from question analysis through ranked retrieval, evidence normalization, conflict control, and final synthesis.
- The curated corpus is privileged, and web expansion is explicitly gap-driven and restricted to acceptable official or standards-like sources.
- Source ranking, source-role preservation, and conflict marking are first-class design elements rather than post-hoc answer wording.
- The plan explicitly states that unsupported claims are dropped or marked uncertain before answer composition.
- EU-first handling is built into the retrieval planner, with Germany and other national material treated as a controlled extension rather than a baseline dependency.

### Judgment calls
- This is the strongest serious option against the non-negotiable requirement to avoid unsupported or wrongly supported core claims.
- The same conservative evidence gating that helps compliance may also make the option somewhat less rich on relationship-heavy grouping or exploratory discovery than the more ambitious alternatives.

### Unresolved uncertainties
- The plan depends heavily on usable article or section anchors in the initial corpus, but it does not show how anchor extraction quality will be validated.
- Retrieval completeness remains the main residual risk: a governing source that is never retrieved will not be corrected by the ledger.
- The primary success scenario calls for provisional grouping, but the plan is more explicit about evidence control than about grouping quality.

### Likely later evaluation needs
- Stress-test whether the ranked retrieval path still finds the highest-available governing source when relevant material is distributed across regulation, annexes, standards, and official project documents.
- Measure anchor extraction quality on the highest-value EU and standards documents because the design assumes anchor-level citation support.
- Compare the usefulness of provisional requirement grouping from this option against a relationship-heavier option on the primary success scenario.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Meets | The answer flow explicitly ends with the final answer being composed only after retrieval, evidence normalization, and ledger approval. | None beyond normal dependence on retrieval quality. |
| R2 | Meets | The ranked retrieval planner starts from regulation and referenced standards and expands to official project or web material only when needed. | Lateral discovery across weakly linked project or national material may still be uneven. |
| R3 | Meets | Source ranking, source roles, conflict markers, and separate answer segments for confirmed, interpretive, and open points are explicitly described. | The plan still relies on correct evidence normalization to preserve these distinctions consistently. |
| R4 | Meets | The source-role and conflict controller is defined to block or downgrade unsupported claims before final synthesis. | If the governing source is missed during retrieval, the guardrail cannot compensate for the missing evidence. |
| R5 | Meets | The plan sets initial EU-first scope and treats Germany or national reasoning as a controlled extension. | National best-effort coverage may remain thin where metadata is sparse. |
| R6 | Meets | Stage gates and explicit evidence control are presented as an intentional trade of speed for defensibility. | Latency may be noticeable, but that is consistent with the requirements basis. |
| R7 | Meets | The curated corpus is the primary base, and web expansion is both gap-driven and limited to acceptable official domains. | The exact gap-detection rule is not specified. |
| R8 | Meets | The plan gives a plausible basis to judge whether it reduces manual reconstruction: cross-layer retrieval plus controlled synthesis are explicit and scenario-mapped. | The qualitative threshold will still need practical testing on grouping-heavy questions. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Can likely extract proposal and annex requirements, connect them in one evidence ledger, and keep the grouping explicitly provisional; enough for V1 if anchor quality is adequate. | Requirement clustering may stay shallow because the plan is optimized more for traceability than for richer structure discovery. |
| Scenario A | Has a clear cross-layer path through regulation, implementing acts, standards, and official implementation material; enough for V1. | Weakly linked national or project documents may still depend on raw retrieval quality rather than modeled relationships. |
| Scenario B | Matches the EU-first then DE-best-effort requirement well and is likely enough for V1. | Sparse national metadata may limit how confidently member-state discretion can be characterized. |
| Scenario C | Well suited to protocol-distinction questions because targeted standards retrieval and anchor-level evidence are explicit; enough for V1. | Nuanced protocol interpretation may still be less graceful than in a more relationship-aware design. |
| High-risk failure pattern | Better defended than the other options because ranked planning and ledger approval explicitly look for higher-ranked support; likely enough for V1 if retrieval is strong. | The remaining failure mode is a cleanly reasoned answer built on an incomplete retrieval set. |

### Reviewer-perspective notes

#### Traceability / Compliance
- This is the clearest plan on preserving source-role fidelity from retrieval through final answer composition.
- It gives the most explicit direct control against unsupported core claims, but it is still vulnerable to silent retrieval misses.

#### System / Data / Performance
- Complexity, cost, and maintenance look plausible for V1 relative to the other serious options.
- Corpus structure quality is a real dependency because weak anchors or weak rank signals directly reduce the value of the evidence ledger.

#### Research Workflow / User Value
- This option is likely to reduce repeated manual reconstruction on the core EU-first research workflow.
- Users may still need extra manual work when the value comes mainly from relationship-heavy grouping rather than from disciplined evidence assembly.

## 4. Option B review

### Summary verdict
- Overall verdict: `Promising but high V1 delivery risk`
- Short rationale: The plan is strong on explicit cross-layer relationship modeling and could be very effective for tracing provision chains and provisional grouping, but its requirements fit depends heavily on graph completeness and ongoing ingest quality. The plan is less explicit than Option A about a hard guardrail that stops weakly supported claims from becoming answer text.

### Supported findings
- The plan uses a persistent provenance graph with typed sources, provisions, references, jurisdiction markers, and provenance links as the primary organization layer.
- The answer path still includes concrete passage retrieval and final synthesis, so it is not graph browsing alone.
- The curated corpus remains the preferred substrate, and web additions are supposed to be typed before influencing synthesis.
- Source role and ranking are encoded in the graph model and are available during both traversal and answer construction.
- The plan itself identifies graph incompleteness and maintenance burden as major V1 risks.

### Judgment calls
- If graph ingest matures well, this option may be the strongest for the primary success scenario's grouping and cross-reference needs.
- For V1, the risk is that the graph creates a sense of governed completeness before the underlying extraction and linking quality is actually dependable.

### Unresolved uncertainties
- The plan does not show how provision segmentation, reference extraction, and graph quality will be verified on the actual corpus.
- It is unclear how well weakly linked national or project material would be normalized without significant extra modeling effort.
- The plan says missing or weakly grounded nodes should remain visible, but it does not define a concrete answer-blocking rule parallel to Option A's controller.

### Likely later evaluation needs
- Benchmark graph completeness on the exact source layers in scope, including references between proposal text, annex material, implementing acts, and standards.
- Run failure probes where the graph is intentionally incomplete to see whether the system visibly degrades or silently overstates confidence.
- Measure whether the graph materially improves provisional requirement grouping and source-landscape reconstruction enough to justify the higher ingestion burden.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Meets | The plan includes graph-guided traversal, passage retrieval, evidence packaging, and final answer composition. | None material beyond dependence on ingest quality. |
| R2 | Meets | The graph is intended to cover regulation, implementing acts, referenced standards, official project material, and typed web additions. | National or weakly linked project material may only enter the graph at coarse granularity. |
| R3 | Meets | Source role, jurisdiction, and ranking are encoded directly in graph nodes and edges, and conflicts are represented as competing paths or claims. | Hidden graph incompleteness can still distort the apparent hierarchy. |
| R4 | Partially meets | Weakly grounded nodes and missing edges are supposed to stay visible, and the composer preserves ranking and uncertainty. | The plan does not define an equally explicit block or downgrade mechanism for unsupported core claims before answer emission. |
| R5 | Meets | EU-level sources anchor the graph, and Germany or national material is described as feasible but coarser best-effort work. | National nuance may lag unless those materials are normalized beyond document level. |
| R6 | Meets | The option explicitly invests in structured provenance before answering and accepts higher ingest effort. | Up-front modeling effort may delay useful V1 output. |
| R7 | Meets | The curated corpus is ingested first and remains primary; web expansion adds typed official material rather than unconstrained browsing. | The quality of typing and provenance assignment becomes part of the answer-quality risk. |
| R8 | Partially meets | The plan is reviewable through the scenario set and cost or maintenance view, and it plausibly targets reduced manual reconstruction. | Without graph-quality evidence, it is hard to tell whether success reflects genuine coverage or only a polished but incomplete graph. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Potentially very strong because proposal-annex relations and grouping can become first-class graph operations; enough for V1 only if ingest maturity is real. | The graph may make provisional grouping look more settled than the requirements basis allows. |
| Scenario A | Well aligned for explicit regulation-to-acts-to-standards chains and likely enough for V1 on strongly cited material. | Weakly linked national or project documents may remain coarse and reduce cross-layer completeness. |
| Scenario B | Can support EU-first reasoning and jurisdiction-aware obligation analysis; borderline but plausible for V1. | Germany best-effort handling looks thin unless national materials receive more normalization work than the plan commits to. |
| Scenario C | Can support protocol-distinction answers if standards sections and links are well normalized; enough for V1 if standards ingest is strong. | The final explanation still depends on text interpretation quality, not on graph structure alone. |
| High-risk failure pattern | Strong in principle because absent required link types can expose missing higher-ranked support; not clearly enough for V1 without graph-quality controls. | The same graph can hide missing governing sources if extraction or linking quality is weaker than assumed. |

### Reviewer-perspective notes

#### Traceability / Compliance
- The option has strong potential traceability because provenance is a first-class model element.
- Compliance risk shifts from answer composition to graph construction: bad or missing graph links can mislead later steps while looking rigorous.

#### System / Data / Performance
- This is the heaviest ingestion and maintenance design in the set aside from multi-worker orchestration.
- Schema evolution, graph integrity, and reference extraction quality look like significant ongoing burdens for a V1 corpus.

#### Research Workflow / User Value
- If the graph is reliable, this option could reduce repeated manual cross-source reconstruction more than the other options on relationship-heavy questions.
- Early V1 user value may be delayed if too much effort is spent on normalization before the graph reaches dependable coverage.

## 5. Option C review

### Summary verdict
- Overall verdict: `Flexible but operationally risky for V1`
- Short rationale: The plan is well aligned with ambiguity-heavy mixed regulatory and technical questions, and it explicitly preserves source-role control through a shared ledger and adjudicator. Its main issue is not conceptual fit but the operational risk that decomposition, specialist drift, and opaque reconciliation will make the architecture harder to trust and maintain than the requirements basis requires for V1.

### Supported findings
- The plan defines specialist roles for regulatory, standards, and implementation or web investigation, with a shared evidence ledger and final adjudication step before answer composition.
- The curated corpus remains the first search space, and web expansion is explicitly constrained rather than generic browsing.
- Source-role enforcement and conflict handling are central responsibilities of the adjudicator.
- The plan explicitly acknowledges high latency, high operating cost, and high maintenance burden.
- The plan itself identifies specialist drift and opaque adjudication as key failure modes.

### Judgment calls
- This option is likely strongest on ambiguity-heavy questions where different source families genuinely need different investigation styles.
- For V1, the added flexibility may not justify the added control burden unless decomposition discipline is exceptionally strong.

### Unresolved uncertainties
- The plan does not show how the orchestrator decides when decomposition improves answer quality versus when it only adds cost and drift.
- The shared ledger is doing a large amount of control work, but the plan does not specify the strictness of that schema or how adjudication remains inspectable.
- It is unclear how reproducible the same answer path would be across repeated runs of the same question if specialists vary in scope or emphasis.

### Likely later evaluation needs
- Compare simple and complex queries to see whether the orchestrator decomposes only when needed or over-investigates routinely.
- Probe for source-role drift by injecting lower-rank implementation material and checking whether the adjudicator consistently prevents false elevation.
- Measure answer quality gains versus added latency and cost on the scenario set, especially the ambiguity-heavy and high-risk cases.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Meets | The plan includes specialist investigations, shared evidence merging, adjudication, and final answer composition. | The reasoning path may become harder to inspect than in the staged pipeline if specialist outputs are not normalized tightly. |
| R2 | Meets | The specialists cover regulation, implementing acts, standards, and official project or national implementation material under controlled rules. | Coverage quality depends on the orchestrator assigning the right specialist mix and boundaries. |
| R3 | Meets | Source-role enforcement is centralized in the adjudicator, and conflicts are intended to remain visible rather than flattened. | Multiple specialists create more opportunities for source-role drift before adjudication. |
| R4 | Meets | The claim adjudicator is explicitly responsible for downgrading unsupported conclusions before answer composition. | The strength of this safeguard depends on how strict the shared ledger and adjudication logic actually are. |
| R5 | Partially meets | The plan says EU-first handling is strong if the orchestrator begins with regulatory and standards specialists and then extends to Germany on a best-effort basis. | EU-first control is partly conditional on orchestration discipline rather than being guaranteed by a fixed path. |
| R6 | Meets | The option explicitly spends more time on decomposition and reconciliation to improve answer quality. | The quality gain over simpler options is asserted rather than demonstrated. |
| R7 | Meets | The curated corpus is the first search space, and web expansion is restricted to the implementation or web specialist after documented gaps. | Lower-rank web material may still enter too early if orchestration or adjudication is lax. |
| R8 | Meets | The plan is scenario-mapped and gives a plausible basis for judging whether it reduces manual reconstruction on hard mixed questions. | Practical usefulness may be undermined if the architecture spends too much effort on decomposition for ordinary prompts. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Can cover proposal, annex, and supporting material through specialist division of labor and produce a provisional grouped answer; plausible for V1. | Grouping consistency depends on adjudication and synthesis discipline rather than on one stable structural model. |
| Scenario A | Very well matched to the multi-layer nature of the question and likely enough for V1 if cost tolerance is real. | The design may over-investigate and become more expensive than the value of the answer justifies. |
| Scenario B | Can anchor EU-first reasoning and extend into Germany as best effort; plausible but only borderline for V1. | Lower-rank implementation material may enter the evidence pool too early unless the adjudicator is strict. |
| Scenario C | Can answer the protocol distinction well through a standards specialist and section-level evidence; enough for V1. | The full orchestrator may be more machinery than the scenario usually needs. |
| High-risk failure pattern | Better than the baseline because multiple specialists and adjudication can cross-check evidence; not fully convincing for V1 yet. | A poorly decomposed investigation can still miss the governing source while creating an impression of thoroughness. |

### Reviewer-perspective notes

#### Traceability / Compliance
- The shared ledger and adjudicator are the right control points for preserving source-role fidelity, but they are also the main trust bottleneck.
- Compared with Option A, more of the compliance burden is pushed into orchestration discipline and less into a fixed, auditable sequence.

#### System / Data / Performance
- This option has the highest likely token, control, and maintenance overhead in the set.
- It also has the greatest risk of duplicated work or non-deterministic behavior unless specialist roles and schemas are tightly bounded.

#### Research Workflow / User Value
- The design fits ambiguity-heavy and mixed-source research well and could be valuable on the hardest questions in scope.
- For routine questions, users may pay substantial latency and complexity overhead for limited additional benefit over a more disciplined single-path design.

## 6. Baseline review

### Summary verdict
- Overall verdict: `Credible control, weak target V1`
- Short rationale: The baseline is appropriately simple and useful as a control option, but the plan is materially weaker than the serious options on the non-negotiable requirement to avoid unsupported or wrongly supported core claims. It is review-worthy as a baseline precisely because its main failure mode stays visible.

### Supported findings
- The plan uses the simplest retrieval-and-synthesis path in the set and intentionally avoids graph modeling, specialist orchestration, and dedicated evidence-control staging.
- The curated corpus remains the main source base, and web fallback is narrow and limited to acceptable official domains.
- Citation handling is post-hoc and source-role control is explicitly described as lighter than in the serious options.
- Conflict handling is shallow and uncertainty is mostly represented through answer wording instead of a stronger internal control state.
- The plan itself says it is the option most likely to return a plausible answer while missing the governing source.

### Judgment calls
- This is a credible baseline and a useful control for testing whether added architecture complexity genuinely improves source-bound research quality.
- It is not a strong candidate for the target V1 architecture if the requirements basis is taken literally, because its weakest area overlaps the requirements basis's worst failure mode.

### Unresolved uncertainties
- The plan does not define how retrieval confidence is judged before web fallback is triggered.
- It is unclear how reliable post-hoc citations and basic anchors will be when the synthesis step has no stronger evidence-control layer.
- The plan assumes the curated corpus is rich enough that simple retrieval is not immediately disqualifying, but that assumption is not substantiated here.

### Likely later evaluation needs
- Measure the rate of plausible but under-supported answers, especially on the high-risk failure pattern and Scenario B.
- Compare post-hoc citation accuracy and source-role fidelity against Option A's ledger-based control path.
- Test whether the baseline materially reduces manual source reconstruction at all on multi-layer questions or mainly works on narrow direct lookups.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Partially meets | The answer flow includes a synthesis step over retrieved evidence rather than stopping at snippet retrieval. | The reasoning and evidence-control path is shallow and largely implicit compared with the must-have emphasis on source-bound synthesis. |
| R2 | Partially meets | The design can search the curated corpus and use narrow official-web fallback when retrieval looks weak. | It lacks an explicit cross-layer planning step, so reaching all mandatory source layers is more accidental than governed. |
| R3 | Partially meets | The plan says source roles can be represented and conflicts can be noted if visible. | Source-role fidelity and conflict exposure are both lighter and more dependent on what happens to be retrieved. |
| R4 | At risk | The only safeguards are post-hoc citation packaging, light filtering, and answer wording about uncertainty. | The plan itself acknowledges that plausible but under-supported core claims are its main failure mode. |
| R5 | Meets | The baseline can still be weighted toward EU-level material and does not depend on broad national coverage to function. | Germany best-effort handling is weakly controlled. |
| R6 | Partially meets | The plan is simple and low-cost, but it does not inherently enforce a quality-first control flow. | Speed and simplicity are achieved partly by removing evidence-governance steps that the requirements basis treats as important. |
| R7 | Meets | The curated corpus is primary, and web expansion is narrow and restricted to acceptable official or standard-setting sources. | The fallback trigger and evidence-governance after web expansion are under-specified. |
| R8 | Meets | As a control option, it is easy to evaluate qualitatively against whether it reduces manual reconstruction on the scenario set. | Reviewability does not change the fact that it may still be too weak on the core failure mode. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Can produce a first synthesis from proposal and annex material, but not convincingly enough for target V1. | Provisional grouping and cross-document linking are likely shallow and unstable. |
| Scenario A | Can retrieve some relevant regulation and standards material, but only partially covers the cross-layer need; not enough for target V1. | There is no strong mechanism for governed gap-filling across layers. |
| Scenario B | Can give an EU-first answer if the right source happens to be retrieved, but not reliably enough for target V1. | Source-role distinction between EU obligations and member-state discretion is too lightly controlled. |
| Scenario C | Can handle narrow direct protocol questions if the right standards sections are retrieved; acceptable as a control but not a strong target V1 basis. | Answer quality falls quickly when the governing section is not in the initial retrieval set. |
| High-risk failure pattern | This is the least defended option against the requirements basis's worst failure and is not enough for target V1. | Missing higher-ranked governing sources is hard to detect without a stronger internal evidence-control layer. |

### Reviewer-perspective notes

#### Traceability / Compliance
- This option is weakest on the non-negotiable source-support requirement because source-role control is mostly post-hoc.
- It is still a useful baseline because the main compliance failure is explicit rather than hidden behind richer machinery.

#### System / Data / Performance
- The baseline has the lowest complexity, cost, and maintenance burden in the set.
- That simplicity is purchased by giving up much of the explicit governance that the serious options use to defend answer quality.

#### Research Workflow / User Value
- It may help on narrower direct questions and on cases where the curated corpus already contains the obvious governing source.
- It is less likely to reduce repeated manual source-landscape reconstruction on the multi-layer research questions that motivated the system.

## 7. Optional cross-option notes

- No blocker-level requirements patch appears necessary from the frozen plan set.
- Option A is the best documented match to the non-negotiable support-fidelity requirement with a V1-plausible control burden.
- Option B offers the strongest structure for relationship-heavy discovery, but only if graph completeness and maintenance are better than the plans can currently prove.
- Option C offers the most flexibility on ambiguity-heavy mixed questions, but that flexibility comes with the highest control and reproducibility risk.
- The baseline is doing the right job as a control: it is credible enough to compare against, but clearly exposes the quality risks that the serious options are trying to solve.
