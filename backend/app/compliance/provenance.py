"""Provenance recording and GDPR suppression checks."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SourceRecord, SuppressionEntry


def record_provenance(
    session: Session,
    *,
    entity_id: str,
    entity_type: str,
    source_adapter: str,
    source_mode: str,
    raw_payload: dict | None = None,
) -> SourceRecord:
    """Persist a provenance row for an externally-sourced datapoint."""
    record = SourceRecord(
        entity_id=entity_id,
        entity_type=entity_type,
        source_adapter=source_adapter,
        source_mode=source_mode,
        raw_payload=raw_payload or {},
    )
    session.add(record)
    return record


def is_suppressed(session: Session, *, full_name: str | None, email: str | None) -> bool:
    """True if a person is on the opt-out / erasure list and must be skipped."""
    if not full_name and not email:
        return False
    stmt = select(SuppressionEntry)
    for entry in session.scalars(stmt):
        if email and entry.email and entry.email.lower() == email.lower():
            return True
        if full_name and entry.full_name and entry.full_name.lower() == full_name.lower():
            return True
    return False
