"""Arq worker definition for running enrichment jobs off the request path.

In production the API enqueues ``run_enrichment_job`` onto Redis and this worker
executes it. For local/dev/test the API can also run the pipeline inline.
"""
from __future__ import annotations

from arq.connections import RedisSettings

from app.config import settings
from app.pipeline.enrich import enrich_company


async def run_enrichment_job(ctx, **kwargs):
    # enrich_company is synchronous; Arq runs the coroutine, the call blocks the
    # worker task which is acceptable for this workload.
    return enrich_company(**kwargs)


class WorkerSettings:
    functions = [run_enrichment_job]
    # arq needs a RedisSettings object, not a bare DSN string.
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
