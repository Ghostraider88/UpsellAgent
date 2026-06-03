"""Source adapter interface + transport DTOs.

Every data source — a compliant API or a shadow scraper — implements the same
``SourceAdapter`` contract, so the pipeline is fully provider-agnostic and
sources can be swapped or stacked without touching downstream logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

Mode = Literal["compliant", "shadow"]


@dataclass
class RawPerson:
    """A person record as returned by a source, before entity resolution."""

    full_name: str
    title: str | None = None
    department: str | None = None
    seniority: str | None = None
    location: str | None = None
    handles: dict = field(default_factory=dict)  # email / linkedin / xing
    # free-form hints the source knows about who this person works with
    works_with: list[str] = field(default_factory=list)
    reports_to: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class Signal:
    """An unstructured signal (e.g. a news snippet) for relation extraction."""

    text: str
    url: str | None = None
    mentioned_names: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@runtime_checkable
class SourceAdapter(Protocol):
    name: str
    mode: Mode

    def is_available(self) -> bool:
        """Whether this adapter is configured/enabled and may be used."""
        ...

    def find_people(self, company_name: str, icp: dict) -> list[RawPerson]:
        ...

    def find_signals(self, company_name: str) -> list[Signal]:
        ...
