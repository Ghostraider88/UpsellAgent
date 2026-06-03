"""Pluggable data-source connectors (compliant + shadow)."""
from app.connectors.registry import get_active_adapters

__all__ = ["get_active_adapters"]
