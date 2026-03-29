# Options Comparison

Status: populated from completed external review wave
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
| C1 | Strongest V1 fit | Strong but maturity-dependent | Good on hard mixed questions, but over-complex | Weak-to-moderate |
| C2 | Strong | Strongest structural upside | Strong but costly | Partial |
| C3 | Strongest explicit control | Strong in principle, weaker under hidden incompleteness | Good in principle, weaker under adjudication opacity | Weak |
| C4 | Strongest | Partial | Medium to medium-high | Weak / does not meet |
| C5 | Strong | Medium | Medium | Control-only |
| C6 | Medium burden | High burden | Highest burden | Lowest burden |
| C7 | Medium dependence risk | Highest dependence risk | Medium-high dependence risk | Medium dependence risk |
| C8 | Medium | High | High | Low to medium |

## 4. Supported findings

Only include claims supported by the option plans, reviews, requirements basis, or decided patches.

- All four external reviewers converged on the same top-level ranking pattern: Option A is the strongest serious V1 fit, Option B is promising but high-risk for V1, Option C is flexible but operationally over-complex, and the baseline is credible only as a control option.
- Option A is consistently the strongest direct fit for the non-negotiable requirement to avoid unsupported or wrongly supported core claims.
- Option B is consistently the most attractive option for relationship-heavy discovery and provisional grouping if graph completeness and ingest quality are materially stronger than the current plans can prove.
- Option C is consistently viewed as strongest on ambiguity-heavy mixed-source questions, but also as the most operationally expensive and hardest to keep inspectable.
- The baseline is consistently seen as a useful comparison floor rather than a target V1 architecture.

## 5. Judgment calls

Use this section for architecture judgment that is not strictly proven by the documents.

- The main decision tension is between Option A's simpler, explicit evidence-control path and Option B's stronger relationship modeling upside.
- Option C may still be attractive if the expected workload turns out to be much more ambiguity-heavy and multi-domain than the current scenario mix suggests.
- The baseline remains valuable in the process because it defines the minimum credible floor the serious options must clearly outperform.

## 6. Unresolved uncertainties

Use this section for issues that remain open after review.

- No blocker-level requirements contradiction emerged from the architecture round.
- The one recurring meta-question is whether internal-process inspectability should be made more explicit in the requirements basis. This was treated as a non-blocking note, not a formal patch, because the current basis already requires visible hierarchy, contradiction, uncertainty, and source-role preservation in the answer behavior.
- Option A remains sensitive to retrieval misses and weak anchors.
- Option B remains sensitive to false completeness from graph incompleteness.
- Option C remains sensitive to specialist drift, over-decomposition, and opaque adjudication.

## 7. Likely later evaluation needs

For each option, record the assumptions that remain untested, why they matter, and what could change a later decision.

### Option A
- Untested assumption: article- and section-level anchors plus source-rank metadata are extractable reliably enough for a query-time evidence ledger.
- Why it matters: if the corpus cannot support stable ledger construction, Option A loses much of its traceability advantage while retaining its step cost.
- What could change later: stronger-than-expected metadata quality would strengthen Option A; weak anchors or repeated retrieval misses could push the decision toward a graph-backed or narrower fallback design.

### Option B
- Untested assumption: provision-level normalization and citation extraction are strong enough to justify a maintained provenance graph in V1.
- Why it matters: if graph completeness is weak, Option B may look rigorous while hiding major evidence gaps and maintenance burden.
- What could change later: a successful ingest spike would materially strengthen Option B; weak normalization or hidden graph incompleteness would likely make it too heavy and too risky for V1.

### Option C
- Untested assumption: the orchestrator can keep specialist work bounded and the shared evidence ledger can prevent source-role drift.
- Why it matters: if decomposition or adjudication is weak, Option C pays high complexity and cost without commensurate trust gains.
- What could change later: convincing bounded specialist behavior and transparent adjudication would strengthen Option C; drift, duplicated effort, or opaque conflict resolution would push the decision toward a simpler control model.

### Baseline
- Untested assumption: the curated corpus is already rich enough that simple hybrid retrieval can still surface the governing sources for many questions.
- Why it matters: if this assumption fails immediately, the baseline stops being a credible control and becomes too weak to compare fairly.
- What could change later: stronger-than-expected baseline performance would raise the bar for adopting heavier architectures; weak performance would reinforce the need for explicit evidence-control machinery and make the baseline useful only as a floor.

## 8. Decision basis

This section should summarize:
- which options remain strongest and why
- which tradeoffs remain real judgment calls
- what should be validated next before a target architecture is chosen

- Current leading option: Option A.
- Why it leads now: it best satisfies the non-negotiable support-fidelity requirement while staying operationally plausible for V1, and it does so with the clearest inspectable control flow.
- Closest alternative: Option B, but only if a focused ingest and graph-quality spike demonstrates that graph completeness and maintenance burden are materially better than the current plans can prove.
- Option C remains viable as a future-extensibility or ambiguity-heavy path, but does not currently beat Option A on the V1 balance of trust, control burden, and likely user value.
- The baseline should remain in play as a comparison floor, not as the preferred target architecture.
- Suggested next validation step before a final architecture choice: run a small evaluation/prototype spike that pressure-tests Option A versus Option B on the primary success scenario, Scenario A, and the high-risk failure pattern.
