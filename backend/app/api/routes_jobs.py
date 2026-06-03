"""Job status endpoint (polled by the frontend during enrichment)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import EnrichmentJob
from app.schemas import JobResponse

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(get_session)) -> JobResponse:
    job = session.get(EnrichmentJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobResponse(
        id=job.id,
        status=job.status,
        progress=job.progress,
        company_id=job.company_id,
        error=job.error,
    )
