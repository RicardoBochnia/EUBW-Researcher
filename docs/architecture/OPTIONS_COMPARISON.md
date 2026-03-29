# Options Comparison

Status: prepared, awaiting completed external reviews
Purpose: consolidate option reviews into an architecture decision basis

## 1. Inputs

Required inputs:
- all frozen option `PLAN.md` files
- all completed option `REVIEW.md` files
- [EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md](../requirements/EUBW_RESEARCH_ASSISTANT_REQUIREMENTS_BASIS.md)
- [MASTERPLAN.md](./MASTERPLAN.md)
- decided entries in [REQUIREMENTS_PATCHES.md](./REQUIREMENTS_PATCHES.md)

Option mapping for this comparison round:
- Option A = Evidence-First Layered Pipeline
- Option B = Provenance Graph Planner
- Option C = Specialist Research Orchestrator
- Baseline = Constrained Hybrid RAG Baseline

## 2. Comparison criteria mapped to the requirements basis

Only use criteria that map back to the requirements basis.

| Criterion ID | Criterion | Requirements basis anchor |
| --- | --- | --- |
| C1 | Source-bound answer synthesis quality | Must-have 1; primary optimization target |
| C2 | Cross-layer source finding capability | Must-have 2; representative scenarios |
| C3 | Handling of hierarchy, contradiction, uncertainty, and source role | Must-have 3; source-role rules |
| C4 | Protection against unsupported or wrongly supported core claims | Non-negotiable property; high-risk failure pattern |
| C5 | V1 scope fit | Scope boundaries for V1 |
| C6 | Operational burden | Quality-over-latency stance; cost / maintenance implications in plans |
| C7 | Data and corpus dependence risk | Data / corpus assumptions logged in the plans |
| C8 | Likely later evaluation burden | Accepted V1 risks and later validation needs |

## 3. Comparison matrix

| Criterion | Option A | Option B | Option C | Baseline |
| --- | --- | --- | --- | --- |
| C1 | `Pending external review` | `Pending external review` | `Pending external review` | `Pending external review` |
| C2 | `Pending external review` | `Pending external review` | `Pending external review` | `Pending external review` |
| C3 | `Pending external review` | `Pending external review` | `Pending external review` | `Pending external review` |
| C4 | `Pending external review` | `Pending external review` | `Pending external review` | `Pending external review` |
| C5 | `Pending external review` | `Pending external review` | `Pending external review` | `Pending external review` |
| C6 | `Pending external review` | `Pending external review` | `Pending external review` | `Pending external review` |
| C7 | `Pending external review` | `Pending external review` | `Pending external review` | `Pending external review` |
| C8 | `Pending external review` | `Pending external review` | `Pending external review` | `Pending external review` |

## 4. Supported findings

Only include claims supported by the option plans, reviews, requirements basis, or decided patches.

- Pending external reviews.

## 5. Judgment calls

Use this section for architecture judgment that is not strictly proven by the documents.

- Pending external reviews.

## 6. Unresolved uncertainties

Use this section for issues that remain open after review.

- Pending external reviews.

## 7. Likely later evaluation needs

For each option, record the assumptions that remain untested, why they matter, and what could change a later decision.

### Option A
- Untested assumption: article- and section-level anchors plus source-rank metadata are extractable reliably enough for a query-time evidence ledger.
- Why it matters: if the corpus cannot support stable ledger construction, Option A loses much of its traceability advantage while retaining its step cost.
- What could change later: stronger-than-expected metadata quality would strengthen Option A; weak anchors could push the decision toward a graph-backed or simpler fallback design.

### Option B
- Untested assumption: provision-level normalization and citation extraction are strong enough to justify a maintained provenance graph in V1.
- Why it matters: if graph completeness is weak, Option B may look rigorous while hiding major evidence gaps and maintenance burden.
- What could change later: a successful ingest spike would materially strengthen Option B; weak normalization would likely make it too heavy for V1.

### Option C
- Untested assumption: the orchestrator can keep specialist work bounded and the shared evidence ledger can prevent source-role drift.
- Why it matters: if decomposition or adjudication is weak, Option C pays high complexity and cost without commensurate trust gains.
- What could change later: convincing bounded specialist behavior would strengthen Option C; drift or duplicated effort would push the decision toward a simpler control model.

### Baseline
- Untested assumption: the curated corpus is already rich enough that simple hybrid retrieval can still surface the governing sources for many questions.
- Why it matters: if this assumption fails immediately, the baseline stops being a credible control and becomes too weak to compare fairly.
- What could change later: stronger-than-expected baseline performance would raise the bar for adopting heavier architectures; weak performance would justify more explicit evidence-control machinery.

## 8. Decision basis

This section should summarize:
- which options remain strongest and why
- which tradeoffs remain real judgment calls
- what should be validated next before a target architecture is chosen

- Pending external reviews. Do not populate this section until all four `REVIEW.md` files are complete.
