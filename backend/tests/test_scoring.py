from app.scoring import score_person


def test_heuristic_scores_operations_lead_high():
    icp = {
        "roles": ["Head of Operations", "COO"],
        "functions": ["operations"],
        "seniority": ["C-Level", "Head"],
        "keywords": ["operations"],
    }
    coo = score_person(
        {"current_title": "Chief Operating Officer", "department": "Operations", "seniority": "C-Level"},
        icp,
    )
    ic = score_person(
        {"current_title": "Junior Designer", "department": "Design", "seniority": "IC"},
        icp,
    )
    assert coo.score > ic.score
    assert coo.score >= 50
    assert isinstance(coo.matched_signals, list)
