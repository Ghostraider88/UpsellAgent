"""Build org-graph edges from resolved people + unstructured signals.

Edges combine explicit source hints, seniority/department heuristics for
hierarchy inference, and co-mention extraction from news signals. Every edge
carries a confidence and an evidence reference.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from app.connectors.base import Signal

# Lower index = more senior. Used to orient inferred reporting lines.
_SENIORITY_RANK = {
    "c-level": 0,
    "vp": 1,
    "head": 2,
    "director": 2,
    "lead": 3,
    "manager": 3,
    "ic": 4,
}


def _rank(seniority: str | None) -> int:
    s = (seniority or "").lower()
    for key, rank in _SENIORITY_RANK.items():
        if key in s:
            return rank
    return 5


@dataclass
class Edge:
    source_person_id: str
    target_person_id: str
    type: str
    confidence: float
    evidence_ref: str | None = None


def build_relationships(people: list[dict], signals: list[Signal]) -> list[Edge]:
    """Return de-duplicated edges for the given company.

    Args:
        people: dicts with keys ``id``, ``full_name``, ``department``,
            ``seniority``, ``reports_to`` (name hint), ``works_with`` (name hints).
        signals: unstructured texts used for co-mention extraction.
    """
    by_name = {p["full_name"].lower(): p for p in people}
    edges: dict[tuple[str, str, str], Edge] = {}

    def add(src: str, tgt: str, etype: str, conf: float, ev: str | None = None) -> None:
        if src == tgt:
            return
        key = (src, tgt, etype)
        existing = edges.get(key)
        if existing is None or conf > existing.confidence:
            edges[key] = Edge(src, tgt, etype, conf, ev)

    # 1) Explicit reports_to hints (highest confidence)
    for p in people:
        boss_name = (p.get("reports_to") or "").lower()
        boss = by_name.get(boss_name)
        if boss:
            add(p["id"], boss["id"], "reports_to", 0.9, "source hint: reports_to")

    # 2) Explicit works_with hints
    for p in people:
        for name in p.get("works_with") or []:
            other = by_name.get(name.lower())
            if other:
                add(p["id"], other["id"], "works_with", 0.7, "source hint: works_with")

    # 3) Department co-membership → same_team / inferred hierarchy
    depts: dict[str, list[dict]] = {}
    for p in people:
        dept = (p.get("department") or "").lower()
        if dept:
            depts.setdefault(dept, []).append(p)
    for members in depts.values():
        for a, b in combinations(members, 2):
            add(a["id"], b["id"], "same_team", 0.6, "shared department")
        # Inferred reporting line: more-senior member in same dept, only if no
        # explicit reports_to already established for the junior person.
        for junior in members:
            if any(
                (junior.get("reports_to") or "").lower() == m["full_name"].lower()
                for m in members
            ):
                continue
            seniors = [m for m in members if _rank(m["seniority"]) < _rank(junior["seniority"])]
            if seniors:
                boss = min(seniors, key=lambda m: _rank(m["seniority"]))
                add(junior["id"], boss["id"], "reports_to", 0.5, "inferred: seniority+dept")

    # 4) Co-mention in signals → co_mentioned
    for sig in signals:
        mentioned = [by_name[n.lower()] for n in sig.mentioned_names if n.lower() in by_name]
        for a, b in combinations(mentioned, 2):
            ev = f"co-mentioned: {sig.url or sig.text[:80]}"
            add(a["id"], b["id"], "co_mentioned", 0.6, ev)

    return list(edges.values())
