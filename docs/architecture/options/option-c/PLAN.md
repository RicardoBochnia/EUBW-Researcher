# Option C Plan

Status: frozen for external review
Option type: serious path
Slug: option-c

## 1. Summary

- Option thesis: Specialist Research Orchestrator.
- One-sentence problem-solving approach: Use a coordinator that decomposes the query into specialist investigations and reconciles their evidence in a shared ledger before final synthesis.
- Why this option is materially different: It relies on role-specialized investigation and adjudication rather than a fixed pipeline or a graph-first corpus model.

## 2. Primary architecture levers

- Lever 1: multi-worker orchestration with explicit specialist roles
- Lever 2: shared evidence ledger plus adjudication step before final answering
- Optional additional lever: role-specific source access policies for regulation, standards, and implementation/web material

## 3. Main components and responsibilities

| Component | Responsibility |
| --- | --- |
| Query Orchestrator | Decide whether to clarify, decompose the question, and assign bounded sub-questions to specialists. |
| Regulatory Specialist | Investigate law, implementing acts, and related regulatory material. |
| Standards Specialist | Investigate referenced technical standards and protocol behavior. |
| Implementation / Web Specialist | Investigate official project, pilot, and national implementation material under constrained source-role rules. |
| Shared Evidence Ledger | Hold specialist findings in one claim/evidence structure with source roles and uncertainty markers. |
| Claim Adjudicator | Resolve conflicts, preserve hierarchy, and downgrade unsupported conclusions before answer composition. |
| Final Answer Composer | Produce the final source-bound synthesis. |

## 4. End-to-end answer flow

1. Analyze the user question and split it into bounded investigation tasks only when decomposition improves answer quality.
2. Dispatch the relevant specialists with shared evidence and source-role rules.
3. Merge specialist outputs into the shared ledger and use the adjudicator to rank, reconcile, and qualify claims.
4. Compose the final answer from the adjudicated ledger, including conflicts, hierarchy, and explicit uncertainty where needed.

## 5. Source handling

### Curated / offline corpus
- Specialists use the curated corpus as the first search space within their source-role boundaries.
- The orchestrator should prefer high-rank evidence sources before invoking lower-rank or web-heavy workstreams.

### Web expansion
- Web expansion is primarily the responsibility of the implementation/web specialist and should remain domain-constrained.
- Web use is not generic browsing; it is a controlled extension path when the curated corpus and higher-rank sources leave a documented gap.

### Source ranking and source roles
- Source-role enforcement happens centrally in the adjudicator, not only inside each specialist.
- Specialists may surface medium- or low-rank material, but the adjudicator controls what can support a core claim.

### Conflict and uncertainty handling
- Conflict handling is one of the main reasons to use this design: specialists may disagree, and the adjudicator makes that visible instead of smoothing it away.
- Open uncertainty can remain in the final answer if the higher-ranked layers do not fully settle the question.

## 6. Data and corpus assumptions

- Assumption 1: Specialist tasks can be bounded clearly enough that they do not overlap excessively or drift into speculative work.
- Assumption 2: The shared evidence ledger is strong enough to prevent source-role drift and unsupported synthesis across specialists.
- Main risk if assumptions fail: The system becomes expensive, redundant, and hard to audit because decomposition and reconciliation create more ambiguity than clarity.

## 7. Scenario coverage

| Scenario | How this option handles it | Main weak point | V1 judgment |
| --- | --- | --- | --- |
| Primary success scenario | Good fit: separate specialists can extract proposal, annex, and supporting material, then feed a provisional grouped answer. | Grouping consistency depends on the adjudication and synthesis layer rather than one stable structural model. | Medium to strong for V1. |
| Scenario A | Very good fit: the question naturally spans regulation, implementing acts, standards, and implementation sources. | The design may over-investigate and pay a high cost even when a simpler pipeline would suffice. | Good for V1 if cost tolerance is real. |
| Scenario B | Good fit: the regulatory specialist can anchor EU-first reasoning, while the implementation specialist extends into Germany on a best-effort basis. | Lower-rank web material may enter too early unless the adjudicator is strict. | Medium for V1. |
| Scenario C | Good fit: the standards specialist can focus tightly on protocol behavior and section-level justification. | The full orchestrator may be overkill for narrow technical questions. | Good for V1. |
| High-risk failure pattern | Good fit in principle because multiple specialists can cross-check each other before synthesis. | If the orchestrator decomposes the problem poorly, the system may still miss the governing source while appearing thorough. | Medium for V1. |

## 8. V1 fit and constraints

- EU-first fit: Strong if the orchestrator always starts with regulatory and standards specialists before lower-rank expansion.
- Germany / national best-effort handling: Better than most options because a dedicated implementation specialist can extend the search when needed.
- Quality-over-latency fit: Very strong; this option explicitly spends time on decomposition and reconciliation.
- Main V1 boundary: It is the most operationally complex option and therefore the hardest to keep disciplined and inspectable.

## 9. Cost, latency, and maintenance view

- Expected latency posture: High; multiple specialist passes and adjudication increase turnaround time.
- Expected operational cost posture: High; multi-step orchestration and reconciliation add substantial token and control overhead.
- Expected maintenance burden: High; prompt discipline, tool discipline, and evidence-schema discipline all need active upkeep.

## 10. Strengths and failure modes

### Expected strengths
- Most flexible option for ambiguity-heavy, mixed regulatory/technical research questions.
- Strong future extensibility if additional source domains or specialist roles become important later.

### Likely failure modes
- Specialist drift or duplicated work increases cost without improving answer quality.
- The final adjudication may become opaque if the shared evidence schema is not strict enough.

## 11. Open assumptions and dependencies

- The orchestrator can keep sub-questions bounded and avoid unnecessary decomposition on simple prompts.
- Source-role rules can be enforced strongly enough in the shared ledger and adjudication layer to offset the complexity of multiple workers.

## 12. Freeze checklist

- Same structure as the other option plans: `yes`
- Same scenario coverage as the other option plans: `yes`
- Comparable argumentative depth: `yes`
- Explicit data assumptions: `yes`
- Explicit treatment of source roles and uncertainty: `yes`
