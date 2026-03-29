# External Reviewer Batch Review

Status: completed  
Reviewer ID: `reviewer-1`  
Review scope: all four frozen architecture options

## 1. Inputs used

- Requirements basis: `../../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md`
- Masterplan: `../MASTERPLAN.md`
- Review rubric: `../REVIEW_RUBRIC.md`
- Requirements patches: `../REQUIREMENTS_PATCHES.md`
- Option A plan: `../options/option-a/PLAN.md`
- Option B plan: `../options/option-b/PLAN.md`
- Option C plan: `../options/option-c/PLAN.md`
- Baseline plan: `../options/baseline/PLAN.md`

## 2. Global review notes

- Review basis used here is the frozen requirements basis, especially the must-haves, the non-negotiable avoidance of unsupported core claims, the EU-first V1 scope, the quality-over-latency stance, and the source-role rules.
- No blocker-level contradiction in the requirements basis was found during this review wave.
- No requirements patch is raised. Several points below are option underspecification or likely evaluation needs, not requirements defects.

## 3. Option A review

### Summary verdict
- Overall verdict: `strongest current V1 fit`
- Short rationale: `Option A is the most directly aligned with the requirements emphasis on source-bound synthesis, explicit source-role preservation, and blocking or downgrading unsupported claims before answer emission. Its main weakness is not conceptual misfit but dependence on retrieval completeness and anchor quality.`

### Supported findings
- The plan defines an explicit staged path from question analysis through ranked retrieval, evidence normalization, conflict control, and final synthesis rather than stopping at retrieval.
- The plan gives the curated corpus a privileged role and constrains web expansion to documented gaps and acceptable official source types.
- The plan treats source ranking, conflict handling, and unsupported-claim blocking as first-class controls, which is closely aligned with the worst-failure definition in the requirements basis.
- The plan is strongly EU-first and treats Germany or national material as a controlled extension rather than a baseline dependency.
- The plan explicitly accepts slower, stage-gated behavior in exchange for defensibility.

### Judgment calls
- This looks like the safest serious option for V1 because it is ambitious enough to address the core pain points without taking on the structural and maintenance burden of a full provenance graph or multi-specialist orchestration.
- The option may underserve relationship-heavy exploratory work compared with a strong graph design, but that seems like an acceptable trade in a V1 whose primary non-negotiable is avoiding wrongly supported core claims.
- The plan appears more inspectable than Option C and less maintenance-heavy than Option B, which likely helps real-world discipline in a research workflow.

### Unresolved uncertainties
- The plan does not yet specify how the ranked retrieval planner detects that a higher-ranked source is still missing rather than merely absent from the returned set.
- The evidence-ledger design is clear at a conceptual level, but the plan does not specify how fine-grained the claim units are or how anchor extraction failures are handled.
- It remains unclear how much cross-document requirement grouping can be done well without drifting toward a more persistent relation model.

### Likely later evaluation needs
- Retrieval-completeness checks on questions where a governing higher-ranked source exists but is easy to miss.
- Audits of article/section anchor quality for the highest-value EU and standards sources.
- Scenario-based tests on whether provisional grouping remains helpful without overstating certainty.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Pass | The flow explicitly ends in final answer composition from an approved evidence ledger after retrieval, normalization, and control. | None at plan level. |
| R2 | Pass | Ranked retrieval starts from regulation and referenced standards, then expands to other layers only if needed; Scenario A explicitly covers regulation, acts, standards, and implementation material. | Depends on retrieval quality rather than explicit cross-document modeling. |
| R3 | Pass | Source ranking is explicit; conflicts are preserved as separate ledger entries; unsupported claims are dropped or marked uncertain. | The exact answer rendering of hierarchy is not fully specified. |
| R4 | Pass | The Source Role and Conflict Controller blocks or downgrades unsupported claims before synthesis. | Failure remains possible if governing sources are missed upstream. |
| R5 | Pass | EU-first scope is built into question analysis and ranked retrieval; national handling is controlled extension only. | None material. |
| R6 | Pass | Stage-gated evidence control explicitly trades speed for defensibility. | None material. |
| R7 | Pass | Curated/offline corpus is primary; web expansion is gap-driven and restricted to acceptable official targets. | The exact trigger for gap detection is underspecified. |
| R8 | Pass | The option plausibly reduces repeated manual reconstruction by assembling a claim/evidence ledger across layers and composing a first-pass answer. | Practical success still depends on retrieval completeness and anchor reliability. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Strong for V1: proposal and annex material can be pulled into one controlled evidence ledger and turned into a provisional grouping. | Grouping may remain somewhat shallow because traceability is prioritized over richer structural modeling. |
| Scenario A | Strong for V1: the ranked, stage-gated flow is a natural fit for cross-layer certificate questions. | Weakly linked national or project material may still be hard to discover. |
| Scenario B | Strong for V1: EU-first reasoning is explicit and Germany is treated as best-effort extension. | National nuances may be missed if retrieval signals are weak. |
| Scenario C | Good for V1: targeted standards retrieval plus anchor-level evidence should support more than a yes/no answer. | Subtle protocol interpretation may still challenge a ledger-centered design. |
| High-risk failure pattern | Better defended than the other options except perhaps a mature graph design, because the design explicitly tries to detect and prevent under-supported synthesis. | If the higher-ranked source is not retrieved at all, the downstream controls cannot fully compensate. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Best source-role discipline of the four options at plan level.
- The explicit controller and approved-ledger concept map well to the requirement to avoid wrongly supported core claims.
- The main compliance risk is not source-role confusion inside the design, but missing evidence upstream.

#### System / Data / Performance
- Reasonable V1 complexity profile.
- Strong dependence on anchor extraction quality and ranked retrieval behavior.
- Maintenance burden appears acceptable compared with graph upkeep or multi-specialist coordination.

#### Research Workflow / User Value
- Strong fit for the actual workflow pain point of repeatedly rebuilding the source landscape.
- Likely to produce usable first-pass answers with evidence while still preserving uncertainty.
- May be less exciting for exploratory clustering than Option B, but likely more dependable in early use.

## 4. Option B review

### Summary verdict
- Overall verdict: `promising but risky for V1`
- Short rationale: `Option B is the strongest design for explicit cross-layer relationship modeling, but its V1 value depends heavily on graph-ingest quality and on not mistaking graph structure for actual completeness. That makes it attractive for the primary success scenario, yet more fragile than Option A against hidden corpus and normalization weaknesses.`

### Supported findings
- The plan defines an explicit path from query analysis to graph traversal, passage fetching, evidence packaging, and final synthesis.
- The plan gives the curated corpus a privileged role by ingesting it first into a typed provenance graph.
- Source role and jurisdiction are meant to be encoded directly in graph objects, which is stronger than leaving them implicit.
- The plan explicitly acknowledges graph incompleteness as a major risk.
- The plan accepts higher maintenance and modeling effort as the price for relationship-aware retrieval.

### Judgment calls
- This is the most attractive option if the real bottleneck is relationship-heavy cross-document navigation and provisional grouping, especially for proposal/annex/reference structures.
- It is also the easiest option to over-trust. A clean graph can make the evidence landscape look more complete and certain than it really is.
- For V1, the graph burden looks high relative to the requirements, which emphasize answer quality and source-role discipline more than persistent structural elegance.

### Unresolved uncertainties
- The plan does not define how graph quality, missing edges, or extraction errors are audited before answers rely on them.
- It is unclear how much of the relevant corpus can realistically be normalized to provision-level nodes and typed references in a V1 time horizon.
- The plan does not explain what happens when source structures are too weak for trustworthy graph normalization but still usable for text retrieval.

### Likely later evaluation needs
- Corpus audits comparing graph coverage against known reference chains and known governing sources.
- Red-team tests for false completeness, where the graph looks well connected but lacks a decisive higher-ranked source.
- Effort tracking on ingestion and schema maintenance to test whether the V1 burden is actually tolerable.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Pass | The plan ends in final answer composition from a graph-derived evidence package, not just traversal output. | None at plan level. |
| R2 | Pass with risk | The planner traverses regulation, acts, standards, and official project material in ranked order through typed provenance links. | Practical reach depends on normalization quality and graph completeness. |
| R3 | Pass | Source role and jurisdiction are encoded directly in node and edge types; conflicts appear as competing paths or conflicting claims. | The answer behavior under ambiguous or partial graph evidence is still somewhat underspecified. |
| R4 | Partial pass | The design should help detect missing higher-ranked sources and preserve provenance, which supports safer claims. | There is no explicit blocking or downgrade controller as direct as in Option A; hidden graph incompleteness could still allow wrongly supported claims. |
| R5 | Pass | EU-level sources can anchor the graph, and national handling is explicitly described as coarser best-effort extension. | None material. |
| R6 | Pass | The design spends effort on structured provenance before answering and does not optimize for chat-like speed. | None material. |
| R7 | Pass | Curated corpus is the preferred substrate; web findings are typed before influencing synthesis. | The temporary-node path for web findings is underspecified and may become messy in practice. |
| R8 | Pass with risk | If ingest works, the option clearly could reduce repeated manual source reconstruction through reusable structured links. | If ingest maturity is weak, the option may fail before that benefit appears. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Potentially excellent, because proposal and annex relationships become first-class and grouping can be graph-supported. | The graph may make provisional grouping look more settled than the requirements basis allows. |
| Scenario A | Good to very good if reference structures are explicit, because chain tracing is a core graph strength. | Weakly linked national or project material may remain coarse and reduce benefit. |
| Scenario B | Medium for V1: the design can encode jurisdiction and obligation scope, which is useful. | Germany best-effort handling may stay thin unless national material is normalized more deeply than seems realistic for V1. |
| Scenario C | Good for V1 if standards sections and references are ingested cleanly. | Text interpretation still does heavy lifting; the graph alone does not answer protocol nuance. |
| High-risk failure pattern | Potentially very good, because missing required link types could reveal missing governing sources. | Hidden graph incompleteness is itself a high-risk failure pattern and may be hard to notice. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Strong explicit provenance model.
- Good theoretical fit for preserving hierarchy and source role.
- Main compliance concern is false confidence from incomplete graph extraction rather than overt flattening.

#### System / Data / Performance
- Highest data-model and maintenance fragility relative to value promised in V1.
- Strong dependence on reliable provision segmentation and reference extraction.
- Cost may be justified later, but the plan does not yet prove V1 proportionality.

#### Research Workflow / User Value
- Attractive for complex relationship-heavy questions and for iterative clustering work.
- Risky if the user needs dependable utility soon rather than after a substantial ingest/modeling investment.
- Could reduce manual reconstruction dramatically, but only after structural maturity is achieved.

## 5. Option C review

### Summary verdict
- Overall verdict: `flexible but operationally over-complex for V1`
- Short rationale: `Option C aligns well with ambiguity-heavy research questions and preserves the idea of explicit adjudication, but it introduces the highest orchestration overhead and the greatest risk of specialist drift, duplicated work, and opaque reconciliation. It fits the spirit of deep research, yet seems harder than necessary for the concrete V1 requirements.`

### Supported findings
- The plan defines a path from query analysis and decomposition through specialist investigations, shared evidence, adjudication, and final synthesis.
- The design explicitly distinguishes regulation, standards, and implementation/web work rather than treating all sources as a single pool.
- The adjudicator is intended to preserve hierarchy and downgrade unsupported conclusions before final answer composition.
- The plan is explicitly quality-over-latency and treats multi-pass investigation as acceptable.
- The plan recognizes operational complexity and inspectability as its main V1 boundary.

### Judgment calls
- This option is the most naturally aligned with messy, mixed regulatory and technical questions, but that strength may be overstated because many V1 questions may not actually need specialist decomposition.
- The design looks more vulnerable than Option A to process overhead disguised as rigor.
- Unless the orchestrator is unusually disciplined, this option could consume a lot of effort while still failing on the same retrieval blind spots as simpler designs.

### Unresolved uncertainties
- The plan does not specify when decomposition is triggered and when the system stays simple, which matters a great deal for V1 usability and cost.
- It is unclear how adjudication remains transparent and auditable once multiple specialists contribute overlapping evidence.
- The plan does not define how specialist overlap, contradiction, or redundant search effort is controlled.

### Likely later evaluation needs
- Instrumentation of decomposition quality: when specialist fan-out helps versus hurts.
- Audits of adjudication transparency and whether final claims remain clearly attributable to evidence.
- Cost and latency studies on realistic question mixes, including narrow questions that may not justify orchestration.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Pass | The design explicitly reconciles specialist evidence in a shared ledger before final synthesis. | None at plan level. |
| R2 | Pass | Separate specialists cover law, standards, and implementation/web material under one orchestrator. | Reach is broad, but not necessarily efficient or disciplined enough in practice. |
| R3 | Pass | Source-role enforcement is centralized in the adjudicator and conflicts can remain visible in the final answer. | The actual transparency of adjudication is underspecified. |
| R4 | Partial pass | The adjudicator is meant to downgrade unsupported conclusions before answer composition. | The shared-ledger design may still allow source-role drift or weak reconciliation if specialist outputs are noisy. |
| R5 | Pass | The orchestrator can start EU-first and extend into Germany through a dedicated implementation specialist. | None material. |
| R6 | Pass | The option explicitly prioritizes decomposition and reconciliation over speed. | None material. |
| R7 | Pass | Specialists use the curated corpus first and web expansion is constrained to a dedicated role when justified by gaps. | The threshold for invoking the implementation/web specialist is not specified clearly enough. |
| R8 | Pass with risk | The option could reduce manual reconstruction on hard cross-layer questions by distributing research effort across roles. | On many questions, orchestration overhead may reduce practical usefulness. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Good for V1 if proposal, annex, and supporting materials genuinely benefit from decomposition. | Provisional grouping may depend too much on adjudication quality rather than one stable evidence structure. |
| Scenario A | Good for V1 because the scenario is naturally multi-layer and role-diverse. | The design may over-investigate even when a simpler ranked pipeline would have been enough. |
| Scenario B | Medium for V1: EU-first plus Germany extension is conceptually well supported. | Lower-rank implementation material may enter too early unless strict gating exists. |
| Scenario C | Good, but likely overpowered for a narrow protocol question. | The full orchestration stack may be unnecessary overhead on focused standards questions. |
| High-risk failure pattern | Better than the baseline because cross-checking is possible across specialists. | Poor decomposition can still miss the governing source while creating a false impression of thoroughness. |

### Reviewer-perspective notes

#### Traceability / Compliance
- The presence of an adjudicator is positive for source-role control.
- But multi-specialist contribution paths can make final support chains harder to inspect than in Option A.
- Compliance strength depends heavily on a strict shared evidence schema that the plan only sketches.

#### System / Data / Performance
- Highest operational overhead of the four options.
- Strongest risk of duplicated work, tool drift, and opaque control flow.
- Likely hardest option to keep disciplined under real use pressure.

#### Research Workflow / User Value
- Potentially very helpful on ambiguity-heavy, mixed-source questions.
- Probably less efficient on ordinary V1 questions than the plan suggests.
- User value depends strongly on the orchestrator being selective rather than decomposing by default.

## 6. Baseline review

### Summary verdict
- Overall verdict: `credible control, not acceptable as the preferred V1 target`
- Short rationale: `The baseline is a properly simple control option and is not disguised as a full architecture. It is credible enough to test whether extra architecture buys real quality, but it is the weakest fit against the non-negotiable requirement to avoid unsupported or wrongly supported core claims.`

### Supported findings
- The baseline defines an explicit retrieval-to-synthesis path and therefore remains a real answering architecture rather than retrieval-only tooling.
- It gives the curated corpus the main role and constrains web fallback to official domains.
- It explicitly acknowledges shallow conflict handling and light source-role control as limitations.
- It is appropriately simple in cost, latency, and maintenance profile compared with the serious options.
- The plan clearly explains why it is a baseline and why it is not a disguised full option.

### Judgment calls
- This is a useful control precisely because it leaves the main failure pattern comparatively exposed.
- It may perform surprisingly well on narrow direct questions, but that does not rescue it as the main V1 target because the requirements basis is shaped around avoiding under-supported synthesis on harder cross-layer questions.
- The baseline is valuable for comparison, but choosing it as the main direction would look like underreacting to the stated pain points.

### Unresolved uncertainties
- The plan does not define how retrieval weakness is detected before web fallback or answer generation.
- It is unclear how often light source-rank filtering would be enough to stop false elevation of medium-rank sources.
- The post-hoc citation packaging step is too lightly specified to judge how trustworthy anchor-level support would be.

### Likely later evaluation needs
- Side-by-side benchmarking against Option A on higher-risk cross-layer questions.
- Analysis of cases where the baseline returns plausible but under-governed answers.
- Measurement of whether narrow direct-question strengths are enough to justify any lighter-weight hybridization into a serious option.

### Requirement-by-requirement assessment

| Rubric ID | Assessment | Evidence from the plan | Concern if any |
| --- | --- | --- | --- |
| R1 | Pass | The baseline still performs synthesis from retrieved evidence and returns an answer with citations and uncertainty notes. | The synthesis is single-pass and lightly controlled. |
| R2 | Partial pass | It can retrieve across the curated corpus and use official-web fallback if needed. | There is no robust mechanism for systematic cross-layer source discovery or ranked gap-filling. |
| R3 | Partial pass | The plan says source roles can be represented and conflicts can be noted. | Handling is shallow and mostly post-hoc, so hierarchy and contradiction exposure are much weaker than in the serious options. |
| R4 | Weak / partial pass | Retrieval preferences and light source-rank filtering provide some defense. | This is the option most likely to emit plausible but wrongly supported core claims because there is no strong evidence-control layer. |
| R5 | Pass | The curated corpus can be weighted toward EU-level material and national reasoning is only possible, not foundational. | None material. |
| R6 | Partial pass | It can be used in deep-research workflows, but the design does not inherently enforce quality-first control. | The low-latency profile may tempt weaker evidence governance. |
| R7 | Pass | Curated corpus is primary and web fallback is narrow and official-only. | The trigger and governance around fallback are underspecified. |
| R8 | Partial pass | The baseline may reduce some manual reconstruction on direct questions. | It gives a weak basis for the harder cross-layer research value the requirements emphasize. |

### Scenario coverage assessment

| Scenario | Assessment | Main concern |
| --- | --- | --- |
| Primary success scenario | Weak to partial: it can retrieve proposal and annex material and produce a first answer. | Cross-document grouping and stable requirement linking are likely too shallow. |
| Scenario A | Partial: simple retrieval may find relevant layers. | Cross-layer relationship handling and ranked source escalation are weak. |
| Scenario B | Partial: EU-first is possible if retrieval succeeds. | Member-state discretion and source-role distinctions are fragile under light filtering. |
| Scenario C | Fairly good as a control on narrow technical questions. | If the right standards section is missed, there is little recovery logic. |
| High-risk failure pattern | Weak by design, which is acceptable for a control. | It is the least defended option against plausible answers that miss the governing higher-ranked source. |

### Reviewer-perspective notes

#### Traceability / Compliance
- Minimal acceptable traceability, but not strong enough for the stated non-negotiable quality bar.
- Light source-rank filtering is too weak a defense against false elevation.
- Good as a comparison point, not as the preferred answer to the worst-failure requirement.

#### System / Data / Performance
- Best simplicity profile.
- Lowest maintenance burden.
- Also the lowest governance strength, which is exactly what the requirements basis says should not be traded away.

#### Research Workflow / User Value
- Could still be helpful for narrow, direct questions.
- Unconvincing as the main answer to the broader workflow pain point of reconstructing multi-layer source landscapes.
- Most likely to save time in the short run while causing re-checking burden later.

## 7. Optional cross-option notes

- Option A appears to be the best V1-balanced answer to the actual requirements basis.
- Option B is the most interesting structurally for relationship-heavy research, but it takes on notable V1 ingest and false-completeness risk.
- Option C is flexible and future-extensible, but it seems to spend too much complexity budget for a V1 whose key problem can likely be addressed with a stricter evidence-first pipeline.
- The baseline is credible and useful as a control, but it should mainly function as a comparison floor that helps test whether the stronger evidence-control designs materially reduce under-supported answers.
