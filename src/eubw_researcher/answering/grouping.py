from __future__ import annotations

from typing import Dict, List

from eubw_researcher.models import LedgerEntry, ProvisionalGroup, QueryIntent


def supports_provisional_grouping(query_intent: QueryIntent) -> bool:
    return any(target.grouping_label for target in query_intent.claim_targets)


def build_provisional_grouping(
    query_intent: QueryIntent,
    approved_entries: List[LedgerEntry],
) -> List[ProvisionalGroup]:
    if not supports_provisional_grouping(query_intent):
        return []

    target_labels: Dict[str, str] = {
        target.target_id: target.grouping_label or "Ungrouped"
        for target in query_intent.claim_targets
        if target.grouping_label
    }

    grouped_claims: Dict[str, Dict[str, set]] = {}
    for entry in approved_entries:
        label = target_labels.get(entry.claim_id)
        if label is None:
            continue
        bucket = grouped_claims.setdefault(
            label,
            {"claim_ids": set(), "source_ids": set()},
        )
        bucket["claim_ids"].add(entry.claim_id)
        for citation in entry.citations:
            bucket["source_ids"].add(citation.source_id)

    groups: List[ProvisionalGroup] = []
    for label, payload in grouped_claims.items():
        groups.append(
            ProvisionalGroup(
                label=label,
                claim_ids=sorted(payload["claim_ids"]),
                source_ids=sorted(payload["source_ids"]),
                provisional=True,
            )
        )
    groups.sort(key=lambda item: item.label.lower())
    return groups
