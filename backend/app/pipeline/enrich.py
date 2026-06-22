"""End-to-end enrichment: sources → resolve → graph → ICP scoring.

Runs synchronously against its own DB session so it can be driven either inline
(FastAPI background task) or from an Arq worker. Progress is written to the
``EnrichmentJob`` row for the frontend to poll/stream.
"""
from __future__ import annotations

import logging

from app.compliance import is_suppressed, record_provenance
from app.connectors import get_active_adapters
from app.connectors.base import RawPerson, Signal
from app.db import SessionLocal
from app.graph import build_relationships
from app.models import (
    Company,
    ContactScore,
    EnrichmentJob,
    JobStatus,
    Person,
    Relationship,
)
from app.scoring import score_person

logger = logging.getLogger("upsell.pipeline")


def _resolve_people(raw: list[RawPerson]) -> list[RawPerson]:
    """Entity resolution: merge duplicate people by normalized name."""
    merged: dict[str, RawPerson] = {}
    for r in raw:
        key = r.full_name.strip().lower()
        if not key:
            continue
        if key not in merged:
            merged[key] = RawPerson(full_name=r.full_name.strip())
        m = merged[key]
        m.title = m.title or r.title
        m.department = m.department or r.department
        m.seniority = m.seniority or r.seniority
        m.location = m.location or r.location
        m.reports_to = m.reports_to or r.reports_to
        m.handles = {**r.handles, **m.handles}
        m.works_with = sorted(set(m.works_with) | set(r.works_with))
    return list(merged.values())


def enrich_company(
    job_id: str,
    company_name: str,
    seed_contacts: list[dict],
    icp: dict,
    icp_profile_id: str | None = None,
    allow_shadow: bool = False,
    actor: str | None = None,
) -> str:
    """Run the full pipeline for one company. Returns the company id."""
    session = SessionLocal()
    try:
        job = session.get(EnrichmentJob, job_id)
        if job:
            job.status = JobStatus.running.value
            job.progress = 5
            session.commit()

        adapters = get_active_adapters(allow_shadow=allow_shadow, actor=actor)

        # 1) Gather people + signals from all active sources
        raw_people: list[RawPerson] = []
        for sc in seed_contacts:
            raw_people.append(
                RawPerson(full_name=sc["full_name"], title=sc.get("title"))
            )
        signals: list[Signal] = []
        source_of: dict[str, str] = {}  # name -> adapter that first produced it
        source_mode: dict[str, str] = {}
        for adapter in adapters:
            for rp in adapter.find_people(company_name, icp):
                raw_people.append(rp)
                source_of.setdefault(rp.full_name.lower(), adapter.name)
                source_mode.setdefault(rp.full_name.lower(), adapter.mode)
            for sig in adapter.find_signals(company_name):
                signals.append(sig)
                # Promote people mentioned in signals (e.g. news) into the roster
                # so they appear in the graph, not just as relationship endpoints.
                for name in sig.mentioned_names:
                    key = name.strip().lower()
                    if not key:
                        continue
                    if key not in source_of:
                        raw_people.append(RawPerson(full_name=name.strip()))
                        source_of[key] = adapter.name
                        source_mode[key] = adapter.mode
        if job:
            job.progress = 35
            session.commit()

        # 2) Entity resolution
        resolved = _resolve_people(raw_people)

        # 3) Persist company + people (+ provenance), honouring suppression list
        company = Company(name=company_name)
        session.add(company)
        session.flush()

        person_rows: list[dict] = []
        seed_names = {s["full_name"].strip().lower() for s in seed_contacts}
        for rp in resolved:
            if is_suppressed(session, full_name=rp.full_name, email=rp.handles.get("email")):
                logger.info("Skipping suppressed person: %s", rp.full_name)
                continue
            p = Person(
                company_id=company.id,
                full_name=rp.full_name,
                current_title=rp.title,
                normalized_role=(rp.title or "").lower() or None,
                seniority=rp.seniority,
                department=rp.department,
                location=rp.location,
                contact_handles=rp.handles,
                is_seed=rp.full_name.strip().lower() in seed_names,
            )
            session.add(p)
            session.flush()
            adapter_name = source_of.get(rp.full_name.lower(), "seed")
            record_provenance(
                session,
                entity_id=p.id,
                entity_type="person",
                source_adapter=adapter_name,
                source_mode=source_mode.get(rp.full_name.lower(), "compliant"),
                raw_payload=rp.raw,
            )
            person_rows.append(
                {
                    "id": p.id,
                    "full_name": p.full_name,
                    "department": p.department,
                    "seniority": p.seniority,
                    "reports_to": rp.reports_to,
                    "works_with": rp.works_with,
                    "current_title": p.current_title,
                }
            )
        session.commit()
        if job:
            job.progress = 60
            session.commit()

        # 4) Build + persist relationships
        edges = build_relationships(person_rows, signals)
        for e in edges:
            session.add(
                Relationship(
                    company_id=company.id,
                    source_person_id=e.source_person_id,
                    target_person_id=e.target_person_id,
                    type=e.type,
                    confidence=e.confidence,
                    evidence_ref=e.evidence_ref,
                )
            )
        session.commit()
        if job:
            job.progress = 80
            session.commit()

        # 5) ICP scoring
        if icp_profile_id:
            for pr in person_rows:
                result = score_person(pr, icp)
                session.add(
                    ContactScore(
                        person_id=pr["id"],
                        icp_profile_id=icp_profile_id,
                        score=result.score,
                        rationale=result.rationale,
                        matched_signals=result.matched_signals,
                    )
                )
            session.commit()

        if job:
            job.status = JobStatus.done.value
            job.company_id = company.id
            job.progress = 100
            session.commit()
        return company.id
    except Exception as exc:  # noqa: BLE001
        logger.exception("Enrichment failed for job %s", job_id)
        session.rollback()
        job = session.get(EnrichmentJob, job_id)
        if job:
            job.status = JobStatus.failed.value
            job.error = str(exc)
            session.commit()
        raise
    finally:
        session.close()
