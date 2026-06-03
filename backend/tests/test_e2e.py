"""End-to-end flow in mock mode: analyze → poll job → fetch graph + contacts."""


def test_analyze_to_graph(client):
    payload = {
        "company_name": "ACME No-Code GmbH",
        "seed_contacts": [{"full_name": "Anna Schmidt", "title": "COO"}],
        "icp": {
            "name": "Ops Decision Makers",
            "roles": ["Head of Operations", "COO"],
            "functions": ["operations"],
            "seniority": ["C-Level", "Head"],
            "keywords": ["operations", "automation"],
        },
    }
    resp = client.post("/companies/analyze", json=payload)
    assert resp.status_code == 200
    job_id = resp.json()["id"]

    # BackgroundTasks run synchronously after the response in TestClient.
    job = client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "done", job
    company_id = job["company_id"]
    assert company_id

    graph = client.get(f"/companies/{company_id}/graph").json()
    assert len(graph["nodes"]) >= 5
    assert len(graph["edges"]) >= 1
    # Seed contact is flagged.
    assert any(n["is_seed"] for n in graph["nodes"])

    contacts = client.get(f"/companies/{company_id}/contacts").json()
    # Sorted by ICP score descending; top contact should be operations-related.
    assert contacts[0]["score"] is not None
    assert contacts[0]["score"] >= contacts[-1]["score"]
