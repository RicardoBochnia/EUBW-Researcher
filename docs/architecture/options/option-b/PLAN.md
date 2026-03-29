# Option B Plan

Status: frozen for external review
Option type: serious path
Slug: option-b

## 1. Summary

- Option thesis: Provenance Graph Planner.
- One-sentence problem-solving approach: Normalize the corpus into a source/provision/provenance graph and use graph-guided query planning before final answer synthesis.
- Why this option is materially different: It centers retrieval and reasoning on a persistent graph of source relationships rather than on a transient ledger or specialist worker decomposition.

## 2. Primary architecture levers

- Lever 1: persistent provenance graph as the primary knowledge organization layer
- Lever 2: planner-led graph traversal before text evidence packaging
- Optional additional lever: explicit jurisdiction and source-role typing in the graph model

## 3. Main components and responsibilities

| Component | Responsibility |
| --- | --- |
| Source Ingestion Normalizer | Convert regulation, standards, and official project material into typed source and provision records. |
| Provenance Graph Store | Hold sources, provisions, references, jurisdiction markers, and provenance links as first-class graph objects. |
| Query Planner | Translate a user question into graph traversal intents, likely evidence targets, and fallback expansion steps. |
| Text Retrieval Adapter | Fetch the concrete passages behind graph nodes and edges for answer-ready evidence. |
| Evidence Pack Builder | Assemble graph-derived evidence into a synthesis-ready package with traceable provenance. |
| Final Answer Composer | Build the answer from the evidence pack while preserving ranking, hierarchy, and uncertainty. |

## 4. End-to-end answer flow

1. Parse the user question into entities, jurisdictions, concepts, and target claim types that can drive graph traversal.
2. Use the query planner to traverse the provenance graph across regulation, acts, referenced standards, and official project material in ranked order.
3. Fetch the underlying text passages for the relevant nodes and edges, then package them into a source-aware evidence set.
4. Synthesize the answer from the evidence set, preserving graph-supported relationships, conflicts, and open gaps.

## 5. Source handling

### Curated / offline corpus
- The curated corpus is ingested into the graph first and remains the preferred research substrate.
- Persistent normalization is intended to make cross-layer links queryable rather than rediscovered from scratch on every prompt.

### Web expansion
- Web expansion is used to attach missing official material as new, typed graph inputs or temporary evidence nodes.
- Web findings should remain explicitly typed by source role and jurisdiction before they influence synthesis.

### Source ranking and source roles
- Source role is encoded directly in node and edge types, not only inferred at synthesis time.
- Ranking logic is therefore available both during retrieval and during comparison of conflicting evidence paths.

### Conflict and uncertainty handling
- Conflicts appear as competing paths or conflicting node claims in the graph-backed evidence package.
- Missing edges or weakly grounded nodes are a first-class uncertainty source and should be made visible in the answer.

## 6. Data and corpus assumptions

- Assumption 1: The highest-value sources can be segmented into provisions and linked via references with acceptable reliability.
- Assumption 2: The effort to maintain graph typing and provenance links is manageable for a V1-grade corpus.
- Main risk if assumptions fail: The graph gives a false sense of completeness while actually hiding missing or weakly extracted relations.

## 7. Scenario coverage

| Scenario | How this option handles it | Main weak point | V1 judgment |
| --- | --- | --- | --- |
| Primary success scenario | Excellent fit if proposal and annex relations are normalized, because clustering and cross-reference tracing become first-class operations. | The up-front graph model may overfit one document family and make provisional grouping look more certain than it is. | Medium to strong for V1, depending on ingest maturity. |
| Scenario A | Excellent for tracing regulation -> implementing acts -> standards chains when the citation structure is explicit. | National or project documents with weak internal linking may still enter the graph only as coarse nodes. | Medium for V1. |
| Scenario B | Good fit if jurisdiction and obligation scope are encoded in the graph model. | Best-effort Germany handling may be thin unless national materials are normalized beyond document level. | Medium for V1. |
| Scenario C | Good fit when standards sections and role relationships are captured as graph nodes and references. | Detailed protocol reasoning still depends on the text interpretation layer, not the graph alone. | Good for V1 if standards ingest is strong. |
| High-risk failure pattern | Very good if the graph is complete enough, because missing higher-ranked sources can be spotted as absent required link types. | Hidden graph incompleteness is itself a serious failure mode and may be hard to detect without separate quality checks. | Medium for V1. |

## 8. V1 fit and constraints

- EU-first fit: Strong, because EU-level sources can anchor the graph model.
- Germany / national best-effort handling: Feasible, but likely coarser unless national materials are more heavily normalized.
- Quality-over-latency fit: Strong, because the design explicitly spends effort on structured provenance before answering.
- Main V1 boundary: The graph-ingest and maintenance burden may be high relative to the initial document set and time horizon.

## 9. Cost, latency, and maintenance view

- Expected latency posture: Medium; graph traversal can help targeted retrieval, but ingest and evidence packaging are non-trivial.
- Expected operational cost posture: Medium to high, depending on how much normalization and graph maintenance is performed before queries.
- Expected maintenance burden: High; schema evolution, graph integrity, and ingestion quality will require ongoing attention.

## 10. Strengths and failure modes

### Expected strengths
- Strongest option for explicit cross-layer relationship modeling and link-driven discovery.
- Naturally aligned with provisional grouping and requirement-cluster exploration in the primary success scenario.

### Likely failure modes
- Graph incompleteness hides missing governing sources or overstates the quality of the evidence network.
- Up-front modeling effort delays value or narrows the range of documents that can be handled well in early V1.

## 11. Open assumptions and dependencies

- References and provision boundaries can be extracted with enough consistency to justify graph normalization.
- The project can afford higher ingestion and maintenance effort in exchange for better relationship-aware retrieval.

## 12. Freeze checklist

- Same structure as the other option plans: `yes`
- Same scenario coverage as the other option plans: `yes`
- Comparable argumentative depth: `yes`
- Explicit data assumptions: `yes`
- Explicit treatment of source roles and uncertainty: `yes`
