"""Compliance layer: provenance, suppression, lawful basis."""
from app.compliance.provenance import is_suppressed, record_provenance

__all__ = ["record_provenance", "is_suppressed"]
