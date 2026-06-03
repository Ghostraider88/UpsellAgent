"""SQLAlchemy ORM models — the relational graph + provenance schema.

The org graph is modelled relationally (``Person`` nodes + ``Relationship``
edges). Every externally-sourced fact is backed by a ``SourceRecord`` carrying
provenance (which adapter, compliant vs. shadow, when) — essential for GDPR
auditability and quality scoring.
"""
from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class SourceMode(str, enum.Enum):
    compliant = "compliant"
    shadow = "shadow"


class RelationshipType(str, enum.Enum):
    reports_to = "reports_to"
    works_with = "works_with"
    co_mentioned = "co_mentioned"
    same_team = "same_team"
    peer = "peer"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Company(Base):
    __tablename__ = "company"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(512), index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    register_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    people: Mapped[list[Person]] = relationship(back_populates="company")


class Person(Base):
    __tablename__ = "person"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    current_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # email / linkedin / xing handles — nullable, provenance tracked separately
    contact_handles: Mapped[dict] = mapped_column(JSON, default=dict)
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    company: Mapped[Company] = relationship(back_populates="people")


class Relationship(Base):
    __tablename__ = "relationship"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), index=True)
    source_person_id: Mapped[str] = mapped_column(ForeignKey("person.id"))
    target_person_id: Mapped[str] = mapped_column(ForeignKey("person.id"))
    type: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ICPProfile(Base):
    __tablename__ = "icp_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    # structured definition: roles, functions, seniority, keywords
    definition: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ContactScore(Base):
    __tablename__ = "contact_score"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    person_id: Mapped[str] = mapped_column(ForeignKey("person.id"), index=True)
    icp_profile_id: Mapped[str] = mapped_column(ForeignKey("icp_profile.id"), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_signals: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SourceRecord(Base):
    """Provenance for every externally-sourced datapoint (GDPR auditability)."""

    __tablename__ = "source_record"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))  # company | person | relationship
    source_adapter: Mapped[str] = mapped_column(String(64))
    source_mode: Mapped[str] = mapped_column(String(16), default=SourceMode.compliant.value)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    lawful_basis: Mapped[str] = mapped_column(String(64), default="legitimate_interest_b2b")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class EnrichmentJob(Base):
    __tablename__ = "enrichment_job"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("company.id"), nullable=True)
    icp_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("icp_profile.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.pending.value)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SuppressionEntry(Base):
    """Opt-out / GDPR erasure list — people that must never be processed."""

    __tablename__ = "suppression_list"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
