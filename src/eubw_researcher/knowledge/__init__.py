"""Internal agentic knowledge-navigation layer."""

from .dynamic import (
    build_candidate_claim_targets,
    build_dynamic_claim_targets,
    selected_evidence_candidates,
)
from .legacy_import import ImportedKnowledgeAssets, load_imported_knowledge_assets
from .profiles import build_research_profile_trace
from .reading import build_reading_artifacts, detect_question_facets
from .service import KnowledgeService
from .source_crosswalk import build_source_crosswalk
from .verifier import build_claim_verification_records, verification_allows_answer_use

__all__ = [
    "KnowledgeService",
    "ImportedKnowledgeAssets",
    "build_candidate_claim_targets",
    "build_dynamic_claim_targets",
    "build_claim_verification_records",
    "build_research_profile_trace",
    "build_reading_artifacts",
    "detect_question_facets",
    "verification_allows_answer_use",
    "build_source_crosswalk",
    "load_imported_knowledge_assets",
    "selected_evidence_candidates",
]
