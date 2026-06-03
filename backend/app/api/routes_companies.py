"""Company analysis + graph/contacts retrieval."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import (
    Company,
    ContactScore,
    EnrichmentJob,
    ICPProfile,
    Person,
    Relationship,
    SourceRecord,
)
from app.pipeline import enrich_company
from app.schemas import AnalyzeRequest, EdgeOut, GraphOut, JobResponse, PersonOut

router = APIRouter(tags=["companies"])


@router.post("/companies/analyze", response_model=JobResponse)
def analyze_company(
    req: AnalyzeRequest,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
) -> JobResponse:
    """Kick off enrichment for a company. Runs as a background task."""
    icp_profile = ICPProfile(name=req.icp.name, definition=req.icp.model_dump())
    session.add(icp_profile)
    session.flush()

    job = EnrichmentJob(
        icp_profile_id=icp_profile.id,
        params={"company_name": req.company_name, "allow_shadow": req.allow_shadow},
    )
    session.add(job)
    session.commit()

    background.add_task(
        enrich_company,
        job_id=job.id,
        company_name=req.company_name,
        seed_contacts=[c.model_dump() for c in req.seed_contacts],
        icp=req.icp.model_dump(),
        icp_profile_id=icp_profile.id,
        allow_shadow=req.allow_shadow,
        actor="api",
    )
    return JobResponse(id=job.id, status=job.status, progress=job.progress)


def _person_to_out(
    person: Person, score: ContactScore | None, source_mode: str
) -> PersonOut:
    return PersonOut(
        id=person.id,
        full_name=person.full_name,
        current_title=person.current_title,
        seniority=person.seniority,
        department=person.department,
        location=person.location,
        is_seed=person.is_seed,
        score=score.score if score else None,
        rationale=score.rationale if score else None,
        matched_signals=score.matched_signals if score else [],
        source_mode=source_mode,
    )


def _load_graph(session: Session, company: Company) -> GraphOut:
    people = list(session.scalars(select(Person).where(Person.company_id == company.id)))
    scores = {
        s.person_id: s
        for s in session.scalars(
            select(ContactScore).where(
                ContactScore.person_id.in_([p.id for p in people])
            )
        )
    }
    modes = {
        r.entity_id: r.source_mode
        for r in session.scalars(
            select(SourceRecord).where(SourceRecord.entity_type == "person")
        )
    }
    edges = list(
        session.scalars(select(Relationship).where(Relationship.company_id == company.id))
    )
    return GraphOut(
        company_id=company.id,
        company_name=company.name,
        nodes=[
            _person_to_out(p, scores.get(p.id), modes.get(p.id, "compliant"))
            for p in people
        ],
        edges=[
            EdgeOut(
                source_person_id=e.source_person_id,
                target_person_id=e.target_person_id,
                type=e.type,
                confidence=e.confidence,
                evidence_ref=e.evidence_ref,
            )
            for e in edges
        ],
    )


@router.get("/companies/{company_id}/graph", response_model=GraphOut)
def get_graph(company_id: str, session: Session = Depends(get_session)) -> GraphOut:
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    return _load_graph(session, company)


@router.get("/companies/{company_id}/contacts", response_model=list[PersonOut])
def get_contacts(company_id: str, session: Session = Depends(get_session)) -> list[PersonOut]:
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    graph = _load_graph(session, company)
    return sorted(graph.nodes, key=lambda n: (n.score or 0), reverse=True)
