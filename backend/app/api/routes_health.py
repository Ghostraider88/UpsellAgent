"""Health + readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "env": settings.app_env,
        "llm_enabled": settings.llm_enabled,
        "shadow_sources_enabled": settings.enable_shadow_sources,
    }
