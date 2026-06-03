"""Adapter registry — selects which sources are active for a given request.

Compliant adapters are always eligible. Shadow adapters require *both* the
global feature flag and an explicit per-request admin opt-in, and every such
activation is recorded for the audit log.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.connectors.base import SourceAdapter
from app.connectors.mock import MockAdapter
from app.connectors.serpapi_news import SerpApiNewsAdapter
from app.connectors.shadow_linkedin import ShadowLinkedInAdapter

logger = logging.getLogger("upsell.connectors")

# Instantiated once; adapters are stateless.
_COMPLIANT: list[SourceAdapter] = [MockAdapter(), SerpApiNewsAdapter()]
_SHADOW: list[SourceAdapter] = [ShadowLinkedInAdapter()]


def get_active_adapters(
    allow_shadow: bool = False, actor: str | None = None
) -> list[SourceAdapter]:
    """Return adapters eligible for this request.

    Args:
        allow_shadow: per-request admin opt-in to the hidden fallback mode.
        actor: identity of the caller (for the audit log).
    """
    adapters = [a for a in _COMPLIANT if a.is_available()]

    if allow_shadow and settings.enable_shadow_sources:
        active_shadow = [a for a in _SHADOW if a.is_available()]
        if active_shadow:
            logger.warning(
                "SHADOW sources activated by actor=%s adapters=%s",
                actor or "unknown",
                [a.name for a in active_shadow],
            )
            adapters.extend(active_shadow)

    return adapters
