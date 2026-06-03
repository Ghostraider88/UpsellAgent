"""Test fixtures: isolated in-memory SQLite DB + FastAPI test client."""
from __future__ import annotations

import os

# Force an isolated test database before app modules read settings.
os.environ["DATABASE_URL"] = "sqlite:///./test_upsell.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    from app.db import Base, engine

    # Fresh schema for the test session.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
