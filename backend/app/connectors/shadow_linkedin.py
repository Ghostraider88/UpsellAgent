"""Shadow / fallback scraping adapter (LinkedIn-style).

DISABLED by default. This adapter is the "hidden fallback" mode: it only
activates when BOTH ``ENABLE_SHADOW_SOURCES=true`` AND the caller passes the
admin flag at request time. Every activation is audit-logged and any data it
produces is tagged ``source_mode=shadow`` so it is clearly distinguishable in
the UI and exports.

NOTE: This ships as an inert stub. Wiring it to a real provider (Bright Data /
PhantomBuster) must only be done where legally permitted; scraping LinkedIn/Xing
violates their ToS and carries GDPR risk in the EU.
"""
from __future__ import annotations

from app.config import settings
from app.connectors.base import RawPerson, Signal


class ShadowLinkedInAdapter:
    name = "shadow_linkedin"
    mode = "shadow"

    def is_available(self) -> bool:
        # Gated by the global feature flag. Per-request admin gating is enforced
        # in the registry / pipeline layer.
        return settings.enable_shadow_sources

    def find_people(self, company_name: str, icp: dict) -> list[RawPerson]:
        # Inert by design. Implement against a licensed provider only where legal.
        return []

    def find_signals(self, company_name: str) -> list[Signal]:
        return []
