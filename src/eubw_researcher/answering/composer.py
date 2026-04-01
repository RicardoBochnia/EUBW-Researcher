from __future__ import annotations

from typing import List, Optional

from eubw_researcher.models import ClaimState, LedgerEntry


def _render_citations(entry: LedgerEntry) -> str:
    citations = entry.governing_evidence or entry.supporting_evidence or entry.contradicting_evidence
    if not citations:
        return "no admissible citation"
    return "; ".join(evidence.citation.render() for evidence in citations)


def _section(title: str, entries: List[LedgerEntry]) -> List[str]:
    if not entries:
        return []
    lines = [title + ":"]
    for entry in entries:
        lines.append(f"- {entry.claim_text}")
        lines.append(f"  Rationale: {entry.rationale}")
        lines.append(f"  Evidence: {_render_citations(entry)}")
    return lines


def compose_answer(
    question: str,
    entries: List[LedgerEntry],
    clarification_note: Optional[str] = None,
) -> str:
    if not entries:
        if clarification_note:
            return (
                f"First-pass note: {clarification_note}\n"
                "No approved answer could be composed from admissible evidence. Review the stored ledger and gap records for unresolved points."
            )
        return "No approved answer could be composed from admissible evidence. Review the stored ledger and gap records for unresolved points."

    summary = "Source-bound answer:"
    if len(entries) >= 2:
        summary += " the reviewed sources support a differentiated answer rather than a flat yes/no."

    confirmed = [entry for entry in entries if entry.final_claim_state == ClaimState.CONFIRMED]
    interpretive = [
        entry for entry in entries if entry.final_claim_state == ClaimState.INTERPRETIVE
    ]
    open_entries = [entry for entry in entries if entry.final_claim_state == ClaimState.OPEN]

    lines: List[str] = [summary]
    if clarification_note:
        lines.append(f"First-pass note: {clarification_note}")
    lines.extend(_section("Confirmed", confirmed))
    lines.extend(_section("Interpretive", interpretive))
    lines.extend(_section("Open", open_entries))

    return "\n".join(lines)
