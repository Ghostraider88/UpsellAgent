"""Pydantic request/response schemas for the API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SeedContact(BaseModel):
    full_name: str
    title: str | None = None


class ICPDefinition(BaseModel):
    name: str = "Default ICP"
    roles: list[str] = Field(default_factory=list)
    functions: list[str] = Field(default_factory=list)
    seniority: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    company_name: str
    seed_contacts: list[SeedContact] = Field(default_factory=list)
    icp: ICPDefinition
    # Hidden fallback: only honoured if the server also has shadow sources enabled.
    allow_shadow: bool = False


class JobResponse(BaseModel):
    id: str
    status: str
    progress: int
    company_id: str | None = None
    error: str | None = None


class PersonOut(BaseModel):
    id: str
    full_name: str
    current_title: str | None
    seniority: str | None
    department: str | None
    location: str | None
    is_seed: bool
    score: int | None = None
    rationale: str | None = None
    matched_signals: list[str] = Field(default_factory=list)
    source_mode: str = "compliant"


class EdgeOut(BaseModel):
    source_person_id: str
    target_person_id: str
    type: str
    confidence: float
    evidence_ref: str | None = None


class GraphOut(BaseModel):
    company_id: str
    company_name: str
    nodes: list[PersonOut]
    edges: list[EdgeOut]
