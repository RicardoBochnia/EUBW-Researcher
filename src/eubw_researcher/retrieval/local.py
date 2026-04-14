from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from eubw_researcher.models import (
    IngestionBundle,
    RetrievalCandidate,
    RetrievalPlanStep,
    RuntimeConfig,
    SourceChunk,
    SourceHierarchyConfig,
)
from eubw_researcher.retrieval.text_normalization import (
    normalize_text_for_matching,
    tokenize_normalized_text,
)

_INDEX_SCHEMA_VERSION = "local_lexical_index.v1"
_PERSISTED_INDEXES: Dict[str, "_SQLiteFtsIndex"] = {}
_MEMORY_INDEXES: Dict[int, "_SQLiteFtsIndex"] = {}
_CHUNK_LOOKUPS: Dict[int, Dict[str, SourceChunk]] = {}


@dataclass
class LocalRetrievalTrace:
    cache_status: Optional[str] = None
    fallback_used: bool = False


@dataclass
class _SQLiteFtsIndex:
    connection: sqlite3.Connection
    cache_status: str

    def query_step(
        self,
        *,
        query_tokens: List[str],
        step: RetrievalPlanStep,
        limit: int,
    ) -> List[str]:
        if not query_tokens:
            return []
        fts_query = " OR ".join(
            _quote_fts_token(token) for token in sorted(set(query_tokens))
        )
        cursor = self.connection.execute(
            """
            SELECT chunk_id
            FROM chunks
            WHERE source_kind = ?
              AND source_role = ?
              AND normalized_text MATCH ?
            ORDER BY bm25(chunks), chunk_id
            LIMIT ?
            """,
            (
                step.required_kind.value,
                step.required_source_role_level.value,
                fts_query,
                limit,
            ),
        )
        return [str(row[0]) for row in cursor.fetchall()]


def _tokenize(text: str) -> List[str]:
    return tokenize_normalized_text(text)


def _expand_tokens(tokens: Iterable[str], expansions: Dict[str, List[str]]) -> List[str]:
    expanded = set(tokens)
    for token in list(expanded):
        for mapped in expansions.get(token, []):
            expanded.add(mapped)
    return sorted(expanded)


def _reverse_expansion_tokens(
    tokens: Iterable[str],
    expansions: Dict[str, List[str]],
) -> List[str]:
    token_set = set(tokens)
    return sorted(
        source_token
        for source_token, mapped_tokens in expansions.items()
        if token_set.intersection(mapped_tokens)
    )


def _fts_match_tokens(
    query_tokens: Iterable[str],
    expansions: Dict[str, List[str]],
) -> List[str]:
    semantic_query_tokens = set(_expand_tokens(query_tokens, expansions))
    semantic_query_tokens.update(
        _reverse_expansion_tokens(semantic_query_tokens, expansions)
    )
    return sorted(semantic_query_tokens)


def _quote_fts_token(token: str) -> str:
    return f'"{token.replace(chr(34), chr(34) * 2)}"'


def _lexical_score(query_tokens: List[str], chunk_tokens: List[str]) -> float:
    if not query_tokens:
        return 0.0
    counts = Counter(chunk_tokens)
    unique_query = set(query_tokens)
    hits = sum(1 for token in unique_query if counts[token] > 0)
    return hits / max(len(unique_query), 1)


def _semantic_score(
    query_tokens: List[str],
    chunk_tokens: List[str],
    expansions: Dict[str, List[str]],
) -> float:
    query_set = set(_expand_tokens(query_tokens, expansions))
    chunk_set = set(_expand_tokens(chunk_tokens, expansions))
    if not query_set:
        return 0.0
    return len(query_set & chunk_set) / len(query_set)


def _score_chunk(
    *,
    chunk: SourceChunk,
    query_tokens: List[str],
    hierarchy: SourceHierarchyConfig,
    runtime_config: RuntimeConfig,
) -> RetrievalCandidate:
    chunk_tokens = _tokenize(chunk.text)
    lexical = _lexical_score(query_tokens, chunk_tokens)
    semantic = _semantic_score(
        query_tokens,
        chunk_tokens,
        runtime_config.semantic_expansions,
    )
    rank = hierarchy.rank_for(chunk.source_kind)
    role_bonus = max(0.0, 0.15 - (0.01 * rank))
    combined = (
        lexical * runtime_config.lexical_weight
        + semantic * runtime_config.semantic_weight
        + role_bonus
    )
    return RetrievalCandidate(
        chunk=chunk,
        lexical_score=round(lexical, 4),
        semantic_score=round(semantic, 4),
        combined_score=round(combined, 4),
        meets_threshold=combined >= runtime_config.min_combined_score,
    )


def _sort_candidates(candidates: List[RetrievalCandidate]) -> List[RetrievalCandidate]:
    candidates.sort(
        key=lambda item: (
            item.combined_score,
            item.lexical_score,
            item.semantic_score,
        ),
        reverse=True,
    )
    return candidates


def _finalize_candidates(
    candidates: List[RetrievalCandidate],
    *,
    inspection_depth: int,
) -> List[RetrievalCandidate]:
    ranked = _sort_candidates(list(candidates))
    thresholded = [candidate for candidate in ranked if candidate.meets_threshold]
    if thresholded:
        return thresholded[:inspection_depth]
    return ranked[:inspection_depth]


def _merge_candidates(
    candidates: List[RetrievalCandidate],
    backfill_candidates: List[RetrievalCandidate],
) -> List[RetrievalCandidate]:
    by_chunk_id: Dict[str, RetrievalCandidate] = {}
    for candidate in candidates + backfill_candidates:
        chunk_id = candidate.chunk.chunk_id
        existing = by_chunk_id.get(chunk_id)
        if existing is None or candidate.combined_score > existing.combined_score:
            by_chunk_id[chunk_id] = candidate
    return list(by_chunk_id.values())


def _chunk_lookup(bundle: IngestionBundle) -> Dict[str, SourceChunk]:
    cache_key = id(bundle)
    cached = _CHUNK_LOOKUPS.get(cache_key)
    if cached is None:
        cached = {
            chunk.chunk_id: chunk
            for document in bundle.documents
            for chunk in document.chunks
        }
        _CHUNK_LOOKUPS[cache_key] = cached
    return cached


def _scan_candidates(
    *,
    query_tokens: List[str],
    step: RetrievalPlanStep,
    bundle: IngestionBundle,
    hierarchy: SourceHierarchyConfig,
    runtime_config: RuntimeConfig,
) -> List[RetrievalCandidate]:
    candidates: List[RetrievalCandidate] = []
    for document in bundle.documents:
        if document.entry.source_kind != step.required_kind:
            continue
        if document.entry.source_role_level != step.required_source_role_level:
            continue
        for chunk in document.chunks:
            candidates.append(
                _score_chunk(
                    chunk=chunk,
                    query_tokens=query_tokens,
                    hierarchy=hierarchy,
                    runtime_config=runtime_config,
                )
            )
    return _sort_candidates(candidates)


def _is_real_corpus_catalog(catalog_path: Optional[Path]) -> bool:
    return (
        catalog_path is not None
        and "real_corpus" in catalog_path.parts
        and catalog_path.name == "curated_catalog.json"
    )


def _index_paths(catalog_path: Path) -> tuple[Path, Path]:
    cache_dir = catalog_path.parent / "cache"
    return (
        cache_dir / "local_lexical_index.sqlite",
        cache_dir / "local_lexical_index_meta.json",
    )


def _index_metadata(corpus_state_id: str) -> dict[str, str]:
    return {
        "corpus_state_id": corpus_state_id,
        "schema_version": _INDEX_SCHEMA_VERSION,
    }


def _create_index(connection: sqlite3.Connection, bundle: IngestionBundle) -> None:
    connection.execute(
        """
        CREATE VIRTUAL TABLE chunks
        USING fts5(
            chunk_id UNINDEXED,
            source_id UNINDEXED,
            source_kind UNINDEXED,
            source_role UNINDEXED,
            normalized_text
        )
        """
    )
    rows = [
        (
            chunk.chunk_id,
            chunk.source_id,
            chunk.source_kind.value,
            chunk.source_role_level.value,
            normalize_text_for_matching(chunk.text),
        )
        for document in bundle.documents
        for chunk in document.chunks
    ]
    connection.executemany(
        """
        INSERT INTO chunks (
            chunk_id,
            source_id,
            source_kind,
            source_role,
            normalized_text
        ) VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()


def _load_or_build_persisted_index(
    *,
    bundle: IngestionBundle,
    catalog_path: Path,
    corpus_state_id: str,
) -> _SQLiteFtsIndex:
    index_path, meta_path = _index_paths(catalog_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    desired_meta = _index_metadata(corpus_state_id)
    cache_key = str(index_path.resolve())
    if index_path.exists() and meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            if metadata == desired_meta:
                cached = _PERSISTED_INDEXES.get(cache_key)
                if cached is not None:
                    cached.cache_status = "cache_hit"
                    return cached
                connection = sqlite3.connect(index_path)
                index = _SQLiteFtsIndex(connection=connection, cache_status="cache_hit")
                _PERSISTED_INDEXES[cache_key] = index
                return index
        except Exception:
            pass

    cached = _PERSISTED_INDEXES.pop(cache_key, None)
    if cached is not None:
        cached.connection.close()
    if index_path.exists():
        index_path.unlink()
    if meta_path.exists():
        meta_path.unlink()

    connection = sqlite3.connect(index_path)
    _create_index(connection, bundle)
    meta_path.write_text(json.dumps(desired_meta, indent=2), encoding="utf-8")
    index = _SQLiteFtsIndex(connection=connection, cache_status="rebuilt")
    _PERSISTED_INDEXES[cache_key] = index
    return index


def _load_or_build_memory_index(bundle: IngestionBundle) -> _SQLiteFtsIndex:
    cache_key = id(bundle)
    cached = _MEMORY_INDEXES.get(cache_key)
    if cached is not None:
        cached.cache_status = "memory"
        return cached
    connection = sqlite3.connect(":memory:")
    _create_index(connection, bundle)
    index = _SQLiteFtsIndex(connection=connection, cache_status="memory")
    _MEMORY_INDEXES[cache_key] = index
    return index


def _load_or_build_sqlite_index(
    *,
    bundle: IngestionBundle,
    catalog_path: Optional[Path],
    corpus_state_id: Optional[str],
) -> _SQLiteFtsIndex:
    if _is_real_corpus_catalog(catalog_path) and corpus_state_id:
        assert catalog_path is not None
        return _load_or_build_persisted_index(
            bundle=bundle,
            catalog_path=catalog_path,
            corpus_state_id=corpus_state_id,
        )
    return _load_or_build_memory_index(bundle)


def _sqlite_fts_candidates(
    *,
    question: str,
    step: RetrievalPlanStep,
    bundle: IngestionBundle,
    hierarchy: SourceHierarchyConfig,
    runtime_config: RuntimeConfig,
    catalog_path: Optional[Path],
    corpus_state_id: Optional[str],
) -> tuple[List[RetrievalCandidate], LocalRetrievalTrace]:
    query_tokens = _tokenize(question)
    fts_query_tokens = _fts_match_tokens(
        query_tokens,
        runtime_config.semantic_expansions,
    )
    requires_semantic_backfill = set(fts_query_tokens) != set(query_tokens)
    trace = LocalRetrievalTrace()
    if not query_tokens:
        trace.fallback_used = True
        return (
            _finalize_candidates(
                _scan_candidates(
                    query_tokens=query_tokens,
                    step=step,
                    bundle=bundle,
                    hierarchy=hierarchy,
                    runtime_config=runtime_config,
                ),
                inspection_depth=step.inspection_depth,
            ),
            trace,
        )

    try:
        index = _load_or_build_sqlite_index(
            bundle=bundle,
            catalog_path=catalog_path,
            corpus_state_id=corpus_state_id,
        )
        trace.cache_status = index.cache_status
        chunk_lookup = _chunk_lookup(bundle)
        chunk_ids = index.query_step(
            query_tokens=fts_query_tokens,
            step=step,
            limit=runtime_config.local_index_candidate_pool,
        )
        candidates = [
            _score_chunk(
                chunk=chunk_lookup[chunk_id],
                query_tokens=query_tokens,
                hierarchy=hierarchy,
                runtime_config=runtime_config,
            )
            for chunk_id in chunk_ids
            if chunk_id in chunk_lookup
        ]
        finalized = _finalize_candidates(
            candidates,
            inspection_depth=step.inspection_depth,
        )
        if requires_semantic_backfill or len(finalized) < step.inspection_depth:
            trace.fallback_used = True
            finalized = _finalize_candidates(
                _merge_candidates(
                    candidates,
                    _scan_candidates(
                        query_tokens=query_tokens,
                        step=step,
                        bundle=bundle,
                        hierarchy=hierarchy,
                        runtime_config=runtime_config,
                    ),
                ),
                inspection_depth=step.inspection_depth,
            )
        return finalized, trace
    except Exception:
        trace.cache_status = "error_fallback_scan"
        trace.fallback_used = True
        return (
            _finalize_candidates(
                _scan_candidates(
                    query_tokens=query_tokens,
                    step=step,
                    bundle=bundle,
                    hierarchy=hierarchy,
                    runtime_config=runtime_config,
                ),
                inspection_depth=step.inspection_depth,
            ),
            trace,
        )


def retrieve_candidates_with_trace(
    question: str,
    step: RetrievalPlanStep,
    bundle: IngestionBundle,
    hierarchy: SourceHierarchyConfig,
    runtime_config: RuntimeConfig,
    *,
    catalog_path: Optional[Path] = None,
    corpus_state_id: Optional[str] = None,
) -> tuple[List[RetrievalCandidate], LocalRetrievalTrace]:
    if runtime_config.local_retrieval_backend == "sqlite_fts":
        return _sqlite_fts_candidates(
            question=question,
            step=step,
            bundle=bundle,
            hierarchy=hierarchy,
            runtime_config=runtime_config,
            catalog_path=catalog_path,
            corpus_state_id=corpus_state_id,
        )

    return (
        _finalize_candidates(
            _scan_candidates(
                query_tokens=_tokenize(question),
                step=step,
                bundle=bundle,
                hierarchy=hierarchy,
                runtime_config=runtime_config,
            ),
            inspection_depth=step.inspection_depth,
        ),
        LocalRetrievalTrace(cache_status="disabled", fallback_used=False),
    )


def retrieve_candidates(
    question: str,
    step: RetrievalPlanStep,
    bundle: IngestionBundle,
    hierarchy: SourceHierarchyConfig,
    runtime_config: RuntimeConfig,
    *,
    catalog_path: Optional[Path] = None,
    corpus_state_id: Optional[str] = None,
) -> List[RetrievalCandidate]:
    candidates, _trace = retrieve_candidates_with_trace(
        question,
        step,
        bundle,
        hierarchy,
        runtime_config,
        catalog_path=catalog_path,
        corpus_state_id=corpus_state_id,
    )
    return candidates
