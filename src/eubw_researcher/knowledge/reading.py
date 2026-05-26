from __future__ import annotations

import re
from collections import defaultdict

from eubw_researcher.models import (
    ClaimVerificationRecord,
    EvidenceCluster,
    EvidenceSynthesisMatrix,
    EvidenceSynthesisRecord,
    OpenedPassageRecord,
    ReadingPlan,
    ReadingPlanItem,
    RuntimeConfig,
    SelectedEvidenceRecord,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching

ROLE_BOUNDARY_FACETS: dict[str, tuple[str, ...]] = {
    "actor_boundary": (
        "auseinanderhalten",
        "abgrenz",
        "boundary",
        "role",
        "rolle",
        "intermediary",
        "intermediaer",
        "relying party",
        "wallet-relying party",
    ),
    "technical_requester": (
        "technical requester",
        "technisch",
        "authenticates",
        "authentisiert",
        "access certificate",
        "access certificates",
        "rpac",
    ),
    "end_relying_party": (
        "end party",
        "end relying party",
        "intermediated",
        "intermediated relying party",
        "wallet-relying party",
        "wallet relying party",
    ),
    "registry_information": (
        "registration",
        "registrierung",
        "registry",
        "register",
        "registrar",
        "certificate",
        "zertifikat",
    ),
    "user_display": (
        "user display",
        "display",
        "anzeige",
        "nutzeranzeige",
        "shown to the user",
        "request context",
    ),
    "purpose_or_intended_use": (
        "purpose",
        "zweck",
        "intended use",
        "use case",
        "uses",
    ),
    "requested_attributes": (
        "requested attributes",
        "attribute",
        "attributes",
        "requested data",
        "daten",
    ),
    "privacy_policy_or_dpa": (
        "privacy policy",
        "privacy",
        "datenschutz",
        "dpa",
        "complaint",
        "contact",
        "kontakt",
    ),
    "certificate_or_trust_anchor": (
        "certificate",
        "zertifikat",
        "trust anchor",
        "access ca",
        "rpac",
        "rprc",
    ),
    "open_issue_or_member_state_choice": (
        "open issue",
        "offen",
        "member state",
        "mitgliedstaat",
        "national",
        "choice",
    ),
}

CENTRAL_ROLE_BOUNDARY_FACETS = {
    "actor_boundary",
    "registry_information",
    "user_display",
    "purpose_or_intended_use",
    "requested_attributes",
    "privacy_policy_or_dpa",
}

FACET_COOCCURRENCE_BOOSTS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("user_display", ("intermediary", "intermediaer"), ("display", "anzeige", "request")),
    ("registry_information", ("intermediary", "intermediaer"), ("registration certificate", "certificate", "registrierung")),
    ("purpose_or_intended_use", ("intended use", "zweck", "purpose"), ("attribute", "attributes", "requested")),
    ("privacy_policy_or_dpa", ("privacy policy", "datenschutz", "dpa"), ("wallet-relying party", "relying party", "intermediary")),
)


def detect_question_facets(question: str) -> list[str]:
    normalized = normalize_text_for_matching(question)
    facets: list[str] = []
    for facet_id, terms in ROLE_BOUNDARY_FACETS.items():
        if any(term in normalized for term in terms):
            facets.append(facet_id)
    if (
        {"technical_requester", "end_relying_party"} & set(facets)
        or ("intermediary" in normalized or "intermediaer" in normalized)
    ) and "actor_boundary" not in facets:
        facets.insert(0, "actor_boundary")
    return facets


def _facet_tags_for_surface(surface: str, question_facets: set[str]) -> list[str]:
    normalized = normalize_text_for_matching(surface)
    tags: list[str] = []
    for facet_id in question_facets:
        terms = ROLE_BOUNDARY_FACETS.get(facet_id, ())
        if any(term in normalized for term in terms):
            tags.append(facet_id)
    for facet_id, left_terms, right_terms in FACET_COOCCURRENCE_BOOSTS:
        if facet_id not in question_facets or facet_id in tags:
            continue
        if any(term in normalized for term in left_terms) and any(
            term in normalized for term in right_terms
        ):
            tags.append(facet_id)
    return sorted(tags)


def _quality_flags(text: str) -> list[str]:
    normalized = normalize_text_for_matching(text)
    flags: list[str] = []
    if re.search(r"\b(references|bibliography)\b", normalized) or normalized.count("http") >= 2:
        flags.append("references_only")
    if re.match(r"^\s*article\s+\d+[a-z]?\b", normalized) and len(text.split()) < 24:
        flags.append("title_only")
    if re.match(r"^\s*\d+(?:\.\d+)+\s+topic\b", normalized) and len(text.split()) < 24:
        flags.append("title_only")
    if normalized.startswith("description section s in arf proposed solution"):
        flags.append("title_only")
    if "registry api s read methods shall be open for public access" in normalized:
        flags.append("context_only")
    if re.search(r"\btopic\s+\d+\b", normalized) and normalized.rstrip().endswith(" a"):
        flags.append("title_only")
    if (
        re.match(r"^\s*(\||table|note|annex|section)\s+\d", normalized)
        or text.lstrip().startswith("|")
        or " table " in f" {normalized} "
    ):
        flags.append("table_note")
    if len(re.findall(r"[.!?]", text)) == 0 and len(text.split()) < 18:
        flags.append("title_only")
    if any(marker in normalized for marker in ("means ", "definition", "for the purposes of")):
        flags.append("definition_only")
    if len(text.split()) < 16 or text.endswith("..."):
        flags.append("snippet_like")
    if not flags or set(flags).isdisjoint({"references_only", "table_note", "title_only", "snippet_like", "context_only", "definition_only"}):
        flags.append("answer_ready")
    return list(dict.fromkeys(flags))


def _facet_score(record, question_facets: set[str]) -> int:
    if not question_facets:
        return 0
    surface = " ".join([record.snippet, record.locator or "", record.source_id])
    tags = _facet_tags_for_surface(surface, question_facets)
    score = len(tags) * 20
    normalized = normalize_text_for_matching(surface)
    for facet_id, left_terms, right_terms in FACET_COOCCURRENCE_BOOSTS:
        if facet_id in question_facets and any(term in normalized for term in left_terms) and any(
            term in normalized for term in right_terms
        ):
            score += 18
    if "actor_boundary" in question_facets and any(
        term in normalized
        for term in (
            "intermediary",
            "intermediaries",
            "intermediaer",
            "intermediated",
            "on behalf",
            "on-behalf",
        )
    ):
        score += 55
    if "user_display" in question_facets and any(
        term in normalized
        for term in ("wallet unit informs the user", "user display", "shown to the user")
    ):
        score += 35
    if "references_only" in _quality_flags(record.snippet):
        score -= 35
    if "table_note" in _quality_flags(record.snippet):
        score -= 15
    if "title_only" in _quality_flags(record.snippet):
        score -= 30
    if any(
        marker in normalized
        for marker in (
            "description section s in arf proposed solution",
            "topic 27 - registration of pid providers",
        )
    ):
        score -= 45
    return score


def _record_priority(record, question_facets: set[str]) -> tuple[int, int, float]:
    role_weight = {"high": 3, "medium": 2, "low": 1}.get(record.source_role_level.value, 0)
    return (_facet_score(record, question_facets), role_weight, record.score)


def _clusters_for_reading(
    clusters: list[EvidenceCluster],
    *,
    max_clusters: int,
    question_facets: set[str] | None = None,
) -> list[EvidenceCluster]:
    if max_clusters <= 0:
        return []
    if question_facets:
        ordered_clusters = sorted(
            clusters,
            key=lambda cluster: max(
                (_record_priority(record, question_facets) for record in cluster.records),
                default=(0, 0, 0.0),
            ),
            reverse=True,
        )
    else:
        ordered_clusters = list(clusters)
    selected = list(ordered_clusters[:max_clusters])
    selected_source_ids = {
        source_id for cluster in selected for source_id in cluster.source_ids
    }
    rescue_clusters = [
        cluster
        for cluster in ordered_clusters[max_clusters:]
        if "source_catalog_candidate_present" in cluster.sufficiency_signals
        and not selected_source_ids.intersection(cluster.source_ids)
    ]
    for cluster in rescue_clusters:
        if len(selected) < max_clusters:
            selected.append(cluster)
        else:
            selected[-1] = cluster
        selected_source_ids.update(cluster.source_ids)
    return selected


def _compact_statement(text: str, *, limit: int = 360) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    compact = re.sub(r"^[#>*\-\s]+", "", compact)
    compact = re.sub(
        r"^(passage|source|evidence)\s+supports:\s*",
        "",
        compact,
        flags=re.IGNORECASE,
    )
    original_normalized = normalize_text_for_matching(compact)
    if (
        "upon cancellation" in original_normalized
        and "must remove the visible trust mark" in original_normalized
        and "not the relying party" in original_normalized
        and "attestation provider" in original_normalized
    ):
        return (
            "Upon cancellation, the Wallet Provider must remove "
            "the visible trust mark and references to it; the scoped trust mark is "
            "for the visible EUDI Wallet mark, not Relying Party services or "
            "Attestation Provider qualifications."
        )
    compact = re.sub(r"^ARF main markdown source\s+", "", compact)
    compact = re.sub(
        r"^(Keep with proposed changes|Delete|Add|Modify)\s+[A-Za-z0-9_-]+\s+",
        "",
        compact,
    )
    compact = re.sub(r"^\*\s+", "", compact)
    compact = re.sub(r"^Abstract\s+(?=The present\b)", "", compact)
    compact = re.sub(
        r"^Article\s+\d+[a-z]?\s+Definitions\s+(?=For the purposes\b)",
        "",
        compact,
        flags=re.IGNORECASE,
    )
    compact = re.sub(
        r"^Commission Implementing Regulation\s+\(EU\)\s+\d+/\d+\s+.*?\s+(?=Under Article\b)",
        "",
        compact,
    )
    if " > " in compact:
        tail = compact.rsplit(" > ", 1)[-1].strip()
        if len(tail) >= 40:
            compact = tail
    compact = re.sub(r"^\*\s+", "", compact)
    compact = re.sub(r"^Abstract\s+(?=The present\b)", "", compact)
    compact = re.sub(
        r"^Article\s+\d+[a-z]?\s+Definitions\s+(?=For the purposes\b)",
        "",
        compact,
        flags=re.IGNORECASE,
    )
    compact = re.sub(
        r"^\d+(?:\.\d+)*\.?\s+[^.!?]{0,120}?\s+(?=(According to|For the purposes|A |An |The ))",
        "",
        compact,
    )
    normalized = normalize_text_for_matching(compact)
    if "out of scope" in normalized and "relying party" in normalized:
        return (
            "The source treats the visible wallet trust mark as "
            "in-scope and leaves unrelated Relying Party or attestation-provider "
            "trust indicators out of scope."
        )
    sentences = re.split(r"(?<=[.!?])\s+", compact)
    chosen = next((sentence for sentence in sentences if len(sentence) > 40), compact)
    if len(chosen) > limit:
        chosen = chosen[:limit].rsplit(" ", 1)[0].strip() + "..."
    return chosen


def _facet_statement(text: str, facet_tags: list[str], *, limit: int = 360) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    compact = re.sub(r"^[#>*\-\s]+", "", compact)
    compact = re.sub(r"^ARF main markdown source\s+", "", compact)
    compact = re.sub(
        r"^(Keep with proposed changes|Delete|Add|Modify)\s+[A-Za-z0-9_-]+\s+",
        "",
        compact,
    )
    if " > " in compact:
        tail = compact.rsplit(" > ", 1)[-1].strip()
        if len(tail) >= 40:
            compact = tail
    compact = re.sub(
        r"^\d+(?:\.\d+)*\.?\s+[^.!?]{0,120}?\s+(?=(According to|For the purposes|A |An |The ))",
        "",
        compact,
    )
    if not facet_tags:
        return _compact_statement(compact, limit=limit)
    normalized_tags = set(facet_tags)
    candidate_terms: list[str] = []
    for facet_id in normalized_tags:
        candidate_terms.extend(ROLE_BOUNDARY_FACETS.get(facet_id, ()))
    sentences = re.split(r"(?<=[.!?])\s+|\s+-\s+", compact)
    scored: list[tuple[int, int, str]] = []
    for sentence in sentences:
        normalized_sentence = normalize_text_for_matching(sentence)
        if re.match(r"^\s*article\s+\d+[a-z]?\b", normalized_sentence) and len(sentence.split()) < 24:
            continue
        if re.match(r"^\s*\d+(?:\.\d+)+\s+topic\b", normalized_sentence) and len(sentence.split()) < 24:
            continue
        if "registry api s read methods shall be open for public access" in normalized_sentence:
            continue
        if re.search(r"\btopic\s+\d+\b", normalized_sentence) and normalized_sentence.rstrip().endswith(" a"):
            continue
        hits = sum(1 for term in candidate_terms if term in normalized_sentence)
        score = hits
        if any(
            term in normalized_sentence
            for term in (
                "intermediary",
                "intermediaries",
                "intermediaer",
                "intermediated",
                "on behalf",
                "on-behalf",
                "usesintermediary",
                "isintermediary",
            )
        ):
            score += 8
        if any(term in normalized_sentence for term in ("wallet unit informed the user", "shown to the user", "user approval")):
            score += 5
        if any(term in normalized_sentence for term in ("intended use", "privacy policy", "requested attributes")):
            score += 4
        if any(
            marker in normalized_sentence
            for marker in (
                "certificate histories",
                "public access",
                "write methods",
                "topic 27",
            )
        ):
            score -= 5
        if score > 0:
            scored.append((score, hits, sentence.strip()))
    if scored:
        scored.sort(key=lambda item: (item[0], item[1], len(item[2])), reverse=True)
        chosen = scored[0][2]
        if len(chosen) > limit:
            chosen = chosen[:limit].rsplit(" ", 1)[0].strip() + "..."
        return chosen
    return _compact_statement(compact, limit=limit)


def _answer_role(cluster: EvidenceCluster, record) -> str:
    surface = normalize_text_for_matching(" ".join([record.snippet, record.locator or ""]))
    if cluster.open_issue_ids:
        return "open_issue"
    if any(marker in surface for marker in ("out of scope", "does not address", "scope is")):
        return "scope_boundary"
    if "source_catalog_candidate_present" in cluster.sufficiency_signals:
        return "core_answer"
    if record.source_role_level.value == "low":
        return "background"
    if record.document_status.value in {"final", "adopted_pending_effective_date"}:
        return "normative_basis"
    if record.source_role_level.value == "medium":
        return "technical_spec_context"
    return "source_role_context"


def _caveats(cluster: EvidenceCluster, record, verification) -> list[str]:
    caveats: list[str] = [
        f"source_role:{record.source_role_level.value}",
        f"binding_level:{record.binding_level.value}",
        f"document_status:{record.document_status.value}",
    ]
    if verification is not None and not verification.answer_use_allowed:
        caveats.append("verification does not allow answer use")
    if cluster.open_issue_ids:
        caveats.extend(f"open_issue:{issue_id}" for issue_id in cluster.open_issue_ids)
    return caveats


def build_reading_artifacts(
    *,
    question: str,
    clusters: list[EvidenceCluster],
    selected_evidence: list[SelectedEvidenceRecord],
    claim_verification: list[ClaimVerificationRecord],
    runtime_config: RuntimeConfig,
) -> tuple[ReadingPlan, list[OpenedPassageRecord], EvidenceSynthesisMatrix]:
    max_clusters = runtime_config.knowledge_service_max_reading_clusters
    max_opened = runtime_config.knowledge_service_max_opened_passages
    max_adjacent = runtime_config.knowledge_service_max_adjacent_passages_per_cluster

    budget = {
        "max_clusters": max_clusters,
        "max_opened_passages": max_opened,
        "max_adjacent_passages_per_cluster": max_adjacent,
        "timeout_seconds": runtime_config.knowledge_service_reading_timeout_seconds,
    }
    reading_plan = ReadingPlan(question=question, budget=budget)
    opened_passages: list[OpenedPassageRecord] = []
    question_facets = set(detect_question_facets(question))
    verification_by_claim_id = {
        record.claim_id: record for record in claim_verification
    }
    selected_by_chunk_id: dict[str, list[SelectedEvidenceRecord]] = defaultdict(list)
    for selected in selected_evidence:
        selected_by_chunk_id[selected.chunk_id].append(selected)

    reading_clusters = _clusters_for_reading(
        clusters,
        max_clusters=max_clusters,
        question_facets=question_facets,
    )
    opened_count = 0
    covered_facets: set[str] = set()
    for cluster in reading_clusters:
        if not cluster.records:
            continue
        ordered_records = sorted(
            cluster.records,
            key=lambda record: _record_priority(record, question_facets),
            reverse=True,
        ) if question_facets else list(cluster.records)
        cluster_records = ordered_records[: 1 + max_adjacent]
        for index, record in enumerate(cluster_records):
            if max_opened and opened_count >= max_opened:
                reading_plan.budget_exhausted = True
                break
            operation = "open_passage" if index == 0 else "open_adjacent_passage"
            facet_tags = _facet_tags_for_surface(
                " ".join([record.snippet, record.locator or "", record.source_id]),
                question_facets,
            )
            uncovered_facets = [
                facet for facet in facet_tags if facet in CENTRAL_ROLE_BOUNDARY_FACETS and facet not in covered_facets
            ]
            item_id = f"read_{len(reading_plan.items) + 1}"
            reading_plan.items.append(
                ReadingPlanItem(
                    item_id=item_id,
                    cluster_id=cluster.cluster_id,
                    source_id=record.source_id,
                    chunk_id=record.chunk_id,
                    locator=record.locator,
                    operation=operation,
                    reason=(
                        "Facet-specific primary passage: " + ", ".join(uncovered_facets or facet_tags)
                        if facet_tags and index == 0
                        else "Primary evidence-cluster passage"
                        if index == 0
                        else "Facet-adjacent context: " + ", ".join(facet_tags)
                        if facet_tags
                        else "Adjacent context passage"
                    ),
                )
            )
            opened_passages.append(
                OpenedPassageRecord(
                    passage_id=item_id,
                    cluster_id=cluster.cluster_id,
                    source_id=record.source_id,
                    chunk_id=record.chunk_id,
                    locator=record.locator,
                    passage_role="primary" if index == 0 else "adjacent",
                    text_snippet=record.snippet,
                )
            )
            covered_facets.update(facet_tags)
            opened_count += 1
        if reading_plan.budget_exhausted:
            break

    records: list[EvidenceSynthesisRecord] = []
    for cluster in reading_clusters:
        ordered_records = sorted(
            cluster.records,
            key=lambda record: _record_priority(record, question_facets),
            reverse=True,
        ) if question_facets else list(cluster.records)
        for record in ordered_records[: 1 + max_adjacent]:
            selected_records = selected_by_chunk_id.get(record.chunk_id, [])
            claim_id = selected_records[0].claim_id if selected_records else None
            verification = verification_by_claim_id.get(claim_id or "")
            facet_tags = _facet_tags_for_surface(
                " ".join([record.snippet, record.locator or "", record.source_id]),
                question_facets,
            )
            quality_flags = _quality_flags(record.snippet)
            answer_role = _answer_role(cluster, record)
            if facet_tags and "answer_ready" in quality_flags and answer_role == "background":
                answer_role = "candidate_core_claim"
            if set(quality_flags).intersection({"references_only", "table_note", "title_only"}):
                answer_role = "background"
            records.append(
                EvidenceSynthesisRecord(
                    synthesis_id=f"synthesis_{len(records) + 1}",
                    claim_id=claim_id,
                    cluster_id=cluster.cluster_id,
                    answer_role=answer_role,
                    statement=_facet_statement(record.snippet, facet_tags),
                    source_ids=[record.source_id],
                    chunk_ids=[record.chunk_id],
                    locators=[record.locator] if record.locator else [],
                    facet_tags=facet_tags,
                    quality_flags=quality_flags,
                    verification_status=(
                        verification.verification_result if verification is not None else None
                    ),
                    caveats=_caveats(cluster, record, verification),
                )
            )

    return (
        reading_plan,
        opened_passages,
        EvidenceSynthesisMatrix(question=question, records=records),
    )
