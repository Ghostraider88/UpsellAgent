"""Mock compliant adapter — deterministic synthetic org for offline/dev/CI.

Returns a small but realistic company graph so the full pipeline (entity
resolution → graph → scoring → visualisation) can be exercised end-to-end
without any external API keys.
"""
from __future__ import annotations

from app.connectors.base import RawPerson, Signal


class MockAdapter:
    name = "mock"
    mode = "compliant"

    def is_available(self) -> bool:
        return True

    def find_people(self, company_name: str, icp: dict) -> list[RawPerson]:
        return [
            RawPerson(
                full_name="Anna Schmidt",
                title="Chief Operating Officer",
                department="Operations",
                seniority="C-Level",
                location="Berlin, DE",
                handles={"linkedin": "linkedin.com/in/anna-schmidt"},
                works_with=["Tobias Berger", "Markus Klein"],
            ),
            RawPerson(
                full_name="Tobias Berger",
                title="Head of Operations",
                department="Operations",
                seniority="Head",
                location="Berlin, DE",
                handles={"email": "t.berger@example.com"},
                reports_to="Anna Schmidt",
                works_with=["Sarah Wolf"],
            ),
            RawPerson(
                full_name="Sarah Wolf",
                title="Operations Manager",
                department="Operations",
                seniority="Manager",
                location="Munich, DE",
                reports_to="Tobias Berger",
            ),
            RawPerson(
                full_name="Markus Klein",
                title="VP Engineering",
                department="Engineering",
                seniority="VP",
                location="Berlin, DE",
                works_with=["Anna Schmidt"],
            ),
            RawPerson(
                full_name="Julia Neumann",
                title="Automation Lead",
                department="Engineering",
                seniority="Lead",
                location="Remote, DE",
                reports_to="Markus Klein",
            ),
            RawPerson(
                full_name="Peter Hoffmann",
                title="Chief Financial Officer",
                department="Finance",
                seniority="C-Level",
                location="Berlin, DE",
            ),
        ]

    def find_signals(self, company_name: str) -> list[Signal]:
        return [
            Signal(
                text=(
                    f"{company_name} announced that COO Anna Schmidt and VP "
                    "Engineering Markus Klein will jointly lead a new automation "
                    "initiative."
                ),
                url="https://news.example.com/automation",
                mentioned_names=["Anna Schmidt", "Markus Klein"],
            ),
        ]
