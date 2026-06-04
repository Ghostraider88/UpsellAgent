"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_companies, routes_health, routes_jobs
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the schema exists for every launch path. ``create_all`` is
    # idempotent, so this is safe alongside Alembic (which remains the source of
    # truth for versioned migrations) and covers SQLite/dev as well as a plain
    # ``uvicorn`` start against Postgres without a separate migration step.
    init_db()
    yield


app = FastAPI(title="UpsellAgent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_companies.router)
app.include_router(routes_jobs.router)
