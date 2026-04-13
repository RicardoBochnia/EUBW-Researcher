from __future__ import annotations

import hashlib
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Deque, Dict, List, Optional, Set, Tuple
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import Request, urlopen

from eubw_researcher.corpus import ingest_text_entry
from eubw_researcher.corpus.normalize import normalize_bytes_content, normalize_text_content
from eubw_researcher.models import (
    CitationQuality,
    DiscoveryEntrypoint,
    DocumentStatus,
    IngestionReportEntry,
    NormalizationStatus,
    RuntimeConfig,
    SourceCatalogEntry,
    SourceDocument,
    SourceKind,
    SourceOrigin,
    WebAllowlistConfig,
    WebDomainPolicy,
    WebFetchRecord,
)
from eubw_researcher.retrieval.text_normalization import normalize_text_for_matching
from eubw_researcher.web.allowlist import normalize_domain, validate_domain


TOKEN_RE = re.compile(r"[a-z0-9]+")
URL_RELEVANCE_HINTS = [
    "spec",
    "openid",
    "wallet",
    "registration",
    "certificate",
    "legal-content",
    "celex",
    "implementing",
    "regulation",
    "eudi",
]
DEFAULT_BLOCKED_URL_KEYWORDS = {
    "/news",
    "/press",
    "/events",
    "/blog",
    "/careers",
    "/media",
    "/newsletter",
    "/search",
    "/login",
    "/cookies",
    "/privacy",
}
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "only",
    "where",
    "what",
    "which",
    "how",
    "can",
    "they",
    "are",
    "into",
    "does",
    "level",
    "must",
}


class _AnchorLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[Tuple[str, str]] = []
        self._current_href: Optional[str] = None
        self._current_text: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current_href is None:
            return
        text = re.sub(r"\s+", " ", "".join(self._current_text)).strip()
        self.links.append((self._current_href, text))
        self._current_href = None
        self._current_text = []


@dataclass
class _CandidateOrigin:
    discovered_from: Optional[str] = None
    provenance_record: Optional[str] = None
    source_kind: Optional[SourceKind] = None
    policy_id: Optional[str] = None
    entrypoint_id: Optional[str] = None
    discovery_strategy: Optional[str] = None
    discovery_query: Optional[str] = None


def _representative_candidate_kind(candidate_kinds: Set[SourceKind]) -> SourceKind:
    return sorted(candidate_kinds, key=lambda kind: kind.value)[0]


def _infer_fetched_source_kind(
    url: str,
    title: str,
    normalized_text: str,
    candidate_kinds: Set[SourceKind],
) -> Optional[SourceKind]:
    if not candidate_kinds:
        return None
    if len(candidate_kinds) == 1:
        return next(iter(candidate_kinds))

    normalized = normalize_text_for_matching(f"{url} {title} {normalized_text}")
    implementing_markers = [
        "implementing act",
        "implementing regulation",
        "implementing decision",
        "commission implementing",
    ]
    regulation_markers = [
        " regulation ",
        "regulation (eu)",
        "regulation eu",
    ]
    if (
        SourceKind.IMPLEMENTING_ACT in candidate_kinds
        and any(marker in normalized for marker in implementing_markers)
    ):
        return SourceKind.IMPLEMENTING_ACT
    if (
        SourceKind.REGULATION in candidate_kinds
        and any(marker in normalized for marker in regulation_markers)
    ):
        return SourceKind.REGULATION
    return None


def _slug_from_url(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def _looks_like_html_document(raw_text: str) -> bool:
    sample = raw_text[:4000].lower()
    return any(
        token in sample
        for token in ["<html", "<body", "<div", "<p", "<table", "<h1", "<h2", "<article", "<section"]
    )


def _supports_web_normalization(
    url: str,
    content_type: str,
    raw_bytes: bytes,
) -> tuple[bool, str]:
    del raw_bytes
    lowered = content_type.lower()
    path = urlparse(url).path.lower()

    if "pdf" in lowered or path.endswith(".pdf"):
        return True, ""
    if "html" in lowered or "xhtml" in lowered or path.endswith((".html", ".htm", ".xhtml")):
        return True, ""
    if lowered.startswith("text/") or "markdown" in lowered or path.endswith((".md", ".txt", ".rst")):
        return True, ""
    if "xml" in lowered or path.endswith(".xml"):
        return True, ""
    return False, f"Unsupported fetched content type for V2 normalization: {content_type}."


def _anchorability_hints_for_web_content(content_type: str, url: str) -> List[str]:
    lowered = content_type.lower()
    path = urlparse(url).path.lower()
    if "html" in lowered or "xhtml" in lowered or "xml" in lowered or path.endswith(
        (".html", ".htm", ".xhtml", ".xml")
    ):
        return ["markdown_headings"]
    if "pdf" in lowered or path.endswith(".pdf"):
        return []
    if lowered.startswith("text/") or "markdown" in lowered or path.endswith((".md", ".txt", ".rst")):
        return ["markdown_headings"]
    return []


def _query_tokens(text: str) -> List[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS and len(token) > 2]


def _score_discovered_link(sub_question: str, candidate_url: str, anchor_text: str) -> int:
    query_tokens = set(_query_tokens(sub_question))
    candidate_tokens = set(_query_tokens(candidate_url)) | set(_query_tokens(anchor_text))
    overlap = len(query_tokens & candidate_tokens)
    bonus = 2 if any(token in candidate_url.lower() for token in ["openid", "wallet", "registration", "certificate", "authorization"]) else 0
    return overlap + bonus


def _is_plausible_for_kind(source_kind: SourceKind, candidate_url: str, anchor_text: str) -> bool:
    lowered = f"{candidate_url} {anchor_text}".lower()
    if source_kind in {SourceKind.REGULATION, SourceKind.IMPLEMENTING_ACT}:
        return any(
            token in lowered
            for token in ["celex", "regulation", "directive", "implementing", "official journal", "legal-content"]
        )
    if source_kind == SourceKind.TECHNICAL_STANDARD:
        return any(
            token in lowered
            for token in ["openid", "spec", "specification", "credential", "presentation", "wallet"]
        )
    if source_kind == SourceKind.PROJECT_ARTIFACT:
        return any(
            token in lowered
            for token in ["eudi", "wallet", "reference", "framework", "registration", "information", "ts05", "ts06"]
        )
    return True


def _request_url(url: str, timeout_seconds: int) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "eubw-researcher/0.2"})
    with urlopen(request, timeout=timeout_seconds) as response:
        raw_bytes = response.read()
        content_type = response.headers.get("Content-Type", "text/plain")
    return raw_bytes, content_type


def _normalize_fetched_content(
    raw_bytes: bytes,
    content_type: str,
    url: str,
) -> tuple[str, Optional[str], str, Optional[str]]:
    path = urlparse(url).path.lower()
    source_format = (
        "application/pdf"
        if "pdf" in content_type.lower() or path.endswith(".pdf")
        else "application/xml"
        if "xml" in content_type.lower() or path.endswith(".xml")
        else content_type
    )
    return normalize_bytes_content(raw_bytes, source_format)


def _default_title_for_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    slug = path.rsplit("/", 1)[-1] if path else parsed.hostname or "official-source"
    slug = re.sub(r"\.[a-z0-9]+$", "", slug, flags=re.IGNORECASE)
    slug = re.sub(r"[-_]+", " ", slug).strip()
    if not slug:
        slug = parsed.hostname or "official source"
    return re.sub(r"\s+", " ", slug).title()


def _infer_document_status(
    url: str,
    policy,
    title: str,
    normalized_text: str,
) -> DocumentStatus:
    if policy.source_kind in {
        SourceKind.REGULATION,
        SourceKind.IMPLEMENTING_ACT,
        SourceKind.TECHNICAL_STANDARD,
    }:
        return DocumentStatus.FINAL

    url_and_title = normalize_text_for_matching(f"{url} {title}")
    combined = normalize_text_for_matching(f"{url} {title} {normalized_text}")
    if "lobbyregister" in url_and_title or "stellungnahme" in url_and_title:
        return DocumentStatus.INFORMATIONAL

    if policy.source_kind == SourceKind.NATIONAL_IMPLEMENTATION:
        if any(marker in combined for marker in ["noch nicht in kraft", "not yet effective", "noch nicht wirksam"]):
            return DocumentStatus.ADOPTED_PENDING_EFFECTIVE_DATE
        if any(
            marker in combined
            for marker in [
                "referentenentwurf",
                "draft law",
                "draft bill",
            ]
        ):
            return DocumentStatus.DRAFT
        if any(
            marker in combined
            for marker in [
                "gesetzentwurf",
                "entwurf eines gesetzes",
                "proposal for a regulation",
                "proposal for a law",
            ]
        ):
            return DocumentStatus.PROPOSAL
        if any(marker in combined for marker in ["nicht in kraft", "not in force", "nicht wirksam"]):
            return DocumentStatus.ADOPTED_PENDING_EFFECTIVE_DATE
        if (
            "in kraft" in combined
            and "nicht in kraft" not in combined
        ) or any(marker in combined for marker in ["entered into force", "verkuendet", "verkundet"]):
            return DocumentStatus.FINAL

    return DocumentStatus.INFORMATIONAL


def _content_digest(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def _url_has_blocked_keyword(url: str, policy) -> bool:
    lowered = url.lower()
    blocked_terms = DEFAULT_BLOCKED_URL_KEYWORDS | set(policy.blocked_url_keywords)
    return any(term in lowered for term in blocked_terms)


def _policy_allows_intent(policy, intent_type: str | None) -> bool:
    return not policy.allowed_intent_types or intent_type in policy.allowed_intent_types


def _candidate_policies_for_url(
    candidate_url: str,
    policy,
    allowlist: WebAllowlistConfig,
    *,
    intent_type: str | None,
) -> List[WebDomainPolicy]:
    candidate_domain = normalize_domain(candidate_url)
    if not candidate_domain or not validate_domain(candidate_url, allowlist):
        return []
    if candidate_domain == policy.domain:
        return [
            candidate_policy
            for candidate_policy in allowlist.policies_for_domain(candidate_domain)
            if _policy_allows_intent(candidate_policy, intent_type)
        ]
    if candidate_domain in policy.allowed_cross_domain_domains:
        return [
            candidate_policy
            for candidate_policy in allowlist.policies_for_domain(candidate_domain)
            if _policy_allows_intent(candidate_policy, intent_type)
        ]
    return []


def _matches_path_prefixes(url: str, prefixes: List[str]) -> bool:
    if not prefixes:
        return False
    path = urlparse(url).path or "/"
    return any(path.startswith(prefix) for prefix in prefixes)


def _matches_crawl_path_prefixes(url: str, policy) -> bool:
    return _matches_path_prefixes(url, policy.crawl_path_prefixes)


def _matches_admission_path_prefixes(url: str, policy) -> bool:
    return _matches_path_prefixes(url, policy.admission_path_prefixes)


def _admission_rule_label(policy) -> str:
    if policy.admission_path_prefixes:
        return "admission_path_prefixes"
    return "configured_seed_url"


def _resolve_discovery_url(entrypoint: DiscoveryEntrypoint, discovery_query: str) -> str:
    if entrypoint.strategy == "official_search":
        return entrypoint.url_template.replace("{query}", quote_plus(discovery_query))
    return entrypoint.url_template


def _admissible_document_policy(
    candidate_url: str,
    policy,
    allowlist: WebAllowlistConfig,
    *,
    intent_type: str | None = None,
):
    candidate_policies = _candidate_policies_for_url(
        candidate_url,
        policy,
        allowlist,
        intent_type=intent_type,
    )
    for candidate_policy in candidate_policies:
        if _url_has_blocked_keyword(candidate_url, candidate_policy):
            continue
        if not _matches_admission_path_prefixes(candidate_url, candidate_policy):
            continue
        return candidate_policy
    return None


def _admissible_document_policies(
    candidate_url: str,
    policy,
    allowlist: WebAllowlistConfig,
    *,
    intent_type: str | None = None,
) -> List[WebDomainPolicy]:
    candidate_policies = _candidate_policies_for_url(
        candidate_url,
        policy,
        allowlist,
        intent_type=intent_type,
    )
    return [
        candidate_policy
        for candidate_policy in candidate_policies
        if not _url_has_blocked_keyword(candidate_url, candidate_policy)
        and _matches_admission_path_prefixes(candidate_url, candidate_policy)
    ]


def _followable_discovery_link(
    candidate_url: str,
    policy,
    allowlist: WebAllowlistConfig,
    *,
    intent_type: str | None = None,
) -> bool:
    candidate_policies = _candidate_policies_for_url(
        candidate_url,
        policy,
        allowlist,
        intent_type=intent_type,
    )
    return any(
        not _url_has_blocked_keyword(candidate_url, candidate_policy)
        and _matches_crawl_path_prefixes(candidate_url, candidate_policy)
        for candidate_policy in candidate_policies
    )


def _discover_candidate_urls(
    sub_question: str,
    discovery_query: str,
    entrypoint: DiscoveryEntrypoint,
    policy,
    allowlist: WebAllowlistConfig,
    runtime_config: RuntimeConfig,
    *,
    intent_type: str | None = None,
    request_cache: Dict[str, Tuple[bytes, str]] | None = None,
) -> tuple[List[str], List[WebFetchRecord]]:
    records: List[WebFetchRecord] = []
    candidate_scores: Dict[Tuple[str, SourceKind], Tuple[int, str, str, WebDomainPolicy]] = {}
    discovery_url = _resolve_discovery_url(entrypoint, discovery_query)
    crawl_queue: Deque[Tuple[str, int, Optional[str]]] = deque(
        [(discovery_url, 0, None)]
    )
    visited: Set[str] = set()
    crawled_pages = 0

    while crawl_queue and crawled_pages < runtime_config.web_discovery_max_pages:
        discovery_url, depth, parent_url = crawl_queue.popleft()
        if discovery_url in visited:
            continue
        visited.add(discovery_url)

        now = datetime.now(timezone.utc).isoformat()
        domain = normalize_domain(discovery_url)
        if not validate_domain(discovery_url, allowlist):
            records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=discovery_url,
                    domain=domain,
                    allowed=False,
                    source_kind=None,
                    source_role_level=None,
                    jurisdiction=None,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason="Discovery URL is not allowlisted.",
                    record_type="discovery",
                    discovered_from=parent_url,
                    normalization_status=NormalizationStatus.FAILED,
                    policy_id=policy.policy_id,
                    entrypoint_id=entrypoint.entrypoint_id,
                    discovery_strategy=entrypoint.strategy,
                    discovery_query=discovery_query if entrypoint.strategy == "official_search" else None,
                    provenance_record=(
                        f"discovered_from={parent_url}" if parent_url else "configured_discovery_url"
                    ),
                )
            )
            continue

        try:
            if request_cache is not None and discovery_url in request_cache:
                raw_bytes, content_type = request_cache[discovery_url]
            else:
                raw_bytes, content_type = _request_url(discovery_url, runtime_config.web_timeout_seconds)
                if request_cache is not None:
                    request_cache[discovery_url] = (raw_bytes, content_type)
        except Exception as exc:  # pragma: no cover
            records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=discovery_url,
                    domain=domain,
                    allowed=True,
                    source_kind=policy.source_kind,
                    source_role_level=policy.source_role_level,
                    jurisdiction=policy.jurisdiction,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason=f"Discovery fetch failed: {exc}",
                    record_type="discovery",
                    discovered_from=parent_url,
                    normalization_status=NormalizationStatus.FAILED,
                    policy_id=policy.policy_id,
                    entrypoint_id=entrypoint.entrypoint_id,
                    discovery_strategy=entrypoint.strategy,
                    discovery_query=discovery_query if entrypoint.strategy == "official_search" else None,
                    provenance_record=(
                        f"discovered_from={parent_url}" if parent_url else "configured_discovery_url"
                    ),
                )
            )
            continue

        supported, reason = _supports_web_normalization(discovery_url, content_type, raw_bytes)
        if not supported:
            records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=discovery_url,
                    domain=domain,
                    allowed=True,
                    source_kind=policy.source_kind,
                    source_role_level=policy.source_role_level,
                    jurisdiction=policy.jurisdiction,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason=reason,
                    record_type="discovery",
                    discovered_from=parent_url,
                    content_type=content_type,
                    normalization_status=NormalizationStatus.FAILED,
                    content_digest=_content_digest(raw_bytes),
                    policy_id=policy.policy_id,
                    entrypoint_id=entrypoint.entrypoint_id,
                    discovery_strategy=entrypoint.strategy,
                    discovery_query=discovery_query if entrypoint.strategy == "official_search" else None,
                    provenance_record=(
                        f"discovered_from={parent_url}" if parent_url else "configured_discovery_url"
                    ),
                )
            )
            continue

        raw_text = raw_bytes.decode("utf-8", errors="replace")
        try:
            normalized_text, _ = (
                normalize_text_content(raw_text, content_type)
                if (
                    "html" in content_type.lower()
                    or "xhtml" in content_type.lower()
                    or "xml" in content_type.lower()
                    or _looks_like_html_document(raw_text)
                )
                else (raw_text.strip(), None)
            )
        except Exception as exc:
            records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=discovery_url,
                    domain=domain,
                    allowed=True,
                    source_kind=policy.source_kind,
                    source_role_level=policy.source_role_level,
                    jurisdiction=policy.jurisdiction,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason=f"Discovery normalization failed: {exc}",
                    record_type="discovery",
                    discovered_from=parent_url,
                    content_type=content_type,
                    normalization_status=NormalizationStatus.FAILED,
                    content_digest=_content_digest(raw_bytes),
                    policy_id=policy.policy_id,
                    entrypoint_id=entrypoint.entrypoint_id,
                    discovery_strategy=entrypoint.strategy,
                    discovery_query=discovery_query if entrypoint.strategy == "official_search" else None,
                    provenance_record=(
                        f"discovered_from={parent_url}" if parent_url else "configured_discovery_url"
                    ),
                )
            )
            continue
        records.append(
            WebFetchRecord(
                sub_question=sub_question,
                canonical_url=discovery_url,
                domain=domain,
                allowed=True,
                source_kind=policy.source_kind,
                source_role_level=policy.source_role_level,
                jurisdiction=policy.jurisdiction,
                retrieval_timestamp=now,
                citation_quality=CitationQuality.DOCUMENT_ONLY,
                metadata_complete=bool(normalized_text.strip()),
                reason="Fetched allowlisted discovery page.",
                record_type="discovery",
                discovered_from=parent_url,
                content_type=content_type,
                normalization_status=NormalizationStatus.SUCCESS,
                content_digest=_content_digest(raw_bytes),
                policy_id=policy.policy_id,
                entrypoint_id=entrypoint.entrypoint_id,
                discovery_strategy=entrypoint.strategy,
                discovery_query=discovery_query if entrypoint.strategy == "official_search" else None,
                provenance_record=(
                    f"discovered_from={parent_url}" if parent_url else "configured_discovery_url"
                ),
            )
        )
        crawled_pages += 1
        if not _looks_like_html_document(raw_text):
            continue

        parser = _AnchorLinkParser()
        parser.feed(raw_text)
        for href, anchor_text in parser.links:
            candidate_url = urljoin(discovery_url, href)
            candidate_policies = _admissible_document_policies(
                candidate_url,
                policy,
                allowlist,
                intent_type=intent_type,
            )
            can_crawl = _followable_discovery_link(
                candidate_url,
                policy,
                allowlist,
                intent_type=intent_type,
            )
            if not candidate_policies and not can_crawl:
                continue

            score = _score_discovered_link(sub_question, candidate_url, anchor_text)
            for candidate_policy in candidate_policies:
                plausible = _is_plausible_for_kind(
                    candidate_policy.source_kind,
                    candidate_url,
                    anchor_text,
                )
                if not plausible or score < 2:
                    continue
                candidate_key = (candidate_url, candidate_policy.source_kind)
                existing = candidate_scores.get(candidate_key)
                if existing is None or score > existing[0]:
                    candidate_scores[candidate_key] = (
                        score,
                        anchor_text,
                        discovery_url,
                        candidate_policy,
                    )

            should_crawl = (
                can_crawl
                and (depth + 1) < runtime_config.web_discovery_max_depth
                and candidate_url not in visited
                and _policy_allows_intent(policy, intent_type)
                and any(token in candidate_url.lower() for token in URL_RELEVANCE_HINTS)
            )
            if should_crawl:
                crawl_queue.append((candidate_url, depth + 1, discovery_url))

    discovered = sorted(
        (
            (score, candidate_url, anchor_text, discovered_from, candidate_policy)
            for (candidate_url, _candidate_kind), (
                score,
                anchor_text,
                discovered_from,
                candidate_policy,
            ) in candidate_scores.items()
        ),
        key=lambda item: (item[0], item[1], item[4].source_kind.value),
        reverse=True,
    )

    selected_urls: List[str] = []
    for score, candidate_url, anchor_text, discovered_from, candidate_policy in discovered:
        if candidate_url not in selected_urls:
            selected_urls.append(candidate_url)
        records.append(
            WebFetchRecord(
                sub_question=sub_question,
                canonical_url=candidate_url,
                domain=normalize_domain(candidate_url),
                allowed=True,
                source_kind=(candidate_policy or policy).source_kind,
                source_role_level=(candidate_policy or policy).source_role_level,
                jurisdiction=(candidate_policy or policy).jurisdiction,
                retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
                citation_quality=None,
                metadata_complete=False,
                reason=f"Discovered allowlisted official candidate link (score {score}) from discovery crawl: {anchor_text or candidate_url}",
                record_type="discovered_link",
                discovered_from=discovered_from,
                policy_id=(candidate_policy or policy).policy_id,
                entrypoint_id=entrypoint.entrypoint_id,
                discovery_strategy=entrypoint.strategy,
                discovery_query=discovery_query if entrypoint.strategy == "official_search" else None,
                admission_rule=_admission_rule_label(candidate_policy or policy),
                provenance_record=f"discovered_from={discovered_from or 'configured_discovery_url'}",
            )
        )
        if len(selected_urls) >= runtime_config.web_discovery_max_candidates_per_kind:
            break

    return selected_urls, records


def fetch_and_normalize_official_sources(
    sub_question: str,
    source_kinds: List[SourceKind],
    discovery_query: str,
    allowlist: WebAllowlistConfig,
    runtime_config: RuntimeConfig,
    *,
    intent_type: str | None = None,
) -> Tuple[List[SourceDocument], List[IngestionReportEntry], List[WebFetchRecord]]:
    documents: List[SourceDocument] = []
    reports: List[IngestionReportEntry] = []
    fetch_records: List[WebFetchRecord] = []
    candidate_urls: Dict[str, Dict[SourceKind, _CandidateOrigin]] = {}
    discovery_request_cache: Dict[str, Tuple[bytes, str]] = {}
    admitted_per_domain: Dict[str, int] = {}
    admitted_total = 0

    for source_kind in source_kinds:
        for url in allowlist.seed_urls_for_kind(source_kind, intent_type=intent_type):
            candidate_urls.setdefault(url, {}).setdefault(
                source_kind,
                _CandidateOrigin(
                    provenance_record="configured_seed_url",
                    source_kind=source_kind,
                ),
            )

        policies = [
            policy
            for policy in allowlist.domain_policies
            if policy.source_kind == source_kind and _policy_allows_intent(policy, intent_type)
        ]
        for policy in policies:
            for entrypoint in policy.discovery_entrypoints:
                _discovered_urls, discovery_records = _discover_candidate_urls(
                    sub_question=sub_question,
                    discovery_query=discovery_query,
                    entrypoint=entrypoint,
                    policy=policy,
                    allowlist=allowlist,
                    runtime_config=runtime_config,
                    intent_type=intent_type,
                    request_cache=discovery_request_cache,
                )
                fetch_records.extend(discovery_records)
                for discovery_record in discovery_records:
                    if (
                        discovery_record.record_type != "discovered_link"
                        or discovery_record.source_kind is None
                    ):
                        continue
                    candidate_urls.setdefault(discovery_record.canonical_url, {}).setdefault(
                        discovery_record.source_kind,
                        _CandidateOrigin(
                            discovered_from=discovery_record.discovered_from,
                            provenance_record=discovery_record.provenance_record,
                            source_kind=discovery_record.source_kind,
                            policy_id=discovery_record.policy_id,
                            entrypoint_id=discovery_record.entrypoint_id,
                            discovery_strategy=discovery_record.discovery_strategy,
                            discovery_query=discovery_record.discovery_query,
                        ),
                    )

    for url, origins_by_kind in candidate_urls.items():
        candidate_kinds = set(origins_by_kind)
        representative_kind = _representative_candidate_kind(candidate_kinds)
        representative_origin = origins_by_kind[representative_kind]
        domain = normalize_domain(url)
        allowed = validate_domain(url, allowlist)
        admissible_policies: Dict[SourceKind, WebDomainPolicy] = {}
        for candidate_kind in candidate_kinds:
            policy = allowlist.policy_for_domain_and_kind(domain, candidate_kind)
            if (
                policy is not None
                and _admissible_document_policy(
                    url,
                    policy,
                    allowlist,
                    intent_type=intent_type,
                )
                is not None
            ):
                admissible_policies[candidate_kind] = policy
        now = datetime.now(timezone.utc).isoformat()

        if not allowed or not admissible_policies:
            fetch_records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=url,
                    domain=domain,
                    allowed=False,
                    source_kind=None,
                    source_role_level=None,
                    jurisdiction=None,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason="Domain is not allowlisted or lacks an admissible domain policy.",
                    record_type="fetch",
                    discovered_from=representative_origin.discovered_from,
                    normalization_status=NormalizationStatus.FAILED,
                    policy_id=representative_origin.policy_id,
                    entrypoint_id=representative_origin.entrypoint_id,
                    discovery_strategy=representative_origin.discovery_strategy,
                    discovery_query=representative_origin.discovery_query,
                    provenance_record=(
                        representative_origin.provenance_record or "configured_seed_url"
                    ),
                )
            )
            continue

        representative_policy = admissible_policies.get(representative_kind) or admissible_policies[
            _representative_candidate_kind(set(admissible_policies))
        ]
        representative_source_id = f"web::{representative_policy.source_kind.value}::{_slug_from_url(url)}"

        if admitted_total >= runtime_config.web_max_admitted_per_run:
            fetch_records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=url,
                    domain=domain,
                    allowed=True,
                    source_kind=representative_policy.source_kind,
                    source_role_level=representative_policy.source_role_level,
                    jurisdiction=representative_policy.jurisdiction,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason="Per-run admitted web-document cap reached before this candidate could be admitted.",
                    record_type="fetch",
                    discovered_from=representative_origin.discovered_from,
                    normalization_status=NormalizationStatus.FAILED,
                    policy_id=representative_policy.policy_id,
                    entrypoint_id=representative_origin.entrypoint_id,
                    discovery_strategy=representative_origin.discovery_strategy,
                    admission_rule=_admission_rule_label(representative_policy),
                    discovery_query=representative_origin.discovery_query,
                    provenance_record=(
                        representative_origin.provenance_record or "configured_seed_url"
                    ),
                    source_id=representative_source_id,
                )
            )
            continue

        if admitted_per_domain.get(domain, 0) >= runtime_config.web_max_admitted_per_domain:
            fetch_records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=url,
                    domain=domain,
                    allowed=True,
                    source_kind=representative_policy.source_kind,
                    source_role_level=representative_policy.source_role_level,
                    jurisdiction=representative_policy.jurisdiction,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason="Per-domain admitted web-document cap reached before this candidate could be admitted.",
                    record_type="fetch",
                    discovered_from=representative_origin.discovered_from,
                    normalization_status=NormalizationStatus.FAILED,
                    policy_id=representative_policy.policy_id,
                    entrypoint_id=representative_origin.entrypoint_id,
                    discovery_strategy=representative_origin.discovery_strategy,
                    admission_rule=_admission_rule_label(representative_policy),
                    discovery_query=representative_origin.discovery_query,
                    provenance_record=(
                        representative_origin.provenance_record or "configured_seed_url"
                    ),
                    source_id=representative_source_id,
                )
            )
            continue

        try:
            raw_bytes, content_type = _request_url(url, runtime_config.web_timeout_seconds)
        except Exception as exc:  # pragma: no cover
            fetch_records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=url,
                    domain=domain,
                    allowed=True,
                    source_kind=representative_policy.source_kind,
                    source_role_level=representative_policy.source_role_level,
                    jurisdiction=representative_policy.jurisdiction,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason=f"Fetch failed: {exc}",
                    record_type="fetch",
                    discovered_from=representative_origin.discovered_from,
                    normalization_status=NormalizationStatus.FAILED,
                    policy_id=representative_policy.policy_id,
                    entrypoint_id=representative_origin.entrypoint_id,
                    discovery_strategy=representative_origin.discovery_strategy,
                    admission_rule=_admission_rule_label(representative_policy),
                    discovery_query=representative_origin.discovery_query,
                    provenance_record=(
                        representative_origin.provenance_record or "configured_seed_url"
                    ),
                    source_id=representative_source_id,
                )
            )
            continue

        supported, normalization_reason = _supports_web_normalization(
            url=url,
            content_type=content_type,
            raw_bytes=raw_bytes,
        )
        if not supported:
            fetch_records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=url,
                    domain=domain,
                    allowed=True,
                    source_kind=representative_policy.source_kind,
                    source_role_level=representative_policy.source_role_level,
                    jurisdiction=representative_policy.jurisdiction,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason=normalization_reason,
                    record_type="fetch",
                    discovered_from=representative_origin.discovered_from,
                    content_type=content_type,
                    normalization_status=NormalizationStatus.FAILED,
                    content_digest=_content_digest(raw_bytes),
                    policy_id=representative_policy.policy_id,
                    entrypoint_id=representative_origin.entrypoint_id,
                    discovery_strategy=representative_origin.discovery_strategy,
                    admission_rule=_admission_rule_label(representative_policy),
                    discovery_query=representative_origin.discovery_query,
                    provenance_record=(
                        representative_origin.provenance_record or "configured_seed_url"
                    ),
                    source_id=representative_source_id,
                )
            )
            continue

        try:
            (
                normalized_text,
                title_from_content,
                normalization_format,
                normalization_note,
            ) = _normalize_fetched_content(
                raw_bytes,
                content_type,
                url,
            )
        except Exception as exc:
            fetch_records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=url,
                    domain=domain,
                    allowed=True,
                    source_kind=representative_policy.source_kind,
                    source_role_level=representative_policy.source_role_level,
                    jurisdiction=representative_policy.jurisdiction,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason=f"Normalization failed: {exc}",
                    record_type="fetch",
                    discovered_from=representative_origin.discovered_from,
                    content_type=content_type,
                    normalization_status=NormalizationStatus.FAILED,
                    content_digest=_content_digest(raw_bytes),
                    policy_id=representative_policy.policy_id,
                    entrypoint_id=representative_origin.entrypoint_id,
                    discovery_strategy=representative_origin.discovery_strategy,
                    admission_rule=_admission_rule_label(representative_policy),
                    discovery_query=representative_origin.discovery_query,
                    provenance_record=(
                        representative_origin.provenance_record or "configured_seed_url"
                    ),
                    source_id=representative_source_id,
                )
            )
            continue

        title = title_from_content or _default_title_for_url(url)
        effective_source_kind = _infer_fetched_source_kind(
            url,
            title,
            normalized_text,
            set(admissible_policies),
        )
        if effective_source_kind is None:
            fetch_records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=url,
                    domain=domain,
                    allowed=True,
                    source_kind=None,
                    source_role_level=None,
                    jurisdiction=None,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason="Fetched URL matched multiple source kinds and could not be classified to a single official source kind.",
                    record_type="fetch",
                    discovered_from=representative_origin.discovered_from,
                    content_type=content_type,
                    normalization_status=NormalizationStatus.FAILED,
                    content_digest=_content_digest(raw_bytes),
                    policy_id=representative_origin.policy_id,
                    entrypoint_id=representative_origin.entrypoint_id,
                    discovery_strategy=representative_origin.discovery_strategy,
                    discovery_query=representative_origin.discovery_query,
                    provenance_record=(
                        representative_origin.provenance_record or "configured_seed_url"
                    ),
                )
            )
            continue

        policy = admissible_policies[effective_source_kind]
        origin = origins_by_kind.get(effective_source_kind, representative_origin)
        source_id = f"web::{policy.source_kind.value}::{_slug_from_url(url)}"
        entry = SourceCatalogEntry(
            source_id=source_id,
            title=title,
            source_kind=policy.source_kind,
            source_role_level=policy.source_role_level,
            jurisdiction=policy.jurisdiction,
            publication_status="fetched",
            publication_date=None,
            local_path=None,
            canonical_url=url,
            document_status=_infer_document_status(
                url,
                policy,
                title,
                normalized_text,
            ),
            source_origin=SourceOrigin.WEB,
            anchorability_hints=_anchorability_hints_for_web_content(content_type, url),
        )
        metadata_complete = all(
            [
                entry.canonical_url,
                entry.title,
                domain,
                entry.source_role_level,
                entry.source_kind,
                entry.jurisdiction,
            ]
        ) and bool(normalized_text.strip())
        if not metadata_complete:
            fetch_records.append(
                WebFetchRecord(
                    sub_question=sub_question,
                    canonical_url=url,
                    domain=domain,
                    allowed=True,
                    source_kind=policy.source_kind,
                    source_role_level=policy.source_role_level,
                    jurisdiction=policy.jurisdiction,
                    retrieval_timestamp=now,
                    citation_quality=None,
                    metadata_complete=False,
                    reason="Normalized web source metadata was incomplete.",
                    record_type="fetch",
                    discovered_from=origin.discovered_from,
                    content_type=content_type,
                    normalization_status=NormalizationStatus.FAILED,
                    content_digest=_content_digest(raw_bytes),
                    policy_id=policy.policy_id,
                    entrypoint_id=origin.entrypoint_id,
                    discovery_strategy=origin.discovery_strategy,
                    admission_rule=_admission_rule_label(policy),
                    discovery_query=origin.discovery_query,
                    provenance_record=(
                        origin.provenance_record or "configured_seed_url"
                    ),
                    source_id=source_id,
                )
            )
            continue

        document, report = ingest_text_entry(
            entry,
            normalized_text,
            normalization_format=normalization_format,
            normalization_note=normalization_note
            or (
                "Fetched from allowlisted official discovery result."
                if origin.discovered_from
                else "Fetched from allowlisted configured source."
            ),
        )
        documents.append(document)
        reports.append(report)
        admitted_per_domain[domain] = admitted_per_domain.get(domain, 0) + 1
        admitted_total += 1
        fetch_records.append(
            WebFetchRecord(
                sub_question=sub_question,
                canonical_url=url,
                domain=domain,
                allowed=True,
                source_kind=policy.source_kind,
                source_role_level=policy.source_role_level,
                jurisdiction=policy.jurisdiction,
                retrieval_timestamp=now,
                citation_quality=document.chunks[0].citation_quality,
                metadata_complete=True,
                reason=(
                    "Fetched and normalized official source discovered from allowlisted index."
                    if origin.discovered_from
                    else "Fetched and normalized official source for gap-driven expansion."
                ),
                record_type="fetch",
                discovered_from=origin.discovered_from,
                content_type=content_type,
                normalization_status=NormalizationStatus.SUCCESS,
                content_digest=_content_digest(raw_bytes),
                policy_id=policy.policy_id,
                entrypoint_id=origin.entrypoint_id,
                discovery_strategy=origin.discovery_strategy,
                admission_rule=_admission_rule_label(policy),
                discovery_query=origin.discovery_query,
                provenance_record=(
                    origin.provenance_record or "configured_seed_url"
                ),
                source_id=source_id,
            )
        )

    return documents, reports, fetch_records
