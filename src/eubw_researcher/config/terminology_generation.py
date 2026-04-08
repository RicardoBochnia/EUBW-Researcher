from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from eubw_researcher.corpus import load_source_catalog
from eubw_researcher.corpus.normalize import normalize_local_source

POLICY_VERSION = "corpus_terminology.v1"
DEFAULT_ARCHIVE_MIN_SOURCES = 2
DEFAULT_CURATED_MIN_SOURCES = 1
MAX_SAMPLE_SOURCE_IDS = 5
ANALYZED_SUFFIXES = {".xhtml", ".html", ".htm", ".xml", ".md", ".txt", ".pdf"}
BUSINESS_WALLET_CONTEXT_ALIASES = (
    "business wallet",
    "eu business wallet",
    "eubw",
    "wallet-relying party",
    "wallet relying party",
    "wallet-relying-party",
)
RELYING_PARTY_CONTEXT_ALIASES = (
    *BUSINESS_WALLET_CONTEXT_ALIASES,
    "wallet-relying parties",
    "wallet relying parties",
    "wallet-relying-parties",
    "wallet relying-parties",
    "relying party",
    "relying parties",
)


@dataclass(frozen=True)
class _AliasSpec:
    term: str
    activation: str = "analyze"
    context_aliases: tuple[str, ...] = ()
    min_archive_sources: int = DEFAULT_ARCHIVE_MIN_SOURCES
    min_curated_sources: int = DEFAULT_CURATED_MIN_SOURCES
    require_family_phrase_evidence: bool = False


@dataclass(frozen=True)
class _FamilySpec:
    canonical_term: str
    aliases: tuple[_AliasSpec, ...]
    short_alias_context_aliases: tuple[str, ...] = ()
    mapping_context_aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class _TermEvidence:
    archive_source_ids: tuple[str, ...]
    curated_source_ids: tuple[str, ...]

    @property
    def archive_source_count(self) -> int:
        return len(self.archive_source_ids)

    @property
    def curated_source_count(self) -> int:
        return len(self.curated_source_ids)


FAMILY_SPECS: tuple[_FamilySpec, ...] = (
    _FamilySpec(
        canonical_term="business wallet",
        aliases=(
            _AliasSpec("eu business wallet", activation="force"),
            _AliasSpec("eubw", activation="force"),
            _AliasSpec("European Business Wallet"),
            _AliasSpec("EBW", require_family_phrase_evidence=True),
        ),
    ),
    _FamilySpec(
        canonical_term="wallet-relying party",
        aliases=(
            _AliasSpec("wallet relying party", activation="force"),
            _AliasSpec("wallet relying-party", activation="force"),
            _AliasSpec("wallet-relying-party", activation="force"),
            _AliasSpec("wallet relying parties", activation="force"),
            _AliasSpec("wallet relying-parties", activation="force"),
            _AliasSpec("wallet-relying parties", activation="force"),
            _AliasSpec("wallet-relying-parties", activation="force"),
        ),
    ),
    _FamilySpec(
        canonical_term="provider of person identification data",
        aliases=(
            _AliasSpec("PID provider", require_family_phrase_evidence=True),
            _AliasSpec("provider of PID", activation="force"),
        ),
    ),
    _FamilySpec(
        canonical_term="person identification data",
        aliases=(
            _AliasSpec(
                "PID",
                require_family_phrase_evidence=True,
            ),
        ),
        short_alias_context_aliases=(
            "wallet",
            "provider",
            "issuer",
            "credential",
            "attestation",
            "eudi",
        ),
    ),
    _FamilySpec(
        canonical_term="qualified electronic attestation of attributes",
        aliases=(
            _AliasSpec(
                "QEAA",
                require_family_phrase_evidence=True,
            ),
        ),
        short_alias_context_aliases=(
            "wallet",
            "provider",
            "credential",
            "attestation",
            "attributes",
            "eudi",
        ),
    ),
    _FamilySpec(
        canonical_term="authorization server",
        aliases=(
            _AliasSpec("authorisation server", activation="force"),
        ),
    ),
    _FamilySpec(
        canonical_term="registration certificate",
        aliases=(
            _AliasSpec("registration cert", activation="force"),
            _AliasSpec("wallet relying party registration certificate", activation="force"),
            _AliasSpec("wallet-relying party registration certificate"),
            _AliasSpec(
                "WRPRC",
                require_family_phrase_evidence=True,
            ),
        ),
        short_alias_context_aliases=RELYING_PARTY_CONTEXT_ALIASES,
    ),
    _FamilySpec(
        canonical_term="access certificate",
        aliases=(
            _AliasSpec("access cert", activation="force"),
            _AliasSpec("wallet relying party access certificate", activation="force"),
            _AliasSpec("wallet-relying party access certificate"),
            _AliasSpec(
                "WRPAC",
                require_family_phrase_evidence=True,
            ),
            _AliasSpec(
                "RPAC",
                require_family_phrase_evidence=True,
            ),
        ),
        short_alias_context_aliases=RELYING_PARTY_CONTEXT_ALIASES,
        mapping_context_aliases=BUSINESS_WALLET_CONTEXT_ALIASES,
    ),
)


def _alias_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)


def _normalize_archive_row_path(archive_root: Path, raw_path: str) -> Path:
    normalized = raw_path.replace("\\", "/")
    path = Path(normalized)
    if path.is_absolute():
        return path.resolve()

    candidates: list[Path] = []
    parts = list(path.parts)
    if parts and parts[0] == "sources":
        candidates.append((archive_root / Path(*parts[1:])).resolve())
    candidates.append((archive_root / path).resolve())

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _should_analyze_archive_path(raw_path: str) -> bool:
    normalized = raw_path.replace("\\", "/").lower()
    path = Path(normalized)
    if path.suffix.lower() not in ANALYZED_SUFFIXES:
        return False
    if "celex_rdf" in normalized:
        return False
    return True


def _load_archive_sources(
    archive_catalog_path: Path,
) -> tuple[list[tuple[str, Path]], list[dict[str, str]]]:
    rows = json.loads(archive_catalog_path.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        raise ValueError(
            "Archive catalog "
            f"{archive_catalog_path} must contain a JSON list of row objects; "
            f"got {type(rows).__name__}"
        )
    archive_root = archive_catalog_path.parent
    sources: list[tuple[str, Path]] = []
    skipped: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            skipped.append(
                {
                    "source_id": "",
                    "path": "",
                    "reason": (
                        "invalid archive catalog row at index "
                        f"{index}: expected object, got {type(row).__name__}"
                    ),
                }
            )
            continue
        source_id = row.get("source_id")
        raw_path = row.get("local_path")
        if not source_id or not raw_path:
            skipped.append(
                {
                    "source_id": "" if source_id is None else str(source_id),
                    "path": "" if raw_path is None else str(raw_path),
                    "reason": "missing source_id or local_path in archive catalog row",
                }
            )
            continue
        if not _should_analyze_archive_path(str(raw_path)):
            skipped.append(
                {
                    "source_id": str(source_id),
                    "path": str(raw_path),
                    "reason": "unsupported or redundant archive source for terminology analysis",
                }
            )
            continue
        sources.append((str(source_id), _normalize_archive_row_path(archive_root, str(raw_path))))
    return sources, skipped


def _load_curated_sources(curated_catalog_path: Optional[Path]) -> list[tuple[str, Path]]:
    if curated_catalog_path is None or not curated_catalog_path.exists():
        return []
    catalog = load_source_catalog(curated_catalog_path)
    sources: list[tuple[str, Path]] = []
    for entry in catalog.entries:
        if entry.local_path is None:
            continue
        sources.append((entry.source_id, entry.local_path.resolve()))
    return sources


def _collect_normalized_texts(
    sources: list[tuple[str, Path]],
) -> tuple[list[tuple[str, str]], list[dict[str, str]]]:
    cache: dict[Path, str] = {}
    normalized_sources: list[tuple[str, str]] = []
    failures: list[dict[str, str]] = []
    for source_id, path in sources:
        if not path.exists():
            failures.append(
                {
                    "source_id": source_id,
                    "path": str(path),
                    "reason": "missing file",
                }
            )
            continue
        if path not in cache:
            try:
                cache[path] = normalize_local_source(path)[0]
            except Exception as exc:
                failures.append(
                    {
                        "source_id": source_id,
                        "path": str(path),
                        "reason": str(exc),
                    }
                )
                continue
        normalized_sources.append((source_id, cache[path]))
    return normalized_sources, failures


def _collect_term_evidence(
    terms: set[str],
    archive_sources: list[tuple[str, str]],
    curated_sources: list[tuple[str, str]],
) -> dict[str, _TermEvidence]:
    patterns = {term: _alias_pattern(term) for term in terms}
    evidence: dict[str, _TermEvidence] = {}
    for term, pattern in patterns.items():
        archive_hits = tuple(
            source_id for source_id, text in archive_sources if pattern.search(text)
        )
        curated_hits = tuple(
            source_id for source_id, text in curated_sources if pattern.search(text)
        )
        evidence[term] = _TermEvidence(
            archive_source_ids=archive_hits,
            curated_source_ids=curated_hits,
        )
    return evidence


def _term_is_short_acronym(term: str) -> bool:
    letters_only = re.sub(r"[^A-Za-z]", "", term)
    return bool(letters_only) and letters_only == letters_only.upper() and len(letters_only) <= 5


def _family_phrase_evidence_count(
    family: _FamilySpec,
    evidence_by_term: dict[str, _TermEvidence],
) -> int:
    phrase_terms = [family.canonical_term]
    phrase_terms.extend(
        alias.term for alias in family.aliases if not _term_is_short_acronym(alias.term)
    )
    return sum(
        evidence_by_term.get(term, _TermEvidence((), ())).archive_source_count
        + evidence_by_term.get(term, _TermEvidence((), ())).curated_source_count
        for term in phrase_terms
    )


def _dedupe_strings(values: tuple[str, ...]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return tuple(ordered)


def _effective_alias_contexts(family: _FamilySpec, alias: _AliasSpec) -> tuple[str, ...]:
    if alias.context_aliases:
        return _dedupe_strings(alias.context_aliases)
    if _term_is_short_acronym(alias.term) and family.short_alias_context_aliases:
        return _dedupe_strings(family.short_alias_context_aliases)
    return ()


def _should_activate_alias(
    family: _FamilySpec,
    alias: _AliasSpec,
    evidence_by_term: dict[str, _TermEvidence],
) -> tuple[bool, str]:
    if alias.activation == "force":
        return True, "forced by generator policy"

    alias_evidence = evidence_by_term[alias.term]
    meets_threshold = (
        alias_evidence.archive_source_count >= alias.min_archive_sources
        or alias_evidence.curated_source_count >= alias.min_curated_sources
    )
    if not meets_threshold:
        return False, "insufficient corpus evidence"

    if alias.require_family_phrase_evidence and _family_phrase_evidence_count(family, evidence_by_term) == 0:
        return False, "missing family phrase evidence"

    return True, "activated from corpus evidence"


def _alias_payload(term: str, context_aliases: tuple[str, ...]) -> str | dict[str, Any]:
    if not context_aliases:
        return term
    return {
        "term": term,
        "context_aliases": list(context_aliases),
    }


def _family_payload(
    family: _FamilySpec,
    evidence_by_term: dict[str, _TermEvidence],
) -> tuple[Optional[dict[str, Any]], dict[str, Any]]:
    aliases_payload: list[str | dict[str, Any]] = []
    candidate_payload: list[dict[str, Any]] = []
    for alias in family.aliases:
        activated, reason = _should_activate_alias(family, alias, evidence_by_term)
        alias_evidence = evidence_by_term[alias.term]
        context_aliases = _effective_alias_contexts(family, alias) if activated else ()
        if activated:
            aliases_payload.append(_alias_payload(alias.term, context_aliases))
        candidate_payload.append(
            {
                "term": alias.term,
                "archive_source_count": alias_evidence.archive_source_count,
                "curated_source_count": alias_evidence.curated_source_count,
                "sample_archive_source_ids": list(alias_evidence.archive_source_ids[:MAX_SAMPLE_SOURCE_IDS]),
                "sample_curated_source_ids": list(alias_evidence.curated_source_ids[:MAX_SAMPLE_SOURCE_IDS]),
                "activated": activated,
                "context_aliases": list(context_aliases),
                "reason": reason,
            }
        )

    mapping_payload: Optional[dict[str, Any]] = None
    if aliases_payload:
        mapping_payload = {
            "canonical_term": family.canonical_term,
            "aliases": aliases_payload,
        }
        if family.mapping_context_aliases:
            mapping_payload["context_aliases"] = list(family.mapping_context_aliases)

    family_evidence = evidence_by_term.get(family.canonical_term, _TermEvidence((), ()))
    report_payload = {
        "canonical_term": family.canonical_term,
        "canonical_archive_source_count": family_evidence.archive_source_count,
        "canonical_curated_source_count": family_evidence.curated_source_count,
        "included_in_config": bool(aliases_payload),
        "candidate_aliases": candidate_payload,
    }
    return mapping_payload, report_payload


def build_generated_terminology(
    archive_catalog_path: Path,
    *,
    curated_catalog_path: Optional[Path] = None,
    archive_catalog_display_path: Optional[str] = None,
    curated_catalog_display_path: Optional[str] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    archive_source_defs, archive_skipped = _load_archive_sources(archive_catalog_path)
    archive_sources, archive_failures = _collect_normalized_texts(archive_source_defs)
    curated_sources, curated_failures = _collect_normalized_texts(
        _load_curated_sources(curated_catalog_path)
    )

    tracked_terms = {
        family.canonical_term
        for family in FAMILY_SPECS
    }
    tracked_terms.update(alias.term for family in FAMILY_SPECS for alias in family.aliases)

    evidence_by_term = _collect_term_evidence(
        tracked_terms,
        archive_sources,
        curated_sources,
    )

    mappings_payload: list[dict[str, Any]] = []
    report_families: list[dict[str, Any]] = []
    for family in FAMILY_SPECS:
        mapping_payload, family_report = _family_payload(family, evidence_by_term)
        if mapping_payload is not None:
            mappings_payload.append(mapping_payload)
        report_families.append(family_report)

    config_payload: dict[str, Any] = {
        "generator_owned": True,
        "policy_version": POLICY_VERSION,
        "archive_catalog_path": archive_catalog_display_path or str(archive_catalog_path),
        "curated_catalog_path": (
            curated_catalog_display_path if curated_catalog_path is not None else None
        ),
        "mappings": mappings_payload,
    }
    report_payload: dict[str, Any] = {
        "policy_version": POLICY_VERSION,
        "archive_catalog_path": archive_catalog_display_path or str(archive_catalog_path),
        "curated_catalog_path": (
            curated_catalog_display_path if curated_catalog_path is not None else None
        ),
        "archive_source_count": len(archive_sources),
        "curated_source_count": len(curated_sources),
        "archive_skipped": archive_skipped,
        "archive_failures": archive_failures,
        "curated_failures": curated_failures,
        "families": report_families,
    }
    return config_payload, report_payload


def render_generated_terminology(config_payload: dict[str, Any]) -> str:
    return json.dumps(config_payload, indent=2) + "\n"
