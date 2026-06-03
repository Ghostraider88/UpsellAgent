"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_companies, routes_health, routes_jobs
from app.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For SQLite/dev we auto-create tables; production relies on Alembic.
    if settings.database_url.startswith("sqlite"):
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
