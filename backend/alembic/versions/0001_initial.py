"""initial schema

Creates the full relational graph + provenance schema from the app metadata.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op
from app import models  # noqa: F401  (register models)
from app.db import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
