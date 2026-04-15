"""Answer composition."""

from .composer import (
    TOPOLOGY_FACET_IDS,
    build_facet_coverage_report,
    compose_answer,
    compose_answer_bundle,
)
from .grouping import build_provisional_grouping, supports_provisional_grouping
from .relation_hints import build_relation_hint_report, supports_relation_hints

__all__ = [
    "TOPOLOGY_FACET_IDS",
    "build_facet_coverage_report",
    "compose_answer",
    "compose_answer_bundle",
    "build_provisional_grouping",
    "build_relation_hint_report",
    "supports_relation_hints",
    "supports_provisional_grouping",
]
