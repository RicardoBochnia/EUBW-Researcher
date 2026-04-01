"""Answer composition."""

from .composer import TOPOLOGY_FACET_IDS, build_facet_coverage_report, compose_answer
from .grouping import build_provisional_grouping, supports_provisional_grouping

__all__ = [
    "TOPOLOGY_FACET_IDS",
    "build_facet_coverage_report",
    "compose_answer",
    "build_provisional_grouping",
    "supports_provisional_grouping",
]
