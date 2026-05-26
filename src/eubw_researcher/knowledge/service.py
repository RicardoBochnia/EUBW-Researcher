from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from eubw_researcher.models import (
    CandidateClaimRecord,
    ConceptRecord,
    EvidenceCluster,
    EvidenceClusterRecord,
    IngestionBundle,
    NavigationSessionTrace,
    NavigationTraceStep,
    OpenIssueRecord,
    RelationGraphEdge,
    SourceChunk,
    SourceHierarchyReport,
    TerminologyConfig,
)
from eubw_researcher.knowledge.query_expansion import (
    QueryExpansion,
    contains_term,
    expand_query,
    searchable_text,
)
from eubw_researcher.knowledge.source_retrieval import (
    SOURCE_RESCUE_THRESHOLD,
    SourceRetrievalCandidate,
    retrieve_source_candidates,
)
from eubw_researcher.knowledge.question_facets import (
    detect_question_facets,
    facet_tags_for_text,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "bei",
    "das",
    "der",
    "die",
    "ein",
    "eine",
    "for",
    "im",
    "in",
    "ist",
    "mit",
    "of",
    "oder",
    "the",
    "to",
    "und",
    "was",
    "wenn",
    "wie",
    "with",
    "zu",
}

TERM_ALIASES = {
    "aendern": ["update", "status", "revocation", "suspension"],
    "aendert": ["update", "status", "revocation", "suspension"],
    "anbieter": ["provider"],
    "architektur": ["architecture"],
    "access": ["access"],
    "auditspur": ["audit", "trace", "log", "transaction"],
    "auditierbarkeit": ["audit", "traceability"],
    "aufbewahren": ["retain", "retention", "record", "records", "10 years"],
    "aufbewahrung": ["retain", "retention", "record", "records", "10 years"],
    "aussteller": ["issuer", "issue", "attestation provider", "credential issuer"],
    "ausstellers": ["issuer", "issue", "attestation provider", "credential issuer"],
    "ausgesetzt": ["suspend", "suspended", "suspension", "cancellation"],
    "ausstellung": ["issuance", "issued", "initial issuance"],
    "ausgestellt": ["issued", "initial issuance"],
    "authentifiziert": ["authenticated", "authentication"],
    "authentisiert": ["authenticated", "authentication"],
    "autorisiert": ["authorise", "authorised", "authorize", "authorized", "authorisation", "authorization"],
    "befugnis": ["authority", "authorisation", "authorization", "mandate", "powers"],
    "behoerden": ["authorities", "public sector bodies", "public authorities"],
    "behoerde": ["authority"],
    "benutzerkonto": ["user account", "resource owner", "end-user", "client"],
    "batch": ["batch", "credential dataset", "credential set"],
    "batches": ["batch", "credential dataset", "credential set"],
    "beschreiben": ["describe", "description", "certificate policy", "practice statement"],
    "betroffenen": ["affected"],
    "ca": ["ca", "certificate authority", "access ca", "access certificate authority"],
    "certificate": ["certificate", "certificate policy", "practice statement"],
    "client": ["client", "resource owner", "authorization server", "token endpoint"],
    "delegationskette": [
        "delegation",
        "chain",
        "mandate",
        "powers",
        "represent",
        "scope",
        "validity",
        "status",
        "revocation",
        "auditability",
    ],
    "dauerhaft": ["retention"],
    "englisch": ["english", "language", "description", "name"],
    "endnutzer": ["end-user", "resource owner"],
    "endnutzers": ["end-user", "resource owner"],
    "ereignisspuren": ["event", "audit", "log", "transaction"],
    "ereignisse": ["event", "audit", "log"],
    "feldbeschreibung": ["field", "description", "attribute", "schema"],
    "feldbeschreibungen": ["field", "description", "attribute", "schema"],
    "finale": ["final"],
    "format": ["format", "schema"],
    "geloescht": ["cancel", "cancelled", "cancellation", "delete", "deleted"],
    "geltendes": ["binding", "final", "law"],
    "grenzueberschreitend": ["cross-border", "cross border", "eu", "european"],
    "grenzueberschreitende": ["cross-border", "cross border", "eu", "european"],
    "handlungsbefugnis": ["authority", "representation", "mandate", "powers"],
    "identitaetsabgleich": ["identity matching", "unequivocal matching", "identity", "matching"],
    "identitaetsmatching": ["identity matching", "unequivocal matching", "identity", "matching"],
    "immabescheinigung": ["enrolment", "student", "attestation", "credential"],
    "immabescheinigungen": ["enrolment", "student", "attestation", "credential"],
    "inhalte": ["content", "payload"],
    "juristische": ["legal"],
    "log": ["log", "audit"],
    "logging": ["log", "audit"],
    "lote": ["lote", "list of trusted entities", "trusted list", "trusted list provider"],
    "mandat": ["mandate", "delegation", "authorisation", "authorization", "powers", "represent", "status", "revocation", "validity", "constraints"],
    "mandate": ["mandate", "delegation", "authorisation", "authorization", "powers", "represent", "status", "revocation", "validity", "constraints"],
    "mandaten": ["mandate", "delegation", "authorisation", "authorization", "powers", "represent", "status", "revocation", "validity", "constraints"],
    "mandats": ["mandate", "delegation", "authorisation", "authorization", "powers", "represent", "status", "revocation", "validity", "constraints"],
    "mindest": ["minimum", "at least", "level of assurance"],
    "nachweis": ["credential", "attestation", "evidence"],
    "nachweise": ["credential", "attestation", "evidence"],
    "nachvollziehbarkeit": ["traceability", "audit"],
    "natuerliche": ["natural"],
    "oeffentliche": ["public sector", "public sector bodies", "public authorities"],
    "person": ["person"],
    "portabilitaet": [
        "portability",
        "migration",
        "export",
        "transfer",
        "migration object",
        "re-issuance",
        "rebinding",
        "device-bound",
    ],
    "protokollieren": ["log", "audit"],
    "pruefbarkeit": ["audit", "verification", "traceability"],
    "providers": ["provider"],
    "pubeaa": [
        "pubeaa",
        "public sector electronic attestation of attributes",
        "public sector body responsible for an authentic source",
        "electronic attestation of attributes issued by or on behalf of a public sector body",
        "Article 45f",
        "revocation",
        "validity",
    ],
    "pubeaas": [
        "pubeaa",
        "public sector electronic attestation of attributes",
        "public sector body responsible for an authentic source",
        "electronic attestation of attributes issued by or on behalf of a public sector body",
        "Article 45f",
        "revocation",
        "validity",
    ],
    "pruefer": ["verifier", "relying", "party"],
    "register": ["register", "registration", "authentic", "source"],
    "registerbetreiber": ["registrar", "register", "registration"],
    "registerdaten": ["register", "registration", "authentic", "source"],
    "recht": ["law", "regulation"],
    "regelwerk": ["rulebook", "catalogue", "attribute", "description"],
    "richtigen": ["selection", "scope", "intended use", "purpose"],
    "rollen": ["roles", "client", "resource owner", "authorization server"],
    "rp": ["relying", "party", "wallet-relying-party"],
    "rulebook": ["rulebook", "catalogue", "attribute", "description"],
    "rulebooks": ["rulebook", "catalogue", "attribute", "description"],
    "spezifikation": ["specification"],
    "spezifikationen": ["specification"],
    "stellen": ["bodies", "public sector bodies", "public authorities"],
    "streitfaelle": ["dispute", "investigation", "audit"],
    "studierendenausweis": ["student", "attestation", "credential", "status"],
    "technische": ["technical", "specification"],
    "unternehmensstatus": ["status", "revocation", "suspension", "cancellation"],
    "uebergangszeit": ["transition", "transitional", "communication solutions", "alternative communication"],
    "vollprotokollierung": ["full", "logging", "retention"],
    "vertrauenskette": [
        "trust",
        "attestation",
        "trust-list",
        "wallet unit attestation",
        "wua",
        "device-bound",
    ],
    "vertretung": ["representation", "mandate", "authority", "powers", "represent"],
    "vertretungsrechte": ["representation", "mandate", "authority", "powers", "represent"],
    "vertrauensniveau": ["level of assurance", "assurance", "substantial level of assurance", "authentication"],
    "vorrang": ["priority", "authentic", "source"],
    "vorschlag": ["proposal"],
    "wechsel": [
        "migration",
        "transfer",
        "export",
        "portability",
        "migration object",
        "re-issuance",
        "rebinding",
    ],
    "widerruf": ["revocation", "revoked"],
    "widerrufen": ["revocation", "revoked", "lose validity", "validity"],
    "widerrufsstatus": ["revocation status", "status", "validity"],
    "wodurch": ["how", "means", "mechanism"],
    "wrp": ["wallet-relying party", "registration", "access certificate", "registration certificate"],
    "zertifikate": ["certificates", "access certificates", "registration certificates"],
}


@dataclass(frozen=True)
class _ChunkMatch:
    chunk: SourceChunk
    score: float
    matched_terms: tuple[str, ...]
    matched_phrases: tuple[str, ...] = ()
    channel_scores: dict[str, float] | None = None


def _terms(value: str) -> list[str]:
    return list(expand_query(value).all_terms)


def _snippet(text: str, terms: Iterable[str], *, max_length: int = 2800) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_length:
        return compact
    lowered = normalize_text_for_matching(compact)
    term_list = list(terms)
    priority_markers = {
        "cancel",
        "cancellation",
        "remove",
        "removal",
        "revoke",
        "revocation",
        "scope",
        "visible",
        "withdraw",
        "withdrawal",
    }
    prioritized_terms = [
        term for term in term_list if term in priority_markers
    ] + [
        term for term in term_list if term not in priority_markers and " " in term
    ] + [
        term for term in term_list if term not in priority_markers and " " not in term
    ]
    first_hit = next(
        (lowered.find(term) for term in prioritized_terms if lowered.find(term) >= 0),
        0,
    )
    start = max(0, first_hit - max_length // 3)
    sentence_start = compact.rfind(". ", start, first_hit)
    if sentence_start >= 0:
        start = sentence_start + 2
    end = min(len(compact), start + max_length)
    return compact[start:end].strip()


class KnowledgeService:
    """Evidence-only navigation helper behind the runtime facade."""

    def __init__(
        self,
        ingestion_bundle: IngestionBundle,
        *,
        candidate_claims: Iterable[CandidateClaimRecord] | None = None,
        relation_edges: Iterable[RelationGraphEdge] | None = None,
        open_issues: Iterable[OpenIssueRecord] | None = None,
        concepts: Iterable[ConceptRecord] | None = None,
        terminology: TerminologyConfig | None = None,
    ) -> None:
        self.ingestion_bundle = ingestion_bundle
        self._chunks_by_id = {
            chunk.chunk_id: chunk
            for document in ingestion_bundle.documents
            for chunk in document.chunks
        }
        self._sources_by_id = ingestion_bundle.catalog.by_id()
        self._claims_by_id = {
            claim.claim_id: claim for claim in (candidate_claims or [])
        }
        self._relations_by_id = {
            edge.edge_id: edge for edge in (relation_edges or [])
        }
        self._open_issues_by_id = {
            issue.issue_id: issue for issue in (open_issues or [])
        }
        self._concepts_by_id = {
            concept.concept_id: concept for concept in (concepts or [])
        }
        self._terminology = terminology
        self._last_clusters_by_id: dict[str, EvidenceCluster] = {}
        self._last_retrieval_diagnostics: dict[str, object] | None = None
        self._last_question_facets: list[str] = []

    def search_claims(
        self,
        question_or_terms: str,
        filters: dict | None = None,
    ) -> list[CandidateClaimRecord]:
        terms = set(_terms(question_or_terms))
        if not terms:
            return []
        source_filter = set((filters or {}).get("source_ids", []))
        status_filter = set((filters or {}).get("statuses", []))
        scored: list[tuple[float, CandidateClaimRecord]] = []
        for claim in self._claims_by_id.values():
            if source_filter and not source_filter.intersection(claim.source_ids):
                continue
            if status_filter and claim.status.value not in status_filter:
                continue
            haystack = " ".join(
                value
                for value in (
                    claim.normalized_statement,
                    claim.topic or "",
                    claim.actor or "",
                    claim.action or "",
                    claim.object or "",
                    claim.modality or "",
                )
                if value
            )
            normalized_haystack = normalize_text_for_matching(haystack)
            matched = {term for term in terms if term in normalized_haystack}
            if not matched:
                continue
            score = len(matched) / len(terms)
            if claim.chunk_ids:
                score += 0.1
            if claim.source_ids:
                score += 0.1
            scored.append((score, claim))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [claim for _, claim in scored[:20]]

    def search_chunks(self, question_or_terms: str, filters: dict | None = None) -> list[EvidenceClusterRecord]:
        matches = self._rank_chunks(question_or_terms, filters=filters)
        return [self._record_for_match(match) for match in matches]

    def build_evidence_clusters(
        self,
        question: str,
        filters: dict | None = None,
    ) -> tuple[list[EvidenceCluster], NavigationSessionTrace, SourceHierarchyReport]:
        matches = self._rank_chunks(question, filters=filters)
        diagnostics = self._last_retrieval_diagnostics or {}
        strong_source_ids = {
            str(candidate.get("source_id"))
            for candidate in diagnostics.get("top_source_candidates", [])
            if float(candidate.get("score", 0.0)) >= SOURCE_RESCUE_THRESHOLD
        }
        grouped: dict[str, list[_ChunkMatch]] = defaultdict(list)
        for match in matches:
            source = self._sources_by_id.get(match.chunk.source_id)
            if match.chunk.source_id in strong_source_ids:
                family = match.chunk.source_id
            elif source and source.source_family_id:
                family = source.source_family_id
            elif match.chunk.source_kind.value in {"technical_standard", "project_artifact"}:
                family = match.chunk.source_id
            else:
                family = match.chunk.source_kind.value
            grouped[family].append(match)

        clusters: list[EvidenceCluster] = []
        for index, (label, label_matches) in enumerate(grouped.items(), start=1):
            records = [
                self._record_for_match(match)
                for match in self._diverse_cluster_matches(label_matches, max_records=5)
            ]
            candidate_signal_present = any(
                (match.channel_scores or {}).get("source_catalog", 0.0) >= SOURCE_RESCUE_THRESHOLD
                for match in label_matches
            )
            claim_ids = sorted(
                {
                    claim.claim_id
                    for claim in self._claims_by_id.values()
                    if set(claim.source_ids).intersection({record.source_id for record in records})
                }
            )
            open_issue_ids = sorted(
                {
                    issue.issue_id
                    for issue in self._open_issues_by_id.values()
                    if set(issue.affected_source_ids).intersection({record.source_id for record in records})
                }
            )
            sufficiency_signals = [
                "decisive_source_candidate_present"
                if records
                else "no_decisive_source_candidate"
            ]
            if candidate_signal_present:
                sufficiency_signals.append("source_catalog_candidate_present")
            clusters.append(
                EvidenceCluster(
                    cluster_id=f"cluster_{index}_{re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_') or 'evidence'}",
                    label=label,
                    matched_concepts=sorted(
                        {
                            term
                            for match in label_matches
                            for term in [*match.matched_terms, *match.matched_phrases]
                        }
                    ),
                    candidate_claim_ids=claim_ids,
                    supporting_chunk_ids=[record.chunk_id for record in records],
                    source_ids=sorted({record.source_id for record in records}),
                    open_issue_ids=open_issue_ids,
                    records=records,
                    confidence="candidate" if records else "insufficient",
                    sufficiency_signals=sufficiency_signals,
                    missing_evidence_signals=[] if records else ["no_matching_chunks"],
                )
            )
        clusters.sort(
            key=lambda cluster: max((record.score for record in cluster.records), default=0.0),
            reverse=True,
        )

        trace = NavigationSessionTrace(
            question=question,
            steps=[
                NavigationTraceStep(
                    operation="expand_query",
                    query=question,
                    result_ids=list(diagnostics.get("expanded_terms", []))[:40],
                    notes=[
                        f"expansions={len(diagnostics.get('expansion_traces', []))}",
                    ],
                ),
                NavigationTraceStep(
                    operation="search_sources",
                    query=question,
                    result_ids=[
                        str(candidate.get("source_id"))
                        for candidate in diagnostics.get("top_source_candidates", [])[:20]
                    ],
                    notes=["source_catalog_lane", "answer_neutral_source_nomination"],
                ),
                NavigationTraceStep(
                    operation="rank_chunks_fusion",
                    query=question,
                    result_ids=[match.chunk.chunk_id for match in matches],
                    notes=["evidence_only", "policy_annotated_not_filtered", "multi_channel_fusion"],
                ),
                NavigationTraceStep(
                    operation="build_evidence_clusters",
                    query=question,
                    result_ids=[cluster.cluster_id for cluster in clusters],
                    notes=["grouped_by_source_family_source_or_kind"],
                ),
            ],
        )
        hierarchy_report = self._source_hierarchy_report(question, clusters)
        missing_facets = self.find_missing_facets(question, clusters)
        for cluster in clusters:
            cluster.missing_evidence_signals.extend(missing_facets)
        self._last_clusters_by_id = {cluster.cluster_id: cluster for cluster in clusters}
        return clusters, trace, hierarchy_report

    def _diverse_cluster_matches(
        self,
        matches: list[_ChunkMatch],
        *,
        max_records: int,
    ) -> list[_ChunkMatch]:
        matches = sorted(matches, key=self._cluster_match_selection_score, reverse=True)
        selected: list[_ChunkMatch] = []
        selected_chunk_ids: set[str] = set()
        seen_source_ids: set[str] = set()
        for match in matches:
            if match.chunk.source_id in seen_source_ids:
                continue
            selected.append(match)
            selected_chunk_ids.add(match.chunk.chunk_id)
            seen_source_ids.add(match.chunk.source_id)
            if len(selected) >= max_records:
                return selected
        for match in matches:
            if match.chunk.chunk_id in selected_chunk_ids:
                continue
            selected.append(match)
            if len(selected) >= max_records:
                break
        return selected

    def _cluster_match_selection_score(self, match: _ChunkMatch) -> float:
        label = searchable_text(
            match.chunk.extracted_anchor_label or match.chunk.chunk_id
        )
        score = match.score
        label_term_hits = {
            term
            for term in [*match.matched_terms, *match.matched_phrases]
            if term and contains_term(label, term)
        }
        score += min(0.1, 0.025 * len(label_term_hits))
        score += 0.08 * (match.channel_scores or {}).get("source_catalog", 0.0)
        score += 0.18 * (match.channel_scores or {}).get("facet_coverage", 0.0)
        if any(
            marker in label
            for marker in ("article", "chapter", "section", "clause")
        ):
            score += 0.18
        elif "annex" in label:
            score += 0.04
        if match.chunk.extracted_anchor_label is None:
            score -= 0.12
        if match.chunk.chunk_id.endswith("::document"):
            score -= 0.08
        return score

    def lookup_source(self, source_id: str):
        return self._sources_by_id.get(source_id)

    def list_source_structure(self, source_id: str) -> list[str]:
        return [
            chunk.extracted_anchor_label or "document"
            for chunk in self._chunks_by_id.values()
            if chunk.source_id == source_id
        ]

    def open_passage(self, source_id: str, locator: str | None, context: int | None = None) -> SourceChunk | None:
        source_chunks = [
            chunk for chunk in self._chunks_by_id.values() if chunk.source_id == source_id
        ]
        if not locator:
            return source_chunks[0] if source_chunks else None
        normalized_locator = normalize_text_for_matching(locator)
        for chunk in source_chunks:
            label = normalize_text_for_matching(chunk.extracted_anchor_label or chunk.chunk_id)
            if normalized_locator in label or label in normalized_locator:
                return chunk
        return None

    def open_adjacent_passages(
        self,
        source_id: str,
        locator: str | None,
        *,
        before: int = 1,
        after: int = 1,
    ) -> list[SourceChunk]:
        source_chunks = [
            chunk for chunk in self._chunks_by_id.values() if chunk.source_id == source_id
        ]
        if not source_chunks:
            return []
        selected = self.open_passage(source_id, locator)
        if selected is None:
            return source_chunks[: before + after + 1]
        index = source_chunks.index(selected)
        start = max(0, index - before)
        end = min(len(source_chunks), index + after + 1)
        return source_chunks[start:end]

    def get_claim_evidence(self, claim_id: str) -> EvidenceCluster | None:
        claim = self._claims_by_id.get(claim_id)
        if claim is None:
            return None
        records: list[EvidenceClusterRecord] = []
        for chunk_id in claim.chunk_ids:
            chunk = self._chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            records.append(
                self._record_for_match(
                    _ChunkMatch(
                        chunk=chunk,
                        score=1.0,
                        matched_terms=tuple(_terms(claim.normalized_statement)),
                    )
                )
            )
        if not records:
            for source_id in claim.source_ids:
                source_chunks = [
                    chunk for chunk in self._chunks_by_id.values() if chunk.source_id == source_id
                ]
                if source_chunks:
                    records.append(
                        self._record_for_match(
                            _ChunkMatch(
                                chunk=source_chunks[0],
                                score=0.5,
                                matched_terms=tuple(_terms(claim.normalized_statement)),
                            )
                        )
                    )
        return EvidenceCluster(
            cluster_id=f"claim_{claim.claim_id}",
            label=claim.topic or claim.claim_id,
            matched_concepts=sorted(set(_terms(claim.normalized_statement))),
            candidate_claim_ids=[claim.claim_id],
            supporting_chunk_ids=[record.chunk_id for record in records],
            source_ids=sorted({source_id for source_id in claim.source_ids if source_id}),
            records=records,
            confidence=claim.status.value,
            sufficiency_signals=["claim_candidate_present"],
            missing_evidence_signals=[] if records else ["claim_has_no_resolvable_chunk"],
        )

    def trace_concept(
        self,
        term_or_concept_id: str,
        *,
        include_aliases: bool = True,
        include_related: bool = True,
    ) -> ConceptRecord | None:
        normalized_query = normalize_text_for_matching(term_or_concept_id)
        for concept in self._concepts_by_id.values():
            labels = [concept.concept_id, concept.canonical_label]
            if include_aliases:
                labels.extend(concept.aliases)
            if any(normalize_text_for_matching(label) == normalized_query for label in labels):
                if include_related:
                    return concept
                return ConceptRecord(
                    concept_id=concept.concept_id,
                    canonical_label=concept.canonical_label,
                    aliases=list(concept.aliases),
                    linked_claim_ids=list(concept.linked_claim_ids),
                    linked_chunk_ids=list(concept.linked_chunk_ids),
                    linked_source_ids=list(concept.linked_source_ids),
                    review_status=concept.review_status,
                )
        matched_chunks = self.search_chunks(term_or_concept_id)
        matched_claims = self.search_claims(term_or_concept_id)
        if not matched_chunks and not matched_claims:
            return None
        concept_id = re.sub(r"[^a-z0-9]+", "_", normalized_query).strip("_") or "concept"
        return ConceptRecord(
            concept_id=f"derived_{concept_id}",
            canonical_label=term_or_concept_id,
            aliases=[],
            related_concept_ids=[],
            linked_claim_ids=[claim.claim_id for claim in matched_claims],
            linked_chunk_ids=[record.chunk_id for record in matched_chunks],
            linked_source_ids=sorted(
                {record.source_id for record in matched_chunks}
                | {source_id for claim in matched_claims for source_id in claim.source_ids}
            ),
            review_status="derived",
        )

    def expand_relations(
        self,
        claim_ids_or_source_ids: Iterable[str],
        relation_types: Iterable[str] | None = None,
        depth: int = 1,
    ) -> list[RelationGraphEdge]:
        relation_filter = set(relation_types or [])
        frontier = {item for item in claim_ids_or_source_ids if item}
        seen_edges: set[str] = set()
        selected: list[RelationGraphEdge] = []
        for _ in range(max(1, depth)):
            next_frontier: set[str] = set()
            for edge in self._relations_by_id.values():
                if edge.edge_id in seen_edges:
                    continue
                if relation_filter and edge.relation_type not in relation_filter:
                    continue
                edge_nodes = {edge.source_id, edge.target_id, *edge.evidence_source_ids}
                if not frontier.intersection(edge_nodes):
                    continue
                seen_edges.add(edge.edge_id)
                selected.append(edge)
                next_frontier.update(edge_nodes)
            if not next_frontier:
                break
            frontier = next_frontier
        return selected

    def compare_sources(self, source_ids_or_claim_ids: Iterable[str]) -> list[dict]:
        source_ids: set[str] = set()
        for item in source_ids_or_claim_ids:
            if item in self._claims_by_id:
                source_ids.update(self._claims_by_id[item].source_ids)
            else:
                source_ids.add(item)
        comparisons: list[dict] = []
        for source_id in sorted(source_ids):
            source = self._sources_by_id.get(source_id)
            if source is None:
                comparisons.append({"source_id": source_id, "status": "missing"})
                continue
            comparisons.append(
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "source_role_level": source.source_role_level.value,
                    "source_kind": source.source_kind.value,
                    "document_status": source.document_status.value,
                    "evidence_tier": source.evidence_tier.value,
                    "binding_level": source.binding_level.value,
                    "jurisdiction": source.jurisdiction,
                    "publication_date": source.publication_date,
                    "version_date": source.version_date,
                    "effective_date": source.effective_date,
                    "legacy_source_ids": list(source.legacy_source_ids),
                    "archive_source_id": source.archive_source_id,
                }
            )
        return comparisons

    def find_counterevidence(
        self,
        claim_or_question: str,
        filters: dict | None = None,
    ) -> list[EvidenceClusterRecord]:
        counter_markers = {
            "conflict",
            "contradict",
            "inconsistent",
            "invalid",
            "not",
            "nicht",
            "revocation",
            "revoked",
            "suspend",
            "widerruf",
            "unless",
        }
        records = self.search_chunks(claim_or_question, filters=filters)
        counter_records = [
            record
            for record in records
            if counter_markers.intersection(_terms(record.snippet))
        ]
        return counter_records[:10]

    def get_open_issues(self, claim_ids_or_terms: Iterable[str] | str) -> list[OpenIssueRecord]:
        terms = [claim_ids_or_terms] if isinstance(claim_ids_or_terms, str) else list(claim_ids_or_terms)
        normalized_terms = set(_terms(" ".join(terms)))
        exact_ids = {term for term in terms if term}
        issues: list[OpenIssueRecord] = []
        for issue in self._open_issues_by_id.values():
            direct_match = bool(
                exact_ids.intersection(
                    {
                        issue.issue_id,
                        *issue.affected_claim_ids,
                        *issue.blocks_claim_ids,
                        *issue.qualifies_claim_ids,
                        *issue.affected_source_ids,
                        *issue.affected_concept_ids,
                    }
                )
            )
            haystack = normalize_text_for_matching(
                " ".join(
                    [
                        issue.issue_statement,
                        issue.reason_open,
                        " ".join(issue.affected_answer_facets),
                    ]
                )
            )
            term_match = bool(normalized_terms and any(term in haystack for term in normalized_terms))
            if direct_match or term_match:
                issues.append(issue)
        return issues

    def find_missing_facets(
        self,
        question: str,
        evidence_clusters: list[EvidenceCluster] | None = None,
    ) -> list[str]:
        clusters = evidence_clusters if evidence_clusters is not None else self._last_clusters_by_id.values()
        matched_text = normalize_text_for_matching(
            " ".join(
                [
                    " ".join(cluster.matched_concepts)
                    + " "
                    + " ".join(record.snippet for record in cluster.records)
                    for cluster in clusters
                ]
            )
        )
        question_terms = set(_terms(question))
        facet_families = {
            "authority_or_register": {"authentic", "register", "registrar", "source", "official"},
            "wallet_or_provider": {"wallet", "provider", "unit", "attestation"},
            "mandate_or_delegation": {"mandate", "delegation", "authority", "representation", "vertretung"},
            "status_or_revocation": {"status", "revocation", "revoked", "widerruf", "suspend"},
            "audit_or_log": {"audit", "log", "trace", "transaction", "timestamp"},
            "cross_border_or_identity": {"identity", "natural", "legal", "person", "juristic", "grenz"},
        }
        missing: list[str] = []
        for facet, indicators in facet_families.items():
            if not question_terms.intersection(indicators):
                continue
            if not any(indicator in matched_text for indicator in indicators):
                missing.append(f"missing_{facet}_evidence")
        return missing

    def explain_result(self, result_id_or_cluster_id: str) -> dict | None:
        cluster = self._last_clusters_by_id.get(result_id_or_cluster_id)
        if cluster is not None:
            return {
                "result_id": result_id_or_cluster_id,
                "result_type": "evidence_cluster",
                "source_ids": list(cluster.source_ids),
                "chunk_ids": list(cluster.supporting_chunk_ids),
                "candidate_claim_ids": list(cluster.candidate_claim_ids),
                "relation_edge_ids": list(cluster.relation_edge_ids),
                "open_issue_ids": list(cluster.open_issue_ids),
                "confidence": cluster.confidence,
                "sufficiency_signals": list(cluster.sufficiency_signals),
                "missing_evidence_signals": list(cluster.missing_evidence_signals),
            }
        if result_id_or_cluster_id in self._chunks_by_id:
            chunk = self._chunks_by_id[result_id_or_cluster_id]
            return {
                "result_id": result_id_or_cluster_id,
                "result_type": "chunk",
                "source_id": chunk.source_id,
                "locator": chunk.extracted_anchor_label,
                "source_role_level": chunk.source_role_level.value,
                "document_status": chunk.document_status.value,
                "evidence_tier": chunk.evidence_tier.value,
                "binding_level": chunk.binding_level.value,
            }
        if result_id_or_cluster_id in self._claims_by_id:
            claim = self._claims_by_id[result_id_or_cluster_id]
            return {
                "result_id": result_id_or_cluster_id,
                "result_type": "candidate_claim",
                "source_ids": list(claim.source_ids),
                "chunk_ids": list(claim.chunk_ids),
                "status": claim.status.value,
                "evidence_tier": claim.evidence_tier.value,
                "binding_level": claim.binding_level.value,
            }
        return None

    def _rank_chunks(self, question_or_terms: str, filters: dict | None = None) -> list[_ChunkMatch]:
        expansion = expand_query(question_or_terms, self._terminology)
        self._last_question_facets = detect_question_facets(question_or_terms)
        terms = list(expansion.all_terms)
        if not terms:
            return []
        source_candidates = retrieve_source_candidates(
            self.ingestion_bundle.catalog,
            expansion,
            candidate_claims=self._claims_by_id.values(),
            open_issues=self._open_issues_by_id.values(),
            relation_edges=self._relations_by_id.values(),
        )
        source_candidates_by_id = {
            candidate.source_id: candidate for candidate in source_candidates
        }
        claim_scores_by_source, claim_scores_by_chunk = self._claim_retrieval_scores(expansion)
        source_kind_filter = set((filters or {}).get("source_kinds", []))
        matches: list[_ChunkMatch] = []
        for chunk in self._chunks_by_id.values():
            if source_kind_filter and chunk.source_kind.value not in source_kind_filter:
                continue
            source_candidate = source_candidates_by_id.get(chunk.source_id)
            source_candidate_score = source_candidate.score if source_candidate is not None else 0.0
            normalized_text = searchable_text(
                "\n".join(
                    value
                    for value in (
                        chunk.title,
                        chunk.extracted_anchor_label or "",
                        chunk.text,
                    )
                    if value
                )
            )
            normalized_label = searchable_text(
                " ".join([chunk.title, chunk.extracted_anchor_label or ""])
            )
            matched_terms = tuple(term for term in terms if contains_term(normalized_text, term))
            matched_phrases = tuple(
                phrase for phrase in expansion.phrases if contains_term(normalized_text, phrase)
            )
            if (
                not matched_terms
                and not matched_phrases
                and source_candidate_score < SOURCE_RESCUE_THRESHOLD
                and claim_scores_by_source.get(chunk.source_id, 0.0) <= 0
            ):
                continue
            term_total = max(
                1.0,
                sum(expansion.term_weights.get(term, 1.0) for term in set(terms)),
            )
            lexical_score = min(
                1.0,
                sum(expansion.term_weights.get(term, 1.0) for term in set(matched_terms))
                / term_total,
            )
            phrase_total = max(
                1.0,
                sum(expansion.term_weights.get(phrase, 2.0) for phrase in set(expansion.phrases)),
            )
            phrase_score = min(
                1.0,
                sum(expansion.term_weights.get(phrase, 2.0) for phrase in set(matched_phrases))
                / phrase_total,
            )
            label_hits = [
                term
                for term in [*matched_terms, *matched_phrases]
                if contains_term(normalized_label, term)
            ]
            label_score = min(1.0, len(label_hits) / max(1, len(set([*matched_terms, *matched_phrases]))))
            claim_score = max(
                claim_scores_by_source.get(chunk.source_id, 0.0),
                claim_scores_by_chunk.get(chunk.chunk_id, 0.0),
            )
            citation_score = 0.1 if chunk.citation_quality.value == "anchor_grounded" else 0.02
            role_score = {
                "high": 0.11,
                "medium": 0.08,
                "low": 0.02,
            }.get(chunk.source_role_level.value, 0.0)
            anchor_label_score = 0.08 if chunk.extracted_anchor_label else 0.0
            facet_tags = facet_tags_for_text(normalized_text, self._last_question_facets)
            facet_score = (
                min(1.0, len(facet_tags) / max(1, len(self._last_question_facets)))
                if self._last_question_facets
                else 0.0
            )
            channel_scores = {
                "chunk_lexical": lexical_score,
                "phrase_match": phrase_score,
                "source_catalog": source_candidate_score,
                "source_label": label_score,
                "imported_claim": claim_score,
                "citation_anchor": citation_score,
                "source_role": role_score,
                "anchor_label": anchor_label_score,
                "facet_coverage": facet_score,
            }
            score = min(
                1.0,
                0.46 * lexical_score
                + 0.24 * phrase_score
                + 0.34 * source_candidate_score
                + 0.10 * label_score
                + 0.16 * claim_score
                + 0.16 * facet_score
                + citation_score
                + role_score
                + anchor_label_score,
            )
            matches.append(
                _ChunkMatch(
                    chunk=chunk,
                    score=score,
                    matched_terms=matched_terms,
                    matched_phrases=matched_phrases,
                    channel_scores=channel_scores,
                )
            )
        matches.sort(key=lambda item: item.score, reverse=True)
        selected = self._select_ranked_matches(matches, source_candidates)
        self._last_retrieval_diagnostics = self._build_retrieval_diagnostics(
            question_or_terms,
            expansion,
            source_candidates,
            matches,
            selected,
        )
        return selected

    def _claim_retrieval_scores(
        self,
        expansion: QueryExpansion,
    ) -> tuple[dict[str, float], dict[str, float]]:
        scores_by_source: dict[str, float] = {}
        scores_by_chunk: dict[str, float] = {}
        distinctive_terms = expansion.distinctive_terms or expansion.all_terms
        total = max(
            1.0,
            sum(expansion.term_weights.get(term, 1.0) for term in distinctive_terms),
        )
        for claim in self._claims_by_id.values():
            surface = searchable_text(
                " ".join(
                    value
                    for value in (
                        claim.normalized_statement,
                        claim.topic or "",
                        claim.actor or "",
                        claim.action or "",
                        claim.object or "",
                        claim.modality or "",
                    )
                    if value
                )
            )
            matched = [
                term for term in distinctive_terms if contains_term(surface, term)
            ]
            if not matched:
                continue
            score = min(
                1.0,
                sum(expansion.term_weights.get(term, 1.0) for term in matched) / total,
            )
            for source_id in claim.source_ids:
                scores_by_source[source_id] = max(scores_by_source.get(source_id, 0.0), score)
            for chunk_id in claim.chunk_ids:
                scores_by_chunk[chunk_id] = max(scores_by_chunk.get(chunk_id, 0.0), score)
        return scores_by_source, scores_by_chunk

    def _select_ranked_matches(
        self,
        matches: list[_ChunkMatch],
        source_candidates: list[SourceRetrievalCandidate],
        *,
        limit: int = 140,
    ) -> list[_ChunkMatch]:
        selected = list(matches[:limit])
        selected_chunk_ids = {match.chunk.chunk_id for match in selected}
        rescued_matches: list[_ChunkMatch] = []
        strong_source_ids = [
            candidate.source_id
            for candidate in source_candidates
            if self._should_rescue_source_candidate(candidate)
        ]
        for source_id in strong_source_ids:
            if any(match.chunk.source_id == source_id for match in selected):
                continue
            source_matches = [match for match in matches if match.chunk.source_id == source_id]
            if not source_matches:
                continue
            best_match = max(source_matches, key=lambda match: match.score)
            if best_match.chunk.chunk_id in selected_chunk_ids:
                continue
            selected.append(best_match)
            rescued_matches.append(best_match)
            selected_chunk_ids.add(best_match.chunk.chunk_id)
        selected.sort(key=lambda item: item.score, reverse=True)
        if len(selected) <= limit:
            return selected
        rescued_by_chunk_id = {
            match.chunk.chunk_id: match for match in rescued_matches
        }
        rescued = sorted(
            rescued_by_chunk_id.values(),
            key=lambda item: item.score,
            reverse=True,
        )[:limit]
        rescue_chunk_ids = {match.chunk.chunk_id for match in rescued}
        remaining_budget = max(0, limit - len(rescued))
        top_non_rescued = [
            match for match in selected if match.chunk.chunk_id not in rescue_chunk_ids
        ][:remaining_budget]
        final = [*top_non_rescued, *rescued]
        final.sort(key=lambda item: item.score, reverse=True)
        return final

    def _should_rescue_source_candidate(
        self,
        candidate: SourceRetrievalCandidate,
    ) -> bool:
        if candidate.score >= SOURCE_RESCUE_THRESHOLD:
            return True
        claim_score = candidate.channel_scores.get("imported_claim_signal", 0.0)
        relation_score = candidate.channel_scores.get("relation_signal", 0.0)
        issue_score = candidate.channel_scores.get("open_issue_signal", 0.0)
        return (
            issue_score >= 0.2
            or claim_score >= 0.12
            or (claim_score >= 0.04 and relation_score >= 0.8)
        )

    def _chunk_match_diagnostic(self, match: _ChunkMatch) -> dict[str, object]:
        facet_surface = " ".join(
            [
                match.chunk.title,
                match.chunk.extracted_anchor_label or "",
                match.chunk.text,
            ]
        )
        return {
            "source_id": match.chunk.source_id,
            "chunk_id": match.chunk.chunk_id,
            "locator": match.chunk.extracted_anchor_label,
            "score": round(match.score, 4),
            "matched_terms": list(match.matched_terms),
            "matched_phrases": list(match.matched_phrases),
            "facet_tags": facet_tags_for_text(
                facet_surface,
                self._last_question_facets,
            ),
            "channel_scores": {
                key: round(value, 4)
                for key, value in (match.channel_scores or {}).items()
            },
        }

    def _build_retrieval_diagnostics(
        self,
        question: str,
        expansion: QueryExpansion,
        source_candidates: list[SourceRetrievalCandidate],
        all_matches: list[_ChunkMatch],
        selected_matches: list[_ChunkMatch],
    ) -> dict[str, object]:
        selected_chunk_ids = {match.chunk.chunk_id for match in selected_matches}
        selected_source_ids = sorted({match.chunk.source_id for match in selected_matches})
        dropped_close = [
            match
            for match in all_matches
            if match.chunk.chunk_id not in selected_chunk_ids and match.score >= 0.35
        ][:30]
        return {
            "question": question,
            "original_terms": list(expansion.original_terms),
            "expanded_terms": list(expansion.all_terms),
            "distinctive_terms": list(expansion.distinctive_terms),
            "question_facets": list(self._last_question_facets),
            "phrases": list(expansion.phrases),
            "term_weights": {
                term: round(weight, 3)
                for term, weight in sorted(expansion.term_weights.items())
            },
            "expansion_traces": list(expansion.traces),
            "top_source_candidates": [
                candidate.to_diagnostic() for candidate in source_candidates[:25]
            ],
            "top_chunk_candidates": [
                self._chunk_match_diagnostic(match) for match in all_matches[:60]
            ],
            "dropped_but_close_candidates": [
                self._chunk_match_diagnostic(match) for match in dropped_close
            ],
            "selected_source_ids": selected_source_ids,
            "selected_chunk_ids": [match.chunk.chunk_id for match in selected_matches],
            "notes": [
                "source_catalog_lane_nominates_sources_only",
                "chunk_ranking_uses_multi_channel_fusion",
                "source_rescue_threshold:" + str(SOURCE_RESCUE_THRESHOLD),
            ],
        }

    def retrieval_diagnostics(self) -> dict[str, object] | None:
        return self._last_retrieval_diagnostics

    def _record_for_match(self, match: _ChunkMatch) -> EvidenceClusterRecord:
        chunk = match.chunk
        return EvidenceClusterRecord(
            record_id=f"record_{chunk.chunk_id}",
            source_id=chunk.source_id,
            chunk_id=chunk.chunk_id,
            locator=chunk.extracted_anchor_label,
            snippet=_snippet(chunk.text, [*match.matched_terms, *match.matched_phrases]),
            source_role_level=chunk.source_role_level,
            source_kind=chunk.source_kind,
            document_status=chunk.document_status,
            evidence_tier=chunk.evidence_tier,
            binding_level=chunk.binding_level,
            jurisdiction=chunk.jurisdiction,
            effective_date=chunk.effective_date,
            version_date=chunk.version_date,
            score=match.score,
        )

    def _source_hierarchy_report(
        self,
        question: str,
        clusters: list[EvidenceCluster],
    ) -> SourceHierarchyReport:
        by_role: dict[str, set[str]] = defaultdict(set)
        by_binding: dict[str, set[str]] = defaultdict(set)
        for cluster in clusters:
            for record in cluster.records:
                by_role[record.source_role_level.value].add(record.source_id)
                by_binding[record.binding_level.value].add(record.source_id)
        return SourceHierarchyReport(
            question=question,
            source_ids_by_role={
                key: sorted(value) for key, value in sorted(by_role.items())
            },
            source_ids_by_binding_level={
                key: sorted(value) for key, value in sorted(by_binding.items())
            },
            notes=["Knowledge Service discovery is evidence-only and non-governing."],
        )
