from app.connectors.base import Signal
from app.graph import build_relationships


def _people():
    return [
        {"id": "1", "full_name": "Anna Schmidt", "department": "Operations", "seniority": "C-Level", "reports_to": None, "works_with": ["Tobias Berger"]},
        {"id": "2", "full_name": "Tobias Berger", "department": "Operations", "seniority": "Head", "reports_to": "Anna Schmidt", "works_with": []},
        {"id": "3", "full_name": "Markus Klein", "department": "Engineering", "seniority": "VP", "reports_to": None, "works_with": []},
    ]


def test_explicit_reports_to_edge():
    edges = build_relationships(_people(), [])
    assert any(
        e.source_person_id == "2" and e.target_person_id == "1" and e.type == "reports_to"
        and e.confidence >= 0.9
        for e in edges
    )


def test_works_with_edge():
    edges = build_relationships(_people(), [])
    assert any(e.type == "works_with" for e in edges)


def test_co_mention_from_signal():
    sig = Signal(text="Anna and Markus lead the initiative", mentioned_names=["Anna Schmidt", "Markus Klein"])
    edges = build_relationships(_people(), [sig])
    assert any(e.type == "co_mentioned" for e in edges)
