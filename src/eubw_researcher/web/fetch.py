from __future__ import annotations

import hashlib
import re
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Deque, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from eubw_researcher.corpus import ingest_text_entry
from eubw_researcher.corpus.normalize import normalize_bytes_content, normalize_text_content
from eubw_researcher.models import (
    CitationQuality,
    DocumentStatus,
    IngestionReportEntry,
    NormalizationStatus,
    RuntimeConfig,
    SourceCatalogEntry,
    SourceDocument,
    SourceKind,
    SourceOrigin,
    WebAllowlistConfig,
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

    combined = normalize_text_for_matching(f"{url} {title} {normalized_text}")
    if "lobbyregister" in combined or "stellungnahme" in combined:
        return DocumentStatus.INFORMATIONAL

    if policy.source_kind == SourceKind.NATIONAL_IMPLEMENTATION:
        if any(marker in combined for marker in ["noch nicht in kraft", "not yet effective", "noch nicht wirksam"]):
            return DocumentStatus.ADOPTED_PENDING_EFFECTIVE_DATE
        if any(
            marker in combined
            for marker in [
                "referentenentwurf",
                " refe ",
                "refe ",
                "refe)",
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
        if any(marker in combined for marker in ["in kraft", "entered into force", "verkuendet", "verkundet"]):
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


def _policy_for_candidate_url(
    candidate_url: str,
    policy,
    allowlist: WebAllowlistConfig,
    *,
    intent_type: str | None,
):
    candidate_domain = normalize_domain(candidate_url)
    if not candidate_domain or not validate_domain(candidate_url, allowlist):
        return None
    if candidate_domain == policy.domain:
        candidate_policy = allowlist.policy_for_domain(candidate_domain) or policy
        return candidate_policy if _policy_allows_intent(candidate_policy, intent_type) else None
    if candidate_domain in policy.allowed_cross_domain_domains:
        candidate_policy = allowlist.policy_for_domain(candidate_domain)
        if candidate_policy is None:
            return None
        return candidate_policy if _policy_allows_intent(candidate_policy, intent_type) else None
    return None


def _matches_allowed_path_prefixes(url: str, policy) -> bool:
    if not policy.allowed_path_prefixes:
        return False
    path = urlparse(url).path or "/"
    return any(path.startswith(prefix) for prefix in policy.allowed_path_prefixes)


def _admissible_document_policy(
    candidate_url: str,
    policy,
    allowlist: WebAllowlistConfig,
    *,
    intent_type: str | None = None,
):
    candidate_policy = _policy_for_candidate_url(
        candidate_url,
        policy,
        allowlist,
        intent_type=intent_type,
    )
    if candidate_policy is None:
        return None
    if _url_has_blocked_keyword(candidate_url, candidate_policy):
        return None
    if not _matches_allowed_path_prefixes(candidate_url, candidate_policy):
        return None
    return candidate_policy


def _followable_discovery_link(
    candidate_url: str,
    policy,
    allowlist: WebAllowlistConfig,
    *,
    intent_type: str | None = None,
) -> bool:
    candidate_policy = _policy_for_candidate_url(
        candidate_url,
        policy,
        allowlist,
        intent_type=intent_type,
    )
    if candidate_policy is None:
        return False
    return not _url_has_blocked_keyword(candidate_url, candidate_policy)


def _discover_candidate_urls(
    sub_question: str,
    discovery_urls: List[str],
    policy,
    allowlist: WebAllowlistConfig,
    runtime_config: RuntimeConfig,
    *,
    intent_type: str | None = None,
) -> tuple[List[str], List[WebFetchRecord]]:
    records: List[WebFetchRecord] = []
    candidate_scores: Dict[str, Tuple[int, str, str]] = {}
    crawl_queue: Deque[Tuple[str, int, Optional[str]]] = deque(
        (url, 0, None) for url in discovery_urls
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
                    provenance_record=(
                        f"discovered_from={parent_url}" if parent_url else "configured_discovery_url"
                    ),
                )
            )
            continue

        try:
            raw_bytes, content_type = _request_url(discovery_url, runtime_config.web_timeout_seconds)
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
            if not _followable_discovery_link(
                candidate_url,
                policy,
                allowlist,
                intent_type=intent_type,
            ):
                continue

            score = _score_discovered_link(sub_question, candidate_url, anchor_text)
            candidate_policy = _admissible_document_policy(
                candidate_url,
                policy,
                allowlist,
                intent_type=intent_type,
            )
            plausible = _is_plausible_for_kind(
                (candidate_policy or policy).source_kind,
                candidate_url,
                anchor_text,
            )
            if candidate_policy is not None and plausible and score >= 2:
                existing = candidate_scores.get(candidate_url)
                if existing is None or score > existing[0]:
                    candidate_scores[candidate_url] = (score, anchor_text, discovery_url)

            should_crawl = (
                (depth + 1) < runtime_config.web_discovery_max_depth
                and candidate_url not in visited
                and _policy_allows_intent(policy, intent_type)
                and any(token in candidate_url.lower() for token in URL_RELEVANCE_HINTS)
            )
            if should_crawl:
                crawl_queue.append((candidate_url, depth + 1, discovery_url))

    discovered = sorted(
        (
            (score, candidate_url, anchor_text, discovered_from)
            for candidate_url, (score, anchor_text, discovered_from) in candidate_scores.items()
        ),
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )

    selected_urls: List[str] = []
    for score, candidate_url, anchor_text, discovered_from in discovered:
        if candidate_url in selected_urls:
            continue
        selected_urls.append(candidate_url)
        records.append(
            WebFetchRecord(
                sub_question=sub_question,
                canonical_url=candidate_url,
                domain=normalize_domain(candidate_url),
                allowed=True,
                source_kind=policy.source_kind,
                source_role_level=policy.source_role_level,
                jurisdiction=policy.jurisdiction,
                retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
                citation_quality=None,
                metadata_complete=False,
                reason=f"Discovered allowlisted official candidate link (score {score}) from discovery crawl: {anchor_text or candidate_url}",
                record_type="discovered_link",
                discovered_from=discovered_from,
                provenance_record=f"discovered_from={discovered_from or 'configured_discovery_url'}",
            )
        )
        if len(selected_urls) >= runtime_config.web_discovery_max_candidates_per_kind:
            break

    return selected_urls, records


def fetch_and_normalize_official_sources(
    sub_question: str,
    source_kinds: List[SourceKind],
    allowlist: WebAllowlistConfig,
    runtime_config: RuntimeConfig,
    *,
    intent_type: str | None = None,
) -> Tuple[List[SourceDocument], List[IngestionReportEntry], List[WebFetchRecord]]:
    documents: List[SourceDocument] = []
    reports: List[IngestionReportEntry] = []
    fetch_records: List[WebFetchRecord] = []
    seen_urls = set()
    admitted_per_domain: Dict[str, int] = {}
    admitted_total = 0

    for source_kind in source_kinds:
        candidate_urls: Dict[str, Optional[str]] = {}
        for url in allowlist.seed_urls_for_kind(source_kind, intent_type=intent_type):
            candidate_urls[url] = None

        policies = [
            policy
            for policy in allowlist.domain_policies
            if policy.source_kind == source_kind and _policy_allows_intent(policy, intent_type)
        ]
        for policy in policies:
            discovered_urls, discovery_records = _discover_candidate_urls(
                sub_question=sub_question,
                discovery_urls=policy.discovery_urls,
                policy=policy,
                allowlist=allowlist,
                runtime_config=runtime_config,
                intent_type=intent_type,
            )
            fetch_records.extend(discovery_records)
            for discovered_url in discovered_urls:
                discovered_from = next(
                    (
                        record.discovered_from
                        for record in reversed(discovery_records)
                        if record.canonical_url == discovered_url
                        and record.record_type == "discovered_link"
                    ),
                    None,
                )
                candidate_urls.setdefault(discovered_url, discovered_from)

        for url, discovered_from in candidate_urls.items():
            if url in seen_urls:
                continue
            seen_urls.add(url)
            domain = normalize_domain(url)
            allowed = validate_domain(url, allowlist)
            policy = allowlist.policy_for_domain(domain)
            now = datetime.now(timezone.utc).isoformat()

            if not allowed or policy is None or policy.source_kind not in source_kinds:
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
                        reason="Domain is not allowlisted or lacks a domain policy.",
                        record_type="fetch",
                        discovered_from=discovered_from,
                        normalization_status=NormalizationStatus.FAILED,
                        provenance_record=(
                            f"discovered_from={discovered_from}" if discovered_from else "configured_seed_url"
                        ),
                    )
                )
                continue

            if _admissible_document_policy(
                url,
                policy,
                allowlist,
                intent_type=intent_type,
            ) is None:
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
                        reason="Fetched URL failed the document-admission policy for this official domain.",
                        record_type="fetch",
                        discovered_from=discovered_from,
                        normalization_status=NormalizationStatus.FAILED,
                        provenance_record=(
                            f"discovered_from={discovered_from}" if discovered_from else "configured_seed_url"
                        ),
                    )
                )
                continue

            if admitted_total >= runtime_config.web_max_admitted_per_run:
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
                        reason="Per-run admitted web-document cap reached before this candidate could be admitted.",
                        record_type="fetch",
                        discovered_from=discovered_from,
                        normalization_status=NormalizationStatus.FAILED,
                        provenance_record=(
                            f"discovered_from={discovered_from}" if discovered_from else "configured_seed_url"
                        ),
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
                        source_kind=policy.source_kind,
                        source_role_level=policy.source_role_level,
                        jurisdiction=policy.jurisdiction,
                        retrieval_timestamp=now,
                        citation_quality=None,
                        metadata_complete=False,
                        reason="Per-domain admitted web-document cap reached before this candidate could be admitted.",
                        record_type="fetch",
                        discovered_from=discovered_from,
                        normalization_status=NormalizationStatus.FAILED,
                        provenance_record=(
                            f"discovered_from={discovered_from}" if discovered_from else "configured_seed_url"
                        ),
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
                        source_kind=policy.source_kind,
                        source_role_level=policy.source_role_level,
                        jurisdiction=policy.jurisdiction,
                        retrieval_timestamp=now,
                        citation_quality=None,
                        metadata_complete=False,
                        reason=f"Fetch failed: {exc}",
                        record_type="fetch",
                        discovered_from=discovered_from,
                        normalization_status=NormalizationStatus.FAILED,
                        provenance_record=(
                            f"discovered_from={discovered_from}" if discovered_from else "configured_seed_url"
                        ),
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
                        source_kind=policy.source_kind,
                        source_role_level=policy.source_role_level,
                        jurisdiction=policy.jurisdiction,
                        retrieval_timestamp=now,
                        citation_quality=None,
                        metadata_complete=False,
                        reason=normalization_reason,
                        record_type="fetch",
                        discovered_from=discovered_from,
                        content_type=content_type,
                        normalization_status=NormalizationStatus.FAILED,
                        content_digest=_content_digest(raw_bytes),
                        provenance_record=(
                            f"discovered_from={discovered_from}" if discovered_from else "configured_seed_url"
                        ),
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
                        source_kind=policy.source_kind,
                        source_role_level=policy.source_role_level,
                        jurisdiction=policy.jurisdiction,
                        retrieval_timestamp=now,
                        citation_quality=None,
                        metadata_complete=False,
                        reason=f"Normalization failed: {exc}",
                        record_type="fetch",
                        discovered_from=discovered_from,
                        content_type=content_type,
                        normalization_status=NormalizationStatus.FAILED,
                        content_digest=_content_digest(raw_bytes),
                        provenance_record=(
                            f"discovered_from={discovered_from}" if discovered_from else "configured_seed_url"
                        ),
                    )
                )
                continue

            title = title_from_content or _default_title_for_url(url)
            entry = SourceCatalogEntry(
                source_id=f"web::{policy.source_kind.value}::{_slug_from_url(url)}",
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
                        discovered_from=discovered_from,
                        content_type=content_type,
                        normalization_status=NormalizationStatus.FAILED,
                        content_digest=_content_digest(raw_bytes),
                        provenance_record=(
                            f"discovered_from={discovered_from}" if discovered_from else "configured_seed_url"
                        ),
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
                    if discovered_from
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
                        if discovered_from
                        else "Fetched and normalized official source for gap-driven expansion."
                    ),
                    record_type="fetch",
                    discovered_from=discovered_from,
                    content_type=content_type,
                    normalization_status=NormalizationStatus.SUCCESS,
                    content_digest=_content_digest(raw_bytes),
                    provenance_record=(
                        f"discovered_from={discovered_from}" if discovered_from else "configured_seed_url"
                    ),
                )
            )

    return documents, reports, fetch_records
